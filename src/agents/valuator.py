"""가치평가 에이전트 (Valuator Agent)

경매 물건의 시세를 추정하고, 낙찰가를 예측하며, 투자 수익률을 분석하는 AI 에이전트.
"""

from datetime import date, datetime
from typing import Any, Optional

import numpy as np
import pandas as pd
import xgboost as xgb
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from ..models.valuation import (
    ComparableSale,
    PriceEstimate,
    PriceTrend,
    ROIScenario,
    ValuationResult,
)
from ..services.llm import get_llm_client
from ..utils.logger import AgentLogger


class PropertyFeatures(BaseModel):
    """물건 특성 피처"""

    area_sqm: float
    building_age: int
    floor: int
    total_floors: int
    is_royal_floor: bool  # 5-15층 선호층
    room_count: int
    parking_ratio: float

    # 위치 특성
    dist_subway_m: float
    dist_school_m: float
    dist_mart_m: float
    accessibility_score: float

    # 시장 특성
    avg_transaction_price: float
    transaction_count_12m: int
    price_volatility: float

    # 경매 특성
    auction_count: int = 0
    appraisal_value: int = 0


class MarketData(BaseModel):
    """시장 데이터"""

    recent_transactions: list[dict] = Field(default_factory=list)
    auction_history: list[dict] = Field(default_factory=list)
    location_info: dict = Field(default_factory=dict)
    macro_indicators: dict = Field(default_factory=dict)


class ValuatorAgent:
    """가치평가 에이전트

    시세 추정, 낙찰가 예측, ROI 시뮬레이션을 수행하는 전문 에이전트.
    """

    def __init__(
        self,
        use_ml_models: bool = False,
        model_path: Optional[str] = None,
    ):
        """초기화

        Args:
            use_ml_models: ML 모델 사용 여부 (False면 휴리스틱 방식)
            model_path: 학습된 모델 경로
        """
        self.logger = AgentLogger("ValuatorAgent")
        self.llm = get_llm_client(temperature=0.0)
        self.use_ml_models = use_ml_models

        # ML 모델 (학습 후 로드)
        self.market_price_model: Optional[xgb.XGBRegressor] = None
        self.bid_ratio_model: Optional[xgb.XGBRegressor] = None

        if use_ml_models and model_path:
            self._load_models(model_path)

    def _load_models(self, model_path: str) -> None:
        """학습된 모델 로드"""
        try:
            import joblib

            self.market_price_model = joblib.load(f"{model_path}/market_price_model.pkl")
            self.bid_ratio_model = joblib.load(f"{model_path}/bid_ratio_model.pkl")
            self.logger.info("ML models loaded successfully", path=model_path)
        except Exception as e:
            self.logger.warning("Failed to load ML models, using heuristic methods", error=str(e))
            self.market_price_model = None
            self.bid_ratio_model = None

    async def valuate(
        self,
        case_number: str,
        property_info: dict,
        market_data: Optional[MarketData] = None,
        rights_analysis: Optional[dict] = None,
    ) -> ValuationResult:
        """가치평가 수행

        Args:
            case_number: 사건번호
            property_info: 물건 정보
            market_data: 수집된 시장 데이터
            rights_analysis: 권리분석 결과

        Returns:
            ValuationResult: 가치평가 결과
        """
        self.logger.step("valuate_start", case_number=case_number)

        # 1. 시세 추정
        self.logger.step("estimate_market_price")
        estimated_price = await self._estimate_market_price(property_info, market_data)

        # 2. 비교 사례 분석
        self.logger.step("analyze_comparables")
        comparables = await self._find_comparable_sales(property_info, market_data)

        # 3. 가격 추세 분석
        self.logger.step("analyze_trend")
        price_trend, trend_rate = await self._analyze_price_trend(property_info, market_data)

        # 4. 낙찰가율 예측
        self.logger.step("predict_bid_rate")
        predicted_bid_rate, bid_rate_range = await self._predict_bid_rate(
            property_info, market_data
        )

        # 5. ROI 시뮬레이션
        self.logger.step("simulate_roi")
        roi_scenarios = await self._simulate_roi(
            property_info, estimated_price, predicted_bid_rate, rights_analysis
        )

        # 6. 평가 의견 생성
        self.logger.step("generate_opinion")
        summary, opinion = await self._generate_valuation_opinion(
            property_info, estimated_price, comparables, price_trend, roi_scenarios
        )

        # 평당가 계산
        area_pyung = property_info.get("area_sqm", 0) / 3.3058
        price_per_pyung = int(estimated_price.estimate / area_pyung) if area_pyung > 0 else 0

        result = ValuationResult(
            case_number=case_number,
            appraisal_value=property_info.get("appraisal_value", 0),
            appraisal_date=property_info.get("appraisal_date"),
            estimated_market_price=estimated_price,
            price_per_pyung=price_per_pyung,
            price_trend=price_trend,
            trend_rate_6m=trend_rate,
            comparables=comparables,
            comparables_avg_price=self._calculate_avg_price(comparables),
            comparables_median_price=self._calculate_median_price(comparables),
            predicted_bid_rate=predicted_bid_rate,
            predicted_bid_rate_range=bid_rate_range,
            roi_scenarios=roi_scenarios,
            summary=summary,
            price_opinion=opinion,
            model_confidence=estimated_price.confidence,
        )

        self.logger.result(
            "valuation_complete",
            estimated_price=estimated_price.estimate,
            bid_rate=predicted_bid_rate,
            gap=result.appraisal_vs_market_gap,
        )

        return result

    async def _estimate_market_price(
        self, property_info: dict, market_data: Optional[MarketData]
    ) -> PriceEstimate:
        """시세 추정

        비교사례 기반 시세 추정 (ML 모델 또는 휴리스틱)
        """
        if self.use_ml_models and self.market_price_model:
            return await self._estimate_with_ml(property_info, market_data)
        else:
            return await self._estimate_with_comparables(property_info, market_data)

    async def _estimate_with_comparables(
        self, property_info: dict, market_data: Optional[MarketData]
    ) -> PriceEstimate:
        """비교사례 기반 시세 추정 (휴리스틱)"""

        # 기본값 (감정가 기반)
        appraisal = property_info.get("appraisal_value", 0)
        if appraisal == 0:
            return PriceEstimate(
                lower_bound=0, estimate=0, upper_bound=0, confidence=0.0
            )

        # 시장 데이터가 있으면 비교 사례 활용
        if market_data and market_data.recent_transactions:
            comparable_prices = []
            target_area = property_info.get("area_sqm", 0)

            for tx in market_data.recent_transactions:
                tx_area = tx.get("area_sqm", 0)
                # 면적 유사성 (±20% 이내)
                if 0.8 <= (tx_area / target_area) <= 1.2:
                    price = tx.get("transaction_price", 0)
                    if price > 0:
                        comparable_prices.append(price)

            if comparable_prices:
                # 비교사례 평균 사용
                avg_price = np.mean(comparable_prices)
                std_price = np.std(comparable_prices)

                # 감정가와 시세 가중 평균
                weight_market = 0.7  # 시장 데이터 70%
                weight_appraisal = 0.3  # 감정가 30%

                estimate = int(avg_price * weight_market + appraisal * weight_appraisal)
                lower = int(estimate - std_price)
                upper = int(estimate + std_price)

                confidence = min(0.8, 0.5 + (len(comparable_prices) * 0.05))

                return PriceEstimate(
                    lower_bound=max(0, lower),
                    estimate=estimate,
                    upper_bound=upper,
                    confidence=confidence,
                )

        # 비교 사례 없으면 감정가 기준 (보수적 조정)
        # 일반적으로 감정가는 시세보다 5-10% 높게 책정되는 경향
        estimate = int(appraisal * 0.95)  # 5% 할인
        margin = int(estimate * 0.1)  # ±10% 신뢰구간

        return PriceEstimate(
            lower_bound=estimate - margin,
            estimate=estimate,
            upper_bound=estimate + margin,
            confidence=0.5,  # 낮은 신뢰도
        )

    async def _estimate_with_ml(
        self, property_info: dict, market_data: Optional[MarketData]
    ) -> PriceEstimate:
        """ML 모델 기반 시세 추정 (XGBoost placeholder)"""

        # 피처 생성
        features = self._create_features(property_info, market_data)
        X = pd.DataFrame([features.__dict__])

        # 예측
        prediction = self.market_price_model.predict(X)[0]

        # 신뢰구간 (간소화: ±5%)
        uncertainty = prediction * 0.05
        lower = int(prediction - uncertainty * 1.96)
        upper = int(prediction + uncertainty * 1.96)

        return PriceEstimate(
            lower_bound=lower,
            estimate=int(prediction),
            upper_bound=upper,
            confidence=0.85,
        )

    async def _find_comparable_sales(
        self, property_info: dict, market_data: Optional[MarketData]
    ) -> list[ComparableSale]:
        """유사 거래 사례 검색"""

        if not market_data or not market_data.recent_transactions:
            return []

        comparables = []
        target_area = property_info.get("area_sqm", 0)
        target_floor = property_info.get("floor", 0)
        target_building_year = property_info.get("building_year", 0)

        for tx in market_data.recent_transactions:
            # 유사도 계산
            similarity = self._calculate_similarity(
                property_info, tx, target_area, target_floor, target_building_year
            )

            if similarity >= 0.5:  # 유사도 50% 이상만
                price_per_sqm = int(
                    tx.get("transaction_price", 0) / tx.get("area_sqm", 1)
                )

                comparable = ComparableSale(
                    address=tx.get("address", ""),
                    transaction_date=tx.get("transaction_date", date.today()),
                    transaction_price=tx.get("transaction_price", 0),
                    area_sqm=tx.get("area_sqm", 0),
                    price_per_sqm=price_per_sqm,
                    floor=tx.get("floor"),
                    building_year=tx.get("building_year"),
                    distance_meters=tx.get("distance_meters"),
                    similarity_score=similarity,
                )
                comparables.append(comparable)

        # 유사도 순 정렬, 상위 10개
        comparables.sort(key=lambda x: x.similarity_score, reverse=True)
        return comparables[:10]

    def _calculate_similarity(
        self,
        target: dict,
        comparable: dict,
        target_area: float,
        target_floor: int,
        target_building_year: int,
    ) -> float:
        """유사도 계산 (0~1)"""

        similarity = 0.0

        # 1. 면적 유사도 (40%)
        comp_area = comparable.get("area_sqm", 0)
        if target_area > 0 and comp_area > 0:
            area_diff = abs(target_area - comp_area) / target_area
            area_sim = max(0, 1 - area_diff)
            similarity += area_sim * 0.4

        # 2. 층수 유사도 (20%)
        comp_floor = comparable.get("floor", 0)
        if target_floor > 0 and comp_floor > 0:
            floor_diff = abs(target_floor - comp_floor) / max(target_floor, comp_floor)
            floor_sim = max(0, 1 - floor_diff)
            similarity += floor_sim * 0.2

        # 3. 건축연도 유사도 (20%)
        comp_year = comparable.get("building_year", 0)
        if target_building_year > 0 and comp_year > 0:
            year_diff = abs(target_building_year - comp_year) / 50  # 50년 기준
            year_sim = max(0, 1 - year_diff)
            similarity += year_sim * 0.2

        # 4. 거리 유사도 (20%) - 가까울수록 높음
        distance = comparable.get("distance_meters", 1000)
        distance_sim = max(0, 1 - (distance / 2000))  # 2km 기준
        similarity += distance_sim * 0.2

        return min(1.0, similarity)

    async def _analyze_price_trend(
        self, property_info: dict, market_data: Optional[MarketData]
    ) -> tuple[PriceTrend, Optional[float]]:
        """가격 추세 분석"""

        if not market_data or not market_data.recent_transactions:
            return PriceTrend.STABLE, None

        # 시계열 데이터 생성
        df = pd.DataFrame(market_data.recent_transactions)
        if "transaction_date" not in df.columns or len(df) < 3:
            return PriceTrend.STABLE, None

        df["transaction_date"] = pd.to_datetime(df["transaction_date"])
        df = df.sort_values("transaction_date")

        # 최근 6개월 가격 변동률 계산
        six_months_ago = datetime.now() - pd.DateOffset(months=6)
        recent_df = df[df["transaction_date"] >= six_months_ago]

        if len(recent_df) < 2:
            return PriceTrend.STABLE, None

        # 평균 가격 변동률
        first_half = recent_df.head(len(recent_df) // 2)
        second_half = recent_df.tail(len(recent_df) // 2)

        avg_first = first_half["transaction_price"].mean()
        avg_second = second_half["transaction_price"].mean()

        if avg_first > 0:
            trend_rate = (avg_second - avg_first) / avg_first
        else:
            return PriceTrend.STABLE, None

        # 추세 판단
        if trend_rate > 0.03:  # 3% 이상 상승
            trend = PriceTrend.UPWARD
        elif trend_rate < -0.03:  # 3% 이상 하락
            trend = PriceTrend.DOWNWARD
        else:
            trend = PriceTrend.STABLE

        return trend, trend_rate

    async def _predict_bid_rate(
        self, property_info: dict, market_data: Optional[MarketData]
    ) -> tuple[float, tuple[float, float]]:
        """낙찰가율 예측"""

        if self.use_ml_models and self.bid_ratio_model:
            return await self._predict_bid_rate_with_ml(property_info, market_data)
        else:
            return await self._predict_bid_rate_heuristic(property_info, market_data)

    async def _predict_bid_rate_heuristic(
        self, property_info: dict, market_data: Optional[MarketData]
    ) -> tuple[float, tuple[float, float]]:
        """낙찰가율 휴리스틱 예측"""

        # 기본 낙찰가율 (지역/물건 유형별)
        base_rate = 0.7  # 70% 기본

        # 경매 이력 데이터가 있으면 활용
        if market_data and market_data.auction_history:
            recent_rates = [
                h.get("bid_ratio", 0.7)
                for h in market_data.auction_history
                if h.get("bid_ratio", 0) > 0
            ]

            if recent_rates:
                # 인근 경매 평균 낙찰가율
                avg_rate = np.mean(recent_rates)
                std_rate = np.std(recent_rates)

                # 유찰 횟수 조정
                auction_count = property_info.get("auction_count", 0)
                adjustment = -0.03 * auction_count  # 유찰당 3% 하락

                predicted_rate = avg_rate + adjustment
                lower = max(0.5, predicted_rate - std_rate)
                upper = min(1.0, predicted_rate + std_rate)

                return predicted_rate, (lower, upper)

        # 기본값 반환
        return base_rate, (0.65, 0.80)

    async def _predict_bid_rate_with_ml(
        self, property_info: dict, market_data: Optional[MarketData]
    ) -> tuple[float, tuple[float, float]]:
        """ML 기반 낙찰가율 예측"""

        features = self._create_features(property_info, market_data)
        X = pd.DataFrame([features.__dict__])

        predicted_rate = self.bid_ratio_model.predict(X)[0]
        predicted_rate = max(0.5, min(1.0, predicted_rate))  # 0.5~1.0 범위

        # 신뢰구간
        lower = max(0.5, predicted_rate - 0.05)
        upper = min(1.0, predicted_rate + 0.05)

        return predicted_rate, (lower, upper)

    async def _simulate_roi(
        self,
        property_info: dict,
        estimated_price: PriceEstimate,
        predicted_bid_rate: float,
        rights_analysis: Optional[dict],
    ) -> list[ROIScenario]:
        """ROI 시뮬레이션 (3가지 시나리오)"""

        appraisal = property_info.get("appraisal_value", 0)
        assumed_amount = 0
        if rights_analysis:
            assumed_amount = rights_analysis.get("total_assumed_amount", 0)

        scenarios = []

        # 시나리오별 낙찰가율과 매도가
        scenario_configs = [
            ("비관적", predicted_bid_rate - 0.05, 0.95),  # 5% 낮은 낙찰, 5% 하락
            ("중립적", predicted_bid_rate, 1.05),  # 예측 낙찰, 5% 상승
            ("낙관적", predicted_bid_rate + 0.05, 1.15),  # 5% 높은 낙찰, 15% 상승
        ]

        for scenario_name, bid_rate, price_multiplier in scenario_configs:
            bid_rate = max(0.5, min(1.0, bid_rate))  # 0.5~1.0 범위
            bid_price = int(appraisal * bid_rate)

            # 취득세 (4.6% - 주택 기준)
            acquisition_tax = int(bid_price * 0.046)
            registration_cost = 500_000  # 등기비용

            # 리모델링 비용 (평당 500만원 * 10% 가정)
            area_pyung = property_info.get("area_sqm", 0) / 3.3058
            renovation_cost = int(area_pyung * 500_000 * 0.1)

            # 총 투자금액
            total_investment = (
                bid_price + assumed_amount + acquisition_tax + registration_cost + renovation_cost
            )

            # 보유 기간 (12개월 가정)
            holding_months = 12
            monthly_expense = 100_000  # 월 관리비
            holding_cost = monthly_expense * holding_months

            # 매도가
            selling_price = int(estimated_price.estimate * price_multiplier)
            selling_cost = int(selling_price * 0.005)  # 중개수수료 0.5%

            # 수익 계산
            gross_profit = selling_price - bid_price
            net_profit = selling_price - total_investment - holding_cost - selling_cost

            # 수익률
            roi_percent = (net_profit / total_investment * 100) if total_investment > 0 else 0
            annualized_roi = roi_percent * (12 / holding_months)

            scenario = ROIScenario(
                scenario_name=scenario_name,
                bid_price=bid_price,
                bid_rate=bid_rate,
                selling_price=selling_price,
                holding_period_months=holding_months,
                acquisition_cost=acquisition_tax + registration_cost,
                holding_cost=holding_cost,
                selling_cost=selling_cost,
                renovation_cost=renovation_cost,
                gross_profit=gross_profit,
                net_profit=net_profit,
                roi_percent=round(roi_percent, 2),
                annualized_roi=round(annualized_roi, 2),
            )

            scenarios.append(scenario)

        return scenarios

    async def _generate_valuation_opinion(
        self,
        property_info: dict,
        estimated_price: PriceEstimate,
        comparables: list[ComparableSale],
        price_trend: PriceTrend,
        roi_scenarios: list[ROIScenario],
    ) -> tuple[str, str]:
        """LLM 기반 평가 의견 생성"""

        # 프롬프트 구성
        system_prompt = """당신은 부동산 경매 전문 감정평가사입니다.
물건의 시세 분석 결과를 바탕으로 간결하고 전문적인 평가 의견을 제시하세요.

출력 형식:
1. 요약 (1-2문장)
2. 가격 평가 의견 (3-5문장)"""

        appraisal = property_info.get("appraisal_value", 0)
        gap = ((appraisal - estimated_price.estimate) / estimated_price.estimate * 100) if estimated_price.estimate > 0 else 0

        comp_avg = self._calculate_avg_price(comparables)

        user_prompt = f"""
[물건 정보]
- 소재지: {property_info.get('address', '알 수 없음')}
- 면적: {property_info.get('area_sqm', 0):.2f}㎡
- 감정가: {appraisal:,}원

[시세 분석]
- 추정 시세: {estimated_price.estimate:,}원 (신뢰도: {estimated_price.confidence:.0%})
- 신뢰구간: {estimated_price.lower_bound:,}원 ~ {estimated_price.upper_bound:,}원
- 감정가 대비 괴리율: {gap:+.1f}%

[비교 사례]
- 유사 거래 {len(comparables)}건
- 평균 거래가: {comp_avg:,}원

[가격 추세]
- 추세: {price_trend.value}

[수익률 전망]
- 중립 시나리오 연 수익률: {roi_scenarios[1].annualized_roi if len(roi_scenarios) > 1 else 0:.1f}%

위 정보를 바탕으로 평가 의견을 작성하세요.
"""

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]

            response = await self.llm.ainvoke(messages)
            content = response.content

            # 요약과 의견 분리
            lines = content.strip().split("\n")
            summary_lines = []
            opinion_lines = []

            in_opinion = False
            for line in lines:
                line = line.strip()
                if not line:
                    continue

                if "의견" in line or "평가" in line:
                    in_opinion = True
                    continue

                if in_opinion:
                    opinion_lines.append(line)
                else:
                    summary_lines.append(line)

            summary = " ".join(summary_lines[:2]) if summary_lines else "시세 분석 완료"
            opinion = " ".join(opinion_lines) if opinion_lines else content

            return summary, opinion

        except Exception as e:
            self.logger.error("Failed to generate opinion", error=str(e))
            return (
                f"추정 시세 {estimated_price.estimate:,}원, 감정가 대비 {gap:+.1f}%",
                "시장 데이터를 기반으로 적정 시세를 산출하였습니다.",
            )

    def _create_features(
        self, property_info: dict, market_data: Optional[MarketData]
    ) -> PropertyFeatures:
        """ML 모델용 피처 생성"""

        area_sqm = property_info.get("area_sqm", 0)
        building_year = property_info.get("building_year", 2020)
        current_year = datetime.now().year
        building_age = current_year - building_year

        floor = property_info.get("floor", 1)
        total_floors = property_info.get("total_floors", 1)
        is_royal_floor = 5 <= floor <= 15

        # 시장 데이터 집계
        avg_price = 0.0
        transaction_count = 0
        volatility = 0.0

        if market_data and market_data.recent_transactions:
            prices = [t.get("transaction_price", 0) for t in market_data.recent_transactions]
            if prices:
                avg_price = np.mean(prices)
                volatility = np.std(prices) / avg_price if avg_price > 0 else 0
                transaction_count = len(prices)

        return PropertyFeatures(
            area_sqm=area_sqm,
            building_age=building_age,
            floor=floor,
            total_floors=total_floors,
            is_royal_floor=is_royal_floor,
            room_count=property_info.get("room_count", 3),
            parking_ratio=property_info.get("parking_ratio", 1.0),
            dist_subway_m=property_info.get("dist_subway_m", 1000),
            dist_school_m=property_info.get("dist_school_m", 500),
            dist_mart_m=property_info.get("dist_mart_m", 500),
            accessibility_score=property_info.get("accessibility_score", 70),
            avg_transaction_price=avg_price,
            transaction_count_12m=transaction_count,
            price_volatility=volatility,
            auction_count=property_info.get("auction_count", 0),
            appraisal_value=property_info.get("appraisal_value", 0),
        )

    def _calculate_avg_price(self, comparables: list[ComparableSale]) -> int:
        """비교 사례 평균 가격"""
        if not comparables:
            return 0
        prices = [c.transaction_price for c in comparables]
        return int(np.mean(prices))

    def _calculate_median_price(self, comparables: list[ComparableSale]) -> int:
        """비교 사례 중간 가격"""
        if not comparables:
            return 0
        prices = [c.transaction_price for c in comparables]
        return int(np.median(prices))


# 손익분기점 계산 유틸리티
def calculate_breakeven_price(
    bid_price: int, assumed_amount: int, acquisition_rate: float = 0.046
) -> dict:
    """손익분기점 계산

    Args:
        bid_price: 낙찰가
        assumed_amount: 인수금액
        acquisition_rate: 취득세율

    Returns:
        손익분기 매도가, 비율
    """
    acquisition_cost = int(bid_price * acquisition_rate) + 500_000  # 취득세 + 등기
    total_investment = bid_price + assumed_amount + acquisition_cost

    selling_cost_rate = 0.005  # 중개수수료 0.5%
    breakeven_price = int(total_investment / (1 - selling_cost_rate))

    return {
        "breakeven_selling_price": breakeven_price,
        "breakeven_ratio": breakeven_price / bid_price if bid_price > 0 else 0,
        "total_investment": total_investment,
    }


# 민감도 분석 유틸리티
def sensitivity_analysis(
    base_scenario: ROIScenario, variable: str, change_pct: float
) -> ROIScenario:
    """민감도 분석

    Args:
        base_scenario: 기준 시나리오
        variable: 변동 변수 (bid_price, selling_price 등)
        change_pct: 변동률 (0.1 = 10% 증가)

    Returns:
        조정된 시나리오
    """
    import copy

    scenario = copy.deepcopy(base_scenario)

    if variable == "bid_price":
        scenario.bid_price = int(scenario.bid_price * (1 + change_pct))
    elif variable == "selling_price":
        scenario.selling_price = int(scenario.selling_price * (1 + change_pct))

    # 수익률 재계산
    total_investment = (
        scenario.bid_price
        + scenario.acquisition_cost
        + scenario.renovation_cost
    )

    scenario.gross_profit = scenario.selling_price - scenario.bid_price
    scenario.net_profit = (
        scenario.selling_price
        - total_investment
        - scenario.holding_cost
        - scenario.selling_cost
    )

    if total_investment > 0:
        scenario.roi_percent = round(scenario.net_profit / total_investment * 100, 2)
        scenario.annualized_roi = round(
            scenario.roi_percent * (12 / scenario.holding_period_months), 2
        )

    return scenario
