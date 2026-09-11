@echo off
REM ============================================================
REM Vision 5D - Local Startup Script
REM Starts API + durable worker; opens the working dashboard.
REM ============================================================

setlocal enabledelayedexpansion

set "V5D_ROOT=%~dp0"
set "V5D_PYTHON=C:\Users\admin\AppData\Local\Programs\Python\Python311\python.exe"
set "V5D_PORT_API=8000"

REM Database path (forward slashes required for SQLAlchemy sqlite:/// URL)
set "V5D_DB_PATH=%V5D_ROOT%vision5d.db"
set "V5D_DB_PATH=%V5D_DB_PATH:\=/%"
set "V5D_DATABASE_URL=sqlite:///%V5D_DB_PATH%"
set "V5D_AUTO_CREATE_TABLES=true"

echo.
echo ============================================================
echo   Vision 5D - Local Application Startup
echo ============================================================
echo.
echo   Root:       %V5D_ROOT%
echo   Database:   %V5D_DATABASE_URL%
echo   Dashboard:  http://localhost:%V5D_PORT_API%/apps/web/index.html
echo.

REM -- 1. Verify Python environment --
echo [1/4] Verifying Python environment...
"%V5D_PYTHON%" -c "import fastapi, uvicorn, sqlalchemy; print('  Python deps OK')" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo   ERROR: Python dependencies missing. Run: pip install -e ".[dev]"
    pause
    exit /b 1
)

REM -- 2. Start API --
echo [2/4] Starting API on port %V5D_PORT_API%...
start "Vision5D-API" /MIN cmd /c "cd /d "%V5D_ROOT%" && "%V5D_PYTHON%" -m uvicorn apps.api.main:app --host 127.0.0.1 --port %V5D_PORT_API% --log-level info"
echo   API starting... (window: Vision5D-API)

REM -- 3. Wait for backend health --
echo [3/4] Waiting for backend...
:wait_loop
timeout /t 2 /nobreak >nul
curl -s http://localhost:%V5D_PORT_API%/health >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo   Still waiting...
    goto wait_loop
)
echo   Backend healthy: http://localhost:%V5D_PORT_API%/health

REM -- 4. Start durable worker + open dashboard --
echo [4/4] Starting durable worker + opening dashboard...
start "Vision5D-Worker" /MIN cmd /c "cd /d "%V5D_ROOT%" && "%V5D_PYTHON%" apps/worker/main.py"
start "" "http://localhost:%V5D_PORT_API%/apps/web/index.html"

echo.
echo ============================================================
echo   Vision 5D is running!
echo.
echo   Dashboard:  http://localhost:%V5D_PORT_API%/apps/web/index.html
echo   API:        http://localhost:%V5D_PORT_API%
echo   API Docs:   http://localhost:%V5D_PORT_API%/docs
echo   Health:     http://localhost:%V5D_PORT_API%/health
echo   Worker:     window "Vision5D-Worker"
echo ============================================================
echo.
echo   Press any key to stop all services...
pause >nul

REM -- Cleanup --
echo Stopping services...
taskkill /FI "WINDOWTITLE eq Vision5D-*" /F >nul 2>&1
echo Done.
