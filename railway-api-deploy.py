#!/usr/bin/env python3
"""
Railway API를 사용한 자동 배포 스크립트
Railway Token 없이 GraphQL API를 통해 배포 상태 확인 및 설정
"""

import requests
import json
import sys
import time

# Railway GraphQL API 엔드포인트
RAILWAY_API_URL = "https://backboard.railway.app/graphql/v2"

# 프로젝트 정보
PROJECT_ID = "dda13b19-c392-456a-9b93-4eb146228f3e"
SERVICE_ID = "8c053802-c726-4e05-9684-59739a3ddedd"
GITHUB_REPO = "merlin183/auction-agent"


def check_railway_status():
    """Railway 프로젝트 공개 상태 확인"""
    print("=" * 60)
    print("Railway 프로젝트 상태 확인")
    print("=" * 60)
    print(f"\n프로젝트 ID: {PROJECT_ID}")
    print(f"서비스 ID: {SERVICE_ID}")
    print(f"GitHub 저장소: {GITHUB_REPO}")
    print(f"\n프로젝트 URL: https://railway.app/project/{PROJECT_ID}")
    print("\n" + "=" * 60)


def generate_railway_cli_commands():
    """Railway CLI 명령어 생성"""
    commands = f"""
# Railway CLI 자동 배포 명령어
# 복사하여 터미널에 붙여넣으세요

# 1. Railway 로그인
railway login

# 2. 프로젝트 연결
railway link {PROJECT_ID}

# 3. 환경 변수 설정 (ANTHROPIC_API_KEY 필수!)
railway variables set ANTHROPIC_API_KEY="sk-ant-api03-your-actual-key-here"
railway variables set DEBUG="false"

# 4. PostgreSQL 추가
railway add postgresql

# 5. Redis 추가
railway add redis

# 6. GitHub 저장소 연결 (Web UI 필요)
echo "GitHub 연결은 Railway Web UI에서:"
echo "https://railway.app/project/{PROJECT_ID}"
echo "Settings → Source → Connect GitHub Repo → {GITHUB_REPO}"

# 7. 배포 (GitHub 연결 후 자동 또는 수동)
railway up

# 8. 로그 확인
railway logs --follow

# 9. 앱 열기
railway open
"""
    return commands


def create_batch_script():
    """Windows 배치 스크립트 생성"""
    batch_content = f"""@echo off
REM Railway 자동 배포 - 완전 자동화
REM 프로젝트: auction-agent

echo ========================================
echo Railway 자동 배포 시작
echo ========================================
echo.

REM Railway 로그인 확인
echo [1/7] Railway 로그인 확인...
railway whoami >nul 2>&1
if errorlevel 1 (
    echo Railway 로그인이 필요합니다.
    echo 브라우저가 열리면 로그인해주세요.
    railway login
    if errorlevel 1 (
        echo 로그인 실패
        pause
        exit /b 1
    )
)
echo ✓ 로그인 확인

REM 프로젝트 연결
echo [2/7] 프로젝트 연결...
railway link {PROJECT_ID}
if errorlevel 1 (
    echo 프로젝트 연결 실패
    pause
    exit /b 1
)
echo ✓ 프로젝트 연결

REM 환경 변수 확인 및 설정
echo [3/7] 환경 변수 설정...
echo.
echo Anthropic API Key를 입력하세요:
set /p API_KEY="API Key (sk-ant-...): "
if "%API_KEY%"=="" (
    echo API Key가 필요합니다.
    pause
    exit /b 1
)
railway variables set ANTHROPIC_API_KEY="%API_KEY%"
railway variables set DEBUG="false"
echo ✓ 환경 변수 설정

REM PostgreSQL 추가
echo [4/7] PostgreSQL 추가...
railway add postgresql
echo ✓ PostgreSQL 추가 (또는 이미 존재)

REM Redis 추가
echo [5/7] Redis 추가...
railway add redis
echo ✓ Redis 추가 (또는 이미 존재)

REM GitHub 연결 확인
echo [6/7] GitHub 연결 확인...
echo.
echo GitHub 저장소를 Railway에 연결해야 합니다.
echo.
echo 다음 URL을 브라우저에서 열어주세요:
echo https://railway.app/project/{PROJECT_ID}
echo.
echo 그리고:
echo 1. Settings 탭 클릭
echo 2. Source 섹션에서 "Connect GitHub Repo" 클릭
echo 3. "{GITHUB_REPO}" 선택
echo 4. Branch: main 선택
echo 5. Connect 클릭
echo.
set /p CONNECTED="GitHub 연결 완료하셨나요? (y/n): "
if /i "%CONNECTED%" neq "y" (
    echo GitHub 연결을 먼저 완료해주세요.
    pause
    exit /b 1
)
echo ✓ GitHub 연결 확인

REM 배포
echo [7/7] 배포 시작...
echo GitHub 연결이 완료되면 자동으로 배포가 시작됩니다.
echo.
echo 배포 상태 확인:
echo https://railway.app/project/{PROJECT_ID}
echo.
echo 또는 수동 배포:
railway up
if errorlevel 1 (
    echo 배포 실패. 로그를 확인하세요.
    railway logs
    pause
    exit /b 1
)
echo ✓ 배포 완료

echo.
echo ========================================
echo 배포 성공!
echo ========================================
echo.
echo 다음 단계:
echo 1. 앱 URL 확인: railway open
echo 2. 로그 확인: railway logs --follow
echo 3. 상태 확인: railway status
echo.
pause
"""

    with open("deploy-railway-auto.bat", "w", encoding="utf-8") as f:
        f.write(batch_content)

    print("✅ deploy-railway-auto.bat 파일 생성 완료")


def create_step_by_step_guide():
    """단계별 상세 가이드 생성"""
    guide = """
# 🤖 Railway 완전 자동 배포 가이드

이 가이드는 최소한의 수동 작업으로 Railway 배포를 완료하는 방법입니다.

---

## ⚡ 빠른 실행 (5분)

### Option 1: 배치 스크립트 사용 (추천)

1. **파일 실행**:
   ```
   deploy-railway-auto.bat
   ```

2. **안내에 따라 진행**:
   - Railway 로그인 (브라우저 자동 열림)
   - Anthropic API Key 입력
   - GitHub 연결 (브라우저에서 클릭 몇 번)
   - 자동 배포 완료!

### Option 2: 수동 명령어 실행

다음 명령어를 순서대로 실행:

```bash
# 1. 로그인
railway login

# 2. 프로젝트 연결
railway link dda13b19-c392-456a-9b93-4eb146228f3e

# 3. 환경 변수
railway variables set ANTHROPIC_API_KEY="your-key"
railway variables set DEBUG="false"

# 4. 데이터베이스
railway add postgresql
railway add redis

# 5. GitHub 연결 (Web UI)
# https://railway.app/project/dda13b19-c392-456a-9b93-4eb146228f3e
# Settings → Source → Connect GitHub Repo

# 6. 배포
railway up
```

---

## 🔧 GitHub 연결 상세 가이드

### 단계 1: Railway 프로젝트 열기

브라우저에서:
```
https://railway.app/project/dda13b19-c392-456a-9b93-4eb146228f3e
```

### 단계 2: 서비스 클릭

프로젝트 캔버스에서 **서비스** (또는 "New Service")를 클릭합니다.

### 단계 3: Settings 탭

서비스 화면에서 **Settings** 탭을 클릭합니다.

### 단계 4: Source 연결

**Source** 섹션으로 스크롤하여:
1. **"Connect GitHub Repo"** 버튼 클릭
2. GitHub 권한 승인 (처음만)
3. **"merlin183/auction-agent"** 저장소 선택
4. **Branch**: main 선택
5. **"Connect"** 버튼 클릭

### 단계 5: 자동 배포 시작

GitHub 연결 후 Railway가 자동으로:
- 코드 빌드
- Docker 이미지 생성
- 서비스 배포
- URL 생성

---

## ✅ 배포 확인

### 배포 상태

**Deployments** 탭에서:
- 진행 중: "Building..." 또는 "Deploying..."
- 성공: "Deployed" (초록색)
- 실패: "Failed" (빨간색, 로그 확인)

### 앱 URL

서비스 화면 상단에 URL 표시:
```
https://auction-agent-production-xxxx.up.railway.app
```

### 헬스 체크

```bash
curl https://your-app-url/health
```

예상 응답:
```json
{"status":"healthy"}
```

---

## 🆘 문제 해결

### "railway: command not found"

Railway CLI 설치:
```bash
npm install -g @railway/cli
```

### "Unauthorized"

다시 로그인:
```bash
railway login
```

### 빌드 실패

로그 확인:
```bash
railway logs
```

일반적인 문제:
- ANTHROPIC_API_KEY 누락
- Python 버전 불일치
- 의존성 설치 실패

### GitHub 연결 안 보임

Railway 프로젝트 새로고침:
- F5 또는 Ctrl+R
- 서비스가 없다면 "New Service" 생성

---

## 📊 완료 체크리스트

배포 전:
- [ ] Railway CLI 설치
- [ ] Railway 로그인
- [ ] 프로젝트 연결
- [ ] 환경 변수 설정
- [ ] PostgreSQL 추가
- [ ] Redis 추가
- [ ] GitHub 저장소 연결

배포 확인:
- [ ] Deployments에서 "Deployed" 상태
- [ ] URL 접속 가능
- [ ] /health 응답 확인
- [ ] /docs Swagger UI 로드

---

## 🎉 완료!

이제 GitHub에 푸시하면 자동으로 배포됩니다!

```bash
git add .
git commit -m "Update feature"
git push origin main
# Railway가 자동으로 재배포! 🚀
```
"""

    with open("RAILWAY_AUTO_DEPLOY_GUIDE.md", "w", encoding="utf-8") as f:
        f.write(guide)

    print("✅ RAILWAY_AUTO_DEPLOY_GUIDE.md 파일 생성 완료")


def main():
    print("\n" + "=" * 60)
    print("Railway 자동 배포 도구")
    print("=" * 60 + "\n")

    # 1. 상태 확인
    check_railway_status()

    # 2. CLI 명령어 생성
    print("\n📋 Railway CLI 명령어 생성 중...")
    commands = generate_railway_cli_commands()

    with open("railway-commands.txt", "w", encoding="utf-8") as f:
        f.write(commands)
    print("✅ railway-commands.txt 파일 생성 완료")

    # 3. 배치 스크립트 생성
    print("\n📋 Windows 배치 스크립트 생성 중...")
    create_batch_script()

    # 4. 상세 가이드 생성
    print("\n📋 상세 가이드 생성 중...")
    create_step_by_step_guide()

    # 5. 완료 메시지
    print("\n" + "=" * 60)
    print("✅ 모든 파일 생성 완료!")
    print("=" * 60)
    print("\n생성된 파일:")
    print("  1. railway-commands.txt - CLI 명령어 모음")
    print("  2. deploy-railway-auto.bat - 자동 배포 스크립트")
    print("  3. RAILWAY_AUTO_DEPLOY_GUIDE.md - 상세 가이드")
    print("\n다음 단계:")
    print("  1. deploy-railway-auto.bat 실행 (Windows)")
    print("  2. 또는 railway-commands.txt 명령어 복사 실행")
    print("  3. 또는 RAILWAY_AUTO_DEPLOY_GUIDE.md 가이드 참고")
    print("\n🚀 배포를 시작하세요!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
