# 🔧 Railway 빌드 실패 해결 가이드

## 🔍 빌드 실패 원인 확인

### 1단계: 로그 확인

Railway에서:
1. 실패한 배포 클릭
2. **"View Logs"** 버튼 클릭
3. 빌드 로그에서 오류 메시지 찾기

**일반적인 오류 패턴**:
- `ModuleNotFoundError` → 의존성 문제
- `No module named` → Python 패키지 누락
- `command not found` → 빌드 명령어 오류
- `syntax error` → 코드 문법 오류

---

## ✅ 일반적인 해결 방법

### 해결책 1: Python 버전 명시

`runtime.txt` 파일 확인:

```txt
python-3.11
```

**현재 상태 확인**:
- railway.json이 올바른지
- runtime.txt가 있는지

### 해결책 2: 의존성 설치 확인

**requirements.txt 확인**:
```bash
cd "C:\Users\user\Desktop\그리드라이프\개발\개발\auction-agent"
cat requirements.txt
```

**필수 패키지 확인**:
- langchain
- langgraph
- fastapi
- uvicorn
- pydantic

### 해결책 3: 빌드 명령어 수정

**railway.json 확인**:
```json
{
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "uvicorn src.api:app --host 0.0.0.0 --port $PORT",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 3
  }
}
```

---

## 🚀 빠른 수정 (가장 많은 경우)

### 문제: 의존성 설치 실패

**해결**:
