"""데이터수집 에이전트 모듈

대법원 경매정보 크롤링, 실거래가 API 연동, 위치 정보 수집을 담당하는 에이전트
"""
import asyncio
import base64
import random
import re
import time
import xml.etree.ElementTree as ET
from collections import deque
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp
import asyncpg
from pydantic import BaseModel, Field
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from ..models.auction import AuctionProperty, AuctionStatus, PropertyType


# ========================================
# Data Models
# ========================================


class Document(BaseModel):
    """경매 문서"""

    case_number: str
    doc_type: str  # registry/status_report/appraisal/sale_specification
    file_path: str
    raw_text: str = ""
    parsed_data: Dict[str, Any] = Field(default_factory=dict)
    collected_at: datetime = Field(default_factory=datetime.now)


class RealTransaction(BaseModel):
    """실거래 데이터"""

    address: str
    transaction_date: date
    price: int
    area: Decimal
    floor: int
    building_year: int
    property_type: str


class LocationData(BaseModel):
    """위치 정보"""

    lat: float
    lng: float
    facilities: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


class CollectedData(BaseModel):
    """수집된 전체 데이터"""

    auction_property: AuctionProperty
    documents: List[Document] = Field(default_factory=list)
    real_transactions: List[RealTransaction] = Field(default_factory=list)
    location_data: Optional[LocationData] = None
    collected_at: datetime = Field(default_factory=datetime.now)


# ========================================
# Rate Limiter
# ========================================


class RateLimiter:
    """요청 제한기 - 서버 부하 방지 및 봇 탐지 회피"""

    def __init__(
        self,
        requests_per_minute: int = 30,
        min_delay: float = 1.0,
        max_delay: float = 3.0,
    ):
        self.requests_per_minute = requests_per_minute
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.request_times: deque = deque(maxlen=requests_per_minute)

    async def wait(self) -> None:
        """요청 전 대기"""
        now = datetime.now()

        # 분당 요청 수 체크
        if len(self.request_times) >= self.requests_per_minute:
            oldest = self.request_times[0]
            if now - oldest < timedelta(minutes=1):
                wait_time = (oldest + timedelta(minutes=1) - now).total_seconds()
                await asyncio.sleep(wait_time)

        # 랜덤 지연 (봇 탐지 방지)
        delay = random.uniform(self.min_delay, self.max_delay)
        await asyncio.sleep(delay)

        self.request_times.append(datetime.now())


# ========================================
# Court Auction Crawler
# ========================================


class CourtAuctionCrawler:
    """대법원 경매정보 크롤러 (courtauction.go.kr)

    주의: 실제 웹사이트 구조는 변경될 수 있으므로 정기적인 업데이트 필요
    """

    BASE_URL = "https://www.courtauction.go.kr"

    def __init__(self, headless: bool = True, mock_mode: bool = True):
        """
        Args:
            headless: 헤드리스 모드 사용 여부
            mock_mode: Mock 모드 (실제 웹사이트 접근하지 않음)
        """
        self.mock_mode = mock_mode
        self.options = Options()

        if headless:
            self.options.add_argument("--headless")

        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--disable-dev-shm-usage")
        self.options.add_argument("--disable-gpu")
        self.options.add_argument("--window-size=1920,1080")

        # User-Agent 설정
        self.options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None

    def __enter__(self) -> "CourtAuctionCrawler":
        if not self.mock_mode:
            self.driver = webdriver.Chrome(options=self.options)
            self.wait = WebDriverWait(self.driver, 10)
        return self

    def __exit__(self, *args: Any) -> None:
        if self.driver:
            self.driver.quit()

    def search_by_case_number(self, case_number: str) -> Optional[AuctionProperty]:
        """사건번호로 경매 정보 검색

        Args:
            case_number: 사건번호 (예: 2024타경12345)

        Returns:
            경매 물건 정보 또는 None
        """
        if self.mock_mode:
            return self._mock_auction_property(case_number)

        try:
            # 메인 페이지 접속
            self.driver.get(f"{self.BASE_URL}/RetrieveRealEstSrchList.laf")
            time.sleep(2)

            # 사건번호 파싱 (예: 2024타경12345)
            year = case_number[:4]
            case_type = case_number[4:6]
            number = case_number[6:]

            # 검색 폼 입력
            year_input = self.wait.until(
                EC.presence_of_element_located((By.NAME, "termStartYear"))
            )
            year_input.clear()
            year_input.send_keys(year)

            # 사건번호 입력
            case_input = self.driver.find_element(By.NAME, "caseNo")
            case_input.clear()
            case_input.send_keys(number)

            # 검색 버튼 클릭
            search_btn = self.driver.find_element(By.ID, "searchBtn")
            search_btn.click()
            time.sleep(3)

            # 결과 파싱
            return self._parse_search_result(case_number)

        except Exception as e:
            print(f"검색 실패: {str(e)}")
            return None

    def _parse_search_result(self, case_number: str) -> Optional[AuctionProperty]:
        """검색 결과 파싱"""
        try:
            # 결과 테이블에서 첫 번째 항목 클릭
            result_row = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.Ltbl_list tbody tr"))
            )

            # 상세 정보 추출
            cells = result_row.find_elements(By.TAG_NAME, "td")

            if len(cells) < 8:
                return None

            return AuctionProperty(
                case_number=cells[1].text.strip(),
                court=cells[0].text.strip(),
                property_type=self._parse_property_type(cells[2].text.strip()),
                address=cells[3].text.strip(),
                appraisal_value=self._parse_price(cells[4].text),
                minimum_bid=self._parse_price(cells[5].text),
                auction_date=self._parse_date(cells[6].text),
                bid_count=int(cells[7].text.strip() or "1"),
                status=AuctionStatus.IN_PROGRESS,
            )

        except Exception as e:
            print(f"결과 파싱 실패: {str(e)}")
            return None

    def get_documents(self, case_number: str) -> List[Document]:
        """경매 문서 다운로드

        Args:
            case_number: 사건번호

        Returns:
            문서 목록
        """
        if self.mock_mode:
            return self._mock_documents(case_number)

        documents = []

        try:
            # 상세 페이지 접속
            detail_url = f"{self.BASE_URL}/RetrieveRealEstCargeDetail.laf"
            self.driver.get(f"{detail_url}?saession={case_number}")
            time.sleep(2)

            # 문서 링크 수집
            doc_links = self.driver.find_elements(By.CSS_SELECTOR, "a[onclick*='openPdf']")

            for link in doc_links:
                doc_type = self._determine_doc_type(link.text)
                if doc_type:
                    # PDF 다운로드 로직 (실제 구현 시 필요)
                    doc = self._download_document(link, doc_type, case_number)
                    if doc:
                        documents.append(doc)

        except Exception as e:
            print(f"문서 수집 실패: {str(e)}")

        return documents

    def _download_document(
        self, link: Any, doc_type: str, case_number: str
    ) -> Optional[Document]:
        """문서 다운로드 (placeholder)"""
        # 실제 구현 시 PDF 다운로드 로직 추가
        return Document(
            case_number=case_number,
            doc_type=doc_type,
            file_path=f"/tmp/{case_number}_{doc_type}.pdf",
            collected_at=datetime.now(),
        )

    def _parse_price(self, text: str) -> int:
        """가격 문자열을 정수로 변환"""
        numbers = re.sub(r"[^\d]", "", text)
        return int(numbers) if numbers else 0

    def _parse_date(self, text: str) -> date:
        """날짜 문자열 파싱"""
        try:
            return datetime.strptime(text.strip(), "%Y.%m.%d").date()
        except Exception:
            return date.today()

    def _parse_property_type(self, text: str) -> PropertyType:
        """물건 유형 파싱"""
        type_map = {
            "아파트": PropertyType.APARTMENT,
            "다세대": PropertyType.VILLA,
            "연립": PropertyType.VILLA,
            "빌라": PropertyType.VILLA,
            "오피스텔": PropertyType.OFFICETEL,
            "단독": PropertyType.HOUSE,
            "상가": PropertyType.COMMERCIAL,
            "사무실": PropertyType.OFFICE,
            "토지": PropertyType.LAND,
            "공장": PropertyType.FACTORY,
        }
        for key, value in type_map.items():
            if key in text:
                return value
        return PropertyType.OTHER

    def _determine_doc_type(self, link_text: str) -> Optional[str]:
        """문서 유형 결정"""
        if "등기" in link_text:
            return "registry"
        elif "현황" in link_text:
            return "status_report"
        elif "감정" in link_text:
            return "appraisal"
        elif "매각" in link_text:
            return "sale_specification"
        return None

    def _mock_auction_property(self, case_number: str) -> AuctionProperty:
        """Mock 경매 정보 생성 (테스트용)"""
        return AuctionProperty(
            case_number=case_number,
            court="서울중앙지방법원",
            property_type=PropertyType.APARTMENT,
            address="서울특별시 강남구 역삼동 123-45",
            detail_address="아크로타워 101동 1001호",
            appraisal_value=500000000,
            minimum_bid=400000000,
            auction_date=date.today() + timedelta(days=30),
            bid_count=1,
            status=AuctionStatus.IN_PROGRESS,
            exclusive_area_sqm=Decimal("84.5"),
            building_area_sqm=Decimal("120.3"),
            building_year=2018,
            floor=10,
            total_floors=25,
        )

    def _mock_documents(self, case_number: str) -> List[Document]:
        """Mock 문서 목록 생성 (테스트용)"""
        return [
            Document(
                case_number=case_number,
                doc_type="registry",
                file_path=f"/mock/documents/{case_number}_registry.pdf",
                raw_text="[Mock 등기부등본 내용]",
                collected_at=datetime.now(),
            ),
            Document(
                case_number=case_number,
                doc_type="status_report",
                file_path=f"/mock/documents/{case_number}_status_report.pdf",
                raw_text="[Mock 현황조사서 내용]",
                collected_at=datetime.now(),
            ),
        ]


# ========================================
# Real Transaction API
# ========================================


class MolitRealTransactionAPI:
    """국토교통부 실거래가 API 클라이언트"""

    BASE_URL = "http://openapi.molit.go.kr/OpenAPI_ToolInstall/service/rest/RTMSOBJSvc"

    def __init__(self, api_key: str, mock_mode: bool = True):
        """
        Args:
            api_key: 공공데이터포털 API 키
            mock_mode: Mock 모드
        """
        self.api_key = api_key
        self.mock_mode = mock_mode

    async def get_apartment_transactions(
        self,
        lawd_cd: str,  # 법정동코드 앞 5자리
        deal_ymd: str,  # 계약년월 (YYYYMM)
    ) -> List[RealTransaction]:
        """아파트 실거래 조회

        Args:
            lawd_cd: 법정동코드 (예: 11680 - 강남구)
            deal_ymd: 계약년월 (YYYYMM)

        Returns:
            실거래 목록
        """
        if self.mock_mode:
            return self._mock_transactions(lawd_cd, deal_ymd)

        url = f"{self.BASE_URL}/getRTMSDataSvcAptTradeDev"
        params = {
            "serviceKey": self.api_key,
            "LAWD_CD": lawd_cd,
            "DEAL_YMD": deal_ymd,
            "numOfRows": 1000,
            "pageNo": 1,
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    raise Exception(f"API 호출 실패: {response.status}")

                xml_text = await response.text()
                return self._parse_response(xml_text)

    def _parse_response(self, xml_text: str) -> List[RealTransaction]:
        """XML 응답 파싱"""
        root = ET.fromstring(xml_text)
        items = root.findall(".//item")

        transactions = []
        for item in items:
            try:
                transaction = RealTransaction(
                    address=self._get_text(item, "법정동") + " " + self._get_text(item, "아파트"),
                    transaction_date=date(
                        int(self._get_text(item, "년")),
                        int(self._get_text(item, "월")),
                        int(self._get_text(item, "일")),
                    ),
                    price=int(self._get_text(item, "거래금액").replace(",", "")) * 10000,
                    area=Decimal(self._get_text(item, "전용면적")),
                    floor=int(self._get_text(item, "층")),
                    building_year=int(self._get_text(item, "건축년도")),
                    property_type="아파트",
                )
                transactions.append(transaction)
            except Exception:
                continue

        return transactions

    def _get_text(self, element: ET.Element, tag: str) -> str:
        """XML 요소 텍스트 추출"""
        child = element.find(tag)
        return child.text.strip() if child is not None and child.text else ""

    def _mock_transactions(self, lawd_cd: str, deal_ymd: str) -> List[RealTransaction]:
        """Mock 실거래 데이터 생성 (테스트용)"""
        year = int(deal_ymd[:4])
        month = int(deal_ymd[4:6])

        return [
            RealTransaction(
                address=f"서울시 강남구 역삼동 아크로타워",
                transaction_date=date(year, month, 15),
                price=480000000,
                area=Decimal("84.5"),
                floor=10,
                building_year=2018,
                property_type="아파트",
            ),
            RealTransaction(
                address=f"서울시 강남구 역삼동 래미안",
                transaction_date=date(year, month, 20),
                price=520000000,
                area=Decimal("84.9"),
                floor=12,
                building_year=2019,
                property_type="아파트",
            ),
        ]


# ========================================
# Address Converter
# ========================================


class AddressConverter:
    """주소 -> 법정동코드 변환기"""

    # 간소화된 법정동코드 매핑
    DISTRICT_CODES = {
        "강남구": "11680",
        "서초구": "11650",
        "송파구": "11710",
        "강동구": "11740",
        "마포구": "11440",
        "용산구": "11170",
        "성동구": "11200",
        "광진구": "11215",
        "종로구": "11110",
        "중구": "11140",
    }

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    async def get_lawd_cd(self, address: str) -> str:
        """주소에서 법정동코드 추출

        실제로는 지오코딩 API를 사용하여 정확한 법정동코드를 조회해야 함
        """
        for district, code in self.DISTRICT_CODES.items():
            if district in address:
                return code

        return "11680"  # 기본값 (강남구)


# ========================================
# Kakao Map API
# ========================================


class KakaoMapAPI:
    """카카오맵 API 클라이언트"""

    BASE_URL = "https://dapi.kakao.com/v2/local"

    def __init__(self, api_key: str, mock_mode: bool = True):
        """
        Args:
            api_key: 카카오 REST API 키
            mock_mode: Mock 모드
        """
        self.api_key = api_key
        self.mock_mode = mock_mode
        self.headers = {"Authorization": f"KakaoAK {api_key}"}

    async def geocode(self, address: str) -> tuple[Optional[float], Optional[float]]:
        """주소 -> 좌표 변환

        Args:
            address: 주소

        Returns:
            (위도, 경도) 또는 (None, None)
        """
        if self.mock_mode:
            return 37.4979, 127.0276  # 강남역 좌표

        url = f"{self.BASE_URL}/search/address.json"
        params = {"query": address}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=self.headers) as response:
                data = await response.json()

                if data.get("documents"):
                    doc = data["documents"][0]
                    return float(doc["y"]), float(doc["x"])

                return None, None

    async def search_nearby(
        self, lat: float, lng: float, category: str, radius: int = 1000
    ) -> List[Dict[str, Any]]:
        """주변 시설 검색

        Args:
            lat: 위도
            lng: 경도
            category: 카테고리 코드 (예: SW8 - 지하철)
            radius: 검색 반경(m)

        Returns:
            시설 목록
        """
        if self.mock_mode:
            return self._mock_nearby_facilities(category)

        url = f"{self.BASE_URL}/search/category.json"
        params = {
            "category_group_code": category,
            "x": lng,
            "y": lat,
            "radius": radius,
            "sort": "distance",
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=self.headers) as response:
                data = await response.json()
                return data.get("documents", [])

    async def get_location_data(self, address: str) -> LocationData:
        """위치 정보 통합 수집

        Args:
            address: 주소

        Returns:
            위치 정보 (좌표 + 주변 시설)
        """
        lat, lng = await self.geocode(address)
        if not lat or not lng:
            raise ValueError(f"주소를 좌표로 변환할 수 없습니다: {address}")

        # 카테고리 코드
        categories = {
            "SW8": "subway",  # 지하철
            "SC4": "school",  # 학교
            "HP8": "hospital",  # 병원
            "MT1": "mart",  # 마트
            "AT4": "attraction",  # 관광명소/공원
        }

        facilities: Dict[str, Dict[str, Any]] = {}

        # 병렬로 주변 시설 검색
        tasks = [self.search_nearby(lat, lng, code) for code in categories.keys()]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for (code, name), result in zip(categories.items(), results):
            if not isinstance(result, Exception) and result:
                nearest = result[0]
                facilities[name] = {
                    "name": nearest.get("place_name"),
                    "distance": int(nearest.get("distance", 0)),
                    "count": len(result),
                }

        return LocationData(lat=lat, lng=lng, facilities=facilities)

    def _mock_nearby_facilities(self, category: str) -> List[Dict[str, Any]]:
        """Mock 주변 시설 데이터 (테스트용)"""
        mock_data = {
            "SW8": [{"place_name": "강남역 2호선", "distance": "250"}],
            "SC4": [{"place_name": "역삼초등학교", "distance": "450"}],
            "HP8": [{"place_name": "강남세브란스병원", "distance": "800"}],
            "MT1": [{"place_name": "이마트 역삼점", "distance": "600"}],
            "AT4": [{"place_name": "선릉공원", "distance": "350"}],
        }
        return mock_data.get(category, [])


# ========================================
# OCR & Document Parser
# ========================================


class ClovaOCR:
    """네이버 Clova OCR 클라이언트"""

    def __init__(self, api_url: str, secret_key: str, mock_mode: bool = True):
        """
        Args:
            api_url: Clova OCR API URL
            secret_key: Secret Key
            mock_mode: Mock 모드
        """
        self.api_url = api_url
        self.secret_key = secret_key
        self.mock_mode = mock_mode

    async def extract_text(self, file_path: str) -> str:
        """이미지/PDF에서 텍스트 추출

        Args:
            file_path: 파일 경로

        Returns:
            추출된 텍스트
        """
        if self.mock_mode:
            return "[Mock OCR 결과]\n표제부\n소재: 서울 강남구 역삼동 123-45\n면적: 84.5㎡"

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")

        with open(file_path, "rb") as f:
            file_data = base64.b64encode(f.read()).decode()

        payload = {
            "version": "V2",
            "requestId": f"req-{datetime.now().timestamp()}",
            "timestamp": 0,
            "images": [
                {
                    "format": "pdf" if file_path.endswith(".pdf") else "jpg",
                    "name": "document",
                    "data": file_data,
                }
            ],
        }

        headers = {"X-OCR-SECRET": self.secret_key, "Content-Type": "application/json"}

        async with aiohttp.ClientSession() as session:
            async with session.post(self.api_url, json=payload, headers=headers) as response:
                result = await response.json()

                texts = []
                for image in result.get("images", []):
                    for field in image.get("fields", []):
                        texts.append(field.get("inferText", ""))

                return "\n".join(texts)


class RegistryParser:
    """등기부등본 파서"""

    def parse(self, raw_text: str) -> Dict[str, Any]:
        """OCR 텍스트를 구조화된 데이터로 파싱

        Args:
            raw_text: OCR로 추출한 원문 텍스트

        Returns:
            파싱된 구조화 데이터
        """
        result: Dict[str, Any] = {
            "title_section": {},  # 표제부
            "gap_gu": [],  # 갑구 (소유권)
            "eul_gu": [],  # 을구 (담보권)
        }

        # 섹션 분리
        sections = self._split_sections(raw_text)

        # 각 섹션 파싱
        if "표제부" in sections:
            result["title_section"] = self._parse_title(sections["표제부"])

        if "갑구" in sections:
            result["gap_gu"] = self._parse_gap_gu(sections["갑구"])

        if "을구" in sections:
            result["eul_gu"] = self._parse_eul_gu(sections["을구"])

        return result

    def _split_sections(self, text: str) -> Dict[str, str]:
        """섹션별 분리"""
        sections: Dict[str, str] = {}
        patterns = {
            "표제부": r"\[표\s*제\s*부\](.*?)(?=\[갑\s*구\]|\[을\s*구\]|\Z)",
            "갑구": r"\[갑\s*구\](.*?)(?=\[을\s*구\]|\Z)",
            "을구": r"\[을\s*구\](.*?)(?=\Z)",
        }

        for name, pattern in patterns.items():
            match = re.search(pattern, text, re.DOTALL)
            if match:
                sections[name] = match.group(1).strip()

        return sections

    def _parse_title(self, text: str) -> Dict[str, str]:
        """표제부 파싱"""
        return {"raw": text}

    def _parse_gap_gu(self, text: str) -> List[Dict[str, Any]]:
        """갑구 파싱 (소유권 관련)"""
        entries: List[Dict[str, Any]] = []

        # 순위번호 패턴으로 항목 분리
        pattern = r"(\d+)\s+([\d.]+)\s+(\d+)\s+(.+?)(?=\d+\s+[\d.]+\s+\d+|\Z)"

        for match in re.finditer(pattern, text, re.DOTALL):
            entry = {
                "sequence": int(match.group(1)),
                "registration_date": match.group(2),
                "registration_number": match.group(3),
                "content": match.group(4).strip(),
                "right_type": self._extract_right_type(match.group(4)),
                "is_cancelled": "말소" in match.group(4),
            }
            entries.append(entry)

        return entries

    def _parse_eul_gu(self, text: str) -> List[Dict[str, Any]]:
        """을구 파싱 (담보권 관련)"""
        # 갑구와 동일한 구조
        return self._parse_gap_gu(text)

    def _extract_right_type(self, content: str) -> str:
        """권리 유형 추출"""
        right_types = [
            "소유권이전",
            "소유권보존",
            "가압류",
            "압류",
            "근저당권설정",
            "저당권설정",
            "전세권설정",
            "가등기",
            "가처분",
            "경매개시결정",
        ]

        for rt in right_types:
            if rt in content:
                return rt

        return "기타"


# ========================================
# Data Store
# ========================================


class DataStore:
    """데이터 저장소 (PostgreSQL)"""

    def __init__(self, database_url: str):
        """
        Args:
            database_url: PostgreSQL 연결 URL
        """
        self.database_url = database_url
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> None:
        """연결 풀 생성"""
        self.pool = await asyncpg.create_pool(self.database_url)

    async def close(self) -> None:
        """연결 종료"""
        if self.pool:
            await self.pool.close()

    async def save_auction_case(self, auction_property: AuctionProperty) -> bool:
        """경매 사건 저장

        Args:
            auction_property: 경매 물건 정보

        Returns:
            성공 여부
        """
        if not self.pool:
            raise RuntimeError("Database not connected. Call connect() first.")

        query = """
            INSERT INTO auction_cases
            (case_number, court, property_type, address, appraisal_value,
             minimum_bid, auction_date, bid_count, status)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ON CONFLICT (case_number)
            DO UPDATE SET
                minimum_bid = EXCLUDED.minimum_bid,
                auction_date = EXCLUDED.auction_date,
                bid_count = EXCLUDED.bid_count,
                status = EXCLUDED.status,
                updated_at = CURRENT_TIMESTAMP
        """

        async with self.pool.acquire() as conn:
            await conn.execute(
                query,
                auction_property.case_number,
                auction_property.court,
                auction_property.property_type.value,
                auction_property.address,
                auction_property.appraisal_value,
                auction_property.minimum_bid,
                auction_property.auction_date,
                auction_property.bid_count,
                auction_property.status.value,
            )

        return True

    async def get_auction_case(self, case_number: str) -> Optional[AuctionProperty]:
        """경매 사건 조회

        Args:
            case_number: 사건번호

        Returns:
            경매 물건 정보 또는 None
        """
        if not self.pool:
            raise RuntimeError("Database not connected. Call connect() first.")

        query = "SELECT * FROM auction_cases WHERE case_number = $1"

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, case_number)

            if row:
                return AuctionProperty(
                    case_number=row["case_number"],
                    court=row["court"],
                    property_type=PropertyType(row["property_type"]),
                    address=row["address"],
                    appraisal_value=row["appraisal_value"],
                    minimum_bid=row["minimum_bid"],
                    auction_date=row["auction_date"],
                    bid_count=row["bid_count"],
                    status=AuctionStatus(row["status"]),
                )

            return None

    async def save_transactions(self, transactions: List[RealTransaction]) -> None:
        """실거래 데이터 벌크 저장

        Args:
            transactions: 실거래 목록
        """
        if not self.pool:
            raise RuntimeError("Database not connected. Call connect() first.")

        if not transactions:
            return

        query = """
            INSERT INTO real_transactions
            (address, transaction_date, price, area, floor, building_year, property_type)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT DO NOTHING
        """

        async with self.pool.acquire() as conn:
            await conn.executemany(
                query,
                [
                    (
                        t.address,
                        t.transaction_date,
                        t.price,
                        float(t.area),
                        t.floor,
                        t.building_year,
                        t.property_type,
                    )
                    for t in transactions
                ],
            )


# ========================================
# Main Agent Class
# ========================================


class DataCollectorAgent:
    """데이터수집 에이전트 메인 클래스

    경매 정보, 실거래가, 위치 정보를 수집하고 통합하는 에이전트
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Args:
            config: 설정 딕셔너리
                - molit_api_key: 국토교통부 API 키
                - kakao_api_key: 카카오 API 키
                - ocr_url: Clova OCR URL
                - ocr_key: Clova OCR Secret Key
                - database_url: PostgreSQL 연결 URL
                - mock_mode: Mock 모드 (기본값: True)
        """
        self.config = config
        mock_mode = config.get("mock_mode", True)

        self.crawler = CourtAuctionCrawler(headless=True, mock_mode=mock_mode)
        self.molit_api = MolitRealTransactionAPI(
            config.get("molit_api_key", ""), mock_mode=mock_mode
        )
        self.kakao_api = KakaoMapAPI(config.get("kakao_api_key", ""), mock_mode=mock_mode)
        self.ocr = ClovaOCR(
            config.get("ocr_url", ""),
            config.get("ocr_key", ""),
            mock_mode=mock_mode,
        )
        self.registry_parser = RegistryParser()
        self.address_converter = AddressConverter(config.get("kakao_api_key"))
        self.data_store = DataStore(config.get("database_url", ""))
        self.rate_limiter = RateLimiter(
            requests_per_minute=20, min_delay=2.0, max_delay=5.0
        )

    async def collect(self, case_number: str) -> CollectedData:
        """전체 데이터 수집

        Args:
            case_number: 경매 사건번호 (예: 2024타경12345)

        Returns:
            수집된 통합 데이터

        Raises:
            Exception: 사건번호를 찾을 수 없거나 수집 실패 시
        """
        # 1. 경매 기본 정보 수집
        await self.rate_limiter.wait()

        with self.crawler as crawler:
            auction_property = crawler.search_by_case_number(case_number)

            if not auction_property:
                raise Exception(f"사건번호 {case_number}를 찾을 수 없습니다.")

            # 문서 수집
            documents = crawler.get_documents(case_number)

        # 2. 문서 OCR 및 파싱
        parsed_documents = await self._process_documents(documents, case_number)

        # 3. 실거래가 수집
        transactions = await self._collect_transactions(auction_property.address)

        # 4. 위치 정보 수집
        location_data = await self._collect_location_data(auction_property.address)

        # 5. 데이터베이스 저장 (선택적)
        if self.config.get("save_to_db", False):
            await self._save_to_database(auction_property, transactions)

        # 6. 결과 반환
        return CollectedData(
            auction_property=auction_property,
            documents=parsed_documents,
            real_transactions=transactions,
            location_data=location_data,
            collected_at=datetime.now(),
        )

    async def _process_documents(
        self, documents: List[Document], case_number: str
    ) -> List[Document]:
        """문서 OCR 및 파싱 처리"""
        parsed_documents = []

        for doc in documents:
            try:
                # OCR 텍스트 추출
                raw_text = await self.ocr.extract_text(doc.file_path)

                # 등기부등본인 경우 파싱
                parsed_data = {}
                if doc.doc_type == "registry":
                    parsed_data = self.registry_parser.parse(raw_text)

                parsed_documents.append(
                    Document(
                        case_number=case_number,
                        doc_type=doc.doc_type,
                        file_path=doc.file_path,
                        raw_text=raw_text,
                        parsed_data=parsed_data,
                        collected_at=datetime.now(),
                    )
                )
            except Exception as e:
                print(f"문서 처리 실패 ({doc.doc_type}): {str(e)}")
                # 실패해도 계속 진행
                parsed_documents.append(doc)

        return parsed_documents

    async def _collect_transactions(self, address: str) -> List[RealTransaction]:
        """실거래가 수집"""
        transactions = []

        try:
            # 주소 -> 법정동코드 변환
            lawd_cd = await self.address_converter.get_lawd_cd(address)

            # 최근 12개월 데이터 수집
            for month_offset in range(12):
                deal_ymd = self._get_deal_ymd(month_offset)

                await self.rate_limiter.wait()
                monthly_transactions = await self.molit_api.get_apartment_transactions(
                    lawd_cd, deal_ymd
                )
                transactions.extend(monthly_transactions)

        except Exception as e:
            print(f"실거래가 수집 실패: {str(e)}")

        return transactions

    async def _collect_location_data(self, address: str) -> Optional[LocationData]:
        """위치 정보 수집"""
        try:
            await self.rate_limiter.wait()
            return await self.kakao_api.get_location_data(address)
        except Exception as e:
            print(f"위치 정보 수집 실패: {str(e)}")
            return None

    async def _save_to_database(
        self, auction_property: AuctionProperty, transactions: List[RealTransaction]
    ) -> None:
        """데이터베이스 저장"""
        try:
            await self.data_store.connect()
            await self.data_store.save_auction_case(auction_property)
            await self.data_store.save_transactions(transactions)
        except Exception as e:
            print(f"데이터베이스 저장 실패: {str(e)}")
        finally:
            await self.data_store.close()

    def _get_deal_ymd(self, months_ago: int) -> str:
        """N개월 전 YYYYMM 반환"""
        target_date = date.today()

        # 개월 수만큼 빼기
        year = target_date.year
        month = target_date.month - months_ago

        while month <= 0:
            month += 12
            year -= 1

        return f"{year:04d}{month:02d}"


# ========================================
# Utility Functions
# ========================================


async def collect_auction_data(case_number: str, config: Dict[str, Any]) -> CollectedData:
    """경매 데이터 수집 유틸리티 함수

    Args:
        case_number: 사건번호
        config: 설정

    Returns:
        수집된 데이터
    """
    agent = DataCollectorAgent(config)
    return await agent.collect(case_number)


# ========================================
# Example Usage
# ========================================


async def main() -> None:
    """사용 예시"""
    config = {
        "molit_api_key": "your-molit-api-key",
        "kakao_api_key": "your-kakao-api-key",
        "ocr_url": "your-ocr-url",
        "ocr_key": "your-ocr-key",
        "database_url": "postgresql://user:pass@localhost/auction_db",
        "mock_mode": True,  # 테스트용 Mock 모드
        "save_to_db": False,
    }

    agent = DataCollectorAgent(config)

    # 경매 정보 수집
    case_number = "2024타경12345"
    collected_data = await agent.collect(case_number)

    print(f"사건번호: {collected_data.auction_property.case_number}")
    print(f"주소: {collected_data.auction_property.address}")
    print(f"감정가: {collected_data.auction_property.appraisal_value:,}원")
    print(f"최저입찰가: {collected_data.auction_property.minimum_bid:,}원")
    print(f"수집 문서 수: {len(collected_data.documents)}")
    print(f"실거래 건수: {len(collected_data.real_transactions)}")

    if collected_data.location_data:
        print(f"좌표: ({collected_data.location_data.lat}, {collected_data.location_data.lng})")
        print(f"주변 시설: {list(collected_data.location_data.facilities.keys())}")


if __name__ == "__main__":
    asyncio.run(main())
