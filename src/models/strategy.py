"""입찰전략 데이터 모델"""
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class StrategyType(str, Enum):
    """전략 유형"""
    CONSERVATIVE = "보수적"
    BALANCED = "균형적"
    AGGRESSIVE = "공격적"


class BidRecommendation(BaseModel):
    """입찰가 추천"""

    strategy_type: StrategyType
    bid_price: int
    bid_rate: float = Field(ge=0, le=1.5, description="감정가 대비 입찰율")

    # 예상 결과
    win_probability: float = Field(ge=0, le=1, description="낙찰 확률")
    expected_profit: int = Field(..., description="예상 수익")
    expected_roi: float = Field(..., description="예상 수익률")

    # 설명
    rationale: str = Field(default="", description="전략 근거")


class CostBreakdown(BaseModel):
    """비용 내역"""

    # 취득 비용
    acquisition_tax: int = Field(default=0, description="취득세")
    registration_tax: int = Field(default=0, description="등록세")
    judicial_fee: int = Field(default=0, description="법무사비")
    brokerage_fee: int = Field(default=0, description="중개수수료")

    # 인수 비용
    assumed_amount: int = Field(default=0, description="인수금액")
    assumed_deposit: int = Field(default=0, description="인수 보증금")

    # 부대 비용
    eviction_cost: int = Field(default=0, description="명도비용")
    renovation_cost: int = Field(default=0, description="수리비")
    holding_cost: int = Field(default=0, description="보유비용")

    @property
    def total_acquisition_cost(self) -> int:
        """총 취득 비용"""
        return (
            self.acquisition_tax
            + self.registration_tax
            + self.judicial_fee
            + self.brokerage_fee
        )

    @property
    def total_assumed_cost(self) -> int:
        """총 인수 비용"""
        return self.assumed_amount + self.assumed_deposit

    @property
    def total_additional_cost(self) -> int:
        """총 부대 비용"""
        return self.eviction_cost + self.renovation_cost + self.holding_cost

    @property
    def total_cost(self) -> int:
        """총 비용"""
        return (
            self.total_acquisition_cost
            + self.total_assumed_cost
            + self.total_additional_cost
        )


class ProfitAnalysis(BaseModel):
    """수익 분석"""

    bid_price: int
    total_investment: int = Field(..., description="총 투자금")
    expected_sale_price: int = Field(..., description="예상 매도가")

    # 수익
    gross_profit: int = Field(..., description="총 수익")
    net_profit: int = Field(..., description="순 수익")
    roi_percent: float = Field(..., description="투자수익률 (%)")

    # 손익분기점
    break_even_price: int = Field(..., description="손익분기 매도가")

    # 시나리오
    scenario: str = Field(default="기본", description="시나리오명")


class BidStrategyResult(BaseModel):
    """입찰전략 결과"""

    case_number: str

    # 최적 입찰가
    optimal_bid: int = Field(..., description="최적 입찰가")
    optimal_bid_rate: float = Field(..., description="최적 입찰율")

    # 전략별 추천
    recommendations: list[BidRecommendation] = Field(
        default_factory=list, description="전략별 추천 (보수/균형/공격)"
    )

    # 비용 분석
    cost_breakdown: CostBreakdown = Field(
        default_factory=CostBreakdown, description="비용 내역"
    )

    # 수익 분석
    profit_analysis: list[ProfitAnalysis] = Field(
        default_factory=list, description="수익 분석 (시나리오별)"
    )

    # 낙찰 확률 분석
    win_probability_by_rate: dict[float, float] = Field(
        default_factory=dict, description="입찰율별 낙찰 확률"
    )

    # 경쟁 분석
    expected_competitors: int = Field(default=3, description="예상 경쟁자 수")
    competition_intensity: str = Field(default="보통", description="경쟁 강도")

    # 추천 사항
    final_recommendation: str = Field(default="", description="최종 추천")
    cautions: list[str] = Field(default_factory=list, description="주의사항")

    # 타이밍
    should_bid_this_round: bool = Field(default=True, description="이번 회차 입찰 여부")
    wait_reason: Optional[str] = Field(None, description="대기 이유")
