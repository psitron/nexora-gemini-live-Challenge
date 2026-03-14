#!/usr/bin/env bash
# vta.sh — Start/stop/restart all VTA services
#
# Usage:
#   bash vta/scripts/vta.sh start    # Start all services in background
#   bash vta/scripts/vta.sh stop     # Stop all services
#   bash vta/scripts/vta.sh restart  # Stop then start
#   bash vta/scripts/vta.sh status   # Show running services
#   bash vta/scripts/vta.sh logs     # Tail all logs

set -euo pipefail

REPO_DIR="${HOME}/ui-agent"
LOG_DIR="${REPO_DIR}/logs"
mkdir -p "$LOG_DIR"

start() {
    echo "=== Starting VTA Services ==="

    cd "$REPO_DIR"
    source .venv/bin/activate
    export NVM_DIR="$HOME/.nvm" && [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
    export VTA_LOCAL_CURRICULUM=true
    export VTA_LOCAL_STATE=true
    export PYTHONPATH="$REPO_DIR"
    export DISPLAY=:1
    # GEMINI_API_KEY is provided by the user via the frontend UI

    # Xvfb
    if ! pgrep -x "Xvfb" > /dev/null; then
        echo "Starting Xvfb..."
        sudo systemctl start xvfb 2>/dev/null || Xvfb :1 -screen 0 1280x800x24 &
        sleep 2
    fi

    # XFCE
    if ! pgrep -x "xfce4-session" > /dev/null; then
        echo "Starting XFCE..."
        DISPLAY=:1 startxfce4 &>/dev/null &
        sleep 2
    fi

    # VNC
    if ! pgrep -x "x11vnc" > /dev/null; then
        echo "Starting VNC..."
        x11vnc -display :1 -forever -nopw -shared -rfbport 5900 &>"$LOG_DIR/vnc.log" &
        sleep 1
    fi

    # noVNC
    if ! pgrep -f "websockify.*6080" > /dev/null; then
        echo "Starting noVNC..."
        websockify --web /usr/share/novnc 6080 localhost:5900 &>"$LOG_DIR/novnc.log" &
        sleep 1
    fi

    # Jupyter
    if ! pgrep -f "jupyter-notebook" > /dev/null; then
        echo "Starting Jupyter..."
        jupyter notebook --no-browser --ip=0.0.0.0 --port=8888 \
            --NotebookApp.token='' --NotebookApp.password='' \
            &>"$LOG_DIR/jupyter.log" &
        sleep 2
    fi

    # Agent S3
    if ! lsof -i:5001 -t > /dev/null 2>&1; then
        echo "Starting Agent S3 (port 5001)..."
        python -m uvicorn vta.agent_s3.server:app --host 0.0.0.0 --port 5001 \
            &>"$LOG_DIR/agent_s3.log" &
        sleep 2
    fi

    # Orchestrator
    if ! lsof -i:5000 -t > /dev/null 2>&1; then
        echo "Starting Orchestrator (port 5000)..."
        python -m uvicorn vta.orchestrator.main:app --host 0.0.0.0 --port 5000 \
            &>"$LOG_DIR/orchestrator.log" &
        sleep 2
    fi

    # Frontend
    if ! lsof -i:3000 -t > /dev/null 2>&1; then
        echo "Starting Frontend (port 3000)..."
        cd vta/frontend
        npx vite --host 0.0.0.0 --port 3000 &>"$LOG_DIR/frontend.log" &
        cd "$REPO_DIR"
        sleep 1
    fi

    # nginx
    sudo systemctl reload nginx 2>/dev/null || true

    IP=$(curl -s ifconfig.me 2>/dev/null || echo "localhost")
    echo ""
    echo "=== All Services Running ==="
    echo "  App:          https://$IP"
    echo "  noVNC:        http://$IP:6080/vnc.html"
    echo "  Orchestrator: http://$IP:5000/health"
    echo "  Agent S3:     http://$IP:5001/health"
    echo "  Jupyter:      http://$IP:8888"
    echo ""
    echo "  Logs: tail -f $LOG_DIR/*.log"
    echo "  Stop: bash vta/scripts/vta.sh stop"
}

stop() {
    echo "=== Stopping VTA Services ==="
    lsof -i:5000 -t 2>/dev/null | xargs -r kill 2>/dev/null && echo "  Orchestrator stopped"
    lsof -i:5001 -t 2>/dev/null | xargs -r kill 2>/dev/null && echo "  Agent S3 stopped"
    lsof -i:3000 -t 2>/dev/null | xargs -r kill 2>/dev/null && echo "  Frontend stopped"
    lsof -i:8888 -t 2>/dev/null | xargs -r kill 2>/dev/null && echo "  Jupyter stopped"
    echo "  Done (VNC/noVNC/Xvfb left running)"
}

status() {
    echo "=== VTA Service Status ==="
    echo -n "  Orchestrator (5000): "; lsof -i:5000 -t >/dev/null 2>&1 && echo "RUNNING" || echo "STOPPED"
    echo -n "  Agent S3     (5001): "; lsof -i:5001 -t >/dev/null 2>&1 && echo "RUNNING" || echo "STOPPED"
    echo -n "  Frontend     (3000): "; lsof -i:3000 -t >/dev/null 2>&1 && echo "RUNNING" || echo "STOPPED"
    echo -n "  Jupyter      (8888): "; lsof -i:8888 -t >/dev/null 2>&1 && echo "RUNNING" || echo "STOPPED"
    echo -n "  VNC          (5900): "; lsof -i:5900 -t >/dev/null 2>&1 && echo "RUNNING" || echo "STOPPED"
    echo -n "  noVNC        (6080): "; lsof -i:6080 -t >/dev/null 2>&1 && echo "RUNNING" || echo "STOPPED"
    echo -n "  Xvfb               : "; pgrep -x Xvfb >/dev/null 2>&1 && echo "RUNNING" || echo "STOPPED"
    echo -n "  nginx              : "; systemctl is-active nginx 2>/dev/null || echo "STOPPED"
}

logs() {
    tail -f "$LOG_DIR"/*.log
}

case "${1:-}" in
    start)   start ;;
    stop)    stop ;;
    restart) stop; sleep 2; start ;;
    status)  status ;;
    logs)    logs ;;
    *)
        echo "Usage: bash vta/scripts/vta.sh {start|stop|restart|status|logs}"
        exit 1
        ;;
esac
