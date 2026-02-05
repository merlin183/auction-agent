"""권리분석 에이전트 간단 테스트 (의존성 최소화)"""
import sys
from datetime import date

# 직접 import하여 순환 참조 방지
sys.path.insert(0, 'src')

from models.rights import RegistryEntry, RightType, TenantInfo
from agents.rights_analyzer import ExtinctionBaseRightDetector, RightClassifier, TenantAnalyzer, RiskScorer


def test_extinction_base_detection():
    """말소기준권리 탐지 테스트"""
    print("=" * 80)
    print("테스트 1: 말소기준권리 탐지")
    print("=" * 80)

    entries = [
        RegistryEntry(
            entry_number="1",
            registration_date=date(2020, 1, 15),
            right_type=RightType.OWNERSHIP,
            right_holder="홍길동",
        ),
        RegistryEntry(
            entry_number="1",
            registration_date=date(2022, 3, 15),
            right_type=RightType.MORTGAGE,
            right_holder="OO은행",
            amount=300_000_000,
        ),
        RegistryEntry(
            entry_number="2",
            registration_date=date(2023, 1, 10),
            right_type=RightType.PROVISIONAL_SEIZURE,
            right_holder="이영희",
        ),
    ]

    detector = ExtinctionBaseRightDetector()
    result = detector.find_extinction_base(entries)

    if result:
        print(f"\n✓ 말소기준권리 탐지 성공!")
        print(f"  유형: {result.right_type.value}")
        print(f"  등기일: {result.registration_date}")
        print(f"  권리자: {result.right_holder}")
    else:
        print("\n✗ 말소기준권리를 찾을 수 없습니다.")

    return result


def test_right_classification(extinction_base):
    """권리 분류 테스트"""
    print("\n" + "=" * 80)
    print("테스트 2: 권리 인수/소멸 분류")
    print("=" * 80)

    entries = [
        # 선순위 전세권 (인수)
        RegistryEntry(
            entry_number="1",
            registration_date=date(2021, 6, 20),
            right_type=RightType.LEASE,
            right_holder="김철수",
            amount=150_000_000,
        ),
        # 근저당권 (말소기준권리, 소멸)
        extinction_base,
        # 후순위 가압류 (소멸)
        RegistryEntry(
            entry_number="2",
            registration_date=date(2023, 1, 10),
            right_type=RightType.PROVISIONAL_SEIZURE,
            right_holder="이영희",
        ),
    ]

    classifier = RightClassifier()
    assumed, extinguished = classifier.classify(entries, extinction_base)

    print(f"\n✓ 권리 분류 완료!")
    print(f"\n인수권리: {len(assumed)}건")
    for r in assumed:
        amount_str = f" - {r.amount:,}원" if r.amount else ""
        print(f"  - {r.right_type.value}{amount_str}")

    print(f"\n소멸권리: {len(extinguished)}건")
    for r in extinguished:
        amount_str = f" - {r.amount:,}원" if r.amount else ""
        print(f"  - {r.right_type.value}{amount_str}")

    return assumed, extinguished


def test_tenant_analysis(extinction_base):
    """임차인 분석 테스트"""
    print("\n" + "=" * 80)
    print("테스트 3: 임차인 대항력 분석")
    print("=" * 80)

    tenants = [
        TenantInfo(
            name="박민수",
            move_in_date=date(2021, 5, 1),  # 근저당권보다 이전 (대항력 있음)
            fixed_date=date(2021, 5, 2),
            deposit=50_000_000,
            occupying=True,
        ),
        TenantInfo(
            name="최유진",
            move_in_date=date(2023, 8, 1),  # 근저당권보다 이후 (대항력 없음)
            fixed_date=date(2023, 8, 5),
            deposit=30_000_000,
            occupying=True,
        ),
    ]

    analyzer = TenantAnalyzer()
    results = analyzer.analyze(tenants, extinction_base, "서울")

    print(f"\n✓ 임차인 분석 완료!")
    for tenant in results:
        print(f"\n{tenant.name}")
        print(f"  - 전입일: {tenant.move_in_date}")
        print(f"  - 보증금: {tenant.deposit:,}원" if tenant.deposit else "  - 보증금: 미상")
        print(f"  - 대항력: {'있음 ✓' if tenant.has_priority else '없음 ✗'}")
        if tenant.priority_amount:
            print(f"  - 최우선변제금: {tenant.priority_amount:,}원")
        if tenant.assumed_deposit:
            print(f"  - 인수금액: {tenant.assumed_deposit:,}원")

    return results


def test_risk_scoring(assumed_rights, tenants):
    """위험도 점수 산정 테스트"""
    print("\n" + "=" * 80)
    print("테스트 4: 위험도 점수 산정")
    print("=" * 80)

    scorer = RiskScorer()
    score, risk_level = scorer.calculate_score(
        assumed_rights=assumed_rights,
        tenants=tenants,
        special_rights=[],
        appraisal_value=400_000_000,
    )

    print(f"\n✓ 위험도 평가 완료!")
    print(f"  - 위험점수: {score}점")
    print(f"  - 위험등급: {risk_level.value}")

    if risk_level.value == "LOW":
        grade_icon = "🟢"
    elif risk_level.value == "MEDIUM":
        grade_icon = "🟡"
    elif risk_level.value == "HIGH":
        grade_icon = "🟠"
    else:
        grade_icon = "🔴"

    print(f"  - 등급표시: {grade_icon} {risk_level.value}")


def main():
    """메인 테스트 실행"""
    print("\n권리분석 에이전트 핵심 기능 테스트\n")

    # 1. 말소기준권리 탐지
    extinction_base = test_extinction_base_detection()

    if not extinction_base:
        print("\n테스트 실패: 말소기준권리 탐지 불가")
        return

    # 2. 권리 분류
    assumed_rights, extinguished_rights = test_right_classification(extinction_base)

    # 3. 임차인 분석
    tenants = test_tenant_analysis(extinction_base)

    # 4. 위험도 점수 산정
    test_risk_scoring(assumed_rights, tenants)

    print("\n" + "=" * 80)
    print("✓ 모든 테스트 완료!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
