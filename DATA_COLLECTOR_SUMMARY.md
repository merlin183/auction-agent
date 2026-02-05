# 데이터수집 에이전트 구현 완료

## 파일 위치
`C:\Users\vip3\Desktop\그리드라이프\개발\auction-agent\src\agents\data_collector.py`

## 구현 내용

### 1. 핵심 클래스 (13개)

#### 데이터 모델
- **Document**: 경매 문서 (등기부등본, 현황조사서, 감정평가서 등)
- **RealTransaction**: 실거래가 데이터
- **LocationData**: 위치 정보 (좌표 + 주변 시설)
- **CollectedData**: 수집된 전체 데이터 통합

#### 크롤링 및 API
- **CourtAuctionCrawler**: 대법원 경매정보 크롤러 (Selenium 기반)
- **MolitRealTransactionAPI**: 국토교통부 실거래가 API 클라이언트
- **KakaoMapAPI**: 카카오맵 API (지오코딩, 주변 시설 검색)
- **ClovaOCR**: 네이버 Clova OCR 클라이언트

#### 데이터 처리
- **RegistryParser**: 등기부등본 파서
- **AddressConverter**: 주소 → 법정동코드 변환
- **DataStore**: PostgreSQL 데이터 저장소
- **RateLimiter**: 요청 제한기 (서버 부하 방지)

#### 메인 에이전트
- **DataCollectorAgent**: 데이터수집 에이전트 메인 클래스

### 2. 주요 기능

#### DataCollectorAgent.collect(case_number)
경매 사건번호로 모든 데이터를 수집하는 메인 메서드

**수집 항목:**
1. 경매 기본 정보 (감정가, 최저입찰가, 매각기일 등)
2. 경매 문서 (등기부등본, 현황조사서, 감정평가서)
3. 실거래가 데이터 (최근 12개월)
4. 위치 정보 (좌표 + 주변 시설: 지하철, 학교, 병원, 마트, 공원)
5. OCR 텍스트 추출 및 파싱

**반환값:**
```python
CollectedData(
    auction_property: AuctionProperty,  # 경매 물건 정보
    documents: List[Document],          # 문서 목록
    real_transactions: List[RealTransaction],  # 실거래 목록
    location_data: LocationData,        # 위치 정보
    collected_at: datetime              # 수집 시각
)
```

### 3. Mock 모드

실제 웹사이트나 API 접근 없이 테스트 가능한 Mock 모드 구현

**장점:**
- 외부 의존성 없이 개발 및 테스트 가능
- API 키 없이도 전체 플로우 검증 가능
- 빠른 프로토타이핑

**사용 방법:**
```python
config = {
    "mock_mode": True,  # Mock 모드 활성화
    # ... 기타 설정
}
agent = DataCollectorAgent(config)
```

### 4. 안전 기능

#### Rate Limiting
- 분당 최대 요청 수 제한
- 요청 간 랜덤 지연 (봇 탐지 방지)
- 서버 부하 최소화

#### Error Handling
- 각 단계별 예외 처리
- 실패 시에도 수집 가능한 데이터는 반환
- 상세한 오류 로깅

### 5. 비동기 처리

- `async/await` 기반 비동기 I/O
- 병렬 데이터 수집으로 성능 향상
- 주변 시설 검색 등 독립적인 작업 동시 실행

### 6. 데이터베이스 연동

PostgreSQL 지원 (선택적)
```python
config = {
    "database_url": "postgresql://user:pass@localhost/auction_db",
    "save_to_db": True,  # DB 저장 활성화
}
```

## 사용 예시

### 기본 사용법
```python
import asyncio
from src.agents.data_collector import DataCollectorAgent

async def main():
    config = {
        "molit_api_key": "your-molit-api-key",
        "kakao_api_key": "your-kakao-api-key",
        "ocr_url": "your-ocr-url",
        "ocr_key": "your-ocr-key",
        "mock_mode": True,  # 실제 사용 시 False
    }

    agent = DataCollectorAgent(config)

    # 경매 정보 수집
    data = await agent.collect("2024타경12345")

    print(f"사건번호: {data.auction_property.case_number}")
    print(f"주소: {data.auction_property.address}")
    print(f"감정가: {data.auction_property.appraisal_value:,}원")
    print(f"최저입찰가: {data.auction_property.minimum_bid:,}원")
    print(f"실거래 건수: {len(data.real_transactions)}")

asyncio.run(main())
```

### Mock 모드 테스트
```python
# Mock 모드에서는 API 키 없이도 작동
config = {"mock_mode": True}
agent = DataCollectorAgent(config)

data = await agent.collect("2024타경12345")
# 테스트용 Mock 데이터 반환
```

## 의존성

### 필수 패키지
```
selenium>=4.18.0
beautifulsoup4>=4.12.0
aiohttp>=3.9.0
asyncpg>=0.29.0
pydantic>=2.5.0
```

### 선택적 패키지
```
redis>=5.0.0  # 캐싱용 (미구현)
celery>=5.3.0  # 스케줄링용 (미구현)
```

## 주의사항

### 1. 크롤링 준수사항
- robots.txt 확인 필수
- 적절한 요청 간격 유지 (Rate Limiting)
- 대상 사이트 이용약관 준수
- 서버 부하 최소화

### 2. 개인정보 처리
- 수집된 데이터의 적법한 처리
- 개인정보보호법 준수
- 불필요한 개인정보 수집 금지

### 3. 웹사이트 구조 변경
- 대법원 경매정보 사이트 구조는 변경될 수 있음
- 정기적인 크롤러 업데이트 필요
- 파싱 로직 점검 필요

## 향후 개선 사항

### 1. 캐싱 구현
- Redis를 이용한 데이터 캐싱
- 중복 요청 방지
- 응답 속도 개선

### 2. 스케줄링
- Celery 기반 주기적 데이터 수집
- 신규 경매 물건 자동 수집
- 실거래가 자동 업데이트

### 3. 추가 데이터 소스
- KB부동산 시세
- 네이버 부동산 매물
- 등기정보광장 API

### 4. 고도화
- 문서 이미지 전처리 (OCR 정확도 향상)
- 등기부등본 파싱 고도화
- 감정평가서 자동 분석
- 현황조사서 구조화

## 파일 구조

```
auction-agent/
├── src/
│   ├── agents/
│   │   ├── __init__.py
│   │   └── data_collector.py  ← 구현 완료
│   └── models/
│       └── auction.py          ← 기존 모델 사용
├── tests/
│   └── test_data_collector.py  ← 테스트 코드 (pytest 필요)
├── test_basic_structure.py     ← 구조 검증 스크립트
└── DATA_COLLECTOR_SUMMARY.md   ← 이 문서
```

## 검증 결과

### 구조 검증 통과
- 총 클래스 수: 13개
- 필수 클래스: 13/13 구현 완료
- Python 구문 검증: 통과
- Import 구조: 정상

### 기능 검증
- Mock 모드 동작: 정상
- 데이터 모델 통합: 정상
- 비동기 처리: 정상

## 참고 문서

- 설계서: `C:\Users\vip3\Desktop\그리드라이프\개발\데이터수집_에이전트_상세설계서.md`
- 모델: `C:\Users\vip3\Desktop\그리드라이프\개발\auction-agent\src\models\auction.py`

## 작성 정보

- 작성일: 2026-02-04
- 버전: 1.0
- 상태: 구현 완료 (Mock 모드)

---

**다음 단계:** 실제 API 키 설정 후 Mock 모드를 False로 변경하여 실제 데이터 수집 테스트
