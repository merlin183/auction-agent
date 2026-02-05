# 🚀 Railway 수동 설정 가이드 (3분)

Railway CLI의 브라우저 인증 때문에 자동화가 제한됩니다.
하지만 이 가이드를 따라하시면 3분 안에 배포가 완료됩니다!

---

## ⚡ 가장 빠른 방법: Railway Web UI에서 GitHub 연동

### 1단계: Railway 프로젝트 열기 (30초)

브라우저에서 다음 URL 열기:
```
https://railway.app/project/dda13b19-c392-456a-9b93-4eb146228f3e
```

### 2단계: 서비스 GitHub 연결 (1분)

1. 프로젝트 캔버스에서 **서비스** 클릭
2. **Settings** 탭 클릭
3. **Source** 섹션으로 스크롤
4. **Connect GitHub Repo** 버튼 클릭
5. `merlin183/auction-agent` 선택
6. **Connect** 버튼 클릭

**설정 확인**:
- ✅ Branch: `main`
- ✅ Root Directory: `/`
- ✅ Build Command: (자동 감지)
- ✅ Start Command: (railway.json 사용)

### 3단계: 환경 변수 설정 (1분)

같은 서비스 화면에서:
1. **Variables** 탭 클릭
2. **New Variable** 버튼 클릭

**필수 변수**:
| 변수명 | 값 |
|--------|-----|
| `ANTHROPIC_API_KEY` | `sk-ant-api03-your-actual-key` |
| `DEBUG` | `false` |

**선택 변수** (나중에 추가 가능):
| 변수명 | 값 |
|--------|-----|
| `MOLIT_API_KEY` | 국토교통부 API 키 |
| `KAKAO_API_KEY` | 카카오맵 API 키 |

### 4단계: 데이터베이스 추가 (30초)

프로젝트 캔버스에서:
1. **+ New** 버튼 클릭
2. **Database** → **PostgreSQL** 선택
3. 다시 **+ New** 버튼
4. **Database** → **Redis** 선택

**자동 생성**:
- ✅ `DATABASE_URL`
- ✅ `REDIS_URL`

### 5단계: 배포 트리거 (즉시)

GitHub 저장소에 이미 코드가 푸시되어 있으므로:
1. Railway가 자동으로 빌드 시작
2. **Deployments** 탭에서 진행 상황 확인
3. 2-3분 후 배포 완료!

---

## 🎯 배포 완료 확인

### 배포 URL 확인
Railway 서비스 화면 상단에 URL 표시:
```
https://auction-agent-production-xxxx.up.railway.app
```

### 헬스 체크
브라우저에서:
```
https://your-app-url/health
```

**예상 응답**:
```json
{"status":"healthy"}
```

### API 문서
```
https://your-app-url/docs
```

---

## 🔄 이후 배포는 자동!

GitHub 연동 완료 후:
```bash
# 코드 수정
git add .
git commit -m "Update feature"
git push origin main

# Railway가 자동으로 배포 시작! 🚀
```

---

## 🆘 문제 발생 시

### 빌드 실패
**Deployments** 탭 → 실패한 배포 클릭 → **View Logs**

**일반적인 문제**:
- 환경 변수 누락 → Variables 탭에서 추가
- 의존성 문제 → `requirements.txt` 확인
- Python 버전 → `runtime.txt`에 `python-3.11` 명시

### 503 Service Unavailable
- 앱 시작 시간 부족
- Settings → Deploy → Healthcheck Timeout: 300초

### DATABASE_URL 오류
- `src/services/database.py`에서 자동 변환 확인
- `postgres://` → `postgresql://`

---

## 💡 완료 체크리스트

배포 전:
- [ ] Railway 프로젝트 열기
- [ ] GitHub 저장소 연결
- [ ] `ANTHROPIC_API_KEY` 설정
- [ ] `DEBUG=false` 설정
- [ ] PostgreSQL 추가
- [ ] Redis 추가

배포 확인:
- [ ] Deployments 탭에서 "Deployed" 상태
- [ ] URL 접속 가능
- [ ] `/health` 엔드포인트 응답
- [ ] `/docs` Swagger UI 로드

---

## 🎉 완료!

이제 Railway에서 자동으로 관리됩니다:
- ✅ GitHub 푸시 시 자동 배포
- ✅ 실패 시 자동 재시작
- ✅ HTTPS 자동 적용
- ✅ 스케일링 자동 조정

**배포 시간**: 첫 배포 3분, 이후 자동 2-3분

---

## 📚 추가 참고

- [Railway Dashboard](https://railway.app/project/dda13b19-c392-456a-9b93-4eb146228f3e)
- [GitHub Repository](https://github.com/merlin183/auction-agent)
- [상세 가이드](./RAILWAY_DEPLOYMENT_STEPS.md)
