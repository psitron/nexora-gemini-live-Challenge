# VTA — Virtual Trainer Agent

**AI-powered voice tutor that teaches Linux commands through real-time conversation and live desktop automation.**

Built for the [Gemini Live Agent Challenge](https://googleai.devpost.com/) hackathon.

**Category: Live Agents** — Real-time voice interaction with vision-enabled desktop tutoring.

---

## What It Does

VTA is a voice-first AI tutor that:

1. **Speaks naturally** — Uses Gemini Live API for real-time bidirectional voice conversation
2. **Understands the student** — Gemini 3 Flash classifies intent (questions, ready, repeat, wait)
3. **Automates the desktop** — Gemini Computer Use + Playwright navigates browsers, opens apps, runs commands while the student watches via noVNC
4. **Adapts to the learner** — Students can ask questions, request repeats, or skip at any point

### Demo Flow

```
Student opens browser → Connects to VTA
  → ARIA (voice tutor) welcomes student
  → Theory: ARIA explains Linux concepts via voice
  → Student says "ready" to advance, "repeat" to hear again, or asks questions
  → Practical: ARIA demonstrates commands on a live Linux desktop
  → Student watches via noVNC as the agent opens terminal, runs ls, pwd, etc.
  → Vision: Gemini Computer Use navigates Jupyter Notebook, creates files
  → Tutorial complete
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Student Browser                       │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ React UI │  │ Audio Stream │  │ noVNC Desktop View │  │
│  └────┬─────┘  └──────┬───────┘  └────────┬──────────┘  │
│       │               │                   │              │
│       └───────────────┼───────────────────┘              │
│                       │ WebSocket                        │
└───────────────────────┼──────────────────────────────────┘
                        │
            ┌───────────▼───────────┐
            │   FastAPI Orchestrator │ (port 5000)
            │                       │
            │  ┌─────────────────┐  │
            │  │ GeminiLiveClient│──┼──→ Gemini Live API (voice)
            │  │  (voice I/O)    │  │    gemini-2.5-flash-native-audio
            │  └─────────────────┘  │
            │                       │
            │  ┌─────────────────┐  │
            │  │   BrainClient   │──┼──→ Gemini 3 Flash (text)
            │  │  (intent + Q&A) │  │    gemini-3-flash-preview
            │  └─────────────────┘  │
            │                       │
            │  ┌─────────────────┐  │
            │  │   VisionLoop    │──┼──→ Gemini Computer Use (vision)
            │  │  (Playwright)   │  │    gemini-3-flash-preview
            │  └────────┬────────┘  │
            │           │           │
            └───────────┼───────────┘
                        │
            ┌───────────▼───────────┐
            │   GCE Linux Desktop   │
            │  Xvfb + XFCE + x11vnc │
            │  Playwright Chromium   │
            │  Agent S3 (port 5001)  │
            └───────────────────────┘
                    │
                    └──→ Google Compute Engine (GCP)
```

---

## Tech Stack

| Component | Technology |
|---|---|
| Voice I/O | Gemini Live API (`gemini-2.5-flash-native-audio`) |
| Intent Classification + Q&A | Gemini 3 Flash (`gemini-3-flash-preview`) |
| Desktop Automation | Gemini Computer Use + Playwright |
| Backend | FastAPI + WebSocket (Python) |
| Frontend | React + Vite |
| Desktop Viewer | noVNC (WebSocket → VNC) |
| SDK | Google GenAI SDK (`google-genai`) |
| Cloud | Google Compute Engine (GCE) |

---

## Quick Start (Local Development)

### Prerequisites
- Python 3.10+
- Node.js 18+
- [Gemini API key](https://aistudio.google.com/apikey)

### 1. Clone and setup

```bash
git clone https://github.com/YOUR_REPO/ui-agent.git
cd ui-agent
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate

pip install -r vta/requirements.txt
playwright install chromium
```

### 2. Configure

```bash
cp vta/.env.example vta/.env
# Edit vta/.env and set GEMINI_API_KEY=your-key
```

### 3. Start backend (Terminal 1)

```bash
# Windows PowerShell
$env:GEMINI_API_KEY="your-key"
$env:VTA_LOCAL_CURRICULUM="true"
$env:VTA_LOCAL_STATE="true"
$env:PYTHONPATH="."

python -m uvicorn vta.orchestrator.main:app --host 0.0.0.0 --port 5000
```

### 4. Start frontend (Terminal 2)

```bash
cd vta/frontend
npm install
npm run dev
```

### 5. Open browser

Go to `http://localhost:5173`, select **Demo Only** + **Gemini Flash**, click **Start Tutorial**.

> Note: Voice and theory tasks work on any OS. Desktop automation (practical/vision tasks) requires Linux with X display, or GCE deployment.

---

## GCE Deployment (Full Experience)

### Prerequisites
- [gcloud CLI](https://cloud.google.com/sdk/docs/install) installed and authenticated
- GCP project with billing enabled

### 1. Create GCE instance

```bash
gcloud config set project YOUR_PROJECT_ID
bash vta/scripts/deploy_gcp.sh
```

### 2. SSH and setup

```bash
gcloud compute ssh vta-agent --zone=us-central1-a

# On the instance:
git clone https://github.com/YOUR_REPO/ui-agent.git
cd ui-agent
bash vta/scripts/gce_setup.sh
```

### 3. Start services

```bash
export GEMINI_API_KEY='your-key'
bash vta/scripts/start_services.sh
```

### 4. Access

- **Frontend:** `http://EXTERNAL_IP:3000`
- **noVNC Desktop:** `http://EXTERNAL_IP:6080/vnc.html`
- **API Health:** `http://EXTERNAL_IP:5000/health`

---

## Hackathon Requirements Checklist

| Requirement | Status |
|---|---|
| Gemini model | Gemini 3 Flash + Gemini 2.5 Flash Native Audio |
| Google GenAI SDK | `google-genai` throughout |
| Google Cloud service | Google Compute Engine |
| Backend on GCP | Deployed on GCE |
| Multimodal I/O | Voice in/out + screenshot vision + browser actions |
| Real-time interaction | Bidirectional voice via Gemini Live API |
| Spin-up instructions | This README |
| Automated deployment | `deploy_gcp.sh` + `gce_setup.sh` + `start_services.sh` |

---

## Project Structure

```
vta/
├── orchestrator/
│   ├── main.py                 # FastAPI WebSocket server
│   ├── orchestrator.py         # Tutorial execution loop
│   ├── gemini_live_client.py   # Gemini Live API voice client
│   ├── brain_client.py         # Gemini 3 Flash intent + Q&A
│   ├── vision_loop.py          # Gemini Computer Use + Playwright
│   └── agent_s3_client.py      # Desktop action execution
├── agent_s3/
│   ├── server.py               # Desktop automation REST API
│   └── actions.py              # pyautogui/xdotool wrappers
├── frontend/
│   ├── src/App.jsx             # React UI
│   └── src/hooks/              # Audio, WebSocket, noVNC hooks
├── curriculum/
│   └── linux_basics.json       # Tutorial content
├── scripts/
│   ├── deploy_gcp.sh           # Create GCE instance
│   ├── gce_setup.sh            # Install dependencies on GCE
│   └── start_services.sh       # Start all services
└── requirements.txt
```

---

## License

MIT
