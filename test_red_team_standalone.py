"""레드팀 에이전트 독립 테스트 (다른 에이전트 의존성 없음)"""
import sys
import asyncio
from datetime import datetime

# 직접 임포트
sys.path.insert(0, 'src')

from models.validation import (
    ValidationIssue,
    ValidationSeverity,
    ValidationStatus,
    AgentValidation,
    CrossValidationResult,
    RedTeamReport
)

from agents.red_team import (
    DataIntegrityValidator,
    CrossValidator,
    StatisticalAnomalyDetector,
    ReliabilityCalculator
)


def test_data_integrity_validator():
    """데이터 무결성 검증 테스트"""
    print("\n" + "=" * 80)
    print("1. 데이터 무결성 검증 테스트")
    print("=" * 80)

    validator = DataIntegrityValidator()

    # 정상 데이터
    valid_output = {
        "case_number": "2024타경12345",
        "reference_right": {"type": "근저당권", "date": "2020-01-15"},
        "assumed_rights": [],
        "extinguished_rights": ["임차권"],
        "total_assumed_amount": 50000000,
        "risk_level": "LOW"
    }

    issues = validator.validate("rights_analyzer", valid_output)
    print(f"\n정상 데이터 검증: {len(issues)}건 이슈")
    for issue in issues:
        print(f"  - [{issue.severity.value}] {issue.description}")

    # 오류 데이터
    invalid_output = {
        "case_number": "invalid",  # 패턴 불일치
        "reference_right": {"type": "근저당권"},  # date 누락
        "assumed_rights": [],
        "extinguished_rights": [],
        "total_assumed_amount": -10000,  # 음수
        "risk_level": "UNKNOWN"  # 허용되지 않는 값
    }

    issues = validator.validate("rights_analyzer", invalid_output)
    print(f"\n오류 데이터 검증: {len(issues)}건 이슈")
    for issue in issues:
        print(f"  - [{issue.severity.value}] {issue.description}")

    print(f"\n테스트 결과: {'성공 ✓' if len(issues) > 0 else '실패 ✗'}")


def test_cross_validator():
    """교차 검증 테스트"""
    print("\n" + "=" * 80)
    print("2. 교차 검증 테스트")
    print("=" * 80)

    validator = CrossValidator()

    # 일치하는 데이터
    consistent_outputs = {
        "valuator": {"appraisal_value": 300000000},
        "rights_analyzer": {"appraisal_value": 300000000},
        "risk_assessor": {"appraisal_value": 300000000}
    }

    results = validator.validate(consistent_outputs)
    print(f"\n일치하는 데이터: {len(results)}건 교차 검증")
    for result in results:
        status = "✓" if result.is_consistent else "✗"
        print(f"  {status} {result.field_compared}: {result.note}")

    # 불일치하는 데이터
    inconsistent_outputs = {
        "valuator": {
            "appraisal_value": 300000000,
            "estimated_market_price": 280000000
        },
        "rights_analyzer": {"appraisal_value": 350000000},  # 불일치
        "risk_assessor": {"appraisal_value": 300000000},
        "bid_strategist": {
            "optimal_bid": 450000000,  # 감정가 초과
            "total_assumed_amount": 50000000
        }
    }

    results = validator.validate(inconsistent_outputs)
    print(f"\n불일치하는 데이터: {len(results)}건 교차 검증")
    for result in results:
        status = "✓" if result.is_consistent else "✗"
        print(f"  {status} {result.field_compared}: {result.note}")
        if not result.is_consistent:
            print(f"      값: {result.values}")

    inconsistent_count = sum(1 for r in results if not r.is_consistent)
    print(f"\n테스트 결과: {'성공 ✓' if inconsistent_count > 0 else '실패 ✗'}")


def test_statistical_anomaly_detector():
    """통계적 이상 탐지 테스트"""
    print("\n" + "=" * 80)
    print("3. 통계적 이상 탐지 테스트")
    print("=" * 80)

    detector = StatisticalAnomalyDetector()

    # 정상 범위 데이터
    normal_outputs = {
        "valuator": {
            "appraisal_value": 300000000,
            "estimated_market_price": 280000000,
            "price_per_pyung": 8500000
        },
        "bid_strategist": {
            "optimal_bid": 210000000,
            "expected_profit": 50000000
        }
    }

    issues = detector.detect(normal_outputs, [])
    print(f"\n정상 범위 데이터: {len(issues)}건 이슈")

    # 극단값 데이터
    extreme_outputs = {
        "valuator": {
            "appraisal_value": 300000000,
            "estimated_market_price": 100000000,  # 감정가의 33% (극단적으로 낮음)
            "price_per_pyung": 8500000
        },
        "bid_strategist": {
            "optimal_bid": 350000000,  # 감정가 초과
            "expected_profit": 50000000
        }
    }

    issues = detector.detect(extreme_outputs, [])
    print(f"\n극단값 데이터: {len(issues)}건 이슈")
    for issue in issues:
        print(f"  - [{issue.severity.value}] {issue.description}")
        if issue.expected_value:
            print(f"      기대값: {issue.expected_value}, 실제값: {issue.actual_value}")

    print(f"\n테스트 결과: {'성공 ✓' if len(issues) > 0 else '실패 ✗'}")


def test_reliability_calculator():
    """신뢰도 산출 테스트"""
    print("\n" + "=" * 80)
    print("4. 신뢰도 산출 테스트")
    print("=" * 80)

    calculator = ReliabilityCalculator()

    # 문제 없는 경우
    perfect_validations = {
        "rights_analyzer": AgentValidation(
            agent_name="rights_analyzer",
            validation_time=datetime.now(),
            issues=[],
            status=ValidationStatus.PASSED,
            reliability_score=100
        ),
        "valuator": AgentValidation(
            agent_name="valuator",
            validation_time=datetime.now(),
            issues=[],
            status=ValidationStatus.PASSED,
            reliability_score=100
        )
    }

    reliability, status = calculator.calculate(
        perfect_validations, [], [], []
    )
    print(f"\n완벽한 데이터:")
    print(f"  신뢰도: {reliability:.1f}점")
    print(f"  상태: {status.value}")

    # 경고가 있는 경우
    warning_validations = {
        "rights_analyzer": AgentValidation(
            agent_name="rights_analyzer",
            validation_time=datetime.now(),
            issues=[
                ValidationIssue(
                    id="test1",
                    severity=ValidationSeverity.WARNING,
                    category="test",
                    source_agent="rights_analyzer",
                    field_path="test",
                    issue_type="test",
                    description="테스트 경고",
                    confidence=1.0
                )
            ],
            status=ValidationStatus.PASSED_WITH_WARNINGS,
            reliability_score=90
        ),
        "valuator": AgentValidation(
            agent_name="valuator",
            validation_time=datetime.now(),
            issues=[],
            status=ValidationStatus.PASSED,
            reliability_score=100
        )
    }

    reliability, status = calculator.calculate(
        warning_validations, [], [], []
    )
    print(f"\n경고 있는 데이터:")
    print(f"  신뢰도: {reliability:.1f}점")
    print(f"  상태: {status.value}")

    # 오류가 많은 경우
    error_validations = {
        "rights_analyzer": AgentValidation(
            agent_name="rights_analyzer",
            validation_time=datetime.now(),
            issues=[
                ValidationIssue(
                    id=f"error{i}",
                    severity=ValidationSeverity.ERROR,
                    category="test",
                    source_agent="rights_analyzer",
                    field_path="test",
                    issue_type="test",
                    description=f"테스트 오류 {i}",
                    confidence=1.0
                ) for i in range(5)
            ],
            status=ValidationStatus.NEEDS_REVIEW,
            reliability_score=50
        )
    }

    reliability, status = calculator.calculate(
        error_validations, [], [], []
    )
    print(f"\n오류 많은 데이터:")
    print(f"  신뢰도: {reliability:.1f}점")
    print(f"  상태: {status.value}")

    print(f"\n테스트 결과: {'성공 ✓' if reliability < 80 else '실패 ✗'}")


def test_integration():
    """통합 테스트"""
    print("\n" + "=" * 80)
    print("5. 통합 테스트")
    print("=" * 80)

    # 모든 검증기 초기화
    integrity = DataIntegrityValidator()
    cross = CrossValidator()
    anomaly = StatisticalAnomalyDetector()
    calculator = ReliabilityCalculator()

    # 샘플 데이터
    agent_outputs = {
        "rights_analyzer": {
            "case_number": "2024타경12345",
            "reference_right": {"type": "근저당권", "date": "2020-01-15"},
            "assumed_rights": [],
            "extinguished_rights": [],
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
        "bid_strategist": {
            "optimal_bid": 210000000,
            "bid_rate": 0.70,
            "expected_profit": 50000000,
            "win_probability": 0.75,
            "total_assumed_amount": 50000000
        }
    }

    # 1. 무결성 검증
    print("\n[1단계] 데이터 무결성 검증")
    agent_validations = {}
    for agent_name, output in agent_outputs.items():
        issues = integrity.validate(agent_name, output)
        print(f"  {agent_name}: {len(issues)}건 이슈")
        agent_validations[agent_name] = AgentValidation(
            agent_name=agent_name,
            validation_time=datetime.now(),
            issues=issues,
            status=ValidationStatus.PASSED if not issues else ValidationStatus.PASSED_WITH_WARNINGS,
            reliability_score=100 - len(issues) * 10
        )

    # 2. 교차 검증
    print("\n[2단계] 교차 검증")
    cross_results = cross.validate(agent_outputs)
    for result in cross_results:
        status = "✓" if result.is_consistent else "✗"
        print(f"  {status} {result.field_compared}: {result.note}")

    # 3. 통계 이상 탐지
    print("\n[3단계] 통계적 이상 탐지")
    stat_issues = anomaly.detect(agent_outputs, [])
    print(f"  발견된 이상: {len(stat_issues)}건")

    # 4. 신뢰도 산출
    print("\n[4단계] 종합 신뢰도 산출")
    reliability, status = calculator.calculate(
        agent_validations, cross_results, stat_issues, []
    )
    print(f"  최종 신뢰도: {reliability:.1f}점")
    print(f"  최종 상태: {status.value}")
    print(f"  승인 여부: {'승인' if status in [ValidationStatus.PASSED, ValidationStatus.PASSED_WITH_WARNINGS] else '거부'}")

    print(f"\n테스트 결과: {'성공 ✓' if reliability >= 60 else '실패 ✗'}")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("레드팀 에이전트 모듈별 테스트")
    print("=" * 80)

    try:
        # 개별 모듈 테스트
        test_data_integrity_validator()
        test_cross_validator()
        test_statistical_anomaly_detector()
        test_reliability_calculator()

        # 통합 테스트
        test_integration()

        print("\n" + "=" * 80)
        print("모든 테스트 완료 ✓")
        print("=" * 80)

    except Exception as e:
        print(f"\n테스트 실패: {e}")
        import traceback
        traceback.print_exc()
