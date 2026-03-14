@echo off
REM VTA Windows Desktop Startup Script
REM Starts Agent S3 + Orchestrator + Frontend on Windows
REM Prerequisites: Python 3.10+, Node.js 18+, TightVNC Server, websockify

echo ============================================
echo   VTA Windows Desktop Mode
echo ============================================

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.10+
    exit /b 1
)

REM Set environment
set VTA_PLATFORM=windows
if not defined AGENT_S3_PORT set AGENT_S3_PORT=5001
if not defined ORCHESTRATOR_PORT set ORCHESTRATOR_PORT=5000
if not defined VNC_PORT set VNC_PORT=5900
if not defined WEBSOCKIFY_PORT set WEBSOCKIFY_PORT=6080

echo.
echo Starting VNC websocket proxy (port %WEBSOCKIFY_PORT% -> %VNC_PORT%)...
start "websockify" cmd /c "python -m websockify %WEBSOCKIFY_PORT% localhost:%VNC_PORT% --web C:\noVNC"

echo.
echo Starting Agent S3 server (port %AGENT_S3_PORT%)...
start "Agent-S3" cmd /c "python -m uvicorn vta.agent_s3.server:app --host 0.0.0.0 --port %AGENT_S3_PORT%"

timeout /t 2 >nul

echo.
echo Starting Orchestrator (port %ORCHESTRATOR_PORT%)...
start "Orchestrator" cmd /c "python -m uvicorn vta.orchestrator.main:app --host 0.0.0.0 --port %ORCHESTRATOR_PORT%"

timeout /t 2 >nul

echo.
echo Starting Frontend...
start "Frontend" cmd /c "cd vta\frontend && npm run dev"

echo.
echo ============================================
echo   All services started!
echo   Frontend:     http://localhost:5173
echo   Orchestrator: http://localhost:%ORCHESTRATOR_PORT%
echo   Agent S3:     http://localhost:%AGENT_S3_PORT%
echo   noVNC:        http://localhost:%WEBSOCKIFY_PORT%/vnc.html
echo ============================================
echo.
echo Make sure TightVNC Server is running on port %VNC_PORT%
echo Press any key to stop all services...
pause >nul

REM Kill all started processes
taskkill /fi "WINDOWTITLE eq websockify*" /f >nul 2>&1
taskkill /fi "WINDOWTITLE eq Agent-S3*" /f >nul 2>&1
taskkill /fi "WINDOWTITLE eq Orchestrator*" /f >nul 2>&1
taskkill /fi "WINDOWTITLE eq Frontend*" /f >nul 2>&1
echo All services stopped.
