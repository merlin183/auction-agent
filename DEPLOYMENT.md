# 배포 가이드

경매 AI 에이전트 시스템의 배포 및 운영 가이드입니다.

## 목차

1. [사전 준비](#사전-준비)
2. [Railway 배포](#railway-배포)
3. [Docker 배포](#docker-배포)
4. [환경 변수 설정](#환경-변수-설정)
5. [CI/CD 설정](#cicd-설정)
6. [모니터링](#모니터링)
7. [트러블슈팅](#트러블슈팅)

---

## 사전 준비

### 필수 요구사항

- Python 3.11 이상
- PostgreSQL 16 이상
- Redis 7 이상
- Git

### API 키 준비

다음 API 키를 미리 발급받으세요:

1. **Anthropic API Key** (필수)
   - https://console.anthropic.com
   - Claude 모델 사용

2. **OpenAI API Key** (선택)
   - https://platform.openai.com
   - GPT 모델 사용 시

3. **국토교통부 API Key** (선택)
   - https://www.data.go.kr
   - 부동산 데이터 조회용

4. **Kakao API Key** (선택)
   - https://developers.kakao.com
   - 지도/위치 정보 조회용

---

## Railway 배포

Railway는 가장 간단한 배포 방법입니다.

### 1. Railway 계정 준비

```bash
# Railway CLI 설치
npm install -g @railway/cli

# 로그인
railway login
```

### 2. 프로젝트 초기화

```bash
cd auction-agent

# Railway 프로젝트 연결 (신규 생성 또는 기존 연결)
railway init
```

### 3. 데이터베이스 추가

Railway 대시보드에서:

1. **PostgreSQL 추가**
   - "New" → "Database" → "Add PostgreSQL"
   - 자동으로 `DATABASE_URL` 환경 변수 생성됨

2. **Redis 추가**
   - "New" → "Database" → "Add Redis"
   - 자동으로 `REDIS_URL` 환경 변수 생성됨

### 4. 환경 변수 설정

Railway 대시보드의 "Variables" 탭에서 설정:

```bash
# 또는 CLI로 설정
railway variables set ANTHROPIC_API_KEY=sk-ant-...
railway variables set OPENAI_API_KEY=sk-...
railway variables set MOLIT_API_KEY=your-key
railway variables set KAKAO_API_KEY=your-key
railway variables set DEBUG=false
```

### 5. 배포 실행

```bash
# 수동 배포
railway up

# 또는 Git push로 자동 배포
git push railway main
```

### 6. 배포 확인

```bash
# 앱 URL 확인
railway open

# 로그 확인
railway logs

# 헬스 체크
curl https://your-app.railway.app/health
```

---

## Docker 배포

### 1. 로컬에서 빌드 및 테스트

```bash
# 이미지 빌드
docker build -t auction-agent:latest .

# 환경 변수 파일 준비
cp .env.example .env
# .env 파일을 편집하여 실제 값 입력

# 로컬에서 실행
docker run -d \
  --name auction-agent \
  --env-file .env \
  -p 8000:8000 \
  auction-agent:latest

# 헬스 체크
curl http://localhost:8000/health
```

### 2. Docker Compose (추천)

`docker-compose.yml` 파일을 생성:

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: auction
      POSTGRES_PASSWORD: your-password
      POSTGRES_DB: auction
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

실행:

```bash
docker-compose up -d

# 로그 확인
docker-compose logs -f app

# 중지
docker-compose down
```

### 3. 프로덕션 배포

```bash
# Docker Registry에 푸시 (예: Docker Hub)
docker tag auction-agent:latest yourusername/auction-agent:latest
docker push yourusername/auction-agent:latest

# 서버에서 실행
docker pull yourusername/auction-agent:latest
docker run -d \
  --name auction-agent \
  --env-file .env \
  -p 8000:8000 \
  --restart unless-stopped \
  yourusername/auction-agent:latest
```

---

## 환경 변수 설정

### 필수 환경 변수

```bash
# AI 모델 API 키
ANTHROPIC_API_KEY=sk-ant-...        # Claude API 키 (필수)

# 데이터베이스
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/auction
REDIS_URL=redis://host:6379

# 앱 설정
DEBUG=false                          # 프로덕션에서는 false
```

### 선택 환경 변수

```bash
# 추가 AI 모델
OPENAI_API_KEY=sk-...               # GPT 사용 시

# 외부 API
MOLIT_API_KEY=your-key              # 국토교통부 API
KAKAO_API_KEY=your-key              # Kakao 지도 API

# 성능 튜닝
WORKERS=2                            # Uvicorn 워커 수
PORT=8000                            # 포트 번호
```

### Railway에서 자동 설정되는 변수

- `DATABASE_URL` - PostgreSQL 플러그인 추가 시
- `REDIS_URL` - Redis 플러그인 추가 시
- `PORT` - Railway가 자동 할당
- `RAILWAY_ENVIRONMENT` - production/staging 등

---

## CI/CD 설정

### GitHub Actions 설정

이미 `.github/workflows/` 디렉토리에 워크플로우가 설정되어 있습니다.

#### 1. GitHub Secrets 설정

GitHub 저장소 Settings → Secrets and variables → Actions에서:

```
# 테스트용 (선택)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# Railway 자동 배포용 (선택)
RAILWAY_TOKEN=...
RAILWAY_SERVICE_ID=...
RAILWAY_APP_URL=https://your-app.railway.app

# Slack 알림용 (선택)
SLACK_WEBHOOK=https://hooks.slack.com/...
```

#### 2. Railway Token 발급

```bash
# CLI로 토큰 생성
railway tokens create

# 또는 대시보드에서
# Settings → Tokens → Create Token
```

#### 3. 워크플로우 활성화

```bash
# main 브랜치에 푸시하면 자동 실행
git push origin main

# PR 생성 시 자동 테스트
git checkout -b feature/something
git push origin feature/something
# GitHub에서 PR 생성
```

### 자동 배포 비활성화

자동 배포를 원하지 않으면:

```bash
# .github/workflows/deploy.yml 파일 삭제 또는 이름 변경
mv .github/workflows/deploy.yml .github/workflows/deploy.yml.disabled
```

---

## 모니터링

### 헬스 체크

```bash
# API 상태 확인
curl https://your-app.railway.app/health

# 예상 응답
{"status":"healthy"}
```

### 로그 확인

**Railway:**

```bash
railway logs
railway logs --tail 100
railway logs -f  # 실시간
```

**Docker:**

```bash
docker logs auction-agent
docker logs -f auction-agent  # 실시간
```

### 메트릭 모니터링

Railway 대시보드에서 자동으로 제공:
- CPU 사용률
- 메모리 사용량
- 네트워크 트래픽
- 응답 시간

### 커스텀 모니터링

애플리케이션 로그는 `structlog` 형식으로 출력됩니다:

```json
{
  "event": "Analysis completed",
  "case_number": "2024타경12345",
  "status": "SUCCESS",
  "reliability": 0.92,
  "timestamp": "2024-01-15T12:34:56Z"
}
```

---

## 트러블슈팅

### 빌드 실패

**증상:** Railway나 Docker 빌드가 실패

**해결책:**

1. **의존성 문제**
   ```bash
   # 로컬에서 재현
   pip install -e .

   # requirements.txt 생성 (필요시)
   pip freeze > requirements.txt
   ```

2. **Python 버전 불일치**
   ```bash
   # railway.toml 확인
   [build]
   builder = "nixpacks"

   # nixpacks.toml에서 Python 버전 명시
   [phases.setup]
   nixPkgs = ["python311"]
   ```

### 런타임 오류

**증상:** 배포는 성공했으나 앱이 시작되지 않음

**해결책:**

1. **로그 확인**
   ```bash
   railway logs
   ```

2. **환경 변수 확인**
   ```bash
   railway variables
   ```

3. **포트 바인딩 문제**
   - Railway는 `$PORT` 환경 변수를 자동 설정
   - `src/api.py`가 `$PORT`를 읽도록 설정됨

### 데이터베이스 연결 실패

**증상:** `Connection refused` 또는 `timeout` 오류

**해결책:**

1. **DATABASE_URL 형식 확인**
   ```bash
   # 올바른 형식
   postgresql+asyncpg://user:password@host:5432/dbname

   # Railway는 자동으로 올바른 형식 제공
   ```

2. **데이터베이스 준비 확인**
   ```bash
   # Railway에서 PostgreSQL이 실행 중인지 확인
   railway status
   ```

### API 키 오류

**증상:** `AuthenticationError` 또는 `Invalid API key`

**해결책:**

1. **환경 변수 확인**
   ```bash
   railway variables | grep API_KEY
   ```

2. **키 형식 확인**
   - Anthropic: `sk-ant-api03-...`
   - OpenAI: `sk-...`

3. **키 갱신**
   ```bash
   railway variables set ANTHROPIC_API_KEY=new-key
   railway restart
   ```

### 메모리 부족

**증상:** 앱이 자주 재시작되거나 `Out of Memory` 오류

**해결책:**

1. **Railway 플랜 업그레이드**
   - Free: 512MB RAM
   - Pro: 8GB+ RAM

2. **워커 수 조정**
   ```bash
   # railway.json 수정
   "startCommand": "uvicorn src.api:app --host 0.0.0.0 --port $PORT --workers 1"
   ```

3. **캐시 최적화**
   - Redis 캐시 설정 확인
   - 불필요한 데이터 메모리에 보관 안 함

### 느린 응답 시간

**증상:** API 응답이 30초 이상 걸림

**해결책:**

1. **타임아웃 설정 확인**
   ```python
   # config/settings.py
   request_timeout: int = 60  # 필요시 증가
   ```

2. **비동기 API 사용**
   ```bash
   # 동기 API 대신 비동기 API 사용
   POST /analyze/async
   GET /analyze/{analysis_id}
   ```

3. **캐시 활용**
   ```bash
   # 이미 분석된 케이스 조회
   GET /cases/{case_number}
   ```

---

## 프로덕션 체크리스트

배포 전 확인사항:

- [ ] 모든 환경 변수 설정 완료
- [ ] 데이터베이스 백업 설정
- [ ] 로그 모니터링 설정
- [ ] 헬스 체크 엔드포인트 작동 확인
- [ ] API 키 권한 확인 (읽기 전용 권장)
- [ ] CORS 설정 검토 (프로덕션 도메인만 허용)
- [ ] Rate limiting 설정
- [ ] 에러 추적 도구 연동 (Sentry 등)
- [ ] 백업 및 복구 계획 수립

---

## 추가 리소스

- [Railway 공식 문서](https://docs.railway.app)
- [FastAPI 배포 가이드](https://fastapi.tiangolo.com/deployment/)
- [Docker 공식 문서](https://docs.docker.com)
- [PostgreSQL 문서](https://www.postgresql.org/docs/)

---

## 지원

문제가 발생하면 GitHub Issues에 등록해주세요.
