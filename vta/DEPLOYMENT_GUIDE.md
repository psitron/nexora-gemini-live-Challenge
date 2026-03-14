# VTA Deployment Guide — Step by Step

Complete guide to deploy VTA from scratch on AWS EC2.

---

## Part 1: AWS Prerequisites (15 minutes)

### Step 1.1: Create IAM Role for EC2

1. Go to **AWS Console → IAM → Roles → Create role**
2. Select **AWS service** → **EC2** → Next
3. Attach these policies:
   - `AmazonDynamoDBFullAccess`
   - `AmazonBedrockFullAccess`
   - `AmazonS3ReadOnlyAccess` (for PDF storage)
4. Name: `VTA-EC2-Role`
5. Click **Create role**

### Step 1.2: Request Bedrock Model Access

1. Go to **AWS Console → Bedrock → Model access**
2. Click **Request model access**
3. Select:
   - `Amazon Nova Sonic`
   - `Anthropic Claude 3 Haiku` (for KB)
4. Submit request (usually instant approval)

### Step 1.3: Launch EC2 Instance

1. Go to **EC2 → Launch Instance**
2. Configure:
   - **Name**: `VTA-Server`
   - **AMI**: Ubuntu Server 22.04 LTS (64-bit x86)
   - **Instance type**: `t3.medium` (minimum, t3.large recommended)
   - **Key pair**: Create new or use existing (download `.pem` file)
   - **Network settings**:
     - Create security group: `VTA-SG`
     - Allow ports: `22` (SSH), `80` (HTTP), `443` (HTTPS)
   - **Storage**: 20 GB gp3
   - **Advanced details → IAM instance profile**: Select `VTA-EC2-Role`
3. Click **Launch instance**
4. Wait 2 minutes for instance to start
5. Note the **Public IPv4 address** (e.g., `3.85.123.45`)

### Step 1.4: Connect to EC2

```bash
# Make key file read-only
chmod 400 your-key.pem

# SSH into instance
ssh -i your-key.pem ubuntu@3.85.123.45
```

You should see the Ubuntu prompt: `ubuntu@ip-172-31-x-x:~$`

---

## Part 2: Upload Code to EC2 (5 minutes)

### Option A: From Your Local Machine (Recommended)

**On your local machine (Windows):**

```bash
# Navigate to project root (parent of vta/)
cd E:\ui-agent

# Upload entire vta/ directory to EC2
scp -i your-key.pem -r vta ubuntu@3.85.123.45:/home/ubuntu/

# This uploads all 41 files (~5 MB)
```

### Option B: Via Git

**On EC2 (after SSH):**

```bash
# Clone your repo
git clone https://github.com/your-username/your-repo.git /home/ubuntu/vta

# Or if not in git yet, use scp from Option A
```

### Step 2.1: Move to /opt/vta

**On EC2:**

```bash
# Move to system location
sudo mv /home/ubuntu/vta /opt/vta

# Verify
ls -la /opt/vta
# Should see: agent_s3/ orchestrator/ frontend/ scripts/ etc.
```

---

## Part 3: System Setup (10 minutes)

### Step 3.1: Run System Setup Script

**On EC2:**

```bash
cd /opt/vta

# Make scripts executable
sudo chmod +x scripts/*.sh

# Run full system setup (installs all packages)
sudo bash scripts/ec2_setup.sh
```

**What this does:**
- Updates Ubuntu packages
- Installs Xvfb, XFCE, x11vnc, xdotool
- Installs Python 3.11, Node.js 20, nginx
- Installs Tesseract OCR
- Installs all Python packages (FastAPI, boto3, pyautogui, etc.)
- Creates `/opt/vta` directory

**Expected output:**
```
===== VTA EC2 Setup =====
[1/8] Updating system packages...
[2/8] Installing Xvfb, XFCE, VNC...
[3/8] Installing noVNC and websockify...
...
===== EC2 Setup Complete =====
```

### Step 3.2: Configure Environment

**On EC2:**

```bash
cd /opt/vta

# Copy environment template
cp .env.example .env

# Edit with your AWS region
nano .env
```

**In nano editor:**

1. Find `AWS_DEFAULT_REGION=us-east-1` — change to your region if needed
2. Find `VTA_KB_ID=your-kb-id-here` — leave empty for now (optional)
3. Press `Ctrl+O` to save
4. Press `Ctrl+X` to exit

**Minimal .env for testing:**
```bash
AWS_DEFAULT_REGION=us-east-1
DISPLAY=:1
VTA_DISPLAY_WIDTH=1280
VTA_DISPLAY_HEIGHT=800
AGENT_S3_PORT=5001
ORCHESTRATOR_PORT=5000
LOG_LEVEL=INFO
```

---

## Part 4: Configure Services (5 minutes)

### Step 4.1: Set Up systemd Services

**On EC2:**

```bash
cd /opt/vta

# Configure all services (Xvfb, XFCE, VNC, Agent S3, Orchestrator, nginx)
sudo bash scripts/configure_services.sh
```

**What this creates:**
- 6 systemd services:
  - `vta-xvfb.service` — Virtual display :1
  - `vta-xfce.service` — Desktop environment
  - `vta-x11vnc.service` — VNC server (port 5900)
  - `vta-websockify.service` — WebSocket bridge (port 6080)
  - `vta-agent-s3.service` — Agent S3 REST API (port 5001)
  - `vta-orchestrator.service` — Task Orchestrator (port 5000)
- nginx reverse proxy config

**Expected output:**
```
===== Configuring VTA Services =====
  Enabled: vta-xvfb
  Enabled: vta-xfce
  ...
===== Services Configured =====
```

### Step 4.2: Verify Services Config

```bash
# Check systemd service files
ls -la /etc/systemd/system/vta-*

# Check nginx config
sudo nginx -t
# Should output: "syntax is ok" and "test is successful"
```

---

## Part 5: Create DynamoDB Tables (2 minutes)

### Step 5.1: Create Tables

**On EC2:**

```bash
cd /opt/vta

# Create 3 DynamoDB tables in your region
bash scripts/create_tables.sh us-east-1
```

**Expected output:**
```
===== Creating VTA DynamoDB Tables (region: us-east-1) =====
[1/3] Creating vta_curriculum...
  Created vta_curriculum
[2/3] Creating vta_session_state...
  Created vta_session_state
[3/3] Creating vta_sessions...
  Created vta_sessions
===== DynamoDB Tables Ready =====
```

### Step 5.2: Verify Tables

```bash
# List tables
aws dynamodb list-tables --region us-east-1

# Should see:
# {
#   "TableNames": [
#     "vta_curriculum",
#     "vta_session_state",
#     "vta_sessions"
#   ]
# }
```

**If you get "Unable to locate credentials" error:**

```bash
# Verify IAM role is attached to EC2
aws sts get-caller-identity

# If fails, go to EC2 console:
# Select instance → Actions → Security → Modify IAM role
# Select VTA-EC2-Role → Update IAM role
# Then SSH again and retry
```

---

## Part 6: Deploy and Start Services (5 minutes)

### Step 6.1: Build and Deploy

**On EC2:**

```bash
cd /opt/vta

# Run deployment (builds React, seeds curriculum, starts services)
sudo bash scripts/deploy.sh --local
```

**What this does:**
1. Installs frontend npm packages
2. Builds React app (`npm run build`)
3. Seeds `linux_basics.json` curriculum into DynamoDB
4. Restarts Agent S3 and Orchestrator services
5. Reloads nginx

**Expected output:**
```
===== Local Deployment on EC2 =====
[1/4] Building React frontend...
added 234 packages in 45s
...
[2/4] Seeding curriculum...
Seeding tutorial: linux_basics_v1
  Seeded task T1: What is Linux?
  Seeded task T2: Understanding the Linux Terminal
  Seeded task T3: Hands-On: Linux Commands
Done. 3 tasks seeded for linux_basics_v1
[3/4] Restarting services...
[4/4] Reloading nginx...
===== Deployment Complete =====
```

### Step 6.2: Start All Services

**On EC2:**

```bash
# Start services in order
sudo systemctl start vta-xvfb
sudo systemctl start vta-xfce
sudo systemctl start vta-x11vnc
sudo systemctl start vta-websockify
sudo systemctl start vta-agent-s3
sudo systemctl start vta-orchestrator
sudo systemctl start nginx
```

### Step 6.3: Verify Services Running

```bash
# Check all services status
systemctl status vta-xvfb vta-xfce vta-x11vnc vta-websockify vta-agent-s3 vta-orchestrator nginx

# All should show: "active (running)" in green
```

**Quick status check:**

```bash
# Check one by one
sudo systemctl status vta-agent-s3
# Look for: "Active: active (running)"

sudo systemctl status vta-orchestrator
# Look for: "Active: active (running)"
```

**If any service failed:**

```bash
# See detailed logs
sudo journalctl -u vta-agent-s3 -n 50

# Common fixes:
# 1. Check DISPLAY=:1 is set in service file
# 2. Verify Python packages installed: pip3 list | grep fastapi
# 3. Check port not in use: sudo netstat -tulpn | grep 5001
```

---

## Part 7: Access VTA (1 minute)

### Step 7.1: Open in Browser

1. Get your EC2 public IP:
   ```bash
   curl http://169.254.169.254/latest/meta-data/public-ipv4
   # Example output: 3.85.123.45
   ```

2. Open browser: `http://3.85.123.45`

3. You should see **Virtual Trainer Agent** interface:
   - Left panel: Chat, Task Progress, Mic button, "Start Tutorial" button
   - Right panel: Empty (waiting for session start)
   - Top bar: "Virtual Trainer Agent" title, connection status

### Step 7.2: Test Connection

1. Look at top-right corner — should show **Connected** (green)
2. Click **Start Tutorial** button
3. You should see:
   - "Tutorial loaded" message
   - Task progress shows 3 tasks
   - Right panel switches to PDF slide viewer (may be empty if no PDF uploaded)

### Step 7.3: Test Voice Interaction

1. Click **Click to Speak** button (mic)
2. Allow microphone permissions in browser
3. Button changes to **Speaking...** (red, pulsing)
4. Say: "Hello"
5. You should hear Nova Sonic respond (audio plays in browser)
6. Transcript appears in chat panel: "YOU: Hello" → "TRAINER: [response]"

---

## Part 8: Verification Tests (5 minutes)

### Test 1: Agent S3 Health

```bash
# On EC2
curl http://localhost:5001/health

# Expected:
# {"status":"healthy","display":":1"}
```

### Test 2: Agent S3 Screenshot

```bash
# On EC2
curl -X POST http://localhost:5001/action/screenshot | jq '.success'

# Expected:
# true
```

### Test 3: Orchestrator WebSocket

```bash
# Install wscat if not present
sudo npm install -g wscat

# Connect to orchestrator
wscat -c ws://localhost:5000/ws

# Send:
{"event":"start_session","tutorial_id":"linux_basics_v1"}

# Should receive:
{"event":"session_started","session_id":"..."}

# Ctrl+C to exit
```

### Test 4: DynamoDB Curriculum

```bash
# Check curriculum loaded
aws dynamodb scan --table-name vta_curriculum --region us-east-1 | jq '.Items | length'

# Expected: 4 (3 tasks + 1 metadata record)
```

### Test 5: Virtual Desktop (noVNC)

1. In browser, open: `http://3.85.123.45/novnc/vnc.html`
2. Click **Connect**
3. Should see XFCE desktop (empty desktop with taskbar)
4. This proves Xvfb → x11vnc → websockify chain is working

---

## Part 9: Troubleshooting

### Problem: "Unable to connect to the server"

**Fix:**

```bash
# Check security group allows port 80
aws ec2 describe-security-groups --group-ids sg-xxxxx | jq '.SecurityGroups[0].IpPermissions'

# Should see port 80 with 0.0.0.0/0

# If not, add rule:
# EC2 Console → Security Groups → VTA-SG → Edit inbound rules
# Add: Type=HTTP, Port=80, Source=0.0.0.0/0
```

### Problem: Services won't start

**Fix:**

```bash
# Check logs
sudo journalctl -u vta-agent-s3 -n 100
sudo journalctl -u vta-orchestrator -n 100

# Common issues:
# 1. Port already in use
sudo netstat -tulpn | grep 5001
# Kill process: sudo kill <pid>

# 2. Missing Python packages
pip3 list | grep fastapi
# Reinstall: pip3 install --break-system-packages fastapi uvicorn

# 3. DISPLAY not set
# Edit service: sudo systemctl edit vta-agent-s3
# Add: Environment=DISPLAY=:1
```

### Problem: "Connected" but no audio

**Browser console check:**

1. Press F12 in browser
2. Click Console tab
3. Look for errors like:
   - "WebSocket connection failed"
   - "NotAllowedError: Permission denied"

**Fixes:**

- **WebSocket failed**: Check nginx config, restart nginx
- **Permission denied**: Click mic button again, allow permissions
- **No audio output**: Check browser audio not muted, volume up

### Problem: Desktop not visible (noVNC black screen)

**Fix:**

```bash
# Restart virtual desktop stack
sudo systemctl restart vta-xvfb
sleep 2
sudo systemctl restart vta-xfce
sleep 2
sudo systemctl restart vta-x11vnc
sleep 2
sudo systemctl restart vta-websockify

# Check logs
sudo journalctl -u vta-x11vnc -n 50
```

### Problem: DynamoDB "AccessDeniedException"

**Fix:**

```bash
# Verify IAM role
aws sts get-caller-identity

# If no role attached:
# 1. Go to EC2 Console
# 2. Select instance → Actions → Security → Modify IAM role
# 3. Choose VTA-EC2-Role
# 4. Update IAM role
# 5. Wait 1 minute, retry
```

### Problem: Nova Sonic "ModelNotFoundError"

**Fix:**

1. Go to **Bedrock Console → Model access**
2. Check **Amazon Nova Sonic** is "Access granted"
3. If not, click **Request model access** → Submit
4. Wait 1-2 minutes for approval (usually instant)
5. Verify:
   ```bash
   aws bedrock list-foundation-models --region us-east-1 | grep sonic
   ```

---

## Part 10: Production Hardening (Optional)

### Add HTTPS (Let's Encrypt)

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate (replace with your domain)
sudo certbot --nginx -d vta.yourdomain.com

# Auto-renewal is configured by certbot
```

### Enable CloudWatch Logging

```bash
# Install CloudWatch agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i amazon-cloudwatch-agent.deb

# Configure (follow prompts)
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-config-wizard
```

### Set Up Monitoring

```bash
# Watch service logs live
sudo journalctl -u vta-agent-s3 -u vta-orchestrator -f

# Check resource usage
htop
```

### Backup DynamoDB

1. Go to **DynamoDB Console**
2. Select each table
3. Click **Backups** tab
4. Click **Create backup**
5. Enable **Point-in-time recovery** for automatic backups

---

## Part 11: Next Steps

### Add More Tutorials

1. Create new JSON file: `curriculum/python_basics.json`
2. Seed: `python3 -m vta.curriculum.seed_curriculum --file curriculum/python_basics.json`
3. Update frontend to show tutorial selector

### Upload PDF Slides

1. Create S3 bucket: `vta-tutorial-pdfs`
2. Upload PDF: `aws s3 cp linux_basics.pdf s3://vta-tutorial-pdfs/tutorials/`
3. Update curriculum JSON: `"pdf_s3_key": "tutorials/linux_basics.pdf"`
4. Add S3 pre-signed URL generation in frontend

### Enable Knowledge Base (RAG)

1. Create Bedrock Knowledge Base in AWS Console
2. Upload documentation to S3
3. Note Knowledge Base ID
4. Update `.env`: `VTA_KB_ID=your-kb-id`
5. Restart orchestrator: `sudo systemctl restart vta-orchestrator`

---

## Quick Reference Commands

```bash
# Start all services
sudo systemctl start vta-{xvfb,xfce,x11vnc,websockify,agent-s3,orchestrator} nginx

# Stop all services
sudo systemctl stop vta-{xvfb,xfce,x11vnc,websockify,agent-s3,orchestrator} nginx

# Restart backend only
sudo systemctl restart vta-agent-s3 vta-orchestrator

# View logs
sudo journalctl -u vta-agent-s3 -f
sudo journalctl -u vta-orchestrator -f

# Rebuild frontend
cd /opt/vta/frontend
npm run build
sudo systemctl reload nginx

# Re-seed curriculum
python3 -m vta.curriculum.seed_curriculum --file curriculum/linux_basics.json

# Check health
curl http://localhost:5001/health
curl http://localhost:5000/health
```

---

## Support

- **Logs**: `/var/log/nginx/` and `sudo journalctl -u vta-*`
- **Config**: `/opt/vta/.env` and `/etc/systemd/system/vta-*.service`
- **Frontend**: `/opt/vta/frontend/dist/`

**Deployment complete!** 🎉

Access: `http://<your-ec2-ip>`
