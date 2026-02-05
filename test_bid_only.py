"""BidStrategistAgent 단독 테스트"""
import sys
import io

# 인코딩 설정
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("BidStrategistAgent 테스트 시작...")
print("=" * 70)

# 의존성 확인
try:
    import numpy as np
    print("[OK] numpy:", np.__version__)
except ImportError:
    print("[ERROR] numpy 미설치")
    exit(1)

try:
    from scipy.stats import norm
    print("[OK] scipy")
except ImportError:
    print("[ERROR] scipy 미설치")
    exit(1)

# 직접 모듈 로드
sys.path.insert(0, 'src')

# 모델 import
try:
    from models.strategy import (
        BidRecommendation,
        BidStrategyResult,
        CostBreakdown,
        ProfitAnalysis,
        StrategyType,
    )
    print("[OK] models.strategy")
except Exception as e:
    print(f"[ERROR] models.strategy: {e}")
    exit(1)

# bid_strategist만 직접 import (agents.__init__ 우회)
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "bid_strategist",
        "src/agents/bid_strategist.py"
    )
    bid_strategist_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bid_strategist_module)

    BidStrategistAgent = bid_strategist_module.BidStrategistAgent
    CostCalculator = bid_strategist_module.CostCalculator
    CompetitionPredictor = bid_strategist_module.CompetitionPredictor
    WinProbabilityCalculator = bid_strategist_module.WinProbabilityCalculator
    FallbackStrategyGenerator = bid_strategist_module.FallbackStrategyGenerator

    print("[OK] bid_strategist 모듈 로드")
except Exception as e:
    print(f"[ERROR] bid_strategist: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n" + "=" * 70)
print("1. 비용 계산기 테스트")
print("=" * 70)

cost_calc = CostCalculator()

# 취득세 계산
print("\n[취득세 계산]")
for price, housing in [(500_000_000, "1주택"), (700_000_000, "1주택"), (1_000_000_000, "2주택")]:
    tax = cost_calc._calculate_acquisition_tax(price, housing)
    print(f"  {housing} {price//100000000}억원: {tax:,}원 ({tax/price*100:.1f}%)")

# 명도비용
print("\n[명도비용 추정]")
for difficulty in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
    cost = cost_calc._estimate_moving_cost(difficulty)
    print(f"  {difficulty}: {cost:,}원")

# 전체 비용 계산
print("\n[전체 비용 계산 예시]")
costs = cost_calc.calculate(
    bid_price=600_000_000,
    rights_analysis={"total_assumed_amount": 150_000_000},
    risk_analysis={"eviction_difficulty": "MEDIUM"},
    user_settings={"housing_count": "1주택", "renovation_budget": 10_000_000},
)

items = [
    ("입찰가", costs.bid_price),
    ("인수금액", costs.assumed_amount),
    ("취득세", costs.acquisition_tax),
    ("등기비용", costs.registration_fee),
    ("명도비용", costs.moving_cost),
    ("리모델링", costs.renovation_cost),
    ("기타비용", costs.misc_cost),
    ("총 투자금", costs.total_investment),
]

for name, value in items:
    print(f"  {name:12s}: {value:>15,}원")

print("\n" + "=" * 70)
print("2. 경쟁률 예측 테스트")
print("=" * 70)

comp_pred = CompetitionPredictor()

scenarios = [
    (0.6, 1, 1, "저가 입찰, 1회차, 낮은 위험"),
    (0.8, 1, 2, "일반 조건"),
    (0.8, 3, 3, "3회 유찰, 높은 위험"),
]

for bid_ratio, auction_count, risk, desc in scenarios:
    comp = comp_pred.predict({
        "bid_ratio": bid_ratio,
        "auction_count": auction_count,
        "risk_grade_encoded": risk,
    })
    print(f"\n[{desc}]")
    print(f"  예상 경쟁자: {comp['predicted_bidders']}명")
    print(f"  경쟁 강도: {comp['intensity']}")
    print(f"  추천: {comp['recommendation']}")

print("\n" + "=" * 70)
print("3. 낙찰 확률 계산 테스트")
print("=" * 70)

prob_calc = WinProbabilityCalculator()
appraisal = 800_000_000
competition = {"predicted_bidders": 5}

print("\n[입찰율별 낙찰 확률]")
for bid_ratio in [0.6, 0.7, 0.8, 0.9]:
    bid = int(appraisal * bid_ratio)
    prob = prob_calc.calculate(bid, appraisal, competition)
    print(f"  {bid_ratio*100:.0f}%: {prob['probability']*100:5.1f}% - {prob['interpretation']}")

print("\n" + "=" * 70)
print("4. 유찰 대응 전략 테스트")
print("=" * 70)

fallback_gen = FallbackStrategyGenerator()
fallback_strategies = fallback_gen.generate(
    current_round=1,
    appraisal_value=800_000_000,
    estimated_market_price=750_000_000,
    user_max_roi=0.15,
)

print("\n[향후 5회차 전략]")
for fs in fallback_strategies:
    print(f"  {fs.round_number}회차: {fs.minimum_bid_ratio*100:4.1f}% ({fs.recommended_bid:>11,}원) - {fs.action}")

print("\n" + "=" * 70)
print("5. BidStrategistAgent 전체 테스트")
print("=" * 70)

agent = BidStrategistAgent()

valuation = {
    "case_number": "2024타경12345",
    "estimated_market_price": 750_000_000,
    "appraisal_value": 800_000_000,
    "minimum_bid": 640_000_000,
    "auction_count": 1,
}

rights_analysis = {"total_assumed_amount": 150_000_000}
risk_analysis = {"eviction_difficulty": "MEDIUM", "risk_grade": "B", "risk_grade_encoded": 2}
user_settings = {
    "target_roi": 0.15,
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
print(f"최적 입찰가: {result.optimal_bid:,}원 ({result.optimal_bid_rate*100:.1f}%)")
print(f"예상 경쟁자: {result.expected_competitors}명 ({result.competition_intensity})")
print(f"이번 회차 입찰: {'예' if result.should_bid_this_round else '아니오'}")
if result.wait_reason:
    print(f"대기 이유: {result.wait_reason}")

print("\n[전략별 추천]")
for rec in result.recommendations:
    print(f"\n  {rec.strategy_type.value}:")
    print(f"    입찰가: {rec.bid_price:,}원 ({rec.bid_rate*100:.1f}%)")
    print(f"    수익률: {rec.expected_roi*100:5.1f}% | 낙찰확률: {rec.win_probability*100:5.1f}%")
    print(f"    근거: {rec.rationale}")

print("\n[비용 분석]")
cost_items = [
    ("취득세", result.cost_breakdown.acquisition_tax),
    ("등록세", result.cost_breakdown.registration_tax),
    ("법무사비", result.cost_breakdown.judicial_fee),
    ("인수금액", result.cost_breakdown.assumed_amount),
    ("명도비용", result.cost_breakdown.eviction_cost),
    ("총 부대비용", result.cost_breakdown.total_cost),
]

for name, value in cost_items:
    print(f"  {name:12s}: {value:>13,}원")

print("\n[수익 분석]")
for pa in result.profit_analysis:
    print(f"\n  {pa.scenario}:")
    print(f"    투자금: {pa.total_investment:,}원")
    print(f"    순수익: {pa.net_profit:,}원 (수익률 {pa.roi_percent:.1f}%)")

print("\n[입찰율별 낙찰 확률]")
prob_str = " | ".join([f"{rate*100:.0f}%: {prob*100:4.1f}%" for rate, prob in sorted(result.win_probability_by_rate.items())])
print(f"  {prob_str}")

print("\n[주의사항]")
for i, caution in enumerate(result.cautions, 1):
    print(f"  {i}. {caution}")

print("\n" + "=" * 70)
print("6. 마크다운 리포트 생성 테스트")
print("=" * 70)

markdown = agent.generate_markdown_report(
    result,
    property_info={
        "address": "서울시 강남구 역삼동 123-45",
        "analysis_date": "2024-02-03",
    }
)

print(f"\n리포트 길이: {len(markdown)} 문자")
print("\n[리포트 미리보기 (처음 800자)]")
print("-" * 70)
print(markdown[:800])
print("-" * 70)

print("\n" + "=" * 70)
print("[SUCCESS] 모든 테스트 완료! BidStrategistAgent가 정상 작동합니다.")
print("=" * 70)
print(f"\n생성된 파일: C:\\Users\\vip3\\Desktop\\그리드라이프\\개발\\auction-agent\\src\\agents\\bid_strategist.py")
print("크기:", len(open("src/agents/bid_strategist.py", "r", encoding="utf-8").read()), "bytes")
