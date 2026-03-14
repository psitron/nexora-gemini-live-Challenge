#!/bin/bash
# Setup real desktop streaming for VTA
# Run this in WSL2 to see actual Linux desktop with browser, file explorer, etc.

set -e

echo "🖥️  Setting up real Linux desktop streaming..."

# 1. Install desktop environment and VNC tools
echo "📦 Installing XFCE desktop and VNC tools..."
sudo apt update
sudo apt install -y xfce4 xfce4-goodies x11vnc websockify xvfb

# 2. Start virtual display
echo "🖼️  Starting Xvfb on display :99..."
export DISPLAY=:99
Xvfb :99 -screen 0 1280x800x24 &
XVFB_PID=$!
sleep 2

# 3. Start XFCE desktop on the virtual display
echo "🎨 Starting XFCE desktop..."
DISPLAY=:99 startxfce4 &
sleep 3

# 4. Start x11vnc to serve the desktop
echo "🔌 Starting x11vnc on port 5900..."
x11vnc -display :99 -forever -shared -rfbport 5900 -nopw &
X11VNC_PID=$!
sleep 2

# 5. Start websockify to bridge VNC to WebSocket
echo "🌐 Starting websockify on port 6080..."
websockify --web=/usr/share/novnc 6080 localhost:5900 &
WEBSOCKIFY_PID=$!

echo ""
echo "✅ Desktop streaming is ready!"
echo ""
echo "📋 Running processes:"
echo "  - Xvfb on :99 (PID: $XVFB_PID)"
echo "  - x11vnc on port 5900 (PID: $X11VNC_PID)"
echo "  - websockify on port 6080 (PID: $WEBSOCKIFY_PID)"
echo ""
echo "🎯 Next steps:"
echo "  1. In another terminal, restart Agent S3 WITHOUT mock mode:"
echo "     cd /mnt/e/ui-agent/vta"
echo "     export DISPLAY=:99"
echo "     python -m vta.agent_s3.server"
echo ""
echo "  2. Keep Orchestrator running (it's fine as-is)"
echo ""
echo "  3. In browser, click 'Start Tutorial'"
echo ""
echo "  4. When T3 (practical task) starts, you'll see the real desktop"
echo "     with terminal opening in the right panel!"
echo ""
echo "⚠️  To stop all services later:"
echo "  kill $XVFB_PID $X11VNC_PID $WEBSOCKIFY_PID"
