# BidStrategistAgent 구현 완료

## 파일 위치
`C:\Users\vip3\Desktop\그리드라이프\개발\auction-agent\src\agents\bid_strategist.py`

## 구현 내용

### 1. 핵심 클래스

#### BidStrategistAgent
- 입찰전략 에이전트 메인 클래스
- 권리분석, 가치평가, 위험평가 결과를 종합하여 최적 입찰가 산정
- 3가지 전략(보수적/균형적/공격적) 제안

#### CostCalculator (비용 계산기)
- 취득세 계산 (1주택/2주택/3주택이상/법인 구분)
- 명도비용 추정 (난이도별: LOW/MEDIUM/HIGH/CRITICAL)
- 총 투자금 계산 (입찰가 + 인수금액 + 취득세 + 등기비용 + 명도비용 + 리모델링 + 기타)

#### CompetitionPredictor (경쟁률 예측기)
- 입찰가율, 유찰 횟수, 위험등급을 기반으로 경쟁자 수 예측
- 경쟁 강도 분류 (LOW/MEDIUM/HIGH/VERY_HIGH)
- 경쟁 강도별 전략 추천

#### WinProbabilityCalculator (낙찰 확률 계산기)
- 정규분포 기반 낙찰 확률 계산
- 경쟁자 수를 반영한 확률 보정
- 확률 해석 및 신뢰도 평가

#### OptimalBidCalculator (최적 입찰가 산정기)
- 목표 수익률 기반 역산 공식 적용
- 3가지 전략 생성 (보수적 90%, 균형적 100%, 공격적 110%)
- 전략별 수익률, 낙찰확률, 위험수준, 추천의견 제공

#### FallbackStrategyGenerator (유찰 대응 전략 생성기)
- 향후 5회차까지 유찰 시나리오 생성
- 회차별 최저입찰가율 계산 (20% 감소율 적용)
- 회차별 추천 행동 제시

### 2. 주요 기능

#### generate_strategy()
입찰 전략 생성 메인 메서드

**입력:**
- `valuation`: 가치평가 결과 (시세, 감정가, 최저입찰가 등)
- `rights_analysis`: 권리분석 결과 (인수금액 등)
- `risk_analysis`: 위험평가 결과 (명도난이도, 위험등급 등)
- `user_settings`: 사용자 설정 (목표수익률, 주택수, 위험선호도 등)

**출력:**
- `BidStrategyResult`: 입찰 전략 결과
  - 최적 입찰가 및 입찰율
  - 3가지 전략별 추천
  - 비용 분석
  - 수익 분석 (시나리오별)
  - 입찰율별 낙찰 확률
  - 경쟁 분석
  - 최종 추천 및 주의사항
  - 이번 회차 입찰 여부 판단

#### generate_markdown_report()
마크다운 형식의 입찰 전략 리포트 생성

### 3. 최적 입찰가 계산 공식

```
목표 수익률 달성을 위한 역산 공식:

시세 = 입찰가 * (1 + 취득세율) * (1 + 목표수익률) + 고정비용 * (1 + 목표수익률)

역산:
입찰가 = (시세 - 고정비용 * (1 + 목표수익률)) / ((1 + 취득세율) * (1 + 목표수익률))

여기서:
- 고정비용 = 인수금액 + 등기비용 + 명도비용 + 리모델링 + 기타비용
- 취득세율 = 주택 수에 따라 1~12%
```

### 4. 취득세율 (주택 기준)

| 주택 수 | 금액 범위 | 세율 |
|---------|----------|------|
| 1주택 | 0 ~ 6억 | 1% |
| 1주택 | 6억 ~ 9억 | 2% |
| 1주택 | 9억 이상 | 3% |
| 2주택 | - | 8% |
| 3주택 이상 | - | 12% |
| 법인 | - | 12% |

### 5. 명도비용 추정

| 난이도 | 비용 |
|--------|------|
| LOW | 0원 |
| MEDIUM | 500만원 |
| HIGH | 1,500만원 |
| CRITICAL | 3,000만원 |

### 6. 전략별 특징

| 전략 | 입찰가 | 수익률 | 낙찰확률 | 위험 | 적합 상황 |
|------|--------|--------|----------|------|----------|
| 보수적 | 최적가 × 0.9 | 높음 | 낮음 | 낮음 | 안정적 수익 추구 |
| 균형적 | 최적가 × 1.0 | 중간 | 중간 | 중간 | 균형잡힌 접근 |
| 공격적 | 최적가 × 1.1 | 낮음 | 높음 | 높음 | 낙찰 우선 |

### 7. 위험 수준 판단

```python
if 수익률 >= 20% and 낙찰확률 >= 50%:
    위험수준 = "LOW"
elif 수익률 >= 10%:
    위험수준 = "MEDIUM"
elif 수익률 >= 0%:
    위험수준 = "HIGH"
else:
    위험수준 = "CRITICAL"
```

### 8. 이번 회차 입찰 여부 판단

다음 조건에서 입찰 대기 권장:
- 예상 수익률이 음수인 경우
- 유찰 대응 전략에서 "관망 추천"인 경우
- 낙찰 확률이 10% 미만인 경우

## 테스트 결과

### 테스트 시나리오
- 감정가: 8억원
- 추정 시세: 7.5억원
- 최저입찰가: 6.4억원 (80%)
- 인수금액: 1.5억원
- 목표 수익률: 15%

### 테스트 결과
```
사건번호: 2024타경12345
최적 입찰가: 640,000,000원 (80.0%)
예상 경쟁자: 4명 (MEDIUM)
이번 회차 입찰: 아니오
대기 이유: 예상 수익률이 음수이므로 유찰 후 재검토를 권장합니다.

전략별 추천:
  보수적:
    입찰가: 640,000,000원 (80.0%)
    수익률: -7.6% | 낙찰확률: 49.4%

  균형적:
    입찰가: 640,000,000원 (80.0%)
    수익률: -7.6% | 낙찰확률: 49.4%

  공격적:
    입찰가: 704,000,000원 (88.0%)
    수익률: -14.5% | 낙찰확률: 64.5%

비용 분석:
  취득세: 12,800,000원
  인수금액: 150,000,000원
  명도비용: 5,000,000원
  총 부대비용: 171,500,000원

주의사항:
  - 예상 수익률이 음수입니다. 현재 시세 기준으로 손실이 예상됩니다.
```

## 의존성

```python
import numpy as np          # 통계 계산
from scipy.stats import norm  # 정규분포 (낙찰 확률 계산)
```

## 사용 예제

```python
from agents.bid_strategist import BidStrategistAgent

# 에이전트 생성
agent = BidStrategistAgent()

# 입력 데이터 준비
valuation = {
    "case_number": "2024타경12345",
    "estimated_market_price": 750_000_000,
    "appraisal_value": 800_000_000,
    "minimum_bid": 640_000_000,
    "auction_count": 1,
}

rights_analysis = {
    "total_assumed_amount": 150_000_000,
}

risk_analysis = {
    "eviction_difficulty": "MEDIUM",
    "risk_grade": "B",
    "risk_grade_encoded": 2,
}

user_settings = {
    "target_roi": 0.15,
    "housing_count": "1주택",
    "renovation_budget": 0,
    "risk_tolerance": "balanced",
}

# 전략 생성
result = agent.generate_strategy(
    valuation=valuation,
    rights_analysis=rights_analysis,
    risk_analysis=risk_analysis,
    user_settings=user_settings,
)

# 결과 활용
print(f"최적 입찰가: {result.optimal_bid:,}원")
print(f"예상 수익률: {result.recommendations[1].expected_roi*100:.1f}%")
print(f"낙찰 확률: {result.recommendations[1].win_probability*100:.1f}%")

# 마크다운 리포트 생성
markdown = agent.generate_markdown_report(result)
```

## 설계서 준수 사항

이 구현은 다음 설계서를 기반으로 작성되었습니다:
- 위치: `C:\Users\vip3\Desktop\그리드라이프\개발\입찰전략_에이전트_상세설계서.md`
- 모든 주요 모듈과 공식이 설계서에 명시된 대로 구현됨
- 데이터 모델은 `src\models\strategy.py`와 호환되도록 설계됨

## 파일 정보

- 파일명: `bid_strategist.py`
- 크기: 약 30KB
- 라인 수: 약 1000 라인
- 주요 클래스: 7개
- 주요 메서드: 20개 이상

## 향후 개선 사항

1. **ML 모델 통합**: 실제 경매 데이터로 학습된 경쟁률 예측 모델 적용
2. **과거 데이터 활용**: 낙찰 확률 계산 시 실제 경매 이력 데이터 반영
3. **Monte Carlo 시뮬레이션**: 수익률 시뮬레이션에 확률적 요소 추가
4. **최적화 알고리즘**: scipy.optimize를 활용한 수리적 최적화
5. **민감도 분석**: 주요 변수 변화에 따른 결과 민감도 분석

## 작성 정보

- 작성일: 2024-02-04
- 구현 시간: 약 1시간
- 테스트 완료: ✅
- 설계서 준수: ✅
