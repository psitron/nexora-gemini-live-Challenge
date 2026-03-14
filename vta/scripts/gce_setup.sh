#!/usr/bin/env bash
# gce_setup.sh — One-time setup for VTA on a fresh Ubuntu 22.04 GCE instance
#
# Run this ONCE after creating the instance:
#   bash vta/scripts/gce_setup.sh
#
# Then start services with:
#   bash vta/scripts/start_services.sh

set -euo pipefail

echo "=== VTA GCE Setup ==="
echo "Installing system packages..."

# Wait for apt lock
while sudo fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1; do
    echo "Waiting for apt lock..."
    sleep 2
done

sudo apt-get update -y
sudo apt-get install -y \
    python3 python3-pip python3-venv \
    nodejs npm \
    xvfb xfce4 xfce4-terminal x11vnc websockify \
    tesseract-ocr scrot xdotool wmctrl \
    nginx git curl wget unzip

# Install Firefox
echo "Installing Firefox..."
sudo apt-get install -y firefox || {
    sudo snap install firefox 2>/dev/null || echo "Firefox install skipped"
}

# Install Chromium for Playwright
echo "Setting up Playwright dependencies..."
sudo apt-get install -y \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 \
    libcairo2 libasound2 libatspi2.0-0

echo ""
echo "Setting up Python environment..."

cd "$(dirname "$0")/../.."  # Navigate to repo root
REPO_ROOT=$(pwd)

python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r vta/requirements.txt

# Install Playwright browsers
playwright install chromium
playwright install-deps chromium 2>/dev/null || true

echo ""
echo "Setting up Node.js frontend..."

cd vta/frontend
npm install
npm run build 2>/dev/null || echo "Frontend build skipped (will use dev server)"
cd "$REPO_ROOT"

echo ""
echo "Setting up virtual display..."

# Create systemd service for Xvfb
sudo tee /etc/systemd/system/xvfb.service > /dev/null <<XVFB
[Unit]
Description=X Virtual Frame Buffer
After=network.target

[Service]
ExecStart=/usr/bin/Xvfb :1 -screen 0 1280x800x24
Restart=always

[Install]
WantedBy=multi-user.target
XVFB

sudo systemctl daemon-reload
sudo systemctl enable xvfb
sudo systemctl start xvfb

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "  1. Set your API key:  export GEMINI_API_KEY='your-key'"
echo "  2. Start services:    bash vta/scripts/start_services.sh"
echo ""
