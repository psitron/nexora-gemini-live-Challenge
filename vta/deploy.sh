#!/usr/bin/env bash
# deploy.sh — One-command deployment for Nexora AI on Google Compute Engine
#
# Deploys the entire VTA (Virtual Trainer Agent) application on a fresh
# Ubuntu 22.04 GCE instance. Installs all dependencies, configures the
# virtual desktop, sets up nginx reverse proxy with SSL, and starts all services.
#
# Usage:
#   chmod +x deploy.sh
#   ./deploy.sh
#
# Prerequisites:
#   - Fresh Ubuntu 22.04 LTS GCE instance (e2-standard-4 recommended)
#   - Project cloned to /home/$USER/ui-agent
#   - Firewall rules allowing ports 80, 443
#
# After deployment, access:
#   https://<EXTERNAL_IP>  (Nexora AI frontend)

set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────
REPO_DIR="${HOME}/ui-agent"
VTA_DIR="${REPO_DIR}/vta"
LOG_DIR="${REPO_DIR}/logs"
VENV_DIR="${REPO_DIR}/.venv"

echo ""
echo "================================================================"
echo "  Nexora AI — Automated GCE Deployment"
echo "  Gemini Live Agent Challenge 2026"
echo "================================================================"
echo ""

# ── Step 1: System Packages ─────────────────────────────────────────
echo "[1/8] Installing system packages..."

# Wait for apt lock (common on fresh GCE instances)
while sudo fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1; do
    echo "  Waiting for apt lock..."
    sleep 2
done

sudo apt-get update -y
sudo apt-get install -y \
    python3 python3-pip python3-venv \
    nodejs npm \
    xvfb xfce4 xfce4-terminal x11vnc websockify mousepad \
    tesseract-ocr scrot xdotool wmctrl \
    nginx git curl wget unzip \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 \
    libcairo2 libasound2 libatspi2.0-0

# Install Firefox
echo "  Installing Firefox..."
sudo apt-get install -y firefox 2>/dev/null || {
    sudo snap install firefox 2>/dev/null || echo "  Firefox install skipped"
}

echo "  System packages installed."

# ── Step 2: Python Environment ──────────────────────────────────────
echo "[2/8] Setting up Python environment..."

cd "$REPO_DIR"

if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"

pip install --upgrade pip -q
pip install -r "$VTA_DIR/requirements.txt" -q

# Install Playwright browsers
playwright install chromium
playwright install-deps chromium 2>/dev/null || true

echo "  Python environment ready."

# ── Step 3: Frontend ────────────────────────────────────────────────
echo "[3/8] Building frontend..."

cd "$VTA_DIR/frontend"
npm install --silent 2>/dev/null
npm run build 2>/dev/null || echo "  Build skipped (will use dev server)"
cd "$REPO_DIR"

echo "  Frontend ready."

# ── Step 4: Virtual Display ─────────────────────────────────────────
echo "[4/8] Configuring virtual display..."

# Create systemd service for Xvfb
sudo tee /etc/systemd/system/xvfb.service > /dev/null <<XVFB
[Unit]
Description=X Virtual Frame Buffer
After=network.target

[Service]
ExecStart=/usr/bin/Xvfb :1 -screen 0 1440x900x24
Restart=always

[Install]
WantedBy=multi-user.target
XVFB

sudo systemctl daemon-reload
sudo systemctl enable xvfb
sudo systemctl start xvfb

echo "  Virtual display configured (1440x900)."

# ── Step 5: Polkit & Desktop Fixes ──────────────────────────────────
echo "[5/8] Applying desktop fixes..."

# Suppress polkit "Authentication needed for color management" popup
sudo mkdir -p /etc/polkit-1/localauthority/50-local.d
sudo tee /etc/polkit-1/localauthority/50-local.d/45-allow-colord.pkla > /dev/null <<POLKIT
[Allow Colord all Users]
Identity=unix-user:*
Action=org.freedesktop.color-manager.create-device;org.freedesktop.color-manager.create-profile;org.freedesktop.color-manager.delete-device;org.freedesktop.color-manager.delete-profile;org.freedesktop.color-manager.modify-device;org.freedesktop.color-manager.modify-profile
ResultAny=no
ResultInactive=no
ResultActive=yes
POLKIT

sudo systemctl restart polkit 2>/dev/null || true

# Disable XFCE session restore
DISPLAY=:1 xfconf-query -c xfce4-session -p /general/SaveOnExit -n -t bool -s false 2>/dev/null || true
DISPLAY=:1 xfconf-query -c xfce4-session -p /general/AutoSave -n -t bool -s false 2>/dev/null || true

echo "  Desktop fixes applied."

# ── Step 6: Nginx Reverse Proxy with SSL ────────────────────────────
echo "[6/8] Configuring nginx with HTTPS..."

# Get external IP
EXTERNAL_IP=$(curl -s -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip 2>/dev/null || curl -s ifconfig.me)

# Generate self-signed SSL certificate
sudo mkdir -p /etc/ssl/vta
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/vta/key.pem \
    -out /etc/ssl/vta/cert.pem \
    -subj "/CN=$EXTERNAL_IP" 2>/dev/null

# Create nginx configuration
sudo tee /etc/nginx/sites-available/vta > /dev/null <<NGINX
server {
    listen 443 ssl;
    server_name $EXTERNAL_IP;

    ssl_certificate /etc/ssl/vta/cert.pem;
    ssl_certificate_key /etc/ssl/vta/key.pem;

    client_max_body_size 50M;

    # Frontend (React via Vite dev server)
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }

    # Orchestrator WebSocket
    location /ws {
        proxy_pass http://localhost:5000/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_read_timeout 86400;
    }

    # Orchestrator REST API
    location /api/ {
        proxy_pass http://localhost:5000/api/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        client_max_body_size 50M;
    }

    # noVNC web client
    location /vnc/ {
        proxy_pass http://localhost:6080/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # VNC WebSocket
    location /websockify {
        proxy_pass http://localhost:6080/websockify;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }
}

server {
    listen 80;
    server_name $EXTERNAL_IP;
    return 301 https://\$host\$request_uri;
}
NGINX

sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -sf /etc/nginx/sites-available/vta /etc/nginx/sites-enabled/vta
sudo nginx -t && sudo systemctl reload nginx

echo "  Nginx configured with HTTPS (self-signed cert)."

# ── Step 7: Create log directory ────────────────────────────────────
echo "[7/8] Setting up logging..."
mkdir -p "$LOG_DIR"
echo "  Log directory: $LOG_DIR"

# ── Step 8: Start all services ──────────────────────────────────────
echo "[8/8] Starting all services..."

cd "$REPO_DIR"
source "$VENV_DIR/bin/activate"
export NVM_DIR="$HOME/.nvm" && [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
export VTA_LOCAL_CURRICULUM=true
export VTA_LOCAL_STATE=true
export PYTHONPATH="$REPO_DIR"
export DISPLAY=:1

# Start XFCE desktop
if ! pgrep -x "xfce4-session" > /dev/null; then
    DISPLAY=:1 startxfce4 &>/dev/null &
    sleep 2
fi

# Start VNC server
if ! pgrep -x "x11vnc" > /dev/null; then
    x11vnc -display :1 -forever -nopw -shared -rfbport 5900 &>"$LOG_DIR/vnc.log" &
    sleep 1
fi

# Start noVNC websockify
if ! pgrep -f "websockify.*6080" > /dev/null; then
    websockify --web /usr/share/novnc 6080 localhost:5900 &>"$LOG_DIR/novnc.log" &
    sleep 1
fi

# Start Jupyter Notebook
if ! pgrep -f "jupyter-notebook" > /dev/null; then
    jupyter notebook --no-browser --ip=0.0.0.0 --port=8888 \
        --NotebookApp.token='' --NotebookApp.password='' \
        &>"$LOG_DIR/jupyter.log" &
    sleep 2
fi

# Start Agent S3
if ! lsof -i:5001 -t > /dev/null 2>&1; then
    python -m uvicorn vta.agent_s3.server:app --host 0.0.0.0 --port 5001 \
        &>"$LOG_DIR/agent_s3.log" &
    sleep 2
fi

# Start Orchestrator
if ! lsof -i:5000 -t > /dev/null 2>&1; then
    python -m uvicorn vta.orchestrator.main:app --host 0.0.0.0 --port 5000 \
        &>"$LOG_DIR/orchestrator.log" &
    sleep 2
fi

# Start Frontend
if ! lsof -i:3000 -t > /dev/null 2>&1; then
    cd "$VTA_DIR/frontend"
    npx vite --host 0.0.0.0 --port 3000 &>"$LOG_DIR/frontend.log" &
    cd "$REPO_DIR"
    sleep 1
fi

# Reload nginx
sudo systemctl reload nginx 2>/dev/null || true

echo ""
echo "================================================================"
echo "  Nexora AI — Deployment Complete!"
echo "================================================================"
echo ""
echo "  Application:   https://$EXTERNAL_IP"
echo "  Desktop (VNC): http://$EXTERNAL_IP:6080/vnc.html"
echo "  Orchestrator:  http://$EXTERNAL_IP:5000/health"
echo "  Agent S3:      http://$EXTERNAL_IP:5001/health"
echo ""
echo "  Manage services:"
echo "    bash vta/scripts/vta.sh start|stop|restart|status|logs"
echo ""
echo "  Note: Enter your Gemini API key in the Configuration panel"
echo "  (gear icon) before starting a course."
echo ""
echo "================================================================"
