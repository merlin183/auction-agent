# 위험평가 에이전트 구현 완료

## 파일 위치
`C:\Users\vip3\Desktop\그리드라이프\개발\auction-agent\src\agents\risk_assessor.py`

## 구현 내역

### 1. 핵심 클래스 (7개)

#### 1.1 RiskScorer
- 종합 위험 점수 계산 엔진
- 카테고리별 가중치 적용 (권리 40%, 시장 20%, 물건 20%, 명도 20%)
- 등급 산출 (A/B/C/D)
- 위험 수준 결정 (LOW/MEDIUM/HIGH/CRITICAL)

#### 1.2 RightsRiskEvaluator (권리 리스크 평가기)
가중치 40%, 5개 평가항목:
- **인수금액 비율** (30%): 감정가 대비 인수금액 비율 평가
- **선순위 권리 수** (20%): 인수해야 할 권리 개수 평가
- **권리관계 복잡도** (15%): 특수 권리 수에 따른 복잡도
- **법정지상권** (20%): 법정지상권 성립 위험도
- **유치권** (15%): 유치권 신고 및 잠재 리스크

#### 1.3 MarketRiskEvaluator (시장 리스크 평가기)
가중치 20%, 4개 평가항목:
- **가격 변동성** (30%): 최근 1년 가격 변동성
- **거래 유동성** (25%): 최근 12개월 거래량
- **시세 괴리** (25%): 감정가와 실제 시세 차이
- **시장 추세** (20%): 상승/안정/하락 추세 평가

#### 1.4 PropertyRiskEvaluator (물건 리스크 평가기)
가중치 20%, 4개 평가항목:
- **건물 노후도** (35%): 건축년도 기준 경과년수
- **하자 가능성** (30%): 발견된 하자 건수
- **특수 물건** (20%): 지분/공유 등 특수성
- **점유 상태** (15%): 공실/소유자/임차인/불명

#### 1.5 EvictionRiskEvaluator (명도 리스크 평가기)
가중치 20%, 4개 평가항목:
- **임차인 대항력** (35%): 대항력 있는 임차인 수
- **점유자 수** (25%): 현재 점유자 수
- **명도 난이도** (25%): LOW/MEDIUM/HIGH/CRITICAL
- **분쟁 가능성** (15%): 진행 중인 소송 여부

#### 1.6 RedFlagDetector (위험 신호 탐지기)
9가지 Red Flag 규칙:
1. 과도한 인수금액 (감정가 30% 초과)
2. 유치권 신고
3. 법정지상권 위험 (HIGH)
4. 가처분 등기
5. 다수 점유자 (4명 이상)
6. 노후 건물 (35년 이상)
7. 시세 괴리 (15% 이상)
8. 복수 선순위 권리 (5개 이상)
9. 거래 유동성 부족 (12개월 5건 미만)

#### 1.7 RiskAssessorAgent (메인 에이전트)
주요 기능:
- 종합 위험 평가 (`assess()` 메서드)
- 카테고리별 평가 통합
- Red Flag 탐지
- 추천 사항 생성 (최대 5개)
- 입문자 적합성 판단
- 상세 리포트 생성

## 2. 데이터 모델 연동

`src/models/risk.py`의 모델 사용:
- `RiskLevel`: 위험 수준 열거형
- `RiskGrade`: 위험 등급 열거형 (A/B/C/D)
- `RiskItem`: 개별 위험 항목
- `CategoryRisk`: 카테고리별 위험
- `RedFlag`: 위험 신호
- `RiskAssessmentResult`: 종합 평가 결과

## 3. 스코어링 알고리즘

### 3.1 카테고리 점수 계산
각 카테고리 내 항목들의 가중 평균:
```
카테고리 점수 = Σ(항목 점수 × 항목 가중치)
```

### 3.2 총점 계산
카테고리 점수들의 가중 평균:
```
총점 = 권리(40%) + 시장(20%) + 물건(20%) + 명도(20%)
```

### 3.3 등급 기준
- **A등급**: 0 ~ 25점 (안전)
- **B등급**: 25 ~ 50점 (보통)
- **C등급**: 50 ~ 70점 (위험)
- **D등급**: 70 ~ 100점 (고위험)

### 3.4 위험 수준
- **LOW**: 0 ~ 25점
- **MEDIUM**: 25 ~ 50점
- **HIGH**: 50 ~ 70점
- **CRITICAL**: 70 ~ 100점

## 4. 사용 예시

```python
from src.agents.risk_assessor import RiskAssessorAgent

# 에이전트 생성
agent = RiskAssessorAgent()

# 위험 평가
result = agent.assess(
    case_number="2024타경12345",
    rights_analysis={...},      # 권리분석 결과
    valuation={...},            # 가치평가 결과
    property_info={...},        # 물건 정보
    status_report={...},        # 현황 보고서
    market_data={...}           # 시장 데이터
)

# 결과 활용
print(f"위험등급: {result.grade.value}")
print(f"총점: {result.total_score}점")
print(f"입문자 적합: {result.beginner_friendly}")

for flag in result.red_flags:
    print(f"경고: {flag.name} - {flag.description}")

for rec in result.recommendations:
    print(f"권장사항: {rec}")
```

## 5. 출력 구조

### RiskAssessmentResult 구조:
```python
{
    "case_number": "2024타경12345",
    "total_score": 42.5,
    "grade": "B",
    "level": "MEDIUM",

    # 카테고리별 위험
    "rights_risk": CategoryRisk(...),
    "market_risk": CategoryRisk(...),
    "property_risk": CategoryRisk(...),
    "eviction_risk": CategoryRisk(...),

    # 경고 및 권장사항
    "red_flags": [RedFlag(...), ...],
    "recommendations": ["...", "..."],

    # 입문자 정보
    "beginner_friendly": False,
    "beginner_note": "...",

    # 상세 리포트
    "detailed_report": "..."
}
```

## 6. 설계서 준수 사항

✅ 권리 리스크 평가 (40%) - 5개 항목
✅ 시장 리스크 평가 (20%) - 4개 항목
✅ 물건 리스크 평가 (20%) - 4개 항목
✅ 명도 리스크 평가 (20%) - 4개 항목
✅ Red Flag 탐지 - 9개 규칙
✅ 종합 위험등급 산출 (A/B/C/D)
✅ 입문자 적합성 판단
✅ 상세 리포트 생성

## 7. 코드 품질

- **총 라인 수**: 1,050줄
- **타입 힌팅**: 모든 함수에 타입 힌트 적용
- **문서화**: Docstring으로 모든 클래스와 메서드 설명
- **가독성**: 명확한 변수명과 구조화된 코드
- **확장성**: 각 평가기가 독립적으로 동작
- **데이터 검증**: Pydantic 모델 활용

## 8. 주요 특징

1. **모듈화 설계**: 각 평가기가 독립적으로 동작
2. **유연한 입력**: 선택적 파라미터 지원
3. **완전한 타입 안정성**: 모든 데이터 Pydantic 검증
4. **상세한 피드백**: 각 항목별 완화 방안 제시
5. **실무 중심**: 실제 경매 현장의 위험 요소 반영

## 9. 다음 단계

이 에이전트는 다른 에이전트들과 통합되어 사용됩니다:
- `RightsAnalyzerAgent`: 권리분석 결과 제공
- `ValuatorAgent`: 가치평가 결과 제공
- `LocationAnalyzerAgent`: 입지분석 결과 제공
- `OrchestratorAgent`: 전체 워크플로우 조율

---

**구현 완료 일시**: 2026-02-04
**작성자**: Claude Sisyphus-Junior
**총 개발 시간**: ~30분
