#!/usr/bin/env bash
# deploy_gcp.sh — Create and configure a GCE instance for VTA
#
# Prerequisites:
#   - gcloud CLI installed and authenticated: gcloud auth login
#   - Project set: gcloud config set project YOUR_PROJECT_ID
#   - Billing enabled on the project
#
# Usage:
#   ./deploy_gcp.sh

set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
ZONE="${GCP_ZONE:-us-central1-a}"
INSTANCE_NAME="${GCP_INSTANCE_NAME:-vta-agent}"
MACHINE_TYPE="${GCP_MACHINE_TYPE:-e2-standard-4}"

if [ -z "$PROJECT_ID" ] || [ "$PROJECT_ID" = "(unset)" ]; then
    echo "ERROR: No GCP project set. Run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo "=== VTA GCE Deployment ==="
echo "  Project:  $PROJECT_ID"
echo "  Zone:     $ZONE"
echo "  Instance: $INSTANCE_NAME"
echo "  Machine:  $MACHINE_TYPE"
echo ""

# ── Create firewall rule ─────────────────────────────────────────────
if ! gcloud compute firewall-rules describe vta-allow-web --project="$PROJECT_ID" &>/dev/null; then
    echo "Creating firewall rule..."
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
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --boot-disk-size=50GB \
    --tags=vta-server

echo ""
echo "Instance created. Waiting 30s for boot..."
sleep 30

# ── Get external IP ──────────────────────────────────────────────────
EXTERNAL_IP=$(gcloud compute instances describe "$INSTANCE_NAME" \
    --project="$PROJECT_ID" \
    --zone="$ZONE" \
    --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

echo ""
echo "=== Instance Ready ==="
echo "  External IP: $EXTERNAL_IP"
echo ""
echo "=== Next Steps ==="
echo ""
echo "1. SSH into the instance:"
echo "   gcloud compute ssh $INSTANCE_NAME --zone=$ZONE"
echo ""
echo "2. Run the setup script on the instance:"
echo "   curl -sSL https://raw.githubusercontent.com/YOUR_REPO/ui-agent/feature-gemini-hackathon/vta/scripts/gce_setup.sh | bash"
echo ""
echo "   Or clone and run manually:"
echo "   git clone https://github.com/YOUR_REPO/ui-agent.git"
echo "   cd ui-agent"
echo "   bash vta/scripts/gce_setup.sh"
echo ""
echo "3. Set your Gemini API key:"
echo "   export GEMINI_API_KEY='your-key-here'"
echo ""
echo "4. Start all services:"
echo "   bash vta/scripts/start_services.sh"
echo ""
echo "5. Access:"
echo "   Frontend:  http://$EXTERNAL_IP:3000"
echo "   noVNC:     http://$EXTERNAL_IP:6080/vnc.html"
echo "   API:       http://$EXTERNAL_IP:5000/health"
echo ""
