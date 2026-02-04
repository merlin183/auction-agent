"""검증(레드팀) 데이터 모델"""
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ValidationSeverity(str, Enum):
    """검증 심각도"""
    INFO = "정보"
    WARNING = "경고"
    ERROR = "오류"
    CRITICAL = "치명적"


class ValidationStatus(str, Enum):
    """검증 상태"""
    PASSED = "통과"
    PASSED_WITH_WARNINGS = "조건부 통과"
    NEEDS_REVIEW = "검토 필요"
    FAILED = "실패"


class ValidationIssue(BaseModel):
    """검증 이슈"""

    id: str
    severity: ValidationSeverity
    category: str  # data_integrity, cross_validation, statistical, adversarial
    source_agent: str
    field_path: str
    issue_type: str
    description: str
    expected_value: Optional[Any] = None
    actual_value: Optional[Any] = None
    suggested_fix: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0, le=1)


class CrossValidationResult(BaseModel):
    """교차 검증 결과"""

    agents_compared: list[str]
    field_compared: str
    values: dict[str, Any]  # {agent_name: value}
    is_consistent: bool
    discrepancy_rate: float
    consensus_value: Optional[Any] = None
    note: str = ""


class AgentValidation(BaseModel):
    """에이전트 출력 검증"""

    agent_name: str
    validation_time: datetime
    issues: list[ValidationIssue] = Field(default_factory=list)
    status: ValidationStatus
    reliability_score: float = Field(ge=0, le=100)
    summary: str = ""


class RedTeamReport(BaseModel):
    """레드팀 종합 보고서"""

    case_id: str
    validation_time: datetime = Field(default_factory=datetime.now)

    # 개별 검증 결과
    agent_validations: dict[str, AgentValidation] = Field(default_factory=dict)

    # 교차 검증 결과
    cross_validations: list[CrossValidationResult] = Field(default_factory=list)

    # 통계적 이상 탐지
    statistical_anomalies: list[ValidationIssue] = Field(default_factory=list)

    # 적대적 검증 결과
    adversarial_findings: list[ValidationIssue] = Field(default_factory=list)

    # 종합
    overall_status: ValidationStatus
    overall_reliability: float = Field(ge=0, le=100)
    critical_issues: list[ValidationIssue] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)

    # 최종 승인
    approved: bool = False
    approval_conditions: list[str] = Field(default_factory=list)

    @property
    def total_issues_count(self) -> int:
        """총 이슈 수"""
        return (
            sum(len(v.issues) for v in self.agent_validations.values())
            + len(self.statistical_anomalies)
            + len(self.adversarial_findings)
        )

    @property
    def critical_count(self) -> int:
        """치명적 이슈 수"""
        return len(
            [i for i in self.critical_issues if i.severity == ValidationSeverity.CRITICAL]
        )

    @property
    def error_count(self) -> int:
        """오류 이슈 수"""
        return len(
            [i for i in self.critical_issues if i.severity == ValidationSeverity.ERROR]
        )
