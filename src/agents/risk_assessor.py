"""위험평가 에이전트

경매 물건의 모든 위험 요소를 종합 평가하여 투자 위험도를 정량화하고 등급을 산출합니다.

가중치:
- 권리 리스크: 40%
- 시장 리스크: 20%
- 물건 리스크: 20%
- 명도 리스크: 20%
"""

from typing import Any, Optional

from ..models.risk import (
    CategoryRisk,
    RedFlag,
    RiskAssessmentResult,
    RiskGrade,
    RiskItem,
    RiskLevel,
)


class RiskScorer:
    """위험도 스코어링 엔진"""

    # 카테고리별 가중치
    CATEGORY_WEIGHTS = {
        "rights": 0.40,  # 권리 리스크 40%
        "market": 0.20,  # 시장 리스크 20%
        "property": 0.20,  # 물건 리스크 20%
        "eviction": 0.20,  # 명도 리스크 20%
    }

    # 등급 기준
    GRADE_THRESHOLDS = {
        "A": (0, 25),  # 안전
        "B": (25, 50),  # 보통
        "C": (50, 70),  # 위험
        "D": (70, 100),  # 고위험
    }

    def calculate_total_score(
        self,
        rights_score: float,
        market_score: float,
        property_score: float,
        eviction_score: float,
    ) -> tuple[float, RiskGrade, RiskLevel]:
        """종합 위험 점수 계산

        Args:
            rights_score: 권리 리스크 점수
            market_score: 시장 리스크 점수
            property_score: 물건 리스크 점수
            eviction_score: 명도 리스크 점수

        Returns:
            (총점, 등급, 위험수준) 튜플
        """
        total = (
            rights_score * self.CATEGORY_WEIGHTS["rights"]
            + market_score * self.CATEGORY_WEIGHTS["market"]
            + property_score * self.CATEGORY_WEIGHTS["property"]
            + eviction_score * self.CATEGORY_WEIGHTS["eviction"]
        )

        grade = self._determine_grade(total)
        level = self._determine_level(total)

        return total, grade, level

    def _determine_grade(self, score: float) -> RiskGrade:
        """점수에서 등급 결정"""
        for grade, (min_s, max_s) in self.GRADE_THRESHOLDS.items():
            if min_s <= score < max_s:
                return RiskGrade(grade)
        return RiskGrade.D

    def _determine_level(self, score: float) -> RiskLevel:
        """점수에서 위험 수준 결정"""
        if score < 25:
            return RiskLevel.LOW
        elif score < 50:
            return RiskLevel.MEDIUM
        elif score < 70:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL


class RightsRiskEvaluator:
    """권리 리스크 평가기 (가중치 40%)"""

    # 개별 항목 가중치
    ITEM_WEIGHTS = {
        "assumed_amount_ratio": 0.30,  # 인수금액 비율
        "senior_rights_count": 0.20,  # 선순위 권리 수
        "complexity": 0.15,  # 복잡도
        "statutory_superficies": 0.20,  # 법정지상권
        "lien": 0.15,  # 유치권
    }

    def evaluate(
        self, rights_analysis: dict[str, Any], appraisal_value: int
    ) -> CategoryRisk:
        """권리 리스크 평가

        Args:
            rights_analysis: 권리분석 결과
            appraisal_value: 감정가

        Returns:
            권리 카테고리 리스크
        """
        items = []

        # 1. 인수금액 비율
        assumed = rights_analysis.get("total_assumed_amount", 0)
        ratio = assumed / appraisal_value if appraisal_value > 0 else 0

        if ratio == 0:
            score = 0
        elif ratio < 0.1:
            score = 20
        elif ratio < 0.3:
            score = 50
        elif ratio < 0.5:
            score = 75
        else:
            score = 100

        items.append(
            RiskItem(
                name="인수금액 비율",
                category="rights",
                score=score,
                weight=self.ITEM_WEIGHTS["assumed_amount_ratio"],
                level=self._score_to_level(score),
                description=f"감정가 대비 {ratio*100:.1f}% 인수 필요",
                mitigation="인수금액을 입찰가에 반영하여 총 투자금 계산 필요" if score > 30 else None,
            )
        )

        # 2. 선순위 권리 수
        senior_count = len(rights_analysis.get("assumed_rights", []))

        if senior_count == 0:
            score = 0
        elif senior_count <= 2:
            score = 30
        elif senior_count <= 4:
            score = 60
        else:
            score = 90

        items.append(
            RiskItem(
                name="선순위 권리 수",
                category="rights",
                score=score,
                weight=self.ITEM_WEIGHTS["senior_rights_count"],
                level=self._score_to_level(score),
                description=f"{senior_count}개의 선순위 권리 존재",
                mitigation="각 권리의 인수 여부를 정확히 확인 필요" if senior_count > 2 else None,
            )
        )

        # 3. 권리관계 복잡도
        special_rights = rights_analysis.get("special_rights", [])
        complexity_score = min(100, len(special_rights) * 25)

        items.append(
            RiskItem(
                name="권리관계 복잡도",
                category="rights",
                score=complexity_score,
                weight=self.ITEM_WEIGHTS["complexity"],
                level=self._score_to_level(complexity_score),
                description=f"특수 권리 {len(special_rights)}건 검토 필요"
                if special_rights
                else "특수 권리 없음",
                mitigation="법무사 상담을 통한 정밀 분석 권장" if complexity_score > 50 else None,
            )
        )

        # 4. 법정지상권
        superficies = rights_analysis.get("statutory_superficies", {})
        superficies_risk = superficies.get("risk_level", "LOW")

        if superficies_risk == "HIGH":
            score = 90
        elif superficies_risk == "MEDIUM":
            score = 50
        else:
            score = 10

        items.append(
            RiskItem(
                name="법정지상권",
                category="rights",
                score=score,
                weight=self.ITEM_WEIGHTS["statutory_superficies"],
                level=self._score_to_level(score),
                description=superficies.get("note", "해당 없음"),
                mitigation="토지-건물 소유권 이력 확인 필요" if score > 50 else None,
            )
        )

        # 5. 유치권
        lien = rights_analysis.get("lien", {})
        if lien.get("has_claim"):
            score = 100
        elif lien.get("potential_risk"):
            score = 60
        else:
            score = 10

        items.append(
            RiskItem(
                name="유치권",
                category="rights",
                score=score,
                weight=self.ITEM_WEIGHTS["lien"],
                level=self._score_to_level(score),
                description="유치권 신고 있음" if lien.get("has_claim") else "유치권 없음",
                mitigation="유치권 주장 금액 및 정당성 검토 필요" if score > 50 else None,
            )
        )

        # 카테고리 점수 계산
        category_score = sum(item.score * item.weight for item in items)

        return CategoryRisk(
            name="권리 리스크",
            score=round(category_score, 1),
            level=self._score_to_level(category_score),
            weight=0.40,
            items=items,
            summary=self._generate_summary(items, category_score),
        )

    def _score_to_level(self, score: float) -> RiskLevel:
        """점수를 위험 수준으로 변환"""
        if score < 30:
            return RiskLevel.LOW
        elif score < 50:
            return RiskLevel.MEDIUM
        elif score < 75:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL

    def _generate_summary(self, items: list[RiskItem], score: float) -> str:
        """요약 생성"""
        high_risk_items = [
            i for i in items if i.level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        ]

        if not high_risk_items:
            return "권리관계가 비교적 깔끔합니다."
        elif len(high_risk_items) == 1:
            return f"{high_risk_items[0].name}에 주의가 필요합니다."
        else:
            names = ", ".join(i.name for i in high_risk_items[:2])
            if len(high_risk_items) > 2:
                names += f" 외 {len(high_risk_items) - 2}건"
            return f"여러 권리 리스크가 있습니다: {names}"


class MarketRiskEvaluator:
    """시장 리스크 평가기 (가중치 20%)"""

    ITEM_WEIGHTS = {
        "volatility": 0.30,  # 가격 변동성
        "liquidity": 0.25,  # 유동성
        "price_gap": 0.25,  # 시세 괴리
        "trend": 0.20,  # 추세
    }

    def evaluate(
        self, valuation: dict[str, Any], market_data: dict[str, Any]
    ) -> CategoryRisk:
        """시장 리스크 평가

        Args:
            valuation: 가치평가 결과
            market_data: 시장 데이터

        Returns:
            시장 카테고리 리스크
        """
        items = []

        # 1. 가격 변동성
        volatility = market_data.get("price_volatility", 0.05)

        if volatility < 0.03:
            score = 10
        elif volatility < 0.07:
            score = 30
        elif volatility < 0.12:
            score = 60
        else:
            score = 90

        items.append(
            RiskItem(
                name="가격 변동성",
                category="market",
                score=score,
                weight=self.ITEM_WEIGHTS["volatility"],
                level=self._score_to_level(score),
                description=f"최근 1년 변동성 {volatility*100:.1f}%",
                mitigation="변동성이 높으므로 보수적 가격 책정 권장" if score > 50 else None,
            )
        )

        # 2. 거래 유동성
        transaction_count = market_data.get("transaction_count_12m", 0)

        if transaction_count >= 15:
            score = 10
        elif transaction_count >= 10:
            score = 30
        elif transaction_count >= 5:
            score = 50
        else:
            score = 80

        items.append(
            RiskItem(
                name="거래 유동성",
                category="market",
                score=score,
                weight=self.ITEM_WEIGHTS["liquidity"],
                level=self._score_to_level(score),
                description=f"최근 12개월 거래 {transaction_count}건",
                mitigation="유동성이 낮아 매각 시 시간이 소요될 수 있음" if score > 50 else None,
            )
        )

        # 3. 시세 vs 감정가 괴리
        market_price = valuation.get("estimated_market_price", 0)
        appraisal = valuation.get("appraisal_value", 0)

        if appraisal > 0:
            gap = (appraisal - market_price) / appraisal
        else:
            gap = 0

        if gap < 0:  # 감정가 < 시세 (좋음)
            score = 10
        elif gap < 0.05:
            score = 20
        elif gap < 0.1:
            score = 40
        elif gap < 0.2:
            score = 60
        else:
            score = 85

        items.append(
            RiskItem(
                name="시세 괴리",
                category="market",
                score=score,
                weight=self.ITEM_WEIGHTS["price_gap"],
                level=self._score_to_level(score),
                description=f"감정가가 시세보다 {gap*100:.1f}% 높음" if gap > 0 else "감정가가 적정함",
                mitigation="감정가가 과대 평가되었을 수 있으니 시세 재확인 필요" if gap > 0.1 else None,
            )
        )

        # 4. 시장 추세
        trend = valuation.get("trend_direction", "STABLE")

        if trend == "UPWARD":
            score = 10
        elif trend == "STABLE":
            score = 30
        else:  # DOWNWARD
            score = 70

        items.append(
            RiskItem(
                name="시장 추세",
                category="market",
                score=score,
                weight=self.ITEM_WEIGHTS["trend"],
                level=self._score_to_level(score),
                description=f"가격 추세: {trend}",
                mitigation="하락 추세이므로 단기 매각 계획 재검토 필요" if trend == "DOWNWARD" else None,
            )
        )

        # 카테고리 점수
        category_score = sum(item.score * item.weight for item in items)

        return CategoryRisk(
            name="시장 리스크",
            score=round(category_score, 1),
            level=self._score_to_level(category_score),
            weight=0.20,
            items=items,
            summary=self._generate_summary(category_score, trend),
        )

    def _score_to_level(self, score: float) -> RiskLevel:
        """점수를 위험 수준으로 변환"""
        if score < 30:
            return RiskLevel.LOW
        elif score < 50:
            return RiskLevel.MEDIUM
        elif score < 75:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL

    def _generate_summary(self, score: float, trend: str) -> str:
        """요약 생성"""
        if score < 30:
            return "시장 상황이 양호합니다."
        elif score < 50:
            return "시장 상황이 보통입니다."
        elif trend == "DOWNWARD":
            return "시장이 하락 추세입니다. 신중한 접근이 필요합니다."
        else:
            return "시장 리스크가 다소 높습니다."


class PropertyRiskEvaluator:
    """물건 리스크 평가기 (가중치 20%)"""

    ITEM_WEIGHTS = {
        "building_age": 0.35,  # 건물 노후도
        "defects": 0.30,  # 하자 가능성
        "special_property": 0.20,  # 특수 물건
        "occupancy": 0.15,  # 점유 상태
    }

    def evaluate(
        self, property_info: dict[str, Any], status_report: dict[str, Any]
    ) -> CategoryRisk:
        """물건 리스크 평가

        Args:
            property_info: 물건 정보
            status_report: 현황 보고서

        Returns:
            물건 카테고리 리스크
        """
        items = []

        # 1. 건물 노후도
        building_year = property_info.get("building_year", 2000)
        current_year = 2024
        age = current_year - building_year

        if age <= 10:
            score = 10
        elif age <= 20:
            score = 25
        elif age <= 30:
            score = 50
        elif age <= 40:
            score = 75
        else:
            score = 95

        items.append(
            RiskItem(
                name="건물 노후도",
                category="property",
                score=score,
                weight=self.ITEM_WEIGHTS["building_age"],
                level=self._score_to_level(score),
                description=f"건축년도 {building_year}년 (경과 {age}년)",
                mitigation="노후 건물은 리모델링 비용 추가 고려" if score > 50 else None,
            )
        )

        # 2. 하자 가능성
        defects = status_report.get("defects", [])
        defect_score = min(100, len(defects) * 25)

        items.append(
            RiskItem(
                name="하자 가능성",
                category="property",
                score=defect_score,
                weight=self.ITEM_WEIGHTS["defects"],
                level=self._score_to_level(defect_score),
                description=f"발견된 하자 {len(defects)}건" if defects else "특이 하자 없음",
                mitigation="하자 수리 비용을 입찰가에 반영 필요" if defect_score > 50 else None,
            )
        )

        # 3. 특수 물건 여부
        is_special = property_info.get("is_special", False)
        special_score = 80 if is_special else 10

        items.append(
            RiskItem(
                name="특수 물건",
                category="property",
                score=special_score,
                weight=self.ITEM_WEIGHTS["special_property"],
                level=self._score_to_level(special_score),
                description="특수 물건 (지분/공유 등)" if is_special else "일반 물건",
                mitigation="지분 물건은 공유자와의 협의 필요" if is_special else None,
            )
        )

        # 4. 점유 상태
        occupancy = status_report.get("occupancy_status", "vacant")

        if occupancy == "vacant":
            score = 10
        elif occupancy == "owner":
            score = 30
        elif occupancy == "tenant":
            score = 50
        else:  # unknown or disputed
            score = 80

        items.append(
            RiskItem(
                name="점유 상태",
                category="property",
                score=score,
                weight=self.ITEM_WEIGHTS["occupancy"],
                level=self._score_to_level(score),
                description=f"점유 상태: {occupancy}",
                mitigation="점유 상태 불명확 시 현장 확인 필수" if score > 50 else None,
            )
        )

        category_score = sum(item.score * item.weight for item in items)

        return CategoryRisk(
            name="물건 리스크",
            score=round(category_score, 1),
            level=self._score_to_level(category_score),
            weight=0.20,
            items=items,
            summary=self._generate_summary(items, category_score),
        )

    def _score_to_level(self, score: float) -> RiskLevel:
        """점수를 위험 수준으로 변환"""
        if score < 30:
            return RiskLevel.LOW
        elif score < 50:
            return RiskLevel.MEDIUM
        elif score < 75:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL

    def _generate_summary(self, items: list[RiskItem], score: float) -> str:
        """요약 생성"""
        high_risk_items = [
            i for i in items if i.level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        ]

        if not high_risk_items:
            return "물건 상태가 양호합니다."
        elif len(high_risk_items) == 1:
            return f"{high_risk_items[0].name}에 유의하세요."
        else:
            return f"{len(high_risk_items)}가지 물건 리스크가 있습니다."


class EvictionRiskEvaluator:
    """명도 리스크 평가기 (가중치 20%)"""

    ITEM_WEIGHTS = {
        "tenant_priority": 0.35,  # 임차인 대항력
        "occupant_count": 0.25,  # 점유자 수
        "difficulty": 0.25,  # 명도 난이도
        "dispute": 0.15,  # 분쟁 가능성
    }

    def evaluate(
        self, rights_analysis: dict[str, Any], status_report: dict[str, Any]
    ) -> CategoryRisk:
        """명도 리스크 평가

        Args:
            rights_analysis: 권리분석 결과
            status_report: 현황 보고서

        Returns:
            명도 카테고리 리스크
        """
        items = []

        # 1. 임차인 대항력
        tenants = rights_analysis.get("tenant_analysis", [])
        priority_tenants = [t for t in tenants if t.get("has_priority")]

        if not priority_tenants:
            score = 10
        elif len(priority_tenants) == 1:
            score = 40
        elif len(priority_tenants) <= 3:
            score = 65
        else:
            score = 90

        items.append(
            RiskItem(
                name="임차인 대항력",
                category="eviction",
                score=score,
                weight=self.ITEM_WEIGHTS["tenant_priority"],
                level=self._score_to_level(score),
                description=f"대항력 있는 임차인 {len(priority_tenants)}명",
                mitigation="대항력 임차인의 보증금 및 인수 조건 확인 필요" if score > 40 else None,
            )
        )

        # 2. 점유자 수
        occupant_count = status_report.get("occupant_count", 0)

        if occupant_count == 0:
            score = 0
        elif occupant_count == 1:
            score = 30
        elif occupant_count <= 3:
            score = 55
        else:
            score = 85

        items.append(
            RiskItem(
                name="점유자 수",
                category="eviction",
                score=score,
                weight=self.ITEM_WEIGHTS["occupant_count"],
                level=self._score_to_level(score),
                description=f"현재 점유자 {occupant_count}명",
                mitigation="복수 점유자로 명도 협상이 복잡할 수 있음" if occupant_count > 1 else None,
            )
        )

        # 3. 명도 난이도
        difficulty = status_report.get("eviction_difficulty", "LOW")

        difficulty_scores = {"LOW": 15, "MEDIUM": 45, "HIGH": 75, "CRITICAL": 95}
        score = difficulty_scores.get(difficulty, 50)

        items.append(
            RiskItem(
                name="명도 난이도",
                category="eviction",
                score=score,
                weight=self.ITEM_WEIGHTS["difficulty"],
                level=self._score_to_level(score),
                description=f"명도 난이도: {difficulty}",
                mitigation="명도 전문 법무사 상담 권장" if score > 50 else None,
            )
        )

        # 4. 분쟁 가능성
        has_dispute = status_report.get("has_dispute", False)
        dispute_score = 85 if has_dispute else 15

        items.append(
            RiskItem(
                name="분쟁 가능성",
                category="eviction",
                score=dispute_score,
                weight=self.ITEM_WEIGHTS["dispute"],
                level=self._score_to_level(dispute_score),
                description="분쟁 진행 중" if has_dispute else "분쟁 없음",
                mitigation="진행 중인 소송 내용 및 영향 검토 필요" if has_dispute else None,
            )
        )

        category_score = sum(item.score * item.weight for item in items)

        return CategoryRisk(
            name="명도 리스크",
            score=round(category_score, 1),
            level=self._score_to_level(category_score),
            weight=0.20,
            items=items,
            summary=self._generate_summary(items, category_score),
        )

    def _score_to_level(self, score: float) -> RiskLevel:
        """점수를 위험 수준으로 변환"""
        if score < 30:
            return RiskLevel.LOW
        elif score < 50:
            return RiskLevel.MEDIUM
        elif score < 75:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL

    def _generate_summary(self, items: list[RiskItem], score: float) -> str:
        """요약 생성"""
        high_risk_items = [
            i for i in items if i.level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        ]

        if not high_risk_items:
            return "명도 리스크가 낮습니다."
        elif len(high_risk_items) == 1:
            return f"{high_risk_items[0].name}로 인한 명도 리스크가 있습니다."
        else:
            return "명도가 복잡할 수 있으니 전문가 상담이 필요합니다."


class RedFlagDetector:
    """위험 신호 탐지기"""

    RED_FLAG_RULES = [
        {
            "name": "과도한 인수금액",
            "severity": RiskLevel.HIGH,
            "condition": lambda r: r.get("assumed_amount_ratio", 0) > 0.3,
            "description": "인수금액이 감정가의 30%를 초과합니다.",
            "recommendation": "인수금액을 포함한 총 투자금액을 신중히 검토하세요.",
        },
        {
            "name": "유치권 신고",
            "severity": RiskLevel.CRITICAL,
            "condition": lambda r: r.get("lien", {}).get("has_claim"),
            "description": "유치권 신고가 있습니다.",
            "recommendation": "유치권의 정당성 및 금액을 법무사와 검토하세요.",
        },
        {
            "name": "법정지상권 위험",
            "severity": RiskLevel.HIGH,
            "condition": lambda r: r.get("statutory_superficies", {}).get("risk_level") == "HIGH",
            "description": "법정지상권 성립 가능성이 높습니다.",
            "recommendation": "토지-건물 소유권 변동 이력을 정밀 분석하세요.",
        },
        {
            "name": "가처분 등기",
            "severity": RiskLevel.HIGH,
            "condition": lambda r: any(
                right.get("type") == "가처분" for right in r.get("assumed_rights", [])
            ),
            "description": "가처분 등기가 있어 소유권 분쟁 가능성이 있습니다.",
            "recommendation": "가처분 사유 및 소송 진행 상황을 확인하세요.",
        },
        {
            "name": "다수 점유자",
            "severity": RiskLevel.MEDIUM,
            "condition": lambda r: r.get("occupant_count", 0) > 3,
            "description": "점유자가 4명 이상으로 명도가 복잡할 수 있습니다.",
            "recommendation": "각 점유자의 법적 지위와 명도 비용을 산정하세요.",
        },
        {
            "name": "노후 건물",
            "severity": RiskLevel.MEDIUM,
            "condition": lambda r: (2024 - r.get("building_year", 2024)) > 35,
            "description": "건물이 35년 이상 노후되어 있습니다.",
            "recommendation": "재건축/리모델링 비용을 투자 계획에 포함하세요.",
        },
        {
            "name": "시세 괴리",
            "severity": RiskLevel.MEDIUM,
            "condition": lambda r: r.get("price_gap", 0) > 0.15,
            "description": "감정가가 시세보다 15% 이상 높게 책정되어 있습니다.",
            "recommendation": "최근 유사 거래 사례를 통해 실제 시세를 재확인하세요.",
        },
        {
            "name": "복수 선순위 권리",
            "severity": RiskLevel.MEDIUM,
            "condition": lambda r: len(r.get("assumed_rights", [])) > 4,
            "description": "선순위 권리가 5개 이상으로 권리관계가 복잡합니다.",
            "recommendation": "모든 권리의 인수 여부를 명확히 파악하세요.",
        },
        {
            "name": "거래 유동성 부족",
            "severity": RiskLevel.MEDIUM,
            "condition": lambda r: r.get("transaction_count_12m", 0) < 5,
            "description": "최근 12개월 거래가 5건 미만으로 유동성이 낮습니다.",
            "recommendation": "장기 보유 계획을 수립하거나 매각 전략을 신중히 검토하세요.",
        },
    ]

    def detect(self, analysis_data: dict[str, Any]) -> list[RedFlag]:
        """Red Flag 탐지

        Args:
            analysis_data: 분석 데이터 (모든 카테고리 통합)

        Returns:
            탐지된 Red Flag 목록
        """
        red_flags = []

        for rule in self.RED_FLAG_RULES:
            try:
                if rule["condition"](analysis_data):
                    red_flags.append(
                        RedFlag(
                            name=rule["name"],
                            severity=rule["severity"],
                            description=rule["description"],
                            recommendation=rule["recommendation"],
                        )
                    )
            except (KeyError, TypeError, AttributeError):
                # 데이터가 없거나 형식이 맞지 않으면 건너뛰기
                continue

        return red_flags


class RiskAssessorAgent:
    """위험평가 에이전트 메인 클래스

    경매 물건의 모든 위험 요소를 종합 평가하여 투자 위험도를 정량화합니다.
    """

    def __init__(self):
        """에이전트 초기화"""
        self.rights_evaluator = RightsRiskEvaluator()
        self.market_evaluator = MarketRiskEvaluator()
        self.property_evaluator = PropertyRiskEvaluator()
        self.eviction_evaluator = EvictionRiskEvaluator()
        self.scorer = RiskScorer()
        self.red_flag_detector = RedFlagDetector()

    def assess(
        self,
        case_number: str,
        rights_analysis: dict[str, Any],
        valuation: dict[str, Any],
        property_info: Optional[dict[str, Any]] = None,
        status_report: Optional[dict[str, Any]] = None,
        market_data: Optional[dict[str, Any]] = None,
    ) -> RiskAssessmentResult:
        """종합 위험 평가

        Args:
            case_number: 사건번호
            rights_analysis: 권리분석 결과
            valuation: 가치평가 결과
            property_info: 물건 정보 (선택)
            status_report: 현황 보고서 (선택)
            market_data: 시장 데이터 (선택)

        Returns:
            위험평가 결과
        """
        # 기본값 설정
        property_info = property_info or {}
        status_report = status_report or {}
        market_data = market_data or {}

        # 1. 카테고리별 평가
        rights_risk = self.rights_evaluator.evaluate(
            rights_analysis, valuation.get("appraisal_value", 0)
        )

        market_risk = self.market_evaluator.evaluate(valuation, market_data)

        property_risk = self.property_evaluator.evaluate(property_info, status_report)

        eviction_risk = self.eviction_evaluator.evaluate(rights_analysis, status_report)

        # 2. 종합 점수 계산
        total_score, grade, level = self.scorer.calculate_total_score(
            rights_risk.score,
            market_risk.score,
            property_risk.score,
            eviction_risk.score,
        )

        # 3. Red Flag 탐지
        analysis_data = {
            **rights_analysis,
            **valuation,
            **property_info,
            **status_report,
            **market_data,
        }

        # 분석 데이터에 추가 계산 값 추가
        appraisal = valuation.get("appraisal_value", 0)
        market_price = valuation.get("estimated_market_price", 0)
        if appraisal > 0:
            analysis_data["price_gap"] = (appraisal - market_price) / appraisal
            analysis_data["assumed_amount_ratio"] = (
                rights_analysis.get("total_assumed_amount", 0) / appraisal
            )

        red_flags = self.red_flag_detector.detect(analysis_data)

        # 4. 추천 사항 생성
        recommendations = self._generate_recommendations(
            grade, rights_risk, market_risk, property_risk, eviction_risk, red_flags
        )

        # 5. 입문자 친화성 판단
        beginner_friendly = grade in [RiskGrade.A, RiskGrade.B] and len(red_flags) == 0
        beginner_note = self._generate_beginner_note(beginner_friendly, grade, red_flags)

        # 6. 상세 리포트 생성
        detailed_report = self._generate_detailed_report(
            grade,
            total_score,
            rights_risk,
            market_risk,
            property_risk,
            eviction_risk,
            red_flags,
            recommendations,
        )

        return RiskAssessmentResult(
            case_number=case_number,
            total_score=round(total_score, 1),
            grade=grade,
            level=level,
            rights_risk=rights_risk,
            market_risk=market_risk,
            property_risk=property_risk,
            eviction_risk=eviction_risk,
            red_flags=red_flags,
            recommendations=recommendations,
            beginner_friendly=beginner_friendly,
            beginner_note=beginner_note,
            detailed_report=detailed_report,
        )

    def _generate_recommendations(
        self,
        grade: RiskGrade,
        rights_risk: CategoryRisk,
        market_risk: CategoryRisk,
        property_risk: CategoryRisk,
        eviction_risk: CategoryRisk,
        red_flags: list[RedFlag],
    ) -> list[str]:
        """추천 사항 생성"""
        recommendations = []

        # 등급별 기본 추천
        if grade == RiskGrade.A:
            recommendations.append("권리관계가 깔끔하여 입문자도 검토 가능합니다.")
        elif grade == RiskGrade.B:
            recommendations.append("일부 주의사항이 있으나 적정 수준입니다.")
        elif grade == RiskGrade.C:
            recommendations.append("복잡한 권리관계로 전문가 상담을 권장합니다.")
        else:
            recommendations.append("고위험 물건입니다. 전문가 없이 입찰을 권장하지 않습니다.")

        # 카테고리별 추천
        if rights_risk.score >= 50:
            recommendations.append("권리분석 결과를 법무사와 재검토하세요.")

        if market_risk.score >= 50:
            recommendations.append("시장 상황이 불안정합니다. 보수적 입찰을 권장합니다.")

        if property_risk.score >= 50:
            recommendations.append("현장 방문하여 물건 상태를 직접 확인하세요.")

        if eviction_risk.score >= 50:
            recommendations.append("명도 비용을 충분히 고려하여 입찰가를 산정하세요.")

        # Red Flag 대응
        if red_flags:
            critical_flags = [f for f in red_flags if f.severity == RiskLevel.CRITICAL]
            if critical_flags:
                recommendations.append(
                    f"치명적 경고 {len(critical_flags)}건에 대한 즉시 검토가 필요합니다."
                )
            else:
                recommendations.append(f"주요 경고 {len(red_flags)}건에 대한 검토가 필요합니다.")

        return recommendations[:5]  # 최대 5개

    def _generate_beginner_note(
        self, beginner_friendly: bool, grade: RiskGrade, red_flags: list[RedFlag]
    ) -> str:
        """입문자 안내 메시지 생성"""
        if beginner_friendly:
            return "이 물건은 입문자가 검토하기에 적합합니다. 권리관계가 단순하고 특별한 위험 요소가 없습니다."
        elif grade in [RiskGrade.A, RiskGrade.B]:
            return f"일부 주의사항({len(red_flags)}건)이 있으니 전문가 조언을 받으시는 것을 권장합니다."
        elif grade == RiskGrade.C:
            return "중위험 물건입니다. 입문자는 전문가와 함께 검토하시기 바랍니다."
        else:
            return "고위험 물건입니다. 입문자에게는 권장하지 않으며, 반드시 전문가 상담이 필요합니다."

    def _generate_detailed_report(
        self,
        grade: RiskGrade,
        total_score: float,
        rights_risk: CategoryRisk,
        market_risk: CategoryRisk,
        property_risk: CategoryRisk,
        eviction_risk: CategoryRisk,
        red_flags: list[RedFlag],
        recommendations: list[str],
    ) -> str:
        """상세 리포트 생성"""
        report_lines = []

        # 헤더
        report_lines.append("=" * 60)
        report_lines.append("위험 평가 상세 리포트")
        report_lines.append("=" * 60)
        report_lines.append(f"\n종합 등급: {grade.value} (위험도: {total_score:.1f}점)")
        report_lines.append("")

        # 카테고리별 상세
        for category in [rights_risk, market_risk, property_risk, eviction_risk]:
            report_lines.append(f"\n[{category.name}] - {category.score:.1f}점 ({category.level.value})")
            report_lines.append(f"  {category.summary}")

            for item in category.items:
                if item.level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                    report_lines.append(f"  - {item.name}: {item.description}")
                    if item.mitigation:
                        report_lines.append(f"    대응: {item.mitigation}")

        # Red Flags
        if red_flags:
            report_lines.append("\n" + "=" * 60)
            report_lines.append(f"주요 경고 사항 ({len(red_flags)}건)")
            report_lines.append("=" * 60)

            for flag in red_flags:
                report_lines.append(f"\n[{flag.severity.value}] {flag.name}")
                report_lines.append(f"  {flag.description}")
                report_lines.append(f"  권장사항: {flag.recommendation}")

        # 추천 사항
        report_lines.append("\n" + "=" * 60)
        report_lines.append("종합 권장사항")
        report_lines.append("=" * 60)

        for i, rec in enumerate(recommendations, 1):
            report_lines.append(f"{i}. {rec}")

        report_lines.append("\n" + "=" * 60)

        return "\n".join(report_lines)
