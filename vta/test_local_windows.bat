@echo off
REM VTA Local Test Script for Windows
REM Runs Agent S3 + Orchestrator + Frontend in mock mode

echo ============================================
echo VTA Local Test - Windows Mock Mode
echo ============================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.11+ first.
    pause
    exit /b 1
)

REM Check Node
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js not found. Install Node.js 20+ first.
    pause
    exit /b 1
)

echo [1/5] Setting up environment...
cd /d "%~dp0"

REM Create .env if not exists
if not exist .env (
    echo Creating .env file...
    copy .env.example .env
    echo VTA_MOCK_DESKTOP=true >> .env
    echo VTA_LOCAL_CURRICULUM=true >> .env
    echo VTA_LOCAL_STATE=true >> .env
    echo LOG_LEVEL=INFO >> .env
)

echo [2/5] Checking Python packages...
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo Installing Python packages (this may take 2-3 minutes)...
    pip install -r requirements.txt
)

echo [3/5] Checking frontend packages...
if not exist frontend\node_modules (
    echo Installing frontend packages (this may take 1-2 minutes)...
    cd frontend
    call npm install
    cd ..
)

echo [4/5] Starting services...
echo.

REM Start Agent S3 in new window
echo Starting Agent S3 (Mock Mode)...
start "VTA Agent S3" cmd /k "set PYTHONPATH=%~dp0.. && set VTA_MOCK_DESKTOP=true && python -m vta.agent_s3.server"
timeout /t 3 /nobreak >nul

REM Start Orchestrator in new window
echo Starting Orchestrator...
start "VTA Orchestrator" cmd /k "set PYTHONPATH=%~dp0.. && set VTA_LOCAL_CURRICULUM=true && set VTA_LOCAL_STATE=true && python -m vta.orchestrator.main"
timeout /t 3 /nobreak >nul

REM Start Frontend in new window
echo Starting Frontend...
start "VTA Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo [5/5] All services starting...
echo.
echo ============================================
echo Wait 10 seconds for services to start, then:
echo.
echo   Open browser: http://localhost:3000
echo.
echo ============================================
echo.
echo NOTE: Running in MOCK MODE
echo - Desktop actions are simulated
echo - No voice (requires AWS credentials in .env)
echo - UI and workflow fully functional
echo.
echo Press any key to open browser...
pause >nul

start http://localhost:3000

echo.
echo To stop all services: Close the 3 CMD windows
echo.
pause
