@echo off
REM Railway 초기 설정 스크립트
echo ======================================
echo Railway 초기 설정
echo ======================================
echo.

REM 1. Railway 로그인
echo [1/5] Railway 로그인...
railway login
if %errorlevel% neq 0 (
    echo 로그인 실패
    pause
    exit /b 1
)
echo ✓ 로그인 성공
echo.

REM 2. 프로젝트 연결
echo [2/5] 프로젝트 연결...
railway link dda13b19-c392-456a-9b93-4eb146228f3e
echo ✓ 연결 성공
echo.

REM 3. 환경 변수 설정
echo [3/5] 환경 변수 설정...
echo.
set /p ANTHROPIC_KEY="Anthropic API Key 입력 (sk-ant-...): "
if "%ANTHROPIC_KEY%"=="" (
    echo API 키가 입력되지 않았습니다.
    pause
    exit /b 1
)
railway variables set ANTHROPIC_API_KEY="%ANTHROPIC_KEY%"
railway variables set DEBUG="false"
echo ✓ 환경 변수 설정 완료
echo.

REM 4. PostgreSQL 추가
echo [4/5] PostgreSQL 추가...
railway add postgresql
if %errorlevel% neq 0 (
    echo PostgreSQL이 이미 존재하거나 추가 실패
)
echo ✓ PostgreSQL 확인
echo.

REM 5. Redis 추가
echo [5/5] Redis 추가...
railway add redis
if %errorlevel% neq 0 (
    echo Redis가 이미 존재하거나 추가 실패
)
echo ✓ Redis 확인
echo.

echo ======================================
echo 초기 설정 완료!
echo ======================================
echo.
echo 다음 명령어로 배포하세요:
echo deploy-to-railway.bat
echo.
echo 또는 수동으로:
echo railway up
echo.
pause
