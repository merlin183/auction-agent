"""경매 물건 기본 데이터 모델"""
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class PropertyType(str, Enum):
    """물건 종류"""
    APARTMENT = "아파트"
    VILLA = "빌라"
    OFFICETEL = "오피스텔"
    HOUSE = "단독주택"
    LAND = "토지"
    COMMERCIAL = "상가"
    OFFICE = "사무실"
    FACTORY = "공장"
    OTHER = "기타"


class AuctionStatus(str, Enum):
    """경매 상태"""
    SCHEDULED = "진행예정"
    IN_PROGRESS = "진행중"
    SUCCESSFUL = "낙찰"
    FAILED = "유찰"
    CANCELLED = "취하"
    SUSPENDED = "정지"


class AuctionProperty(BaseModel):
    """경매 물건 기본 정보"""

    # 사건 정보
    case_number: str = Field(..., description="사건번호 (예: 2024타경12345)")
    court: str = Field(..., description="관할법원")

    # 물건 정보
    property_type: PropertyType = Field(..., description="물건 종류")
    address: str = Field(..., description="소재지")
    detail_address: Optional[str] = Field(None, description="상세주소")

    # 면적 정보
    land_area_sqm: Optional[Decimal] = Field(None, description="대지면적(㎡)")
    building_area_sqm: Optional[Decimal] = Field(None, description="건물면적(㎡)")
    exclusive_area_sqm: Optional[Decimal] = Field(None, description="전용면적(㎡)")

    # 건물 정보 (건물인 경우)
    building_year: Optional[int] = Field(None, description="건축년도")
    floor: Optional[int] = Field(None, description="층수")
    total_floors: Optional[int] = Field(None, description="총 층수")
    rooms: Optional[int] = Field(None, description="방 수")
    bathrooms: Optional[int] = Field(None, description="화장실 수")

    # 가격 정보
    appraisal_value: int = Field(..., description="감정가(원)")
    minimum_bid: int = Field(..., description="최저입찰가(원)")
    bid_count: int = Field(default=1, description="입찰 회차")

    # 일정 정보
    auction_date: date = Field(..., description="매각기일")
    appraisal_date: Optional[date] = Field(None, description="감정평가일")

    # 상태
    status: AuctionStatus = Field(default=AuctionStatus.SCHEDULED)

    # 좌표
    latitude: Optional[float] = Field(None, description="위도")
    longitude: Optional[float] = Field(None, description="경도")

    # 메타데이터
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @property
    def land_area_pyung(self) -> Optional[Decimal]:
        """대지면적(평)"""
        if self.land_area_sqm:
            return self.land_area_sqm / Decimal("3.305785")
        return None

    @property
    def exclusive_area_pyung(self) -> Optional[Decimal]:
        """전용면적(평)"""
        if self.exclusive_area_sqm:
            return self.exclusive_area_sqm / Decimal("3.305785")
        return None

    @property
    def bid_rate(self) -> Decimal:
        """입찰율 (최저가/감정가)"""
        return Decimal(self.minimum_bid) / Decimal(self.appraisal_value)

    @property
    def discount_rate(self) -> Decimal:
        """할인율"""
        return Decimal("1") - self.bid_rate


class AuctionDocument(BaseModel):
    """경매 문서"""

    case_number: str
    document_type: str  # 현황조사서, 감정평가서, 매각물건명세서 등
    document_url: Optional[str] = None
    content: Optional[str] = None
    parsed_data: Optional[dict] = None


class AuctionSchedule(BaseModel):
    """기일 내역"""

    case_number: str
    schedule_date: date
    schedule_type: str  # 매각기일, 배당기일 등
    location: str
    result: Optional[str] = None
    highest_bid: Optional[int] = None
    bidder_count: Optional[int] = None
