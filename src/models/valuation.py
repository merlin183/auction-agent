"""가치평가 데이터 모델"""
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class PriceTrend(str, Enum):
    """가격 추세"""
    UPWARD = "상승"
    STABLE = "보합"
    DOWNWARD = "하락"


class ComparableSale(BaseModel):
    """비교 거래 사례"""

    address: str
    transaction_date: date
    transaction_price: int
    area_sqm: Decimal
    price_per_sqm: int
    floor: Optional[int] = None
    building_year: Optional[int] = None
    distance_meters: Optional[int] = None
    similarity_score: float = Field(default=0.0, ge=0, le=1)


class PriceEstimate(BaseModel):
    """가격 추정"""

    lower_bound: int = Field(..., description="하한가")
    estimate: int = Field(..., description="추정가")
    upper_bound: int = Field(..., description="상한가")
    confidence: float = Field(default=0.7, ge=0, le=1, description="신뢰도")


class ROIScenario(BaseModel):
    """수익률 시나리오"""

    scenario_name: str  # 낙관적, 중립적, 비관적
    bid_price: int
    bid_rate: float
    selling_price: int
    holding_period_months: int

    # 비용
    acquisition_cost: int  # 취득세 등
    holding_cost: int  # 보유 비용
    selling_cost: int  # 매도 비용
    renovation_cost: int  # 수리비

    # 수익
    gross_profit: int
    net_profit: int
    roi_percent: float
    annualized_roi: float


class ValuationResult(BaseModel):
    """가치평가 결과"""

    case_number: str

    # 감정가 정보
    appraisal_value: int
    appraisal_date: Optional[date] = None
    appraisal_note: Optional[str] = None

    # 시세 추정
    estimated_market_price: PriceEstimate
    price_per_pyung: int = Field(..., description="평당가")

    # 시장 분석
    price_trend: PriceTrend = Field(default=PriceTrend.STABLE)
    trend_rate_6m: Optional[float] = Field(None, description="6개월 추세율")
    volatility: Optional[float] = Field(None, description="가격 변동성")

    # 비교 사례
    comparables: list[ComparableSale] = Field(
        default_factory=list, description="비교 사례"
    )
    comparables_avg_price: Optional[int] = None
    comparables_median_price: Optional[int] = None

    # 낙찰가율 예측
    predicted_bid_rate: float = Field(default=0.7, description="예상 낙찰가율")
    predicted_bid_rate_range: tuple[float, float] = Field(
        default=(0.65, 0.8), description="낙찰가율 범위"
    )

    # 수익률 시뮬레이션
    roi_scenarios: list[ROIScenario] = Field(
        default_factory=list, description="수익률 시나리오"
    )

    # 모델 정보
    model_version: str = Field(default="1.0")
    model_confidence: float = Field(default=0.7, ge=0, le=1)

    # 분석 요약
    summary: str = Field(default="")
    price_opinion: str = Field(default="", description="가격 평가 의견")

    @property
    def appraisal_vs_market_gap(self) -> float:
        """감정가 vs 시세 괴리율"""
        if self.estimated_market_price.estimate > 0:
            return (
                self.appraisal_value - self.estimated_market_price.estimate
            ) / self.estimated_market_price.estimate
        return 0.0
