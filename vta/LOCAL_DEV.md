# VTA Local Development Guide

Testing VTA locally on Windows or without full Linux setup.

---

## Quick Test (Windows - No Virtual Desktop)

### 1. Install Dependencies

```bash
# Install Python packages
pip install -r requirements.txt

# Install frontend packages
cd frontend
npm install
cd ..
```

### 2. Configure Local Mode

Create `.env` file:

```bash
cp .env.example .env
```

Edit `.env` with these settings:

```bash
# Use local files instead of DynamoDB
VTA_LOCAL_CURRICULUM=true
VTA_LOCAL_STATE=true

# Mock desktop mode (actions won't actually execute)
VTA_MOCK_DESKTOP=true

# Ports
AGENT_S3_PORT=5001
ORCHESTRATOR_PORT=5000

# AWS (only needed for Nova Sonic - optional for testing)
# AWS_DEFAULT_REGION=us-east-1
# AWS_ACCESS_KEY_ID=your-key
# AWS_SECRET_ACCESS_KEY=your-secret
```

### 3. Run Services (3 Terminals)

**Terminal 1 - Agent S3 (with mock mode):**

```bash
set PYTHONPATH=E:\ui-agent
set VTA_MOCK_DESKTOP=true
python -m vta.agent_s3.server
```

**Terminal 2 - Orchestrator:**

```bash
set PYTHONPATH=E:\ui-agent
set VTA_LOCAL_CURRICULUM=true
set VTA_LOCAL_STATE=true
python -m vta.orchestrator.main
```

**Terminal 3 - Frontend:**

```bash
cd frontend
npm run dev
```

### 4. Access

Open browser: `http://localhost:3000`

---

## What Works in Local Mode

✅ **Frontend UI** - Full interface
✅ **WebSocket** - Communication between components
✅ **Curriculum Loading** - From local JSON
✅ **Session State** - In-memory tracking
✅ **Task Progress** - UI updates
✅ **Confirmation Flow** - Yes/No/Repeat buttons

❌ **Virtual Desktop** - No Xvfb (shows blank screen)
❌ **Desktop Actions** - Mocked (returns success without doing anything)
❌ **Nova Sonic** - Needs AWS credentials (can test without voice)
❌ **Audio** - Needs Nova Sonic setup

---

## Testing Without Nova Sonic

You can test the full UI flow without voice:

1. **Start services** (all 3 terminals above)
2. **Open browser**: `http://localhost:3000`
3. **Click "Start Tutorial"**
4. Tasks will advance automatically (no voice)
5. Confirmation bar appears - click "Yes"
6. Desktop panel shows (but will be blank)

---

## Testing With Nova Sonic (Requires AWS)

### Setup AWS Credentials

1. Get AWS credentials with Bedrock access
2. Update `.env`:
   ```bash
   AWS_DEFAULT_REGION=us-east-1
   AWS_ACCESS_KEY_ID=your-key
   AWS_SECRET_ACCESS_KEY=your-secret
   ```
3. Restart orchestrator
4. Now you can:
   - Click mic button
   - Speak to Sonic
   - Hear audio responses
   - See transcript updates

---

## Full Linux Testing (WSL2 on Windows)

### Install WSL2

```powershell
# PowerShell (Admin)
wsl --install -d Ubuntu-22.04
```

### Setup in WSL2

```bash
# In WSL2 terminal
cd /mnt/e/ui-agent/vta

# Install system packages
sudo apt update
sudo apt install -y \
  xvfb xfce4 x11vnc xdotool \
  python3-pip python3-venv nodejs npm \
  tesseract-ocr

# Install Python deps
pip3 install -r requirements.txt

# Configure
cp .env.example .env
nano .env  # Set LOCAL_CURRICULUM=true, LOCAL_STATE=true
```

### Run in WSL2

```bash
# Terminal 1: Xvfb
Xvfb :1 -screen 0 1280x800x24 &

# Terminal 2: x11vnc (optional - to view desktop)
x11vnc -display :1 -forever -nopw &

# Terminal 3: Agent S3
export DISPLAY=:1
export PYTHONPATH=/mnt/e/ui-agent
python3 -m vta.agent_s3.server

# Terminal 4: Orchestrator
export PYTHONPATH=/mnt/e/ui-agent
python3 -m vta.orchestrator.main

# Terminal 5: Frontend (can run in Windows PowerShell)
cd frontend
npm run dev
```

### Access

- **Frontend**: `http://localhost:3000`
- **Desktop (VNC)**: Use TigerVNC or TightVNC viewer → `localhost:5900`

---

## Troubleshooting Local Dev

### "Module not found" error

```bash
# Windows CMD
set PYTHONPATH=E:\ui-agent
python -m vta.agent_s3.server

# Windows PowerShell
$env:PYTHONPATH="E:\ui-agent"
python -m vta.agent_s3.server

# WSL2
export PYTHONPATH=/mnt/e/ui-agent
python3 -m vta.agent_s3.server
```

### "Port already in use"

```bash
# Windows: Find and kill process
netstat -ano | findstr :5001
taskkill /PID <pid> /F

# WSL2
sudo netstat -tulpn | grep 5001
kill <pid>
```

### Frontend can't connect

Check `frontend/vite.config.js` proxy settings:

```javascript
proxy: {
  '/ws': {
    target: 'http://localhost:5000',
    ws: true,
  },
}
```

### "aws_sdk_bedrock_runtime not found"

```bash
# This package may not install via pip on Windows
# Either:
# 1. Use WSL2, or
# 2. Comment out Nova Sonic imports for testing without voice
```

---

## Quick Test Script (Windows)

Save as `test_local.bat`:

```batch
@echo off
echo Starting VTA Local Test...

start cmd /k "cd /d %~dp0 && set PYTHONPATH=E:\ui-agent && set VTA_MOCK_DESKTOP=true && python -m vta.agent_s3.server"
timeout /t 3

start cmd /k "cd /d %~dp0 && set PYTHONPATH=E:\ui-agent && set VTA_LOCAL_CURRICULUM=true && set VTA_LOCAL_STATE=true && python -m vta.orchestrator.main"
timeout /t 3

start cmd /k "cd /d %~dp0frontend && npm run dev"

echo All services starting...
echo Wait 10 seconds, then open http://localhost:3000
pause
```

Run: `test_local.bat`

---

## What to Test Locally

- [ ] Frontend loads at `localhost:3000`
- [ ] Connection status shows "Connected"
- [ ] Click "Start Tutorial" - tasks appear
- [ ] Task progress updates
- [ ] Confirmation bar appears (click Yes)
- [ ] Slide viewer shows (may be blank without PDF)
- [ ] Desktop panel toggles (blank in mock mode)
- [ ] Mic button works (if AWS configured)

---

## Moving to Production

Once local testing works:

1. Deploy to EC2 (follow `DEPLOYMENT_GUIDE.md`)
2. Virtual desktop will work on EC2 Linux
3. Desktop actions will execute for real
4. Nova Sonic will have full bidirectional audio

---

**Local testing complete when frontend loads and you can navigate the UI!**
