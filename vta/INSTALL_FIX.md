# Fix for aws-sdk-bedrock-runtime Install Error

The `aws-sdk-bedrock-runtime` package is **optional** for local testing. Voice features require it, but the UI and workflow work without it.

---

## Quick Fix (Run This)

```bash
# In WSL2 or Linux
cd /mnt/e/ui-agent/vta

# Install all required packages (voice SDK is now optional)
pip3 install -r requirements.txt

# You should see SUCCESS now (no errors)
```

---

## What Changed

✅ **Updated `requirements.txt`** — Commented out optional voice packages:
```
# aws-sdk-bedrock-runtime==0.1.0  ← Now optional
# smithy-aws-core==0.1.0          ← Now optional
```

✅ **Updated `sonic_client.py`** — Gracefully handles missing SDK:
- If SDK not installed → runs in **mock mode**
- Voice features disabled, but everything else works

---

## What Works Without Voice SDK

✅ Full UI (all panels, buttons, progress)
✅ Task progression
✅ Curriculum loading
✅ Session state tracking
✅ Desktop actions (via Agent S3)
✅ Confirmation flow (Yes/No/Repeat)

❌ Voice input (microphone)
❌ Nova Sonic audio output
❌ Speech-to-text transcript

---

## To Enable Voice (Optional)

If you have AWS credentials and want voice features:

```bash
# Install voice SDK manually (if available)
pip3 install aws-sdk-bedrock-runtime smithy-aws-core

# Add credentials to .env
echo "AWS_DEFAULT_REGION=us-east-1" >> .env
echo "AWS_ACCESS_KEY_ID=your-key" >> .env
echo "AWS_SECRET_ACCESS_KEY=your-secret" >> .env

# Restart orchestrator
# Voice features now enabled
```

---

## Continue Testing

```bash
# You should be at this step now:
cd /mnt/e/ui-agent/vta

# Run the install again (should work now)
pip3 install -r requirements.txt

# Continue with test script
bash test_local_linux.sh
```

Access: `http://localhost:3000`

---

**The install should work now!** 🎉
