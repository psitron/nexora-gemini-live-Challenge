# How My AI Agent Works - Complete Block Diagram

**Visual explanation of the entire system architecture**

---

## 🎯 High-Level Overview

```
USER INPUT (Natural Language Goal)
         ↓
    VISION AGENT
         ↓
   [Vision Loop with Logging]
         ↓
  ACTIONS EXECUTED
         ↓
 DETAILED LOGS CREATED
```

---

## 📊 Complete System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER                                      │
│                                                                   │
│  "Open Excel and create a budget with SUM formula"              │
└───────────────────────────────┬───────────────────────────────────┘
                                │
                                ↓
┌─────────────────────────────────────────────────────────────────┐
│                   VISION AGENT LOGGED                            │
│  (core/vision_agent_logged.py)                                  │
│                                                                   │
│  • Initializes DetailedLogger                                   │
│  • Captures initial screenshot                                  │
│  • Runs vision loop                                             │
│  • Logs every step                                              │
│  • Generates HTML report                                        │
└───────────────────────────────┬───────────────────────────────────┘
                                │
                                ↓
┌─────────────────────────────────────────────────────────────────┐
│                     VISION LOOP (Main)                           │
│  Runs up to MAX_STEPS (default: 30)                            │
│                                                                   │
│  For each step:                                                  │
│    1. Capture screenshot BEFORE                                 │
│    2. Send to Vision AI                                         │
│    3. Get action decision                                       │
│    4. Execute action                                            │
│    5. Capture screenshot AFTER                                  │
│    6. Log everything                                            │
│    7. Repeat                                                    │
└───────────────────────────────┬───────────────────────────────────┘
                                │
                                ↓
        ┌───────────────────────┴───────────────────────┐
        │                                               │
        ↓                                               ↓
┌─────────────────┐                            ┌─────────────────┐
│  PERCEPTION     │                            │  DECISION       │
│  (Step 1-2)     │                            │  (Step 3)       │
│                 │                            │                 │
│  Screenshot     │                            │  Vision AI      │
│  Capture        │                            │  Analysis       │
│                 │                            │                 │
│  • MSS library  │────Screenshot─────────────>│  • Gemini Flash│
│  • Monitor 3    │    (resized to            │  • Amazon Nova  │
│  • Full desktop │     1024px wide)           │  • Qwen2-VL     │
└─────────────────┘                            │                 │
                                               │  Returns:       │
                                               │  - action_type  │
                                               │  - target       │
                                               │  - hint_x,hint_y│
                                               │  - description  │
                                               └─────────┬───────┘
                                                         │
                                                         ↓
                                               ┌─────────────────┐
                                               │  ACTION TYPES   │
                                               │                 │
                                               │  • click_text   │
                                               │  • type_text    │
                                               │  • keyboard     │
                                               │  • scroll       │
                                               │  • drag         │
                                               │  • open_search  │
                                               │  • run_command  │
                                               │  • wait         │
                                               │  • done         │
                                               └─────────┬───────┘
                                                         │
                                                         ↓
                                               ┌─────────────────────┐
                                               │  EXECUTION (Step 4) │
                                               │                     │
                                               │  Educational Mouse  │
                                               │  Controller         │
                                               │                     │
                                               │  • Visible movement │
                                               │  • 0.8s duration    │
                                               │  • Smooth easing    │
                                               │  • Pauses           │
                                               └──────────┬──────────┘
                                                          │
                                                          ↓
                                    ┌─────────────────────┴─────────────────────┐
                                    │                                           │
                           ┌────────┴────────┐                     ┌────────────┴─────────┐
                           │  OCR FINDER     │                     │  PYAUTOGUI           │
                           │                 │                     │                      │
                           │  Find text on   │                     │  • moveTo(x,y)       │
                           │  screen:        │                     │  • click()           │
                           │  • Windows OCR  │                     │  • drag()            │
                           │  • Coordinates  │                     │  • scroll()          │
                           │  • Validation   │                     │  • press()           │
                           └────────┬────────┘                     └──────────────────────┘
                                    │
                                    ↓
                           ┌────────────────┐
                           │  ANNOTATIONS   │
                           │                │
                           │  Red boxes     │
                           │  show targets  │
                           └────────────────┘
```

---

## 🔄 Detailed Step-by-Step Flow

### STEP 1: Initialize

```
VisionAgentLogged.__init__()
    │
    ├──> super().__init__()  # VisionAgent initialization
    │     │
    │     ├──> Load vision model (Gemini/Nova)
    │     ├──> Initialize educational mouse controller
    │     ├──> Setup monitor detection (PRIMARY_MONITOR=3)
    │     └──> Calculate screenshot scale factor
    │
    └──> Setup logging (DetailedLogger)
```

### STEP 2: Run Method Called

```
agent.run(goal)
    │
    ├──> Initialize DetailedLogger
    │     │
    │     ├──> Create logs/ directory
    │     ├──> Timestamp: YYYYMMDD_HHMMSS
    │     └──> Create screenshots/ subdirectory
    │
    ├──> Capture initial screenshot
    │     │
    │     └──> Log to: step_0_initialization.png
    │
    └──> Start _run_with_logging(goal)
```

### STEP 3: Vision Loop (Main Loop)

```
For each step (up to MAX_STEPS=30):

    1. CAPTURE BEFORE
       │
       ├──> capture_selected_monitor()
       │     │
       │     ├──> MSS library captures Monitor 3
       │     ├──> Returns PIL Image
       │     └──> Store as screenshot_before
       │
       └──> Save to: screenshots/step_N_before.png


    2. RESIZE FOR AI
       │
       ├──> _resize_screenshot(screenshot)
       │     │
       │     ├──> Calculate scale factor (width → 1024px)
       │     ├──> Maintain aspect ratio
       │     └──> Return smaller image for AI
       │
       └──> This saves tokens and API costs


    3. ASK VISION AI
       │
       ├──> _ask_vision_ai(small_screenshot, goal, history)
       │     │
       │     ├──> Build prompt:
       │     │     "You are a desktop automation agent.
       │     │      Goal: {goal}
       │     │      Previous actions: {history}
       │     │      What should I do next?"
       │     │
       │     ├──> Send to vision model:
       │     │     │
       │     │     ├──> Gemini Flash (gemini-3-flash-preview)
       │     │     │   OR
       │     │     └──> Amazon Nova (us.amazon.nova-2-lite)
       │     │
       │     ├──> Parse response:
       │     │     {
       │     │       "action": "click_text",
       │     │       "target": "Excel",
       │     │       "hint_x": 450,
       │     │       "hint_y": 320,
       │     │       "description": "Click Excel icon"
       │     │     }
       │     │
       │     └──> Return VisionAction object
       │
       └──> If AI fails 3 times → abort


    4. SCALE COORDINATES
       │
       ├──> AI gave coordinates in resized image (1024px wide)
       ├──> Need to map back to actual screen (1920px wide)
       │     │
       │     └──> actual_x = hint_x * scale_factor
       │          actual_y = hint_y * scale_factor
       │
       └──> Add monitor offset (for multi-monitor setups)


    5. EXECUTE ACTION
       │
       ├──> _execute_action(action)
       │     │
       │     ├──> Based on action_type:
       │     │     │
       │     │     ├──> "click_text" → Find text with OCR, click it
       │     │     │     │
       │     │     │     ├──> OCR finds all "Excel" on screen
       │     │     │     ├──> Use hint to pick closest match
       │     │     │     ├──> Draw red box annotation
       │     │     │     └──> Educational mouse click
       │     │     │
       │     │     ├──> "type_text" → Type string
       │     │     │     │
       │     │     │     └──> pyautogui.write(text)
       │     │     │
       │     │     ├──> "keyboard" → Press keys
       │     │     │     │
       │     │     │     └──> pyautogui.press(key)
       │     │     │
       │     │     ├──> "scroll" → Scroll up/down
       │     │     │     │
       │     │     │     └──> pyautogui.scroll(amount)
       │     │     │
       │     │     └──> "done" → Task complete!
       │     │
       │     └──> Return success/failure
       │
       └──> Educational mode adds:
             • Visible 0.8s mouse movements
             • 0.3s pause before click
             • 0.5s pause after click


    6. CAPTURE AFTER
       │
       ├──> Wait 0.5s for UI to settle
       ├──> capture_selected_monitor()
       └──> Save to: screenshots/step_N_after.png


    7. LOG EVERYTHING
       │
       ├──> logger.log_action(
       │      action_name,
       │      parameters,
       │      result,
       │      screenshot_before,
       │      screenshot_after
       │    )
       │     │
       │     ├──> Add to execution_log.json
       │     ├──> Add to execution_log.txt
       │     └──> Save screenshots
       │
       └──> Continue to next step


    8. CHECK IF DONE
       │
       ├──> If action_type == "done" → SUCCESS!
       ├──> If steps >= MAX_STEPS → TIMEOUT
       └──> Else → Continue loop
```

### STEP 4: Finalize

```
After loop completes:
    │
    ├──> Capture final screenshot
    │
    ├──> Generate HTML report
    │     │
    │     ├──> execution_report.html
    │     │     │
    │     │     ├──> Dashboard (summary stats)
    │     │     ├──> Every step with details
    │     │     ├──> Embedded screenshots
    │     │     └──> Beautiful styling
    │     │
    │     ├──> execution_log.txt (human-readable)
    │     └──> execution_log.json (machine-readable)
    │
    └──> Print path to HTML report
```

---

## 🎓 Educational Mouse Controller Detail

```
When action requires mouse movement:

Educational Mode ENABLED (default):
    │
    ├──> Current position: (100, 100)
    ├──> Target position: (500, 300)
    │
    ├──> Calculate movement path
    │     │
    │     └──> Easing function: easeInOutQuad
    │           (smooth acceleration/deceleration)
    │
    ├──> Move smoothly over 0.8 seconds
    │     │
    │     ├──> Student watches cursor move
    │     ├──> Natural, human-like movement
    │     └──> Can follow with eyes
    │
    ├──> Pause 0.3s before clicking
    │     │
    │     └──> Let student see target
    │
    ├──> Click
    │
    └──> Pause 0.5s after clicking
          │
          └──> Let student see result


Educational Mode DISABLED (fast mode):
    │
    ├──> Instant teleport to target
    ├──> Immediate click
    └──> No pauses (production speed)
```

---

## 📸 Screenshot Logging Flow

```
Every single step captures 2 screenshots:

BEFORE Screenshot:
    │
    ├──> Captures desktop state BEFORE action
    ├──> Shows what agent sees
    └──> Saved to: screenshots/step_N_before.png


ACTION Execution:
    │
    └──> (Mouse moves, clicks, types, etc.)


AFTER Screenshot:
    │
    ├──> Captures desktop state AFTER action
    ├──> Shows result of action
    └──> Saved to: screenshots/step_N_after.png


Both screenshots embedded in HTML report:
    │
    └──> Click any step → see before/after comparison
```

**Example for 10-step task:**
- 1 initial screenshot
- 10 before screenshots
- 10 after screenshots
- 1 final screenshot
- **Total: 22 screenshots!** ✅

---

## 🎯 Action Type Details

### 1. click_text
```
"Find 'Excel' and click it"
    │
    ├──> OCR finds all "Excel" text on screen
    ├──> Multiple matches found:
    │     • Taskbar (100, 1000)
    │     • Desktop icon (450, 320)
    │     • Recent file (800, 500)
    │
    ├──> AI hint: (450, 320)
    ├──> Pick closest match to hint
    ├──> Draw red box on desktop icon
    └──> Educational mouse clicks center
```

### 2. type_text
```
"Type 'Income' in cell"
    │
    ├──> Click already positioned cursor
    └──> pyautogui.write("Income")
          │
          └──> Student sees each character typed
```

### 3. keyboard
```
"Press Enter"
    │
    └──> pyautogui.press("enter")
          │
          └──> Executes keyboard shortcut
```

### 4. scroll
```
"Scroll down"
    │
    ├──> Move mouse to hint position
    └──> pyautogui.scroll(-3)  # Negative = down
```

### 5. drag
```
"Select cells A1 to A10"
    │
    ├──> Start: (start_x, start_y)
    ├──> End: (end_x, end_y)
    │
    └──> educational_mouse_controller.drag_to(
           start_x, start_y, end_x, end_y
         )
         │
         ├──> Move to start (0.8s)
         ├──> Hold left button
         ├──> Drag to end (0.8s)
         └──> Release button
```

---

## 🗂️ File Structure

```
E:\ui-agent\
│
├── core/
│   ├── vision_agent.py          ← Base agent (no logging)
│   ├── vision_agent_logged.py   ← Logged version ⭐
│   ├── detailed_logger.py       ← Logging system
│   ├── vision_models.py         ← Gemini/Nova adapters
│   └── ocr_finder.py            ← Text finding with OCR
│
├── execution/
│   └── educational_mouse_controller.py  ← Visible movements
│
├── perception/
│   └── visual/
│       └── screenshot.py        ← Screen capture
│
├── logs/                        ← Created at runtime
│   └── YYYYMMDD_HHMMSS/
│       ├── execution_report.html  ⭐
│       ├── execution_log.txt
│       ├── execution_log.json
│       └── screenshots/
│           ├── step_1_before.png
│           ├── step_1_after.png
│           └── ...
│
└── test_educational_excel.py    ← Demo script
```

---

## 🔧 Configuration

```
.env file controls behavior:

EDUCATIONAL_MODE=true
    │
    ├──> Enables visible mouse movements
    ├──> 0.8s duration
    ├──> Pauses before/after clicks
    └──> Perfect for teaching students

EDUCATIONAL_MODE=false
    │
    ├──> Instant movements
    ├──> No pauses
    └──> Production speed


VISION_PROVIDER=gemini
    │
    └──> Uses Gemini Flash for vision analysis


PRIMARY_MONITOR=3
    │
    └──> Captures from third monitor (right)


DEBUG_MODE=true
    │
    └──> Saves extra debug screenshots
```

---

## 📊 Complete Data Flow Summary

```
1. USER TYPES GOAL
   "Open Excel and create budget"

2. AGENT INITIALIZES
   • Loads vision model (Gemini Flash)
   • Creates logger
   • Captures initial screenshot

3. VISION LOOP STARTS
   │
   └──> For each step:
         │
         ├──> Capture BEFORE
         ├──> Resize for AI (1024px)
         ├──> Send to vision AI
         ├──> AI decides action
         ├──> Scale coordinates
         ├──> Execute action (with visible movement)
         ├──> Capture AFTER
         ├──> Log everything
         └──> Repeat

4. TASK COMPLETES
   • AI says "done"
   • Capture final screenshot
   • Generate HTML report

5. USER OPENS REPORT
   • Sees every step
   • Sees every screenshot
   • Understands what happened
```

---

## 🎉 Summary

### What Makes This System Special:

✅ **Vision-Based**: AI understands screens like humans do
✅ **Educational Mode**: Visible movements for teaching
✅ **Comprehensive Logging**: Every screenshot, every action
✅ **Multi-Model Support**: Gemini, Amazon Nova, Qwen2-VL
✅ **Smart Coordination**: OCR + Vision AI + Hints
✅ **Beautiful Reports**: HTML with embedded images
✅ **Configurable**: Educational vs. fast mode
✅ **Cross-Platform**: Works on Windows/Mac/Linux (mostly)

### Data Flow:
1. Natural language → Vision AI
2. Vision AI → Action decision
3. Action → Educational execution
4. Results → Detailed logs
5. Logs → HTML report

### Screenshot Logging:
- **2 per step** (before/after)
- **Plus** initial and final
- **All saved** to screenshots/
- **All embedded** in HTML report

**You can see EVERYTHING your agent does!** 📊🎓

---

*Your agent is a complete teaching tool with full transparency!* ✨
