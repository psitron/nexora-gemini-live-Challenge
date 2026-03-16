# Nexora AI — Complete Architecture

## Architecture Diagram Prompt

Use this prompt with an AI image generator (e.g., Napkin AI, Eraser.io, or similar) to create the architecture diagram:

```
Create a professional software architecture diagram for "Nexora AI — Voice-Driven AI Tutor" with a dark theme and clean layout.

The diagram should show these layers from top to bottom:

LAYER 1 — STUDENT BROWSER (top)
A browser window containing 4 panels side by side:
- "Slide Viewer (PDF.js)" — displays course slides
- "Chat Transcript (Real-time)" — shows conversation text streaming word by word
- "Desktop Viewer (noVNC)" — shows live Linux desktop stream
- "Mic / Audio (Web Audio API)" — captures student voice and plays Nexora's voice
Below these panels: "React Frontend (Port 3000)" with "useWebSocket + useAudioStream hooks"

LAYER 2 — NGINX REVERSE PROXY (middle)
A horizontal bar showing:
- HTTPS Port 443 (SSL)
- Route: / → Frontend :3000
- Route: /ws → Orchestrator :5000 (WebSocket)
- Route: /api/ → Orchestrator :5000 (REST)
- Route: /vnc/ → noVNC :6080
- Route: /websockify → VNC WebSocket :6080
- HTTP Port 80 → redirect to 443

LAYER 3 — BACKEND SERVICES (below nginx)
Four boxes connected to nginx:

Box 1: "Frontend Service (Port 3000)" — Vite + React

Box 2: "Orchestrator (Port 5000)" — FastAPI + WebSocket
This is the central hub. It connects to:
  - Left arrow to: "Gemini Live API" cloud box (Voice Stream, bidirectional audio, Model: gemini-2.5-flash-native-audio)
  - Right arrow to: "Brain Client" box (Intent Classification + Q&A + Slide Explanation, Model: gemini-3-flash-preview)
  - Down arrow splits into TWO paths:
    Path A: "Desktop Vision Loop" → "Desktop Automation Agent (Port 5001)" FastAPI REST
    Path B: "Browser Vision Loop" → "Playwright + Chromium" (runs on virtual desktop)
  Both vision loops use: Model: gemini-3-flash-preview

Box 3: "noVNC Service (Port 6080)" — websockify bridge

Box 4: "Desktop Automation Agent (Port 5001)" — FastAPI REST API
Connected to 3 sub-components:
  - "Screenshot Capture (mss)" — captures virtual display
  - "Desktop Actions (xdotool + pyautogui)" — click, type, keyboard, open terminal, run command
  - "Reflex Verifier (xdotool)" — post-action verification

LAYER 4 — VIRTUAL LINUX DESKTOP (bottom)
A box representing the GCE virtual machine:
  - "Xvfb (Display :1, 1440x900)"
  - "XFCE Desktop Environment"
  - "x11vnc (VNC Server, Port 5900)"
  - Inside the desktop: Terminal windows, Firefox browser, Playwright Chromium — all visible
  - Arrow from x11vnc → websockify → noVNC → Student Browser (completing the desktop streaming loop)

CONNECTIONS TO SHOW:
- Student mic audio flows: Browser → WebSocket → Orchestrator → Gemini Live API
- Gemini Live audio flows back: Gemini Live API → Orchestrator → WebSocket → Browser speaker
- Desktop vision flow: Orchestrator → Desktop Automation Agent → screenshot → Gemini Flash → action → Desktop Automation Agent → executes on desktop
- Browser vision flow: Orchestrator → Playwright → screenshot → Gemini Computer Use → Playwright executes on Chromium
- Desktop stream: Xvfb → x11vnc → websockify → nginx → noVNC in browser

CLOUD LABELS:
- Google Compute Engine (wrapping the entire backend)
- "Google GenAI SDK" label near the Gemini connections
- "Gemini Live API" for voice
- "Gemini Flash" for brain + vision
- "Gemini Computer Use" for browser automation

COLOR SCHEME:
- Dark background (#0f1117)
- Blue accents for Gemini/Google services (#4285f4)
- Purple accents for voice (#818cf8)
- Green accents for success/status (#4ade80)
- White/light text for labels
```

---

## Component Names (Hackathon-Ready)

| Internal Code Name | Public Name | Purpose |
|-------------------|-------------|---------|
| Agent S3 | **Desktop Automation Agent** | Executes desktop actions via xdotool/pyautogui |
| Sonic / GeminiLiveClient | **Nexora Voice Engine** | Bidirectional voice via Gemini Live API |
| Brain Client | **Intent & Knowledge Engine** | Classifies student intent, answers questions, explains slides |
| Desktop Vision Loop | **Desktop Vision Planner** | Screenshots desktop → Gemini plans actions |
| Browser Vision Loop | **Browser Automation Agent** | Playwright + Gemini Computer Use for web tasks |
| Orchestrator | **Session Orchestrator** | Coordinates all components for tutorial execution |

---

## High-Level Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                        STUDENT BROWSER                               │
│                                                                      │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐  ┌───────────┐ │
│  │ Slide Viewer │  │ Chat         │  │ Desktop     │  │ Mic/Audio │ │
│  │ (PDF.js)     │  │ Transcript   │  │ Viewer      │  │ (WebAudio)│ │
│  │              │  │ (Real-time)  │  │ (noVNC)     │  │           │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬──────┘  └─────┬─────┘ │
│         └────────────┬────┴──────────────────┴───────────────┘       │
│                      │                                               │
│               React Frontend (Port 3000)                             │
└──────────────────────┬───────────────────────────────────────────────┘
                       │ HTTPS (Port 443)
         ┌─────────────▼──────────────┐
         │    nginx Reverse Proxy      │
         │  /     → :3000 Frontend     │
         │  /ws   → :5000 WebSocket    │
         │  /api/ → :5000 REST API     │
         │  /vnc/ → :6080 noVNC        │
         └─────────────┬──────────────┘
                       │
    ┌──────────────────┼──────────────────────┐
    │                  │                      │
    ▼                  ▼                      ▼
┌────────┐    ┌────────────────┐      ┌──────────────┐
│Frontend│    │  Session       │      │   noVNC       │
│ :3000  │    │  Orchestrator  │      │   :6080       │
│ React  │    │    :5000       │      │  websockify   │
└────────┘    └───────┬────────┘      └──────┬───────┘
                      │                      │
         ┌────────────┼────────────┐         │
         │            │            │         │
         ▼            ▼            ▼         ▼
   ┌──────────┐ ┌──────────┐ ┌─────────┐ ┌────────┐
   │ Nexora   │ │ Intent & │ │Desktop  │ │Browser │
   │ Voice    │ │Knowledge │ │Vision   │ │Autom.  │
   │ Engine   │ │ Engine   │ │Planner  │ │Agent   │
   │          │ │          │ │    │    │ │   │    │
   │ Gemini   │ │ Gemini   │ │    ▼    │ │   ▼    │
   │ Live API │ │ Flash    │ │Desktop  │ │Playwright
   │ Native   │ │          │ │Autom.   │ │Chromium│
   │ Audio    │ │classify_ │ │Agent    │ │        │
   │          │ │intent()  │ │ :5001   │ │ On     │
   │ Bidir.   │ │answer_   │ │         │ │DISPLAY │
   │ voice    │ │question()│ │xdotool  │ │  :1    │
   │ stream   │ │explain_  │ │pyauto   │ │        │
   └──────────┘ │slide()   │ │gui      │ └────────┘
                └──────────┘ └────┬────┘
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
                    ▼             ▼             ▼
              ┌──────────┐ ┌──────────┐ ┌──────────┐
              │Screenshot│ │ Desktop  │ │ Reflex   │
              │ Capture  │ │ Actions  │ │ Verifier │
              │ (mss)    │ │(xdotool) │ │(xdotool) │
              └──────────┘ └──────────┘ └──────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │  Virtual Linux Desktop     │
                    │  Xvfb (Display :1)         │
                    │  1440x900 • XFCE          │
                    │  x11vnc → websockify       │
                    │  ┌────────┐ ┌───────────┐  │
                    │  │Terminal│ │ Chromium/  │  │
                    │  │Windows │ │ Firefox    │  │
                    │  └────────┘ └───────────┘  │
                    └────────────────────────────┘

                 ─── Google Compute Engine (GCE) ───
```

## Gemini Models Used

| Model ID | Component | Purpose | API Type |
|----------|-----------|---------|----------|
| `gemini-2.5-flash-native-audio-preview-12-2025` | Nexora Voice Engine | Real-time bidirectional voice streaming | Gemini Live API |
| `gemini-3-flash-preview` | Intent & Knowledge Engine | Intent classification, Q&A, slide vision explanation | generateContent |
| `gemini-3-flash-preview` | Desktop Vision Planner | Screenshot → JSON action plan → Desktop Automation Agent executes | generateContent |
| `gemini-3-flash-preview` | Browser Automation Agent | Screenshot → Computer Use function calls → Playwright executes | generateContent (with tools) |

All accessed via **Google GenAI Python SDK** (`google-genai`).

## Detailed Data Flows

### Voice Flow
```
Student mic → Browser WebAudio (16kHz PCM) → WebSocket "student_audio"
→ Orchestrator → add_audio_chunk() → _audio_input_queue
→ _audio_sender_loop → send_realtime_input()
→ Gemini Live API (gemini-2.5-flash-native-audio)
→ input_transcription (student text) + model audio (Nexora voice)
→ WebSocket "audio_chunk" + "transcript_update"
→ Browser plays audio (24kHz) + displays transcript
```

### Desktop Vision Flow
```
Orchestrator receives subtask goal
→ Desktop Automation Agent: POST /action/screenshot → mss captures DISPLAY :1
→ Gemini Flash: generateContent(screenshot + goal + planning prompt)
→ Returns JSON: {"action_type":"run_command","target":"echo hello"}
→ Desktop Automation Agent: POST /action/run_command
→ xdotool types command + presses Enter on virtual desktop
→ Screenshot again → Gemini: "done" or next action
→ Loop until done (max 15 steps)
→ Nexora narrates result via Voice Engine
```

### Browser Vision Flow
```
Orchestrator receives subtask goal with URL/browser keywords
→ Playwright launches Chromium on DISPLAY :1
→ page.screenshot() → Gemini Computer Use: generateContent(screenshot + goal + tools)
→ Returns function_call: type_text_at({x, y, text, press_enter})
→ Playwright executes: page.mouse.click(x, y) + page.keyboard.type(text)
→ page.screenshot() → FunctionResponse with new screenshot
→ Loop until Gemini returns text (done) or max 20 steps
→ Nexora narrates result via Voice Engine
```

### Student Intent Flow
```
Student speaks → transcript captured (3s settle)
→ is_simple_yes()? → YES: continue to next task
→ brain.classify_intent(transcript, context)
   → "continue" → next task
   → "question" → brain.answer_question() → Nexora speaks answer
   → "repeat"   → re-run vision loop on current task
   → "freestyle" → extract goal → run Desktop Vision Planner
   → "wait"     → Nexora: "Take your time"
→ Loop until student says "ready"
```

## Service Port Map

| Port | Service | Public? | Protocol |
|------|---------|---------|----------|
| 443 | nginx (HTTPS) | Yes | HTTPS + WSS |
| 80 | nginx (redirect) | Yes | HTTP → 443 |
| 3000 | React Frontend | No (via nginx) | HTTP |
| 5000 | Session Orchestrator | No (via nginx) | HTTP + WS |
| 5001 | Desktop Automation Agent | No | HTTP REST |
| 5900 | x11vnc | No | VNC |
| 6080 | websockify / noVNC | No (via nginx) | HTTP + WS |
| 8888 | Jupyter (optional) | No | HTTP |

## Session Lifecycle

```
1. Browser → WebSocket /ws → Orchestrator
2. start_session {tutorial_id, execution_mode, api_key, models}
3. Orchestrator creates:
   ├── Nexora Voice Engine (Gemini Live session)
   ├── Intent & Knowledge Engine (Gemini Flash client)
   ├── Desktop Automation Agent client (HTTP)
   └── Confirmation Manager
4. Welcome → Nexora speaks → Student says "ready"
5. Tutorial loop:
   ├── Theory: Slide image → Brain explains → Nexora speaks
   ├── Desktop: Vision Planner → Automation Agent → Nexora narrates
   ├── Browser: Vision Loop → Playwright → Nexora narrates
   └── After each: listen → classify intent → handle
6. Last task: "That was our final step" → "Congratulations!"
7. Desktop reset: wmctrl closes all windows
8. session_complete → Frontend returns to course list
```
