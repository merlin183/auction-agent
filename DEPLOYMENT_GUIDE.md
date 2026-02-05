# 경매 AI 에이전트 배포 가이드

Railway를 이용한 프로덕션 배포 완벽 가이드입니다. 초보자도 쉽게 따라할 수 있도록 모든 단계를 상세히 설명합니다.

## 목차

1. [사전 준비사항](#1-사전-준비사항)
2. [GitHub 저장소 설정](#2-github-저장소-설정)
3. [Railway 프로젝트 설정](#3-railway-프로젝트-설정)
4. [환경 변수 설정](#4-환경-변수-설정)
5. [데이터베이스 마이그레이션](#5-데이터베이스-마이그레이션)
6. [자동 배포 설정](#6-자동-배포-설정)
7. [CI/CD 파이프라인 구성](#7-cicd-파이프라인-구성)
8. [테스트 및 검증](#8-테스트-및-검증)
9. [모니터링 및 로깅](#9-모니터링-및-로깅)
10. [문제 해결 (FAQ)](#10-문제-해결-faq)

---

## 1. 사전 준비사항

### 1.1 필수 계정 생성

배포를 시작하기 전에 다음 계정들을 준비해주세요.

#### GitHub 계정
- **목적**: 소스 코드 버전 관리 및 협업
- **가입**: https://github.com/join
- **요금**: 무료 (Private 저장소 포함)

#### Railway 계정
- **목적**: 애플리케이션 호스팅
- **가입**: https://railway.app/ (GitHub으로 로그인 가능)
- **요금**:
  - Hobby Plan: $5/월 (500시간 실행 시간, $5 크레딧 포함)
  - 처음 사용 시 $5 무료 크레딧 제공

#### Anthropic API 키
- **목적**: Claude AI 모델 사용
- **발급**: https://console.anthropic.com/
- **요금**: 사용량 기반 (API 호출마다 과금)
  - Claude Sonnet: $3 / 1M input tokens, $15 / 1M output tokens
  - Claude Opus: $15 / 1M input tokens, $75 / 1M output tokens
- **발급 절차**:
  1. Anthropic Console 접속
  2. 우측 상단 프로필 클릭
  3. "API Keys" 메뉴 선택
  4. "Create Key" 클릭
  5. 키 이름 입력 (예: `auction-agent-production`)
  6. 생성된 키 복사 (⚠️ 한 번만 표시됩니다!)

### 1.2 선택 사항 API 키

다음 API들은 선택 사항이지만, 사용하면 분석 품질이 향상됩니다.

#### 국토교통부 공공데이터 API
- **목적**: 실거래가, 건축물대장 등 부동산 데이터
- **발급**: https://www.data.go.kr/
- **요금**: 무료
- **발급 절차**:
  1. 공공데이터포털 회원가입
  2. "부동산 실거래가" 검색
  3. 활용신청 클릭
  4. 승인 후 마이페이지에서 인증키 확인

#### 카카오맵 API
- **목적**: 지도, 주소 검색, 주변 시설 정보
- **발급**: https://developers.kakao.com/
- **요금**: 월 30만건까지 무료
- **발급 절차**:
  1. 카카오 개발자 센터 가입
  2. "내 애플리케이션" → "애플리케이션 추가하기"
  3. 앱 이름 입력 (예: `경매AI에이전트`)
  4. "REST API 키" 복사

### 1.3 개발 환경 준비

로컬 컴퓨터에 다음 도구들을 설치해주세요.

#### Git 설치
```bash
# Windows
https://git-scm.com/download/win 에서 다운로드

# macOS (Homebrew 사용)
brew install git

# Linux (Ubuntu/Debian)
sudo apt-get install git
```

설치 확인:
```bash
git --version
# 출력 예: git version 2.40.0
```

#### GitHub CLI (선택사항, 편리함)
```bash
# Windows (winget)
winget install GitHub.cli

# macOS
brew install gh

# Linux
sudo apt install gh
```

인증:
```bash
gh auth login
# 프롬프트에 따라 GitHub 계정 연동
```

---

## 2. GitHub 저장소 설정

### 2.1 Git 저장소 초기화

현재 프로젝트 폴더로 이동한 후:

```bash
# 프로젝트 디렉토리로 이동
cd C:\Users\user\Desktop\그리드라이프\개발\개발\auction-agent

# Git 초기화
git init

# 기본 브랜치 이름 설정 (main)
git branch -M main
```

### 2.2 .gitignore 파일 생성

민감한 정보와 불필요한 파일을 제외하기 위한 `.gitignore` 파일을 생성합니다.

**`.gitignore` 파일 내용:**
```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual Environment
venv/
env/
ENV/
.venv

# Environment Variables
.env
.env.local
.env.*.local

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/
outputs/
cache/

# Database
*.db
*.sqlite3

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# Railway
.railway/

# Temporary files
tmp/
temp/
*.tmp
```

### 2.3 첫 커밋 생성

```bash
# 모든 파일 스테이징
git add .

# 첫 커밋
git commit -m "Initial commit: Auction AI Agent System"
```

### 2.4 GitHub 저장소 생성

#### 방법 1: GitHub CLI 사용 (추천)

```bash
# Private 저장소 생성 및 푸시 (한 번에!)
gh repo create auction-ai-agent \
  --private \
  --source=. \
  --remote=origin \
  --push
```

#### 방법 2: 웹 브라우저 사용

1. **GitHub 웹사이트 접속**: https://github.com/new

2. **저장소 정보 입력**:
   - Repository name: `auction-ai-agent`
   - Description: `부동산 경매 AI 분석 플랫폼 - 멀티 에이전트 시스템`
   - Visibility: **Private** (⚠️ 중요: API 키 보호)
   - ❌ "Add a README file" 체크 해제 (이미 있음)
   - ❌ ".gitignore" 선택 안함 (이미 있음)

3. **Create repository** 클릭

4. **로컬 저장소와 연결**:
   ```bash
   # GitHub 저장소 URL 연결 (your-username을 본인 계정으로 변경)
   git remote add origin https://github.com/your-username/auction-ai-agent.git

   # 코드 푸시
   git push -u origin main
   ```

### 2.5 브랜치 보호 규칙 설정 (권장)

프로덕션 안정성을 위해 main 브랜치를 보호합니다.

1. GitHub 저장소 페이지 → **Settings** 탭
2. 좌측 메뉴 → **Branches**
3. **Add branch protection rule** 클릭
4. 설정:
   - Branch name pattern: `main`
   - ✅ **Require a pull request before merging** (PR 필수)
   - ✅ **Require status checks to pass before merging** (CI 통과 필수)
   - ✅ **Require branches to be up to date before merging**
5. **Create** 클릭

---

## 3. Railway 프로젝트 설정

### 3.1 Railway 프로젝트 생성

1. **Railway 대시보드 접속**: https://railway.app/dashboard

2. **New Project 클릭**

3. **"Deploy from GitHub repo" 선택**

4. **GitHub 저장소 연동**:
   - "Configure GitHub App" 클릭
   - Railway에 저장소 접근 권한 부여
   - `auction-ai-agent` 저장소 선택

5. **저장소 선택 후 배포 시작**:
   - Railway가 자동으로 저장소를 감지합니다
   - Dockerfile이 있으면 자동으로 Docker 빌드를 시작합니다

### 3.2 서비스 추가 (PostgreSQL)

Railway 대시보드에서:

1. **+ New 버튼** 클릭

2. **"Database" → "Add PostgreSQL"** 선택

3. **자동으로 PostgreSQL 인스턴스 생성됨**
   - 데이터베이스 이름, 사용자, 비밀번호가 자동 생성됩니다
   - 연결 정보는 "Variables" 탭에서 확인 가능

4. **연결 정보 확인**:
   - PostgreSQL 서비스 클릭
   - "Connect" 탭 → "Available Variables" 확인
   - `DATABASE_URL` 변수 자동 생성됨

### 3.3 서비스 추가 (Redis)

1. **+ New 버튼** 클릭

2. **"Database" → "Add Redis"** 선택

3. **자동으로 Redis 인스턴스 생성됨**
   - `REDIS_URL` 변수 자동 생성됨

### 3.4 서비스 연결 구성

Railway는 같은 프로젝트 내의 서비스들을 자동으로 네트워크로 연결합니다.

**현재 구성**:
```
┌─────────────────────────────────────┐
│      Railway Project                │
├─────────────────────────────────────┤
│  ┌──────────────┐                  │
│  │   App        │                  │
│  │  (FastAPI)   │                  │
│  └──────┬───────┘                  │
│         │                           │
│    ┌────┴────┬──────────┐          │
│    │         │          │          │
│  ┌─▼─────┐ ┌▼──────┐ ┌─▼──────┐  │
│  │Postgres│ │Redis  │ │ Volume │  │
│  └────────┘ └───────┘ └────────┘  │
└─────────────────────────────────────┘
```

### 3.5 도메인 설정

1. **App 서비스 클릭** → **Settings** 탭

2. **"Networking" 섹션**:
   - **Generate Domain** 클릭
   - 자동으로 `your-app.up.railway.app` 형식의 도메인 생성

3. **커스텀 도메인 (선택사항)**:
   - "Custom Domain" 입력란에 도메인 입력 (예: `api.yourdomain.com`)
   - Railway가 제공하는 DNS 설정을 도메인 관리 페이지에 추가

---

## 4. 환경 변수 설정

### 4.1 Railway 환경 변수 추가

Railway 대시보드에서 App 서비스 선택 → **Variables** 탭:

#### 필수 환경 변수

| 변수 이름 | 설명 | 예시 값 |
|----------|------|---------|
| `ANTHROPIC_API_KEY` | Claude API 키 | `sk-ant-api03-xxx...` |
| `DATABASE_URL` | PostgreSQL 연결 URL | 자동 설정됨 (수정 불필요) |
| `REDIS_URL` | Redis 연결 URL | 자동 설정됨 (수정 불필요) |

#### 선택 환경 변수

| 변수 이름 | 설명 | 기본값 |
|----------|------|--------|
| `MOLIT_API_KEY` | 국토교통부 API 키 | (없음) |
| `KAKAO_API_KEY` | 카카오맵 API 키 | (없음) |
| `DEBUG` | 디버그 모드 | `false` |
| `OPENAI_API_KEY` | OpenAI API 키 (선택) | (없음) |

#### Railway에서 환경 변수 추가하기

1. **Raw Editor 클릭** (오른쪽 상단)

2. **아래 내용 붙여넣기** (값은 본인의 키로 변경):
   ```env
   # AI API Keys
   ANTHROPIC_API_KEY=sk-ant-api03-xxx...

   # Optional External APIs
   MOLIT_API_KEY=your_molit_key_here
   KAKAO_API_KEY=your_kakao_key_here

   # App Settings
   DEBUG=false
   ```

3. **Save Changes** 클릭

4. **자동으로 재배포 시작됨**

### 4.2 환경 변수 체크리스트

배포 전에 확인하세요:

- [ ] `ANTHROPIC_API_KEY`가 올바르게 설정되었는가?
- [ ] `DATABASE_URL`이 PostgreSQL 서비스와 연결되어 있는가?
- [ ] `REDIS_URL`이 Redis 서비스와 연결되어 있는가?
- [ ] `DEBUG`가 `false`로 설정되어 있는가? (프로덕션)
- [ ] API 키에 공백이나 줄바꿈이 없는가?

### 4.3 환경 변수 검증 방법

Railway 배포 로그에서 확인:

```bash
# Railway CLI 설치 (선택사항)
npm i -g @railway/cli

# 프로젝트 연결
railway link

# 로그 확인
railway logs
```

로그에서 찾아야 할 내용:
```
✅ Database connection established
✅ Redis connection established
✅ Anthropic API key validated
```

---

## 5. 데이터베이스 마이그레이션

### 5.1 마이그레이션 스크립트 생성

현재 프로젝트는 SQLAlchemy를 사용하므로, 데이터베이스 스키마 초기화가 필요합니다.

**`scripts/init_db.py` 생성:**

```python
"""데이터베이스 초기화 스크립트"""
import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine
from config.settings import get_settings

async def init_db():
    """데이터베이스 테이블 생성"""
    settings = get_settings()

    engine = create_async_engine(settings.database_url, echo=True)

    # 여기서 Base.metadata.create_all()을 실행
    # (현재 프로젝트에 모델이 정의되어 있다면)

    print("✅ Database initialized successfully")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(init_db())
```

### 5.2 Railway에서 마이그레이션 실행

#### 방법 1: Railway CLI 사용

```bash
# Railway 프로젝트 연결
railway link

# 마이그레이션 실행
railway run python scripts/init_db.py
```

#### 방법 2: 배포 후 자동 실행

**`railway.toml` 파일 수정** (이미 존재하면 업데이트):

```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "Dockerfile"

[deploy]
startCommand = "python scripts/init_db.py && uvicorn src.api:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
healthcheckTimeout = 100
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10
```

### 5.3 데이터베이스 백업 설정

Railway는 자동 백업을 제공하지만, 수동 백업도 설정할 수 있습니다.

1. **PostgreSQL 서비스** → **Settings** 탭
2. **"Backups" 섹션** → Enable 클릭
3. 일일 자동 백업 활성화

---

## 6. 자동 배포 설정

### 6.1 Git Push 자동 배포

Railway는 기본적으로 GitHub 저장소의 `main` 브랜치에 푸시하면 자동 배포됩니다.

**테스트해보기:**

```bash
# 간단한 변경 사항 추가
echo "# Railway 자동 배포 테스트" >> README.md

# 커밋 및 푸시
git add README.md
git commit -m "test: Railway auto-deploy"
git push origin main
```

Railway 대시보드에서:
1. **Deployments** 탭 확인
2. 새로운 배포가 자동으로 시작됨
3. 빌드 로그 실시간 확인 가능

### 6.2 배포 트리거 설정

**Railway 프로젝트** → **Settings** → **Triggers**:

| 설정 | 값 | 설명 |
|------|---|------|
| Branch | `main` | main 브랜치만 자동 배포 |
| Deploy on PR | ❌ | PR은 수동 배포만 |
| Auto Deploy | ✅ | 커밋 푸시 시 자동 배포 |

### 6.3 배포 알림 설정

**Slack/Discord 웹훅 연동** (선택사항):

1. **Railway 프로젝트** → **Settings** → **Webhooks**
2. Deployment 이벤트에 대한 웹훅 URL 추가
3. 배포 성공/실패 시 팀 채널로 알림

---

## 7. CI/CD 파이프라인 구성

### 7.1 GitHub Actions 워크플로우 설정

**`.github/workflows/ci.yml` 파일 생성:**

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    name: Run Tests
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_auction
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'
        cache: 'pip'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e ".[dev]"

    - name: Run linting
      run: |
        pip install ruff
        ruff check src/ tests/

    - name: Run type checking
      run: |
        pip install mypy
        mypy src/ --ignore-missing-imports

    - name: Run tests with coverage
      env:
        ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/test_auction
        REDIS_URL: redis://localhost:6379
      run: |
        pytest tests/ --cov=src --cov-report=xml --cov-report=html -v

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v4
      with:
        file: ./coverage.xml
        fail_ci_if_error: false

  security:
    name: Security Scan
    runs-on: ubuntu-latest

    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Run Trivy vulnerability scanner
      uses: aquasecurity/trivy-action@master
      with:
        scan-type: 'fs'
        scan-ref: '.'
        format: 'sarif'
        output: 'trivy-results.sarif'

    - name: Upload Trivy results to GitHub Security
      uses: github/codeql-action/upload-sarif@v3
      with:
        sarif_file: 'trivy-results.sarif'

    - name: Run Bandit security linter
      run: |
        pip install bandit
        bandit -r src/ -f json -o bandit-report.json || true

    - name: Check dependencies for vulnerabilities
      run: |
        pip install safety
        safety check --json || true

  docker:
    name: Build Docker Image
    runs-on: ubuntu-latest
    needs: [test, security]
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'

    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3

    - name: Build Docker image
      uses: docker/build-push-action@v5
      with:
        context: .
        push: false
        tags: auction-ai-agent:${{ github.sha }}
        cache-from: type=gha
        cache-to: type=gha,mode=max
```

### 7.2 GitHub Secrets 설정

CI/CD에서 사용할 비밀 정보를 등록합니다.

1. **GitHub 저장소** → **Settings** → **Secrets and variables** → **Actions**

2. **New repository secret** 클릭

3. 다음 시크릿 추가:

| Name | Value | 용도 |
|------|-------|------|
| `ANTHROPIC_API_KEY` | `sk-ant-api03-xxx...` | 테스트용 API 키 |
| `CODECOV_TOKEN` | (선택) Codecov 토큰 | 커버리지 리포트 업로드 |

### 7.3 Pull Request 자동 테스트

PR을 생성하면 자동으로:
1. ✅ 코드 린팅 (Ruff)
2. ✅ 타입 체킹 (mypy)
3. ✅ 단위 테스트 실행
4. ✅ 보안 스캔 (Trivy, Bandit)
5. ✅ 커버리지 리포트

**PR 생성 예시:**

```bash
# 새 브랜치 생성
git checkout -b feature/new-agent

# 코드 작성 후 커밋
git add .
git commit -m "feat: Add new valuation agent"

# 푸시
git push origin feature/new-agent

# GitHub에서 Pull Request 생성
gh pr create --title "Add new valuation agent" --body "새로운 가치평가 에이전트 추가"
```

### 7.4 배포 승인 프로세스 (선택사항)

프로덕션 배포 전 수동 승인이 필요한 경우:

**`.github/workflows/deploy.yml` 생성:**

```yaml
name: Deploy to Production

on:
  workflow_dispatch:
  push:
    branches: [ main ]

jobs:
  deploy:
    name: Deploy to Railway
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://your-app.up.railway.app

    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Deploy to Railway
      run: |
        # Railway CLI를 사용한 배포 (자동으로 트리거됨)
        echo "Deployment triggered by git push"
```

**GitHub Environment 설정**:
1. **Settings** → **Environments** → **New environment**
2. Environment name: `production`
3. ✅ **Required reviewers** 체크
4. 승인자 추가 (팀 멤버)

---

## 8. 테스트 및 검증

### 8.1 배포 후 헬스 체크

배포가 완료되면 API가 정상 작동하는지 확인합니다.

```bash
# Railway 도메인으로 헬스 체크
curl https://your-app.up.railway.app/health

# 예상 응답:
# {"status":"healthy"}
```

### 8.2 API 엔드포인트 테스트

#### 경매 분석 API 테스트

```bash
# 동기 분석
curl -X POST https://your-app.up.railway.app/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "case_number": "2024타경12345",
    "options": {}
  }'
```

**예상 응답** (200 OK):
```json
{
  "status": "SUCCESS",
  "case_number": "2024타경12345",
  "reliability": 85.5,
  "report": { ... },
  "red_team_report": { ... }
}
```

#### 비동기 분석 API 테스트

```bash
# 1. 비동기 분석 시작
ANALYSIS_ID=$(curl -X POST https://your-app.up.railway.app/analyze/async \
  -H "Content-Type: application/json" \
  -d '{"case_number": "2024타경12345"}' | jq -r '.analysis_id')

echo "Analysis ID: $ANALYSIS_ID"

# 2. 상태 확인
curl https://your-app.up.railway.app/analyze/$ANALYSIS_ID
```

### 8.3 성능 테스트

부하 테스트로 시스템 안정성을 확인합니다.

#### Locust를 이용한 부하 테스트

**`tests/load_test.py` 생성:**

```python
"""Locust 부하 테스트"""
from locust import HttpUser, task, between

class AuctionAPIUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def health_check(self):
        self.client.get("/health")

    @task(1)
    def analyze_auction(self):
        self.client.post(
            "/analyze/async",
            json={"case_number": "2024타경12345"}
        )
```

**실행:**

```bash
# Locust 설치
pip install locust

# 부하 테스트 실행
locust -f tests/load_test.py --host=https://your-app.up.railway.app
```

웹 UI(http://localhost:8089)에서:
- Number of users: 10
- Spawn rate: 2
- 5분간 테스트 실행

**성공 기준**:
- ✅ 95th percentile 응답 시간 < 2초
- ✅ 에러율 < 1%
- ✅ RPS (초당 요청) > 10

### 8.4 모니터링 설정

#### Railway 기본 모니터링

Railway 대시보드에서 자동으로 제공:
- CPU 사용률
- 메모리 사용률
- 네트워크 트래픽
- 요청 수 (Requests Per Second)

#### 커스텀 메트릭 (Prometheus + Grafana)

**`src/monitoring.py` 추가:**

```python
"""Prometheus 메트릭"""
from prometheus_client import Counter, Histogram, generate_latest
from fastapi import Response

# 메트릭 정의
request_count = Counter(
    'auction_api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'auction_api_request_duration_seconds',
    'API request duration',
    ['method', 'endpoint']
)

analysis_count = Counter(
    'auction_analysis_total',
    'Total auction analyses',
    ['status']
)
```

**API에 메트릭 엔드포인트 추가** (`src/api.py`):

```python
from prometheus_client import generate_latest

@app.get("/metrics")
async def metrics():
    """Prometheus 메트릭"""
    return Response(
        content=generate_latest(),
        media_type="text/plain"
    )
```

### 8.5 로그 확인

#### Railway 로그 보기

```bash
# Railway CLI
railway logs --tail

# 최근 100줄
railway logs -n 100
```

#### 구조화된 로그 검색

프로젝트는 `structlog`를 사용하므로 JSON 형식 로그를 출력합니다.

**로그 예시:**
```json
{
  "event": "Starting auction analysis",
  "case_number": "2024타경12345",
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "info"
}
```

**Railway 대시보드에서 필터링**:
- `level:error` - 에러만 표시
- `case_number:"2024타경12345"` - 특정 사건 로그만
- `event:"Analysis failed"` - 실패한 분석만

---

## 9. 모니터링 및 로깅

### 9.1 애플리케이션 로깅 전략

#### 로그 레벨 설정

| 레벨 | 용도 | 예시 |
|------|------|------|
| DEBUG | 개발/디버깅 | 변수 값, 상세 흐름 |
| INFO | 일반 이벤트 | 분석 시작/완료, API 호출 |
| WARNING | 주의 필요 | 느린 응답, 재시도 |
| ERROR | 오류 발생 | 예외, 실패한 API 호출 |
| CRITICAL | 치명적 오류 | 서비스 다운, DB 연결 실패 |

#### 로그 구조화 모범 사례

**좋은 로그 예시:**
```python
logger.info(
    "Auction analysis started",
    case_number=case_number,
    user_id=user_id,
    options=options
)
```

**나쁜 로그 예시:**
```python
logger.info(f"Starting analysis for {case_number}")
# 문자열 포맷팅은 검색/필터링 어려움
```

### 9.2 에러 추적 (Sentry 연동)

심각한 에러를 자동으로 알림받기 위해 Sentry를 연동합니다.

#### Sentry 설정

1. **Sentry 가입**: https://sentry.io/signup/

2. **Python 프로젝트 생성**

3. **DSN 키 복사**

4. **Railway 환경 변수 추가**:
   ```env
   SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
   ```

5. **코드 통합** (`src/api.py`):

```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    integrations=[FastApiIntegration()],
    traces_sample_rate=0.1,  # 10% 트랜잭션 추적
    profiles_sample_rate=0.1,
    environment="production",
)
```

### 9.3 알림 설정

#### Railway 알림 (이메일/Slack)

1. **Railway 프로젝트** → **Settings** → **Notifications**
2. 알림 받을 이벤트 선택:
   - ✅ Deployment failed
   - ✅ Service crashed
   - ✅ High CPU usage (>80%)
   - ✅ High memory usage (>90%)

#### Sentry 알림

1. **Sentry 프로젝트** → **Settings** → **Alerts**
2. 알림 규칙 생성:
   - 에러 발생 시 즉시 알림
   - 같은 에러 10회 이상 시 알림
   - 에러율 > 5% 시 알림

### 9.4 대시보드 구성

#### Railway Metrics 대시보드

Railway 대시보드에서 기본 제공:
- CPU/메모리 사용률 차트
- 요청 수 및 응답 시간
- 에러율
- 배포 히스토리

#### Grafana 커스텀 대시보드 (고급)

**Grafana Cloud 무료 플랜 사용:**

1. **Grafana Cloud 가입**: https://grafana.com/

2. **Prometheus 데이터 소스 추가**:
   - Railway 앱의 `/metrics` 엔드포인트 연동

3. **대시보드 패널 구성**:
   - 총 분석 건수
   - 평균 분석 시간
   - 에이전트별 성공률
   - API 응답 시간 분포

---

## 10. 문제 해결 (FAQ)

### 10.1 배포 실패

#### 문제: "Build failed - Dockerfile not found"

**원인**: Railway가 Dockerfile을 찾지 못함

**해결**:
1. Dockerfile이 프로젝트 루트에 있는지 확인
2. `railway.toml`에서 경로 확인:
   ```toml
   [build]
   builder = "DOCKERFILE"
   dockerfilePath = "Dockerfile"
   ```

#### 문제: "Error: Failed to pull image"

**원인**: Docker 빌드 중 네트워크 오류

**해결**:
1. Railway 대시보드에서 "Redeploy" 클릭
2. 여전히 실패하면 Dockerfile에서 베이스 이미지 변경:
   ```dockerfile
   # 변경 전
   FROM python:3.11-slim

   # 변경 후
   FROM python:3.11-slim-bookworm
   ```

### 10.2 환경 변수 문제

#### 문제: "ANTHROPIC_API_KEY not found"

**원인**: 환경 변수가 설정되지 않았거나 잘못됨

**해결**:
1. Railway 대시보드 → Variables 탭 확인
2. 변수 이름에 오타가 없는지 확인 (대소문자 구분!)
3. 값에 공백/줄바꿈이 없는지 확인
4. 변경 후 재배포: "Redeploy" 클릭

#### 문제: "Database connection failed"

**원인**: `DATABASE_URL` 형식 오류

**해결**:
1. Railway PostgreSQL 서비스의 "Connect" 탭에서 정확한 URL 복사
2. URL 형식 확인:
   ```
   postgresql+asyncpg://user:password@host:port/database
   ```
3. `asyncpg` 드라이버 확인 (SQLAlchemy 비동기 연결)

### 10.3 성능 문제

#### 문제: "API 응답이 느림 (5초 이상)"

**원인**: Railway의 프리 티어 리소스 부족

**해결**:
1. **Railway 플랜 업그레이드**:
   - Hobby Plan: $5/월
   - Pro Plan: $20/월 (더 많은 CPU/메모리)

2. **코드 최적화**:
   - 데이터베이스 쿼리 최적화 (인덱스 추가)
   - Redis 캐싱 활용
   - 비동기 API 사용

3. **수평 확장**:
   - Railway에서 서비스 복제 (Scale to zero 비활성화)

#### 문제: "Out of Memory (OOM) 에러"

**원인**: 메모리 사용량 초과

**해결**:
1. **메모리 제한 확인**:
   - Railway Settings → Resources → Memory Limit

2. **메모리 누수 확인**:
   ```python
   # 메모리 프로파일링
   import tracemalloc
   tracemalloc.start()
   # ... 코드 실행
   print(tracemalloc.get_traced_memory())
   ```

3. **최적화**:
   - LLM 응답 스트리밍 사용
   - 불필요한 데이터 즉시 해제
   - 워커 프로세스 수 줄이기

### 10.4 데이터베이스 문제

#### 문제: "Too many connections"

**원인**: 데이터베이스 연결 풀 고갈

**해결**:
1. **연결 풀 설정 조정** (`src/services/database.py`):
   ```python
   engine = create_async_engine(
       settings.database_url,
       pool_size=5,          # 기본 연결 수
       max_overflow=10,      # 최대 추가 연결
       pool_timeout=30,      # 연결 대기 시간
       pool_recycle=3600,    # 연결 재사용 시간
   )
   ```

2. **연결 누수 확인**:
   - 모든 데이터베이스 세션이 제대로 닫히는지 확인
   - `async with` 컨텍스트 매니저 사용

#### 문제: "Migration failed"

**원인**: 스키마 변경 실패

**해결**:
1. **Railway 콘솔에서 직접 실행**:
   ```bash
   railway run python scripts/init_db.py
   ```

2. **Alembic 마이그레이션 사용** (권장):
   ```bash
   # 로컬
   alembic revision --autogenerate -m "Add new column"
   alembic upgrade head

   # Railway
   railway run alembic upgrade head
   ```

### 10.5 보안 문제

#### 문제: GitHub에 API 키를 실수로 커밋함

**긴급 대응**:
1. **API 키 즉시 폐기**:
   - Anthropic Console → API Keys → Revoke
   - 새 키 발급

2. **Git 히스토리에서 제거**:
   ```bash
   # BFG Repo-Cleaner 설치
   brew install bfg

   # API 키가 포함된 파일 제거
   bfg --delete-files .env

   # 히스토리 정리
   git reflog expire --expire=now --all
   git gc --prune=now --aggressive

   # 강제 푸시 (주의!)
   git push origin --force --all
   ```

3. **Secret Scanning 활성화**:
   - GitHub 저장소 → Settings → Security → Secret Scanning

#### 문제: CORS 에러

**원인**: 프론트엔드에서 API 호출 시 CORS 차단

**해결** (`src/api.py`):
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://yourdomain.com",  # 프로덕션 도메인만
        "http://localhost:3000",   # 로컬 개발용
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],  # 필요한 메소드만
    allow_headers=["*"],
)
```

### 10.6 Railway 관련 문제

#### 문제: "Service is sleeping"

**원인**: Railway Hobby Plan의 자동 슬립 기능

**해결**:
1. **Settings** → **Sleep Mode** → Disable
2. 또는 헬스 체크 핑거 설정:
   ```bash
   # 5분마다 깨우기 (외부 크론잡)
   curl https://your-app.up.railway.app/health
   ```

#### 문제: "Deployment quota exceeded"

**원인**: 무료 플랜 시간 초과 (월 500시간)

**해결**:
1. 플랜 업그레이드
2. 불필요한 서비스 중지
3. 슬립 모드 활성화

---

## 부록: 유용한 명령어 모음

### Git 명령어

```bash
# 현재 브랜치 확인
git branch

# 새 브랜치 생성 및 이동
git checkout -b feature/new-feature

# 변경사항 확인
git status

# 커밋 히스토리 확인
git log --oneline --graph

# 원격 저장소 동기화
git pull origin main
```

### Railway CLI 명령어

```bash
# 프로젝트 연결
railway link

# 로그 확인
railway logs --tail

# 환경 변수 보기
railway variables

# 환경 변수 설정
railway variables set KEY=value

# 명령어 실행
railway run python scripts/init_db.py

# 배포 상태 확인
railway status
```

### Docker 명령어

```bash
# 로컬 빌드 테스트
docker build -t auction-agent .

# 로컬 실행
docker run -p 8000:8000 --env-file .env auction-agent

# 컨테이너 로그 확인
docker logs <container-id>

# 컨테이너 내부 진입
docker exec -it <container-id> /bin/bash
```

### Python 명령어

```bash
# 의존성 설치
pip install -e ".[dev]"

# 테스트 실행
pytest tests/ -v

# 커버리지 확인
pytest --cov=src --cov-report=html

# 린팅
ruff check src/

# 타입 체킹
mypy src/
```

---

## 추가 리소스

### 공식 문서
- [Railway Docs](https://docs.railway.app/)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [LangGraph Docs](https://langchain-ai.github.io/langgraph/)
- [Anthropic API Docs](https://docs.anthropic.com/)

### 커뮤니티
- [Railway Discord](https://discord.gg/railway)
- [LangChain Discord](https://discord.gg/langchain)

### 튜토리얼
- [Railway 배포 가이드](https://docs.railway.app/guides/deployments)
- [FastAPI 프로덕션 가이드](https://fastapi.tiangolo.com/deployment/)

---

## 요약 체크리스트

배포 완료 전에 확인하세요:

### 배포 전
- [ ] GitHub 저장소 생성 (Private)
- [ ] `.gitignore`에 `.env` 포함
- [ ] 모든 API 키 발급 완료
- [ ] 로컬 테스트 통과 (`pytest`)

### Railway 설정
- [ ] Railway 프로젝트 생성
- [ ] PostgreSQL 서비스 추가
- [ ] Redis 서비스 추가
- [ ] 환경 변수 설정 완료
- [ ] 도메인 생성

### CI/CD
- [ ] GitHub Actions 워크플로우 추가
- [ ] GitHub Secrets 설정
- [ ] 브랜치 보호 규칙 활성화

### 배포 후
- [ ] 헬스 체크 통과
- [ ] API 엔드포인트 테스트
- [ ] 로그 확인
- [ ] 모니터링 대시보드 설정
- [ ] 알림 설정 (Sentry/Railway)

---

**축하합니다! 경매 AI 에이전트가 성공적으로 배포되었습니다.** 🎉

문제가 발생하면 [FAQ 섹션](#10-문제-해결-faq)을 참고하거나 GitHub Issues에 문의해주세요.
