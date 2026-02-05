"""입찰전략 에이전트 독립 테스트"""
import sys
sys.path.insert(0, 'src')

from agents.bid_strategist import (
    BidStrategistAgent,
    CostCalculator,
    CompetitionPredictor,
    WinProbabilityCalculator,
    OptimalBidCalculator,
    FallbackStrategyGenerator,
)

# 테스트 1: 비용 계산기
print("=" * 80)
print("테스트 1: 비용 계산기")
print("=" * 80)

cost_calc = CostCalculator()

rights_analysis = {"total_assumed_amount": 150_000_000}
risk_analysis = {"eviction_difficulty": "MEDIUM"}
user_settings = {"housing_count": "1주택", "renovation_budget": 0}

costs = cost_calc.calculate(
    bid_price=600_000_000,
    rights_analysis=rights_analysis,
    risk_analysis=risk_analysis,
    user_settings=user_settings,
)

print(f"입찰가: {costs.bid_price:,}원")
print(f"인수금액: {costs.assumed_amount:,}원")
print(f"취득세: {costs.acquisition_tax:,}원")
print(f"등기비용: {costs.registration_fee:,}원")
print(f"명도비용: {costs.moving_cost:,}원")
print(f"총 투자금: {costs.total_investment:,}원")

# 테스트 2: 경쟁률 예측
print("\n" + "=" * 80)
print("테스트 2: 경쟁률 예측")
print("=" * 80)

comp_pred = CompetitionPredictor()
competition = comp_pred.predict(
    {
        "bid_ratio": 0.8,
        "auction_count": 1,
        "risk_grade_encoded": 2,
    }
)

print(f"예상 경쟁자 수: {competition['predicted_bidders']}명")
print(f"경쟁 강도: {competition['intensity']}")
print(f"추천: {competition['recommendation']}")

# 테스트 3: 낙찰 확률 계산
print("\n" + "=" * 80)
print("테스트 3: 낙찰 확률 계산")
print("=" * 80)

prob_calc = WinProbabilityCalculator()
win_prob = prob_calc.calculate(
    my_bid=600_000_000,
    appraisal_value=800_000_000,
    competition=competition,
    auction_history=None,
)

print(f"낙찰 확률: {win_prob['probability']*100:.1f}%")
print(f"해석: {win_prob['interpretation']}")
print(f"신뢰도: {win_prob['confidence']}")

# 테스트 4: 유찰 대응 전략
print("\n" + "=" * 80)
print("테스트 4: 유찰 대응 전략")
print("=" * 80)

fallback_gen = FallbackStrategyGenerator()
fallback_strategies = fallback_gen.generate(
    current_round=1,
    appraisal_value=800_000_000,
    estimated_market_price=750_000_000,
    user_max_roi=0.15,
)

for fs in fallback_strategies[:3]:
    print(f"\n{fs.round_number}회차:")
    print(f"  - 최저입찰가율: {fs.minimum_bid_ratio*100:.1f}%")
    print(f"  - 최저입찰가: {fs.recommended_bid:,}원")
    print(f"  - 추천 행동: {fs.action}")
    print(f"  - 예상 경쟁: {fs.expected_competition}")

# 테스트 5: 최적 입찰가 계산기
print("\n" + "=" * 80)
print("테스트 5: 최적 입찰가 계산 (3가지 전략)")
print("=" * 80)

optimal_calc = OptimalBidCalculator(cost_calc, prob_calc, comp_pred)

valuation = {
    "estimated_market_price": 750_000_000,
    "appraisal_value": 800_000_000,
    "minimum_bid": 640_000_000,
    "auction_count": 1,
}

strategies = optimal_calc.calculate_optimal_bid(
    valuation=valuation,
    rights_analysis=rights_analysis,
    risk_analysis=risk_analysis,
    user_settings=user_settings,
)

for strategy in strategies:
    print(f"\n{strategy.name} 전략:")
    print(f"  - 입찰가: {strategy.bid_price:,}원")
    print(f"  - 낙찰가율: {strategy.bid_ratio*100:.1f}%")
    print(f"  - 예상 수익률: {strategy.expected_roi*100:.1f}%")
    print(f"  - 낙찰 확률: {strategy.win_probability*100:.1f}%")
    print(f"  - 위험 수준: {strategy.risk_level}")
    print(f"  - 총 투자금: {strategy.total_investment:,}원")
    print(f"  - 예상 수익: {strategy.expected_profit:,}원")
    print(f"  - 추천: {strategy.recommendation}")

# 테스트 6: 전체 에이전트 실행
print("\n" + "=" * 80)
print("테스트 6: BidStrategistAgent 전체 실행")
print("=" * 80)

agent = BidStrategistAgent()

valuation_full = {
    "case_number": "2024타경12345",
    "estimated_market_price": 750_000_000,
    "appraisal_value": 800_000_000,
    "minimum_bid": 640_000_000,
    "auction_count": 1,
}

user_settings_full = {
    "target_roi": 0.15,
    "housing_count": "1주택",
    "renovation_budget": 0,
    "risk_tolerance": "balanced",
}

result = agent.generate_strategy(
    valuation=valuation_full,
    rights_analysis=rights_analysis,
    risk_analysis=risk_analysis,
    user_settings=user_settings_full,
)

print(f"\n사건번호: {result.case_number}")
print(f"최적 입찰가: {result.optimal_bid:,}원")
print(f"최적 입찰율: {result.optimal_bid_rate*100:.1f}%")
print(f"예상 경쟁자: {result.expected_competitors}명")
print(f"경쟁 강도: {result.competition_intensity}")
print(f"이번 회차 입찰 여부: {result.should_bid_this_round}")

print("\n전략별 추천:")
for rec in result.recommendations:
    print(f"  - {rec.strategy_type.value}: {rec.bid_price:,}원 (수익률 {rec.expected_roi*100:.1f}%, 낙찰확률 {rec.win_probability*100:.1f}%)")

print("\n비용 내역:")
print(f"  - 취득세: {result.cost_breakdown.acquisition_tax:,}원")
print(f"  - 등록세: {result.cost_breakdown.registration_tax:,}원")
print(f"  - 인수금액: {result.cost_breakdown.assumed_amount:,}원")
print(f"  - 명도비용: {result.cost_breakdown.eviction_cost:,}원")
print(f"  - 총 부대비용: {result.cost_breakdown.total_cost:,}원")

print("\n주의사항:")
for caution in result.cautions:
    print(f"  - {caution}")

print("\n" + "=" * 80)
print("모든 테스트 완료!")
print("=" * 80)
