#!/usr/bin/env bash
# start_services.sh — Start all VTA services on GCE
#
# Prerequisites:
#   - gce_setup.sh has been run
#   - GEMINI_API_KEY is set in environment
#
# Usage:
#   export GEMINI_API_KEY='your-key'
#   bash vta/scripts/start_services.sh

set -euo pipefail

if [ -z "${GEMINI_API_KEY:-}" ]; then
    echo "ERROR: GEMINI_API_KEY not set."
    echo "  export GEMINI_API_KEY='your-key'"
    exit 1
fi

cd "$(dirname "$0")/../.."  # Navigate to repo root
REPO_ROOT=$(pwd)
source .venv/bin/activate

export DISPLAY=:1
export VTA_LOCAL_CURRICULUM=true
export VTA_LOCAL_STATE=true
export PYTHONPATH="$REPO_ROOT"

echo "=== Starting VTA Services ==="

# 1. Start desktop environment (if not running)
if ! pgrep -x "xfce4-session" > /dev/null; then
    echo "Starting XFCE desktop..."
    DISPLAY=:1 startxfce4 &
    sleep 3
fi

# 2. Start VNC server
if ! pgrep -x "x11vnc" > /dev/null; then
    echo "Starting VNC server..."
    x11vnc -display :1 -forever -nopw -shared -rfbport 5900 &
    sleep 1
fi

# 3. Start noVNC websockify
if ! pgrep -f "websockify.*6080" > /dev/null; then
    echo "Starting noVNC (websockify)..."
    websockify --web /usr/share/novnc 6080 localhost:5900 &
    sleep 1
fi

# 4. Start Agent S3 server
echo "Starting Agent S3 (port 5001)..."
python -m uvicorn vta.agent_s3.server:app --host 0.0.0.0 --port 5001 &
sleep 2

# 5. Start Orchestrator
echo "Starting Orchestrator (port 5000)..."
python -m uvicorn vta.orchestrator.main:app --host 0.0.0.0 --port 5000 &
sleep 2

# 6. Start Frontend
echo "Starting Frontend (port 3000)..."
cd vta/frontend
npx vite --host 0.0.0.0 --port 3000 &
cd "$REPO_ROOT"

echo ""
echo "=== All Services Running ==="
echo ""
echo "  Frontend:     http://$(curl -s ifconfig.me):3000"
echo "  noVNC:        http://$(curl -s ifconfig.me):6080/vnc.html"
echo "  Orchestrator: http://$(curl -s ifconfig.me):5000/health"
echo "  Agent S3:     http://$(curl -s ifconfig.me):5001/health"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for any background process to exit
wait
