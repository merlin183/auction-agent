"""권리분석 에이전트

등기부등본을 분석하여 낙찰자가 인수해야 할 권리와 소멸되는 권리를 자동 판별하고,
위험도를 평가하는 전문 에이전트
"""
from datetime import date
from typing import Optional

from ..models.rights import (
    RegistryEntry,
    RightType,
    RightStatus,
    RiskLevel,
    ReferenceRight,
    RightsAnalysisResult,
    TenantInfo,
    SpecialRight,
)
from ..services.llm import get_llm_client
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ExtinctionBaseRightDetector:
    """말소기준권리 탐지기"""

    # 말소기준권리가 될 수 있는 권리 유형
    EXTINCTION_BASE_TYPES = {
        RightType.MORTGAGE,
        RightType.SEIZURE,
        RightType.PROVISIONAL_SEIZURE,
        RightType.AUCTION_REGISTRATION,
    }

    def find_extinction_base(
        self, entries: list[RegistryEntry], auction_start_date: Optional[date] = None
    ) -> Optional[RegistryEntry]:
        """말소기준권리 찾기

        규칙:
        1. 말소기준권리 유형에 해당하는 권리 중
        2. 가장 먼저 등기된 권리

        Args:
            entries: 등기 항목 리스트
            auction_start_date: 경매 개시일자 (선택)

        Returns:
            말소기준권리 (없으면 None)
        """
        candidates = []

        for entry in entries:
            # 말소기준권리 유형인지 확인
            if entry.right_type in self.EXTINCTION_BASE_TYPES:
                candidates.append(entry)

            # 담보가등기 특별 처리
            if self._is_collateral_provisional(entry):
                candidates.append(entry)

        if not candidates:
            logger.warning("말소기준권리를 찾을 수 없습니다.")
            return None

        # 접수일자가 가장 빠른 권리 선택
        candidates.sort(key=lambda e: (e.registration_date, e.entry_number))
        extinction_base = candidates[0]

        logger.info(
            f"말소기준권리 탐지: {extinction_base.right_type.value} "
            f"({extinction_base.registration_date})"
        )

        return extinction_base

    def _is_collateral_provisional(self, entry: RegistryEntry) -> bool:
        """담보가등기 여부 판단"""
        if entry.right_type != RightType.PROVISIONAL_REGISTRATION:
            return False

        # 담보 목적의 가등기인지 확인
        if not entry.purpose:
            return False

        collateral_keywords = ["담보", "대물변제", "채권담보"]
        return any(kw in entry.purpose for kw in collateral_keywords)


class RightClassifier:
    """권리 인수/소멸 분류기"""

    def classify(
        self, entries: list[RegistryEntry], extinction_base: RegistryEntry
    ) -> tuple[list[RegistryEntry], list[RegistryEntry]]:
        """말소기준권리를 기준으로 인수/소멸 권리 분류

        기본 규칙:
        - 말소기준권리 이전 등기 → 인수 (낙찰자가 떠안음)
        - 말소기준권리 이후 등기 → 소멸 (낙찰로 사라짐)

        Args:
            entries: 등기 항목 리스트
            extinction_base: 말소기준권리

        Returns:
            (인수할 권리 리스트, 소멸할 권리 리스트)
        """
        assumed_rights = []  # 인수할 권리
        extinguished_rights = []  # 소멸할 권리

        base_date = extinction_base.registration_date

        for entry in entries:
            # 소유권은 분류하지 않음
            if entry.right_type == RightType.OWNERSHIP:
                continue

            # 말소기준권리 자체는 소멸
            if entry.entry_number == extinction_base.entry_number:
                entry.status = RightStatus.EXTINGUISHED
                extinguished_rights.append(entry)
                continue

            # 시간순 비교
            is_before_base = entry.registration_date < base_date or (
                entry.registration_date == base_date
                and entry.entry_number < extinction_base.entry_number
            )

            # 기본 분류
            if is_before_base:
                entry.status = RightStatus.ASSUMED
                assumed_rights.append(entry)
                logger.debug(
                    f"인수권리: {entry.right_type.value} "
                    f"({entry.registration_date})"
                )
            else:
                entry.status = RightStatus.EXTINGUISHED
                extinguished_rights.append(entry)
                logger.debug(
                    f"소멸권리: {entry.right_type.value} "
                    f"({entry.registration_date})"
                )

        return assumed_rights, extinguished_rights


class TenantAnalyzer:
    """임차인 분석기"""

    # 소액임차인 최우선변제금 (2024년 기준)
    SMALL_TENANT_LIMITS = {
        "서울": {"deposit_limit": 165_000_000, "priority_amount": 55_000_000},
        "과밀억제권역": {"deposit_limit": 145_000_000, "priority_amount": 48_000_000},
        "광역시": {"deposit_limit": 85_000_000, "priority_amount": 28_000_000},
        "기타": {"deposit_limit": 75_000_000, "priority_amount": 25_000_000},
    }

    def analyze(
        self,
        tenants: list[TenantInfo],
        extinction_base: RegistryEntry,
        property_region: str = "기타",
    ) -> list[TenantInfo]:
        """임차인별 대항력 및 인수금액 분석

        Args:
            tenants: 임차인 정보 리스트
            extinction_base: 말소기준권리
            property_region: 부동산 소재 지역

        Returns:
            분석 결과가 추가된 임차인 리스트
        """
        analyzed_tenants = []

        for tenant in tenants:
            analyzed = self._analyze_single_tenant(
                tenant, extinction_base, property_region
            )
            analyzed_tenants.append(analyzed)

        return analyzed_tenants

    def _analyze_single_tenant(
        self, tenant: TenantInfo, extinction_base: RegistryEntry, region: str
    ) -> TenantInfo:
        """개별 임차인 분석"""
        notes = []

        # 1. 대항력 판단 (전입일 vs 말소기준권리일)
        if tenant.move_in_date:
            has_priority = (
                tenant.move_in_date < extinction_base.registration_date
            )
            tenant.has_priority = has_priority

            if has_priority:
                notes.append(
                    f"전입일({tenant.move_in_date})이 "
                    f"말소기준권리일({extinction_base.registration_date}) 이전으로 대항력 있음"
                )
            else:
                notes.append("대항력 없음 - 낙찰로 임차권 소멸")
        else:
            tenant.has_priority = False
            notes.append("전입일 정보 없음")

        # 2. 소액임차인 여부 판단
        if tenant.deposit:
            limits = self.SMALL_TENANT_LIMITS.get(
                region, self.SMALL_TENANT_LIMITS["기타"]
            )
            is_small_tenant = tenant.deposit <= limits["deposit_limit"]

            if is_small_tenant:
                tenant.priority_amount = limits["priority_amount"]
                notes.append(
                    f"소액임차인 해당 - 최우선변제금 {tenant.priority_amount:,}원"
                )
            else:
                tenant.priority_amount = 0

        # 3. 인수금액 계산
        if tenant.has_priority and tenant.deposit:
            # 대항력이 있으면 보증금 전액 인수 (배당요구 여부는 별도 고려)
            tenant.assumed_deposit = tenant.deposit
            notes.append(f"인수 예상 보증금: {tenant.assumed_deposit:,}원")
        else:
            tenant.assumed_deposit = 0

        tenant.note = " | ".join(notes)

        logger.debug(f"임차인 분석: {tenant.name or '미상'} - {tenant.note}")

        return tenant


class StatutorySuperficiesDetector:
    """법정지상권 탐지기"""

    def analyze(
        self,
        land_entries: list[RegistryEntry],
        building_entries: list[RegistryEntry],
    ) -> Optional[SpecialRight]:
        """법정지상권 성립 요건 분석

        성립 요건:
        1. 토지와 건물이 동일인 소유였을 것
        2. 저당권 설정 당시 건물이 존재했을 것
        3. 경매로 인해 토지와 건물의 소유자가 달라질 것

        Args:
            land_entries: 토지 등기 항목
            building_entries: 건물 등기 항목

        Returns:
            법정지상권 특수권리 (위험 없으면 None)
        """
        # 토지와 건물의 저당권 확인
        land_mortgages = [
            e
            for e in land_entries
            if e.right_type
            in [RightType.MORTGAGE, RightType.PROVISIONAL_REGISTRATION]
        ]
        building_exists = len(building_entries) > 0

        if not land_mortgages or not building_exists:
            return None

        # 간단한 위험도 평가 (실제로는 더 복잡한 분석 필요)
        risk_level = RiskLevel.MEDIUM

        logger.info("법정지상권 성립 가능성 감지")

        return SpecialRight(
            right_type="법정지상권",
            risk_level=risk_level,
            description="토지와 건물이 별도 경매될 경우 법정지상권 성립 가능",
            estimated_amount=None,
            mitigation="토지와 건물을 함께 낙찰받거나 전문가 상담 필요",
        )


class LienDetector:
    """유치권 탐지기"""

    def analyze(self, status_report: Optional[dict] = None) -> Optional[SpecialRight]:
        """유치권 관련 위험 분석

        유치권은 등기되지 않으므로 현황조사서와 매각물건명세서에서 확인 필요

        Args:
            status_report: 현황조사서 데이터

        Returns:
            유치권 특수권리 (위험 없으면 None)
        """
        if not status_report:
            return None

        # 유치권 신고 여부 확인
        occupancy_status = status_report.get("occupancy_status", "")
        keywords = ["유치권", "공사대금", "공사업자"]

        has_lien_claim = any(kw in occupancy_status for kw in keywords)

        if has_lien_claim:
            logger.warning("유치권 신고 발견")
            return SpecialRight(
                right_type="유치권",
                risk_level=RiskLevel.CRITICAL,
                description="유치권 신고가 있습니다. 명도 전까지 대금 지급 불가",
                estimated_amount=None,
                mitigation="유치권 금액 확인 및 전문가 상담 필수",
            )

        return None


class RiskScorer:
    """위험도 스코어링"""

    # 등급 기준
    GRADE_THRESHOLDS = {
        RiskLevel.LOW: (0, 30),
        RiskLevel.MEDIUM: (30, 60),
        RiskLevel.HIGH: (60, 80),
        RiskLevel.CRITICAL: (80, 100),
    }

    def calculate_score(
        self,
        assumed_rights: list[RegistryEntry],
        tenants: list[TenantInfo],
        special_rights: list[SpecialRight],
        appraisal_value: int = 1_000_000_000,  # 기본값 10억
    ) -> tuple[int, RiskLevel]:
        """종합 위험 점수 계산

        Args:
            assumed_rights: 인수할 권리 리스트
            tenants: 임차인 리스트
            special_rights: 특수 권리 리스트
            appraisal_value: 감정평가액

        Returns:
            (위험점수, 위험등급)
        """
        score = 0

        # 1. 인수금액 비율 점수 (최대 30점)
        total_assumed = sum(r.amount or 0 for r in assumed_rights)
        assumed_ratio = total_assumed / appraisal_value if appraisal_value > 0 else 0
        score += min(30, assumed_ratio * 100)

        # 2. 선순위 권리 개수 점수 (최대 20점)
        score += min(20, len(assumed_rights) * 5)

        # 3. 임차인 대항력 점수 (최대 20점)
        priority_tenants = [t for t in tenants if t.has_priority]
        score += min(20, len(priority_tenants) * 10)

        # 4. 특수권리 점수 (최대 30점)
        for special in special_rights:
            if special.risk_level == RiskLevel.CRITICAL:
                score += 30
            elif special.risk_level == RiskLevel.HIGH:
                score += 20
            elif special.risk_level == RiskLevel.MEDIUM:
                score += 10

        # 점수 제한
        score = min(100, score)

        # 등급 결정
        risk_level = self._determine_risk_level(score)

        logger.info(f"위험도 점수: {score:.1f}점, 등급: {risk_level.value}")

        return int(score), risk_level

    def _determine_risk_level(self, score: float) -> RiskLevel:
        """점수에 따른 위험등급 결정"""
        for level, (min_score, max_score) in self.GRADE_THRESHOLDS.items():
            if min_score <= score < max_score:
                return level
        return RiskLevel.CRITICAL


class RightsAnalyzerAgent:
    """권리분석 에이전트 메인 클래스"""

    def __init__(self):
        self.extinction_detector = ExtinctionBaseRightDetector()
        self.classifier = RightClassifier()
        self.tenant_analyzer = TenantAnalyzer()
        self.superficies_detector = StatutorySuperficiesDetector()
        self.lien_detector = LienDetector()
        self.risk_scorer = RiskScorer()
        self.llm = get_llm_client(temperature=0.1)

        logger.info("권리분석 에이전트 초기화 완료")

    def analyze(
        self,
        case_number: str,
        gap_gu_entries: list[RegistryEntry],
        eul_gu_entries: list[RegistryEntry],
        tenants: Optional[list[TenantInfo]] = None,
        property_region: str = "기타",
        appraisal_value: Optional[int] = None,
        status_report: Optional[dict] = None,
    ) -> RightsAnalysisResult:
        """경매 사건 권리분석 수행

        Args:
            case_number: 경매 사건번호
            gap_gu_entries: 갑구 등기 항목
            eul_gu_entries: 을구 등기 항목
            tenants: 임차인 정보 (선택)
            property_region: 부동산 소재 지역
            appraisal_value: 감정평가액
            status_report: 현황조사서 데이터

        Returns:
            권리분석 결과
        """
        logger.info(f"권리분석 시작: 사건번호 {case_number}")

        # 1. 모든 등기 항목 통합
        all_entries = gap_gu_entries + eul_gu_entries

        # 2. 말소기준권리 탐지
        extinction_base = self.extinction_detector.find_extinction_base(all_entries)

        if not extinction_base:
            logger.error("말소기준권리를 찾을 수 없습니다.")
            # 기본값으로 결과 반환
            return RightsAnalysisResult(
                case_number=case_number,
                reference_right=ReferenceRight(
                    entry_number="미확인",
                    right_type=RightType.MORTGAGE,
                    registration_date=date.today(),
                    right_holder="미확인",
                    note="말소기준권리를 찾을 수 없습니다. 수동 검토 필요",
                ),
                risk_level=RiskLevel.CRITICAL,
                risk_score=100,
                summary="말소기준권리 미확인 - 전문가 검토 필수",
                warnings=["말소기준권리를 자동 탐지하지 못했습니다."],
            )

        # 3. 권리 분류
        assumed_rights, extinguished_rights = self.classifier.classify(
            all_entries, extinction_base
        )

        # 4. 임차인 분석
        analyzed_tenants = []
        if tenants:
            analyzed_tenants = self.tenant_analyzer.analyze(
                tenants, extinction_base, property_region
            )

        # 5. 특수권리 분석
        special_rights = []

        # 법정지상권 체크
        superficies_risk = self.superficies_detector.analyze(
            gap_gu_entries, eul_gu_entries
        )
        if superficies_risk:
            special_rights.append(superficies_risk)

        # 유치권 체크
        lien_risk = self.lien_detector.analyze(status_report)
        if lien_risk:
            special_rights.append(lien_risk)

        # 6. 위험도 평가
        risk_score, risk_level = self.risk_scorer.calculate_score(
            assumed_rights,
            analyzed_tenants,
            special_rights,
            appraisal_value or 1_000_000_000,
        )

        # 7. 금액 계산
        total_assumed_amount = sum(r.amount or 0 for r in assumed_rights)
        total_assumed_deposit = sum(
            t.assumed_deposit or 0 for t in analyzed_tenants
        )

        # 8. 경고 및 권장사항 생성
        warnings = self._generate_warnings(
            assumed_rights, analyzed_tenants, special_rights
        )
        recommendations = self._generate_recommendations(risk_level, assumed_rights)

        # 9. 요약 생성
        summary = self._generate_summary(
            extinction_base,
            assumed_rights,
            extinguished_rights,
            analyzed_tenants,
            total_assumed_amount,
            risk_level,
        )

        # 10. 입문자 적합성 판단
        beginner_suitable = risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM] and len(
            special_rights
        ) == 0

        # 11. 결과 조합
        result = RightsAnalysisResult(
            case_number=case_number,
            reference_right=ReferenceRight(
                entry_number=extinction_base.entry_number,
                right_type=extinction_base.right_type,
                registration_date=extinction_base.registration_date,
                right_holder=extinction_base.right_holder,
            ),
            assumed_rights=assumed_rights,
            extinguished_rights=extinguished_rights,
            total_assumed_amount=total_assumed_amount,
            tenants=analyzed_tenants,
            total_assumed_deposit=total_assumed_deposit,
            special_rights=special_rights,
            risk_level=risk_level,
            risk_score=risk_score,
            summary=summary,
            warnings=warnings,
            recommendations=recommendations,
            beginner_suitable=beginner_suitable,
            beginner_note=(
                "입문자에게 적합한 물건입니다."
                if beginner_suitable
                else "복잡한 권리관계가 있어 경험자에게 권장합니다."
            ),
        )

        logger.info(f"권리분석 완료: {case_number} - 위험등급 {risk_level.value}")

        return result

    def _generate_warnings(
        self,
        assumed_rights: list[RegistryEntry],
        tenants: list[TenantInfo],
        special_rights: list[SpecialRight],
    ) -> list[str]:
        """경고 메시지 생성"""
        warnings = []

        # 인수권리 경고
        if assumed_rights:
            total_amount = sum(r.amount or 0 for r in assumed_rights)
            warnings.append(
                f"인수해야 할 권리가 {len(assumed_rights)}건 있습니다. "
                f"총 {total_amount:,}원"
            )

        # 대항력 있는 임차인 경고
        priority_tenants = [t for t in tenants if t.has_priority]
        if priority_tenants:
            total_deposit = sum(t.assumed_deposit or 0 for t in priority_tenants)
            warnings.append(
                f"대항력 있는 임차인이 {len(priority_tenants)}명 있습니다. "
                f"총 보증금 {total_deposit:,}원"
            )

        # 특수권리 경고
        for special in special_rights:
            if special.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                warnings.append(f"{special.right_type}: {special.description}")

        return warnings

    def _generate_recommendations(
        self, risk_level: RiskLevel, assumed_rights: list[RegistryEntry]
    ) -> list[str]:
        """권장사항 생성"""
        recommendations = []

        if risk_level == RiskLevel.LOW:
            recommendations.append("권리관계가 깨끗합니다. 적극 검토 권장.")
        elif risk_level == RiskLevel.MEDIUM:
            recommendations.append("일부 주의사항이 있습니다. 상세 검토 후 결정하세요.")
        elif risk_level == RiskLevel.HIGH:
            recommendations.append(
                "복잡한 권리관계가 있습니다. 입문자에게는 비추천."
            )
        else:  # CRITICAL
            recommendations.append("고위험 물건입니다. 전문가 상담 없이 입찰 금지.")

        if assumed_rights:
            recommendations.append("인수금액을 포함한 총 투자금액을 계산하여 수익성을 재검토하세요.")
            recommendations.append("현장 방문하여 실제 상황을 확인하세요.")

        return recommendations

    def _generate_summary(
        self,
        extinction_base: RegistryEntry,
        assumed_rights: list[RegistryEntry],
        extinguished_rights: list[RegistryEntry],
        tenants: list[TenantInfo],
        total_assumed_amount: int,
        risk_level: RiskLevel,
    ) -> str:
        """요약 생성"""
        summary_parts = [
            f"말소기준권리: {extinction_base.right_type.value} "
            f"({extinction_base.registration_date})",
            f"인수권리: {len(assumed_rights)}건 (총 {total_assumed_amount:,}원)",
            f"소멸권리: {len(extinguished_rights)}건",
        ]

        if tenants:
            priority_count = sum(1 for t in tenants if t.has_priority)
            summary_parts.append(
                f"임차인: {len(tenants)}명 (대항력 {priority_count}명)"
            )

        summary_parts.append(f"위험등급: {risk_level.value}")

        return " | ".join(summary_parts)


# 편의 함수
def analyze_rights(
    case_number: str,
    gap_gu_entries: list[RegistryEntry],
    eul_gu_entries: list[RegistryEntry],
    **kwargs,
) -> RightsAnalysisResult:
    """권리분석 편의 함수

    Args:
        case_number: 경매 사건번호
        gap_gu_entries: 갑구 등기 항목
        eul_gu_entries: 을구 등기 항목
        **kwargs: 추가 옵션 (tenants, property_region, appraisal_value 등)

    Returns:
        권리분석 결과
    """
    agent = RightsAnalyzerAgent()
    return agent.analyze(case_number, gap_gu_entries, eul_gu_entries, **kwargs)
