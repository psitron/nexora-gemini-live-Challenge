# Where the Red Box Annotation Appears When Running `python scripts/demo_ai_teacher.py`

When you run **`python scripts/demo_ai_teacher.py`** and press Enter, the demo opens **"Control Panel"**. The red box can appear in **one of two places** depending on which strategy runs.

---

## 1. Strategy 2 (Start menu) – **this is what usually runs**

If the console shows:
- `Strategy 1: Looking for 'Control Panel' on desktop...`
- `✗ Not found on desktop: ...`
- `Strategy 2: Searching in Start menu...`

then the **only annotation** is drawn here:

### Where it appears

- **Monitor:** The monitor that contains your **mouse cursor** at the moment the script runs (after Win+S has opened the Start menu).
- **Position:** **Top‑center of that monitor**, where the Start menu search box is:
  - **Horizontal:** Centered (middle 60% of the monitor width).
  - **Vertical:** About **8% down** from the top of that monitor.
- **Size:** Width = 60% of monitor width, height = 6% of monitor height (minimum 40 px).

So: **one red box around the search box** on whichever screen your cursor is on (e.g. if the cursor is on your middle screen, the box is on the middle screen, top‑center).

**Code path:**  
`demo_ai_teacher.py` → `desktop_click("Control Panel")` → Strategy 2 → `start_menu_helper.search_and_click()` → `search_box_bbox_on_monitor_containing_cursor()` → `highlight_bbox(bbox)`.

**Formula (from `core/monitor_utils.py`):**
- `rect = monitor that contains cursor (left, top, right, bottom)`
- `x = left + (width - w) / 2` with `w = 60% of monitor width`
- `y = top + 8% of monitor height`
- Box size: `w × h` with `h = 6% of monitor height` (min 40 px).

---

## 2. Strategy 1 (Desktop vision) – only if Gemini finds the icon

If the console shows:
- `Strategy 1: Looking for 'Control Panel' on desktop...`
- `Vision found 'Control Panel icon on desktop'`
- `Bbox (denormalized): x,y,w,h`

then the red box is drawn **exactly around the “Control Panel” element** that the vision model found (e.g. a desktop shortcut), at the **pixel coordinates** returned by the model (denormalized to your screen resolution).

- **Monitor:** Whichever monitor contains those coordinates (usually the primary or the one where the desktop is visible).
- **Position:** The exact `(x, y, w, h)` from the vision result.

**Code path:**  
`desktop_click("Control Panel")` → Strategy 1 → `_try_desktop_vision()` → `Level5CloudVisionExecutor.execute(..., perform_click=True)` → `highlight_bbox(denorm_bbox)`.

---

## Summary for `demo_ai_teacher.py`

| What you see in console | Where the red box appears |
|-------------------------|----------------------------|
| Strategy 2 runs (usual) | **One red box:** around the **Start menu search box**, on the **monitor under the cursor**, at **top‑center** of that monitor. |
| Strategy 1 runs (rare)  | **One red box:** around the **“Control Panel”** element (e.g. desktop icon) at the **vision bbox** coordinates. |

So when you run the demo yourself: in the normal case the annotation should appear **around the search box at the top‑center of the monitor where your mouse is**, right after the Start menu opens (Win+S).
