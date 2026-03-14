#!/bin/bash
# VTA Local Test Script for Linux/WSL2
# Runs Agent S3 + Orchestrator + Frontend with real Xvfb

set -e

echo "============================================"
echo "VTA Local Test - Linux/WSL2"
echo "============================================"
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check dependencies
echo "[1/6] Checking dependencies..."
command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 not found"; exit 1; }
command -v node >/dev/null 2>&1 || { echo "ERROR: node not found"; exit 1; }
command -v Xvfb >/dev/null 2>&1 || { echo "ERROR: Xvfb not found. Run: sudo apt install xvfb"; exit 1; }

echo "[2/6] Setting up environment..."
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo "VTA_LOCAL_CURRICULUM=true" >> .env
    echo "VTA_LOCAL_STATE=true" >> .env
    echo "LOG_LEVEL=INFO" >> .env
    echo "DISPLAY=:1" >> .env
fi

echo "[3/6] Installing Python packages..."
pip3 show fastapi >/dev/null 2>&1 || {
    echo "Installing Python packages (may take 2-3 minutes)..."
    pip3 install -r requirements.txt
}

echo "[4/6] Installing frontend packages..."
if [ ! -d "frontend/node_modules" ]; then
    echo "Installing frontend packages (may take 1-2 minutes)..."
    cd frontend
    npm install
    cd ..
fi

echo "[5/6] Starting virtual display..."
# Kill existing Xvfb on :1
pkill -f "Xvfb :1" 2>/dev/null || true
sleep 1

# Start Xvfb in background
Xvfb :1 -screen 0 1280x800x24 >/dev/null 2>&1 &
XVFB_PID=$!
sleep 2

echo "[6/6] Starting services..."
echo ""

# Set environment
export DISPLAY=:1
export PYTHONPATH="$(dirname "$SCRIPT_DIR")"
export VTA_LOCAL_CURRICULUM=true
export VTA_LOCAL_STATE=true

# Start Agent S3 in background
echo "Starting Agent S3..."
python3 -m vta.agent_s3.server >/tmp/vta-agent-s3.log 2>&1 &
AGENT_PID=$!
sleep 3

# Start Orchestrator in background
echo "Starting Orchestrator..."
python3 -m vta.orchestrator.main >/tmp/vta-orchestrator.log 2>&1 &
ORCH_PID=$!
sleep 3

# Start Frontend in background
echo "Starting Frontend..."
cd frontend
npm run dev >/tmp/vta-frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

echo ""
echo "============================================"
echo "All services started!"
echo ""
echo "   Agent S3:     http://localhost:5001/health"
echo "   Orchestrator: http://localhost:5000/health"
echo "   Frontend:     http://localhost:3000"
echo ""
echo "Logs:"
echo "   Agent S3:     tail -f /tmp/vta-agent-s3.log"
echo "   Orchestrator: tail -f /tmp/vta-orchestrator.log"
echo "   Frontend:     tail -f /tmp/vta-frontend.log"
echo ""
echo "============================================"
echo ""
echo "Press Ctrl+C to stop all services..."
echo ""

# Cleanup function
cleanup() {
    echo ""
    echo "Stopping services..."
    kill $AGENT_PID 2>/dev/null || true
    kill $ORCH_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    kill $XVFB_PID 2>/dev/null || true
    echo "Done."
    exit 0
}

trap cleanup SIGINT SIGTERM

# Wait indefinitely
while true; do
    sleep 1
done
