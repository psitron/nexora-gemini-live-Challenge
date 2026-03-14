#!/usr/bin/env bash
# deploy_gcp.sh — Deploy VTA to Google Compute Engine
#
# Prerequisites:
#   - gcloud CLI authenticated: gcloud auth login
#   - Project set: gcloud config set project YOUR_PROJECT_ID
#   - GEMINI_API_KEY set in environment or passed as argument
#
# Usage:
#   ./deploy_gcp.sh [GEMINI_API_KEY]

set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
ZONE="${GCP_ZONE:-us-central1-a}"
INSTANCE_NAME="${GCP_INSTANCE_NAME:-vta-agent}"
MACHINE_TYPE="${GCP_MACHINE_TYPE:-e2-standard-4}"
IMAGE_FAMILY="ubuntu-2204-lts"
IMAGE_PROJECT="ubuntu-os-cloud"
GEMINI_API_KEY="${1:-${GEMINI_API_KEY:-}}"

if [ -z "$PROJECT_ID" ]; then
    echo "ERROR: No GCP project set. Run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

if [ -z "$GEMINI_API_KEY" ]; then
    echo "ERROR: GEMINI_API_KEY not set. Pass as argument or set in environment."
    exit 1
fi

echo "=== VTA GCE Deployment ==="
echo "  Project:  $PROJECT_ID"
echo "  Zone:     $ZONE"
echo "  Instance: $INSTANCE_NAME"
echo "  Machine:  $MACHINE_TYPE"
echo ""

# ── Create firewall rule (if not exists) ─────────────────────────────
if ! gcloud compute firewall-rules describe vta-allow-web --project="$PROJECT_ID" &>/dev/null; then
    echo "Creating firewall rule for ports 3000, 5000, 5001, 6080..."
    gcloud compute firewall-rules create vta-allow-web \
        --project="$PROJECT_ID" \
        --allow=tcp:3000,tcp:5000,tcp:5001,tcp:6080 \
        --source-ranges=0.0.0.0/0 \
        --target-tags=vta-server \
        --description="Allow VTA web traffic"
fi

# ── Create GCE instance ─────────────────────────────────────────────
echo "Creating GCE instance..."
gcloud compute instances create "$INSTANCE_NAME" \
    --project="$PROJECT_ID" \
    --zone="$ZONE" \
    --machine-type="$MACHINE_TYPE" \
    --image-family="$IMAGE_FAMILY" \
    --image-project="$IMAGE_PROJECT" \
    --boot-disk-size=50GB \
    --tags=vta-server \
    --metadata=startup-script='#!/bin/bash
set -e

# Wait for apt to be available
while fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1; do sleep 1; done

# Install system dependencies
apt-get update -y
apt-get install -y git python3-pip python3-venv nodejs npm \
    xvfb xfce4 x11vnc websockify nginx \
    tesseract-ocr scrot xdotool wmctrl \
    firefox

# Clone VTA repo
cd /opt
if [ ! -d vta ]; then
    git clone https://github.com/YOUR_REPO/ui-agent.git vta
fi
cd vta

# Setup Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r vta/requirements.txt

# Setup virtual display
export DISPLAY=:1
Xvfb :1 -screen 0 1280x800x24 &
sleep 2
startxfce4 &
sleep 3
x11vnc -display :1 -forever -nopw -shared &
websockify --web /usr/share/novnc 6080 localhost:5900 &

echo "VTA GCE instance setup complete"
'

echo ""
echo "Instance created. Waiting for it to start..."
sleep 10

# ── Get external IP ──────────────────────────────────────────────────
EXTERNAL_IP=$(gcloud compute instances describe "$INSTANCE_NAME" \
    --project="$PROJECT_ID" \
    --zone="$ZONE" \
    --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

echo ""
echo "=== Deployment Info ==="
echo "  External IP: $EXTERNAL_IP"
echo ""
echo "  Set GEMINI_API_KEY on the instance:"
echo "    gcloud compute ssh $INSTANCE_NAME --zone=$ZONE -- \"echo 'export GEMINI_API_KEY=$GEMINI_API_KEY' >> ~/.bashrc\""
echo ""
echo "  Start VTA services:"
echo "    gcloud compute ssh $INSTANCE_NAME --zone=$ZONE"
echo "    cd /opt/vta && source .venv/bin/activate"
echo "    export GEMINI_API_KEY='$GEMINI_API_KEY'"
echo "    export VTA_LOCAL_CURRICULUM=true VTA_LOCAL_STATE=true"
echo "    python -m uvicorn vta.agent_s3.server:app --host 0.0.0.0 --port 5001 &"
echo "    python -m uvicorn vta.orchestrator.main:app --host 0.0.0.0 --port 5000 &"
echo "    cd vta/frontend && npm install && npm run dev -- --host 0.0.0.0 &"
echo ""
echo "  Access:"
echo "    Frontend:  http://$EXTERNAL_IP:3000"
echo "    noVNC:     http://$EXTERNAL_IP:6080/vnc.html"
echo "    API:       http://$EXTERNAL_IP:5000/health"
echo ""
