"""입지분석 데이터 모델"""
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class POICategory(str, Enum):
    """POI 카테고리"""
    SUBWAY = "지하철역"
    BUS_STOP = "버스정류장"
    SCHOOL = "학교"
    HOSPITAL = "병원"
    MART = "대형마트"
    CONVENIENCE = "편의점"
    PARK = "공원"
    BANK = "은행"
    CAFE = "카페"


class POI(BaseModel):
    """주변 시설 (Point of Interest)"""

    name: str
    category: POICategory
    distance_meters: int
    walk_time_minutes: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class TransportScore(BaseModel):
    """교통 점수"""

    total_score: float = Field(ge=0, le=100)

    # 지하철
    nearest_subway: Optional[str] = None
    subway_distance_meters: Optional[int] = None
    subway_walk_minutes: Optional[int] = None
    subway_lines: list[str] = Field(default_factory=list)

    # 버스
    bus_stops_within_300m: int = 0
    bus_routes_count: int = 0

    # 도로
    main_road_access: bool = False
    highway_distance_km: Optional[float] = None

    note: str = ""


class EducationScore(BaseModel):
    """교육 점수"""

    total_score: float = Field(ge=0, le=100)

    # 학교
    elementary_schools: list[str] = Field(default_factory=list)
    middle_schools: list[str] = Field(default_factory=list)
    high_schools: list[str] = Field(default_factory=list)

    nearest_elementary_meters: Optional[int] = None
    nearest_middle_meters: Optional[int] = None
    nearest_high_meters: Optional[int] = None

    # 학원가
    academy_density: str = "보통"  # 높음, 보통, 낮음

    # 대학교
    universities_within_3km: list[str] = Field(default_factory=list)

    note: str = ""


class AmenityScore(BaseModel):
    """편의시설 점수"""

    total_score: float = Field(ge=0, le=100)

    # 의료
    hospitals_within_1km: int = 0
    pharmacy_within_500m: int = 0

    # 쇼핑
    marts_within_1km: list[str] = Field(default_factory=list)
    convenience_stores_within_300m: int = 0

    # 공원/녹지
    parks_within_500m: list[str] = Field(default_factory=list)
    green_ratio: Optional[float] = None  # 녹지율

    note: str = ""


class DevelopmentInfo(BaseModel):
    """개발 호재 정보"""

    name: str
    development_type: str  # 재개발, 재건축, 신규노선, 산업단지 등
    status: str  # 예정, 진행중, 완료
    expected_completion: Optional[str] = None
    distance_km: Optional[float] = None
    impact_level: str = "보통"  # 높음, 보통, 낮음
    description: str = ""


class DemographicInfo(BaseModel):
    """인구통계 정보"""

    population: Optional[int] = None
    households: Optional[int] = None
    population_change_1y: Optional[float] = None  # 1년 인구 증감률
    avg_age: Optional[float] = None
    young_population_ratio: Optional[float] = None  # 청년 인구 비율
    note: str = ""


class LocationAnalysisResult(BaseModel):
    """입지분석 결과"""

    case_number: str
    address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    # 카테고리별 점수
    total_score: float = Field(ge=0, le=100)
    transport_score: TransportScore
    education_score: EducationScore
    amenity_score: AmenityScore

    # 개발 호재
    development_info: list[DevelopmentInfo] = Field(default_factory=list)
    development_score: float = Field(default=50, ge=0, le=100)

    # 인구통계
    demographic_info: Optional[DemographicInfo] = None

    # 주변 시설 목록
    nearby_pois: list[POI] = Field(default_factory=list)

    # 지역 시세
    area_average_price_per_pyung: Optional[int] = None
    price_rank_in_district: Optional[str] = None  # 상위 10%, 중위권 등

    # 종합 평가
    summary: str = ""
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    outlook: str = ""  # 향후 전망

    @property
    def weighted_score(self) -> float:
        """가중 평균 점수"""
        return (
            self.transport_score.total_score * 0.35
            + self.education_score.total_score * 0.25
            + self.amenity_score.total_score * 0.20
            + self.development_score * 0.20
        )
