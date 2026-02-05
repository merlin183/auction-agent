"""데이터수집 에이전트 테스트"""
import asyncio
from datetime import date

import pytest

from src.agents.data_collector import (
    AddressConverter,
    CourtAuctionCrawler,
    DataCollectorAgent,
    KakaoMapAPI,
    MolitRealTransactionAPI,
    RateLimiter,
    RegistryParser,
)
from src.models.auction import PropertyType


@pytest.fixture
def mock_config():
    """Mock 설정"""
    return {
        "molit_api_key": "test-molit-key",
        "kakao_api_key": "test-kakao-key",
        "ocr_url": "test-ocr-url",
        "ocr_key": "test-ocr-key",
        "database_url": "postgresql://test:test@localhost/test_db",
        "mock_mode": True,
        "save_to_db": False,
    }


class TestCourtAuctionCrawler:
    """대법원 경매정보 크롤러 테스트"""

    def test_crawler_initialization(self):
        """크롤러 초기화 테스트"""
        crawler = CourtAuctionCrawler(headless=True, mock_mode=True)
        assert crawler.mock_mode is True
        assert crawler.BASE_URL == "https://www.courtauction.go.kr"

    def test_mock_auction_property(self):
        """Mock 경매 정보 생성 테스트"""
        crawler = CourtAuctionCrawler(mock_mode=True)
        with crawler:
            auction_property = crawler.search_by_case_number("2024타경12345")

            assert auction_property is not None
            assert auction_property.case_number == "2024타경12345"
            assert auction_property.court == "서울중앙지방법원"
            assert auction_property.property_type == PropertyType.APARTMENT
            assert auction_property.appraisal_value == 500000000
            assert auction_property.minimum_bid == 400000000

    def test_mock_documents(self):
        """Mock 문서 수집 테스트"""
        crawler = CourtAuctionCrawler(mock_mode=True)
        with crawler:
            documents = crawler.get_documents("2024타경12345")

            assert len(documents) == 2
            assert documents[0].doc_type == "registry"
            assert documents[1].doc_type == "status_report"


class TestMolitRealTransactionAPI:
    """국토교통부 실거래가 API 테스트"""

    @pytest.mark.asyncio
    async def test_mock_transactions(self):
        """Mock 실거래 데이터 테스트"""
        api = MolitRealTransactionAPI("test-key", mock_mode=True)
        transactions = await api.get_apartment_transactions("11680", "202401")

        assert len(transactions) == 2
        assert transactions[0].property_type == "아파트"
        assert transactions[0].price > 0


class TestAddressConverter:
    """주소 변환기 테스트"""

    @pytest.mark.asyncio
    async def test_get_lawd_cd(self):
        """법정동코드 조회 테스트"""
        converter = AddressConverter()

        # 강남구
        code1 = await converter.get_lawd_cd("서울특별시 강남구 역삼동")
        assert code1 == "11680"

        # 서초구
        code2 = await converter.get_lawd_cd("서울특별시 서초구 서초동")
        assert code2 == "11650"

        # 알 수 없는 주소 (기본값)
        code3 = await converter.get_lawd_cd("알 수 없는 주소")
        assert code3 == "11680"


class TestKakaoMapAPI:
    """카카오맵 API 테스트"""

    @pytest.mark.asyncio
    async def test_mock_geocode(self):
        """Mock 지오코딩 테스트"""
        api = KakaoMapAPI("test-key", mock_mode=True)
        lat, lng = await api.geocode("서울특별시 강남구 역삼동")

        assert lat is not None
        assert lng is not None
        assert lat == 37.4979
        assert lng == 127.0276

    @pytest.mark.asyncio
    async def test_mock_location_data(self):
        """Mock 위치 정보 수집 테스트"""
        api = KakaoMapAPI("test-key", mock_mode=True)
        location_data = await api.get_location_data("서울특별시 강남구 역삼동")

        assert location_data is not None
        assert location_data.lat == 37.4979
        assert location_data.lng == 127.0276
        assert "subway" in location_data.facilities
        assert "school" in location_data.facilities


class TestRegistryParser:
    """등기부등본 파서 테스트"""

    def test_split_sections(self):
        """섹션 분리 테스트"""
        parser = RegistryParser()
        text = """
        [표제부]
        소재지: 서울 강남구
        [갑구]
        1 2024.01.01 12345 소유권이전
        [을구]
        1 2024.02.01 67890 근저당권설정
        """

        sections = parser._split_sections(text)
        assert "표제부" in sections
        assert "갑구" in sections
        assert "을구" in sections

    def test_extract_right_type(self):
        """권리 유형 추출 테스트"""
        parser = RegistryParser()

        assert parser._extract_right_type("소유권이전 등기") == "소유권이전"
        assert parser._extract_right_type("근저당권설정 금액 5억원") == "근저당권설정"
        assert parser._extract_right_type("가압류 신청") == "가압류"
        assert parser._extract_right_type("알 수 없는 내용") == "기타"


class TestRateLimiter:
    """요청 제한기 테스트"""

    @pytest.mark.asyncio
    async def test_rate_limiter_delay(self):
        """지연 시간 테스트"""
        limiter = RateLimiter(
            requests_per_minute=60, min_delay=0.1, max_delay=0.2
        )

        start_time = asyncio.get_event_loop().time()
        await limiter.wait()
        end_time = asyncio.get_event_loop().time()

        elapsed = end_time - start_time
        assert 0.1 <= elapsed <= 0.3  # 약간의 오차 허용


class TestDataCollectorAgent:
    """데이터수집 에이전트 통합 테스트"""

    @pytest.mark.asyncio
    async def test_collect_auction_data(self, mock_config):
        """경매 데이터 수집 통합 테스트"""
        agent = DataCollectorAgent(mock_config)
        case_number = "2024타경12345"

        collected_data = await agent.collect(case_number)

        # 기본 정보 확인
        assert collected_data.auction_property.case_number == case_number
        assert collected_data.auction_property.property_type == PropertyType.APARTMENT
        assert collected_data.auction_property.appraisal_value == 500000000

        # 문서 확인
        assert len(collected_data.documents) == 2

        # 실거래 확인
        assert len(collected_data.real_transactions) > 0

        # 위치 정보 확인
        assert collected_data.location_data is not None
        assert collected_data.location_data.lat == 37.4979
        assert len(collected_data.location_data.facilities) > 0

    @pytest.mark.asyncio
    async def test_get_deal_ymd(self, mock_config):
        """계약년월 계산 테스트"""
        agent = DataCollectorAgent(mock_config)

        # 현재 월
        ymd_0 = agent._get_deal_ymd(0)
        assert len(ymd_0) == 6

        # 1개월 전
        ymd_1 = agent._get_deal_ymd(1)
        assert len(ymd_1) == 6

        # 12개월 전
        ymd_12 = agent._get_deal_ymd(12)
        assert len(ymd_12) == 6

        # 연도 넘김 확인
        from datetime import date

        current_date = date.today()
        if current_date.month == 1:
            # 1월인 경우 1개월 전은 작년 12월
            expected_year = current_date.year - 1
            expected_month = 12
            assert ymd_1 == f"{expected_year:04d}{expected_month:02d}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
