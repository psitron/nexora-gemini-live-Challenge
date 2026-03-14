# VTA (Virtual Trainer Agent)

Voice-driven AI tutoring platform with live desktop demonstrations powered by Amazon Nova Sonic and Agent S3.

## Architecture

```
Student Browser (React)
  ↓ WebSocket
EC2 Ubuntu 22.04
  ├─ nginx (reverse proxy)
  ├─ Task Orchestrator (FastAPI, port 5000)
  │   ├─ Nova Sonic Client (bidirectional audio)
  │   ├─ Curriculum Manager (DynamoDB)
  │   └─ Agent S3 HTTP Client
  ├─ Agent S3 REST API (FastAPI, port 5001)
  │   ├─ Linux-adapted actions (xdotool + pyautogui)
  │   └─ Reflex Verifier (xdotool checks)
  └─ Virtual Desktop: Xvfb → XFCE → x11vnc → websockify → noVNC
```

## Quick Start (EC2 Ubuntu 22.04)

### 1. Initial Setup

```bash
# Clone repo
git clone <your-repo> /opt/vta
cd /opt/vta/vta

# Run system setup
sudo bash scripts/ec2_setup.sh

# Configure .env
cp .env.example .env
nano .env  # Add AWS credentials, KB_ID, etc.
```

### 2. Configure Services

```bash
# Set up systemd services + nginx
sudo bash scripts/configure_services.sh

# Create DynamoDB tables
bash scripts/create_tables.sh us-east-1
```

### 3. Deploy

```bash
# Build frontend + start services
bash scripts/deploy.sh --local
```

### 4. Access

```
http://<your-ec2-ip>
```

## Development (Local)

### Prerequisites

- Python 3.11+
- Node.js 20+
- Xvfb (Linux) or Windows desktop

### Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend
npm install
cd ..

# Configure environment
cp .env.example .env
# Edit .env with VTA_LOCAL_CURRICULUM=true for local dev
```

### Run Services

```bash
# Terminal 1: Agent S3
export DISPLAY=:1  # Linux only
python -m vta.agent_s3.server

# Terminal 2: Orchestrator
python -m vta.orchestrator.main

# Terminal 3: React frontend
cd frontend
npm run dev
```

### Access

```
http://localhost:3000
```

## Curriculum Management

### Seed Tutorial

```bash
python -m vta.curriculum.seed_curriculum --file curriculum/linux_basics.json --region us-east-1
```

### Curriculum Structure

See `curriculum/linux_basics.json` for format:

- **Theory tasks**: `slide_number` + `slide_context` (Sonic speaks naturally)
- **Practical tasks**: `sonic_prompt` + `subtasks[]` (each with `action`, `params`, `reflex_check`)

## Architecture Details

### Nova Sonic Integration

- **Bidirectional streaming** via `aws_sdk_bedrock_runtime`
- **Tools**: `show_slide`, `run_ui_action`, `signal_task_complete`, `signal_student_confirmation`, `query_knowledge_base`
- **Audio**: 16kHz input (student) → 24kHz output (Sonic)
- **System prompt**: Full ARIA master prompt in `s2s_events.py`

### Agent S3 Actions

| Action | Description | Linux Implementation |
|--------|-------------|---------------------|
| `open_terminal` | Open terminal | `xfce4-terminal` via subprocess |
| `run_command` | Execute command | `xdotool type` + `xdotool key Return` |
| `click_text` | Click on text | Grounding agent → `pyautogui.click()` |
| `type_text` | Type text | `xdotool type` |
| `keyboard` | Press keys | `xdotool key` |
| `screenshot` | Capture screen | `mss` on DISPLAY=:1 |

### Reflex Verification

- **`terminal_visible`**: `xdotool search --name terminal`
- **`command_output_visible`**: Same as terminal_visible (proxy)
- **Retry once** on failure before marking failed

### Student Confirmation Flow

After every task:
1. Sonic asks: "Ready to move on?"
2. Student responds: **Yes** (advance) / **No** (wait) / **Repeat** (replay task)
3. Supports both button clicks and voice detection

## File Structure

```
vta/
├── agent_s3/              # Agent S3 REST API (port 5001)
│   ├── linux_adaptations.py   # Xvfb patches
│   ├── reflex_verifier.py     # xdotool checks
│   ├── actions.py             # 10 Linux actions
│   └── server.py              # FastAPI endpoints
├── orchestrator/          # Task Orchestrator (port 5000)
│   ├── s2s_events.py          # Nova Sonic event builders
│   ├── sonic_client.py        # Bidirectional streaming
│   ├── tool_handler.py        # Tool call dispatcher
│   ├── agent_s3_client.py     # HTTP client for Agent S3
│   ├── orchestrator.py        # Core execution loop
│   ├── curriculum_manager.py  # DynamoDB curriculum loader
│   ├── session_state.py       # State tracking
│   ├── confirmation.py        # Yes/No/Repeat flow
│   ├── kb_client.py           # Bedrock KB (RAG)
│   └── main.py                # WebSocket server
├── curriculum/            # Tutorial definitions
│   ├── linux_basics.json      # Sample curriculum
│   └── seed_curriculum.py     # DynamoDB seeder
├── frontend/              # React SPA
│   ├── src/
│   │   ├── components/        # UI components
│   │   ├── hooks/             # WebSocket, audio, noVNC
│   │   ├── App.jsx            # Main layout
│   │   └── styles/App.css     # Styling
│   ├── package.json
│   └── vite.config.js
└── scripts/               # Deployment
    ├── ec2_setup.sh           # System packages
    ├── configure_services.sh  # systemd services
    ├── create_tables.sh       # DynamoDB tables
    └── deploy.sh              # Build + deploy
```

## DynamoDB Tables

### `vta_curriculum`
- **PK**: `tutorial_id`
- **SK**: `task_id` (or `__meta__` for metadata)

### `vta_session_state`
- **PK**: `session_id`
- **SK**: `task_sort_key` (format: `T1#null` or `T3#T3.1`)
- **Status**: `pending` → `running` → `awaiting_confirmation` → `completed`

### `vta_sessions`
- **PK**: `session_id`
- Metadata: `tutorial_id`, `student_id`, `started_at`, `status`

## Troubleshooting

### Agent S3 not connecting to desktop

```bash
# Check Xvfb is running
ps aux | grep Xvfb

# Restart Xvfb
sudo systemctl restart vta-xvfb
```

### Nova Sonic timeout

```bash
# Check AWS credentials
aws sts get-caller-identity

# Check model access
aws bedrock list-foundation-models --region us-east-1 --query "modelSummaries[?contains(modelId, 'sonic')]"
```

### DynamoDB access denied

```bash
# Attach policy to EC2 IAM role:
# - AmazonDynamoDBFullAccess
# - AmazonBedrockFullAccess
```

### Frontend not loading

```bash
# Check nginx
sudo nginx -t
sudo systemctl status nginx

# Rebuild frontend
cd /opt/vta/vta/frontend
npm run build
```

## Testing

### Test Agent S3

```bash
curl http://localhost:5001/health
curl -X POST http://localhost:5001/action/screenshot
```

### Test Orchestrator

```bash
# WebSocket test (requires wscat)
npm install -g wscat
wscat -c ws://localhost:5000/ws
> {"event": "start_session", "tutorial_id": "linux_basics_v1"}
```

### Test Virtual Desktop

```bash
# VNC viewer (local test)
vncviewer localhost:5900

# Or via browser (noVNC)
# http://localhost:6080/vnc.html
```

## Production Checklist

- [ ] EC2 security group: ports 80, 443, 22 only
- [ ] IAM role with DynamoDB + Bedrock permissions
- [ ] DynamoDB tables created in correct region
- [ ] Curriculum seeded
- [ ] SSL certificate (HTTPS) via Let's Encrypt
- [ ] CloudWatch logging enabled
- [ ] Backup strategy for DynamoDB
- [ ] Cost monitoring alerts

## License

See main project LICENSE.
