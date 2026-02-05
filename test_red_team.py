"""레드팀 에이전트 테스트"""
import asyncio
from datetime import datetime
from src.agents.red_team import RedTeamAgent
from src.models.validation import ValidationStatus


async def test_red_team_basic():
    """기본 검증 테스트"""

    # 샘플 에이전트 출력 데이터
    agent_outputs = {
        "rights_analyzer": {
            "case_number": "2024타경12345",
            "reference_right": {"type": "근저당권", "date": "2020-01-15"},
            "assumed_rights": [],
            "extinguished_rights": ["임차권"],
            "total_assumed_amount": 50000000,
            "risk_level": "LOW"
        },
        "valuator": {
            "appraisal_value": 300000000,
            "estimated_market_price": 280000000,
            "price_per_pyung": 8500000,
            "confidence": 0.85,
            "comparables_count": 12
        },
        "location_analyzer": {
            "total_score": 78.5,
            "transport_score": 82.0,
            "education_score": 75.0,
            "coordinates": {"lat": 37.5665, "lng": 126.9780},
            "area_average_price": 285000000
        },
        "risk_assessor": {
            "total_score": 82.0,
            "grade": "A",
            "beginner_friendly": True,
            "appraisal_value": 300000000  # 교차 검증용
        },
        "bid_strategist": {
            "optimal_bid": 210000000,
            "bid_rate": 0.70,
            "expected_profit": 50000000,
            "win_probability": 0.75,
            "total_assumed_amount": 50000000,  # 교차 검증용
            "strategy_type": "balanced"
        }
    }

    case_info = {
        "case_number": "2024타경12345",
        "property_type": "아파트",
        "location": "서울시 강남구",
        "area": 85.5
    }

    # 레드팀 에이전트 초기화 및 검증 실행
    red_team = RedTeamAgent()

    print("=" * 80)
    print("레드팀 에이전트 검증 테스트")
    print("=" * 80)

    report = await red_team.validate(
        case_id="2024타경12345",
        agent_outputs=agent_outputs,
        case_info=case_info,
        historical_cases=[]
    )

    # 결과 출력
    print(f"\n사건번호: {report.case_id}")
    print(f"검증 시간: {report.validation_time}")
    print(f"전체 상태: {report.overall_status.value}")
    print(f"신뢰도: {report.overall_reliability}점")
    print(f"승인 여부: {'승인' if report.approved else '거부'}")

    print(f"\n총 이슈 수: {report.total_issues_count}건")
    print(f"치명적 이슈: {report.critical_count}건")
    print(f"오류 이슈: {report.error_count}건")

    print("\n[에이전트별 검증 결과]")
    for agent_name, validation in report.agent_validations.items():
        print(f"  {agent_name}:")
        print(f"    - 상태: {validation.status.value}")
        print(f"    - 신뢰도: {validation.reliability_score}점")
        print(f"    - 요약: {validation.summary}")
        if validation.issues:
            print(f"    - 이슈:")
            for issue in validation.issues[:3]:
                print(f"      * [{issue.severity.value}] {issue.description}")

    print("\n[교차 검증 결과]")
    for cv in report.cross_validations:
        status = "✓" if cv.is_consistent else "✗"
        print(f"  {status} {cv.field_compared}: {cv.note}")

    print("\n[주요 이슈]")
    for issue in report.critical_issues[:5]:
        print(f"  [{issue.severity.value}] {issue.description}")
        if issue.suggested_fix:
            print(f"    → {issue.suggested_fix}")

    print("\n[권장 사항]")
    for i, rec in enumerate(report.recommendations, 1):
        print(f"  {i}. {rec}")

    if report.approval_conditions:
        print("\n[승인 조건]")
        for i, cond in enumerate(report.approval_conditions, 1):
            print(f"  {i}. {cond}")

    print("\n" + "=" * 80)
    print(f"테스트 결과: {'성공 ✓' if report.overall_reliability > 0 else '실패 ✗'}")
    print("=" * 80)

    return report


async def test_red_team_with_errors():
    """오류가 있는 데이터 검증 테스트"""

    # 의도적으로 오류를 포함한 데이터
    agent_outputs = {
        "rights_analyzer": {
            "case_number": "invalid_format",  # 형식 오류
            "reference_right": {"type": "근저당권"},  # date 누락
            "assumed_rights": [],
            "extinguished_rights": [],
            "total_assumed_amount": -10000,  # 음수 (범위 오류)
            "risk_level": "UNKNOWN"  # 허용되지 않는 값
        },
        "valuator": {
            "appraisal_value": 300000000,
            "estimated_market_price": 100000000,  # 감정가 대비 너무 낮음
            "price_per_pyung": 8500000,
            "confidence": 1.5,  # 범위 초과
            "comparables_count": 2  # 너무 적음
        },
        "bid_strategist": {
            "optimal_bid": 350000000,  # 감정가 초과
            "bid_rate": 1.17,
            "expected_profit": 0,
            "win_probability": 0.5
        }
    }

    red_team = RedTeamAgent()

    print("\n" + "=" * 80)
    print("오류 데이터 검증 테스트")
    print("=" * 80)

    report = await red_team.validate(
        case_id="2024타경99999",
        agent_outputs=agent_outputs,
        case_info={},
        historical_cases=[]
    )

    print(f"\n전체 상태: {report.overall_status.value}")
    print(f"신뢰도: {report.overall_reliability}점")
    print(f"승인 여부: {'승인' if report.approved else '거부'}")
    print(f"\n발견된 이슈 수: {report.total_issues_count}건")

    print("\n[주요 오류]")
    for issue in report.critical_issues[:10]:
        print(f"  [{issue.severity.value}] {issue.source_agent}.{issue.field_path}")
        print(f"    {issue.description}")

    print("\n" + "=" * 80)
    expected_fail = report.overall_status in [ValidationStatus.FAILED, ValidationStatus.NEEDS_REVIEW]
    print(f"테스트 결과: {'성공 ✓' if expected_fail else '실패 ✗'} (오류 감지 {'됨' if expected_fail else '안됨'})")
    print("=" * 80)

    return report


if __name__ == "__main__":
    print("\n레드팀 에이전트 통합 테스트\n")

    # 테스트 1: 정상 데이터
    asyncio.run(test_red_team_basic())

    # 테스트 2: 오류 데이터
    asyncio.run(test_red_team_with_errors())

    print("\n모든 테스트 완료!")
