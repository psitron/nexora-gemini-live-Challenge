# Example Tasks to Test Your Agent

Quick copy-paste examples you can run right now!

---

## 🟢 File Operations (Always Work - No API Key Needed)

### Example 1: Create a Simple File (30 seconds)

```bash
python -c "from core.agent_loop import AgentLoop; import tempfile, os; agent = AgentLoop(); result = agent.run(f'Create a file at {os.path.join(tempfile.gettempdir(), \"hello.txt\")} with content: Hello from AI Agent!'); print(f'Status: {result.goal_status}'); print(f'Steps: {result.steps_executed}')"
```

**What it does:** Creates a text file with a greeting message

**How to verify:**
```bash
# Windows
type %TEMP%\hello.txt

# macOS/Linux
cat /tmp/hello.txt
```

---

### Example 2: Create Multiple Files (1 minute)

```bash
python -c "from core.agent_loop import AgentLoop; import tempfile, os; agent = AgentLoop(); base = os.path.join(tempfile.gettempdir(), 'test_project'); result = agent.run(f'Create directory {base}, then create files: {base}/readme.txt with \"Project Readme\", {base}/notes.txt with \"Project Notes\", {base}/todo.txt with \"Task List\"'); print(f'Status: {result.goal_status}')"
```

**What it does:** Creates a project folder with 3 text files

**How to verify:**
```bash
# Windows
dir %TEMP%\test_project

# macOS/Linux
ls /tmp/test_project
```

---

### Example 3: Shopping List (1 minute)

```bash
python -c "from core.agent_loop import AgentLoop; import tempfile, os; agent = AgentLoop(); file = os.path.join(tempfile.gettempdir(), 'shopping.txt'); result = agent.run(f'Create a shopping list at {file} with these items: Milk, Bread, Eggs, Butter'); print(f'Status: {result.goal_status}')"
```

**What it does:** Creates a shopping list file

**How to verify:**
```bash
# Windows
type %TEMP%\shopping.txt

# macOS/Linux
cat /tmp/shopping.txt
```

---

### Example 4: Contact Information (1 minute)

```bash
python -c "from core.agent_loop import AgentLoop; import tempfile, os; agent = AgentLoop(); file = os.path.join(tempfile.gettempdir(), 'contacts.txt'); result = agent.run(f'Create a contact file at {file} with: Name: John Doe, Email: john@example.com, Phone: 555-1234'); print(f'Status: {result.goal_status}')"
```

**What it does:** Creates a contact information file

---

## 🟡 Desktop Automation (Requires L2 - pywinauto on Windows)

### Example 5: Open Notepad (Windows, 30 seconds)

```bash
python -c "from core.agent_loop import AgentLoop; agent = AgentLoop(); result = agent.run('Open Notepad'); print(f'Status: {result.goal_status}')"
```

**What it does:** Opens the Notepad application

**How to verify:** Notepad window should appear on screen

---

### Example 6: Open Notepad and Type (Windows, 1 minute)

```bash
python -c "from core.agent_loop import AgentLoop; agent = AgentLoop(); result = agent.run('Open Notepad, wait 2 seconds, then type: This was written by an AI agent!'); print(f'Status: {result.goal_status}')"
```

**What it does:** Opens Notepad and types a message

**How to verify:** You should see the text in Notepad

⚠️ **Close Notepad manually** when done (don't save)

---

### Example 7: Open Calculator (Windows, 30 seconds)

```bash
python -c "from core.agent_loop import AgentLoop; agent = AgentLoop(); result = agent.run('Open Calculator'); print(f'Status: {result.goal_status}')"
```

**What it does:** Opens Windows Calculator

**How to verify:** Calculator window should appear

---

### Example 8: Open TextEdit (macOS, 30 seconds)

```bash
python -c "from core.agent_loop import AgentLoop; agent = AgentLoop(); result = agent.run('Open TextEdit'); print(f'Status: {result.goal_status}')"
```

**What it does:** Opens TextEdit application

**How to verify:** TextEdit window should appear

---

## 🔵 Interactive Examples (Better Testing Experience)

### Run Interactive Menu (Recommended!)

```bash
python test_real_tasks.py
```

**What it does:** Shows a menu of 7 different examples you can choose from

**Features:**
- Easy-to-use menu
- Detailed descriptions
- Automatic verification
- Safe cleanup after each test

**Examples included:**
1. ✅ Simple File Creation
2. ✅ Multiple Files
3. ✅ File Manipulation
4. ✅ Open Notepad (Windows)
5. ✅ Open TextEdit (macOS)
6. ✅ Open Calculator (Windows)
7. ✅ Organize Files

---

## 📝 Create Your Own Task

Template:
```python
from core.agent_loop import AgentLoop
import tempfile
import os

agent = AgentLoop()

# Your task description
task = """
Your instructions here...
Can be multiple lines
"""

result = agent.run(task)

print(f"Status: {result.goal_status}")
print(f"Steps: {result.steps_executed}")
```

---

## 🎯 Tips for Writing Good Tasks

### ✅ Good Task Examples:

```python
# Specific with paths
"Create a file at C:/temp/test.txt with content: Hello World"

# Clear steps
"First open Notepad, then type 'Hello', then wait 2 seconds"

# Explicit content
"Create a file containing: Line 1, Line 2, Line 3"
```

### ❌ Bad Task Examples:

```python
# Too vague
"Make a file"

# Unclear location
"Create a text file somewhere"

# Ambiguous
"Do something with notepad"
```

---

## 🔧 Troubleshooting

### "Task failed" or "Steps: 0"

**Check:**
1. Is the path valid? (Use `tempfile.gettempdir()` for temp files)
2. Do you have permissions? (Don't use C:\\ root on Windows)
3. Is the task clear enough?

### "Desktop automation not working"

**Fix:**
```bash
# Windows
pip install pywinauto

# macOS
pip install pyobjc-framework-Cocoa pyobjc-framework-ApplicationServices

# Linux
sudo apt-get install python3-pyatspi
pip install PyGObject
```

### "API key errors" during execution

**This is normal if you don't have API keys configured.**

The agent will still work for:
- ✅ File operations (L0)
- ✅ Desktop automation (L2)
- ❌ Vision-based tasks (L5) - needs API key

---

## 📚 More Complex Examples

### Example: Todo List Manager

```python
from core.agent_loop import AgentLoop
import tempfile
import os

agent = AgentLoop()

todo_file = os.path.join(tempfile.gettempdir(), "todos.txt")

task = f"""
Create a todo list at {todo_file} with these tasks:

1. [ ] Buy groceries
2. [ ] Call dentist
3. [ ] Finish project
4. [ ] Send emails

Add a header at the top: "My Todo List - 2026-03-01"
"""

result = agent.run(task)
print(f"Status: {result.goal_status}")

# Check the file
if os.path.exists(todo_file):
    with open(todo_file, 'r') as f:
        print("\nTodo list created:")
        print(f.read())
```

---

### Example: Meeting Notes

```python
from core.agent_loop import AgentLoop
import tempfile
import os

agent = AgentLoop()

notes_file = os.path.join(tempfile.gettempdir(), "meeting_notes.txt")

task = f"""
Create meeting notes at {notes_file} with:

Meeting Notes - March 1, 2026
================================

Attendees:
- John Smith
- Jane Doe
- AI Agent (note taker)

Topics Discussed:
1. Project status
2. Next milestones
3. Resource allocation

Action Items:
- John: Review proposal
- Jane: Update timeline
- All: Prepare for next meeting
"""

result = agent.run(task)
print(f"Status: {result.goal_status}")
```

---

### Example: Project Structure

```python
from core.agent_loop import AgentLoop
import tempfile
import os

agent = AgentLoop()

project_dir = os.path.join(tempfile.gettempdir(), "my_project")

task = f"""
Create a project structure:

1. Create base directory: {project_dir}

2. Create subdirectories:
   - {project_dir}/src
   - {project_dir}/docs
   - {project_dir}/tests

3. Create files:
   - {project_dir}/README.md with "# My Project"
   - {project_dir}/src/main.py with "# Main application"
   - {project_dir}/docs/notes.txt with "Project documentation"
   - {project_dir}/tests/test.py with "# Tests go here"
"""

result = agent.run(task)
print(f"Status: {result.goal_status}")

# Verify
if os.path.exists(project_dir):
    print("\nProject structure created:")
    for root, dirs, files in os.walk(project_dir):
        level = root.replace(project_dir, '').count(os.sep)
        indent = ' ' * 2 * level
        print(f"{indent}{os.path.basename(root)}/")
        sub_indent = ' ' * 2 * (level + 1)
        for file in files:
            print(f"{sub_indent}{file}")
```

---

## 🚀 Quick Start

**1. Try the simplest example first:**
```bash
python -c "from core.agent_loop import AgentLoop; import tempfile, os; result = AgentLoop().run(f'Create a file at {os.path.join(tempfile.gettempdir(), \"test.txt\")} with content: Hello!'); print(f'Success: {result.goal_status}')"
```

**2. Then try the interactive menu:**
```bash
python test_real_tasks.py
```

**3. Create your own tasks using the templates above!**

---

## 📊 What to Expect

### Typical Output:

```
Plan (2 steps):
  1. Create the file
  2. Verify it exists

--- Step 1/2: Create the file ---
  [1] file_write({'path': 'C:\\temp\\test.txt', 'content': 'Hello!'})
      -> Wrote file C:\temp\test.txt (success=True)

--- Step 2/2: Verify it exists ---
  [1] file_read({'path': 'C:\\temp\\test.txt'})
      -> Read file C:\temp\test.txt (success=True)

Result: SUCCESS
Steps executed: 2

Status: SUCCESS
Steps: 2
```

---

## 🎉 You're Ready!

Start with the **interactive menu**:
```bash
python test_real_tasks.py
```

Or try the **simple one-liners** above!

All examples are safe and use temporary files. Have fun testing your agent! 🤖
