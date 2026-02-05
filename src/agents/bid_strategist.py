"""입찰전략 에이전트 (Bid Strategist Agent)

권리분석, 가치평가, 위험평가 결과를 종합하여 최적의 입찰가를 산정하고,
목표 수익률에 맞는 전략을 제안하는 전문 AI 에이전트
"""
from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
from scipy.stats import norm

try:
    from ..models.strategy import (
        BidRecommendation,
        BidStrategyResult,
        CostBreakdown,
        ProfitAnalysis,
        StrategyType,
    )
except ImportError:
    from models.strategy import (
        BidRecommendation,
        BidStrategyResult,
        CostBreakdown,
        ProfitAnalysis,
        StrategyType,
    )


@dataclass
class CostComponents:
    """투자 비용 구성요소"""

    bid_price: int  # 입찰가
    assumed_amount: int  # 인수금액 (선순위 권리)
    acquisition_tax: int  # 취득세
    registration_fee: int  # 등기비용
    brokerage_fee: int  # 중개수수료
    moving_cost: int  # 명도비용
    renovation_cost: int  # 리모델링 비용
    misc_cost: int  # 기타 비용

    @property
    def total_investment(self) -> int:
        """총 투자금액"""
        return (
            self.bid_price
            + self.assumed_amount
            + self.acquisition_tax
            + self.registration_fee
            + self.brokerage_fee
            + self.moving_cost
            + self.renovation_cost
            + self.misc_cost
        )


@dataclass
class BidStrategy:
    """입찰 전략"""

    name: str  # 전략명
    bid_price: int  # 입찰가
    bid_ratio: float  # 낙찰가율
    expected_roi: float  # 예상 수익률
    win_probability: float  # 낙찰 확률
    risk_level: str  # 위험 수준
    total_investment: int  # 총 투자금
    expected_profit: int  # 예상 수익
    recommendation: str  # 추천 의견


@dataclass
class FallbackStrategy:
    """유찰 대응 전략"""

    round_number: int  # 회차
    minimum_bid_ratio: float  # 최저입찰가율
    recommended_bid: int  # 추천 입찰가
    expected_competition: str  # 예상 경쟁
    action: str  # 추천 행동


class CostCalculator:
    """비용 계산기"""

    # 취득세율 (주택 기준)
    ACQUISITION_TAX_RATES = {
        "1주택": {
            (0, 600_000_000): 0.01,
            (600_000_000, 900_000_000): 0.02,
            (900_000_000, float("inf")): 0.03,
        },
        "2주택": 0.08,
        "3주택이상": 0.12,
        "법인": 0.12,
    }

    def calculate(
        self,
        bid_price: int,
        rights_analysis: Dict,
        risk_analysis: Dict,
        user_settings: Dict,
    ) -> CostComponents:
        """총 비용 계산"""

        # 인수금액 (권리분석 결과에서)
        assumed_amount = rights_analysis.get("total_assumed_amount", 0)

        # 취득세
        tax_type = user_settings.get("housing_count", "1주택")
        acquisition_tax = self._calculate_acquisition_tax(bid_price, tax_type)

        # 등기비용 (낙찰가의 약 0.5%)
        registration_fee = int(bid_price * 0.005)

        # 명도비용 (위험분석 결과 기반)
        eviction_difficulty = risk_analysis.get("eviction_difficulty", "LOW")
        moving_cost = self._estimate_moving_cost(eviction_difficulty)

        # 리모델링 비용 (선택적)
        renovation_cost = user_settings.get("renovation_budget", 0)

        return CostComponents(
            bid_price=bid_price,
            assumed_amount=assumed_amount,
            acquisition_tax=acquisition_tax,
            registration_fee=registration_fee,
            brokerage_fee=0,  # 경매는 중개수수료 없음
            moving_cost=moving_cost,
            renovation_cost=renovation_cost,
            misc_cost=500_000,  # 기타 비용 (법무사비 등)
        )

    def _calculate_acquisition_tax(self, price: int, tax_type: str) -> int:
        """취득세 계산"""
        if tax_type == "1주택":
            rates = self.ACQUISITION_TAX_RATES["1주택"]
            for (lower, upper), rate in rates.items():
                if lower <= price < upper:
                    return int(price * rate)
        else:
            rate = self.ACQUISITION_TAX_RATES.get(tax_type, 0.03)
            return int(price * rate)
        return int(price * 0.03)

    def _estimate_moving_cost(self, difficulty: str) -> int:
        """명도비용 추정"""
        costs = {
            "LOW": 0,
            "MEDIUM": 5_000_000,
            "HIGH": 15_000_000,
            "CRITICAL": 30_000_000,
        }
        return costs.get(difficulty, 5_000_000)


class CompetitionPredictor:
    """경쟁률 예측기"""

    def __init__(self):
        self.model = None

    def predict(self, features: Dict) -> Dict:
        """경쟁률 예측

        실제 ML 모델이 없는 경우 휴리스틱 기반 예측
        """

        # 입찰가율이 낮을수록 경쟁자 적음
        bid_ratio = features.get("bid_ratio", 0.8)
        auction_count = features.get("auction_count", 1)
        risk_grade = features.get("risk_grade_encoded", 2)

        # 기본 경쟁자 수 예측
        base_bidders = 5.0

        # 입찰가율 보정 (낮을수록 경쟁자 증가)
        ratio_factor = (0.8 - bid_ratio) * 10  # 0.7 -> +1명, 0.6 -> +2명

        # 유찰 횟수 보정 (유찰 많을수록 경쟁자 감소)
        auction_factor = -0.5 * (auction_count - 1)

        # 위험등급 보정 (위험할수록 경쟁자 감소)
        risk_factor = -0.5 * risk_grade

        predicted_bidders = max(
            1, round(base_bidders + ratio_factor + auction_factor + risk_factor)
        )

        # 경쟁 강도 분류
        if predicted_bidders <= 2:
            intensity = "LOW"
        elif predicted_bidders <= 5:
            intensity = "MEDIUM"
        elif predicted_bidders <= 10:
            intensity = "HIGH"
        else:
            intensity = "VERY_HIGH"

        return {
            "predicted_bidders": predicted_bidders,
            "intensity": intensity,
            "recommendation": self._get_recommendation(intensity),
        }

    def _get_recommendation(self, intensity: str) -> str:
        """경쟁 강도별 추천"""
        recommendations = {
            "LOW": "경쟁이 적어 낮은 입찰가로도 낙찰 가능성 높음",
            "MEDIUM": "적정 경쟁 예상. 균형적 전략 권장",
            "HIGH": "경쟁 치열 예상. 목표가 상향 검토 필요",
            "VERY_HIGH": "매우 치열한 경쟁 예상. 시세 근접 입찰 필요",
        }
        return recommendations.get(intensity, "")


class WinProbabilityCalculator:
    """낙찰 확률 계산기"""

    def __init__(self):
        self.historical_data = None

    def calculate(
        self,
        my_bid: int,
        appraisal_value: int,
        competition: Dict,
        auction_history: Optional[List] = None,
    ) -> Dict:
        """낙찰 확률 계산"""

        my_bid_ratio = my_bid / appraisal_value if appraisal_value > 0 else 0

        # 과거 낙찰가율 분포 분석
        if auction_history:
            bid_ratios = [h.get("bid_ratio", 0.75) for h in auction_history]
            mean_ratio = np.mean(bid_ratios)
            std_ratio = np.std(bid_ratios) if len(bid_ratios) > 1 else 0.05
        else:
            # 기본값 (통상 경매 낙찰가율 평균 75%, 표준편차 10%)
            mean_ratio = 0.75
            std_ratio = 0.1

        # 정규분포 기반 확률 계산
        # 내 입찰가가 평균 낙찰가보다 높을 확률
        if std_ratio > 0:
            z_score = (my_bid_ratio - mean_ratio) / std_ratio
            base_probability = norm.cdf(z_score)
        else:
            base_probability = 1.0 if my_bid_ratio >= mean_ratio else 0.0

        # 경쟁률 보정
        bidders = competition.get("predicted_bidders", 3)
        # 경쟁자가 많을수록 낙찰 확률 감소 (단순화)
        competition_factor = 1.0 / (1.0 + 0.1 * bidders)

        # 최종 확률 (경쟁자 수 반영)
        win_probability = base_probability * competition_factor

        # 확률 범위 제한
        win_probability = max(0.01, min(0.99, win_probability))

        return {
            "probability": round(win_probability, 3),
            "percentage": f"{round(win_probability * 100, 1)}%",
            "confidence": self._assess_confidence(
                std_ratio, len(auction_history) if auction_history else 0
            ),
            "interpretation": self._interpret_probability(win_probability),
        }

    def _assess_confidence(self, std: float, sample_size: int) -> str:
        """예측 신뢰도 평가"""
        if sample_size >= 10 and std < 0.1:
            return "HIGH"
        elif sample_size >= 5:
            return "MEDIUM"
        else:
            return "LOW"

    def _interpret_probability(self, prob: float) -> str:
        """확률 해석"""
        if prob >= 0.8:
            return "매우 높음 - 낙찰 유력"
        elif prob >= 0.6:
            return "높음 - 낙찰 가능성 양호"
        elif prob >= 0.4:
            return "보통 - 경쟁에 따라 결정"
        elif prob >= 0.2:
            return "낮음 - 낙찰 어려울 수 있음"
        else:
            return "매우 낮음 - 입찰가 상향 권장"


class OptimalBidCalculator:
    """최적 입찰가 산정기"""

    def __init__(
        self,
        cost_calculator: CostCalculator,
        probability_calculator: WinProbabilityCalculator,
        competition_predictor: CompetitionPredictor,
    ):
        self.cost_calc = cost_calculator
        self.prob_calc = probability_calculator
        self.comp_pred = competition_predictor

    def calculate_optimal_bid(
        self,
        valuation: Dict,
        rights_analysis: Dict,
        risk_analysis: Dict,
        user_settings: Dict,
    ) -> List[BidStrategy]:
        """최적 입찰가 및 3가지 전략 생성"""

        estimated_market_price = valuation["estimated_market_price"]
        appraisal_value = valuation["appraisal_value"]
        minimum_bid = valuation["minimum_bid"]
        assumed_amount = rights_analysis.get("total_assumed_amount", 0)
        target_roi = user_settings.get("target_roi", 0.15)  # 기본 15%

        # 경쟁률 예측
        competition = self.comp_pred.predict(
            {
                "bid_ratio": minimum_bid / appraisal_value if appraisal_value > 0 else 0.8,
                "auction_count": valuation.get("auction_count", 1),
                "region_encoded": valuation.get("region_encoded", 0),
                "risk_grade_encoded": risk_analysis.get("risk_grade_encoded", 2),
            }
        )

        # 최적 입찰가 계산 (목표 수익률 기반)
        optimal_bid = self._calculate_target_roi_bid(
            estimated_market_price,
            assumed_amount,
            target_roi,
            rights_analysis,
            risk_analysis,
            user_settings,
        )

        # 최저입찰가 보장
        optimal_bid = max(minimum_bid, optimal_bid)

        # 3가지 전략 생성
        strategies = []

        # 1. 보수적 전략 (높은 수익률, 낮은 낙찰 확률)
        conservative_bid = max(minimum_bid, int(optimal_bid * 0.9))
        strategies.append(
            self._create_strategy(
                name="보수적",
                bid_price=conservative_bid,
                appraisal_value=appraisal_value,
                estimated_market_price=estimated_market_price,
                assumed_amount=assumed_amount,
                competition=competition,
                rights_analysis=rights_analysis,
                risk_analysis=risk_analysis,
                user_settings=user_settings,
            )
        )

        # 2. 균형적 전략 (적정 수익률, 적정 낙찰 확률)
        balanced_bid = optimal_bid
        strategies.append(
            self._create_strategy(
                name="균형적",
                bid_price=balanced_bid,
                appraisal_value=appraisal_value,
                estimated_market_price=estimated_market_price,
                assumed_amount=assumed_amount,
                competition=competition,
                rights_analysis=rights_analysis,
                risk_analysis=risk_analysis,
                user_settings=user_settings,
            )
        )

        # 3. 공격적 전략 (낮은 수익률, 높은 낙찰 확률)
        aggressive_bid = max(minimum_bid, int(optimal_bid * 1.1))
        strategies.append(
            self._create_strategy(
                name="공격적",
                bid_price=aggressive_bid,
                appraisal_value=appraisal_value,
                estimated_market_price=estimated_market_price,
                assumed_amount=assumed_amount,
                competition=competition,
                rights_analysis=rights_analysis,
                risk_analysis=risk_analysis,
                user_settings=user_settings,
            )
        )

        return strategies

    def _calculate_target_roi_bid(
        self,
        market_price: int,
        assumed_amount: int,
        target_roi: float,
        rights_analysis: Dict,
        risk_analysis: Dict,
        user_settings: Dict,
    ) -> int:
        """
        목표 수익률 달성을 위한 최적 입찰가 계산

        공식:
        총투자금 = 입찰가 + 인수금액 + 취득세 + 기타비용
        목표수익 = 시세 - 총투자금
        목표수익률 = 목표수익 / 총투자금

        역산:
        입찰가 = (시세 - 인수금액 - 기타비용) / (1 + 목표수익률 + 취득세율)
        """

        # 기타 비용 추정
        registration_fee = 500_000
        moving_cost = self.cost_calc._estimate_moving_cost(
            risk_analysis.get("eviction_difficulty", "LOW")
        )
        renovation_cost = user_settings.get("renovation_budget", 0)
        misc_cost = 500_000

        fixed_costs = (
            assumed_amount + registration_fee + moving_cost + renovation_cost + misc_cost
        )

        # 취득세율
        tax_type = user_settings.get("housing_count", "1주택")
        if tax_type == "1주택":
            tax_rate = 0.02  # 평균
        else:
            tax_rate = 0.08

        # 최적 입찰가 역산
        # 시세 = 입찰가 * (1 + 세율) + 고정비용 + (입찰가 * (1 + 세율) + 고정비용) * 목표수익률
        # 시세 = 입찰가 * (1 + 세율) * (1 + 목표수익률) + 고정비용 * (1 + 목표수익률)
        # 입찰가 = (시세 - 고정비용 * (1 + 목표수익률)) / ((1 + 세율) * (1 + 목표수익률))

        numerator = market_price - fixed_costs * (1 + target_roi)
        denominator = (1 + tax_rate) * (1 + target_roi)

        optimal_bid = int(numerator / denominator)

        return max(0, optimal_bid)

    def _create_strategy(
        self,
        name: str,
        bid_price: int,
        appraisal_value: int,
        estimated_market_price: int,
        assumed_amount: int,
        competition: Dict,
        rights_analysis: Dict,
        risk_analysis: Dict,
        user_settings: Dict,
    ) -> BidStrategy:
        """전략 객체 생성"""

        # 비용 계산
        costs = self.cost_calc.calculate(
            bid_price, rights_analysis, risk_analysis, user_settings
        )

        # 수익률 계산
        expected_profit = estimated_market_price - costs.total_investment
        expected_roi = (
            expected_profit / costs.total_investment if costs.total_investment > 0 else 0
        )

        # 낙찰 확률 계산
        win_prob = self.prob_calc.calculate(
            bid_price, appraisal_value, competition, None
        )

        # 위험 수준 결정
        if expected_roi >= 0.2 and win_prob["probability"] >= 0.5:
            risk_level = "LOW"
        elif expected_roi >= 0.1:
            risk_level = "MEDIUM"
        elif expected_roi >= 0:
            risk_level = "HIGH"
        else:
            risk_level = "CRITICAL"

        # 추천 의견
        recommendation = self._generate_recommendation(
            name, expected_roi, win_prob["probability"], risk_level
        )

        return BidStrategy(
            name=name,
            bid_price=bid_price,
            bid_ratio=bid_price / appraisal_value if appraisal_value > 0 else 0,
            expected_roi=expected_roi,
            win_probability=win_prob["probability"],
            risk_level=risk_level,
            total_investment=costs.total_investment,
            expected_profit=expected_profit,
            recommendation=recommendation,
        )

    def _generate_recommendation(
        self, strategy_name: str, roi: float, win_prob: float, risk_level: str
    ) -> str:
        """전략별 추천 의견 생성"""

        if strategy_name == "보수적":
            if win_prob < 0.3:
                return "낙찰 확률이 낮아 유찰 시 재입찰 권장"
            return f"예상 수익률 {roi*100:.1f}%로 안정적이나 낙찰 확률 주의"

        elif strategy_name == "균형적":
            return f"수익률({roi*100:.1f}%)과 낙찰확률({win_prob*100:.1f}%)의 균형점"

        else:  # 공격적
            if risk_level == "CRITICAL":
                return "수익률이 낮아 권장하지 않음"
            return f"높은 낙찰 확률({win_prob*100:.1f}%)이나 수익률 리스크 존재"


class FallbackStrategyGenerator:
    """유찰 대응 전략 생성기"""

    # 유찰 시 최저입찰가 감소율 (통상 20%)
    REDUCTION_RATE = 0.2

    def generate(
        self,
        current_round: int,
        appraisal_value: int,
        estimated_market_price: int,
        user_max_roi: float = 0.1,
    ) -> List[FallbackStrategy]:
        """향후 5회차까지 유찰 대응 전략 생성"""

        strategies = []
        current_min_ratio = 0.8  # 1회차 최저입찰가율

        for round_num in range(current_round, current_round + 5):
            # 회차별 최저입찰가율 계산
            reductions = round_num - 1
            min_ratio = current_min_ratio * ((1 - self.REDUCTION_RATE) ** reductions)

            # 최저입찰가
            minimum_bid = int(appraisal_value * min_ratio)

            # 시세 대비 비율
            market_ratio = (
                minimum_bid / estimated_market_price if estimated_market_price > 0 else 0
            )

            # 추천 행동 결정
            if market_ratio <= (1 - user_max_roi):
                action = "적극 입찰 권장"
                competition = "HIGH"
            elif market_ratio <= 0.9:
                action = "입찰 고려"
                competition = "MEDIUM"
            else:
                action = "관망 추천"
                competition = "LOW"

            strategies.append(
                FallbackStrategy(
                    round_number=round_num,
                    minimum_bid_ratio=min_ratio,
                    recommended_bid=minimum_bid,
                    expected_competition=competition,
                    action=action,
                )
            )

        return strategies


class BidStrategistAgent:
    """입찰전략 에이전트 메인 클래스

    권리분석, 가치평가, 위험평가 결과를 종합하여
    최적의 입찰가를 산정하고 전략을 제안합니다.
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.cost_calculator = CostCalculator()
        self.competition_predictor = CompetitionPredictor()
        self.probability_calculator = WinProbabilityCalculator()
        self.optimal_bid_calculator = OptimalBidCalculator(
            self.cost_calculator,
            self.probability_calculator,
            self.competition_predictor,
        )
        self.fallback_generator = FallbackStrategyGenerator()

    def generate_strategy(
        self,
        valuation: Dict,
        rights_analysis: Dict,
        risk_analysis: Dict,
        user_settings: Dict,
    ) -> BidStrategyResult:
        """입찰 전략 생성

        Args:
            valuation: 가치평가 결과
                - estimated_market_price: 추정 시세
                - appraisal_value: 감정가
                - minimum_bid: 최저입찰가
                - auction_count: 유찰 횟수
            rights_analysis: 권리분석 결과
                - total_assumed_amount: 인수금액
            risk_analysis: 위험평가 결과
                - eviction_difficulty: 명도 난이도
                - risk_grade: 위험등급
                - risk_grade_encoded: 위험등급 인코딩 (0-4)
            user_settings: 사용자 설정
                - target_roi: 목표 수익률 (기본 0.15)
                - housing_count: 보유 주택 수 (기본 '1주택')
                - renovation_budget: 리모델링 예산 (기본 0)
                - risk_tolerance: 위험선호도 (기본 'balanced')

        Returns:
            BidStrategyResult: 입찰 전략 결과
        """

        case_number = valuation.get("case_number", "")
        appraisal_value = valuation["appraisal_value"]

        # 1. 3가지 전략 생성
        strategies = self.optimal_bid_calculator.calculate_optimal_bid(
            valuation, rights_analysis, risk_analysis, user_settings
        )

        # 2. 유찰 대응 전략
        fallback_strategies = self.fallback_generator.generate(
            current_round=valuation.get("auction_count", 1),
            appraisal_value=appraisal_value,
            estimated_market_price=valuation["estimated_market_price"],
            user_max_roi=user_settings.get("target_roi", 0.15),
        )

        # 3. 최종 추천 전략 선정
        recommended = self._select_recommended_strategy(
            strategies, risk_analysis.get("risk_grade", "B"), user_settings
        )

        # 4. BidRecommendation 객체 생성
        recommendations = []
        for strategy in strategies:
            strategy_type_map = {
                "보수적": StrategyType.CONSERVATIVE,
                "균형적": StrategyType.BALANCED,
                "공격적": StrategyType.AGGRESSIVE,
            }
            recommendations.append(
                BidRecommendation(
                    strategy_type=strategy_type_map[strategy.name],
                    bid_price=strategy.bid_price,
                    bid_rate=strategy.bid_ratio,
                    win_probability=strategy.win_probability,
                    expected_profit=strategy.expected_profit,
                    expected_roi=strategy.expected_roi,
                    rationale=strategy.recommendation,
                )
            )

        # 5. 비용 분석
        cost_breakdown = self._create_cost_breakdown(
            recommended.bid_price, rights_analysis, risk_analysis, user_settings
        )

        # 6. 수익 분석 (3가지 시나리오)
        profit_analysis = self._create_profit_analysis(
            strategies, valuation["estimated_market_price"]
        )

        # 7. 낙찰 확률 분석
        win_probability_by_rate = self._calculate_win_probability_by_rate(
            appraisal_value,
            valuation["estimated_market_price"],
            self.competition_predictor.predict(
                {
                    "bid_ratio": valuation.get("minimum_bid", 0) / appraisal_value if appraisal_value > 0 else 0.8,
                    "auction_count": valuation.get("auction_count", 1),
                }
            ),
        )

        # 8. 최종 추천 및 주의사항
        final_recommendation = self._generate_final_recommendation(
            recommended, fallback_strategies[0] if fallback_strategies else None
        )
        cautions = self._generate_cautions(
            recommended, rights_analysis, risk_analysis
        )

        # 9. 이번 회차 입찰 여부 판단
        should_bid, wait_reason = self._should_bid_this_round(
            recommended, valuation, fallback_strategies
        )

        return BidStrategyResult(
            case_number=case_number,
            optimal_bid=recommended.bid_price,
            optimal_bid_rate=recommended.bid_ratio,
            recommendations=recommendations,
            cost_breakdown=cost_breakdown,
            profit_analysis=profit_analysis,
            win_probability_by_rate=win_probability_by_rate,
            expected_competitors=self.competition_predictor.predict(
                {"bid_ratio": 0.8, "auction_count": 1}
            )["predicted_bidders"],
            competition_intensity=self.competition_predictor.predict(
                {"bid_ratio": 0.8, "auction_count": 1}
            )["intensity"],
            final_recommendation=final_recommendation,
            cautions=cautions,
            should_bid_this_round=should_bid,
            wait_reason=wait_reason,
        )

    def _select_recommended_strategy(
        self, strategies: List[BidStrategy], risk_grade: str, user_settings: Dict
    ) -> BidStrategy:
        """최적 전략 선정"""

        user_risk_tolerance = user_settings.get("risk_tolerance", "balanced")

        if user_risk_tolerance == "conservative":
            return strategies[0]  # 보수적
        elif user_risk_tolerance == "aggressive":
            return strategies[2]  # 공격적
        else:
            # 균형적 기본, 위험등급에 따라 조정
            if risk_grade in ["C", "D"]:
                return strategies[0]  # 위험 물건은 보수적
            return strategies[1]  # 균형적

    def _create_cost_breakdown(
        self,
        bid_price: int,
        rights_analysis: Dict,
        risk_analysis: Dict,
        user_settings: Dict,
    ) -> CostBreakdown:
        """비용 내역 생성"""

        costs = self.cost_calculator.calculate(
            bid_price, rights_analysis, risk_analysis, user_settings
        )

        return CostBreakdown(
            acquisition_tax=costs.acquisition_tax,
            registration_tax=costs.registration_fee,
            judicial_fee=costs.misc_cost,
            brokerage_fee=costs.brokerage_fee,
            assumed_amount=costs.assumed_amount,
            assumed_deposit=0,
            eviction_cost=costs.moving_cost,
            renovation_cost=costs.renovation_cost,
            holding_cost=0,
        )

    def _create_profit_analysis(
        self, strategies: List[BidStrategy], estimated_market_price: int
    ) -> List[ProfitAnalysis]:
        """수익 분석 생성 (3가지 전략별)"""

        analyses = []
        scenario_names = ["보수적", "균형적", "공격적"]

        for strategy, scenario_name in zip(strategies, scenario_names):
            gross_profit = estimated_market_price - strategy.bid_price
            net_profit = strategy.expected_profit
            roi_percent = strategy.expected_roi * 100

            analyses.append(
                ProfitAnalysis(
                    bid_price=strategy.bid_price,
                    total_investment=strategy.total_investment,
                    expected_sale_price=estimated_market_price,
                    gross_profit=gross_profit,
                    net_profit=net_profit,
                    roi_percent=roi_percent,
                    break_even_price=strategy.total_investment,
                    scenario=scenario_name,
                )
            )

        return analyses

    def _calculate_win_probability_by_rate(
        self, appraisal_value: int, estimated_market_price: int, competition: Dict
    ) -> Dict[float, float]:
        """입찰율별 낙찰 확률 계산"""

        probabilities = {}
        for rate in [0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9]:
            bid_price = int(appraisal_value * rate)
            prob_result = self.probability_calculator.calculate(
                bid_price, appraisal_value, competition
            )
            probabilities[rate] = prob_result["probability"]

        return probabilities

    def _generate_final_recommendation(
        self,
        recommended_strategy: BidStrategy,
        first_fallback: Optional[FallbackStrategy],
    ) -> str:
        """최종 추천 생성"""

        recommendation = f"""
## 최종 추천: {recommended_strategy.name} 전략

**입찰가**: {recommended_strategy.bid_price:,}원 (감정가 대비 {recommended_strategy.bid_ratio*100:.1f}%)
**예상 수익률**: {recommended_strategy.expected_roi*100:.1f}%
**낙찰 확률**: {recommended_strategy.win_probability*100:.1f}%
**위험 수준**: {recommended_strategy.risk_level}

{recommended_strategy.recommendation}
"""

        if first_fallback and first_fallback.action == "관망 추천":
            recommendation += f"\n\n**참고**: 현재 회차({first_fallback.round_number}회차) 최저입찰가가 높아 유찰 가능성이 있습니다. {first_fallback.round_number + 1}회차 이후 입찰을 고려하는 것도 전략적 선택이 될 수 있습니다."

        return recommendation.strip()

    def _generate_cautions(
        self,
        recommended_strategy: BidStrategy,
        rights_analysis: Dict,
        risk_analysis: Dict,
    ) -> List[str]:
        """주의사항 생성"""

        cautions = []

        # 수익률 위험
        if recommended_strategy.expected_roi < 0:
            cautions.append(
                f"⚠️ 예상 수익률이 음수({recommended_strategy.expected_roi*100:.1f}%)입니다. 현재 시세 기준으로 손실이 예상됩니다."
            )
        elif recommended_strategy.expected_roi < 0.05:
            cautions.append(
                "⚠️ 예상 수익률이 5% 미만으로 낮습니다. 시세 하락 시 손실 위험이 있습니다."
            )

        # 낙찰 확률 위험
        if recommended_strategy.win_probability < 0.3:
            cautions.append(
                f"⚠️ 낙찰 확률이 {recommended_strategy.win_probability*100:.1f}%로 낮습니다. 유찰 가능성이 높습니다."
            )

        # 인수금액 위험
        assumed_amount = rights_analysis.get("total_assumed_amount", 0)
        if assumed_amount > recommended_strategy.bid_price * 0.3:
            cautions.append(
                f"⚠️ 인수금액({assumed_amount:,}원)이 입찰가의 30% 이상입니다. 초기 투자금이 크므로 자금 계획 주의가 필요합니다."
            )

        # 명도 위험
        eviction_difficulty = risk_analysis.get("eviction_difficulty", "LOW")
        if eviction_difficulty in ["HIGH", "CRITICAL"]:
            cautions.append(
                f"⚠️ 명도 난이도가 '{eviction_difficulty}'로 높습니다. 명도 기간이 길어지고 비용이 증가할 수 있습니다."
            )

        # 위험등급 위험
        risk_grade = risk_analysis.get("risk_grade", "B")
        if risk_grade in ["C", "D"]:
            cautions.append(
                f"⚠️ 위험등급이 '{risk_grade}'입니다. 법적 문제나 하자가 있을 수 있으므로 전문가 자문을 권장합니다."
            )

        if not cautions:
            cautions.append("✅ 현재 분석 기준으로 특별한 주의사항이 없습니다.")

        return cautions

    def _should_bid_this_round(
        self,
        recommended_strategy: BidStrategy,
        valuation: Dict,
        fallback_strategies: List[FallbackStrategy],
    ) -> tuple[bool, Optional[str]]:
        """이번 회차 입찰 여부 판단"""

        # 수익률이 음수면 대기 권장
        if recommended_strategy.expected_roi < 0:
            return False, "예상 수익률이 음수이므로 유찰 후 재검토를 권장합니다."

        # 유찰 대응 전략에서 관망 추천이면 대기
        if fallback_strategies and fallback_strategies[0].action == "관망 추천":
            return (
                False,
                f"현재 회차 최저입찰가가 높아 {fallback_strategies[0].round_number + 1}회차 이후 입찰을 권장합니다.",
            )

        # 낙찰 확률이 너무 낮으면 대기 고려
        if recommended_strategy.win_probability < 0.1:
            return False, "낙찰 확률이 10% 미만으로 매우 낮아 유찰 후 재입찰을 권장합니다."

        return True, None

    def generate_markdown_report(
        self,
        result: BidStrategyResult,
        property_info: Optional[Dict] = None,
    ) -> str:
        """마크다운 리포트 생성"""

        report = f"""# 입찰 전략 리포트

## 기본 정보
- **사건번호**: {result.case_number}
"""

        if property_info:
            report += f"""- **소재지**: {property_info.get('address', 'N/A')}
- **분석일**: {property_info.get('analysis_date', 'N/A')}
"""

        report += f"""
---

## 핵심 수치

| 항목 | 금액/비율 |
|------|-----------|
| 최적 입찰가 | {result.optimal_bid:,}원 |
| 최적 입찰율 | {result.optimal_bid_rate*100:.1f}% |
| 예상 경쟁자 | {result.expected_competitors}명 |
| 경쟁 강도 | {result.competition_intensity} |

---

## 추천 전략

{result.final_recommendation}

---

## 전략별 비교

| 전략 | 입찰가 | 입찰율 | 수익률 | 낙찰확률 | 위험도 |
|------|--------|--------|--------|----------|--------|
"""

        for rec in result.recommendations:
            marker = "✓" if rec.bid_price == result.optimal_bid else ""
            report += f"| {rec.strategy_type.value} {marker} | {rec.bid_price:,} | {rec.bid_rate*100:.1f}% | {rec.expected_roi*100:.1f}% | {rec.win_probability*100:.1f}% | - |\n"

        report += f"""
---

## 비용 내역

| 항목 | 금액 |
|------|------|
| 취득세 | {result.cost_breakdown.acquisition_tax:,}원 |
| 등록세 | {result.cost_breakdown.registration_tax:,}원 |
| 법무사비 | {result.cost_breakdown.judicial_fee:,}원 |
| 인수금액 | {result.cost_breakdown.assumed_amount:,}원 |
| 명도비용 | {result.cost_breakdown.eviction_cost:,}원 |
| 수리비 | {result.cost_breakdown.renovation_cost:,}원 |
| **총 부대비용** | **{result.cost_breakdown.total_cost:,}원** |

---

## 수익 분석

"""
        for pa in result.profit_analysis:
            report += f"""### {pa.scenario} 시나리오
- 입찰가: {pa.bid_price:,}원
- 총 투자금: {pa.total_investment:,}원
- 예상 매도가: {pa.expected_sale_price:,}원
- 순수익: {pa.net_profit:,}원
- 수익률: {pa.roi_percent:.1f}%

"""

        report += f"""---

## 주의사항

"""
        for caution in result.cautions:
            report += f"{caution}\n"

        report += """
---

*본 리포트는 AI 분석 결과이며, 최종 투자 결정은 전문가 상담 후 진행하시기 바랍니다.*
"""

        return report
