# 부동산 경매 AI 에이전트 시스템

입문자도 안전하게 부동산 법원경매에 참여할 수 있도록 도와주는 **멀티 AI 에이전트 기반 경매 분석 플랫폼**

## 주요 기능

- **자동 권리분석**: 등기부 분석, 말소기준권리 탐지, 인수/소멸 분류
- **AI 가치평가**: 시세 추정, 낙찰가율 예측, 수익률 시뮬레이션
- **입지 분석**: 교통, 교육, 편의시설, 개발호재 평가
- **종합 위험평가**: 권리/시장/물건/명도 리스크 스코어링
- **입찰 전략**: 최적 입찰가 산정, 전략별 추천
- **레드팀 검증**: 모든 분석 결과의 교차 검증 및 품질 보증

## 아키텍처

```
┌─────────────────────────────────────────┐
│           오케스트레이터 에이전트          │
├─────────────────────────────────────────┤
│  ┌─────────┐ ┌─────────┐ ┌─────────┐  │
│  │데이터수집│ │권리분석 │ │가치평가 │  │
│  └─────────┘ └─────────┘ └─────────┘  │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐  │
│  │입지분석 │ │위험평가 │ │입찰전략 │  │
│  └─────────┘ └─────────┘ └─────────┘  │
│              ┌─────────┐               │
│              │ 레드팀  │ ← 품질 검증    │
│              └─────────┘               │
│              ┌─────────┐               │
│              │ 리포터  │               │
│              └─────────┘               │
└─────────────────────────────────────────┘
```

## 설치

### 요구사항
- Python 3.11+
- Redis (캐싱용)
- PostgreSQL (선택사항, 데이터 저장용)

### 설치 방법

```bash
# 저장소 클론
git clone <repository-url>
cd auction-agent

# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -e ".[dev]"

# 환경 변수 설정
cp .env.example .env
# .env 파일 편집하여 API 키 설정
```

## 사용법

### CLI 사용

```bash
# 단일 물건 분석
python -m src.main 2024타경12345

# 결과를 파일로 저장
python -m src.main 2024타경12345 -o result.json
```

### API 서버 실행

```bash
# 서버 시작
uvicorn src.api:app --reload

# API 문서: http://localhost:8000/docs
```

### API 예시

```bash
# 분석 요청
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"case_number": "2024타경12345"}'

# 비동기 분석
curl -X POST http://localhost:8000/analyze/async \
  -H "Content-Type: application/json" \
  -d '{"case_number": "2024타경12345"}'
```

## 환경 변수

| 변수 | 설명 | 필수 |
|------|------|------|
| `ANTHROPIC_API_KEY` | Anthropic API 키 | Yes |
| `MOLIT_API_KEY` | 국토교통부 API 키 | No |
| `KAKAO_API_KEY` | 카카오맵 API 키 | No |
| `DATABASE_URL` | PostgreSQL URL | No |
| `REDIS_URL` | Redis URL | No |

## 테스트

```bash
# 전체 테스트 실행
pytest

# 커버리지 포함
pytest --cov=src

# 특정 테스트
pytest tests/test_models.py
```

## 프로젝트 구조

```
auction-agent/
├── src/
│   ├── agents/           # AI 에이전트
│   │   ├── orchestrator.py
│   │   ├── data_collector.py
│   │   ├── rights_analyzer.py
│   │   ├── valuator.py
│   │   ├── location_analyzer.py
│   │   ├── risk_assessor.py
│   │   ├── bid_strategist.py
│   │   ├── red_team.py
│   │   └── reporter.py
│   ├── models/           # 데이터 모델
│   │   ├── auction.py
│   │   ├── rights.py
│   │   ├── valuation.py
│   │   ├── location.py
│   │   ├── risk.py
│   │   ├── strategy.py
│   │   └── validation.py
│   ├── services/         # 서비스
│   │   ├── llm.py
│   │   ├── database.py
│   │   └── cache.py
│   ├── utils/            # 유틸리티
│   │   ├── logger.py
│   │   └── rate_limiter.py
│   ├── main.py           # CLI 엔트리포인트
│   └── api.py            # REST API
├── config/
│   └── settings.py
├── tests/
├── pyproject.toml
└── README.md
```

## 출력 예시

### 분석 결과 (JSON)

```json
{
  "status": "SUCCESS",
  "reliability": 85.5,
  "report": {
    "case_number": "2024타경12345",
    "property_summary": { ... },
    "rights_analysis": {
      "risk_level": "LOW",
      "risk_score": 25,
      "beginner_suitable": true
    },
    "valuation": {
      "estimated_market_price": 1180000000,
      "predicted_bid_rate": 0.78
    },
    "risk_assessment": {
      "grade": "B",
      "total_score": 32
    },
    "bid_strategy": {
      "optimal_bid": 900000000,
      "recommendations": [ ... ]
    }
  },
  "red_team_report": {
    "overall_status": "PASSED",
    "overall_reliability": 85.5,
    "approved": true
  }
}
```

## 기술 스택

- **AI 오케스트레이션**: LangGraph
- **LLM**: Claude (Anthropic)
- **ML**: XGBoost (가격 예측)
- **백엔드**: FastAPI
- **데이터베이스**: PostgreSQL + Redis
- **테스트**: pytest

## 라이선스

MIT License
