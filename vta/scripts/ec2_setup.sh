#!/bin/bash
# VTA EC2 Setup Script
# Run on a fresh Ubuntu 22.04 EC2 instance
# Usage: sudo bash ec2_setup.sh

set -euo pipefail

echo "===== VTA EC2 Setup ====="

# System update
echo "[1/8] Updating system packages..."
apt update && apt upgrade -y

# Desktop environment + virtual display
echo "[2/8] Installing Xvfb, XFCE, VNC..."
apt install -y \
  xvfb xfce4 xfce4-terminal x11vnc xdotool \
  dbus-x11 at-spi2-core \
  fonts-dejavu fonts-liberation

# Install websockify and noVNC
echo "[3/8] Installing noVNC and websockify..."
apt install -y novnc websockify

# Python
echo "[4/8] Installing Python and pip..."
apt install -y python3 python3-pip python3-venv python3-dev

# OCR
echo "[5/8] Installing Tesseract OCR..."
apt install -y tesseract-ocr libtesseract-dev

# Node.js for React build
echo "[6/8] Installing Node.js..."
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs

# nginx
echo "[7/8] Installing nginx..."
apt install -y nginx

# Python dependencies
echo "[8/8] Installing Python packages..."
pip3 install --break-system-packages \
  fastapi uvicorn[standard] websockets httpx boto3 python-dotenv \
  pyautogui pillow pytesseract mss pynput python-xlib \
  aws-sdk-bedrock-runtime smithy-aws-core

# Create VTA directory
mkdir -p /opt/vta

echo ""
echo "===== EC2 Setup Complete ====="
echo "Next steps:"
echo "  1. Run configure_services.sh to set up systemd services"
echo "  2. Run create_tables.sh to create DynamoDB tables"
echo "  3. Run deploy.sh to deploy VTA code"
