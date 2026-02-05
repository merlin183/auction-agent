"""위험평가 데이터 모델"""
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    """위험 수준"""
    LOW = "낮음"
    MEDIUM = "보통"
    HIGH = "높음"
    CRITICAL = "매우 높음"


class RiskGrade(str, Enum):
    """위험 등급"""
    A = "A"  # 안전
    B = "B"  # 보통
    C = "C"  # 위험
    D = "D"  # 고위험


class RiskItem(BaseModel):
    """개별 위험 항목"""

    name: str
    category: str
    score: float = Field(ge=0, le=100)
    weight: float = Field(ge=0, le=1)
    level: RiskLevel
    description: str
    mitigation: Optional[str] = None


class CategoryRisk(BaseModel):
    """카테고리별 위험"""

    name: str
    score: float = Field(ge=0, le=100)
    level: RiskLevel
    weight: float = Field(ge=0, le=1)
    items: list[RiskItem] = Field(default_factory=list)
    summary: str = ""


class RedFlag(BaseModel):
    """위험 신호"""

    name: str
    severity: RiskLevel
    description: str
    recommendation: str


class RiskAssessmentResult(BaseModel):
    """위험평가 결과"""

    case_number: str

    # 종합 점수
    total_score: float = Field(ge=0, le=100)
    grade: RiskGrade
    level: RiskLevel

    # 카테고리별 위험
    rights_risk: CategoryRisk = Field(..., description="권리 리스크 (40%)")
    market_risk: CategoryRisk = Field(..., description="시장 리스크 (20%)")
    property_risk: CategoryRisk = Field(..., description="물건 리스크 (20%)")
    eviction_risk: CategoryRisk = Field(..., description="명도 리스크 (20%)")

    # 위험 신호
    red_flags: list[RedFlag] = Field(default_factory=list)

    # 추천
    recommendations: list[str] = Field(default_factory=list)

    # 입문자 적합성
    beginner_friendly: bool = Field(default=False)
    beginner_note: Optional[str] = None

    # 상세 리포트
    detailed_report: str = Field(default="")

    @property
    def weighted_score(self) -> float:
        """가중 평균 점수"""
        return (
            self.rights_risk.score * 0.4
            + self.market_risk.score * 0.2
            + self.property_risk.score * 0.2
            + self.eviction_risk.score * 0.2
        )
