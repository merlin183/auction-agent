"""FastAPI 기반 REST API"""
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.agents.orchestrator import OrchestratorAgent
from src.services.cache import get_cache_service
from src.utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 생명주기 관리"""
    # 시작 시
    cache = await get_cache_service()
    logger.info("Application started")
    yield
    # 종료 시
    await cache.disconnect()
    logger.info("Application shutdown")


app = FastAPI(
    title="경매 AI 에이전트 API",
    description="부동산 경매 분석 AI 시스템",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalysisRequest(BaseModel):
    """분석 요청"""
    case_number: str
    options: Optional[dict] = None


class AnalysisResponse(BaseModel):
    """분석 응답"""
    status: str
    case_number: str
    reliability: Optional[float] = None
    report: Optional[dict] = None
    red_team_report: Optional[dict] = None
    message: Optional[str] = None


# 진행 중인 분석 저장
_running_analyses: dict[str, dict] = {}


@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {"status": "healthy"}


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_auction(request: AnalysisRequest):
    """경매 물건 분석"""
    try:
        orchestrator = OrchestratorAgent()
        result = await orchestrator.run(request.case_number)

        return AnalysisResponse(
            status=result.get("status", "SUCCESS"),
            case_number=request.case_number,
            reliability=result.get("reliability"),
            report=result.get("report"),
            red_team_report=result.get("red_team_report"),
        )
    except Exception as e:
        logger.error("Analysis failed", case_number=request.case_number, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze/async")
async def analyze_auction_async(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks,
):
    """비동기 경매 물건 분석"""
    import uuid
    analysis_id = str(uuid.uuid4())

    _running_analyses[analysis_id] = {
        "status": "running",
        "case_number": request.case_number,
    }

    async def run_analysis():
        try:
            orchestrator = OrchestratorAgent()
            result = await orchestrator.run(request.case_number)
            _running_analyses[analysis_id] = {
                "status": "completed",
                "case_number": request.case_number,
                "result": result,
            }
        except Exception as e:
            _running_analyses[analysis_id] = {
                "status": "failed",
                "case_number": request.case_number,
                "error": str(e),
            }

    background_tasks.add_task(run_analysis)

    return {
        "analysis_id": analysis_id,
        "status": "accepted",
        "message": "분석이 시작되었습니다.",
    }


@app.get("/analyze/{analysis_id}")
async def get_analysis_status(analysis_id: str):
    """분석 상태 조회"""
    if analysis_id not in _running_analyses:
        raise HTTPException(status_code=404, detail="분석을 찾을 수 없습니다.")

    return _running_analyses[analysis_id]


@app.get("/cases/{case_number}")
async def get_cached_analysis(case_number: str):
    """캐시된 분석 결과 조회"""
    cache = await get_cache_service()
    result = await cache.get_auction_data(case_number)

    if not result:
        raise HTTPException(status_code=404, detail="캐시된 분석 결과가 없습니다.")

    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
