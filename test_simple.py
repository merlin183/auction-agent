"""간단한 테스트 - numpy와 scipy 의존성 확인"""
import sys
import io

# 인코딩 설정
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("테스트 시작...")

# numpy 확인
try:
    import numpy as np
    print("[OK] numpy 설치됨:", np.__version__)
except ImportError:
    print("[ERROR] numpy 미설치")
    exit(1)

# scipy 확인
try:
    from scipy.stats import norm
    print("[OK] scipy 설치됨")
except ImportError:
    print("[ERROR] scipy 미설치")
    exit(1)

# 모델 import
sys.path.insert(0, 'src')

try:
    from models.strategy import (
        BidRecommendation,
        BidStrategyResult,
        CostBreakdown,
        ProfitAnalysis,
        StrategyType,
    )
    print("[OK] models.strategy import 성공")
except Exception as e:
    print(f"[ERROR] models.strategy import 실패: {e}")
    exit(1)

# bid_strategist import
try:
    from agents.bid_strategist import (
        BidStrategistAgent,
        CostCalculator,
        CompetitionPredictor,
        WinProbabilityCalculator,
    )
    print("[OK] agents.bid_strategist import 성공")
except Exception as e:
    print(f"[ERROR] agents.bid_strategist import 실패: {e}")
    exit(1)

# 간단한 실행 테스트
print("\n" + "=" * 60)
print("비용 계산기 테스트")
print("=" * 60)

cost_calc = CostCalculator()

# 취득세 계산 테스트
tax_1 = cost_calc._calculate_acquisition_tax(500_000_000, "1주택")
print(f"1주택 5억원 취득세: {tax_1:,}원 (1%)")

tax_2 = cost_calc._calculate_acquisition_tax(700_000_000, "1주택")
print(f"1주택 7억원 취득세: {tax_2:,}원 (2%)")

tax_3 = cost_calc._calculate_acquisition_tax(1_000_000_000, "1주택")
print(f"1주택 10억원 취득세: {tax_3:,}원 (3%)")

# 명도비용 추정 테스트
moving_low = cost_calc._estimate_moving_cost("LOW")
moving_high = cost_calc._estimate_moving_cost("HIGH")
print(f"\n명도비용 LOW: {moving_low:,}원")
print(f"명도비용 HIGH: {moving_high:,}원")

# 전체 비용 계산
costs = cost_calc.calculate(
    bid_price=600_000_000,
    rights_analysis={"total_assumed_amount": 150_000_000},
    risk_analysis={"eviction_difficulty": "MEDIUM"},
    user_settings={"housing_count": "1주택", "renovation_budget": 10_000_000},
)

print(f"\n입찰가: {costs.bid_price:,}원")
print(f"인수금액: {costs.assumed_amount:,}원")
print(f"취득세: {costs.acquisition_tax:,}원")
print(f"등기비용: {costs.registration_fee:,}원")
print(f"명도비용: {costs.moving_cost:,}원")
print(f"리모델링: {costs.renovation_cost:,}원")
print(f"기타비용: {costs.misc_cost:,}원")
print(f"총 투자금: {costs.total_investment:,}원")

# 경쟁률 예측 테스트
print("\n" + "=" * 60)
print("경쟁률 예측 테스트")
print("=" * 60)

comp_pred = CompetitionPredictor()

# 다양한 조건으로 테스트
test_cases = [
    {"bid_ratio": 0.6, "auction_count": 1, "risk_grade_encoded": 1, "desc": "낮은 입찰가율, 1회차"},
    {"bid_ratio": 0.8, "auction_count": 1, "risk_grade_encoded": 2, "desc": "일반 조건"},
    {"bid_ratio": 0.8, "auction_count": 3, "risk_grade_encoded": 3, "desc": "3회 유찰, 위험"},
]

for tc in test_cases:
    comp = comp_pred.predict(tc)
    print(f"\n{tc['desc']}:")
    print(f"  - 예상 경쟁자: {comp['predicted_bidders']}명")
    print(f"  - 경쟁 강도: {comp['intensity']}")

# 낙찰 확률 테스트
print("\n" + "=" * 60)
print("낙찰 확률 계산 테스트")
print("=" * 60)

prob_calc = WinProbabilityCalculator()

# 다양한 입찰가로 테스트
appraisal = 800_000_000
competition = {"predicted_bidders": 5}

for bid_ratio in [0.6, 0.7, 0.8, 0.9]:
    bid = int(appraisal * bid_ratio)
    prob = prob_calc.calculate(bid, appraisal, competition)
    print(f"\n입찰율 {bid_ratio*100:.0f}%:")
    print(f"  - 낙찰 확률: {prob['probability']*100:.1f}%")
    print(f"  - 해석: {prob['interpretation']}")

# BidStrategistAgent 테스트
print("\n" + "=" * 60)
print("BidStrategistAgent 전체 테스트")
print("=" * 60)

agent = BidStrategistAgent()

valuation = {
    "case_number": "2024타경12345",
    "estimated_market_price": 750_000_000,  # 7.5억
    "appraisal_value": 800_000_000,  # 8억
    "minimum_bid": 640_000_000,  # 6.4억
    "auction_count": 1,
}

rights_analysis = {
    "total_assumed_amount": 150_000_000,  # 1.5억
}

risk_analysis = {
    "eviction_difficulty": "MEDIUM",
    "risk_grade": "B",
    "risk_grade_encoded": 2,
}

user_settings = {
    "target_roi": 0.15,  # 15%
    "housing_count": "1주택",
    "renovation_budget": 0,
    "risk_tolerance": "balanced",
}

result = agent.generate_strategy(
    valuation=valuation,
    rights_analysis=rights_analysis,
    risk_analysis=risk_analysis,
    user_settings=user_settings,
)

print(f"\n사건번호: {result.case_number}")
print(f"최적 입찰가: {result.optimal_bid:,}원")
print(f"최적 입찰율: {result.optimal_bid_rate*100:.1f}%")
print(f"예상 경쟁자: {result.expected_competitors}명")
print(f"경쟁 강도: {result.competition_intensity}")
print(f"이번 회차 입찰: {result.should_bid_this_round}")

print("\n전략별 추천:")
for rec in result.recommendations:
    print(f"\n  {rec.strategy_type.value}:")
    print(f"    - 입찰가: {rec.bid_price:,}원 ({rec.bid_rate*100:.1f}%)")
    print(f"    - 예상 수익률: {rec.expected_roi*100:.1f}%")
    print(f"    - 낙찰 확률: {rec.win_probability*100:.1f}%")
    print(f"    - 근거: {rec.rationale}")

print("\n비용 분석:")
print(f"  - 취득세: {result.cost_breakdown.acquisition_tax:,}원")
print(f"  - 등록세: {result.cost_breakdown.registration_tax:,}원")
print(f"  - 인수금액: {result.cost_breakdown.assumed_amount:,}원")
print(f"  - 명도비용: {result.cost_breakdown.eviction_cost:,}원")
print(f"  - 총 비용: {result.cost_breakdown.total_cost:,}원")

print("\n수익 분석:")
for pa in result.profit_analysis:
    print(f"\n  {pa.scenario}:")
    print(f"    - 총 투자금: {pa.total_investment:,}원")
    print(f"    - 순수익: {pa.net_profit:,}원")
    print(f"    - 수익률: {pa.roi_percent:.1f}%")

print("\n주의사항:")
for i, caution in enumerate(result.cautions, 1):
    print(f"  {i}. {caution}")

print("\n" + "=" * 60)
print("[SUCCESS] 모든 테스트 성공! BidStrategistAgent 정상 작동")
print("=" * 60)
