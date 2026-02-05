"""권리분석 에이전트 테스트"""
from datetime import date
from src.models.rights import RegistryEntry, RightType, TenantInfo
from src.agents.rights_analyzer import RightsAnalyzerAgent


def test_simple_case():
    """간단한 케이스 테스트"""
    print("=" * 80)
    print("테스트 1: 간단한 권리관계 (인수사항 없음)")
    print("=" * 80)

    # 갑구: 소유권만
    gap_gu = [
        RegistryEntry(
            entry_number="1",
            registration_date=date(2020, 1, 15),
            right_type=RightType.OWNERSHIP,
            right_holder="홍길동",
        )
    ]

    # 을구: 근저당권 1건
    eul_gu = [
        RegistryEntry(
            entry_number="1",
            registration_date=date(2022, 3, 15),
            right_type=RightType.MORTGAGE,
            right_holder="OO은행",
            amount=300_000_000,
            purpose="근저당권설정",
        )
    ]

    # 분석 수행
    agent = RightsAnalyzerAgent()
    result = agent.analyze(
        case_number="2024타경12345",
        gap_gu_entries=gap_gu,
        eul_gu_entries=eul_gu,
        appraisal_value=500_000_000,
    )

    # 결과 출력
    print(f"\n사건번호: {result.case_number}")
    print(f"말소기준권리: {result.reference_right.right_type.value}")
    print(f"  - 등기일: {result.reference_right.registration_date}")
    print(f"  - 권리자: {result.reference_right.right_holder}")
    print(f"\n인수권리: {len(result.assumed_rights)}건")
    for r in result.assumed_rights:
        print(f"  - {r.right_type.value}: {r.amount:,}원" if r.amount else f"  - {r.right_type.value}")
    print(f"\n소멸권리: {len(result.extinguished_rights)}건")
    for r in result.extinguished_rights:
        print(f"  - {r.right_type.value}: {r.amount:,}원" if r.amount else f"  - {r.right_type.value}")
    print(f"\n위험등급: {result.risk_level.value}")
    print(f"위험점수: {result.risk_score}점")
    print(f"\n요약: {result.summary}")
    print(f"\n입문자 적합: {'예' if result.beginner_suitable else '아니오'}")


def test_complex_case():
    """복잡한 케이스 테스트 (선순위 전세권 포함)"""
    print("\n" + "=" * 80)
    print("테스트 2: 복잡한 권리관계 (선순위 전세권 + 임차인)")
    print("=" * 80)

    gap_gu = [
        RegistryEntry(
            entry_number="1",
            registration_date=date(2020, 1, 15),
            right_type=RightType.OWNERSHIP,
            right_holder="홍길동",
        )
    ]

    eul_gu = [
        # 선순위 전세권
        RegistryEntry(
            entry_number="1",
            registration_date=date(2021, 6, 20),
            right_type=RightType.LEASE,
            right_holder="김철수",
            amount=150_000_000,
            purpose="전세권설정",
        ),
        # 후순위 근저당권 (말소기준권리)
        RegistryEntry(
            entry_number="2",
            registration_date=date(2022, 3, 15),
            right_type=RightType.MORTGAGE,
            right_holder="OO은행",
            amount=200_000_000,
            purpose="근저당권설정",
        ),
        # 후순위 가압류
        RegistryEntry(
            entry_number="3",
            registration_date=date(2023, 1, 10),
            right_type=RightType.PROVISIONAL_SEIZURE,
            right_holder="이영희",
            amount=50_000_000,
            purpose="가압류",
        ),
    ]

    # 임차인 정보
    tenants = [
        TenantInfo(
            name="박민수",
            move_in_date=date(2021, 5, 1),  # 근저당권보다 이전
            fixed_date=date(2021, 5, 2),
            deposit=50_000_000,
            occupying=True,
        ),
        TenantInfo(
            name="최유진",
            move_in_date=date(2023, 8, 1),  # 근저당권보다 이후
            fixed_date=date(2023, 8, 5),
            deposit=30_000_000,
            occupying=True,
        ),
    ]

    # 분석 수행
    agent = RightsAnalyzerAgent()
    result = agent.analyze(
        case_number="2024타경23456",
        gap_gu_entries=gap_gu,
        eul_gu_entries=eul_gu,
        tenants=tenants,
        property_region="서울",
        appraisal_value=400_000_000,
    )

    # 결과 출력
    print(f"\n사건번호: {result.case_number}")
    print(f"말소기준권리: {result.reference_right.right_type.value}")
    print(f"  - 등기일: {result.reference_right.registration_date}")
    print(f"  - 권리자: {result.reference_right.right_holder}")

    print(f"\n인수권리: {len(result.assumed_rights)}건")
    total_assumed = 0
    for r in result.assumed_rights:
        if r.amount:
            print(f"  - {r.right_type.value}: {r.amount:,}원")
            total_assumed += r.amount
        else:
            print(f"  - {r.right_type.value}")
    print(f"  총 인수금액: {total_assumed:,}원")

    print(f"\n소멸권리: {len(result.extinguished_rights)}건")
    for r in result.extinguished_rights:
        if r.amount:
            print(f"  - {r.right_type.value}: {r.amount:,}원")
        else:
            print(f"  - {r.right_type.value}")

    print(f"\n임차인: {len(result.tenants)}명")
    for t in result.tenants:
        print(f"  - {t.name}")
        print(f"    대항력: {'있음' if t.has_priority else '없음'}")
        if t.deposit:
            print(f"    보증금: {t.deposit:,}원")
        if t.assumed_deposit:
            print(f"    인수금액: {t.assumed_deposit:,}원")
        if t.priority_amount:
            print(f"    최우선변제금: {t.priority_amount:,}원")

    print(f"\n총 인수 보증금: {result.total_assumed_deposit:,}원")
    print(f"\n위험등급: {result.risk_level.value}")
    print(f"위험점수: {result.risk_score}점")

    print(f"\n경고사항:")
    for warning in result.warnings:
        print(f"  - {warning}")

    print(f"\n권장사항:")
    for rec in result.recommendations:
        print(f"  - {rec}")

    print(f"\n요약: {result.summary}")
    print(f"\n입문자 적합: {'예' if result.beginner_suitable else '아니오'}")
    print(f"입문자 메모: {result.beginner_note}")


if __name__ == "__main__":
    test_simple_case()
    test_complex_case()
    print("\n" + "=" * 80)
    print("모든 테스트 완료!")
    print("=" * 80)
