#!/bin/bash
# VTA Deployment Script
# Uploads code, builds React frontend, restarts services
# Usage: bash deploy.sh [ec2-host] [key-file]
#   or run locally on EC2: bash deploy.sh --local

set -euo pipefail

if [ "${1:-}" = "--local" ]; then
    echo "===== Local Deployment on EC2 ====="

    cd /opt/vta

    # Build React frontend
    echo "[1/4] Building React frontend..."
    cd vta/frontend
    npm install
    npm run build
    cd /opt/vta

    # Seed curriculum (if tables exist)
    echo "[2/4] Seeding curriculum..."
    python3 -m vta.curriculum.seed_curriculum --file vta/curriculum/linux_basics.json || echo "  Skipping seed (tables may not exist)"

    # Restart services
    echo "[3/4] Restarting services..."
    for svc in vta-agent-s3 vta-orchestrator; do
        systemctl restart "$svc" 2>/dev/null || echo "  $svc not configured yet"
    done

    # Reload nginx
    echo "[4/4] Reloading nginx..."
    nginx -t && systemctl reload nginx

    echo ""
    echo "===== Deployment Complete ====="
    echo "Access: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo 'your-ec2-ip')"

else
    # Remote deployment via SSH
    EC2_HOST="${1:?Usage: deploy.sh <ec2-host> <key-file>}"
    KEY_FILE="${2:?Usage: deploy.sh <ec2-host> <key-file>}"

    echo "===== Deploying to $EC2_HOST ====="

    # Find project root (directory containing vta/)
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

    echo "[1/4] Uploading code..."
    rsync -avz --exclude='node_modules' --exclude='.git' --exclude='__pycache__' \
        --exclude='vta/frontend/dist' --exclude='.env' \
        -e "ssh -i $KEY_FILE" \
        "$PROJECT_ROOT/" "ubuntu@${EC2_HOST}:/opt/vta/"

    echo "[2/4] Running remote setup..."
    ssh -i "$KEY_FILE" "ubuntu@${EC2_HOST}" << 'REMOTE_EOF'
        cd /opt/vta

        # Build frontend
        echo "Building React frontend..."
        cd vta/frontend
        npm install
        npm run build
        cd /opt/vta

        # Seed curriculum
        echo "Seeding curriculum..."
        python3 -m vta.curriculum.seed_curriculum --file vta/curriculum/linux_basics.json 2>/dev/null || true

        # Restart services
        echo "Restarting services..."
        sudo systemctl restart vta-agent-s3 2>/dev/null || true
        sudo systemctl restart vta-orchestrator 2>/dev/null || true
        sudo nginx -t && sudo systemctl reload nginx 2>/dev/null || true

        echo "Deployment complete!"
REMOTE_EOF

    echo ""
    echo "===== Deployed to $EC2_HOST ====="
    echo "Access: http://$EC2_HOST"
fi
