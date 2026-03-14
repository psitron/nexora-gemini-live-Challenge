# Windows Desktop VNC Setup

## Prerequisites

### 1. Install TightVNC Server
- Download from: https://www.tightvnc.com/download.html
- Install "TightVNC Server" (you don't need the viewer)
- Set a VNC password during install
- It runs as a Windows service on port 5900

### 2. Install websockify (bridges VNC to WebSocket for noVNC)
```bash
pip install websockify
```

### 3. Download noVNC web client
```bash
git clone https://github.com/novnc/noVNC.git C:\noVNC
```

## Running

### Option A: Use the startup script
```bash
cd E:\ui-agent
vta\scripts\start_windows.bat
```

### Option B: Manual startup
```bash
# 1. Make sure TightVNC Server is running (check Services)

# 2. Start websockify proxy
python -m websockify 6080 localhost:5900 --web C:\noVNC

# 3. Start Agent S3
python -m uvicorn vta.agent_s3.server:app --host 0.0.0.0 --port 5001

# 4. Start Orchestrator
python -m uvicorn vta.orchestrator.main:app --host 0.0.0.0 --port 5000

# 5. Start Frontend
cd vta/frontend && npm run dev
```

## Access
- **Frontend UI**: http://localhost:5173
- **noVNC direct**: http://localhost:6080/vnc.html
- The noVNC panel in the frontend shows your Windows desktop
- ARIA controls your Windows desktop via pyautogui (mouse/keyboard)

## Notes
- TightVNC streams your actual Windows desktop - everything is visible
- pyautogui controls mouse/keyboard directly on Windows - no xdotool needed
- Screenshot capture uses mss library - works on Windows natively
- All other components (Sonic, Brain, vision loop) work unchanged
