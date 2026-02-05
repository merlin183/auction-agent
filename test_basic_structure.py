"""기본 구조 검증 스크립트 (의존성 없이 실행 가능)"""
import ast
import sys
from pathlib import Path


def check_python_syntax(file_path):
    """Python 파일 구문 검증"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        ast.parse(source)
        return True, "OK"
    except SyntaxError as e:
        return False, f"Syntax Error: {e}"


def analyze_file_structure(file_path):
    """파일 구조 분석"""
    with open(file_path, 'r', encoding='utf-8') as f:
        source = f.read()

    tree = ast.parse(source)

    classes = []
    functions = []
    imports = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            classes.append(node.name)
        elif isinstance(node, ast.FunctionDef):
            if not node.name.startswith('_'):  # public 함수만
                functions.append(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            imports.append(ast.unparse(node))

    return {
        'classes': classes,
        'functions': functions,
        'imports': imports
    }


def main():
    data_collector_path = Path("C:/Users/vip3/Desktop/그리드라이프/개발/auction-agent/src/agents/data_collector.py")

    print("=" * 70)
    print("데이터수집 에이전트 구조 검증")
    print("=" * 70)
    print()

    # 1. 파일 존재 여부
    if not data_collector_path.exists():
        print("[X] 파일이 존재하지 않습니다.")
        sys.exit(1)

    print("[OK] 파일 존재 확인")

    # 2. 구문 검증
    is_valid, message = check_python_syntax(data_collector_path)
    if not is_valid:
        print(f"[ERROR] 구문 오류: {message}")
        sys.exit(1)

    print("[OK] Python 구문 검증 통과")

    # 3. 구조 분석
    structure = analyze_file_structure(data_collector_path)

    print()
    print("-" * 70)
    print("클래스 목록:")
    print("-" * 70)
    for cls in structure['classes']:
        print(f"  - {cls}")

    print()
    print("-" * 70)
    print("주요 함수:")
    print("-" * 70)
    for func in structure['functions'][:10]:  # 처음 10개만
        print(f"  - {func}")

    # 4. 필수 클래스 확인
    print()
    print("-" * 70)
    print("필수 클래스 확인:")
    print("-" * 70)

    required_classes = [
        "DataCollectorAgent",
        "CourtAuctionCrawler",
        "MolitRealTransactionAPI",
        "KakaoMapAPI",
        "RateLimiter",
        "Document",
        "RealTransaction",
        "LocationData",
        "CollectedData",
        "DataStore",
        "ClovaOCR",
        "RegistryParser",
        "AddressConverter",
    ]

    all_present = True
    for req_class in required_classes:
        if req_class in structure['classes']:
            print(f"  [OK] {req_class}")
        else:
            print(f"  [X] {req_class} - 누락")
            all_present = False

    # 5. 메인 에이전트 클래스 메서드 확인
    print()
    print("-" * 70)
    print("DataCollectorAgent 메서드 확인:")
    print("-" * 70)

    with open(data_collector_path, 'r', encoding='utf-8') as f:
        source = f.read()

    tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "DataCollectorAgent":
            methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
            for method in methods:
                if not method.startswith('_'):
                    print(f"  - {method}()")

    # 6. 결과 요약
    print()
    print("=" * 70)
    if all_present:
        print("[OK] 모든 필수 클래스가 정상적으로 구현되었습니다.")
        print()
        print("파일 정보:")
        print(f"  - 총 클래스 수: {len(structure['classes'])}")
        print(f"  - 총 함수 수: {len(structure['functions'])}")
        print(f"  - Import 수: {len(structure['imports'])}")
        print()
        print("[OK] 구조 검증 완료")
    else:
        print("[X] 일부 필수 클래스가 누락되었습니다.")
        sys.exit(1)

    print("=" * 70)


if __name__ == "__main__":
    main()
