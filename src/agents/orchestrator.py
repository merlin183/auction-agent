"""오케스트레이터 에이전트 - 워크플로우 조율"""
import asyncio
from typing import TypedDict, Optional, List, Literal, Callable, TypeVar
from functools import wraps
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
import structlog

from .data_collector import DataCollectorAgent
from .rights_analyzer import RightsAnalyzerAgent
from .valuator import ValuatorAgent
from .location_analyzer import LocationAnalyzerAgent
from .risk_assessor import RiskAssessorAgent
from .bid_strategist import BidStrategistAgent
from .red_team import RedTeamAgent
from .reporter import ReporterAgent

logger = structlog.get_logger()

T = TypeVar('T')


# ==================== 상태 정의 ====================

class AuctionState(TypedDict):
    """워크플로우 전체 상태"""

    # 입력
    case_number: str
    user_settings: dict

    # 수집된 데이터
    collected_data: Optional[dict]

    # 각 에이전트 분석 결과
    rights_analysis: Optional[dict]
    location_analysis: Optional[dict]
    valuation: Optional[dict]
    risk_assessment: Optional[dict]
    bid_strategy: Optional[dict]
    red_team_review: Optional[dict]

    # 최종 결과
    final_report: Optional[dict]

    # 워크플로우 메타
    current_step: str
    errors: List[str]
    status: Literal["running", "completed", "failed", "paused"]
    retry_count: int


# ==================== 재시도 데코레이터 ====================

def with_retry(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """재시도 데코레이터"""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None
            current_delay = delay

            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(
                            "재시도",
                            attempt=attempt + 1,
                            max_retries=max_retries,
                            error=str(e),
                            function=func.__name__
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            "재시도 최대 횟수 초과",
                            function=func.__name__,
                            error=str(e)
                        )

            raise last_exception

        return wrapper
    return decorator


# ==================== 워크플로우 노드 함수 ====================

async def collect_data(state: AuctionState) -> AuctionState:
    """데이터 수집 노드"""
    log = logger.bind(
        case_number=state["case_number"],
        step="data_collection"
    )

    try:
        log.info("데이터 수집 시작")
        state["current_step"] = "data_collection"

        data_collector = DataCollectorAgent()
        result = await data_collector.collect(
            case_number=state["case_number"]
        )

        state["collected_data"] = result
        log.info(
            "데이터 수집 완료",
            documents_count=len(result.get("documents", [])),
            has_property_info=bool(result.get("property"))
        )

        return state

    except Exception as e:
        error_msg = f"데이터 수집 실패: {str(e)}"
        log.error("데이터 수집 에러", error=str(e))
        state["errors"].append(error_msg)
        state["status"] = "failed"
        return state


async def analyze_rights(state: AuctionState) -> AuctionState:
    """권리분석 노드"""
    log = logger.bind(
        case_number=state["case_number"],
        step="rights_analysis"
    )

    try:
        log.info("권리분석 시작")
        state["current_step"] = "rights_analysis"

        analyzer = RightsAnalyzerAgent()
        result = await analyzer.analyze(
            case_number=state["case_number"],
            documents=state["collected_data"]["documents"]
        )

        state["rights_analysis"] = result
        log.info("권리분석 완료", rights_count=len(result.get("rights", [])))

        return state

    except Exception as e:
        error_msg = f"권리분석 실패: {str(e)}"
        log.error("권리분석 에러", error=str(e))
        state["errors"].append(error_msg)
        # 부분 실패 허용
        state["rights_analysis"] = {"status": "failed", "error": str(e)}
        return state


async def analyze_location(state: AuctionState) -> AuctionState:
    """입지분석 노드"""
    log = logger.bind(
        case_number=state["case_number"],
        step="location_analysis"
    )

    try:
        log.info("입지분석 시작")
        state["current_step"] = "location_analysis"

        analyzer = LocationAnalyzerAgent()
        result = await analyzer.analyze(
            address=state["collected_data"]["property"]["address"],
            property_type=state["collected_data"]["property"]["type"]
        )

        state["location_analysis"] = result
        log.info("입지분석 완료")

        return state

    except Exception as e:
        error_msg = f"입지분석 실패: {str(e)}"
        log.error("입지분석 에러", error=str(e))
        state["errors"].append(error_msg)
        # 부분 실패 허용
        state["location_analysis"] = {"status": "failed", "error": str(e)}
        return state


async def parallel_analysis(state: AuctionState) -> AuctionState:
    """병렬 분석 노드 (권리분석 + 입지분석)"""
    log = logger.bind(
        case_number=state["case_number"],
        step="parallel_analysis"
    )

    try:
        log.info("병렬 분석 시작")
        state["current_step"] = "parallel_analysis"

        # 에이전트 인스턴스 생성
        rights_analyzer = RightsAnalyzerAgent()
        location_analyzer = LocationAnalyzerAgent()

        # 병렬 태스크 생성
        rights_task = asyncio.create_task(
            rights_analyzer.analyze(
                case_number=state["case_number"],
                documents=state["collected_data"]["documents"]
            )
        )

        location_task = asyncio.create_task(
            location_analyzer.analyze(
                address=state["collected_data"]["property"]["address"],
                property_type=state["collected_data"]["property"]["type"]
            )
        )

        # 동시 완료 대기
        rights_result, location_result = await asyncio.gather(
            rights_task, location_task, return_exceptions=True
        )

        # 권리분석 결과 처리
        if not isinstance(rights_result, Exception):
            state["rights_analysis"] = rights_result
            log.info("권리분석 완료", rights_count=len(rights_result.get("rights", [])))
        else:
            error_msg = f"권리분석 실패: {str(rights_result)}"
            state["errors"].append(error_msg)
            state["rights_analysis"] = {"status": "failed", "error": str(rights_result)}
            log.error("권리분석 에러", error=str(rights_result))

        # 입지분석 결과 처리
        if not isinstance(location_result, Exception):
            state["location_analysis"] = location_result
            log.info("입지분석 완료")
        else:
            error_msg = f"입지분석 실패: {str(location_result)}"
            state["errors"].append(error_msg)
            state["location_analysis"] = {"status": "failed", "error": str(location_result)}
            log.error("입지분석 에러", error=str(location_result))

        return state

    except Exception as e:
        error_msg = f"병렬 분석 실패: {str(e)}"
        log.error("병렬 분석 에러", error=str(e))
        state["errors"].append(error_msg)
        return state


async def evaluate_value(state: AuctionState) -> AuctionState:
    """가치평가 노드"""
    log = logger.bind(
        case_number=state["case_number"],
        step="valuation"
    )

    try:
        log.info("가치평가 시작")
        state["current_step"] = "valuation"

        valuator = ValuatorAgent()
        result = await valuator.valuate(
            case_number=state["case_number"],
            property_info=state["collected_data"]["property"],
            rights_analysis=state["rights_analysis"]
        )

        state["valuation"] = result
        log.info(
            "가치평가 완료",
            estimated_value=result.get("estimated_value")
        )

        return state

    except Exception as e:
        error_msg = f"가치평가 실패: {str(e)}"
        log.error("가치평가 에러", error=str(e))
        state["errors"].append(error_msg)
        return state


async def assess_risk(state: AuctionState) -> AuctionState:
    """위험평가 노드"""
    log = logger.bind(
        case_number=state["case_number"],
        step="risk_assessment"
    )

    try:
        log.info("위험평가 시작")
        state["current_step"] = "risk_assessment"

        assessor = RiskAssessorAgent()
        result = await assessor.assess(
            rights_analysis=state["rights_analysis"],
            valuation=state["valuation"],
            location_analysis=state["location_analysis"]
        )

        state["risk_assessment"] = result
        log.info(
            "위험평가 완료",
            risk_grade=result.get("risk_grade"),
            total_score=result.get("total_score")
        )

        return state

    except Exception as e:
        error_msg = f"위험평가 실패: {str(e)}"
        log.error("위험평가 에러", error=str(e))
        state["errors"].append(error_msg)
        return state


async def generate_bid_strategy(state: AuctionState) -> AuctionState:
    """입찰전략 노드"""
    log = logger.bind(
        case_number=state["case_number"],
        step="bid_strategy"
    )

    try:
        log.info("입찰전략 생성 시작")
        state["current_step"] = "bid_strategy"

        strategist = BidStrategistAgent()
        result = await strategist.generate_strategy(
            valuation=state["valuation"],
            rights_analysis=state["rights_analysis"],
            risk_analysis=state["risk_assessment"],
            user_settings=state["user_settings"]
        )

        state["bid_strategy"] = result
        log.info(
            "입찰전략 생성 완료",
            recommended_bid=result.get("recommended_bid")
        )

        return state

    except Exception as e:
        error_msg = f"입찰전략 생성 실패: {str(e)}"
        log.error("입찰전략 에러", error=str(e))
        state["errors"].append(error_msg)
        return state


async def red_team_review(state: AuctionState) -> AuctionState:
    """레드팀 검토 노드"""
    log = logger.bind(
        case_number=state["case_number"],
        step="red_team_review"
    )

    try:
        log.info("레드팀 검토 시작")
        state["current_step"] = "red_team_review"

        red_team = RedTeamAgent()
        result = await red_team.review(
            rights_analysis=state["rights_analysis"],
            valuation=state["valuation"],
            risk_assessment=state["risk_assessment"],
            bid_strategy=state["bid_strategy"]
        )

        state["red_team_review"] = result
        log.info(
            "레드팀 검토 완료",
            issues_found=len(result.get("issues", []))
        )

        return state

    except Exception as e:
        error_msg = f"레드팀 검토 실패: {str(e)}"
        log.error("레드팀 에러", error=str(e))
        state["errors"].append(error_msg)
        # 레드팀은 선택적이므로 실패해도 진행
        state["red_team_review"] = {"status": "failed", "error": str(e)}
        return state


async def generate_report(state: AuctionState) -> AuctionState:
    """리포트 생성 노드"""
    log = logger.bind(
        case_number=state["case_number"],
        step="report_generation"
    )

    try:
        log.info("리포트 생성 시작")
        state["current_step"] = "report_generation"

        reporter = ReporterAgent()
        result = await reporter.generate(
            case_number=state["case_number"],
            rights_analysis=state["rights_analysis"],
            location_analysis=state["location_analysis"],
            valuation=state["valuation"],
            risk_assessment=state["risk_assessment"],
            bid_strategy=state["bid_strategy"],
            red_team_review=state.get("red_team_review")
        )

        state["final_report"] = result
        state["status"] = "completed"
        log.info("리포트 생성 완료", report_path=result.get("report_path"))

        return state

    except Exception as e:
        error_msg = f"리포트 생성 실패: {str(e)}"
        log.error("리포트 생성 에러", error=str(e))
        state["errors"].append(error_msg)
        state["status"] = "failed"
        return state


# ==================== 조건부 분기 함수 ====================

def check_data_completeness(state: AuctionState) -> str:
    """데이터 완전성 검사"""

    collected = state.get("collected_data")

    if not collected:
        logger.error("데이터 수집 결과 없음", case_number=state["case_number"])
        return "failed"

    required_fields = ["documents", "property", "auction_info"]
    missing = [f for f in required_fields if f not in collected]

    if missing:
        error_msg = f"필수 데이터 누락: {', '.join(missing)}"
        state["errors"].append(error_msg)
        logger.warning(
            "데이터 불완전",
            case_number=state["case_number"],
            missing_fields=missing
        )

        # 재시도 제한
        retry_count = state.get("retry_count", 0)
        if retry_count < 2:
            state["retry_count"] = retry_count + 1
            logger.info("데이터 수집 재시도", retry_count=retry_count + 1)
            return "retry_collection"
        else:
            logger.error("데이터 수집 재시도 횟수 초과")
            return "failed"

    return "continue"


def should_generate_strategy(state: AuctionState) -> str:
    """위험등급에 따른 분기 결정"""

    risk_assessment = state.get("risk_assessment", {})
    risk_grade = risk_assessment.get("risk_grade", "B")

    logger.info(
        "위험등급 평가",
        case_number=state["case_number"],
        risk_grade=risk_grade
    )

    # 고위험 등급 경고
    if risk_grade in ["C", "D"]:
        warning_msg = f"⚠️ 위험등급 {risk_grade}: 고위험 물건입니다. 신중한 검토가 필요합니다."
        state["errors"].append(warning_msg)
        logger.warning(
            "고위험 물건",
            case_number=state["case_number"],
            risk_grade=risk_grade
        )

    # 모든 경우 입찰전략 생성 (경고만 추가)
    return "generate_strategy"


def should_red_team_review(state: AuctionState) -> str:
    """레드팀 검토 필요 여부 결정"""

    risk_assessment = state.get("risk_assessment", {})
    risk_grade = risk_assessment.get("risk_grade", "B")

    # 위험등급이 C 이상이면 레드팀 검토
    if risk_grade in ["C", "D"]:
        logger.info(
            "레드팀 검토 필요",
            case_number=state["case_number"],
            risk_grade=risk_grade
        )
        return "red_team_review"

    # 사용자 설정에서 레드팀 강제 활성화
    user_settings = state.get("user_settings", {})
    if user_settings.get("force_red_team_review", False):
        logger.info("사용자 요청으로 레드팀 검토 실행")
        return "red_team_review"

    # 그 외에는 스킵
    return "skip_red_team"


# ==================== 워크플로우 구성 ====================

def build_workflow() -> StateGraph:
    """워크플로우 그래프 구성"""

    logger.info("워크플로우 그래프 생성 중")

    # 그래프 생성
    workflow = StateGraph(AuctionState)

    # 노드 추가
    workflow.add_node("collect_data", collect_data)
    workflow.add_node("parallel_analysis", parallel_analysis)
    workflow.add_node("evaluate_value", evaluate_value)
    workflow.add_node("assess_risk", assess_risk)
    workflow.add_node("generate_strategy", generate_bid_strategy)
    workflow.add_node("red_team_review", red_team_review)
    workflow.add_node("generate_report", generate_report)

    # 시작점 설정
    workflow.set_entry_point("collect_data")

    # 엣지 연결
    # 1. 데이터 수집 -> 완전성 검사 -> 병렬분석 or 재시도 or 실패
    workflow.add_conditional_edges(
        "collect_data",
        check_data_completeness,
        {
            "continue": "parallel_analysis",
            "retry_collection": "collect_data",
            "failed": END
        }
    )

    # 2. 병렬분석 -> 가치평가
    workflow.add_edge("parallel_analysis", "evaluate_value")

    # 3. 가치평가 -> 위험평가
    workflow.add_edge("evaluate_value", "assess_risk")

    # 4. 위험평가 -> 입찰전략 (항상 실행)
    workflow.add_conditional_edges(
        "assess_risk",
        should_generate_strategy,
        {
            "generate_strategy": "generate_strategy"
        }
    )

    # 5. 입찰전략 -> 레드팀 검토 or 리포트 생성
    workflow.add_conditional_edges(
        "generate_strategy",
        should_red_team_review,
        {
            "red_team_review": "red_team_review",
            "skip_red_team": "generate_report"
        }
    )

    # 6. 레드팀 검토 -> 리포트 생성
    workflow.add_edge("red_team_review", "generate_report")

    # 7. 리포트 생성 -> 종료
    workflow.add_edge("generate_report", END)

    logger.info("워크플로우 그래프 생성 완료")

    return workflow


# ==================== 오케스트레이터 에이전트 ====================

class OrchestratorAgent:
    """오케스트레이터 에이전트 메인 클래스"""

    def __init__(self, db_path: str = "./workflow_state.db"):
        """
        초기화

        Args:
            db_path: SQLite 체크포인트 DB 경로
        """
        logger.info("OrchestratorAgent 초기화", db_path=db_path)

        # 체크포인트 저장소 생성 (메모리 기반)
        self.checkpointer = MemorySaver()

        # 워크플로우 컴파일
        self.workflow = build_workflow().compile(checkpointer=self.checkpointer)

        logger.info("OrchestratorAgent 초기화 완료")

    async def run_analysis(
        self,
        case_number: str,
        user_settings: dict = None
    ) -> dict:
        """
        전체 분석 워크플로우 실행

        Args:
            case_number: 사건번호
            user_settings: 사용자 설정

        Returns:
            최종 상태 dict
        """
        log = logger.bind(case_number=case_number)
        log.info("경매 분석 워크플로우 시작")

        # 초기 상태
        initial_state: AuctionState = {
            "case_number": case_number,
            "user_settings": user_settings or {},
            "collected_data": None,
            "rights_analysis": None,
            "location_analysis": None,
            "valuation": None,
            "risk_assessment": None,
            "bid_strategy": None,
            "red_team_review": None,
            "final_report": None,
            "current_step": "initialized",
            "errors": [],
            "status": "running",
            "retry_count": 0
        }

        # 워크플로우 실행 설정
        config = {"configurable": {"thread_id": case_number}}

        # 워크플로우 스트리밍 실행
        final_state = None
        try:
            async for event in self.workflow.astream(initial_state, config):
                # 진행 상황 로깅
                for node_name, state in event.items():
                    log.info(
                        "노드 실행 완료",
                        node=node_name,
                        current_step=state.get("current_step"),
                        status=state.get("status"),
                        error_count=len(state.get("errors", []))
                    )
                    final_state = state

            log.info(
                "워크플로우 완료",
                status=final_state.get("status"),
                total_errors=len(final_state.get("errors", []))
            )

            return final_state

        except Exception as e:
            log.error("워크플로우 실행 중 예외 발생", error=str(e), exc_info=True)
            raise

    async def get_status(self, case_number: str) -> dict:
        """
        분석 상태 조회

        Args:
            case_number: 사건번호

        Returns:
            상태 정보 dict
        """
        config = {"configurable": {"thread_id": case_number}}

        try:
            state = await self.workflow.aget_state(config)

            return {
                "case_number": case_number,
                "current_step": state.values.get("current_step"),
                "status": state.values.get("status"),
                "errors": state.values.get("errors", []),
                "next_node": state.next[0] if state.next else None
            }
        except Exception as e:
            logger.error("상태 조회 실패", case_number=case_number, error=str(e))
            raise

    async def resume(self, case_number: str) -> dict:
        """
        중단된 워크플로우 재개

        Args:
            case_number: 사건번호

        Returns:
            최종 상태 dict
        """
        log = logger.bind(case_number=case_number)
        log.info("워크플로우 재개")

        config = {"configurable": {"thread_id": case_number}}

        # 저장된 상태에서 재개
        final_state = None
        try:
            async for event in self.workflow.astream(None, config):
                for node_name, state in event.items():
                    log.info(
                        "노드 재개 완료",
                        node=node_name,
                        current_step=state.get("current_step")
                    )
                    final_state = state

            log.info("워크플로우 재개 완료", status=final_state.get("status"))

            return final_state

        except Exception as e:
            log.error("워크플로우 재개 중 예외 발생", error=str(e), exc_info=True)
            raise

    async def cancel(self, case_number: str) -> dict:
        """
        실행 중인 워크플로우 취소

        Args:
            case_number: 사건번호

        Returns:
            취소 결과 dict
        """
        log = logger.bind(case_number=case_number)
        log.info("워크플로우 취소 요청")

        # TODO: LangGraph에서 취소 기능 지원 시 구현
        # 현재는 상태만 업데이트

        return {
            "case_number": case_number,
            "status": "cancelled",
            "message": "워크플로우가 취소되었습니다."
        }

    def visualize(self, output_path: str = "workflow.png"):
        """
        워크플로우 그래프 시각화

        Args:
            output_path: 출력 이미지 경로
        """
        try:
            from langgraph.graph import draw_mermaid_png

            graph_image = draw_mermaid_png(self.workflow)

            with open(output_path, "wb") as f:
                f.write(graph_image)

            logger.info("워크플로우 시각화 완료", output_path=output_path)

        except ImportError:
            logger.warning("시각화 라이브러리 없음 (langgraph[draw] 필요)")
        except Exception as e:
            logger.error("시각화 실패", error=str(e))
