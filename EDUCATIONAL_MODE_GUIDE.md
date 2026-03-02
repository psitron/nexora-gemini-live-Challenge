# Educational Mode Guide

**Making Your AI Agent Perfect for Teaching Students**

---

## 🎓 Why Educational Mode?

When students learn software (like Excel), they need to **SEE** what to do:
- ❌ **Bad**: Agent uses shortcuts → Students don't see the action
- ✅ **Good**: Agent moves mouse → Students follow visually
- ✅ **Best**: Agent uses BOTH → Students learn multiple methods

---

## 🖱️ Educational Mouse Controller

### What It Does

**Normal Mode (Other Agents):**
```
Action: Click cell A1
Result: *instant teleport* → Click
Students see: Nothing! Cell is suddenly selected
```

**Educational Mode (Your Agent):**
```
Action: Click cell A1
Steps:
1. Mouse moves SLOWLY from current position → A1 (0.8 seconds)
2. Pause (0.3 seconds) - students see the target
3. Click
4. Pause (0.5 seconds) - students see the result

Students see: Full mouse movement path, clear target, clear result
```

---

## 🎯 Key Features

### 1. **Visible Mouse Movement**
```python
# Instead of instant teleport
pyautogui.moveTo(x, y)  # Instant

# Educational mode uses smooth movement
pyautogui.moveTo(x, y, duration=0.8, tween=easeInOutQuad)  # Visible
```

**Students can:**
- Follow the mouse with their eyes
- See where it's going
- Understand the target location
- Learn by watching

---

### 2. **Deliberate Pacing**
```python
MOVEMENT_DURATION = 0.8      # Slow enough to follow
PAUSE_BEFORE_CLICK = 0.3     # See what we're about to click
PAUSE_AFTER_CLICK = 0.5      # See the result
```

**Why this helps:**
- Brain needs time to process
- Too fast = missed learning opportunity
- Too slow = bored students
- 0.8s movement = perfect balance

---

### 3. **Combination Teaching**
```python
# Teaching Excel: SUM function

# Step 1: Mouse to cell (visual)
controller.click_at(100, 200, show_movement=True)
print("Clicking cell C1")

# Step 2: Type formula (keyboard)
type_text("=SUM(A1:A10)")
print("Typing: =SUM(A1:A10)")

# Step 3: Press Enter (shortcut)
press_keys("enter")
print("Pressing: Enter")

# Result: Students learn:
#   - Where to click (visual)
#   - What to type (syntax)
#   - What shortcut to use (efficiency)
```

---

## 📊 Comparison: Shortcuts vs Mouse

### Example: Copy Cell in Excel

**Shortcut-Only Approach:**
```
1. Select cell
2. Ctrl+C
3. Select destination
4. Ctrl+V

Students learn: Shortcuts only
Missing: Where are the menu options?
Problem: If they forget shortcut, they're stuck
```

**Mouse-Only Approach:**
```
1. Click cell
2. Click Edit menu
3. Click Copy
4. Click destination cell
5. Click Edit menu
6. Click Paste

Students learn: Menu locations
Problem: Too slow, not efficient
Missing: Shortcuts for speed
```

**Combined Approach (BEST):**
```
1. Click cell (mouse - visual)
2. Ctrl+C to copy (shortcut - efficient)
3. Click destination (mouse - visual)
4. Ctrl+V to paste (shortcut - efficient)

Students learn:
✅ Where to click
✅ What shortcuts do
✅ How to combine methods
✅ Efficient workflow
```

---

## 🎨 How to Use

### Enable Educational Mode

```python
from execution.educational_mouse_controller import EducationalMouseController

# Create controller in educational mode
controller = EducationalMouseController(educational_mode=True)

# Use for all actions
result = controller.click_at(100, 200, show_movement=True)
```

### Configure Speed

```python
# Adjust movement speed
controller.MOVEMENT_DURATION = 0.8  # Default: good for most students
controller.MOVEMENT_DURATION = 1.2  # Slower: for beginners
controller.MOVEMENT_DURATION = 0.5  # Faster: for advanced students

# Adjust pauses
controller.PAUSE_BEFORE_CLICK = 0.3  # Let students see target
controller.PAUSE_AFTER_CLICK = 0.5   # Let students see result
```

---

## 📚 Example: Teaching Excel

### Task: Sum a Column

**With Educational Mode:**

```python
controller = EducationalMouseController(educational_mode=True)

# Step 1: Click result cell (visible movement)
print("Step 1: Select cell where sum will appear")
controller.click_at(cell_x, cell_y, show_movement=True)
time.sleep(1)  # Let students absorb

# Step 2: Click first cell to sum (visual)
print("Step 2: Click first cell in range")
controller.click_at(start_cell_x, start_cell_y, show_movement=True)
time.sleep(0.5)

# Step 3: Drag to last cell (visual selection)
print("Step 3: Drag to select range")
controller.drag_to(start_cell_x, start_cell_y, end_cell_x, end_cell_y)
time.sleep(1)

# Step 4: Click AutoSum button (visual + shortcut combo)
print("Step 4: Click AutoSum (or use Alt+=)")
controller.click_at(autosum_x, autosum_y, show_movement=True)
print("  Tip: You can also press Alt+=")
time.sleep(1)

# Result: Students learned:
#   - Where sum goes
#   - How to select range
#   - Where AutoSum button is
#   - Shortcut alternative (Alt+=)
```

---

## 🎯 Best Practices for Educational Mode

### 1. **Announce What You're Doing**
```python
print("Now we'll click cell A1")  # Tell them
controller.click_at(x, y)          # Show them
time.sleep(1)                       # Let them process
```

### 2. **Show AND Tell Shortcuts**
```python
print("Clicking cell (you can also press Ctrl+Home)")
controller.click_at(x, y)
print("  Shortcut: Ctrl+Home")
```

### 3. **Highlight Important Areas**
```python
# Use annotations for extra visibility
from core.visual_annotator_adapter import highlight_bbox

print("This is the formula bar - watch closely")
bbox = f"{x},{y},{width},{height}"
highlight_bbox(bbox, duration=2.0)  # Show for 2 seconds
controller.click_at(x, y)
```

### 4. **Combine Methods**
```python
# Example: Format cell as currency
print("Method 1: Using ribbon")
controller.click_at(format_button_x, format_button_y)

time.sleep(1)

print("Method 2: Using shortcut (Ctrl+Shift+$)")
press_keys("ctrl", "shift", "4")  # $ symbol

print("Both methods do the same thing!")
```

---

## ⚙️ Configuration Options

### Movement Speed

```python
# Beginner students (slower)
controller.MOVEMENT_DURATION = 1.2
controller.PAUSE_BEFORE_CLICK = 0.5
controller.PAUSE_AFTER_CLICK = 0.7

# Intermediate students (default)
controller.MOVEMENT_DURATION = 0.8
controller.PAUSE_BEFORE_CLICK = 0.3
controller.PAUSE_AFTER_CLICK = 0.5

# Advanced students (faster)
controller.MOVEMENT_DURATION = 0.5
controller.PAUSE_BEFORE_CLICK = 0.2
controller.PAUSE_AFTER_CLICK = 0.3
```

### Easing Functions

The educational mouse controller uses `pyautogui.easeInOutQuad` by default for smooth, natural movements.

If you want to change the easing:
```python
# Edit educational_mouse_controller.py line 84
# Change: tween=pyautogui.easeInOutQuad
# To one of:

tween=pyautogui.linear          # Linear (constant speed)
tween=pyautogui.easeOutQuad     # Fast start, slow end
tween=pyautogui.easeInQuad      # Slow start, fast end
```

Note: The easing function must be passed directly to avoid Python method binding issues.

---

## 🐛 Fixing Annotation Issues

### Problem: Annotations Inaccurate on Desktop

**Issue:** Red boxes appear in wrong location, especially on desktop vs other windows.

**Causes:**
1. DPI scaling (Windows display settings)
2. Multiple monitors
3. Window borders/title bars
4. Coordinate system differences

**Solutions:**

#### 1. **Fix DPI Scaling**
```python
import ctypes

# Make application DPI-aware
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
except:
    ctypes.windll.user32.SetProcessDPIAware()  # Fallback for Windows < 8.1
```

#### 2. **Account for Window Borders**
```python
# When clicking in a window, account for title bar and borders
def get_window_client_rect(hwnd):
    """Get actual clickable area (excluding title bar and borders)"""
    import win32gui

    rect = win32gui.GetClientRect(hwnd)
    point = win32gui.ClientToScreen(hwnd, (rect[0], rect[1]))

    return {
        'x': point[0],
        'y': point[1],
        'width': rect[2] - rect[0],
        'height': rect[3] - rect[1]
    }
```

#### 3. **Verify Coordinates Before Clicking**
```python
def click_with_verification(x, y):
    """Click with visual verification"""

    # 1. Show annotation
    bbox = f"{x-20},{y-20},40,40"
    highlight_bbox(bbox, duration=1.0)

    # 2. Get current mouse position
    current_x, current_y = pyautogui.position()
    print(f"  Current mouse: ({current_x}, {current_y})")

    # 3. Move mouse to verify position
    controller.move_to(x, y, show_path=True)
    time.sleep(0.5)  # Pause so user can verify

    # 4. Ask for confirmation (in demo mode)
    # input("Position correct? Press Enter to click...")

    # 5. Click
    pyautogui.click()
```

---

## 📈 Student Learning Outcomes

### With Educational Mode:

✅ **Visual Learning**
- Students SEE where to click
- Understand spatial relationships
- Follow along easily

✅ **Multiple Methods**
- Learn mouse navigation
- Learn keyboard shortcuts
- Understand when to use each

✅ **Pace Control**
- Deliberate speed = better comprehension
- Pauses = time to process
- Not overwhelming

✅ **Confidence Building**
- Clear demonstrations
- Reproducible steps
- "I can do that too!"

---

## 🎯 Recommendation

**For teaching students Excel (or any software):**

1. **Use Educational Mode** (`educational_mode=True`)
   - Visible mouse movements
   - Deliberate pacing
   - Clear demonstrations

2. **Combine Mouse + Keyboard**
   - Click to show location (visual)
   - Use shortcuts for speed (efficient)
   - Explain both methods (comprehensive)

3. **Add Annotations**
   - Red boxes show targets
   - Extra visual feedback
   - Clarifies complex actions

4. **Pace Appropriately**
   - Beginners: 1.2s movements, longer pauses
   - Intermediate: 0.8s movements (default)
   - Advanced: 0.5s movements, shorter pauses

5. **Narrate Actions**
   - Print what you're doing
   - Explain why
   - Mention alternatives

---

## 💡 Example Lesson: Excel Basics

```python
from execution.educational_mouse_controller import EducationalMouseController

controller = EducationalMouseController(educational_mode=True)

print("=== Excel Lesson: Creating a Simple Budget ===\n")

# Lesson 1: Enter data
print("Lesson 1: Entering Data")
print("We'll type 'Income' in cell A1")
controller.click_at(cell_a1_x, cell_a1_y, show_movement=True)
type_text("Income")
press_keys("enter")
print("  Tip: Press Enter to move to the next row\n")
time.sleep(2)

# Lesson 2: Format as currency
print("Lesson 2: Formatting as Currency")
print("First, select the cell with the number")
controller.click_at(cell_b1_x, cell_b1_y, show_movement=True)
time.sleep(1)

print("Now we'll click the Currency button in the ribbon")
controller.click_at(currency_button_x, currency_button_y, show_movement=True)
print("  Tip: Shortcut is Ctrl+Shift+$\n")
time.sleep(2)

# Lesson 3: Create a formula
print("Lesson 3: Writing a Formula")
print("Click the cell where the sum should appear")
controller.click_at(sum_cell_x, sum_cell_y, show_movement=True)
time.sleep(1)

print("Type the formula: =SUM(B1:B10)")
type_text("=SUM(B1:B10)")
print("  This adds all values from B1 to B10")
time.sleep(1)

print("Press Enter to calculate")
press_keys("enter")
print("  Tip: You can also press Alt+= for quick sum\n")
time.sleep(2)

print("=== Lesson Complete! ===")
print("You learned:")
print("  ✓ How to enter data")
print("  ✓ How to format cells")
print("  ✓ How to write formulas")
print("  ✓ Useful shortcuts")
```

---

## ✅ Summary

**Key Points:**

1. **Educational mode shows movements** - students can follow
2. **Combine mouse + keyboard** - comprehensive learning
3. **Deliberate pacing** - 0.8s movements, pauses between actions
4. **Visual feedback** - annotations + movement = clear demonstrations
5. **Explain alternatives** - show GUI + mention shortcuts

**For Excel teaching specifically:**
- Show where buttons are (mouse)
- Show what shortcuts do (keyboard)
- Explain both methods
- Let students choose their preferred method

**This makes your agent the BEST teaching tool!** 🎓

---

*Your students will learn better because they can SEE and UNDERSTAND every action!*
