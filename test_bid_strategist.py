"""입찰전략 에이전트 테스트"""
from src.agents.bid_strategist import BidStrategistAgent

# 테스트 데이터
valuation = {
    "case_number": "2024타경12345",
    "estimated_market_price": 750_000_000,  # 7.5억
    "appraisal_value": 800_000_000,  # 8억
    "minimum_bid": 640_000_000,  # 6.4억 (80%)
    "auction_count": 1,
    "region_encoded": 0,
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
    "target_roi": 0.15,  # 15% 목표
    "housing_count": "1주택",
    "renovation_budget": 0,
    "risk_tolerance": "balanced",
}

# 에이전트 실행
agent = BidStrategistAgent()
result = agent.generate_strategy(
    valuation=valuation,
    rights_analysis=rights_analysis,
    risk_analysis=risk_analysis,
    user_settings=user_settings,
)

# 결과 출력
print("=" * 80)
print("입찰 전략 분석 결과")
print("=" * 80)
print(f"\n사건번호: {result.case_number}")
print(f"최적 입찰가: {result.optimal_bid:,}원")
print(f"최적 입찰율: {result.optimal_bid_rate*100:.1f}%")
print(f"\n예상 경쟁자: {result.expected_competitors}명")
print(f"경쟁 강도: {result.competition_intensity}")

print("\n" + "=" * 80)
print("전략별 추천")
print("=" * 80)
for rec in result.recommendations:
    print(f"\n{rec.strategy_type.value} 전략:")
    print(f"  - 입찰가: {rec.bid_price:,}원")
    print(f"  - 입찰율: {rec.bid_rate*100:.1f}%")
    print(f"  - 예상 수익률: {rec.expected_roi*100:.1f}%")
    print(f"  - 낙찰 확률: {rec.win_probability*100:.1f}%")
    print(f"  - 근거: {rec.rationale}")

print("\n" + "=" * 80)
print("비용 내역")
print("=" * 80)
print(f"취득세: {result.cost_breakdown.acquisition_tax:,}원")
print(f"등록세: {result.cost_breakdown.registration_tax:,}원")
print(f"법무사비: {result.cost_breakdown.judicial_fee:,}원")
print(f"인수금액: {result.cost_breakdown.assumed_amount:,}원")
print(f"명도비용: {result.cost_breakdown.eviction_cost:,}원")
print(f"총 부대비용: {result.cost_breakdown.total_cost:,}원")

print("\n" + "=" * 80)
print("수익 분석")
print("=" * 80)
for pa in result.profit_analysis:
    print(f"\n{pa.scenario} 시나리오:")
    print(f"  - 입찰가: {pa.bid_price:,}원")
    print(f"  - 총 투자금: {pa.total_investment:,}원")
    print(f"  - 예상 매도가: {pa.expected_sale_price:,}원")
    print(f"  - 순수익: {pa.net_profit:,}원")
    print(f"  - 수익률: {pa.roi_percent:.1f}%")

print("\n" + "=" * 80)
print("입찰율별 낙찰 확률")
print("=" * 80)
for rate, prob in result.win_probability_by_rate.items():
    print(f"{rate*100:.0f}%: {prob*100:.1f}%")

print("\n" + "=" * 80)
print("최종 추천")
print("=" * 80)
print(result.final_recommendation)

print("\n" + "=" * 80)
print("주의사항")
print("=" * 80)
for caution in result.cautions:
    print(f"- {caution}")

print("\n" + "=" * 80)
print(f"이번 회차 입찰 여부: {result.should_bid_this_round}")
if result.wait_reason:
    print(f"대기 이유: {result.wait_reason}")
print("=" * 80)

# 마크다운 리포트 생성
print("\n\n")
print("=" * 80)
print("마크다운 리포트")
print("=" * 80)
markdown_report = agent.generate_markdown_report(
    result,
    property_info={
        "address": "서울시 강남구 역삼동 123-45",
        "analysis_date": "2024-02-03",
    },
)
print(markdown_report)
