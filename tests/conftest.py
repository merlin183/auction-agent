"""Pytest 설정 및 픽스처"""
import pytest
from datetime import date
from decimal import Decimal

from src.models.auction import AuctionProperty, PropertyType
from src.models.rights import (
    RightsAnalysisResult,
    ReferenceRight,
    RightType,
    RiskLevel,
    TenantInfo,
)
from src.models.valuation import ValuationResult, PriceEstimate, PriceTrend
from src.models.location import (
    LocationAnalysisResult,
    TransportScore,
    EducationScore,
    AmenityScore,
)
from src.models.risk import RiskAssessmentResult, RiskGrade, CategoryRisk
from src.models.strategy import BidStrategyResult, BidRecommendation, StrategyType


@pytest.fixture
def sample_auction_property() -> AuctionProperty:
    """샘플 경매 물건"""
    return AuctionProperty(
        case_number="2024타경12345",
        court="서울중앙지방법원",
        property_type=PropertyType.APARTMENT,
        address="서울시 강남구 역삼동 123-45 ○○아파트 101동 1501호",
        exclusive_area_sqm=Decimal("84.97"),
        building_year=2015,
        floor=15,
        total_floors=25,
        rooms=3,
        bathrooms=2,
        appraisal_value=1_200_000_000,
        minimum_bid=960_000_000,
        bid_count=1,
        auction_date=date(2024, 3, 15),
        latitude=37.5012,
        longitude=127.0396,
    )


@pytest.fixture
def sample_rights_analysis() -> RightsAnalysisResult:
    """샘플 권리분석 결과"""
    return RightsAnalysisResult(
        case_number="2024타경12345",
        reference_right=ReferenceRight(
            entry_number="2",
            right_type=RightType.MORTGAGE,
            registration_date=date(2020, 3, 10),
            right_holder="○○은행",
        ),
        total_assumed_amount=0,
        tenants=[
            TenantInfo(
                name="김○○",
                move_in_date=date(2022, 5, 1),
                fixed_date=date(2022, 5, 2),
                deposit=200_000_000,
                has_priority=False,
                assumed_deposit=0,
            )
        ],
        total_assumed_deposit=0,
        risk_level=RiskLevel.LOW,
        risk_score=25,
        summary="권리관계가 깨끗하여 입문자도 안전하게 접근 가능합니다.",
        beginner_suitable=True,
    )


@pytest.fixture
def sample_valuation() -> ValuationResult:
    """샘플 가치평가 결과"""
    return ValuationResult(
        case_number="2024타경12345",
        appraisal_value=1_200_000_000,
        appraisal_date=date(2024, 1, 15),
        estimated_market_price=PriceEstimate(
            lower_bound=1_100_000_000,
            estimate=1_180_000_000,
            upper_bound=1_250_000_000,
            confidence=0.85,
        ),
        price_per_pyung=46_000_000,
        price_trend=PriceTrend.STABLE,
        predicted_bid_rate=0.78,
        predicted_bid_rate_range=(0.72, 0.85),
    )


@pytest.fixture
def sample_location_analysis() -> LocationAnalysisResult:
    """샘플 입지분석 결과"""
    return LocationAnalysisResult(
        case_number="2024타경12345",
        address="서울시 강남구 역삼동",
        latitude=37.5012,
        longitude=127.0396,
        total_score=82,
        transport_score=TransportScore(
            total_score=90,
            nearest_subway="역삼역",
            subway_distance_meters=350,
            subway_walk_minutes=5,
            subway_lines=["2호선"],
            bus_stops_within_300m=3,
        ),
        education_score=EducationScore(
            total_score=75,
            nearest_elementary_meters=400,
            academy_density="높음",
        ),
        amenity_score=AmenityScore(
            total_score=80,
            hospitals_within_1km=5,
            marts_within_1km=["이마트", "홈플러스"],
        ),
        development_score=70,
        strengths=["지하철 역세권", "강남 학군"],
        weaknesses=["주차 공간 부족"],
    )


@pytest.fixture
def sample_risk_assessment() -> RiskAssessmentResult:
    """샘플 위험평가 결과"""
    return RiskAssessmentResult(
        case_number="2024타경12345",
        total_score=32,
        grade=RiskGrade.B,
        level=RiskLevel.MEDIUM,
        rights_risk=CategoryRisk(
            name="권리 리스크",
            score=25,
            level=RiskLevel.LOW,
            weight=0.4,
            summary="인수 권리 없음",
        ),
        market_risk=CategoryRisk(
            name="시장 리스크",
            score=35,
            level=RiskLevel.MEDIUM,
            weight=0.2,
            summary="시세 안정적",
        ),
        property_risk=CategoryRisk(
            name="물건 리스크",
            score=30,
            level=RiskLevel.LOW,
            weight=0.2,
            summary="관리 양호",
        ),
        eviction_risk=CategoryRisk(
            name="명도 리스크",
            score=45,
            level=RiskLevel.MEDIUM,
            weight=0.2,
            summary="임차인 1명, 명도 협조 예상",
        ),
        beginner_friendly=True,
        beginner_note="권리관계가 깔끔하여 입문자도 검토 가능합니다.",
    )


@pytest.fixture
def sample_bid_strategy() -> BidStrategyResult:
    """샘플 입찰전략 결과"""
    return BidStrategyResult(
        case_number="2024타경12345",
        optimal_bid=900_000_000,
        optimal_bid_rate=0.75,
        recommendations=[
            BidRecommendation(
                strategy_type=StrategyType.CONSERVATIVE,
                bid_price=840_000_000,
                bid_rate=0.70,
                win_probability=0.45,
                expected_profit=180_000_000,
                expected_roi=0.214,
                rationale="유찰 시 추가 할인 기대",
            ),
            BidRecommendation(
                strategy_type=StrategyType.BALANCED,
                bid_price=900_000_000,
                bid_rate=0.75,
                win_probability=0.65,
                expected_profit=140_000_000,
                expected_roi=0.156,
                rationale="적정 경쟁에서 낙찰 목표",
            ),
            BidRecommendation(
                strategy_type=StrategyType.AGGRESSIVE,
                bid_price=960_000_000,
                bid_rate=0.80,
                win_probability=0.85,
                expected_profit=100_000_000,
                expected_roi=0.104,
                rationale="물건 확보 우선",
            ),
        ],
        expected_competitors=5,
        competition_intensity="보통",
        final_recommendation="균형적 전략으로 9억원 입찰을 권장합니다.",
        should_bid_this_round=True,
    )
