# Free Task Mode - Example Tasks

Run any task with: `python my_task.py "your task here"`

---

## Easy Tasks (Good for Testing)

### 1. Notepad Tasks
```bash
python my_task.py "open notepad and type hello world"
python my_task.py "open notepad and write a short poem about AI"
python my_task.py "open notepad, type 'Meeting Notes', press enter twice, then type 'Attendees:'"
```

### 2. Calculator Tasks
```bash
python my_task.py "open calculator and calculate 25 times 37"
python my_task.py "open calculator and add 123 plus 456"
python my_task.py "open calculator, calculate 100 divided by 4"
```

### 3. Paint Tasks
```bash
python my_task.py "open paint"
python my_task.py "open paint and draw a red circle"
python my_task.py "open paint, select the pencil tool, and draw a line"
```

### 4. File Explorer Tasks
```bash
python my_task.py "open file explorer and navigate to Documents folder"
python my_task.py "open file explorer and show the Desktop folder"
python my_task.py "open file explorer, create a new folder called Test"
```

---

## Medium Tasks

### 5. Web Search Tasks
```bash
python my_task.py "open edge browser and search for weather forecast"
python my_task.py "open chrome and go to youtube.com"
python my_task.py "search google for python tutorials"
```

### 6. Settings Tasks
```bash
python my_task.py "open windows settings"
python my_task.py "open windows settings and go to display settings"
python my_task.py "check the current time and date"
```

### 7. Multi-Step Tasks
```bash
python my_task.py "open notepad, type your name is Claude, save the file as test.txt"
python my_task.py "open calculator, add 50 plus 50, then multiply by 2"
python my_task.py "open paint, draw a square, then change the color to blue"
```

---

## Advanced Tasks

### 8. Excel Tasks
```bash
python my_task.py "open excel, create a blank workbook, and type Income in cell A1"
python my_task.py "open excel, make a simple budget with categories: Rent, Food, Transport"
```

### 9. Word Tasks
```bash
python my_task.py "open word and write a short paragraph about technology"
python my_task.py "open word, type a letter header with Name, Address, Date"
```

### 10. File Management
```bash
python my_task.py "create a new folder on desktop called Projects"
python my_task.py "open notepad, type hello, save as test.txt on desktop"
```

---

## Creative Tasks

### 11. Fun Tasks
```bash
python my_task.py "open notepad and write a haiku about computers"
python my_task.py "open calculator and find the answer to life, the universe, and everything"
python my_task.py "open paint and draw a smiley face"
```

### 12. Information Gathering
```bash
python my_task.py "what is the current time?"
python my_task.py "search for today's news headlines"
python my_task.py "find information about Python programming"
```

---

## Testing Different Features

### Test Vision Detection
```bash
python my_task.py "click on the start menu"
python my_task.py "find and click the search box"
```

### Test Typing
```bash
python my_task.py "open notepad and type: The quick brown fox jumps over the lazy dog"
```

### Test Keyboard Shortcuts
```bash
python my_task.py "open notepad, type hello, press Ctrl+A to select all, then press Ctrl+C to copy"
```

### Test Multi-Window
```bash
python my_task.py "open notepad and calculator at the same time"
python my_task.py "open two notepad windows"
```

---

## How to Use

1. **Basic usage:**
   ```bash
   python my_task.py "open notepad and write a poem"
   ```

2. **Check logs after:**
   ```bash
   ls -lt logs/ | head -1
   ```

3. **View HTML report:**
   ```bash
   start logs/<latest>/execution_report.html
   ```

4. **View screenshots:**
   ```bash
   ls logs/<latest>/screenshots/
   ```

---

## Tips

- **Keep tasks simple** - Start with 1-3 step tasks
- **Be specific** - "open notepad and type hello" is better than "use notepad"
- **One app at a time** - Focus on single application tasks first
- **Check logs** - Always review logs to see what went wrong
- **Iterate** - If task fails, try a simpler version

---

## Expected Success Rates (Current Agent)

| Task Type | Success Rate | Notes |
|-----------|--------------|-------|
| Open apps | 70% | Usually works |
| Type text | 80% | Works well |
| Simple calculations | 60% | Calculator detection OK |
| Multi-step (2-3 steps) | 50% | Gets stuck sometimes |
| Complex tasks (5+ steps) | 30% | Often stops early |

---

## Common Issues

1. **"open_search failed"** - Agent couldn't open Windows search
   - Try: "open notepad" directly instead of "search for notepad"

2. **"click_text failed"** - Couldn't find text on screen
   - Check screenshots to see what agent was looking at
   - Text might not be visible or OCR can't read it

3. **"Stopped after 3 consecutive failures"** - Agent got stuck
   - This is expected behavior (prevents infinite loops)
   - Task might be too complex or ambiguous

4. **Task completes but result is wrong** - Agent misunderstood task
   - Be more specific in task description
   - Break into smaller subtasks

---

## Quick Test Suite

Run these to verify agent is working:

```bash
# Test 1: Basic app opening
python my_task.py "open notepad"

# Test 2: Typing
python my_task.py "open notepad and type hello"

# Test 3: Multi-step
python my_task.py "open calculator and add 5 plus 5"

# Test 4: File operation
python my_task.py "open file explorer"
```

If all 4 tests work, agent is functioning correctly!
