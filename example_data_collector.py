"""데이터수집 에이전트 사용 예시

이 스크립트는 DataCollectorAgent의 기본 사용법을 보여줍니다.
Mock 모드로 실행되므로 외부 API 키 없이 테스트 가능합니다.
"""
import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from agents.data_collector import DataCollectorAgent, collect_auction_data


async def example_basic_usage():
    """기본 사용 예시"""
    print("=" * 80)
    print("예시 1: 기본 사용법")
    print("=" * 80)
    print()

    # Mock 모드 설정 (실제 API 호출 없이 테스트)
    config = {
        "molit_api_key": "mock-key",
        "kakao_api_key": "mock-key",
        "ocr_url": "mock-url",
        "ocr_key": "mock-key",
        "mock_mode": True,  # Mock 모드 활성화
        "save_to_db": False,  # DB 저장 비활성화
    }

    # 에이전트 생성
    agent = DataCollectorAgent(config)

    # 경매 정보 수집
    case_number = "2024타경12345"
    print(f"경매 정보 수집 중: {case_number}")
    print()

    collected_data = await agent.collect(case_number)

    # 결과 출력
    print("-" * 80)
    print("수집 결과")
    print("-" * 80)
    print()

    # 1. 경매 기본 정보
    prop = collected_data.auction_property
    print("[경매 기본 정보]")
    print(f"  사건번호: {prop.case_number}")
    print(f"  관할법원: {prop.court}")
    print(f"  물건종류: {prop.property_type.value}")
    print(f"  주소: {prop.address}")
    print(f"  상세주소: {prop.detail_address}")
    print(f"  감정가: {prop.appraisal_value:,}원")
    print(f"  최저입찰가: {prop.minimum_bid:,}원")
    print(f"  입찰율: {prop.bid_rate * 100:.1f}%")
    print(f"  할인율: {prop.discount_rate * 100:.1f}%")
    print(f"  매각기일: {prop.auction_date}")
    print(f"  입찰회차: {prop.bid_count}회")
    print()

    # 2. 면적 정보
    if prop.exclusive_area_sqm:
        print("[면적 정보]")
        print(f"  전용면적: {prop.exclusive_area_sqm}㎡ ({prop.exclusive_area_pyung:.1f}평)")
        if prop.building_area_sqm:
            print(f"  건물면적: {prop.building_area_sqm}㎡")
        if prop.land_area_sqm:
            print(f"  대지면적: {prop.land_area_sqm}㎡")
        print()

    # 3. 건물 정보
    if prop.building_year:
        print("[건물 정보]")
        print(f"  건축년도: {prop.building_year}년")
        if prop.floor and prop.total_floors:
            print(f"  층수: {prop.floor}층 / {prop.total_floors}층")
        print()

    # 4. 문서 정보
    print("[수집 문서]")
    print(f"  총 {len(collected_data.documents)}개 문서 수집")
    for doc in collected_data.documents:
        doc_type_name = {
            "registry": "등기부등본",
            "status_report": "현황조사서",
            "appraisal": "감정평가서",
            "sale_specification": "매각물건명세서",
        }.get(doc.doc_type, doc.doc_type)
        print(f"  - {doc_type_name}")
    print()

    # 5. 실거래가 정보
    print("[실거래가 정보]")
    print(f"  총 {len(collected_data.real_transactions)}건 수집")
    if collected_data.real_transactions:
        # 최근 3건만 출력
        for trans in collected_data.real_transactions[:3]:
            print(f"  - {trans.transaction_date}: {trans.price:,}원 "
                  f"({trans.area}㎡, {trans.floor}층)")
    print()

    # 6. 위치 정보
    if collected_data.location_data:
        loc = collected_data.location_data
        print("[위치 정보]")
        print(f"  좌표: ({loc.lat}, {loc.lng})")
        print(f"  주변 시설:")
        for facility_type, info in loc.facilities.items():
            facility_name_kr = {
                "subway": "지하철",
                "school": "학교",
                "hospital": "병원",
                "mart": "마트",
                "attraction": "공원/명소",
            }.get(facility_type, facility_type)
            print(f"    - {facility_name_kr}: {info['name']} ({info['distance']}m)")
        print()

    print("-" * 80)
    print("수집 완료")
    print("-" * 80)


async def example_multiple_cases():
    """여러 사건 수집 예시"""
    print()
    print("=" * 80)
    print("예시 2: 여러 사건 수집")
    print("=" * 80)
    print()

    config = {
        "mock_mode": True,
        "save_to_db": False,
    }

    agent = DataCollectorAgent(config)

    case_numbers = [
        "2024타경12345",
        "2024타경23456",
        "2024타경34567",
    ]

    print(f"총 {len(case_numbers)}건의 경매 정보 수집")
    print()

    results = []
    for case_number in case_numbers:
        try:
            data = await agent.collect(case_number)
            results.append(data)
            print(f"  [OK] {case_number}: {data.auction_property.address}")
        except Exception as e:
            print(f"  [실패] {case_number}: {str(e)}")

    print()
    print(f"수집 완료: {len(results)}/{len(case_numbers)}건")


async def example_with_utility_function():
    """유틸리티 함수 사용 예시"""
    print()
    print("=" * 80)
    print("예시 3: 유틸리티 함수 사용")
    print("=" * 80)
    print()

    config = {"mock_mode": True}

    # collect_auction_data 유틸리티 함수 사용
    data = await collect_auction_data("2024타경12345", config)

    print(f"사건번호: {data.auction_property.case_number}")
    print(f"감정가: {data.auction_property.appraisal_value:,}원")
    print(f"최저입찰가: {data.auction_property.minimum_bid:,}원")
    print(f"실거래 건수: {len(data.real_transactions)}건")


async def main():
    """메인 실행 함수"""
    try:
        # 예시 1: 기본 사용법
        await example_basic_usage()

        # 예시 2: 여러 사건 수집
        await example_multiple_cases()

        # 예시 3: 유틸리티 함수
        await example_with_utility_function()

        print()
        print("=" * 80)
        print("모든 예시 실행 완료!")
        print()
        print("실제 사용 시:")
        print("  1. API 키 발급 (국토교통부, 카카오, Clova OCR)")
        print("  2. config에서 mock_mode=False로 변경")
        print("  3. 실제 사건번호로 테스트")
        print("=" * 80)

    except Exception as e:
        print(f"오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Python 3.7+에서 실행
    asyncio.run(main())
