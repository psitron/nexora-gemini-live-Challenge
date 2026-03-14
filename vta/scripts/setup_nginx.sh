#!/usr/bin/env bash
# setup_nginx.sh — Configure nginx as HTTPS reverse proxy for VTA
#
# Serves everything on port 443 (HTTPS):
#   /           → Vite frontend (port 3000)
#   /ws         → Orchestrator WebSocket (port 5000)
#   /api/       → Orchestrator API (port 5000)
#   /vnc/       → noVNC web client (port 6080)
#   /websockify → websockify WebSocket (port 6080)
#
# This eliminates mixed content issues — everything is HTTPS.

set -euo pipefail

EXTERNAL_IP=$(curl -s ifconfig.me)

echo "=== Setting up nginx HTTPS reverse proxy ==="
echo "  IP: $EXTERNAL_IP"

# Generate self-signed SSL cert
sudo mkdir -p /etc/ssl/vta
if [ ! -f /etc/ssl/vta/cert.pem ]; then
    sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /etc/ssl/vta/key.pem \
        -out /etc/ssl/vta/cert.pem \
        -subj "/CN=$EXTERNAL_IP"
    echo "SSL cert generated"
fi

# Write nginx config
sudo tee /etc/nginx/sites-available/vta > /dev/null <<'NGINX'
server {
    listen 443 ssl;
    server_name _;

    ssl_certificate /etc/ssl/vta/cert.pem;
    ssl_certificate_key /etc/ssl/vta/key.pem;

    # Frontend
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Orchestrator WebSocket
    location /ws {
        proxy_pass http://localhost:5000/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }

    # Orchestrator API
    location /api/ {
        proxy_pass http://localhost:5000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        client_max_body_size 50M;
    }

    # noVNC web client
    location /vnc/ {
        proxy_pass http://localhost:6080/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }

    # websockify WebSocket (VNC data)
    location /websockify {
        proxy_pass http://localhost:6080/websockify;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
        proxy_buffering off;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name _;
    return 301 https://$host$request_uri;
}
NGINX

# Enable site
sudo ln -sf /etc/nginx/sites-available/vta /etc/nginx/sites-enabled/vta
sudo rm -f /etc/nginx/sites-enabled/default

# Test and reload
sudo nginx -t
sudo systemctl reload nginx

echo ""
echo "=== nginx HTTPS proxy configured ==="
echo ""
echo "  App:     https://$EXTERNAL_IP"
echo "  Desktop: embedded in app (no separate tab needed)"
echo ""
echo "  Note: Browser will warn about self-signed cert."
echo "  Click Advanced → Proceed to continue."
echo ""
