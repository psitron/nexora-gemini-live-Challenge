# Real Desktop Local Testing Guide

Complete guide to test VTA with **real Linux desktop UI** on your Windows machine using WSL2.

**Use this when you need:**
- Real terminal opening and commands executing
- Visual desktop streaming (not mock mode)
- Testing automation actions before EC2 deployment
- Seeing mouse cursor, windows, file explorer in real-time

---

## Prerequisites

- Windows 10/11 with WSL2 support
- At least 8GB RAM (16GB recommended)
- Admin access to install WSL2

---

## Part 1: Install WSL2 (5 minutes)

### Step 1.1: Enable WSL2

**Open PowerShell as Administrator** and run:

```powershell
wsl --install -d Ubuntu-22.04
```

**If already installed:**
```powershell
# Check WSL version
wsl --list --verbose

# Ensure Ubuntu is WSL2 (not WSL1)
wsl --set-version Ubuntu-22.04 2
```

### Step 1.2: Launch Ubuntu

1. Search for "Ubuntu" in Windows Start menu
2. Click to launch
3. First launch will take 2-3 minutes to set up
4. Create username and password when prompted

### Step 1.3: Verify Installation

In Ubuntu terminal:
```bash
# Check you're in Ubuntu
uname -a
# Should show: Linux ... x86_64 GNU/Linux

# Check you can access Windows files
ls /mnt/e/ui-agent
# Should show your project files
```

---

## Part 2: Install System Dependencies (10 minutes)

### Step 2.1: Update Ubuntu Packages

In WSL2 Ubuntu terminal:

```bash
sudo apt update
sudo apt upgrade -y
```

### Step 2.2: Install Desktop Environment and VNC Tools

```bash
sudo apt install -y \
  xfce4 \
  xfce4-goodies \
  x11vnc \
  websockify \
  xvfb \
  xdotool
```

**What each package does:**
- `xfce4` - Lightweight desktop environment
- `x11vnc` - VNC server to stream the desktop
- `websockify` - Bridges VNC to WebSocket for browser
- `xvfb` - Virtual framebuffer (headless X server)
- `xdotool` - Automates keyboard/mouse actions

### Step 2.3: Install Python and Node.js

```bash
# Install Python 3.11
sudo apt install -y python3 python3-pip python3-venv

# Install Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Verify installations
python3 --version  # Should be 3.10 or higher
node --version     # Should be v20.x
npm --version      # Should be 10.x
```

### Step 2.4: Install Tesseract OCR

```bash
sudo apt install -y tesseract-ocr libtesseract-dev
```

### Step 2.5: Install Python Dependencies

```bash
cd /mnt/e/ui-agent/vta

# Install VTA Python packages
pip3 install -r requirements.txt --user

# Verify key packages are installed
pip3 list | grep -E "fastapi|boto3|pyautogui|python-xlib|Pillow"
```

**Expected output:**
```
boto3               1.35.0
fastapi             0.115.0
Pillow              10.4.0
pyautogui           0.9.54
python-xlib         0.33
```

**If packages are missing:**
```bash
# Install missing packages individually
pip3 install --user pyautogui python-xlib Pillow pytesseract pynput mss

# Verify again
pip3 list | grep -E "pyautogui|python-xlib|Pillow"
```

---

## Part 3: Configure Environment (5 minutes)

### Step 3.1: Create .env File

```bash
cd /mnt/e/ui-agent/vta

# Copy template
cp .env.example .env

# Edit with nano
nano .env
```

### Step 3.2: Configure .env for Local Testing

**Required settings:**

```bash
# Display configuration
DISPLAY=:99
VTA_DISPLAY_WIDTH=1280
VTA_DISPLAY_HEIGHT=800

# Local mode (use JSON files, not DynamoDB)
VTA_LOCAL_CURRICULUM=true
VTA_LOCAL_STATE=true

# Service ports
AGENT_S3_PORT=5001
ORCHESTRATOR_PORT=5000

# Log level
LOG_LEVEL=INFO

# IMPORTANT: Do NOT set VTA_MOCK_DESKTOP
# Leave it unset or commented out for real desktop mode
```

**Optional (for Nova Sonic voice testing):**

```bash
# AWS configuration (only if testing voice features)
AWS_DEFAULT_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-key-here
AWS_SECRET_ACCESS_KEY=your-secret-here
```

**Save and exit:**
- Press `Ctrl+O` (save)
- Press `Enter` (confirm)
- Press `Ctrl+X` (exit)

---

## Part 4: Start Real Desktop Environment (5 minutes)

### Step 4.1: Run Desktop Setup Script

In WSL2 terminal:

```bash
cd /mnt/e/ui-agent/vta

# Make script executable
chmod +x setup_real_desktop.sh

# Run setup
./setup_real_desktop.sh
```

**Expected output:**
```
🖥️  Setting up real Linux desktop streaming...
📦 Installing XFCE desktop and VNC tools...
🖼️  Starting Xvfb on display :99...
🎨 Starting XFCE desktop...
🔌 Starting x11vnc on port 5900...
🌐 Starting websockify on port 6080...

✅ Desktop streaming is ready!

📋 Running processes:
  - Xvfb on :99 (PID: 1234)
  - x11vnc on port 5900 (PID: 1235)
  - websockify on port 6080 (PID: 1236)
```

### Step 4.2: Verify Desktop Services

```bash
# Check Xvfb is running
ps aux | grep Xvfb
# Should show: Xvfb :99 -screen 0 1280x800x24

# Check x11vnc is running
ps aux | grep x11vnc
# Should show: x11vnc -display :99 -forever

# Check websockify is running
ps aux | grep websockify
# Should show: websockify --web=/usr/share/novnc 6080 localhost:5900

# Check display is accessible
export DISPLAY=:99
xdpyinfo | head -5
# Should show display information
```

---

## Part 5: Start VTA Services (5 minutes)

You need **3 separate terminals**. Keep the desktop setup terminal running.

### Terminal 1: Agent S3 (in WSL2)

```bash
cd /mnt/e/ui-agent/vta

# Set environment variables
export DISPLAY=:99
export PYTHONPATH=/mnt/e/ui-agent

# Start Agent S3 (NO mock mode)
python3 -m vta.agent_s3.server
```

**Expected output:**
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:5001
```

### Terminal 2: Orchestrator (in WSL2)

Open new WSL2 terminal:

```bash
cd /mnt/e/ui-agent/vta

# Set environment variables
export PYTHONPATH=/mnt/e/ui-agent

# Start Orchestrator
python3 -m vta.orchestrator.main
```

**Expected output:**
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:5000
```

### Terminal 3: Frontend (in Windows PowerShell or WSL2)

**Option A - Windows PowerShell:**
```powershell
cd E:\ui-agent\vta\frontend

# Install packages (first time only)
npm install

# Start dev server
npm run dev
```

**Option B - WSL2:**
```bash
cd /mnt/e/ui-agent/vta/frontend

# Install packages (first time only)
npm install

# Start dev server
npm run dev
```

**Expected output:**
```
  VITE v5.x.x  ready in 1234 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

---

## Part 6: Access and Test (2 minutes)

### Step 6.1: Open Browser

Navigate to: `http://localhost:5173` (or port shown by Vite)

You should see:
```
┌─────────────────────────────────────────────────┐
│ Virtual Trainer Agent              Connected ● │
├──────────────────┬──────────────────────────────┤
│                  │                              │
│  Chat Panel      │   [Empty right panel]        │
│                  │                              │
│  Task Progress   │                              │
│                  │                              │
│  [Start Tutorial]│                              │
│                  │                              │
│  🎤 Click to     │                              │
│     Speak        │                              │
│                  │                              │
└──────────────────┴──────────────────────────────┘
```

### Step 6.2: Start Tutorial

1. Click **"Start Tutorial"** button
2. You should see:
   - "Tutorial loaded" message in chat
   - Task list appears showing 3 tasks
   - Right panel may show PDF or desktop

### Step 6.3: Watch Real Desktop in Action

When the tutorial reaches **T3 (Hands-On: Linux Commands)**:

1. Right panel switches to **Desktop View**
2. You'll see a **real XFCE desktop** streaming live
3. Watch as the system:
   - Opens terminal automatically
   - Types commands in real-time
   - Shows output
   - Moves mouse cursor

**What you'll see:**
```
┌─────────────────────────────────────────────────┐
│ Virtual Trainer Agent              Connected ● │
├──────────────────┬──────────────────────────────┤
│                  │   🖥️ LIVE LINUX DESKTOP      │
│  💬 TRAINER:     │   ┌──────────────────────┐   │
│  "Now I'll open  │   │ $ ls -la             │   │
│  the terminal    │   │ total 48             │   │
│  and run ls"     │   │ drwxr-xr-x ...       │   │
│                  │   │ (Real terminal)      │   │
│  ✓ T3.1 Open     │   └──────────────────────┘   │
│    terminal      │                              │
│  ⏳ T3.2 Run ls   │   [XFCE Desktop Background]  │
│                  │                              │
│  [✓ Yes] [✗ No]  │   Mouse cursor visible!      │
│                  │   Windows opening!           │
└──────────────────┴──────────────────────────────┘
```

---

## Part 7: Verify Everything Works

### Test 1: Agent S3 Health Check

Open new terminal:

```bash
# In WSL2
curl http://localhost:5001/health

# Expected:
# {"status":"healthy","display":":99"}
```

### Test 2: Take Screenshot

```bash
curl -X POST http://localhost:5001/action/screenshot | jq '.success'

# Expected:
# true
```

### Test 3: Check Desktop Display

```bash
# In WSL2, open a test application
export DISPLAY=:99
xfce4-terminal &
```

Then check the browser - you should see a terminal window appear in the desktop panel!

### Test 4: WebSocket Connection

In browser console (F12):
```javascript
// Should NOT see any WebSocket errors
// Should see: "WebSocket connected"
```

### Test 5: Voice Interaction (if AWS configured)

1. Click **🎤 Click to Speak** button
2. Allow microphone permissions
3. Say "Hello"
4. You should:
   - Hear Nova Sonic respond
   - See transcript in chat
   - Get audio feedback

---

## Part 8: Troubleshooting

### Problem: "Cannot connect to X server :99"

**Fix:**

```bash
# Check if Xvfb is running
ps aux | grep Xvfb

# If not running, restart setup script
cd /mnt/e/ui-agent/vta
./setup_real_desktop.sh

# Verify DISPLAY variable
echo $DISPLAY
# Should output: :99

# Test display
export DISPLAY=:99
xdpyinfo | head -5
```

### Problem: Desktop panel shows black screen

**Fix:**

```bash
# Check websockify is running
ps aux | grep websockify
# Should show: websockify ... 6080 localhost:5900

# Check x11vnc is running
ps aux | grep x11vnc
# Should show: x11vnc -display :99

# Restart services if needed
pkill -f websockify
pkill -f x11vnc
./setup_real_desktop.sh
```

### Problem: "Module not found: vta"

**Fix:**

```bash
# Make sure PYTHONPATH is set
export PYTHONPATH=/mnt/e/ui-agent

# Verify
echo $PYTHONPATH
# Should output: /mnt/e/ui-agent

# Check module exists
ls /mnt/e/ui-agent/vta
# Should show: agent_s3/ orchestrator/ etc.
```

### Problem: Missing Python packages (pyautogui, python-xlib, Pillow)

**Fix:**

```bash
# Check which packages are missing
pip3 list | grep -E "pyautogui|python-xlib|Pillow"

# If any are missing, install them
cd /mnt/e/ui-agent/vta
pip3 install --user -r requirements.txt

# Or install individually
pip3 install --user pyautogui python-xlib Pillow pytesseract pynput mss

# Verify all are installed
pip3 list | grep -E "pyautogui|python-xlib|Pillow|pynput|pytesseract"

# You should see:
# Pillow              10.4.0
# pyautogui           0.9.54
# pynput              1.7.7
# pytesseract         0.3.10
# python-xlib         0.33
```

### Problem: Frontend can't connect to backend

**Fix:**

Check `vta/frontend/vite.config.js` has correct proxy:

```javascript
export default defineConfig({
  server: {
    proxy: {
      '/ws': {
        target: 'http://localhost:5000',
        ws: true,
        changeOrigin: true,
      },
    },
  },
})
```

### Problem: Port already in use

**Fix:**

```bash
# Find what's using the port
sudo netstat -tulpn | grep 5001

# Kill the process
kill <PID>

# Or kill all Python processes (careful!)
pkill python3
```

### Problem: Desktop services keep stopping

**Make them persistent:**

```bash
# Add to ~/.bashrc to auto-start on WSL launch
nano ~/.bashrc

# Add at the end:
if ! pgrep -f "Xvfb :99" > /dev/null; then
    cd /mnt/e/ui-agent/vta
    ./setup_real_desktop.sh
fi
```

---

## Part 9: Stopping Services

### Stop VTA Services

```bash
# In each terminal running Agent S3, Orchestrator, Frontend
# Press: Ctrl+C
```

### Stop Desktop Services

```bash
# Kill all desktop-related processes
pkill -f Xvfb
pkill -f x11vnc
pkill -f websockify
pkill -f xfce4

# Verify stopped
ps aux | grep -E "Xvfb|x11vnc|websockify"
# Should return nothing
```

### Clean Restart

```bash
# Stop everything
pkill -f Xvfb
pkill -f x11vnc
pkill -f websockify
pkill -f xfce4
pkill python3

# Wait 5 seconds
sleep 5

# Start fresh
cd /mnt/e/ui-agent/vta
./setup_real_desktop.sh

# Then restart Agent S3 and Orchestrator
```

---

## Part 10: What to Test

### Checklist for Real Desktop Testing

- [ ] Frontend loads at `localhost:5173`
- [ ] Connection status shows "Connected" (green)
- [ ] Click "Start Tutorial" - tasks appear
- [ ] Desktop panel shows **live XFCE desktop** (not black)
- [ ] Terminal opens automatically when T3 starts
- [ ] Commands typed in real-time visible
- [ ] Mouse cursor moves in desktop
- [ ] Confirmation bar appears after actions
- [ ] Can click Yes/No buttons
- [ ] Task progress updates correctly
- [ ] Voice works (if AWS configured)

### Success Criteria

You'll know it's working when:
1. **Desktop panel is NOT black** - shows blue XFCE background
2. **Terminal window opens** - you see actual xfce4-terminal
3. **Commands execute** - see `ls`, `pwd`, etc. running
4. **Mouse moves** - cursor visible moving between UI elements

---

## Part 11: Differences from Mock Mode

| Feature | Mock Mode | Real Desktop Mode |
|---------|-----------|-------------------|
| Desktop Panel | Black/empty | Live XFCE streaming |
| Actions | Logged only | Actually executed |
| Terminal | Pretends to open | Opens xfce4-terminal |
| Commands | Returns fake output | Runs real commands |
| Mouse | Not visible | Cursor moves visibly |
| Display | Not needed | Requires Xvfb :99 |
| Setup | Quick (1 min) | Full setup (20 min) |
| Use Case | Test workflow only | Test full automation |

---

## Part 12: Moving to EC2 Production

Once local testing works in WSL2, you're ready for EC2:

1. Use `DEPLOYMENT_GUIDE.md` for EC2 setup
2. Desktop will work the same way on EC2
3. Replace DynamoDB local mode with real tables
4. Add nginx reverse proxy
5. Set up systemd services for auto-start

**Local WSL2 testing proves:**
- Desktop automation works
- VNC streaming works
- Agent S3 can control the display
- Tutorial flow is correct

---

## Quick Reference

### Start Everything (After Initial Setup)

**Terminal 1 (Desktop Services):**
```bash
cd /mnt/e/ui-agent/vta
./setup_real_desktop.sh
```

**Terminal 2 (Agent S3):**
```bash
cd /mnt/e/ui-agent/vta
export DISPLAY=:99
export PYTHONPATH=/mnt/e/ui-agent
python3 -m vta.agent_s3.server
```

**Terminal 3 (Orchestrator):**
```bash
cd /mnt/e/ui-agent/vta
export PYTHONPATH=/mnt/e/ui-agent
python3 -m vta.orchestrator.main
```

**Terminal 4 (Frontend):**
```bash
cd /mnt/e/ui-agent/vta/frontend
npm run dev
```

**Browser:**
```
http://localhost:5173
```

---

## Support

**Common Issues:**
- Desktop black: Check Xvfb, x11vnc, websockify processes
- Can't connect: Check PYTHONPATH and DISPLAY variables
- Slow performance: Increase WSL2 memory in `.wslconfig`

**Logs:**
```bash
# Agent S3 logs
journalctl -u vta-agent-s3 -f

# Check Python errors
python3 -m vta.agent_s3.server 2>&1 | tee agent_s3.log
```

---

**Testing complete when you can see the terminal opening and typing commands in the browser!**
