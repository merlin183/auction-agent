"""권리분석 데이터 모델"""
from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class RightType(str, Enum):
    """권리 유형"""
    MORTGAGE = "근저당권"
    SEIZURE = "압류"
    PROVISIONAL_SEIZURE = "가압류"
    PROVISIONAL_DISPOSITION = "가처분"
    PROVISIONAL_REGISTRATION = "가등기"
    LEASE = "전세권"
    SUPERFICIES = "지상권"
    EASEMENT = "지역권"
    AUCTION_REGISTRATION = "경매개시결정등기"
    OWNERSHIP = "소유권"
    TRUST = "신탁"


class RightStatus(str, Enum):
    """권리 상태 (낙찰 후)"""
    EXTINGUISHED = "소멸"
    ASSUMED = "인수"
    UNCERTAIN = "불확실"


class RiskLevel(str, Enum):
    """위험 등급"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RegistryEntry(BaseModel):
    """등기 항목"""

    entry_number: str = Field(..., description="순위번호")
    registration_date: date = Field(..., description="등기일자")
    receipt_date: Optional[date] = Field(None, description="접수일자")
    right_type: RightType = Field(..., description="권리 유형")
    right_holder: str = Field(..., description="권리자")
    amount: Optional[int] = Field(None, description="채권액/설정액")
    purpose: Optional[str] = Field(None, description="등기 목적")
    cause: Optional[str] = Field(None, description="등기 원인")

    # 분석 결과
    status: Optional[RightStatus] = Field(None, description="낙찰 후 상태")
    note: Optional[str] = Field(None, description="비고")


class TenantInfo(BaseModel):
    """임차인 정보"""

    name: Optional[str] = Field(None, description="임차인명")
    move_in_date: Optional[date] = Field(None, description="전입일자")
    fixed_date: Optional[date] = Field(None, description="확정일자")
    deposit: Optional[int] = Field(None, description="보증금")
    monthly_rent: Optional[int] = Field(None, description="월세")
    occupying: bool = Field(default=True, description="점유 여부")

    # 분석 결과
    has_priority: Optional[bool] = Field(None, description="대항력 여부")
    priority_amount: Optional[int] = Field(None, description="최우선변제금")
    expected_dividend: Optional[int] = Field(None, description="예상 배당액")
    assumed_deposit: Optional[int] = Field(None, description="인수 보증금")
    note: Optional[str] = None


class SpecialRight(BaseModel):
    """특수 권리"""

    right_type: str = Field(..., description="권리 유형 (법정지상권, 유치권 등)")
    risk_level: RiskLevel
    description: str
    estimated_amount: Optional[int] = Field(None, description="추정 금액")
    mitigation: Optional[str] = Field(None, description="대응 방안")


class ReferenceRight(BaseModel):
    """말소기준권리"""

    entry_number: str
    right_type: RightType
    registration_date: date
    right_holder: str
    note: Optional[str] = None


class RightsAnalysisResult(BaseModel):
    """권리분석 결과"""

    case_number: str

    # 말소기준권리
    reference_right: ReferenceRight = Field(..., description="말소기준권리")

    # 권리 분류
    assumed_rights: list[RegistryEntry] = Field(
        default_factory=list, description="인수 권리"
    )
    extinguished_rights: list[RegistryEntry] = Field(
        default_factory=list, description="소멸 권리"
    )

    # 금액 분석
    total_assumed_amount: int = Field(default=0, description="총 인수금액")

    # 임차인 분석
    tenants: list[TenantInfo] = Field(default_factory=list, description="임차인 목록")
    total_assumed_deposit: int = Field(default=0, description="총 인수 보증금")

    # 특수 권리
    special_rights: list[SpecialRight] = Field(
        default_factory=list, description="특수 권리"
    )

    # 법정지상권
    statutory_superficies: Optional[dict] = Field(
        None, description="법정지상권 분석 결과"
    )

    # 유치권
    lien: Optional[dict] = Field(None, description="유치권 분석 결과")

    # 종합 평가
    risk_level: RiskLevel = Field(default=RiskLevel.MEDIUM)
    risk_score: int = Field(default=50, ge=0, le=100)
    summary: str = Field(default="")
    warnings: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)

    # 입문자 적합성
    beginner_suitable: bool = Field(default=False)
    beginner_note: Optional[str] = None
