# 🔗 Railway GitHub 연결 가이드 (스크린샷 기반)

**문제**: Settings에 "Source" 섹션이 없음
**원인**: 프로젝트 Settings를 보고 계심 (서비스 Settings가 아님)

---

## ✅ 해결 방법

### 방법 1: 새 서비스 생성 + GitHub 연결 (추천)

#### 1단계: 프로젝트 캔버스로 이동

현재 Settings 화면에서:
- 좌측 상단 **"victorious-grace"** 클릭
- 또는 브라우저 뒤로가기
- 또는 URL: https://railway.app/project/dda13b19-c392-456a-9b93-4eb146228f3e

#### 2단계: 새 서비스 생성

프로젝트 캔버스(메인 화면)에서:
1. **"+ New"** 버튼 클릭 (우측 상단 또는 중앙)
2. **"GitHub Repo"** 선택
3. GitHub 권한 승인 (처음만)
4. **"merlin183/auction-agent"** 저장소 선택
5. **Branch**: main 선택
6. **"Deploy"** 또는 **"Add"** 버튼 클릭

**완료!** Railway가 자동으로:
- 서비스 생성
- GitHub 연결
- 코드 빌드
- 배포 시작

---

### 방법 2: 기존 서비스에 연결

#### 캔버스에 이미 서비스(박스)가 있는 경우:

1. **서비스 박스** 클릭
2. **Settings 탭** 클릭
3. 왼쪽 메뉴 **"Source"** 섹션 클릭
4. **"Connect Repo"** 버튼 클릭
5. **"merlin183/auction-agent"** 선택
6. **"Connect"** 버튼

---

## 🎯 빠른 실행 (클릭 순서)

### 가장 빠른 방법:

```
1. 프로젝트 이름 클릭 (좌측 상단)
   ↓
2. "+ New" 버튼 클릭
   ↓
3. "GitHub Repo" 선택
   ↓
4. "merlin183/auction-agent" 선택
   ↓
5. "Deploy" 클릭
   ↓
완료! 🎉
```

---

## 📸 화면별 안내

### 현재 화면 (프로젝트 Settings)
- ❌ 여기에는 Source가 없음
- ✅ 뒤로가기하여 캔버스로 이동

### 올바른 화면 (서비스 Settings)
- ✅ Settings 탭 (서비스 내부)
- ✅ 왼쪽 메뉴에 "Source" 있음
- ✅ "Connect Repo" 버튼 있음

---

## 🔍 서비스 vs 프로젝트 구분

### 프로젝트 (현재 보고 계신 곳)
- 전체 프로젝트 설정
- Members, Tokens, Webhooks 등
- ❌ Source 연결 없음

### 서비스 (가야 할 곳)
- 개별 서비스 설정
- Source, Variables, Deployments 등
- ✅ GitHub 연결하는 곳

---

## 🆘 여전히 안 보이면

### 서비스가 아직 없는 경우:

Railway 프로젝트가 비어있을 수 있습니다.

**해결**:
1. 프로젝트 캔버스로 이동
2. "+ New" 버튼 클릭
3. "GitHub Repo" 직접 선택
4. 저장소 연결

이 방법이 가장 빠릅니다!

---

## 💡 Railway CLI 대안

Web UI가 복잡하다면 CLI 사용:

```bash
cd "C:\Users\user\Desktop\그리드라이프\개발\개발\auction-agent"

# Railway 로그인
railway login

# 프로젝트 연결
railway link dda13b19-c392-456a-9b93-4eb146228f3e

# GitHub 연결 (Web UI로 자동 이동)
railway service

# 환경 변수 설정
railway variables set ANTHROPIC_API_KEY="your-key"

# 배포
railway up
```

---

## ✅ 체크리스트

현재 위치 확인:
- [ ] URL에 `/settings/general`이 있음? → 프로젝트 Settings (❌)
- [ ] 캔버스에 박스(서비스)가 보임? → 서비스 클릭! (✅)
- [ ] "+ New" 버튼이 보임? → 새 서비스 생성! (✅)

---

## 🎉 성공 확인

GitHub 연결 성공하면:
- ✅ Deployments 탭에 빌드 진행 상황
- ✅ 2-3분 후 "Deployed" 상태
- ✅ 서비스 상단에 URL 표시

---

**다음 단계**:
1. 프로젝트 캔버스로 이동
2. "+ New" → "GitHub Repo" 클릭
3. "merlin183/auction-agent" 선택
4. 완료!

아직 어려우시면 스크린샷을 하나 더 찍어주세요:
- 프로젝트 캔버스 화면 (메인 화면)
- "+ New" 버튼이 보이는 화면
