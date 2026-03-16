# Hackathon Submission Guide — Nexora AI

Use this document to fill in every field on the Devpost submission form.

---

## General Info

### Project Name (60 chars max)
```
Nexora AI — Voice-Driven AI Tutor
```

### Elevator Pitch (200 chars max)
```
An AI tutor that sees your screen, speaks naturally, and teaches hands-on skills by automating desktops and browsers in real-time — powered by Gemini Live API on Google Cloud.
```

### About the Project

```markdown
## Inspiration

Traditional e-learning is passive — students watch pre-recorded videos and follow static instructions. We asked: what if an AI tutor could actually *see* the student's screen, *speak* naturally like a real instructor, and *perform* hands-on tasks live? Inspired by the Gemini Live Agent Challenge's vision of agents that See, Hear, and Speak, we built Nexora AI — a voice-driven tutor that breaks the text box paradigm entirely.

## What it does

Nexora AI is an immersive AI tutoring platform where:

- **Nexora speaks** — Using Gemini Live API for real-time bidirectional voice, Nexora has a distinct persona and explains concepts naturally
- **Nexora sees slides** — Gemini Vision reads actual slide images and generates spoken explanations, not canned text
- **Nexora controls the desktop** — Opens terminals, runs commands, and interacts with applications by taking screenshots and planning actions
- **Nexora navigates browsers** — Uses Gemini Computer Use API with Playwright to navigate websites, click buttons, and fill forms
- **Students interact naturally** — Ask questions by voice, request repeats, or even give freestyle instructions ("Can you run the date command?") and Nexora adapts instantly
- **Desktop resets automatically** — After each tutorial, all windows close and the desktop returns to a clean state

The entire session flows through voice — no typing needed. The student watches Nexora demonstrate on a live Linux desktop streamed via noVNC, then interacts through conversation.

## How we built it

**Voice Layer**: Gemini 2.5 Flash Native Audio via the Live API handles all bidirectional voice streaming. We built a custom session manager with pre-created session pools, output gating to suppress auto-responses during listening, and VAD tuning for natural speech detection.

**Vision Layer**: Two parallel vision loops — Desktop Vision (Agent S3 + Gemini Flash for terminal/desktop tasks) and Browser Vision (Playwright + Gemini Computer Use for web tasks). The system auto-detects which to use based on goal keywords.

**Brain Layer**: Gemini Flash classifies student intent in real-time (continue, repeat, question, freestyle) and generates concise answers or extracts actionable goals from natural speech.

**Orchestrator**: A FastAPI WebSocket server coordinates the entire flow — loading curriculum, sequencing tasks, routing between voice/vision/brain, and managing session state.

**Frontend**: React 18 with real-time audio streaming, word-by-word transcript display, PDF slide viewer, and noVNC desktop panel — all in a single responsive interface.

**Infrastructure**: Deployed on Google Compute Engine with Xvfb virtual display, XFCE desktop, nginx HTTPS reverse proxy, and automated deployment via a single `deploy.sh` script.

## Challenges we ran into

1. **Gemini Live session lifecycle** — Sessions close after TURN_COMPLETE, requiring pre-created session pools with silence keepalive to ensure instant reconnection
2. **Voice transcription accuracy** — Speech was transcribed in Hindi instead of English until we added explicit `language_code="en-US"` and system prompt reinforcement
3. **Desktop reset after tutorials** — Initial attempts used Agent S3's `run_command` which typed reset scripts into the active window via xdotool. We switched to direct `subprocess` calls with `wmctrl` window management
4. **Repeat task loops** — When students asked to repeat a command, Gemini would re-execute it indefinitely. We added anti-repeat rules to the vision planning prompt
5. **Browser safety confirmations** — Gemini Computer Use returns `safety_decision: require_confirmation` when typing into chat interfaces, requiring acknowledgment in function responses
6. **Frontend mic recreation delay** — The microphone was being fully destroyed and recreated on every turn transition, causing 500ms-1s delays. We switched to keeping the mic stream alive and toggling a send gate

## Accomplishments that we're proud of

- **Freestyle mode** — Students can ask Nexora to do *anything* on the computer outside the curriculum, and it adapts using the same vision loop
- **Natural narration** — Nexora rephrases technical results ("The XFCE terminal application is open") into friendly language ("The terminal is ready on your screen!")
- **One-command deployment** — `bash deploy.sh` sets up everything on a fresh GCE instance in under 10 minutes
- **Multi-modal integration** — Voice (Gemini Live) + Vision (Gemini Flash) + Browser (Computer Use) + Desktop (Agent S3) all work together seamlessly in one tutoring session
- **Course creation flexibility** — Upload a PDF and get auto-generated theory tasks, or build custom curricula with the visual builder

## What we learned

- Gemini Live API sessions are ephemeral — you need pre-created session pools and keepalive mechanisms for reliable voice interaction
- The `audio_stream_end` signal and `SessionResumptionConfig` are essential for production Gemini Live apps
- Vision-based desktop automation requires careful prompt engineering to prevent action loops
- Browser automation via Computer Use needs safety decision handling for communication tools
- Keeping the browser microphone stream persistent (instead of recreating per turn) eliminates the most significant UX delay

## What's next for Nexora AI

- **Multi-student support** — Concurrent tutoring sessions with isolated desktop environments
- **Assessment mode** — AI evaluates student's own attempts and provides feedback
- **Curriculum marketplace** — Share and discover courses created by other educators
- **Mobile support** — Voice-first interface adapted for phone/tablet
- **ADK integration** — Migrate to Google's Agent Development Kit for managed session lifecycle
```

### Built With
```
Python, JavaScript, React, FastAPI, Google Gemini Live API, Google GenAI SDK, Gemini Computer Use API, Playwright, Google Compute Engine, Xvfb, XFCE, x11vnc, noVNC, nginx, WebSocket, Vite, PDF.js, PyMuPDF, xdotool, wmctrl
```

---

## "Try it out" Links

| Link Type | URL |
|-----------|-----|
| Live Demo | `https://<YOUR_EXTERNAL_IP>` (GCE instance) |
| GitHub Repo | `https://github.com/03sarath/ui-agent` |
| Desktop VNC | `http://<YOUR_EXTERNAL_IP>:6080/vnc.html` |

---

## Image Gallery (Recommendations)

Upload these images (3:2 ratio, JPG/PNG, max 5MB each):

1. **Architecture Diagram** (REQUIRED) — Your system architecture showing Gemini connections. Save as `architecture.png`
2. **Nexora AI Welcome Screen** — Screenshot of the app's landing page showing the course list and welcome panel
3. **Slide Narration** — Screenshot showing Nexora narrating a slide (left: transcript, right: slide viewer)
4. **Desktop Automation** — Screenshot showing the terminal with commands executed by the AI, visible in the noVNC panel
5. **Browser Automation** — Screenshot showing Gemini chat page with the AI-typed prompt and response
6. **Configuration Panel** — Screenshot of the gear icon settings (model configuration, API key)
7. **Freestyle Mode** — Screenshot showing the student asking a custom command and Nexora executing it

---

## File Upload (Recommendation)

Upload a **ZIP file** containing:
- `architecture.png` — Architecture diagram
- `nexora-ai-slides.pdf` — The demo curriculum slides used in the video
- `vertex_ai_studio_curriculum.json` — Sample curriculum JSON

Name it: `nexora-ai-hackathon-assets.zip`

---

## App Category

**Select: `Live Agents`**

Rationale: The core differentiator is real-time voice interaction via Gemini Live API. The UI navigation is a feature within the Live Agent experience, not the primary category. The Live Agents category description matches exactly: "a vision-enabled customized tutor that sees your homework."

---

## Project Start Date

```
02-16-26
```
(February 16, 2026 — start of the submission period)

---

## URL to PUBLIC Code Repo

```
https://github.com/03sarath/ui-agent
```

---

## Reproducible Testing Instructions in README?

**Yes** — The README includes:
- One-command deployment: `bash vta/deploy.sh`
- Step-by-step GCE guide (5 steps)
- Service management commands
- Troubleshooting table
- Verification commands

---

## URL to Proof of Google Cloud Deployment

Option 1 (code file link):
```
https://github.com/03sarath/ui-agent/blob/feature-gemini-hackathon/vta/deploy.sh
```

Option 2 (better — record a 30-second screen recording showing):
- GCP Console with the running VM instance
- SSH terminal showing `bash vta/scripts/vta.sh status` with all services RUNNING
- `curl` to health endpoints returning OK
- Upload to YouTube as unlisted and provide the link

---

## Architecture Diagram Location

```
Image Gallery (first image)
```

Upload the architecture diagram as the FIRST image in the gallery.

---

## OPTIONAL: Automated Cloud Deployment (Bonus 0.2 points)

```
https://github.com/03sarath/ui-agent/blob/feature-gemini-hackathon/vta/deploy.sh
```

This is the automated deployment script that sets up the entire application on a fresh GCE instance with a single command.

---

## OPTIONAL: Published Content (Bonus 0.6 points)

Write a blog post on Medium or dev.to covering:
- How Nexora AI was built with Gemini Live API, Computer Use, and GenAI SDK
- The challenges of real-time voice + vision integration
- Include: "This content was created for the purposes of entering the Gemini Live Agent Challenge hackathon. #GeminiLiveAgentChallenge"

---

## OPTIONAL: GDG Profile (Bonus 0.2 points)

Sign up at https://developers.google.com/community/gdg and provide your public profile URL.

---

## Demo Video Checklist (under 4 minutes)

Your video should include:

1. **Pitch (30s)** — "Traditional learning is passive. Nexora AI is a voice-driven tutor that sees, speaks, and acts on your screen."
2. **Course Selection (15s)** — Show the UI, select a course, start
3. **Slide Narration (30s)** — Nexora reads and explains a slide using AI vision
4. **Desktop Automation (45s)** — Nexora opens terminal, runs commands, narrates results
5. **Browser Automation (45s)** — Nexora navigates to Gemini, types a prompt, gets response
6. **Student Interaction (30s)** — Ask a question or freestyle request ("Can you check the date?")
7. **Architecture (15s)** — Flash the architecture diagram
8. **Cloud Proof (10s)** — Show GCP console or `vta.sh status`

Total: ~3.5 minutes — under the 4-minute limit.
