# 데이터수집 에이전트 빠른 시작 가이드

## 5분 만에 시작하기

### 1. 파일 위치 확인
```
C:\Users\vip3\Desktop\그리드라이프\개발\auction-agent\src\agents\data_collector.py
```

### 2. Mock 모드로 즉시 테스트
```bash
cd C:\Users\vip3\Desktop\그리드라이프\개발\auction-agent
python example_data_collector.py
```

### 3. 코드에서 직접 사용
```python
import asyncio
from src.agents.data_collector import DataCollectorAgent

async def main():
    # Mock 모드 (API 키 불필요)
    config = {"mock_mode": True}
    agent = DataCollectorAgent(config)

    # 경매 정보 수집
    data = await agent.collect("2024타경12345")

    # 결과 출력
    print(f"사건번호: {data.auction_property.case_number}")
    print(f"주소: {data.auction_property.address}")
    print(f"감정가: {data.auction_property.appraisal_value:,}원")
    print(f"최저입찰가: {data.auction_property.minimum_bid:,}원")
    print(f"실거래: {len(data.real_transactions)}건")

asyncio.run(main())
```

## 주요 클래스

### DataCollectorAgent
메인 에이전트 클래스

**메서드:**
- `collect(case_number)` - 전체 데이터 수집

**반환:**
- `CollectedData` - 경매정보, 문서, 실거래가, 위치정보

### CourtAuctionCrawler
대법원 경매정보 크롤러

**메서드:**
- `search_by_case_number(case_number)` - 사건번호 검색
- `get_documents(case_number)` - 문서 다운로드

### MolitRealTransactionAPI
국토교통부 실거래가 API

**메서드:**
- `get_apartment_transactions(lawd_cd, deal_ymd)` - 실거래 조회

### KakaoMapAPI
카카오맵 API

**메서드:**
- `geocode(address)` - 주소 → 좌표
- `get_location_data(address)` - 위치정보 통합 수집

## 실제 사용 (API 키 필요)

```python
config = {
    "molit_api_key": "발급받은-국토교통부-키",
    "kakao_api_key": "발급받은-카카오-키",
    "ocr_url": "Clova-OCR-엔드포인트",
    "ocr_key": "Clova-OCR-키",
    "mock_mode": False,  # 실제 모드
}

agent = DataCollectorAgent(config)
data = await agent.collect("실제-사건번호")
```

## API 키 발급처

1. **국토교통부**: https://www.data.go.kr/
2. **카카오**: https://developers.kakao.com/
3. **Clova OCR**: https://www.ncloud.com/

## 주요 데이터 구조

```python
CollectedData
├── auction_property: AuctionProperty  # 경매 기본정보
│   ├── case_number: str               # 사건번호
│   ├── address: str                   # 주소
│   ├── appraisal_value: int           # 감정가
│   ├── minimum_bid: int               # 최저입찰가
│   └── auction_date: date             # 매각기일
│
├── documents: List[Document]          # 문서 목록
│   ├── doc_type: str                  # registry/status_report/appraisal
│   ├── file_path: str                 # 파일 경로
│   └── parsed_data: dict              # 파싱된 데이터
│
├── real_transactions: List[RealTransaction]  # 실거래 목록
│   ├── transaction_date: date         # 거래일
│   ├── price: int                     # 가격
│   └── area: Decimal                  # 면적
│
└── location_data: LocationData        # 위치 정보
    ├── lat: float                     # 위도
    ├── lng: float                     # 경도
    └── facilities: dict               # 주변시설
```

## 문제 해결

### 의존성 오류
```bash
pip install selenium aiohttp asyncpg pydantic beautifulsoup4
```

### ChromeDriver 오류
```bash
pip install webdriver-manager
```

### Import 오류
```python
import sys
sys.path.insert(0, "C:/Users/vip3/Desktop/그리드라이프/개발/auction-agent/src")
```

## 참고 문서

- **상세 가이드**: `DATA_COLLECTOR_SUMMARY.md`
- **구현 보고서**: `IMPLEMENTATION_COMPLETE.md`
- **사용 예시**: `example_data_collector.py`
- **테스트 코드**: `tests/test_data_collector.py`

## 다음 단계

1. Mock 모드로 테스트
2. API 키 발급
3. 실제 모드로 전환
4. 데이터베이스 연동 (선택적)

---

**구현 완료일**: 2026-02-04
**버전**: 1.0.0
**상태**: Mock 모드 검증 완료
