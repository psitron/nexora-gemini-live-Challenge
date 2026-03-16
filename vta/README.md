# Nexora AI — Voice-Driven AI Tutor with Desktop & Browser Automation

> **Built for the [Gemini Live Agent Challenge](https://geminiliveagentchallenge.devpost.com/) Hackathon**

Nexora AI is a multimodal AI tutoring agent that **sees**, **hears**, and **speaks** — moving beyond the text box to deliver immersive, real-time learning experiences. It combines Gemini's Live API for natural voice interaction with vision-based desktop and browser automation to teach students hands-on skills.

![Architecture Diagram](architecture.png)

## What Nexora AI Does

Nexora AI is an AI-powered voice tutor that can:

- **Read and explain slides** using Gemini's vision capabilities — it sees the actual slide image and narrates the content naturally
- **Automate desktop tasks** — opens terminals, runs commands, and interacts with desktop applications by seeing the screen
- **Navigate web browsers** — uses Gemini Computer Use to click, type, and navigate real websites
- **Have natural conversations** — students speak naturally and Nexora responds with a distinct voice persona via Gemini Live API
- **Handle freestyle requests** — students can ask Nexora to do anything on the computer ("Can you run the date command?") and it adapts
- **Support repeat and Q&A** — students can ask questions, request repeats, and Nexora adapts in real-time

## Hackathon Category

**Live Agents + UI Navigator** — Nexora AI spans two categories:

- **Live Agent**: Real-time voice interaction via Gemini Live API with natural interruption handling and a distinct persona
- **UI Navigator**: Vision-based desktop and browser automation using Gemini multimodal to interpret screenshots and execute actions

## Gemini Live Agent Challenge

The **Gemini Live Agent Challenge** encourages developers to build intelligent agents powered by Gemini that can:

- Understand multimodal inputs (audio, vision, text)
- Interact through natural voice
- Observe and interpret user interfaces
- Plan and execute workflows autonomously
- Assist users through real-time AI agents

Nexora AI demonstrates a voice-driven AI UI agent capable of observing, reasoning, and performing tasks on behalf of the user — a next-generation learning experience that goes far beyond traditional text-based tutoring.

## Architecture

### System Components

```
Student Browser
    |
    |--- HTTPS (nginx reverse proxy, port 443)
    |        |
    |        |--- / .................. React Frontend (port 3000)
    |        |--- /ws ............... Orchestrator WebSocket (port 5000)
    |        |--- /api/ ............. Orchestrator REST API (port 5000)
    |        |--- /vnc/ ............. noVNC Desktop Viewer (port 6080)
    |        |--- /websockify ....... VNC WebSocket Bridge (port 6080)
    |
    v
Orchestrator (FastAPI + WebSocket, port 5000)
    |
    |--- Gemini Live API ............ Voice streaming (bidirectional audio)
    |       Model: gemini-2.5-flash-native-audio-preview
    |
    |--- Brain Client ............... Intent classification + Q&A
    |       Model: gemini-3-flash-preview (configurable)
    |
    |--- Desktop Vision Loop ........ Screenshot -> action planning
    |       Model: gemini-3-flash-preview (configurable)
    |       Execution: Agent S3 (xdotool, pyautogui)
    |
    |--- Browser Vision Loop ........ Gemini Computer Use + Playwright
    |       Model: gemini-3-flash-preview (configurable)
    |       Execution: Playwright Chromium
    |
    v
Agent S3 (FastAPI REST, port 5001)
    |
    |--- Screenshot capture (mss)
    |--- Desktop actions (xdotool, pyautogui)
    |--- Terminal control (xdotool type + Enter)
    |--- Reflex verification (post-action checks)
    |
    v
Virtual Linux Desktop (Xvfb + XFCE + x11vnc)
    |--- Display :1, 1920x1080
    |--- Streamed via noVNC to student browser
```

### How It Works

1. **Student connects** via browser to the Nexora AI frontend
2. **Selects a course** and starts a session
3. **Nexora speaks** the welcome message via Gemini Live API
4. **For theory slides**: Gemini Vision reads the slide image and generates a natural spoken explanation
5. **For hands-on tasks**: The Desktop Vision Loop takes a screenshot, Gemini plans the next action (click, type, run command), Agent S3 executes it, and Nexora narrates what happened
6. **For browser tasks**: The Browser Vision Loop uses Gemini Computer Use + Playwright for precise web automation
7. **Student interacts** via voice — asks questions, requests repeats, or asks Nexora to do freestyle tasks
8. **Brain classifies intent** and routes to the appropriate handler (continue, repeat, question, freestyle)
9. **Desktop resets** after tutorial completion using wmctrl to close all windows

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Voice | Gemini Live API (Native Audio) | Bidirectional voice streaming |
| Brain | Gemini Flash / Pro | Intent classification, Q&A, slide explanation |
| Desktop Vision | Gemini Flash + Agent S3 | Screenshot-based desktop automation |
| Browser Vision | Gemini Computer Use + Playwright | Web page automation |
| Frontend | React 18 + Vite | Student UI, slide viewer, VNC panel |
| Backend | FastAPI + WebSocket | Orchestration, session management |
| Desktop | Xvfb + XFCE + x11vnc + noVNC | Virtual Linux desktop |
| Proxy | nginx | HTTPS reverse proxy with WebSocket support |
| Cloud | Google Compute Engine | Hosting on Google Cloud |
| SDK | Google GenAI Python SDK | All Gemini API interactions |

## Quick Start

### One-Command Deployment on GCE

```bash
# 1. SSH into your GCE instance
gcloud compute ssh YOUR_INSTANCE --zone=us-central1-a

# 2. Clone the repository
git clone https://github.com/03sarath/ui-agent.git
cd ui-agent

# 3. Run the deployment script
chmod +x vta/deploy.sh
bash vta/deploy.sh

# 4. Access the application
# https://<EXTERNAL_IP>
```

The deploy script handles everything: system packages, Python/Node.js dependencies, virtual display, Playwright, nginx with SSL, and starts all services.

## GCE Deployment Guide

### Step 1: Create a GCE Instance

```bash
# Set your project
gcloud config set project YOUR_PROJECT_ID

# Create the instance
gcloud compute instances create nexora-ai \
    --zone=us-central1-a \
    --machine-type=e2-standard-4 \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --boot-disk-size=50GB \
    --tags=nexora-server
```

**Recommended Configuration:**

| Setting | Value | Reason |
|---------|-------|--------|
| Machine type | `e2-standard-4` | 4 vCPUs, 16GB RAM — needed for Playwright + XFCE |
| OS | Ubuntu 22.04 LTS | Tested and verified |
| Boot disk | 50GB | Space for Chromium, Node modules, PDFs |
| Zone | `us-central1-a` | Close to Gemini API endpoints |

### Step 2: Configure Firewall Rules

```bash
# Allow HTTPS and HTTP
gcloud compute firewall-rules create nexora-allow-web \
    --allow=tcp:80,tcp:443 \
    --source-ranges=0.0.0.0/0 \
    --target-tags=nexora-server \
    --description="Allow Nexora AI web traffic"
```

**Required Ports:**

| Port | Protocol | Service | Access |
|------|----------|---------|--------|
| 80 | HTTP | nginx (redirects to HTTPS) | Public |
| 443 | HTTPS | nginx (main entry point) | Public |
| 3000 | HTTP | Frontend (internal, via nginx) | Internal |
| 5000 | HTTP/WS | Orchestrator (internal, via nginx) | Internal |
| 5001 | HTTP | Agent S3 (internal) | Internal |
| 5900 | VNC | x11vnc (internal) | Internal |
| 6080 | HTTP/WS | noVNC (internal, via nginx) | Internal |

Only ports 80 and 443 need to be exposed publicly. All other services are accessed through the nginx reverse proxy.

### Step 3: SSH and Deploy

```bash
# SSH into the instance
gcloud compute ssh nexora-ai --zone=us-central1-a

# Clone the repository
git clone https://github.com/03sarath/ui-agent.git
cd ui-agent

# Run automated deployment
chmod +x vta/deploy.sh
bash vta/deploy.sh
```

### Step 4: Verify Deployment

```bash
# Check service status
bash vta/scripts/vta.sh status

# Check health endpoints
curl -k https://localhost/api/tutorials
curl http://localhost:5001/health

# View logs
bash vta/scripts/vta.sh logs
```

### Step 5: Access the Application

1. Open `https://<EXTERNAL_IP>` in your browser
2. Accept the self-signed certificate warning
3. Click the gear icon and enter your Gemini API key
4. Upload or create a course
5. Start the tutorial and interact with Nexora via voice

### Security Best Practices

- Only ports 80 and 443 are exposed publicly via firewall rules
- All internal services (5000, 5001, 5900, 6080) are accessed only through nginx
- HTTPS with SSL certificate (self-signed for demo, use Let's Encrypt for production)
- Gemini API key is stored in browser localStorage, entered per-session
- No credentials stored in the codebase

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Services not starting | `bash vta/scripts/vta.sh restart` |
| Port already in use | `lsof -i:<PORT> -t \| xargs kill` |
| Xvfb not running | `sudo systemctl restart xvfb` |
| nginx errors | `sudo nginx -t && sudo systemctl reload nginx` |
| Playwright fails | `playwright install chromium && playwright install-deps chromium` |
| No audio in browser | Check browser microphone permissions, use HTTPS |
| Polkit popup on desktop | Check `/etc/polkit-1/localauthority/50-local.d/45-allow-colord.pkla` exists |
| View service logs | `tail -f ~/ui-agent/logs/*.log` |
| Frontend not loading | Check `bash vta/scripts/vta.sh status` — frontend should be RUNNING on port 3000 |

## Service Management

```bash
# Start all services
bash vta/scripts/vta.sh start

# Stop all services
bash vta/scripts/vta.sh stop

# Restart all services
bash vta/scripts/vta.sh restart

# Check status
bash vta/scripts/vta.sh status

# View real-time logs
bash vta/scripts/vta.sh logs
```

## Course Creation

Nexora AI supports three ways to create courses:

1. **Create Course** — Visual builder with theory slides, practical tasks, and vision-driven tasks
2. **Import from Slides** — Upload a PDF, auto-generates one theory task per slide
3. **Import with Curriculum** — Upload a JSON curriculum file with optional PDF

### Curriculum JSON Format

```json
{
  "title": "Course Title",
  "description": "Course description",
  "tasks": [
    {
      "task_id": "T1",
      "type": "theory",
      "title": "Slide Title",
      "slide_number": 1,
      "subtasks": []
    },
    {
      "task_id": "T2",
      "type": "vision_driven",
      "title": "Hands-on Task",
      "sonic_prompt": "What Nexora says before starting",
      "subtasks": [
        {
          "subtask_id": "T2.1",
          "title": "Step title",
          "sonic_prompt": "What Nexora says",
          "goal": "What the AI should do on screen"
        }
      ]
    }
  ]
}
```

## Configuration

Click the gear icon in the header to configure:

- **Gemini API Key** — Required for all AI features
- **Voice Model** — Gemini 2.5 Flash Native Audio (fixed)
- **Brain Model** — Gemini Flash or Pro (configurable)
- **Desktop Vision Model** — Gemini Flash or custom
- **Browser Vision Model** — Gemini Flash or custom

All settings are saved to browser localStorage and persist across sessions.

## Project Structure

```
ui-agent/
  vta/
    orchestrator/              # Task orchestrator (port 5000)
      main.py                  # FastAPI WebSocket server
      orchestrator.py          # Tutorial execution loop
      gemini_live_client.py    # Gemini Live API voice client
      brain_client.py          # Intent classification + Q&A
      vision_loop.py           # Browser vision (Playwright)
      desktop_vision_loop.py   # Desktop vision (Agent S3)
      pdf_utils.py             # PDF slide extraction
    agent_s3/                  # Desktop automation (port 5001)
      server.py                # FastAPI REST server
      actions.py               # Linux desktop actions
      windows_actions.py       # Windows desktop actions
      reflex_verifier.py       # Post-action verification
    frontend/                  # React frontend (port 3000)
      src/
        App.jsx                # Main application
        components/            # UI components
        hooks/                 # WebSocket + audio hooks
      vite.config.js           # Vite build configuration
    scripts/                   # Deployment & management scripts
      vta.sh                   # Service manager (start/stop/restart)
      gce_setup.sh             # GCE initial setup
      setup_nginx.sh           # HTTPS proxy configuration
      deploy_gcp.sh            # Create GCE instance via gcloud
    curriculum/                # Course JSON files
    pdfs/                      # Course PDF slides
    deploy.sh                  # One-command automated deployment
    requirements.txt           # Python dependencies
    README.md                  # This file
```

## Proof of Google Cloud Deployment

The application runs on Google Compute Engine:

- **Instance**: `e2-standard-4` on `us-central1-a`
- **OS**: Ubuntu 22.04 LTS
- **Services**: Orchestrator (port 5000), Agent S3 (port 5001), Frontend (port 3000)
- **Proxy**: nginx with HTTPS
- **Automated deployment**: `deploy.sh` script in the repository

All Gemini API calls use the Google GenAI Python SDK (`google-genai`):
- `gemini-2.5-flash-native-audio-preview-12-2025` for voice ([`gemini_live_client.py`](vta/orchestrator/gemini_live_client.py))
- `gemini-3-flash-preview` for vision and brain ([`brain_client.py`](vta/orchestrator/brain_client.py), [`desktop_vision_loop.py`](vta/orchestrator/desktop_vision_loop.py))
- Gemini Computer Use API for browser automation ([`vision_loop.py`](vta/orchestrator/vision_loop.py))

## License

This project was created for the Gemini Live Agent Challenge hackathon.
