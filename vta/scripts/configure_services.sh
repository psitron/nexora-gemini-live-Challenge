#!/bin/bash
# VTA systemd service configuration
# Sets up all background services: Xvfb, XFCE, x11vnc, websockify,
# Agent S3, Task Orchestrator
# Usage: sudo bash configure_services.sh

set -euo pipefail

echo "===== Configuring VTA Services ====="

# --- 1. Xvfb (Virtual Display) ---
cat > /etc/systemd/system/vta-xvfb.service << 'EOF'
[Unit]
Description=VTA Xvfb Virtual Display
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/Xvfb :1 -screen 0 1280x800x24
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# --- 2. XFCE Desktop ---
cat > /etc/systemd/system/vta-xfce.service << 'EOF'
[Unit]
Description=VTA XFCE Desktop
After=vta-xvfb.service
Requires=vta-xvfb.service

[Service]
Type=simple
Environment=DISPLAY=:1
Environment=DBUS_SESSION_BUS_ADDRESS=unix:path=/run/dbus/system_bus_socket
ExecStart=/usr/bin/startxfce4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# --- 3. x11vnc (VNC Server) ---
cat > /etc/systemd/system/vta-x11vnc.service << 'EOF'
[Unit]
Description=VTA x11vnc VNC Server
After=vta-xfce.service
Requires=vta-xvfb.service

[Service]
Type=simple
Environment=DISPLAY=:1
ExecStart=/usr/bin/x11vnc -display :1 -forever -nopw -rfbport 5900 -shared
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# --- 4. websockify (VNC → WebSocket bridge) ---
cat > /etc/systemd/system/vta-websockify.service << 'EOF'
[Unit]
Description=VTA websockify (VNC to WebSocket)
After=vta-x11vnc.service
Requires=vta-x11vnc.service

[Service]
Type=simple
ExecStart=/usr/bin/websockify --web /usr/share/novnc 6080 localhost:5900
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# --- 5. Agent S3 REST API ---
cat > /etc/systemd/system/vta-agent-s3.service << 'EOF'
[Unit]
Description=VTA Agent S3 REST API
After=vta-xfce.service
Requires=vta-xvfb.service

[Service]
Type=simple
WorkingDirectory=/opt/vta
Environment=DISPLAY=:1
Environment=PYTHONPATH=/opt/vta
Environment=AWS_DEFAULT_REGION=us-east-1
EnvironmentFile=-/opt/vta/.env
ExecStart=/usr/bin/python3 -m vta.agent_s3.server
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# --- 6. Task Orchestrator ---
cat > /etc/systemd/system/vta-orchestrator.service << 'EOF'
[Unit]
Description=VTA Task Orchestrator
After=vta-agent-s3.service
Requires=vta-agent-s3.service

[Service]
Type=simple
WorkingDirectory=/opt/vta
Environment=PYTHONPATH=/opt/vta
Environment=DISPLAY=:1
Environment=AWS_DEFAULT_REGION=us-east-1
EnvironmentFile=-/opt/vta/.env
ExecStart=/usr/bin/python3 -m vta.orchestrator.main
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# --- nginx configuration ---
cat > /etc/nginx/sites-available/vta << 'EOF'
server {
    listen 80;

    # React frontend (built static files)
    location / {
        root /opt/vta/vta/frontend/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # WebSocket: Orchestrator
    location /ws {
        proxy_pass http://localhost:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }

    # WebSocket: noVNC (desktop streaming)
    location /novnc {
        proxy_pass http://localhost:6080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }

    # Agent S3 health check
    location /agent-health {
        proxy_pass http://localhost:5001/health;
    }
}
EOF

# Enable nginx site
ln -sf /etc/nginx/sites-available/vta /etc/nginx/sites-enabled/vta
rm -f /etc/nginx/sites-enabled/default

# Reload systemd and enable services
systemctl daemon-reload

for svc in vta-xvfb vta-xfce vta-x11vnc vta-websockify vta-agent-s3 vta-orchestrator; do
    systemctl enable $svc
    echo "  Enabled: $svc"
done

systemctl enable nginx

echo ""
echo "===== Services Configured ====="
echo "Start all services with: sudo bash -c 'for s in vta-xvfb vta-xfce vta-x11vnc vta-websockify vta-agent-s3 vta-orchestrator nginx; do systemctl start \$s; done'"
echo "Check status with: systemctl status vta-*"
