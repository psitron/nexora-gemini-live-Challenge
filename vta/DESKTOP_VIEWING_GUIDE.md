# Desktop Viewing Guide

## What You Currently Have (Mock Mode)

```
┌─────────────────────────────────────────────────┐
│ Virtual Trainer Agent              Connected ● │
├──────────────────┬──────────────────────────────┤
│                  │                              │
│  Chat Transcript │   📄 Slides Panel            │
│                  │   (Shows PDF slides)         │
│  Task Progress   │                              │
│                  │   OR                         │
│  [Start Tutorial]│                              │
│                  │   🖥️ Desktop Panel           │
│  🎤 Microphone   │   (Currently empty/black)    │
│                  │                              │
└──────────────────┴──────────────────────────────┘
```

**Current behavior:**
- When T3 starts → system PRETENDS to open terminal
- Desktop panel stays black (no streaming)
- Actions logged but not executed

---

## What You'll See With Real Desktop

After running `setup_real_desktop.sh`:

```
┌─────────────────────────────────────────────────┐
│ Virtual Trainer Agent              Connected ● │
├──────────────────┬──────────────────────────────┤
│                  │                              │
│  💬 ARIA:        │   🖥️ LIVE LINUX DESKTOP      │
│  "Now I'll open  │   ┌──────────────────────┐   │
│   the terminal"  │   │ $ _                  │   │
│                  │   │                      │   │
│  ✓ T3.1 Open     │   │  (Real terminal)     │   │
│    terminal      │   └──────────────────────┘   │
│  ⏳ T3.2 Run ls   │                              │
│  ⏳ T3.3 Navigate│   [XFCE Desktop Background]  │
│                  │                              │
│  [✓ Yes] [No]    │   You see REAL mouse moving, │
│                  │   REAL typing, REAL apps!    │
│  🎤 (listening)  │                              │
└──────────────────┴──────────────────────────────┘
```

**Real desktop features:**
- ✅ See actual Linux desktop (XFCE)
- ✅ Watch terminal open automatically
- ✅ See commands typed in real-time
- ✅ File explorer, browser can be opened
- ✅ Cursor moves visibly during automation

---

## Quick Setup (2 Minutes)

### Option 1: Keep Mock Mode (Test Workflow Only)
If you just want to test the tutorial flow without seeing real desktop:
- ✅ You're already set up!
- Click "Start Tutorial"
- Watch slides switch, tasks progress
- Desktop panel will stay empty (that's normal in mock mode)

### Option 2: Enable Real Desktop Viewing (See Actual OS UI)
If you want to see browser, file explorer, terminal opening:

**Step 1:** In WSL2, run the setup script:
```bash
cd /mnt/e/ui-agent/vta
chmod +x setup_real_desktop.sh
./setup_real_desktop.sh
```

**Step 2:** Stop your current Agent S3 (Ctrl+C), then restart WITHOUT mock flag:
```bash
cd /mnt/e/ui-agent/vta
export DISPLAY=:99
python -m vta.agent_s3.server
```

**Step 3:** In browser, refresh and click "Start Tutorial"

**Step 4:** Wait for T3 (practical task) to start → you'll see the real desktop!

---

## Troubleshooting

**Q: Desktop panel still black after setup?**
- Check websockify is running: `ss -tuln | grep 6080`
- Check browser console for noVNC errors
- Verify WSL2 IP in App.jsx matches: `ip addr show eth0`

**Q: Can't see mouse or windows?**
- Xvfb might not have started: `ps aux | grep Xvfb`
- Try: `export DISPLAY=:99 && xdpyinfo` (should show display info)

**Q: Want to see desktop RIGHT NOW without tutorial?**
```bash
# In WSL2
export DISPLAY=:99
xfce4-terminal &  # Opens a terminal manually
```
Then check the desktop panel in browser - you should see it!

---

## Architecture Reminder

```
Browser (Windows)
  └─ noVNC client connects to ws://172.18.151.61:6080
       ↓
WSL2: websockify (port 6080)
       └─ bridges WebSocket to VNC
           ↓
WSL2: x11vnc (port 5900)
       └─ streams the X11 display
           ↓
WSL2: Xvfb :99 (virtual display 1280x800)
       └─ where XFCE desktop runs
           └─ where Agent S3 performs actions
```

**Mock mode:** Agent S3 doesn't touch the display, just returns fake results
**Real mode:** Agent S3 controls :99 display, x11vnc streams it to browser
