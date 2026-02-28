## Hybrid AI Agent – First Task (Hello World)

This task validates that the skeleton is wired up correctly **before** you start implementing the detailed modules from the PRD.

It exercises:
- The project scaffold and folder layout
- The `.env` configuration
- Python dependencies
- A real Claude API call through `verify_setup.py`

---

### 1. Create and activate a virtual environment

From `E:\ui-agent`:

```bash
python -m venv .venv
.venv\Scripts\activate
```

Then install baseline dependencies:

```bash
pip install --upgrade pip
pip install anthropic google-generativeai playwright pywinauto mss opencv-python pillow imagehash deepdiff gradio python-dotenv
```

(You can refine versions later into `requirements.txt`.)

---

### 2. Generate the scaffold

From `E:\ui-agent`:

```bash
python scaffold.py
```

You should see `Scaffold complete.` and new folders such as `core/`, `config/`, `perception/`, etc.

---

### 3. Create your `.env`

Copy the template and fill in real values:

```bash
copy .env.template .env
```

Edit `.env` and set:
- `ANTHROPIC_API_KEY` (required for the first smoke test)
- `ANTHROPIC_TASK_MODEL` / `ANTHROPIC_EXECUTION_MODEL` (or keep defaults)
- `GEMINI_API_KEY` / `GEMINI_VISION_MODEL` if you plan to test vision later
- Any path overrides you care about

You do **not** need to have Gemini/Qwen running for this first task; only the Claude key is required for the smoke test.

---

### 4. Run the setup verifier

From `E:\ui-agent`:

```bash
python verify_setup.py
```

Expected outcome for a successful “hello world”:
- Python version is 3.11+
- Most packages import (you can ignore optional ones for now if you wish)
- Directories and key files exist
- Environment variables are present
- The final line shows: **“Claude hello-world call succeeded.”**

If any checks fail, fix them and re-run until the script exits with code 0.

---

### 5. Open in Cursor and start Phase 1

Once `verify_setup.py` passes:
1. Open `E:\ui-agent` in Cursor.
2. Ensure `.cursorrules` exists at the repo root (if empty, paste the v5.0 rules from the PRD).
3. Use the PRD’s Phase 1 prompts to implement:
   - `config/settings.py` (load `.env` and expose config objects)
   - `core/state_model.py` with `dirty_flag` and `NormalisedEnvironment` field
   - A minimal `main.py` that loads settings and instantiates `StateModel`

Your second “hello world” is:
- Run `python -m main` (or equivalent entry point) and see it print that configuration loaded and `StateModel` initialised successfully.

