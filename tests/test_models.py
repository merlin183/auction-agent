"""데이터 모델 테스트"""
import pytest
from datetime import date
from decimal import Decimal

from src.models.auction import AuctionProperty, PropertyType, AuctionStatus
from src.models.rights import (
    RegistryEntry,
    RightType,
    RightStatus,
    RightsAnalysisResult,
    ReferenceRight,
    RiskLevel as RightsRiskLevel,
)
from src.models.valuation import ValuationResult, PriceEstimate, PriceTrend
from src.models.risk import RiskAssessmentResult, RiskGrade, CategoryRisk, RiskLevel
from src.models.strategy import BidStrategyResult, BidRecommendation, StrategyType
from src.models.validation import RedTeamReport, ValidationStatus


class TestAuctionProperty:
    """경매 물건 모델 테스트"""

    def test_create_auction_property(self):
        """경매 물건 생성"""
        prop = AuctionProperty(
            case_number="2024타경12345",
            court="서울중앙지방법원",
            property_type=PropertyType.APARTMENT,
            address="서울시 강남구 역삼동 123-45",
            exclusive_area_sqm=Decimal("84.5"),
            appraisal_value=500_000_000,
            minimum_bid=400_000_000,
            auction_date=date(2024, 3, 15),
        )

        assert prop.case_number == "2024타경12345"
        assert prop.bid_rate == Decimal("0.8")
        assert prop.discount_rate == Decimal("0.2")

    def test_area_conversion(self):
        """면적 변환"""
        prop = AuctionProperty(
            case_number="2024타경12345",
            court="서울중앙지방법원",
            property_type=PropertyType.APARTMENT,
            address="서울시 강남구",
            exclusive_area_sqm=Decimal("33.0579"),  # 약 10평
            appraisal_value=100_000_000,
            minimum_bid=80_000_000,
            auction_date=date(2024, 3, 15),
        )

        assert prop.exclusive_area_pyung is not None
        assert 9.9 < float(prop.exclusive_area_pyung) < 10.1


class TestRightsAnalysis:
    """권리분석 모델 테스트"""

    def test_create_registry_entry(self):
        """등기 항목 생성"""
        entry = RegistryEntry(
            entry_number="1",
            registration_date=date(2020, 1, 15),
            right_type=RightType.MORTGAGE,
            right_holder="○○은행",
            amount=300_000_000,
            status=RightStatus.EXTINGUISHED,
        )

        assert entry.right_type == RightType.MORTGAGE
        assert entry.status == RightStatus.EXTINGUISHED

    def test_rights_analysis_result(self):
        """권리분석 결과"""
        result = RightsAnalysisResult(
            case_number="2024타경12345",
            reference_right=ReferenceRight(
                entry_number="1",
                right_type=RightType.MORTGAGE,
                registration_date=date(2020, 1, 15),
                right_holder="○○은행",
            ),
            total_assumed_amount=50_000_000,
            risk_level=RightsRiskLevel.MEDIUM,
            risk_score=45,
            beginner_suitable=True,
        )

        assert result.risk_level == RightsRiskLevel.MEDIUM
        assert result.beginner_suitable


class TestValuation:
    """가치평가 모델 테스트"""

    def test_valuation_result(self):
        """가치평가 결과"""
        result = ValuationResult(
            case_number="2024타경12345",
            appraisal_value=500_000_000,
            estimated_market_price=PriceEstimate(
                lower_bound=450_000_000,
                estimate=480_000_000,
                upper_bound=520_000_000,
                confidence=0.8,
            ),
            price_per_pyung=15_000_000,
            price_trend=PriceTrend.STABLE,
        )

        assert result.appraisal_vs_market_gap == pytest.approx(0.0417, rel=0.01)


class TestRiskAssessment:
    """위험평가 모델 테스트"""

    def test_risk_assessment_result(self):
        """위험평가 결과"""
        result = RiskAssessmentResult(
            case_number="2024타경12345",
            total_score=42.5,
            grade=RiskGrade.B,
            level=RiskLevel.MEDIUM,
            rights_risk=CategoryRisk(
                name="권리 리스크",
                score=45,
                level=RiskLevel.MEDIUM,
                weight=0.4,
            ),
            market_risk=CategoryRisk(
                name="시장 리스크",
                score=35,
                level=RiskLevel.MEDIUM,
                weight=0.2,
            ),
            property_risk=CategoryRisk(
                name="물건 리스크",
                score=40,
                level=RiskLevel.MEDIUM,
                weight=0.2,
            ),
            eviction_risk=CategoryRisk(
                name="명도 리스크",
                score=50,
                level=RiskLevel.MEDIUM,
                weight=0.2,
            ),
            beginner_friendly=True,
        )

        assert result.grade == RiskGrade.B
        assert result.weighted_score == pytest.approx(43.0)


class TestBidStrategy:
    """입찰전략 모델 테스트"""

    def test_bid_recommendation(self):
        """입찰 추천"""
        rec = BidRecommendation(
            strategy_type=StrategyType.BALANCED,
            bid_price=350_000_000,
            bid_rate=0.7,
            win_probability=0.65,
            expected_profit=50_000_000,
            expected_roi=0.143,
        )

        assert rec.strategy_type == StrategyType.BALANCED
        assert rec.win_probability == 0.65


class TestRedTeamReport:
    """레드팀 리포트 모델 테스트"""

    def test_red_team_report(self):
        """레드팀 리포트"""
        report = RedTeamReport(
            case_id="2024타경12345",
            overall_status=ValidationStatus.PASSED_WITH_WARNINGS,
            overall_reliability=82.5,
            approved=True,
        )

        assert report.overall_status == ValidationStatus.PASSED_WITH_WARNINGS
        assert report.approved
        assert report.total_issues_count == 0
