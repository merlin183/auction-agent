"""입지분석 에이전트

경매 물건의 지리적 위치를 분석하여 교통, 교육, 편의시설, 개발호재 등을 종합 평가합니다.
"""

import asyncio
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

from ..models.location import (
    LocationAnalysisResult,
    TransportScore,
    EducationScore,
    AmenityScore,
    DevelopmentInfo,
    DemographicInfo,
    POI,
    POICategory,
)


logger = logging.getLogger(__name__)


@dataclass
class TransportFacility:
    """교통 시설"""
    name: str
    type: str  # subway, bus, highway
    line: Optional[str] = None
    distance: float = 0.0
    walk_time: float = 0.0


class TransportAnalyzer:
    """교통 분석기"""

    # 점수 기준
    SUBWAY_SCORE_CRITERIA = {
        (0, 300): 100,  # 역세권 (300m 이내)
        (300, 500): 90,  # 도보 5분
        (500, 1000): 70,  # 도보 10분
        (1000, 1500): 50,  # 도보 15분
        (1500, float("inf")): 30,  # 그 이상
    }

    def __init__(self, map_api):
        self.map_api = map_api

    async def analyze(self, lat: float, lng: float) -> TransportScore:
        """교통 분석 수행"""
        try:
            # 병렬로 시설 검색
            subway_task = self._search_subway(lat, lng)
            bus_task = self._search_bus(lat, lng)
            highway_task = self._search_highway(lat, lng)

            subway, bus, highway = await asyncio.gather(
                subway_task, bus_task, highway_task
            )

            # 점수 계산
            transport_score = self._calculate_score(subway, bus, highway)

            # TransportScore 모델 생성
            result = TransportScore(total_score=transport_score)

            if subway:
                nearest = subway[0]
                result.nearest_subway = nearest.name
                result.subway_distance_meters = int(nearest.distance)
                result.subway_walk_minutes = int(nearest.walk_time)
                result.subway_lines = [s.line for s in subway if s.line]

            if bus:
                result.bus_stops_within_300m = len([b for b in bus if b.distance <= 300])
                # 버스 노선 수는 API에서 받아올 수 있으면 설정
                result.bus_routes_count = len(bus)

            if highway:
                result.main_road_access = highway.distance <= 1000
                result.highway_distance_km = round(highway.distance / 1000, 1)

            # 점수에 따른 평가 메시지
            result.note = self._generate_note(result)

            return result

        except Exception as e:
            logger.error(f"교통 분석 실패: {e}")
            # 기본값 반환
            return TransportScore(
                total_score=0,
                note=f"교통 분석 실패: {str(e)}"
            )

    async def _search_subway(self, lat: float, lng: float) -> List[TransportFacility]:
        """지하철역 검색"""
        try:
            # API 인터페이스 - 실제 구현 시 map_api 사용
            # results = await self.map_api.search_nearby(lat, lng, "SW8", radius=2000)

            # 목업 데이터 (실제 API 연동 전까지)
            results = []

            stations = []
            for r in results[:5]:  # 상위 5개
                stations.append(
                    TransportFacility(
                        name=r.get("place_name"),
                        type="subway",
                        line=self._extract_line(r.get("place_name")),
                        distance=float(r.get("distance", 0)),
                        walk_time=float(r.get("distance", 0)) / 80,  # 분당 80m
                    )
                )

            return sorted(stations, key=lambda x: x.distance)
        except Exception as e:
            logger.warning(f"지하철역 검색 실패: {e}")
            return []

    async def _search_bus(self, lat: float, lng: float) -> List[TransportFacility]:
        """버스 정류장 검색"""
        try:
            # API 인터페이스
            # results = await self.map_api.search_nearby(lat, lng, "BK9", radius=500)

            results = []

            stops = []
            for r in results[:10]:
                stops.append(
                    TransportFacility(
                        name=r.get("place_name"),
                        type="bus",
                        line=None,
                        distance=float(r.get("distance", 0)),
                        walk_time=float(r.get("distance", 0)) / 80,
                    )
                )

            return sorted(stops, key=lambda x: x.distance)
        except Exception as e:
            logger.warning(f"버스정류장 검색 실패: {e}")
            return []

    async def _search_highway(self, lat: float, lng: float) -> Optional[TransportFacility]:
        """고속도로 접근성 검색"""
        try:
            # API 인터페이스
            # results = await self.map_api.search_nearby(lat, lng, "highway", radius=5000)

            results = []

            if results:
                r = results[0]
                return TransportFacility(
                    name=r.get("place_name"),
                    type="highway",
                    distance=float(r.get("distance", 0)),
                )
            return None
        except Exception as e:
            logger.warning(f"고속도로 검색 실패: {e}")
            return None

    def _extract_line(self, name: str) -> Optional[str]:
        """역명에서 노선 추출"""
        if not name:
            return None

        # 간단한 노선 추출 로직
        for i in range(1, 10):
            if f"{i}호선" in name:
                return f"{i}호선"

        # 특수 노선
        special_lines = ["신분당선", "경의중앙선", "수인분당선", "공항철도"]
        for line in special_lines:
            if line in name:
                return line

        return None

    def _calculate_score(
        self,
        subway: List[TransportFacility],
        bus: List[TransportFacility],
        highway: Optional[TransportFacility],
    ) -> float:
        """교통 점수 계산"""
        score = 0

        # 지하철 점수 (50%)
        if subway:
            dist = subway[0].distance
            for (min_d, max_d), points in self.SUBWAY_SCORE_CRITERIA.items():
                if min_d <= dist < max_d:
                    score += points * 0.5
                    break

        # 버스 점수 (30%)
        if bus:
            dist = bus[0].distance
            if dist <= 200:
                score += 30
            elif dist <= 400:
                score += 20
            else:
                score += 10

        # 차량 접근성 점수 (20%)
        if highway and highway.distance <= 3000:
            score += 20
        elif highway:
            score += 10

        return min(100, score)

    def _generate_note(self, score: TransportScore) -> str:
        """점수에 따른 평가 메시지 생성"""
        parts = []

        if score.subway_distance_meters:
            if score.subway_distance_meters <= 300:
                parts.append("역세권 입지")
            elif score.subway_distance_meters <= 500:
                parts.append("지하철 도보 5분 이내")
            elif score.subway_distance_meters <= 1000:
                parts.append("지하철 도보 10분 이내")
        else:
            parts.append("지하철역 거리 다소 멀음")

        if score.bus_stops_within_300m >= 3:
            parts.append("버스 접근성 양호")

        return ", ".join(parts) if parts else "교통 접근성 분석 완료"


class EducationAnalyzer:
    """교육환경 분석기"""

    def __init__(self, map_api, school_data_api):
        self.map_api = map_api
        self.school_api = school_data_api

    async def analyze(self, lat: float, lng: float) -> EducationScore:
        """교육환경 분석"""
        try:
            # 학교 검색
            # schools_raw = await self.map_api.search_nearby(lat, lng, "SC4", radius=1500)
            schools_raw = []

            elementary = []
            middle = []
            high = []

            elem_distances = []
            middle_distances = []
            high_distances = []

            for s in schools_raw:
                name = s.get("place_name", "")
                distance = float(s.get("distance", 0))

                if "초등" in name or "초교" in name:
                    elementary.append(name)
                    elem_distances.append(distance)
                elif "중학" in name or "중교" in name:
                    middle.append(name)
                    middle_distances.append(distance)
                elif "고등" in name or "고교" in name:
                    high.append(name)
                    high_distances.append(distance)

            # 학원 수 조회
            # academies = await self.map_api.search_nearby(lat, lng, "AC5", radius=1000)
            academies = []
            academy_count = len(academies)

            # 학원 밀집도 평가
            if academy_count >= 20:
                academy_density = "높음"
            elif academy_count >= 10:
                academy_density = "보통"
            else:
                academy_density = "낮음"

            # 점수 계산
            score = self._calculate_score(
                len(elementary),
                len(middle),
                len(high),
                academy_count,
                min(elem_distances) if elem_distances else None
            )

            result = EducationScore(
                total_score=score,
                elementary_schools=sorted(elementary)[:3],
                middle_schools=sorted(middle)[:3],
                high_schools=sorted(high)[:3],
                nearest_elementary_meters=int(min(elem_distances)) if elem_distances else None,
                nearest_middle_meters=int(min(middle_distances)) if middle_distances else None,
                nearest_high_meters=int(min(high_distances)) if high_distances else None,
                academy_density=academy_density,
                note=self._generate_note(score, academy_density)
            )

            return result

        except Exception as e:
            logger.error(f"교육환경 분석 실패: {e}")
            return EducationScore(
                total_score=0,
                note=f"교육환경 분석 실패: {str(e)}"
            )

    def _calculate_score(
        self,
        elementary_count: int,
        middle_count: int,
        high_count: int,
        academy_count: int,
        nearest_elementary_dist: Optional[float]
    ) -> float:
        """교육 점수 계산"""
        score = 0

        # 초등학교 거리 (30%)
        if nearest_elementary_dist is not None:
            if nearest_elementary_dist <= 500:
                score += 30
            elif nearest_elementary_dist <= 1000:
                score += 20
            else:
                score += 10

        # 중/고등학교 존재 (30%)
        if middle_count > 0:
            score += 15
        if high_count > 0:
            score += 15

        # 학원가 (20%)
        if academy_count >= 20:
            score += 20
        elif academy_count >= 10:
            score += 15
        elif academy_count >= 5:
            score += 10

        # 교육기관 다양성 (20%)
        total_schools = elementary_count + middle_count + high_count
        if total_schools >= 5:
            score += 20
        elif total_schools >= 3:
            score += 15
        elif total_schools >= 1:
            score += 10

        return min(100, score)

    def _generate_note(self, score: float, academy_density: str) -> str:
        """평가 메시지 생성"""
        parts = []

        if score >= 80:
            parts.append("우수한 교육환경")
        elif score >= 60:
            parts.append("양호한 교육환경")
        else:
            parts.append("교육환경 개선 필요")

        parts.append(f"학원가 밀집도 {academy_density}")

        return ", ".join(parts)


class AmenityAnalyzer:
    """편의시설 분석기"""

    CATEGORY_CODES = {
        "mart": "MT1",
        "hospital": "HP8",
        "park": "AT4",
        "bank": "BK9",
        "restaurant": "FD6",
        "cafe": "CE7",
        "convenience": "CS2",
    }

    def __init__(self, map_api):
        self.map_api = map_api

    async def analyze(self, lat: float, lng: float) -> AmenityScore:
        """편의시설 분석"""
        try:
            # 병렬 검색
            tasks = {}
            for name, code in self.CATEGORY_CODES.items():
                # tasks[name] = self.map_api.search_nearby(lat, lng, code, radius=1000)
                tasks[name] = asyncio.sleep(0)  # 목업

            results = {}
            for name in tasks.keys():
                # results[name] = await tasks[name]
                results[name] = []  # 목업

            # 점수 계산
            marts = results.get("mart", [])
            hospitals = results.get("hospital", [])
            parks = results.get("park", [])
            convenience = results.get("convenience", [])

            score = self._calculate_score(
                len(marts),
                len(hospitals),
                len(parks),
                len(convenience)
            )

            result = AmenityScore(
                total_score=score,
                hospitals_within_1km=len(hospitals),
                marts_within_1km=[m.get("place_name", "") for m in marts[:5]],
                parks_within_500m=[p.get("place_name", "") for p in parks[:3]],
                convenience_stores_within_300m=len(
                    [c for c in convenience if float(c.get("distance", 9999)) <= 300]
                ),
                note=self._generate_note(score)
            )

            return result

        except Exception as e:
            logger.error(f"편의시설 분석 실패: {e}")
            return AmenityScore(
                total_score=0,
                note=f"편의시설 분석 실패: {str(e)}"
            )

    def _calculate_score(
        self,
        mart_count: int,
        hospital_count: int,
        park_count: int,
        convenience_count: int
    ) -> float:
        """편의시설 점수 계산"""
        score = 0

        # 대형마트 (25%)
        if mart_count >= 2:
            score += 25
        elif mart_count >= 1:
            score += 20

        # 병원 (25%)
        if hospital_count >= 3:
            score += 25
        elif hospital_count >= 1:
            score += 15

        # 공원 (25%)
        if park_count >= 2:
            score += 25
        elif park_count >= 1:
            score += 15

        # 편의점 (25%)
        if convenience_count >= 5:
            score += 25
        elif convenience_count >= 3:
            score += 20
        elif convenience_count >= 1:
            score += 15

        return min(100, score)

    def _generate_note(self, score: float) -> str:
        """평가 메시지 생성"""
        if score >= 80:
            return "편의시설 매우 우수"
        elif score >= 60:
            return "편의시설 양호"
        elif score >= 40:
            return "편의시설 보통"
        else:
            return "편의시설 부족"


class DevelopmentAnalyzer:
    """개발호재 분석기"""

    def __init__(self, urban_plan_api, news_api):
        self.urban_api = urban_plan_api
        self.news_api = news_api

    async def analyze(
        self, lat: float, lng: float, address: str
    ) -> Tuple[List[DevelopmentInfo], float]:
        """개발호재 분석"""
        try:
            projects = []

            # 1. 도시계획 정보 조회
            # urban_plans = await self._get_urban_plans(lat, lng)
            urban_plans = []

            for plan in urban_plans:
                if plan.get("type") in ["정비구역", "재개발", "재건축"]:
                    project = DevelopmentInfo(
                        name=plan.get("name", ""),
                        development_type="재개발",
                        status=plan.get("status", "예정"),
                        expected_completion=plan.get("completion_year"),
                        distance_km=plan.get("distance_km", 0),
                        impact_level=self._assess_impact_level(plan),
                        description=plan.get("description", "")
                    )
                    projects.append(project)

            # 2. 신규 교통노선 조회
            # new_lines = await self._get_new_transit_lines(lat, lng)
            new_lines = []

            for line in new_lines:
                project = DevelopmentInfo(
                    name=line.get("name", ""),
                    development_type="신규노선",
                    status=line.get("status", "예정"),
                    expected_completion=line.get("completion_year"),
                    distance_km=line.get("distance_km", 0),
                    impact_level="높음",
                    description=f"{line.get('name')} 개통 예정"
                )
                projects.append(project)

            # 총 영향도 점수 계산
            impact_score = self._calculate_development_score(projects)

            return projects, impact_score

        except Exception as e:
            logger.error(f"개발호재 분석 실패: {e}")
            return [], 50.0  # 기본값

    def _assess_impact_level(self, plan: Dict) -> str:
        """개발 사업 영향도 평가"""
        scale = plan.get("scale", "")
        status = plan.get("status", "")

        if scale == "대규모" and status in ["시행중", "인가"]:
            return "높음"
        elif scale == "중규모" or status in ["시행중"]:
            return "보통"
        else:
            return "낮음"

    def _calculate_development_score(self, projects: List[DevelopmentInfo]) -> float:
        """개발호재 점수 계산"""
        if not projects:
            return 50.0  # 기본값

        score = 50.0  # 기본 점수

        for project in projects:
            if project.impact_level == "높음":
                score += 15
            elif project.impact_level == "보통":
                score += 10
            else:
                score += 5

        return min(100, score)


class LocationScoreCalculator:
    """입지 점수 계산기"""

    # 카테고리별 가중치
    WEIGHTS = {
        "transport": 0.35,  # 교통 35%
        "education": 0.25,  # 교육 25%
        "amenity": 0.20,  # 편의시설 20%
        "development": 0.20,  # 개발호재 20%
    }

    def calculate(
        self,
        transport: TransportScore,
        education: EducationScore,
        amenity: AmenityScore,
        development_score: float,
    ) -> Tuple[float, List[str], List[str]]:
        """종합 입지 점수 계산

        Returns:
            (총점, 강점 목록, 약점 목록)
        """
        scores = {
            "transport": transport.total_score,
            "education": education.total_score,
            "amenity": amenity.total_score,
            "development": development_score,
        }

        # 가중 평균
        total_score = sum(scores[key] * self.WEIGHTS[key] for key in scores)

        # 강점/약점 분석
        strengths, weaknesses = self._analyze_strengths_weaknesses(scores)

        return round(total_score, 1), strengths, weaknesses

    def _analyze_strengths_weaknesses(
        self, scores: Dict[str, float]
    ) -> Tuple[List[str], List[str]]:
        """강점/약점 분석"""
        strengths = []
        weaknesses = []

        thresholds = {
            "transport": ("교통 접근성", 70),
            "education": ("교육 환경", 70),
            "amenity": ("생활 편의성", 70),
            "development": ("개발 호재", 60),
        }

        for key, (name, threshold) in thresholds.items():
            if scores[key] >= threshold:
                strengths.append(f"{name} 우수")
            elif scores[key] < threshold - 20:
                weaknesses.append(f"{name} 미흡")

        return strengths, weaknesses


class LocationAnalyzerAgent:
    """입지분석 에이전트 메인 클래스"""

    def __init__(self, config: Optional[Dict] = None):
        """
        Args:
            config: 설정 딕셔너리
                - kakao_api_key: 카카오 API 키
                - naver_api_key: 네이버 API 키
        """
        self.config = config or {}

        # API 인터페이스 (실제 구현 시 교체)
        self.map_api = self._create_map_api()

        # 분석기 초기화
        self.transport_analyzer = TransportAnalyzer(self.map_api)
        self.education_analyzer = EducationAnalyzer(self.map_api, None)
        self.amenity_analyzer = AmenityAnalyzer(self.map_api)
        self.development_analyzer = DevelopmentAnalyzer(None, None)
        self.score_calculator = LocationScoreCalculator()

    def _create_map_api(self):
        """지도 API 인스턴스 생성 (인터페이스)"""
        # 실제 구현 시 KakaoMapAPI 등으로 교체
        class MockMapAPI:
            async def geocode(self, address: str) -> Tuple[Optional[float], Optional[float]]:
                """주소 -> 좌표 변환"""
                # 목업 구현
                logger.warning(f"MockMapAPI.geocode 호출: {address}")
                return None, None

            async def search_nearby(
                self, lat: float, lng: float, category: str, radius: int
            ):
                """주변 시설 검색"""
                logger.warning(f"MockMapAPI.search_nearby 호출: {category}, {radius}m")
                return []

        return MockMapAPI()

    async def analyze(
        self,
        case_number: str,
        address: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> LocationAnalysisResult:
        """입지 분석 수행

        Args:
            case_number: 사건번호
            address: 주소
            latitude: 위도 (선택)
            longitude: 경도 (선택)

        Returns:
            LocationAnalysisResult: 입지분석 결과
        """
        try:
            # 1. 좌표 확보
            if latitude is None or longitude is None:
                lat, lng = await self.map_api.geocode(address)
                if lat is None or lng is None:
                    raise ValueError(f"주소를 좌표로 변환할 수 없습니다: {address}")
            else:
                lat, lng = latitude, longitude

            logger.info(f"입지 분석 시작: {address} ({lat}, {lng})")

            # 2. 병렬 분석
            transport_task = self.transport_analyzer.analyze(lat, lng)
            education_task = self.education_analyzer.analyze(lat, lng)
            amenity_task = self.amenity_analyzer.analyze(lat, lng)
            development_task = self.development_analyzer.analyze(lat, lng, address)

            transport, education, amenity, (development_info, development_score) = (
                await asyncio.gather(
                    transport_task,
                    education_task,
                    amenity_task,
                    development_task,
                )
            )

            # 3. 종합 점수 계산
            total_score, strengths, weaknesses = self.score_calculator.calculate(
                transport, education, amenity, development_score
            )

            # 4. 주변 시설 목록 생성 (대표적인 것들)
            nearby_pois = self._create_poi_list(transport, education, amenity)

            # 5. 종합 평가 작성
            summary = self._generate_summary(total_score, strengths, weaknesses)
            outlook = self._generate_outlook(development_info)

            # 6. 결과 조합
            result = LocationAnalysisResult(
                case_number=case_number,
                address=address,
                latitude=lat,
                longitude=lng,
                total_score=total_score,
                transport_score=transport,
                education_score=education,
                amenity_score=amenity,
                development_info=development_info,
                development_score=development_score,
                nearby_pois=nearby_pois,
                summary=summary,
                strengths=strengths,
                weaknesses=weaknesses,
                outlook=outlook,
            )

            logger.info(f"입지 분석 완료: 총점 {total_score}점")
            return result

        except Exception as e:
            logger.error(f"입지 분석 실패: {e}", exc_info=True)
            # 실패 시 기본값 반환
            return LocationAnalysisResult(
                case_number=case_number,
                address=address,
                latitude=latitude,
                longitude=longitude,
                total_score=0,
                transport_score=TransportScore(total_score=0, note="분석 실패"),
                education_score=EducationScore(total_score=0, note="분석 실패"),
                amenity_score=AmenityScore(total_score=0, note="분석 실패"),
                summary=f"입지 분석 중 오류 발생: {str(e)}",
            )

    def _create_poi_list(
        self,
        transport: TransportScore,
        education: EducationScore,
        amenity: AmenityScore,
    ) -> List[POI]:
        """주변 시설 목록 생성"""
        pois = []

        # 지하철역
        if transport.nearest_subway and transport.subway_distance_meters:
            pois.append(
                POI(
                    name=transport.nearest_subway,
                    category=POICategory.SUBWAY,
                    distance_meters=transport.subway_distance_meters,
                    walk_time_minutes=transport.subway_walk_minutes,
                )
            )

        # 학교
        for school in education.elementary_schools[:2]:
            pois.append(
                POI(
                    name=school,
                    category=POICategory.SCHOOL,
                    distance_meters=education.nearest_elementary_meters or 0,
                )
            )

        # 마트
        for mart in amenity.marts_within_1km[:2]:
            pois.append(
                POI(
                    name=mart,
                    category=POICategory.MART,
                    distance_meters=0,  # 실제 거리는 API에서
                )
            )

        return pois

    def _generate_summary(
        self, total_score: float, strengths: List[str], weaknesses: List[str]
    ) -> str:
        """종합 평가 작성"""
        if total_score >= 80:
            grade = "매우 우수"
        elif total_score >= 65:
            grade = "우수"
        elif total_score >= 50:
            grade = "보통"
        else:
            grade = "미흡"

        summary = f"입지 종합 평가: {grade} ({total_score}점). "

        if strengths:
            summary += f"강점: {', '.join(strengths)}. "

        if weaknesses:
            summary += f"개선 필요: {', '.join(weaknesses)}."

        return summary.strip()

    def _generate_outlook(self, development_info: List[DevelopmentInfo]) -> str:
        """향후 전망 작성"""
        if not development_info:
            return "현재 특별한 개발 호재는 확인되지 않습니다."

        high_impact = [d for d in development_info if d.impact_level == "높음"]

        if high_impact:
            projects = ", ".join([d.name for d in high_impact[:2]])
            return f"{projects} 등 개발 호재로 향후 가치 상승 기대됩니다."
        else:
            return "일부 개발 호재가 있으나 영향은 제한적일 것으로 예상됩니다."


async def main():
    """테스트용 메인 함수"""
    agent = LocationAnalyzerAgent()

    # 테스트 실행
    result = await agent.analyze(
        case_number="2024타경12345",
        address="서울시 강남구 역삼동 123-45",
        latitude=37.5012,
        longitude=127.0396,
    )

    print(f"입지 분석 결과: {result.summary}")
    print(f"총점: {result.total_score}점")
    print(f"교통: {result.transport_score.total_score}점")
    print(f"교육: {result.education_score.total_score}점")
    print(f"편의시설: {result.amenity_score.total_score}점")
    print(f"개발호재: {result.development_score}점")


if __name__ == "__main__":
    asyncio.run(main())
