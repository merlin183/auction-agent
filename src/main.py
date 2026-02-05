"""경매 AI 에이전트 시스템 메인 엔트리포인트"""
import asyncio
from typing import Optional

from agents.orchestrator import OrchestratorAgent
from utils.logger import get_logger

logger = get_logger(__name__)


async def analyze_auction(
    case_number: str,
    options: Optional[dict] = None,
) -> dict:
    """경매 물건 종합 분석

    Args:
        case_number: 사건번호 (예: "2024타경12345")
        options: 분석 옵션

    Returns:
        분석 결과 딕셔너리
    """
    options = options or {}

    logger.info("Starting auction analysis", case_number=case_number)

    # 오케스트레이터 초기화
    orchestrator = OrchestratorAgent()

    # 분석 실행
    result = await orchestrator.run(case_number)

    logger.info(
        "Auction analysis completed",
        case_number=case_number,
        status=result.get("status"),
        reliability=result.get("reliability"),
    )

    return result


async def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="경매 AI 에이전트 시스템")
    parser.add_argument("case_number", help="분석할 사건번호")
    parser.add_argument("--output", "-o", help="출력 파일 경로")
    parser.add_argument("--format", "-f", choices=["json", "md", "html"], default="json")

    args = parser.parse_args()

    result = await analyze_auction(args.case_number)

    if args.output:
        import json
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"결과가 {args.output}에 저장되었습니다.")
    else:
        import json
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
