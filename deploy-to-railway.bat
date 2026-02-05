@echo off
REM Railway 자동 배포 스크립트
REM 프로젝트: auction-agent
REM Service ID: 8c053802-c726-4e05-9684-59739a3ddedd

echo ======================================
echo Railway 자동 배포 시작
echo ======================================
echo.

REM 1. Railway 로그인 상태 확인
echo [1/6] Railway 로그인 확인...
railway whoami
if %errorlevel% neq 0 (
    echo.
    echo Railway 로그인이 필요합니다.
    echo 브라우저가 열리면 로그인해주세요.
    echo.
    railway login
    if %errorlevel% neq 0 (
        echo 로그인 실패. 스크립트를 종료합니다.
        pause
        exit /b 1
    )
)
echo ✓ 로그인 성공
echo.

REM 2. 프로젝트 연결
echo [2/6] 프로젝트 연결...
railway link dda13b19-c392-456a-9b93-4eb146228f3e
if %errorlevel% neq 0 (
    echo 프로젝트 연결 실패
    pause
    exit /b 1
)
echo ✓ 프로젝트 연결 성공
echo.

REM 3. 환경 변수 확인
echo [3/6] 환경 변수 확인...
railway variables
echo.
echo 필수 환경 변수 확인:
echo - ANTHROPIC_API_KEY (필수)
echo - DEBUG (권장: false)
echo - DATABASE_URL (자동 생성)
echo - REDIS_URL (자동 생성)
echo.
set /p CHECK_VARS="환경 변수가 설정되어 있습니까? (y/n): "
if /i "%CHECK_VARS%" neq "y" (
    echo.
    echo 환경 변수를 먼저 설정해주세요:
    echo railway variables set ANTHROPIC_API_KEY="your-key"
    echo railway variables set DEBUG="false"
    echo.
    pause
    exit /b 1
)
echo ✓ 환경 변수 확인 완료
echo.

REM 4. 데이터베이스 확인
echo [4/6] 데이터베이스 확인...
railway service
echo.
set /p CHECK_DB="PostgreSQL과 Redis가 추가되어 있습니까? (y/n): "
if /i "%CHECK_DB%" neq "y" (
    echo.
    echo 데이터베이스를 먼저 추가해주세요:
    echo railway add postgresql
    echo railway add redis
    echo.
    pause
    exit /b 1
)
echo ✓ 데이터베이스 확인 완료
echo.

REM 5. 배포 시작
echo [5/6] Railway에 배포 중...
echo 이 작업은 2-5분 정도 소요됩니다.
echo.
railway up
if %errorlevel% neq 0 (
    echo.
    echo 배포 실패. 로그를 확인해주세요:
    echo railway logs
    pause
    exit /b 1
)
echo ✓ 배포 성공
echo.

REM 6. 배포 상태 확인
echo [6/6] 배포 상태 확인...
railway status
echo.

echo ======================================
echo 배포 완료!
echo ======================================
echo.
echo 다음 단계:
echo 1. 앱 URL 확인: railway open
echo 2. 로그 확인: railway logs --follow
echo 3. 헬스 체크: curl https://your-app.railway.app/health
echo.
pause
