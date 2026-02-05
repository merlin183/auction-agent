"""레드팀 에이전트 - 분석 결과 검증 및 품질 보증"""
import json
import re
from collections import Counter
from datetime import datetime
from typing import Any, Optional

import numpy as np
from scipy import stats
from langchain_core.language_models import BaseChatModel

from src.models.validation import (
    AgentValidation,
    CrossValidationResult,
    RedTeamReport,
    ValidationIssue,
    ValidationSeverity,
    ValidationStatus,
)
from src.services.llm import get_high_reasoning_llm
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DataIntegrityValidator:
    """데이터 무결성 검증기"""

    # 각 에이전트별 필수 출력 스키마
    REQUIRED_SCHEMAS = {
        "rights_analyzer": {
            "case_number": {"type": str, "pattern": r"^\d{4}타경\d+$"},
            "reference_right": {"type": dict, "required_keys": ["type", "date"]},
            "assumed_rights": {"type": list},
            "extinguished_rights": {"type": list},
            "total_assumed_amount": {"type": (int, float), "min": 0},
            "risk_level": {"type": str, "values": ["LOW", "MEDIUM", "HIGH", "CRITICAL"]},
        },
        "valuator": {
            "appraisal_value": {"type": int, "min": 0},
            "estimated_market_price": {"type": int, "min": 0},
            "price_per_pyung": {"type": (int, float), "min": 0},
            "confidence": {"type": float, "min": 0, "max": 1},
            "comparables_count": {"type": int, "min": 0},
        },
        "location_analyzer": {
            "total_score": {"type": (int, float), "min": 0, "max": 100},
            "transport_score": {"type": (int, float), "min": 0, "max": 100},
            "education_score": {"type": (int, float), "min": 0, "max": 100},
            "coordinates": {"type": dict, "required_keys": ["lat", "lng"]},
        },
        "risk_assessor": {
            "total_score": {"type": (int, float), "min": 0, "max": 100},
            "grade": {"type": str, "values": ["A", "B", "C", "D"]},
            "beginner_friendly": {"type": bool},
        },
        "bid_strategist": {
            "optimal_bid": {"type": int, "min": 0},
            "bid_rate": {"type": float, "min": 0, "max": 1.5},
            "expected_profit": {"type": (int, float)},
            "win_probability": {"type": float, "min": 0, "max": 1},
        },
    }

    def validate(self, agent_name: str, output: dict) -> list[ValidationIssue]:
        """에이전트 출력 무결성 검증"""
        issues = []
        schema = self.REQUIRED_SCHEMAS.get(agent_name, {})

        for field_name, rules in schema.items():
            issue = self._validate_field(agent_name, output, field_name, rules)
            if issue:
                issues.append(issue)

        return issues

    def _validate_field(
        self, agent_name: str, output: dict, field_name: str, rules: dict
    ) -> Optional[ValidationIssue]:
        """개별 필드 검증"""

        # 필드 존재 확인
        value = output.get(field_name)
        if value is None:
            return ValidationIssue(
                id=f"{agent_name}_{field_name}_missing",
                severity=ValidationSeverity.ERROR,
                category="data_integrity",
                source_agent=agent_name,
                field_path=field_name,
                issue_type="missing_field",
                description=f"필수 필드 '{field_name}'이(가) 누락되었습니다.",
                confidence=1.0,
            )

        # 타입 검증
        expected_type = rules.get("type")
        if expected_type and not isinstance(value, expected_type):
            return ValidationIssue(
                id=f"{agent_name}_{field_name}_type",
                severity=ValidationSeverity.ERROR,
                category="data_integrity",
                source_agent=agent_name,
                field_path=field_name,
                issue_type="type_mismatch",
                description=f"타입 불일치: '{field_name}'",
                expected_value=str(expected_type),
                actual_value=str(type(value)),
                confidence=1.0,
            )

        # 범위 검증
        min_val = rules.get("min")
        max_val = rules.get("max")

        if min_val is not None and isinstance(value, (int, float)) and value < min_val:
            return ValidationIssue(
                id=f"{agent_name}_{field_name}_range",
                severity=ValidationSeverity.WARNING,
                category="data_integrity",
                source_agent=agent_name,
                field_path=field_name,
                issue_type="out_of_range",
                description=f"값이 허용 범위를 벗어남: {value} < {min_val}",
                expected_value=f">= {min_val}",
                actual_value=value,
                confidence=1.0,
            )

        if max_val is not None and isinstance(value, (int, float)) and value > max_val:
            return ValidationIssue(
                id=f"{agent_name}_{field_name}_range",
                severity=ValidationSeverity.WARNING,
                category="data_integrity",
                source_agent=agent_name,
                field_path=field_name,
                issue_type="out_of_range",
                description=f"값이 허용 범위를 벗어남: {value} > {max_val}",
                expected_value=f"<= {max_val}",
                actual_value=value,
                confidence=1.0,
            )

        # 허용값 검증
        allowed_values = rules.get("values")
        if allowed_values and value not in allowed_values:
            return ValidationIssue(
                id=f"{agent_name}_{field_name}_invalid",
                severity=ValidationSeverity.ERROR,
                category="data_integrity",
                source_agent=agent_name,
                field_path=field_name,
                issue_type="invalid_value",
                description=f"허용되지 않은 값: '{value}'",
                expected_value=str(allowed_values),
                actual_value=value,
                confidence=1.0,
            )

        # 딕셔너리 필수 키 검증
        required_keys = rules.get("required_keys")
        if required_keys and isinstance(value, dict):
            missing_keys = [k for k in required_keys if k not in value]
            if missing_keys:
                return ValidationIssue(
                    id=f"{agent_name}_{field_name}_missing_keys",
                    severity=ValidationSeverity.ERROR,
                    category="data_integrity",
                    source_agent=agent_name,
                    field_path=field_name,
                    issue_type="missing_keys",
                    description=f"필수 키 누락: {', '.join(missing_keys)}",
                    expected_value=str(required_keys),
                    actual_value=str(list(value.keys())),
                    confidence=1.0,
                )

        # 패턴 검증
        pattern = rules.get("pattern")
        if pattern and isinstance(value, str):
            if not re.match(pattern, value):
                return ValidationIssue(
                    id=f"{agent_name}_{field_name}_pattern",
                    severity=ValidationSeverity.WARNING,
                    category="data_integrity",
                    source_agent=agent_name,
                    field_path=field_name,
                    issue_type="pattern_mismatch",
                    description=f"패턴 불일치: '{value}'",
                    expected_value=f"패턴: {pattern}",
                    actual_value=value,
                    confidence=0.8,
                )

        return None


class CrossValidator:
    """에이전트 간 교차 검증기"""

    # 교차 검증 규칙
    CROSS_VALIDATION_RULES = [
        {
            "name": "감정가 일치",
            "agents": ["valuator", "rights_analyzer", "risk_assessor"],
            "field": "appraisal_value",
            "tolerance": 0,  # 정확히 일치해야 함
        },
        {
            "name": "인수금액 일치",
            "agents": ["rights_analyzer", "bid_strategist"],
            "field": "total_assumed_amount",
            "tolerance": 0,
        },
        {
            "name": "시세 범위 검증",
            "agents": ["valuator", "location_analyzer"],
            "custom_check": "market_price_within_location_range",
        },
        {
            "name": "입찰가 범위 검증",
            "agents": ["valuator", "bid_strategist"],
            "custom_check": "bid_within_valuation_range",
        },
    ]

    def validate(self, agent_outputs: dict[str, dict]) -> list[CrossValidationResult]:
        """교차 검증 수행"""
        results = []

        for rule in self.CROSS_VALIDATION_RULES:
            result = self._apply_rule(rule, agent_outputs)
            if result:
                results.append(result)

        return results

    def _apply_rule(
        self, rule: dict, outputs: dict[str, dict]
    ) -> Optional[CrossValidationResult]:
        """개별 교차 검증 규칙 적용"""

        rule_name = rule["name"]
        agents = rule["agents"]

        # 필요한 에이전트 출력이 모두 있는지 확인
        available_agents = [a for a in agents if a in outputs]
        if len(available_agents) < 2:
            return None

        # 단순 필드 비교
        if "field" in rule:
            return self._compare_field(
                rule_name,
                available_agents,
                outputs,
                rule["field"],
                rule.get("tolerance", 0),
            )

        # 커스텀 체크
        if "custom_check" in rule:
            return self._custom_check(
                rule["custom_check"], rule_name, available_agents, outputs
            )

        return None

    def _compare_field(
        self,
        rule_name: str,
        agents: list[str],
        outputs: dict,
        field: str,
        tolerance: float,
    ) -> CrossValidationResult:
        """필드 값 비교"""

        values = {}
        for agent in agents:
            value = outputs[agent].get(field)
            if value is not None:
                values[agent] = value

        if len(values) < 2:
            return CrossValidationResult(
                agents_compared=agents,
                field_compared=field,
                values=values,
                is_consistent=True,
                discrepancy_rate=0,
                consensus_value=list(values.values())[0] if values else None,
                note="비교 대상 부족",
            )

        # 불일치율 계산
        all_values = list(values.values())

        if isinstance(all_values[0], (int, float)):
            # 수치형 비교
            avg = sum(all_values) / len(all_values)
            max_diff = max(abs(v - avg) for v in all_values)
            discrepancy_rate = max_diff / avg if avg > 0 else 0
            is_consistent = discrepancy_rate <= tolerance
            consensus_value = avg
        else:
            # 범주형 비교
            counts = Counter(all_values)
            most_common = counts.most_common(1)[0]
            discrepancy_rate = 1 - (most_common[1] / len(all_values))
            is_consistent = discrepancy_rate == 0
            consensus_value = most_common[0]

        return CrossValidationResult(
            agents_compared=agents,
            field_compared=field,
            values=values,
            is_consistent=is_consistent,
            discrepancy_rate=discrepancy_rate,
            consensus_value=consensus_value,
            note=f"불일치율 {discrepancy_rate*100:.1f}%" if not is_consistent else "일치",
        )

    def _custom_check(
        self, check_name: str, rule_name: str, agents: list[str], outputs: dict
    ) -> Optional[CrossValidationResult]:
        """커스텀 검증 로직"""

        if check_name == "bid_within_valuation_range":
            # 입찰가가 가치평가 범위 내인지 확인
            valuation = outputs.get("valuator", {})
            bid = outputs.get("bid_strategist", {})

            appraisal = valuation.get("appraisal_value", 0)
            market_price = valuation.get("estimated_market_price", 0)
            optimal_bid = bid.get("optimal_bid", 0)

            # 입찰가는 감정가의 50% ~ 시세의 90% 범위 내여야 함
            min_acceptable = appraisal * 0.5
            max_acceptable = market_price * 0.9

            is_consistent = min_acceptable <= optimal_bid <= max_acceptable

            return CrossValidationResult(
                agents_compared=agents,
                field_compared="optimal_bid vs valuation",
                values={
                    "optimal_bid": optimal_bid,
                    "appraisal_value": appraisal,
                    "market_price": market_price,
                },
                is_consistent=is_consistent,
                discrepancy_rate=0 if is_consistent else 1,
                consensus_value=None,
                note=f"입찰가 {optimal_bid:,}원, 허용범위 {min_acceptable:,.0f}~{max_acceptable:,.0f}원",
            )

        if check_name == "market_price_within_location_range":
            # 시세가 입지 분석의 평균 시세와 비슷한지
            valuation = outputs.get("valuator", {})
            location = outputs.get("location_analyzer", {})

            estimated_price = valuation.get("estimated_market_price", 0)
            area_avg_price = location.get("area_average_price", estimated_price)

            if area_avg_price > 0:
                diff_rate = abs(estimated_price - area_avg_price) / area_avg_price
            else:
                diff_rate = 0

            is_consistent = diff_rate <= 0.2  # 20% 이내 허용

            return CrossValidationResult(
                agents_compared=agents,
                field_compared="market_price vs area_average",
                values={
                    "estimated_market_price": estimated_price,
                    "area_average_price": area_avg_price,
                },
                is_consistent=is_consistent,
                discrepancy_rate=diff_rate,
                consensus_value=(estimated_price + area_avg_price) / 2,
                note=f"시세 차이율 {diff_rate*100:.1f}%",
            )

        return None


class StatisticalAnomalyDetector:
    """통계적 이상 탐지기"""

    def __init__(self):
        self.historical_data = {}  # 과거 분석 데이터 캐시

    def detect(
        self, agent_outputs: dict[str, dict], historical_cases: list[dict]
    ) -> list[ValidationIssue]:
        """통계적 이상치 탐지"""

        issues = []

        # 1. Z-Score 기반 이상치 탐지
        z_score_issues = self._z_score_detection(agent_outputs, historical_cases)
        issues.extend(z_score_issues)

        # 2. IQR 기반 극단값 탐지
        iqr_issues = self._iqr_detection(agent_outputs, historical_cases)
        issues.extend(iqr_issues)

        # 3. 비율 검증
        ratio_issues = self._ratio_validation(agent_outputs)
        issues.extend(ratio_issues)

        return issues

    def _z_score_detection(
        self, outputs: dict, historical: list[dict]
    ) -> list[ValidationIssue]:
        """Z-Score 기반 이상치 탐지"""

        issues = []

        # 검증할 수치 필드들
        fields_to_check = [
            ("valuator", "price_per_pyung", "평당가"),
            ("valuator", "bid_rate_suggestion", "제안낙찰율"),
            ("risk_assessor", "total_score", "위험점수"),
            ("bid_strategist", "expected_profit_rate", "예상수익률"),
        ]

        for agent, field, label in fields_to_check:
            current_value = outputs.get(agent, {}).get(field)
            if current_value is None:
                continue

            # 과거 데이터에서 동일 필드 값 수집
            historical_values = [
                case.get(agent, {}).get(field)
                for case in historical
                if case.get(agent, {}).get(field) is not None
            ]

            if len(historical_values) < 10:
                continue

            # Z-Score 계산
            mean = np.mean(historical_values)
            std = np.std(historical_values)

            if std > 0:
                z_score = (current_value - mean) / std
            else:
                z_score = 0

            # |Z| > 3 이면 이상치
            if abs(z_score) > 3:
                severity = (
                    ValidationSeverity.WARNING
                    if abs(z_score) < 4
                    else ValidationSeverity.ERROR
                )

                issues.append(
                    ValidationIssue(
                        id=f"stat_{agent}_{field}",
                        severity=severity,
                        category="statistical_anomaly",
                        source_agent=agent,
                        field_path=field,
                        issue_type="z_score_outlier",
                        description=f"{label}이(가) 통계적 이상치입니다 (Z={z_score:.2f})",
                        expected_value=f"평균 {mean:,.0f} ± {std:,.0f}",
                        actual_value=current_value,
                        suggested_fix="값의 근거를 재확인하세요.",
                        confidence=min(0.99, 0.5 + abs(z_score) * 0.1),
                    )
                )

        return issues

    def _iqr_detection(
        self, outputs: dict, historical: list[dict]
    ) -> list[ValidationIssue]:
        """IQR 기반 극단값 탐지"""

        issues = []

        # 가격 관련 필드 IQR 검증
        valuator = outputs.get("valuator", {})
        appraisal = valuator.get("appraisal_value", 0)
        market = valuator.get("estimated_market_price", 0)

        if appraisal > 0 and market > 0:
            # 감정가 대비 시세 비율
            price_ratio = market / appraisal

            # 일반적으로 0.7 ~ 1.3 범위
            if price_ratio < 0.5 or price_ratio > 1.5:
                issues.append(
                    ValidationIssue(
                        id="stat_price_ratio_extreme",
                        severity=ValidationSeverity.WARNING,
                        category="statistical_anomaly",
                        source_agent="valuator",
                        field_path="price_ratio",
                        issue_type="extreme_value",
                        description=f"감정가 대비 시세 비율이 극단적입니다 ({price_ratio:.2f})",
                        expected_value="0.7 ~ 1.3",
                        actual_value=price_ratio,
                        confidence=0.8,
                    )
                )

        return issues

    def _ratio_validation(self, outputs: dict) -> list[ValidationIssue]:
        """비율 검증"""

        issues = []

        bid_strategy = outputs.get("bid_strategist", {})
        valuator = outputs.get("valuator", {})

        optimal_bid = bid_strategy.get("optimal_bid", 0)
        appraisal = valuator.get("appraisal_value", 0)

        if optimal_bid > 0 and appraisal > 0:
            bid_rate = optimal_bid / appraisal

            # 낙찰율이 너무 낮거나 높은 경우
            if bid_rate < 0.4:
                issues.append(
                    ValidationIssue(
                        id="ratio_bid_too_low",
                        severity=ValidationSeverity.WARNING,
                        category="statistical_anomaly",
                        source_agent="bid_strategist",
                        field_path="bid_rate",
                        issue_type="ratio_check",
                        description=f"입찰율이 매우 낮습니다 ({bid_rate*100:.1f}%)",
                        expected_value=">= 50%",
                        actual_value=f"{bid_rate*100:.1f}%",
                        suggested_fix="인수금액이나 시세가 정확한지 재확인하세요.",
                        confidence=0.7,
                    )
                )

            if bid_rate > 1.0:
                issues.append(
                    ValidationIssue(
                        id="ratio_bid_too_high",
                        severity=ValidationSeverity.ERROR,
                        category="statistical_anomaly",
                        source_agent="bid_strategist",
                        field_path="bid_rate",
                        issue_type="ratio_check",
                        description=f"입찰율이 감정가를 초과합니다 ({bid_rate*100:.1f}%)",
                        expected_value="<= 100%",
                        actual_value=f"{bid_rate*100:.1f}%",
                        suggested_fix="시세 분석 또는 전략 설정을 재검토하세요.",
                        confidence=0.95,
                    )
                )

        return issues


class AdversarialValidator:
    """적대적 검증기 (Devil's Advocate)"""

    def __init__(self, llm_client: BaseChatModel):
        self.llm = llm_client

    async def validate(
        self, agent_outputs: dict[str, dict], case_info: dict
    ) -> list[ValidationIssue]:
        """적대적 관점에서 분석 결과 검증"""

        issues = []

        # 1. 권리분석 적대적 검증
        if "rights_analyzer" in agent_outputs:
            rights_issues = await self._challenge_rights_analysis(
                agent_outputs["rights_analyzer"], case_info
            )
            issues.extend(rights_issues)

        # 2. 가치평가 적대적 검증
        if "valuator" in agent_outputs:
            valuation_issues = await self._challenge_valuation(
                agent_outputs.get("valuator", {}),
                agent_outputs.get("location_analyzer", {}),
            )
            issues.extend(valuation_issues)

        # 3. 입찰전략 적대적 검증
        if "bid_strategist" in agent_outputs and "risk_assessor" in agent_outputs:
            strategy_issues = await self._challenge_bid_strategy(
                agent_outputs["bid_strategist"], agent_outputs["risk_assessor"]
            )
            issues.extend(strategy_issues)

        # 4. 숨겨진 위험 탐지
        hidden_risks = await self._find_hidden_risks(agent_outputs, case_info)
        issues.extend(hidden_risks)

        return issues

    async def _challenge_rights_analysis(
        self, rights: dict, case_info: dict
    ) -> list[ValidationIssue]:
        """권리분석 반박"""

        issues = []

        prompt = f"""당신은 부동산 경매 전문 변호사입니다. 아래 권리분석 결과에서
놓쳤을 수 있는 위험 요소나 잘못된 해석을 찾아주세요.

권리분석 결과:
- 말소기준권리: {rights.get('reference_right', {{}})}
- 인수 권리: {rights.get('assumed_rights', [])}
- 소멸 권리: {rights.get('extinguished_rights', [])}
- 총 인수금액: {rights.get('total_assumed_amount', 0):,}원
- 위험등급: {rights.get('risk_level', 'N/A')}

사건정보:
{json.dumps(case_info, ensure_ascii=False, indent=2)}

다음 관점에서 검토해주세요:
1. 말소기준권리 설정이 정확한가?
2. 인수/소멸 분류가 올바른가?
3. 놓친 권리관계가 있는가?
4. 특수한 법적 쟁점이 있는가?

JSON 형식으로 응답:
{{"issues": [{{"type": "...", "description": "...", "severity": "WARNING|ERROR"}}]}}
"""

        try:
            response = await self.llm.ainvoke(prompt)
            result = self._parse_llm_response(
                response.content if hasattr(response, "content") else str(response)
            )

            for item in result.get("issues", []):
                issues.append(
                    ValidationIssue(
                        id=f"adversarial_rights_{len(issues)}",
                        severity=ValidationSeverity[item.get("severity", "WARNING")],
                        category="adversarial",
                        source_agent="rights_analyzer",
                        field_path="overall",
                        issue_type=item.get("type", "potential_issue"),
                        description=item.get("description", ""),
                        confidence=0.7,
                    )
                )
        except Exception as e:
            logger.warning(f"적대적 검증 중 LLM 오류: {e}")

        return issues

    async def _challenge_valuation(
        self, valuation: dict, location: dict
    ) -> list[ValidationIssue]:
        """가치평가 반박"""

        issues = []

        prompt = f"""당신은 부동산 감정평가사입니다. 아래 가치평가 결과가 합리적인지 검토해주세요.

가치평가:
- 감정가: {valuation.get('appraisal_value', 0):,}원
- 추정 시세: {valuation.get('estimated_market_price', 0):,}원
- 평당가: {valuation.get('price_per_pyung', 0):,}원
- 비교 사례 수: {valuation.get('comparables_count', 0)}건
- 신뢰도: {valuation.get('confidence', 0):.1%}

입지분석:
- 총점: {location.get('total_score', 0)}점
- 교통: {location.get('transport_score', 0)}점
- 교육: {location.get('education_score', 0)}점

다음을 검토해주세요:
1. 평당가가 해당 지역 시세에 적합한가?
2. 감정가와 시세 간 괴리가 합리적인가?
3. 입지 점수 대비 가격이 적절한가?
4. 비교 사례가 충분한가?

JSON 형식으로 응답:
{{"issues": [{{"type": "...", "description": "...", "severity": "WARNING|ERROR"}}]}}
"""

        try:
            response = await self.llm.ainvoke(prompt)
            result = self._parse_llm_response(
                response.content if hasattr(response, "content") else str(response)
            )

            for item in result.get("issues", []):
                issues.append(
                    ValidationIssue(
                        id=f"adversarial_valuation_{len(issues)}",
                        severity=ValidationSeverity[item.get("severity", "WARNING")],
                        category="adversarial",
                        source_agent="valuator",
                        field_path="overall",
                        issue_type=item.get("type", "potential_issue"),
                        description=item.get("description", ""),
                        confidence=0.65,
                    )
                )
        except Exception as e:
            logger.warning(f"적대적 검증 중 LLM 오류: {e}")

        return issues

    async def _challenge_bid_strategy(
        self, strategy: dict, risk: dict
    ) -> list[ValidationIssue]:
        """입찰 전략 반박"""

        issues = []

        # 위험등급과 입찰전략 일관성 검증
        risk_grade = risk.get("grade", "B")
        strategy_type = strategy.get("strategy_type", "balanced")

        inconsistent_combos = [
            ("D", "aggressive", "고위험 물건에 공격적 전략은 위험합니다."),
            ("C", "aggressive", "위험등급 C에서 공격적 전략은 주의가 필요합니다."),
            ("A", "conservative", "안전 물건에 지나치게 보수적인 전략은 기회비용이 큽니다."),
        ]

        for grade, strat, message in inconsistent_combos:
            if risk_grade == grade and strategy_type == strat:
                issues.append(
                    ValidationIssue(
                        id=f"adversarial_strategy_{grade}_{strat}",
                        severity=ValidationSeverity.WARNING,
                        category="adversarial",
                        source_agent="bid_strategist",
                        field_path="strategy_type",
                        issue_type="inconsistent_strategy",
                        description=message,
                        confidence=0.8,
                    )
                )

        return issues

    async def _find_hidden_risks(
        self, outputs: dict, case_info: dict
    ) -> list[ValidationIssue]:
        """숨겨진 위험 탐지"""

        issues = []

        # 낙찰 후 숨겨진 비용 체크
        rights = outputs.get("rights_analyzer", {})
        strategy = outputs.get("bid_strategist", {})

        expected_profit = strategy.get("expected_profit", 0)

        # 명도비용 고려 여부
        if rights.get("has_occupants") and expected_profit > 0:
            eviction_cost_included = strategy.get("includes_eviction_cost", False)

            if not eviction_cost_included:
                issues.append(
                    ValidationIssue(
                        id="hidden_eviction_cost",
                        severity=ValidationSeverity.WARNING,
                        category="adversarial",
                        source_agent="bid_strategist",
                        field_path="expected_profit",
                        issue_type="hidden_cost",
                        description="점유자가 있으나 명도비용이 수익 계산에 미포함되었습니다.",
                        suggested_fix="명도비용 500~2000만원을 추가 고려하세요.",
                        confidence=0.85,
                    )
                )

        # 리모델링 비용 체크
        property_info = outputs.get("data_collector", {}).get("property_info", {})
        building_year = property_info.get("building_year", 2024)

        if building_year and (2024 - building_year) > 25:
            remodel_cost_included = strategy.get("includes_remodel_cost", False)

            if not remodel_cost_included:
                issues.append(
                    ValidationIssue(
                        id="hidden_remodel_cost",
                        severity=ValidationSeverity.INFO,
                        category="adversarial",
                        source_agent="bid_strategist",
                        field_path="expected_profit",
                        issue_type="hidden_cost",
                        description=f"건물이 {2024-building_year}년 경과하여 리모델링 비용 고려가 필요합니다.",
                        confidence=0.7,
                    )
                )

        return issues

    def _parse_llm_response(self, response: str) -> dict:
        """LLM 응답 파싱"""

        # JSON 블록 추출
        json_match = re.search(r"\{[\s\S]*\}", response)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        return {"issues": []}


class ReliabilityCalculator:
    """신뢰도 산출기"""

    # 에이전트별 기본 가중치
    AGENT_WEIGHTS = {
        "rights_analyzer": 0.30,
        "valuator": 0.25,
        "location_analyzer": 0.10,
        "risk_assessor": 0.15,
        "bid_strategist": 0.20,
    }

    # 이슈 유형별 감점
    SEVERITY_PENALTIES = {
        ValidationSeverity.INFO: 2,
        ValidationSeverity.WARNING: 10,
        ValidationSeverity.ERROR: 25,
        ValidationSeverity.CRITICAL: 50,
    }

    def calculate(
        self,
        agent_validations: dict[str, AgentValidation],
        cross_validations: list[CrossValidationResult],
        statistical_issues: list[ValidationIssue],
        adversarial_issues: list[ValidationIssue],
    ) -> tuple[float, ValidationStatus]:
        """종합 신뢰도 계산"""

        # 1. 에이전트별 신뢰도 계산
        agent_scores = {}
        for agent_name, validation in agent_validations.items():
            base_score = 100

            for issue in validation.issues:
                penalty = self.SEVERITY_PENALTIES.get(issue.severity, 5)
                penalty *= issue.confidence
                base_score -= penalty

            agent_scores[agent_name] = max(0, min(100, base_score))

        # 2. 가중 평균 계산
        weighted_sum = 0
        total_weight = 0

        for agent_name, score in agent_scores.items():
            weight = self.AGENT_WEIGHTS.get(agent_name, 0.1)
            weighted_sum += score * weight
            total_weight += weight

        base_reliability = weighted_sum / total_weight if total_weight > 0 else 0

        # 3. 교차 검증 불일치 감점
        cross_penalty = sum(10 for cv in cross_validations if not cv.is_consistent)

        # 4. 통계적 이상 감점
        stat_penalty = sum(
            self.SEVERITY_PENALTIES.get(issue.severity, 5)
            for issue in statistical_issues
        )

        # 5. 적대적 검증 감점 (가중치 낮음)
        adversarial_penalty = sum(
            self.SEVERITY_PENALTIES.get(issue.severity, 5) * 0.5
            for issue in adversarial_issues
        )

        # 6. 최종 신뢰도
        final_reliability = (
            base_reliability - cross_penalty - stat_penalty - adversarial_penalty
        )
        final_reliability = max(0, min(100, final_reliability))

        # 7. 상태 결정
        critical_count = sum(
            1
            for v in agent_validations.values()
            for i in v.issues
            if i.severity == ValidationSeverity.CRITICAL
        )

        error_count = sum(
            1
            for v in agent_validations.values()
            for i in v.issues
            if i.severity == ValidationSeverity.ERROR
        )

        if critical_count > 0:
            status = ValidationStatus.FAILED
        elif error_count > 2:
            status = ValidationStatus.NEEDS_REVIEW
        elif final_reliability >= 80:
            status = ValidationStatus.PASSED
        elif final_reliability >= 60:
            status = ValidationStatus.PASSED_WITH_WARNINGS
        else:
            status = ValidationStatus.NEEDS_REVIEW

        return final_reliability, status


class RedTeamAgent:
    """레드팀 에이전트 메인 클래스"""

    def __init__(self, llm_client: Optional[BaseChatModel] = None):
        self.llm = llm_client or get_high_reasoning_llm()

        # 검증 모듈 초기화
        self.integrity_validator = DataIntegrityValidator()
        self.cross_validator = CrossValidator()
        self.anomaly_detector = StatisticalAnomalyDetector()
        self.adversarial_validator = AdversarialValidator(self.llm)
        self.reliability_calculator = ReliabilityCalculator()

    async def validate(
        self,
        case_id: str,
        agent_outputs: dict[str, dict],
        case_info: Optional[dict] = None,
        historical_cases: Optional[list[dict]] = None,
    ) -> RedTeamReport:
        """종합 검증 수행"""

        case_info = case_info or {}
        historical_cases = historical_cases or []
        validation_time = datetime.now()

        logger.info(f"레드팀 검증 시작: {case_id}")

        # 1. 에이전트별 데이터 무결성 검증
        agent_validations = {}
        for agent_name, output in agent_outputs.items():
            issues = self.integrity_validator.validate(agent_name, output)

            status = self._determine_status(issues)
            reliability = 100 - sum(
                self.reliability_calculator.SEVERITY_PENALTIES.get(i.severity, 0)
                for i in issues
            )

            agent_validations[agent_name] = AgentValidation(
                agent_name=agent_name,
                validation_time=validation_time,
                issues=issues,
                status=status,
                reliability_score=max(0, reliability),
                summary=self._generate_agent_summary(issues),
            )

        # 2. 교차 검증
        cross_validations = self.cross_validator.validate(agent_outputs)

        # 3. 통계적 이상 탐지
        statistical_anomalies = self.anomaly_detector.detect(
            agent_outputs, historical_cases
        )

        # 4. 적대적 검증
        adversarial_findings = await self.adversarial_validator.validate(
            agent_outputs, case_info
        )

        # 5. 종합 신뢰도 계산
        overall_reliability, overall_status = self.reliability_calculator.calculate(
            agent_validations,
            cross_validations,
            statistical_anomalies,
            adversarial_findings,
        )

        # 6. 치명적 이슈 수집
        critical_issues = self._collect_critical_issues(
            agent_validations,
            cross_validations,
            statistical_anomalies,
            adversarial_findings,
        )

        # 7. 추천 사항 생성
        recommendations = self._generate_recommendations(
            overall_status, critical_issues, cross_validations
        )

        # 8. 승인 결정
        approved = overall_status in [
            ValidationStatus.PASSED,
            ValidationStatus.PASSED_WITH_WARNINGS,
        ]

        approval_conditions = []
        if overall_status == ValidationStatus.PASSED_WITH_WARNINGS:
            approval_conditions = [
                issue.description
                for issue in critical_issues
                if issue.severity == ValidationSeverity.WARNING
            ][:3]

        logger.info(
            f"레드팀 검증 완료: {case_id} - 상태: {overall_status.value}, 신뢰도: {overall_reliability:.1f}"
        )

        return RedTeamReport(
            case_id=case_id,
            validation_time=validation_time,
            agent_validations=agent_validations,
            cross_validations=cross_validations,
            statistical_anomalies=statistical_anomalies,
            adversarial_findings=adversarial_findings,
            overall_status=overall_status,
            overall_reliability=round(overall_reliability, 1),
            critical_issues=critical_issues,
            recommendations=recommendations,
            approved=approved,
            approval_conditions=approval_conditions,
        )

    def _determine_status(self, issues: list[ValidationIssue]) -> ValidationStatus:
        """이슈 목록에서 상태 결정"""

        severities = [i.severity for i in issues]

        if ValidationSeverity.CRITICAL in severities:
            return ValidationStatus.FAILED
        if ValidationSeverity.ERROR in severities:
            return ValidationStatus.NEEDS_REVIEW
        if ValidationSeverity.WARNING in severities:
            return ValidationStatus.PASSED_WITH_WARNINGS
        return ValidationStatus.PASSED

    def _generate_agent_summary(self, issues: list[ValidationIssue]) -> str:
        """에이전트 검증 요약 생성"""

        if not issues:
            return "모든 검증을 통과했습니다."

        error_count = sum(
            1
            for i in issues
            if i.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]
        )
        warning_count = sum(1 for i in issues if i.severity == ValidationSeverity.WARNING)

        parts = []
        if error_count > 0:
            parts.append(f"오류 {error_count}건")
        if warning_count > 0:
            parts.append(f"경고 {warning_count}건")

        return ", ".join(parts) + " 발견"

    def _collect_critical_issues(
        self,
        agent_validations: dict,
        cross_validations: list,
        statistical_issues: list,
        adversarial_issues: list,
    ) -> list[ValidationIssue]:
        """치명적 이슈 수집"""

        all_issues = []

        # 에이전트 검증 이슈
        for validation in agent_validations.values():
            all_issues.extend(validation.issues)

        # 통계적 이상
        all_issues.extend(statistical_issues)

        # 적대적 검증
        all_issues.extend(adversarial_issues)

        # 교차 검증 불일치를 이슈로 변환
        for cv in cross_validations:
            if not cv.is_consistent:
                all_issues.append(
                    ValidationIssue(
                        id=f"cross_{cv.field_compared}",
                        severity=ValidationSeverity.WARNING,
                        category="cross_validation",
                        source_agent=",".join(cv.agents_compared),
                        field_path=cv.field_compared,
                        issue_type="inconsistency",
                        description=f"에이전트 간 불일치: {cv.note}",
                        confidence=0.9,
                    )
                )

        # 심각도 순 정렬
        severity_order = {
            ValidationSeverity.CRITICAL: 0,
            ValidationSeverity.ERROR: 1,
            ValidationSeverity.WARNING: 2,
            ValidationSeverity.INFO: 3,
        }

        all_issues.sort(key=lambda x: severity_order.get(x.severity, 99))

        return all_issues[:10]  # 상위 10개

    def _generate_recommendations(
        self,
        status: ValidationStatus,
        critical_issues: list[ValidationIssue],
        cross_validations: list[CrossValidationResult],
    ) -> list[str]:
        """추천 사항 생성"""

        recommendations = []

        # 상태별 기본 추천
        if status == ValidationStatus.PASSED:
            recommendations.append("모든 검증을 통과했습니다. 리포트 생성을 진행해도 좋습니다.")

        elif status == ValidationStatus.PASSED_WITH_WARNINGS:
            recommendations.append("경고 사항이 있으나 진행 가능합니다. 아래 사항을 확인하세요.")

        elif status == ValidationStatus.NEEDS_REVIEW:
            recommendations.append("전문가 검토가 필요합니다. 자동 승인이 거부되었습니다.")

        else:  # FAILED
            recommendations.append("치명적 오류가 발견되었습니다. 해당 에이전트를 재실행하세요.")

        # 개별 이슈별 추천
        for issue in critical_issues[:5]:
            if issue.suggested_fix:
                recommendations.append(issue.suggested_fix)

        # 교차 검증 불일치 추천
        inconsistent_count = sum(1 for cv in cross_validations if not cv.is_consistent)
        if inconsistent_count > 0:
            recommendations.append(
                f"에이전트 간 {inconsistent_count}건의 데이터 불일치가 있습니다. 원본 데이터를 확인하세요."
            )

        return recommendations[:6]
