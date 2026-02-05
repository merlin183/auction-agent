"""직접 import 테스트"""
import sys
import os

# 모듈 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# 직접 파일에서 import (패키지 구조 우회)
import importlib.util

spec = importlib.util.spec_from_file_location(
    "bid_strategist",
    "src/agents/bid_strategist.py"
)
bid_strategist = importlib.util.module_from_spec(spec)

# 의존성 모듈 먼저 로드
spec_strategy = importlib.util.spec_from_file_location(
    "strategy",
    "src/models/strategy.py"
)
strategy_module = importlib.util.module_from_spec(spec_strategy)
spec_strategy.loader.exec_module(strategy_module)

# strategy 모듈을 sys.modules에 등록
sys.modules['models.strategy'] = strategy_module
sys.modules['src.models.strategy'] = strategy_module

# bid_strategist 로드
spec.loader.exec_module(bid_strategist)

# 클래스 가져오기
BidStrategistAgent = bid_strategist.BidStrategistAgent
CostCalculator = bid_strategist.CostCalculator
CompetitionPredictor = bid_strategist.CompetitionPredictor
WinProbabilityCalculator = bid_strategist.WinProbabilityCalculator

# 테스트 실행
print("=" * 80)
print("BidStrategistAgent 테스트")
print("=" * 80)

# 비용 계산기 테스트
print("\n1. 비용 계산기 테스트")
print("-" * 40)

cost_calc = CostCalculator()
costs = cost_calc.calculate(
    bid_price=600_000_000,
    rights_analysis={"total_assumed_amount": 150_000_000},
    risk_analysis={"eviction_difficulty": "MEDIUM"},
    user_settings={"housing_count": "1주택", "renovation_budget": 0},
)

print(f"입찰가: {costs.bid_price:,}원")
print(f"인수금액: {costs.assumed_amount:,}원")
print(f"취득세: {costs.acquisition_tax:,}원")
print(f"등기비용: {costs.registration_fee:,}원")
print(f"명도비용: {costs.moving_cost:,}원")
print(f"총 투자금: {costs.total_investment:,}원")
print("✅ 비용 계산 성공!")

# 경쟁률 예측 테스트
print("\n2. 경쟁률 예측 테스트")
print("-" * 40)

comp_pred = CompetitionPredictor()
competition = comp_pred.predict({
    "bid_ratio": 0.8,
    "auction_count": 1,
    "risk_grade_encoded": 2,
})

print(f"예상 경쟁자 수: {competition['predicted_bidders']}명")
print(f"경쟁 강도: {competition['intensity']}")
print(f"추천: {competition['recommendation']}")
print("✅ 경쟁률 예측 성공!")

# 낙찰 확률 테스트
print("\n3. 낙찰 확률 계산 테스트")
print("-" * 40)

prob_calc = WinProbabilityCalculator()
win_prob = prob_calc.calculate(
    my_bid=600_000_000,
    appraisal_value=800_000_000,
    competition=competition,
    auction_history=None,
)

print(f"낙찰 확률: {win_prob['probability']*100:.1f}%")
print(f"해석: {win_prob['interpretation']}")
print("✅ 낙찰 확률 계산 성공!")

# 전체 에이전트 테스트
print("\n4. BidStrategistAgent 전체 테스트")
print("-" * 40)

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

print(f"사건번호: {result.case_number}")
print(f"최적 입찰가: {result.optimal_bid:,}원")
print(f"최적 입찰율: {result.optimal_bid_rate*100:.1f}%")
print(f"예상 경쟁자: {result.expected_competitors}명")
print(f"경쟁 강도: {result.competition_intensity}")

print("\n전략별 추천:")
for rec in result.recommendations:
    print(f"  - {rec.strategy_type.value}: {rec.bid_price:,}원")
    print(f"    수익률: {rec.expected_roi*100:.1f}%, 낙찰확률: {rec.win_probability*100:.1f}%")

print("\n✅ 전체 에이전트 테스트 성공!")

# 마크다운 리포트 생성 테스트
print("\n5. 마크다운 리포트 생성 테스트")
print("-" * 40)

markdown = agent.generate_markdown_report(
    result,
    property_info={
        "address": "서울시 강남구 역삼동 123-45",
        "analysis_date": "2024-02-03",
    }
)

print(f"리포트 길이: {len(markdown)} 문자")
print("리포트 미리보기:")
print(markdown[:500] + "...")
print("\n✅ 마크다운 리포트 생성 성공!")

print("\n" + "=" * 80)
print("모든 테스트 완료! BidStrategistAgent가 정상적으로 작동합니다.")
print("=" * 80)
