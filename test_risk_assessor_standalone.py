"""위험평가 에이전트 독립 테스트"""

import sys
from pathlib import Path

# Direct import without going through package __init__
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import models first
from models.risk import (
    CategoryRisk,
    RedFlag,
    RiskAssessmentResult,
    RiskGrade,
    RiskItem,
    RiskLevel,
)

# Import the classes directly from the module
import importlib.util

spec = importlib.util.spec_from_file_location(
    "risk_assessor",
    Path(__file__).parent / "src" / "agents" / "risk_assessor.py"
)
risk_assessor_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(risk_assessor_module)

RiskAssessorAgent = risk_assessor_module.RiskAssessorAgent


def test_risk_assessor():
    """기본 기능 테스트"""

    # 에이전트 생성
    agent = RiskAssessorAgent()

    # 테스트 데이터
    case_number = "2024타경12345"

    rights_analysis = {
        "total_assumed_amount": 50000000,
        "assumed_rights": [
            {"type": "근저당권", "amount": 30000000},
            {"type": "전세권", "amount": 20000000}
        ],
        "special_rights": [],
        "statutory_superficies": {
            "risk_level": "LOW",
            "note": "토지-건물 동일 소유자"
        },
        "lien": {
            "has_claim": False,
            "potential_risk": False
        },
        "tenant_analysis": [
            {
                "name": "김철수",
                "has_priority": True,
                "deposit": 50000000
            }
        ]
    }

    valuation = {
        "appraisal_value": 500000000,
        "estimated_market_price": 480000000,
        "trend_direction": "STABLE"
    }

    property_info = {
        "building_year": 2010,
        "is_special": False
    }

    status_report = {
        "defects": [],
        "occupancy_status": "tenant",
        "occupant_count": 1,
        "eviction_difficulty": "MEDIUM",
        "has_dispute": False
    }

    market_data = {
        "price_volatility": 0.05,
        "transaction_count_12m": 12
    }

    # 위험 평가 실행
    result = agent.assess(
        case_number=case_number,
        rights_analysis=rights_analysis,
        valuation=valuation,
        property_info=property_info,
        status_report=status_report,
        market_data=market_data
    )

    # 결과 출력
    print("=" * 70)
    print("위험평가 에이전트 테스트 결과")
    print("=" * 70)
    print(f"\n사건번호: {result.case_number}")
    print(f"종합 점수: {result.total_score}점")
    print(f"등급: {result.grade.value}")
    print(f"위험 수준: {result.level.value}")

    print(f"\n권리 리스크: {result.rights_risk.score:.1f}점 ({result.rights_risk.level.value})")
    print(f"  {result.rights_risk.summary}")

    print(f"\n시장 리스크: {result.market_risk.score:.1f}점 ({result.market_risk.level.value})")
    print(f"  {result.market_risk.summary}")

    print(f"\n물건 리스크: {result.property_risk.score:.1f}점 ({result.property_risk.level.value})")
    print(f"  {result.property_risk.summary}")

    print(f"\n명도 리스크: {result.eviction_risk.score:.1f}점 ({result.eviction_risk.level.value})")
    print(f"  {result.eviction_risk.summary}")

    print(f"\nRed Flags: {len(result.red_flags)}건")
    for flag in result.red_flags:
        print(f"  - [{flag.severity.value}] {flag.name}: {flag.description}")

    print(f"\n입문자 적합성: {'예' if result.beginner_friendly else '아니오'}")
    print(f"  {result.beginner_note}")

    print("\n권장사항:")
    for i, rec in enumerate(result.recommendations, 1):
        print(f"  {i}. {rec}")

    print("\n" + "=" * 70)
    print("상세 리포트")
    print("=" * 70)
    print(result.detailed_report)

    # 검증
    assert result.total_score >= 0 and result.total_score <= 100
    assert result.grade in [RiskGrade.A, RiskGrade.B, RiskGrade.C, RiskGrade.D]
    assert len(result.recommendations) > 0

    print("\n✓ 모든 테스트 통과!")


if __name__ == "__main__":
    test_risk_assessor()
