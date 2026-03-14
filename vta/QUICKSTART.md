# VTA Quick Start — 30 Minutes to Live System

Fast track deployment guide. See `DEPLOYMENT_GUIDE.md` for detailed explanations.

---

## Prerequisites (Do First)

1. **AWS Console → IAM → Create Role**
   - Service: EC2
   - Policies: `AmazonDynamoDBFullAccess`, `AmazonBedrockFullAccess`
   - Name: `VTA-EC2-Role`

2. **AWS Console → Bedrock → Model access**
   - Request access: `Amazon Nova Sonic`, `Claude 3 Haiku`

3. **AWS Console → EC2 → Launch Instance**
   - AMI: Ubuntu 22.04
   - Type: `t3.medium` minimum
   - Security group: Allow ports 22, 80, 443
   - IAM role: `VTA-EC2-Role`
   - Note public IP: `3.85.123.45` ← (your IP)

---

## Installation (On Your Local Machine)

```bash
# Upload code to EC2
cd E:\ui-agent
scp -i your-key.pem -r vta ubuntu@3.85.123.45:/home/ubuntu/
```

---

## Setup (On EC2 via SSH)

```bash
# SSH in
ssh -i your-key.pem ubuntu@3.85.123.45

# Move to system location
sudo mv /home/ubuntu/vta /opt/vta
cd /opt/vta

# Make scripts executable
sudo chmod +x scripts/*.sh

# 1. Install packages (5 min)
sudo bash scripts/ec2_setup.sh

# 2. Configure environment
cp .env.example .env
nano .env  # Set AWS_DEFAULT_REGION, save and exit

# 3. Set up services (2 min)
sudo bash scripts/configure_services.sh

# 4. Create DynamoDB tables (1 min)
bash scripts/create_tables.sh us-east-1

# 5. Deploy (5 min)
sudo bash scripts/deploy.sh --local

# 6. Start services (1 min)
sudo systemctl start vta-xvfb vta-xfce vta-x11vnc vta-websockify vta-agent-s3 vta-orchestrator nginx
```

---

## Verify

```bash
# Check services running
systemctl status vta-agent-s3 vta-orchestrator nginx | grep Active
# All should say: "Active: active (running)"

# Test Agent S3
curl http://localhost:5001/health
# Expected: {"status":"healthy","display":":1"}

# Test Orchestrator
curl http://localhost:5000/health
# Expected: {"status":"healthy",...}
```

---

## Access

1. **Open browser:** `http://3.85.123.45` ← (your EC2 public IP)

2. **You should see:**
   - Title: "Virtual Trainer Agent"
   - Status: "Connected" (green, top-right)
   - Left panel: Chat, Tasks, Mic button
   - "Start Tutorial" button

3. **Click "Start Tutorial"**
   - Tasks appear in progress panel
   - Slide viewer loads (right panel)

4. **Click "Click to Speak"**
   - Allow microphone
   - Say "Hello"
   - Hear Nova Sonic respond
   - See transcript in chat

---

## Troubleshooting

### Can't connect to http://3.85.123.45

```bash
# Check security group allows port 80
# EC2 Console → Security Groups → Edit inbound rules
# Add: HTTP, Port 80, Source 0.0.0.0/0
```

### Services won't start

```bash
# View logs
sudo journalctl -u vta-agent-s3 -n 50
sudo journalctl -u vta-orchestrator -n 50

# Common fix: restart in order
sudo systemctl restart vta-xvfb
sleep 2
sudo systemctl restart vta-xfce
sleep 2
sudo systemctl restart vta-agent-s3
sudo systemctl restart vta-orchestrator
```

### DynamoDB access denied

```bash
# Verify IAM role attached
aws sts get-caller-identity

# If fails: EC2 Console → Instance → Actions → Security → Modify IAM role
# Select VTA-EC2-Role → Update
```

### No audio from Nova Sonic

1. Check browser not muted
2. Click mic button again to refresh permissions
3. Check Bedrock model access approved:
   ```bash
   aws bedrock list-foundation-models --region us-east-1 | grep sonic
   ```

---

## Quick Commands

```bash
# Restart backend
sudo systemctl restart vta-agent-s3 vta-orchestrator

# View live logs
sudo journalctl -u vta-orchestrator -f

# Stop all
sudo systemctl stop vta-{xvfb,xfce,x11vnc,websockify,agent-s3,orchestrator}

# Start all
sudo systemctl start vta-{xvfb,xfce,x11vnc,websockify,agent-s3,orchestrator} nginx
```

---

## Next Steps

- **See full guide:** `DEPLOYMENT_GUIDE.md`
- **Add HTTPS:** `sudo certbot --nginx -d yourdomain.com`
- **Upload PDFs:** Create S3 bucket `vta-tutorial-pdfs`
- **Add tutorials:** Edit `curriculum/linux_basics.json`, re-seed

---

**Done!** Access: http://your-ec2-ip
