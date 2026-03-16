# Nexora AI — Complete Architecture

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
│         │                 │                  │               │       │
│         └────────────┬────┴──────────────────┴───────────────┘       │
│                      │                                               │
│               React Frontend (Port 3000)                             │
│               useWebSocket / useAudioStream hooks                    │
└──────────────────────┬───────────────────────────────────────────────┘
                       │
                       │ HTTPS (Port 443)
                       │
         ┌─────────────▼──────────────┐
         │    nginx Reverse Proxy      │
         │                             │
         │  /        → :3000 Frontend  │
         │  /ws      → :5000 WebSocket │
         │  /api/    → :5000 REST API  │
         │  /vnc/    → :6080 noVNC     │
         │  /websockify → :6080 VNC WS │
         │                             │
         │  SSL: Self-signed cert      │
         │  HTTP :80 → redirect :443   │
         └─────────────┬──────────────┘
                       │
     ┌─────────────────┼──────────────────────┐
     │                 │                      │
     ▼                 ▼                      ▼
┌─────────┐   ┌───────────────┐      ┌──────────────┐
│Frontend │   │ Orchestrator  │      │   noVNC       │
│  :3000  │   │    :5000      │      │   :6080       │
│ Vite    │   │  FastAPI +    │      │  websockify   │
│ React   │   │  WebSocket    │      │       │       │
└─────────┘   └───────┬───────┘      │       ▼       │
                      │               │  x11vnc :5900 │
                      │               │       │       │
                      │               │       ▼       │
                      │               │  Xvfb :1      │
                      │               │  1920x1080    │
                      │               │  XFCE Desktop │
                      │               └──────────────┘
                      │
    ┌─────────────────┼─────────────────────────┐
    │                 │                         │
    ▼                 ▼                         ▼
┌────────┐   ┌──────────────┐          ┌──────────────┐
│Gemini  │   │  Brain       │          │  Agent S3    │
│Live API│   │  Client      │          │   :5001      │
│        │   │              │          │  FastAPI     │
│Voice   │   │Intent + Q&A  │          │  REST API    │
│Stream  │   │Slide Explain │          └──────┬───────┘
└────────┘   └──────────────┘                 │
                                              │
                              ┌───────────────┼───────────────┐
                              │               │               │
                              ▼               ▼               ▼
                        ┌──────────┐  ┌────────────┐  ┌────────────┐
                        │Screenshot│  │  xdotool   │  │  Reflex    │
                        │ (mss)    │  │ pyautogui  │  │ Verifier   │
                        │          │  │            │  │ (xdotool   │
                        │ Capture  │  │ Click,Type │  │  checks)   │
                        │ desktop  │  │ Keyboard   │  │            │
                        └──────────┘  └────────────┘  └────────────┘
```

## Detailed Data Flow

### 1. Voice Interaction Flow

```
Student speaks into browser mic
    │
    ▼
useAudioStream.js (kept alive, sendingRef gate)
    │ PCM 16kHz mono → base64
    ▼
WebSocket → event: "student_audio"
    │
    ▼
Orchestrator (main.py)
    │ add_audio_chunk() → _audio_input_queue
    ▼
gemini_live_client.py → _audio_sender_loop
    │ send_realtime_input(audio blob)
    ▼
Gemini Live API (gemini-2.5-flash-native-audio-preview-12-2025)
    │
    ├── input_transcription → [STUDENT] text chunks
    │   │ Streamed to frontend via transcript_callback
    │   ▼
    │   _settle_transcript (3s silence) → transcript captured
    │
    └── model audio response (when Nexora speaks)
        │ output audio chunks → audio_output_callback
        │ output_transcription → [Nexora] text chunks
        ▼
        WebSocket → event: "audio_chunk" + "transcript_update"
            │
            ▼
        Browser plays audio via Web Audio API (24kHz)
```

### 2. Theory Task Flow (Slide Narration)

```
Orchestrator: execute_theory_task()
    │
    ├── 1. ws_send("show_slide", page: N)
    │       → Frontend switches to slide viewer
    │       → PDF.js renders the slide
    │
    ├── 2. extract_slide_image(pdf_path, page_number)
    │       → PyMuPDF (fitz) renders page as PNG (200 DPI)
    │
    ├── 3. brain.explain_slide(image_bytes)
    │       → Gemini Flash: "Summarize in 2 sentences"
    │       → Returns spoken explanation text
    │       Model: gemini-3-flash-preview
    │
    ├── 4. sonic.reconnect(prompt=explanation)
    │       → Gemini Live speaks the explanation
    │       → Audio streamed to browser
    │
    └── 5. sonic.wait_for_student_speech()
            → Student responds via voice
            → Brain classifies intent
```

### 3. Desktop Vision Task Flow

```
Orchestrator: execute_desktop_vision_task()
    │
    ├── 1. ws_send("show_desktop")
    │       → Frontend switches to noVNC panel
    │
    ├── 2. Nexora narrates intro via Gemini Live
    │
    └── 3. For each subtask:
            │
            ▼
        DesktopVisionLoop.run(goal="Open terminal")
            │
            ├── Agent S3: POST /action/screenshot
            │       → mss captures DISPLAY :1
            │       → Returns base64 PNG
            │
            ├── Gemini Flash: generateContent(screenshot + goal)
            │       Model: gemini-3-flash-preview
            │       → Returns JSON: {"action_type":"open_terminal"}
            │
            ├── Agent S3: POST /action/open_terminal
            │       → xdotool: xfce4-terminal launches
            │
            ├── Agent S3: POST /action/screenshot (verify)
            │       → New screenshot captured
            │
            ├── Gemini Flash: generateContent(new screenshot + goal)
            │       → Returns: {"action_type":"done","target":"Terminal is open"}
            │
            └── Loop ends → Nexora narrates result naturally
                    via Gemini Live
```

### 4. Browser Vision Task Flow

```
Orchestrator: execute_vision_task()
    │
    ├── 1. ws_send("show_desktop")
    │
    ├── 2. Nexora narrates intro via Gemini Live
    │
    └── 3. For each subtask:
            │
            ▼
        VisionLoop.run(goal="Navigate to gemini.google.com")
            │
            ├── Playwright: Launch Chromium on DISPLAY :1
            │       → Visible in noVNC panel
            │
            ├── page.screenshot() → PNG bytes
            │
            ├── Gemini Computer Use: generateContent(screenshot + goal)
            │       Model: gemini-3-flash-preview
            │       Tools: Computer Use function declarations
            │       → Returns: function_call: navigate({url: "..."})
            │
            ├── Playwright: page.goto(url)
            │
            ├── page.screenshot() → FunctionResponse with new screenshot
            │
            ├── Gemini: Next action or "done" (text response)
            │
            └── Loop ends → Nexora narrates result
```

### 5. Student Response Flow

```
Student speaks after task completion
    │
    ▼
wait_for_student_speech()
    │ Session may die → swap to pre-created session (with keepalive)
    │ _settle_transcript (3s) → transcript captured
    ▼
handle_student_response(transcript)
    │
    ├── is_simple_yes(transcript)?
    │   YES → return (next task)
    │
    ├── brain.classify_intent(transcript, task_context)
    │   Model: gemini-3-flash-preview
    │   │
    │   ├── "continue" → return (next task)
    │   ├── "question" → brain.answer_question() → Nexora speaks answer
    │   ├── "repeat"   → Re-run vision loop with repeat context
    │   ├── "freestyle" → Extract goal → Run desktop vision loop
    │   └── "wait"     → Nexora: "Take your time"
    │
    └── Loop: ask again until student says "ready"
```

## Gemini Models Used

| Model ID | Component | Purpose | API |
|----------|-----------|---------|-----|
| `gemini-2.5-flash-native-audio-preview-12-2025` | gemini_live_client.py | Bidirectional voice streaming (Nexora's voice) | Gemini Live API |
| `gemini-3-flash-preview` | brain_client.py | Intent classification, Q&A, slide explanation | generateContent |
| `gemini-3-flash-preview` | desktop_vision_loop.py | Desktop screenshot → action planning (JSON) | generateContent |
| `gemini-3-flash-preview` | vision_loop.py | Browser automation via Computer Use tool | generateContent (with tools) |

All models are accessed via **Google GenAI Python SDK** (`google-genai`).

## Service Port Map

```
┌──────────────────────────────────────────┐
│           Google Compute Engine          │
│           Ubuntu 22.04 LTS              │
│           e2-standard-4                 │
│                                          │
│  Port 443 (HTTPS) ─── nginx ──────────┐ │
│  Port 80  (HTTP)  ─── redirect → 443  │ │
│                                        │ │
│  Port 3000 ── React Frontend (Vite)    │ │
│  Port 5000 ── Orchestrator (FastAPI)   │ │
│  Port 5001 ── Agent S3 (FastAPI)       │ │
│  Port 5900 ── x11vnc (VNC server)     │ │
│  Port 6080 ── websockify (noVNC)      │ │
│  Port 8888 ── Jupyter (optional)      │ │
│                                        │ │
│  DISPLAY :1 ── Xvfb 1920x1080x24     │ │
│              └── XFCE Desktop          │ │
│              └── Playwright Chromium   │ │
│              └── Firefox               │ │
│              └── xfce4-terminal        │ │
└────────────────────────────────────────┘ │
└──────────────────────────────────────────┘
```

## Session Lifecycle

```
1. Browser connects → WebSocket /ws
2. start_session {tutorial_id, execution_mode, api_key, brain_model}
3. Orchestrator creates:
   ├── GeminiLiveClient (voice)
   ├── BrainClient (intent + Q&A)
   ├── AgentS3Client (desktop actions)
   └── ConfirmationManager
4. Tutorial loop:
   ├── Theory tasks → Slide image → Brain explains → Nexora speaks
   ├── Vision tasks → Desktop/Browser loop → Nexora narrates
   └── After each: wait_for_student_speech → classify → handle
5. Tutorial complete → Nexora congratulates
6. Desktop reset → wmctrl closes all windows
7. session_complete event → Frontend returns to course list
```
