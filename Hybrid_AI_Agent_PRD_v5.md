**HYBRID AI AGENT**

**PRODUCT REQUIREMENTS DOCUMENT**

*v5.0 · Final Complete Edition*

Five Rounds of Technical Review · Production-Grade · Ready to Build

  ------------------- ----------------- ------------- ---------------- ---------------- ------------
  **NormEnvSchema**   **TemplateCfg**   **VLM         **dirty_flag**   **IDEMPOTENT**   **Affinity
                                        Grounding**                                     Map**

  ------------------- ----------------- ------------- ---------------- ---------------- ------------

**Includes: Full Tool Stack · 7-Phase Build Plan · 17 Cursor Prompts ·
.cursorrules · v5.0 Additions**

Version: 5.0 --- Final Complete Edition

Status: Ready to Build

Date: February 2026

Classification: Internal

**1. What\'s New in v5.0**

Version 5.0 is the final synthesis of five rounds of technical review.
It adds six targeted additions that close the last remaining gaps in the
v4.0 architecture --- no structural changes, no new layers, only precise
upgrades to existing modules.

  -----------------------------------------------------------------------
  *All six v5.0 additions are targeted improvements to existing modules.
  Nothing in v4.0 is changed or removed --- these are additive upgrades
  only.*

  -----------------------------------------------------------------------

**1.1 Five-Round Review Summary**

  ----------- --------------------- -------------------------------------------
  **Round**   **Key Critique        **What Was Fixed**
              Source**              

  v1.0        Initial design        Hybrid loop, safety layer, execution
                                    hierarchy, structured perception first

  v2.0        Review round 1        Verifier concept, backtracking stack,
                                    programmatic L0, UI memory, plan batching,
                                    adapters

  v3.0        Review round 2        Verifier internals, State Graph (tree),
                                    ElementID, LatencyPolicy, DeadlockDetector,
                                    Trajectory schema

  v4.0        Review round 3        GoalSpecCompiler, TransactionManager, Typed
                                    Contracts, EvidencePlanner, State.diff(),
                                    Interactive HiL

  v5.0        Review round 4        NormalisedEnvironmentSchema,
                                    TemplateMatchingConfig, VLM grounding
                                    prompt, StateModel dirty_flag, IDEMPOTENT
                                    risk class, Tool Affinity Map
  ----------- --------------------- -------------------------------------------

**1.2 Six v5.0 Additions at a Glance**

  ----------------------------- ---------------------------------- ------------------- ----------------
  **Addition**                  **Affects**                        **What It Fixes**   **Impact**

  NormalisedEnvironmentSchema   StateModel, Planner                Planner was         Planner gets one
                                                                   reasoning over      unified JSON
                                                                   heterogeneous raw   schema --- more
                                                                   DOM + UI tree +     reliable tool
                                                                   visual data         selection

  TemplateMatchingConfig        execution/level3_pattern.py        OpenCV template     Reliable pattern
                                                                   matching was        matching with
                                                                   underspecified ---  defined storage,
                                                                   no storage,         scaling, and
                                                                   scaling, or         multi-monitor
                                                                   confidence rules    policy

  VLM Grounding Prompt Format   execution/level4_local_vision.py   Qwen2-VL received   Precise prompt
                                                                   raw OmniParser      format reduces
                                                                   output --- no       hallucinated
                                                                   structured          coordinates by
                                                                   grounding prompt    grounding VLM in
                                                                                       labelled
                                                                                       elements

  StateModel dirty_flag         core/state_model.py                DOM and UI tree     \~30-50% loop
                                                                   re-queried every    time reduction
                                                                   loop iteration      by skipping
                                                                   regardless of       perception when
                                                                   screen change       screen hash
                                                                                       unchanged

  IDEMPOTENT risk class         config/tool_contracts.py,          No way to mark      Clean retry
                                safety/classifier.py               actions             logic ---
                                                                   safe-to-repeat ---  idempotent
                                                                   all retries treated actions retry
                                                                   as risky            freely without
                                                                                       compensating
                                                                                       action

  Tool Affinity Map             latency_policy/policy.py           LatencyPolicy tried Action-type
                                                                   all levels in order routing reduces
                                                                   for every action    unnecessary
                                                                   type                level
                                                                                       escalations and
                                                                                       latency
  ----------------------------- ---------------------------------- ------------------- ----------------

**2. Six v5.0 Additions --- Full Specification**

**2.1 NormalisedEnvironmentSchema**

The StateModel currently stores three separate raw data structures:
Playwright DOM snapshot (HTML dict), pywinauto UI tree (element list),
and visual OmniParser output (bbox list). The Planner must reason over
all three heterogeneous formats simultaneously. The
NormalisedEnvironmentSchema unifies all three into one common JSON
structure that the Planner, Verifier, and EvidencePlanner all reason
over.

  -----------------------------------------------------------------------
  *Root cause: Without normalisation, the Planner receives a DOM that
  says \'#submit-btn\' exists, a UI tree that says \'Submit Button\'
  exists, and visual data that says a button at \[450,320\] exists ---
  and cannot tell these are the same element. Normalisation collapses
  them.*

  -----------------------------------------------------------------------

**2.1.1 NormalisedElement Schema**

> \@dataclass
>
> class NormalisedElement:
>
> id: str \# stable UUID assigned on first normalisation
>
> label: str \# human-readable, e.g. \'Submit Button\'
>
> element_type: str \#
> \'button\'\|\'input\'\|\'link\'\|\'text\'\|\'image\'\|\'container\'
>
> text_content: str \| None \# visible text in element
>
> state: str \# \'enabled\'\|\'disabled\'\|\'checked\'\|\'hidden\'
>
> sources: list\[str\] \# which sources provided this:
> \[\'dom\',\'ui_tree\',\'visual\'\]
>
> dom_locator: str \| None \# CSS/XPath selector if dom source present
>
> ui_tree_id: str \| None \# automation_id if ui_tree source present
>
> bbox: str \| None \# \'x,y,w,h\' if visual source present
>
> confidence: float \# merged confidence across sources
>
> children: list\[\'NormalisedElement\'\] = field(default_factory=list)

**2.1.2 NormalisedEnvironment Schema**

> \@dataclass
>
> class NormalisedEnvironment:
>
> window_title: str
>
> window_type: str \#
> \'browser\'\|\'desktop_app\'\|\'dialog\'\|\'unknown\'
>
> current_url: str \| None \# browser only
>
> app_name: str
>
> elements: list\[NormalisedElement\]
>
> interactive: list\[NormalisedElement\] \# filtered: enabled
> buttons/inputs/links
>
> timestamp: datetime
>
> source_hash: str \# hash of raw sources used to build this

**2.1.3 Normalisation Process**

1.  DOM reader extracts elements with selector, text, type, state

2.  UI tree reader extracts elements with automation_id, name,
    control_type

3.  Visual reader extracts elements with bbox, label (from OmniParser)

4.  Normaliser merges by text similarity + spatial proximity + type
    matching

5.  Merged elements get stable id --- same element across sources gets
    same id

6.  NormalisedEnvironment replaces raw dom_snapshot and ui_elements in
    StateModel

7.  Planner receives NormalisedEnvironment.interactive as its action
    target list

  ------------------ ------------------ ----------------------------------
  **Raw Source**     **Field Mapped     **Merge Strategy**
                     To**               

  DOM selector       dom_locator        Exact --- CSS selector is stable

  UI tree            ui_tree_id         Exact --- automation_id is stable
  automation_id                         

  OmniParser label + label + bbox       Fuzzy text match + spatial overlap
  bbox                                  with DOM/UI tree element

  DOM text content   text_content       DOM text preferred over UI tree
                                        name if both present

  DOM element type   element_type       Mapped: input→input, a→link,
                                        button→button, div→container

  UI tree            element_type       Fallback if DOM type not available
  control_type                          

  Max confidence     confidence         Highest confidence locator wins
  across sources                        
  ------------------ ------------------ ----------------------------------

**2.1.4 How Modules Use NormalisedEnvironment**

  ----------------------------- --------------------- -------------------------------
  **Module**                    **What It Uses**      **Benefit**

  ExecutionPlanner              interactive list      Plans actions against unified
                                                      element list --- no
                                                      source-specific logic

  ElementID.Resolver            dom_locator,          Fills ElementID fallback chain
                                ui_tree_id, bbox      from all three sources
                                                      automatically

  Verifier.ExpectationMatcher   elements list before  Checks element state changes in
                                and after             one schema, not three

  EvidencePlanner               elements list         Declares ProofPoints using
                                                      normalised element ids

  TrajectoryMemory              element id + label    Stable cache key that works
                                                      regardless of which source
                                                      detected it

  DeadlockDetector              interactive count     Detects UI overlays:
                                                      interactive count drops to 0 =
                                                      dialog blocking
  ----------------------------- --------------------- -------------------------------

**2.1.5 New File: perception/normaliser.py**

> class EnvironmentNormaliser:
>
> def normalise(self,
>
> dom: dict \| None,
>
> ui_tree: list \| None,
>
> visual: list \| None,
>
> ) -\> NormalisedEnvironment:
>
> \...
>
> def \_merge_elements(self, dom_els, tree_els, vis_els) -\>
> list\[NormalisedElement\]:
>
> \# 1. Start with DOM elements (most precise selectors)
>
> \# 2. Match UI tree elements by text + type similarity
>
> \# 3. Match visual elements by spatial overlap + label similarity
>
> \# 4. Unmatched sources create new NormalisedElement with partial
> fields
>
> \...
>
> def \_text_similarity(self, a: str, b: str) -\> float:
>
> \# Use difflib.SequenceMatcher --- fast, no dependencies
>
> \...
>
> def \_spatial_overlap(self, bbox1: str, bbox2: str) -\> float:
>
> \# IoU (Intersection over Union) of bounding boxes
>
> \...

**2.2 TemplateMatchingConfig**

The Level 3 OpenCV pattern matching was specified as \'active window
ROI\' but lacked a defined template storage strategy, resolution scaling
policy, confidence thresholds, and multi-monitor handling. Without
these, template matching is unreliable in practice --- different screen
resolutions break cached templates.

**2.2.1 TemplateMatchingConfig Dataclass**

> \@dataclass
>
> class TemplateMatchingConfig:
>
> \# Storage
>
> template_dir: Path \# config: \'./templates/\'
>
> template_format: str \# \'png\' --- lossless only
>
> naming_convention: str \#
> \'{app_name}\_{element_label}\_{resolution}.png\'
>
> \# Resolution policy
>
> capture_resolution: tuple \# (width, height) at capture time
>
> normalise_to: tuple \# (1280, 720) --- all templates normalised to
> this
>
> scale_factors: list \# \[0.75, 1.0, 1.25\] --- try all on match
>
> \# Confidence
>
> min_confidence: float \# 0.80 --- below this = no match
>
> multi_match_threshold: float \# 0.95 --- above this = strong match,
> stop searching
>
> \# ROI
>
> roi_mode: str \# \'active_window\' \| \'full_screen\' \| \'custom\'
>
> roi_padding_px: int \# 20px padding around active window bounds
>
> \# Multi-monitor
>
> monitor_strategy: str \# \'active_only\' \| \'all\' \| \'primary\'
>
> active_monitor_detect: bool \# True --- detect which monitor has
> active window

**2.2.2 Template Storage Strategy**

  --------------- --------------------------- ----------------------------
  **Policy**      **Rule**                    **Reason**

  Format          PNG only --- never JPEG     JPEG compression alters
                                              pixel values, breaks exact
                                              matching

  Normalisation   All templates resized to    Consistent resolution
                  1280x720 before storage     prevents scale mismatch
                                              across machines

  Naming          app_name + element_label +  Allows multiple templates
                  resolution string           per element for different
                                              resolutions

  Capture ROI     Active window bounds + 20px Eliminates background
                  padding                     desktop noise from templates

  Multi-scale     Try 0.75x, 1.0x, 1.25x      Handles DPI differences and
  match           scale factors at match time window size changes

  Invalidation    Template confidence drops   App UI updates break cached
                  below 0.70 after 3          templates --- detect and
                  consecutive misses          invalidate

  Version tagging Template filename includes  Stale templates from old app
                  app version hash            version auto-excluded
  --------------- --------------------------- ----------------------------

**2.2.3 Multi-Monitor Handling**

-   Default: capture active window only --- use pygetwindow to get
    bounds, mss to capture exact region

-   If active_monitor_detect is True: identify which physical monitor
    contains the active window

-   Capture from that monitor only --- prevents mis-coordinates when
    monitors have different resolutions

-   Returned coordinates are always in absolute screen coordinates, not
    monitor-relative

-   Log monitor configuration on startup --- warn if monitors have
    different DPI scaling

**2.3 VLM Grounding Prompt Format**

Qwen2-VL receives a screenshot after OmniParser has labelled UI
elements. Without a structured grounding prompt, the VLM may hallucinate
element positions or confuse elements with similar labels. The grounding
prompt format precisely instructs the VLM using OmniParser\'s output as
structured context.

**2.3.1 Input Pipeline to Qwen2-VL**

8.  MSS captures screenshot of active window (ROI)

9.  Screenshot resized to 1280x720 (Pillow)

10. OmniParser runs on resized screenshot --- outputs labelled elements
    with bounding boxes

11. NormalisedEnvironment built from OmniParser output

12. Grounding prompt assembled from NormalisedEnvironment.interactive +
    task action

13. Screenshot + grounding prompt sent to Qwen2-VL

14. VLM returns element id + action + coordinates

15. Coordinates normalised back to original resolution

**2.3.2 Grounding Prompt Template**

+-----------------------------------------------------------------------+
| SYSTEM:                                                               |
|                                                                       |
| You are a GUI agent. You must identify the exact UI element to        |
| interact with.                                                        |
|                                                                       |
| You will be given:                                                    |
|                                                                       |
| 1\. A screenshot of the current screen                                |
|                                                                       |
| 2\. A list of detected UI elements with their labels and positions    |
|                                                                       |
| 3\. The action you need to perform                                    |
|                                                                       |
| Rules:                                                                |
|                                                                       |
| \- Only reference elements from the provided element list             |
|                                                                       |
| \- Never invent element positions --- use the bbox from the list      |
|                                                                       |
| \- If the target element is not in the list, respond with             |
| ELEMENT_NOT_FOUND                                                     |
|                                                                       |
| \- Return ONLY the JSON response format below --- no other text       |
|                                                                       |
| USER:                                                                 |
|                                                                       |
| Current screen elements (detected by OmniParser):                     |
|                                                                       |
| \[ELEMENT_LIST_JSON\]                                                 |
|                                                                       |
| Example element list format:                                          |
|                                                                       |
| \[                                                                    |
|                                                                       |
| {\"id\": \"el_001\", \"label\": \"Submit Button\", \"type\":          |
| \"button\",                                                           |
|                                                                       |
| \"bbox\": \"450,320,80,30\", \"confidence\": 0.94},                   |
|                                                                       |
| {\"id\": \"el_002\", \"label\": \"Email Input\", \"type\": \"input\", |
|                                                                       |
| \"bbox\": \"200,150,400,40\", \"confidence\": 0.91}                   |
|                                                                       |
| \]                                                                    |
|                                                                       |
| Action to perform: \[ACTION_DESCRIPTION\]                             |
|                                                                       |
| Target element description: \[ELEMENT_DESCRIPTION\]                   |
|                                                                       |
| Respond ONLY with this JSON:                                          |
|                                                                       |
| {                                                                     |
|                                                                       |
| \"element_id\": \"el_001\",                                           |
|                                                                       |
| \"element_label\": \"Submit Button\",                                 |
|                                                                       |
| \"action\": \"click\",                                                |
|                                                                       |
| \"bbox\": \"450,320,80,30\",                                          |
|                                                                       |
| \"click_point\": \"490,335\",                                         |
|                                                                       |
| \"confidence\": 0.94,                                                 |
|                                                                       |
| \"reasoning\": \"Matched \'Submit Button\' to target \'submit form    |
| button\'\"                                                            |
|                                                                       |
| }                                                                     |
|                                                                       |
| If element not found:                                                 |
|                                                                       |
| {\"element_id\": null, \"confidence\": 0.0, \"reasoning\":            |
| \"ELEMENT_NOT_FOUND: \[reason\]\"}                                    |
+-----------------------------------------------------------------------+

**2.3.3 VLM Response Processing**

  ------------------- ------------------------------ -------------------------
  **Response Field**  **How Used**                   **Fallback if Missing**

  element_id          Maps back to NormalisedElement Log warning, use bbox
                      --- updates its bbox           directly

  confidence          If \< vlm_confidence_threshold Default to 0.50
                      (0.60): escalate to L5 cloud   

  bbox                Source of truth for click      Reject --- escalate to L5
                      coordinates                    

  click_point         Centre of bbox --- use as      Calculate from bbox
                      click target                   centre

  reasoning           Logged for debugging and       \'No reasoning provided\'
                      trajectory storage             

  ELEMENT_NOT_FOUND   Trigger L5 cloud vision or     N/A
                      human loop                     
  ------------------- ------------------------------ -------------------------

**2.3.4 VLM Confidence Threshold**

> \# Add to config/latency_thresholds.py
>
> VLM_LOCAL_CONFIDENCE_THRESHOLD = 0.60 \# below this → escalate to L5
> cloud
>
> VLM_CLOUD_CONFIDENCE_THRESHOLD = 0.50 \# below this → escalate to L6
> human
>
> OMNIPARSER_MIN_CONFIDENCE = 0.40 \# discard elements below this

**2.4 StateModel dirty_flag --- Perception Cache**

Every iteration of the agent loop re-queries the DOM and UI tree
regardless of whether the screen has changed. This is the largest single
source of unnecessary latency. A dirty_flag on StateModel skips
perception re-query when the screen hash is unchanged from the previous
iteration.

  -----------------------------------------------------------------------
  *Performance impact: DOM query takes \~15ms, UI tree query takes
  \~20ms. Skipping both when screen is unchanged saves \~35ms per loop
  iteration. For a 50-step task where 60% of steps produce no screen
  change, this saves \~1,050ms total --- over 1 second.*

  -----------------------------------------------------------------------

**2.4.1 dirty_flag Logic**

> class StateModel:
>
> \# NEW fields in v5.0
>
> \_dirty: bool = True \# True = perception re-query needed
>
> \_last_screen_hash: str = \'\' \# hash from previous iteration
>
> def check_and_update_dirty(self, new_screen_hash: str) -\> bool:
>
> \'\'\'
>
> Returns True if re-query needed (screen changed).
>
> Returns False if screen unchanged --- caller should skip perception.
>
> \'\'\'
>
> if new_screen_hash == self.\_last_screen_hash:
>
> self.\_dirty = False
>
> return False \# skip DOM + UI tree re-query
>
> self.\_dirty = True
>
> self.\_last_screen_hash = new_screen_hash
>
> return True \# re-query needed
>
> def invalidate(self):
>
> \'\'\'Force re-query on next iteration --- call after any
> action.\'\'\'
>
> self.\_dirty = True
>
> self.\_last_screen_hash = \'\'

**2.4.2 Integration in Agent Loop**

> \# In core/agent_loop.py --- perception step
>
> current_hash = screen_hasher.hash(mss_screenshot())
>
> if state.check_and_update_dirty(current_hash):
>
> \# Screen changed --- re-query everything
>
> dom = dom_reader.read()
>
> ui_tree = ui_tree_reader.read()
>
> env = normaliser.normalise(dom, ui_tree, visual=None)
>
> state.update_from_structured(env)
>
> else:
>
> \# Screen unchanged --- skip expensive queries
>
> \# state.environment is still valid from last iteration
>
> pass
>
> \# ALWAYS invalidate after executing any action
>
> state.invalidate() \# called in agent_loop after execution

**2.4.3 dirty_flag Rules**

-   Take a fast screen hash (imagehash.phash, \~5ms) at the start of
    every loop iteration

-   Only re-query DOM and UI tree if hash has changed from previous
    iteration

-   Always call state.invalidate() immediately after executing any
    action --- action may change screen

-   Force invalidate on: any Verifier result other than PASS, any
    backtrack operation, task start

-   Never skip perception if state.ambiguous is True --- ambiguous
    states must always re-query

-   Log every cache hit (skip) and cache miss (re-query) for latency
    profiling

**2.5 IDEMPOTENT Risk Class**

The current ToolContract.risk field has four values: SAFE, REVERSIBLE,
DESTRUCTIVE, UNKNOWN. There is no way to mark an action as safe to
repeat multiple times without side effects. This forces retry logic to
treat all repeated actions with unnecessary caution. The IDEMPOTENT
class fixes this.

**2.5.1 Risk Class Definitions --- Updated**

  ------------- ------------------- ------------- -------------------- ------------------
  **Risk        **Definition**      **Retry       **Compensating       **Confirmation**
  Class**                           Policy**      Action**             

  SAFE          Read-only, no state Retry freely, None required        Never
                change possible     unlimited                          

  IDEMPOTENT    May change state    Retry freely, None required        Never
                but safe to repeat  up to 5 times                      
                --- same result                                        
                every time                                             

  REVERSIBLE    Changes state, can  Retry with    Required ---         Never
                be undone with      caution, log  registered in        (auto-undoable)
                compensating action each retry    TransactionManager   

  DESTRUCTIVE   Changes state, hard Single        Required ---         Always
                or impossible to    attempt only, registered in        
                undo                no auto-retry TransactionManager   

  UNKNOWN       Risk level not      Treat as      Treat as DESTRUCTIVE Always
                determinable        DESTRUCTIVE                        
  ------------- ------------------- ------------- -------------------- ------------------

**2.5.2 IDEMPOTENT Examples**

  ---------------------- ------------------------- -----------------------------
  **Tool**               **Why IDEMPOTENT**        **Example**

  open_application       Opening an already-open   open_browser() twice = one
                         app has no additional     browser window
                         effect                    

  navigate_to_url        Navigating to current URL navigate(\'https://x.com\')
                         reloads same page         twice = same page

  open_folder            Opening an open folder    open_folder(\'C:/temp\')
                         brings it to focus --- no twice = same window
                         duplication               

  set_checkbox_checked   Checking already-checked  check(\'accept_terms\') twice
                         box = no change           = checked once

  close_dialog           Closing already-closed    close_dialog() twice = dialog
                         dialog = no change        closed

  mkdir                  Creating existing         mkdir(\'C:/temp\') twice =
                         directory = no error, no  dir exists
                         change                    

  focus_window           Focusing already-focused  focus(\'Notepad\') twice =
                         window = no change        Notepad focused
  ---------------------- ------------------------- -----------------------------

**2.5.3 Updated ToolContract Fields**

> \@dataclass
>
> class ToolContract:
>
> name: str
>
> description: str
>
> inputs: dict\[str, type\]
>
> preconditions: list\[str\]
>
> effects: dict\[str, Any\]
>
> risk: str \# SAFE\|IDEMPOTENT\|REVERSIBLE\|DESTRUCTIVE\|UNKNOWN
>
> compensating_action: str \| None \# None for SAFE and IDEMPOTENT
>
> max_auto_retries: int \# SAFE/IDEMPOTENT: 5, REVERSIBLE: 2,
> DESTRUCTIVE: 0
>
> latency_ms_estimate: int
>
> requires_spec_check: bool

**2.5.4 Retry Logic Update in agent_loop.py**

> match contract.risk:
>
> case \'SAFE\' \| \'IDEMPOTENT\':
>
> \# Retry freely up to max_auto_retries --- no confirmation, no
> compensating action
>
> if retry_count \< contract.max_auto_retries:
>
> await execution_hierarchy.attempt(action)
>
> case \'REVERSIBLE\':
>
> \# Retry with caution --- log each retry, TransactionManager.begin()
> each time
>
> if retry_count \< contract.max_auto_retries:
>
> transaction_manager.begin(action, state)
>
> await execution_hierarchy.attempt(action)
>
> case \'DESTRUCTIVE\' \| \'UNKNOWN\':
>
> \# No auto-retry --- require fresh human confirmation each attempt
>
> if not confirmation.get(action):
>
> return \# block
>
> transaction_manager.begin(action, state)
>
> await execution_hierarchy.attempt(action)

**2.6 Tool Affinity Map**

LatencyPolicy currently evaluates ElementID confidence and state signals
to choose an execution level. But some action types have a natural
affinity to specific execution levels --- a browser click should always
start at L1 DOM, never at L2 pywinauto. The Tool Affinity Map encodes
these affinities to skip unnecessary level attempts.

**2.6.1 Affinity Map Definition**

> \# In config/tool_contracts.py
>
> TOOL_AFFINITY_MAP: dict\[str, list\[str\]\] = {
>
> \# Browser actions --- DOM first, visual fallback
>
> \'browser_click\': \[\'L1_DOM\', \'L4_LOCAL_VLM\', \'L5_CLOUD\',
> \'L6_HUMAN\'\],
>
> \'browser_type\': \[\'L1_DOM\', \'L4_LOCAL_VLM\', \'L5_CLOUD\',
> \'L6_HUMAN\'\],
>
> \'browser_navigate\': \[\'L1_DOM\', \'L6_HUMAN\'\],
>
> \'browser_scroll\': \[\'L1_DOM\', \'L4_LOCAL_VLM\', \'L6_HUMAN\'\],
>
> \# Desktop app actions --- UI tree first
>
> \'desktop_click\': \[\'L2_UI_TREE\', \'L3_PATTERN\', \'L4_LOCAL_VLM\',
> \'L5_CLOUD\', \'L6_HUMAN\'\],
>
> \'desktop_type\': \[\'L2_UI_TREE\', \'L4_LOCAL_VLM\', \'L6_HUMAN\'\],
>
> \'menu_select\': \[\'L2_UI_TREE\', \'L4_LOCAL_VLM\', \'L6_HUMAN\'\],
>
> \'dialog_respond\': \[\'L2_UI_TREE\', \'L4_LOCAL_VLM\',
> \'L6_HUMAN\'\],
>
> \# File operations --- always programmatic
>
> \'file_read\': \[\'L0_PROGRAMMATIC\'\],
>
> \'file_write\': \[\'L0_PROGRAMMATIC\'\],
>
> \'file_delete\': \[\'L0_PROGRAMMATIC\'\],
>
> \'file_copy\': \[\'L0_PROGRAMMATIC\'\],
>
> \'list_directory\': \[\'L0_PROGRAMMATIC\'\],
>
> \# System operations --- programmatic, UI tree fallback
>
> \'app_launch\': \[\'L0_PROGRAMMATIC\', \'L2_UI_TREE\',
> \'L4_LOCAL_VLM\'\],
>
> \'app_close\': \[\'L0_PROGRAMMATIC\', \'L2_UI_TREE\'\],
>
> \'registry_read\': \[\'L0_PROGRAMMATIC\'\],
>
> \'registry_write\': \[\'L0_PROGRAMMATIC\'\],
>
> \'system_info\': \[\'L0_PROGRAMMATIC\'\],
>
> \# Search / data extraction --- programmatic first
>
> \'web_search\': \[\'L0_PROGRAMMATIC\'\],
>
> \'api_call\': \[\'L0_PROGRAMMATIC\'\],
>
> \'extract_text\': \[\'L1_DOM\', \'L0_PROGRAMMATIC\',
> \'L4_LOCAL_VLM\'\],
>
> }

**2.6.2 How LatencyPolicy Uses Affinity Map**

> def choose_level(self, element: ElementID, state: StateModel,
>
> action: dict, retry_count: int) -\> ExecutionLevel:
>
> tool_name = action.get(\'tool_name\', \'\')
>
> \# Check affinity map first
>
> if tool_name in TOOL_AFFINITY_MAP:
>
> allowed_levels = TOOL_AFFINITY_MAP\[tool_name\]
>
> \# Apply confidence filtering within allowed levels only
>
> return self.\_best_level_from_allowed(element, state, allowed_levels)
>
> \# Fall back to full confidence-based routing for unknown tool types
>
> return self.\_full_confidence_routing(element, state, retry_count)

**2.6.3 Affinity Map Latency Impact**

  -------------------- ----------------- ---------------- ----------------
  **Scenario**         **Without         **With Affinity  **Saving**
                       Affinity Map**    Map**            

  Browser click with   Try L0 → fail →   Start at L1      \~5ms + 1 failed
  good DOM             try L1            directly         attempt

  File delete          Try L0 → succeed  Start at L0      No wasted
                                         directly         attempts

  Desktop app button   Try L0 → fail →   Start at L2      \~10ms + 2
  click                try L1 → fail →   directly         failed attempts
                       try L2                             

  Web search           Try L0 → succeed  Start at L0      No wasted
                                         directly         attempts

  Menu navigation in   All levels tried  L2 → L4 only     Skips L0, L1,
  desktop app          in sequence                        L3, L5
  -------------------- ----------------- ---------------- ----------------

**3. Complete Module Inventory v5.0**

All modules from v1.0 through v5.0. New or updated modules in v5.0 are
marked.

  ----------------------------------------- ------------- ----------------------------------------
  **File**                                  **Version**   **Purpose**

  perception/normaliser.py                  v5.0 NEW      EnvironmentNormaliser --- merges DOM+UI
                                                          tree+visual into NormalisedEnvironment

  perception/schemas.py                     v5.0 NEW      NormalisedElement and
                                                          NormalisedEnvironment dataclasses

  core/state_model.py                       v5.0 UPDATED  Added dirty_flag,
                                                          check_and_update_dirty(), invalidate(),
                                                          NormalisedEnvironment field

  config/tool_contracts.py                  v5.0 UPDATED  Added IDEMPOTENT risk class,
                                                          TOOL_AFFINITY_MAP, max_auto_retries
                                                          field

  config/latency_thresholds.py              v5.0 UPDATED  Added VLM_LOCAL_CONFIDENCE_THRESHOLD,
                                                          VLM_CLOUD_CONFIDENCE_THRESHOLD,
                                                          OMNIPARSER_MIN_CONFIDENCE

  execution/level3_pattern.py               v5.0 UPDATED  Now uses TemplateMatchingConfig ---
                                                          storage, scaling, ROI, multi-monitor

  execution/level4_local_vision.py          v5.0 UPDATED  Now uses VLM Grounding Prompt Format ---
                                                          OmniParser output structured into prompt

  latency_policy/policy.py                  v5.0 UPDATED  Tool Affinity Map integration ---
                                                          choose_level() checks affinity before
                                                          confidence routing

  safety/classifier.py                      v5.0 UPDATED  Added IDEMPOTENT handling --- idempotent
                                                          actions never require confirmation

  config/template_matching.py               v5.0 NEW      TemplateMatchingConfig dataclass with
                                                          all storage, scaling, confidence, ROI
                                                          settings

  templates/                                v5.0 NEW      Template storage directory --- PNG files
                                                          named app_label_resolution.png

  .cursorrules                              v5.0 UPDATED  All six v5.0 additions added to
                                                          architecture rules

  main.py                                   v1.0          Entry point --- unchanged

  goal_spec/compiler.py                     v4.0          GoalSpecCompiler

  goal_spec/validator.py                    v4.0          Spec validation per action

  core/agent_loop.py                        v5.0 UPDATED  dirty_flag check + invalidate(),
                                                          IDEMPOTENT retry logic, affinity map
                                                          routing

  core/planner_task.py                      v2.0          Task Planner --- Claude Sonnet

  core/planner_execution.py                 v3.0          Execution Planner --- Claude Haiku,
                                                          batched

  core/evidence_planner.py                  v4.0          EvidencePlan generation

  core/goal_tracker.py                      v1.0          Success criteria and retry management

  core/governance_budget.py                 v4.0          step+time+cost+retry budgets

  core/deadlock_detector.py                 v3.0          4 deadlock conditions

  verifier/pre_state.py                     v3.0          Pre-action state capture

  verifier/post_state.py                    v3.0          Post-action state capture

  verifier/diff_engine.py                   v3.0          Multi-modal diff

  verifier/expectation_matcher.py           v5.0 UPDATED  Uses NormalisedEnvironment for element
                                                          state checks

  verifier/outcome_classifier.py            v3.0          PASS/NO_OP/WRONG_STATE/TIMEOUT/PARTIAL

  state_graph/graph.py                      v3.0          Tree-structured state graph

  state_graph/node.py                       v3.0          StateNode dataclass

  state_graph/edge.py                       v3.0          ActionEdge with StateDiff

  transaction/manager.py                    v4.0          TransactionManager

  transaction/compensating.py               v4.0          Compensating action registry

  transaction/trash.py                      v4.0          File trash/restore

  latency_policy/profiler.py                v3.0          Latency logging

  safety/simulator.py                       v2.0          Pre-execution simulation

  safety/confirmation.py                    v1.0          Confirmation gate

  safety/action_logger.py                   v1.0          SQLite action log

  safety/sandbox.py                         v1.0          Sandbox mode

  execution/hierarchy.py                    v3.0          Routes via LatencyPolicy + affinity

  execution/level0_programmatic.py          v2.0          Python/shell/API

  execution/level1_dom.py                   v1.0          Playwright DOM

  execution/level2_ui_tree.py               v1.0          pywinauto

  execution/level5_cloud_vision.py          v1.0          Gemini Flash

  execution/level6_human.py                 v4.0          InteractiveHumanLoop

  adapters/browser_adapter.py               v2.0          BrowserAdapter

  adapters/windows_ui_adapter.py            v2.0          WindowsUIAdapter

  adapters/filesystem_adapter.py            v2.0          FilesystemAdapter

  adapters/shell_adapter.py                 v2.0          ShellAdapter

  adapters/api_adapter.py                   v2.0          APIAdapter

  perception/structured/dom_reader.py       v1.0          Playwright DOM extraction

  perception/structured/ui_tree_reader.py   v1.0          pywinauto tree

  perception/structured/screen_hasher.py    v2.0          Perceptual hash

  perception/visual/screenshot.py           v1.0          MSS capture with ROI

  perception/visual/omniparser.py           v1.0          Element detection

  perception/visual/vlm_reader.py           v5.0 UPDATED  Uses VLM Grounding Prompt Format

  element_id/element_id.py                  v3.0          ElementID dataclass

  element_id/resolver.py                    v5.0 UPDATED  Now uses NormalisedElement fields to
                                                          populate ElementID fallbacks

  trajectory/element_fingerprints.py        v3.0          Fingerprint store

  trajectory/action_templates.py            v3.0          Action templates

  trajectory/failure_patterns.py            v3.0          Failure patterns

  trajectory/navigation_paths.py            v3.0          Navigation paths

  trajectory/db.py                          v3.0          SQLite schema

  human_loop/interactive.py                 v4.0          InteractiveHumanLoop

  human_loop/context_packager.py            v4.0          Context package for human

  human_loop/hint_parser.py                 v4.0          Parses human hint

  memory/session_memory.py                  v1.0          In-session history

  memory/persistent_memory.py               v1.0          General storage

  config/settings.py                        v1.0          API keys, paths, flags

  config/safety_rules.py                    v1.0          Classification defaults

  tests/                                    v1.0+         Full test suite
  ----------------------------------------- ------------- ----------------------------------------

**4. Updated .cursorrules --- v5.0**

Replace your .cursorrules file with this complete v5.0 version.

+-----------------------------------------------------------------------+
| \# hybrid_agent/.cursorrules                                          |
|                                                                       |
| \# ─────────────────────────────────────────────────────              |
|                                                                       |
| \# HYBRID AI AGENT --- CURSOR RULES v5.0                              |
|                                                                       |
| \# ─────────────────────────────────────────────────────              |
|                                                                       |
| \## PROJECT IDENTITY                                                  |
|                                                                       |
| Safety-aware hybrid AI agent automating computer tasks.               |
|                                                                       |
| Language: Python 3.11+ \| Async throughout \| Production-grade        |
|                                                                       |
| Architecture: programmatic-first, structured perception, vision       |
| fallback only.                                                        |
|                                                                       |
| \## ARCHITECTURE RULES (NON-NEGOTIABLE)                               |
|                                                                       |
| \- NEVER execute before GoalSpec validation                           |
|                                                                       |
| \- NEVER execute before ToolContract precondition check               |
|                                                                       |
| \- NEVER execute without TransactionManager.begin() first             |
|                                                                       |
| \- NEVER skip Verifier after any action                               |
|                                                                       |
| \- NEVER continue a batch after Verifier returns WRONG_STATE          |
|                                                                       |
| \- NEVER use raw coordinates or CSS selectors --- always wrap in      |
| ElementID                                                             |
|                                                                       |
| \- NEVER call vision if structured confidence \> 0.80                 |
|                                                                       |
| \- NEVER classify risk by tool name --- use ToolContract.risk field   |
|                                                                       |
| \- NEVER re-query DOM/UI tree if StateModel.\_dirty is False          |
|                                                                       |
| \- NEVER skip state.invalidate() after executing any action           |
|                                                                       |
| \- ALWAYS capture pre-state before action for StateDiff               |
|                                                                       |
| \- ALWAYS check ElementID resolution cache before detecting elements  |
|                                                                       |
| \- ALWAYS use NormalisedEnvironment for element reasoning --- never   |
| raw DOM                                                               |
|                                                                       |
| \- ALWAYS check TOOL_AFFINITY_MAP before confidence-based level       |
| routing                                                               |
|                                                                       |
| \- ALWAYS add type hints to every function signature                  |
|                                                                       |
| \- ALWAYS add docstrings to every class and public method             |
|                                                                       |
| \## PERCEPTION PIPELINE ORDER                                         |
|                                                                       |
| 1\. Fast screen hash (imagehash.phash) --- \~5ms                      |
|                                                                       |
| 2\. If hash unchanged: skip to step 6 (dirty_flag cache hit)          |
|                                                                       |
| 3\. DOM reader (Playwright) → raw DOM                                 |
|                                                                       |
| 4\. UI tree reader (pywinauto) → raw tree                             |
|                                                                       |
| 5\. EnvironmentNormaliser.normalise(dom, ui_tree) →                   |
| NormalisedEnvironment                                                 |
|                                                                       |
| 6\. StateModel.update_from_structured(normalised_env)                 |
|                                                                       |
| 7\. If action fails: visual pipeline (MSS → OmniParser → VLM          |
| grounding prompt)                                                     |
|                                                                       |
| \## EXECUTION HIERARCHY ORDER                                         |
|                                                                       |
| Check TOOL_AFFINITY_MAP first --- only try levels in the affinity     |
| list.                                                                 |
|                                                                       |
| L0: Programmatic (code/shell/API) --- file ops, system info, API      |
| calls ALWAYS here                                                     |
|                                                                       |
| L1: Playwright DOM --- browser actions, confidence \>= 0.80           |
|                                                                       |
| L2: pywinauto UI tree --- desktop apps, confidence \>= 0.75           |
|                                                                       |
| L3: OpenCV (active window ROI, 1280x720 normalised) --- confidence    |
| \>= 0.65                                                              |
|                                                                       |
| L4: OmniParser → VLM Grounding Prompt → Qwen2-VL --- confidence \>=   |
| 0.60                                                                  |
|                                                                       |
| L5: Gemini Flash --- VLM confidence \< 0.60 or GPU unavailable        |
|                                                                       |
| L6: InteractiveHumanLoop --- all levels failed                        |
|                                                                       |
| \## VLM GROUNDING RULE                                                |
|                                                                       |
| Qwen2-VL must ALWAYS receive:                                         |
|                                                                       |
| 1\. Resized screenshot (1280x720)                                     |
|                                                                       |
| 2\. OmniParser element list as JSON                                   |
|                                                                       |
| 3\. Grounding prompt format from PRD Section 2.3.2                    |
|                                                                       |
| Never send raw screenshot to VLM without OmniParser pre-labelling.    |
|                                                                       |
| \## RISK CLASSES                                                      |
|                                                                       |
| SAFE: read-only, no state change, retry unlimited                     |
|                                                                       |
| IDEMPOTENT: safe to repeat, same result, retry up to 5x, no           |
| compensating action                                                   |
|                                                                       |
| REVERSIBLE: changes state, undo available, retry up to 2x with        |
| TransactionManager                                                    |
|                                                                       |
| DESTRUCTIVE: hard to undo, single attempt only, always require        |
| confirmation                                                          |
|                                                                       |
| UNKNOWN: treat as DESTRUCTIVE always                                  |
|                                                                       |
| \## SAFETY RULES                                                      |
|                                                                       |
| \- All file deletes → copy to C:/.agent_trash/ first                  |
|                                                                       |
| \- All file writes → backup to C:/.agent_backups/ first               |
|                                                                       |
| \- All registry edits → export to C:/.agent_reg_backups/ first        |
|                                                                       |
| \- Destructive: simulation + confirmation + transaction               |
|                                                                       |
| \- Unknown risk: default to DESTRUCTIVE                               |
|                                                                       |
| \- IDEMPOTENT and SAFE: no confirmation, no compensating action       |
|                                                                       |
| \## CODE STYLE                                                        |
|                                                                       |
| \- dataclasses for all state objects and contracts                    |
|                                                                       |
| \- asyncio for all I/O and agent loop                                 |
|                                                                       |
| \- pathlib for all file paths --- never os.path                       |
|                                                                       |
| \- deepdiff for state comparison                                      |
|                                                                       |
| \- imagehash for screen change detection                              |
|                                                                       |
| \- difflib.SequenceMatcher for text similarity in normaliser          |
|                                                                       |
| \- try/except on all external calls with specific error types         |
|                                                                       |
| \- Timeouts on every external API call                                |
|                                                                       |
| \- Log every action to SQLite via safety/action_logger.py             |
|                                                                       |
| \## FOLDER STRUCTURE                                                  |
|                                                                       |
| goal_spec/ --- GoalSpec compiler and validator                        |
|                                                                       |
| core/ --- agent_loop, planners, goal_tracker, state_model,            |
|                                                                       |
| deadlock_detector, governance_budget, evidence_planner                |
|                                                                       |
| verifier/ --- pre/post state, diff_engine, expectation_matcher,       |
| outcome                                                               |
|                                                                       |
| state_graph/ --- tree backtracking: graph, node, edge                 |
|                                                                       |
| transaction/ --- TransactionManager, compensating, trash              |
|                                                                       |
| latency_policy/ --- LatencyPolicy (affinity map) + profiler           |
|                                                                       |
| safety/ --- classifier, simulator, confirmation, logger, sandbox      |
|                                                                       |
| execution/ --- hierarchy + L0-L6                                      |
|                                                                       |
| adapters/ --- browser, windows_ui, filesystem, shell, api             |
|                                                                       |
| perception/ --- normaliser.py, schemas.py, structured/, visual/       |
|                                                                       |
| element_id/ --- ElementID dataclass and resolver                      |
|                                                                       |
| trajectory/ --- 4 stores + SQLite schema                              |
|                                                                       |
| human_loop/ --- interactive escalation, context_packager, hint_parser |
|                                                                       |
| config/ --- settings, safety_rules, latency_thresholds,               |
|                                                                       |
| tool_contracts (AFFINITY_MAP), template_matching                      |
|                                                                       |
| templates/ --- OpenCV template PNG files                              |
|                                                                       |
| memory/ --- session and persistent                                    |
|                                                                       |
| tests/ --- full test suite                                            |
+-----------------------------------------------------------------------+

**5. New Cursor Prompts --- v5.0 Additions**

These prompts add to the 17 prompts from v4.0. Use them in Phase 3 when
building the perception and configuration layers.

**Prompt 18 --- perception/normaliser.py + schemas.py**

+-----------------------------------------------------------------------+
| Build perception/normaliser.py and perception/schemas.py              |
|                                                                       |
| for a hybrid AI agent.                                                |
|                                                                       |
| PURPOSE: Merge DOM, UI tree, and visual (OmniParser) element data     |
|                                                                       |
| into a single NormalisedEnvironment schema. All modules reason over   |
|                                                                       |
| NormalisedEnvironment --- never raw DOM or UI tree directly.          |
|                                                                       |
| SCHEMAS (in perception/schemas.py):                                   |
|                                                                       |
| NormalisedElement dataclass:                                          |
|                                                                       |
| id: str (stable UUID)                                                 |
|                                                                       |
| label: str                                                            |
|                                                                       |
| element_type: str \# button\|input\|link\|text\|image\|container      |
|                                                                       |
| text_content: str \| None                                             |
|                                                                       |
| state: str \# enabled\|disabled\|checked\|hidden                      |
|                                                                       |
| sources: list\[str\] \# \[\'dom\',\'ui_tree\',\'visual\'\]            |
|                                                                       |
| dom_locator: str \| None                                              |
|                                                                       |
| ui_tree_id: str \| None                                               |
|                                                                       |
| bbox: str \| None \# \'x,y,w,h\'                                      |
|                                                                       |
| confidence: float                                                     |
|                                                                       |
| children: list\[\'NormalisedElement\'\]                               |
|                                                                       |
| NormalisedEnvironment dataclass:                                      |
|                                                                       |
| window_title: str                                                     |
|                                                                       |
| window_type: str \# browser\|desktop_app\|dialog\|unknown             |
|                                                                       |
| current_url: str \| None                                              |
|                                                                       |
| app_name: str                                                         |
|                                                                       |
| elements: list\[NormalisedElement\]                                   |
|                                                                       |
| interactive: list\[NormalisedElement\] \# enabled                     |
| buttons/inputs/links only                                             |
|                                                                       |
| timestamp: datetime                                                   |
|                                                                       |
| source_hash: str                                                      |
|                                                                       |
| NORMALISER (in perception/normaliser.py):                             |
|                                                                       |
| EnvironmentNormaliser class:                                          |
|                                                                       |
| normalise(dom, ui_tree, visual) -\> NormalisedEnvironment             |
|                                                                       |
| \_merge_elements(dom_els, tree_els, vis_els) -\>                      |
| list\[NormalisedElement\]                                             |
|                                                                       |
| \_text_similarity(a, b) -\> float \# difflib.SequenceMatcher          |
|                                                                       |
| \_spatial_overlap(bbox1, bbox2) -\> float \# IoU calculation          |
|                                                                       |
| \_map_dom_type(html_tag) -\> str                                      |
|                                                                       |
| \_map_ui_control_type(control_type) -\> str                           |
|                                                                       |
| MERGE STRATEGY:                                                       |
|                                                                       |
| 1\. Start with DOM elements (most precise locators)                   |
|                                                                       |
| 2\. For each UI tree element: match to DOM by text similarity \> 0.80 |
|                                                                       |
| If matched: add ui_tree_id to existing element                        |
|                                                                       |
| If unmatched: create new NormalisedElement with ui_tree source only   |
|                                                                       |
| 3\. For each visual element: match by spatial overlap (IoU \> 0.50) + |
| label sim \> 0.70                                                     |
|                                                                       |
| If matched: add bbox to existing element, take higher confidence      |
|                                                                       |
| If unmatched: create new NormalisedElement with visual source only    |
|                                                                       |
| 4\. interactive = filter(elements, state==\'enabled\' and             |
|                                                                       |
| type in \[\'button\',\'input\',\'link\'\])                            |
|                                                                       |
| RULES:                                                                |
|                                                                       |
| \- Assign stable UUID on first normalisation --- same element keeps   |
| same id                                                               |
|                                                                       |
| \- Never require all three sources --- any combination is valid       |
|                                                                       |
| \- source_hash = hash of raw inputs --- used for cache validation     |
|                                                                       |
| \- Log merge statistics: matched count per source                     |
|                                                                       |
| Follow .cursorrules.                                                  |
+-----------------------------------------------------------------------+

**Prompt 19 --- config/template_matching.py +
execution/level3_pattern.py**

+-----------------------------------------------------------------------+
| Build config/template_matching.py and update                          |
| execution/level3_pattern.py                                           |
|                                                                       |
| for a hybrid AI agent.                                                |
|                                                                       |
| PURPOSE: Reliable OpenCV template matching with defined storage       |
| strategy,                                                             |
|                                                                       |
| resolution normalisation, confidence policy, and multi-monitor        |
| handling.                                                             |
|                                                                       |
| CONFIG (config/template_matching.py):                                 |
|                                                                       |
| TemplateMatchingConfig dataclass:                                     |
|                                                                       |
| template_dir: Path \# \'./templates/\' from settings                  |
|                                                                       |
| template_format: str = \'png\'                                        |
|                                                                       |
| naming_convention: str =                                              |
| \'{app_name}\_{label}\_{width}x{height}.png\'                         |
|                                                                       |
| normalise_to: tuple = (1280, 720)                                     |
|                                                                       |
| scale_factors: list = \[0.75, 1.0, 1.25\]                             |
|                                                                       |
| min_confidence: float = 0.80                                          |
|                                                                       |
| multi_match_threshold: float = 0.95                                   |
|                                                                       |
| roi_mode: str = \'active_window\' \# active_window\|full_screen       |
|                                                                       |
| roi_padding_px: int = 20                                              |
|                                                                       |
| monitor_strategy: str = \'active_only\'                               |
|                                                                       |
| LEVEL 3 EXECUTOR (execution/level3_pattern.py):                       |
|                                                                       |
| PatternMatchExecutor class:                                           |
|                                                                       |
| \_\_init\_\_(config: TemplateMatchingConfig)                          |
|                                                                       |
| find(element: ElementID, state: StateModel) -\> MatchResult \| None   |
|                                                                       |
| click(match: MatchResult) -\> bool                                    |
|                                                                       |
| save_template(screenshot, label, app_name) -\> Path                   |
|                                                                       |
| \_capture_roi(state) -\> np.ndarray \# active window region only      |
|                                                                       |
| \_normalise(img) -\> np.ndarray \# resize to normalise_to             |
|                                                                       |
| \_match(template, roi) -\> list\[MatchResult\] \# try all             |
| scale_factors                                                         |
|                                                                       |
| \_get_active_monitor() -\> dict \# monitor containing active window   |
|                                                                       |
| \_to_absolute_coords(match, roi_offset) -\> tuple \# convert ROI to   |
| screen coords                                                         |
|                                                                       |
| MatchResult dataclass:                                                |
|                                                                       |
| element_id: str                                                       |
|                                                                       |
| confidence: float                                                     |
|                                                                       |
| bbox: str \# absolute screen coordinates \'x,y,w,h\'                  |
|                                                                       |
| scale_factor: float \# which scale matched                            |
|                                                                       |
| monitor_id: int                                                       |
|                                                                       |
| RULES:                                                                |
|                                                                       |
| \- Always capture active window ROI + roi_padding_px --- never full   |
| screen                                                                |
|                                                                       |
| \- Try all scale_factors --- return highest confidence match above    |
| min_confidence                                                        |
|                                                                       |
| \- Return None if no match above min_confidence --- do not guess      |
|                                                                       |
| \- Coordinates always in absolute screen space --- not                |
| monitor-relative                                                      |
|                                                                       |
| \- Use pygetwindow for active window bounds                           |
|                                                                       |
| \- Use mss for ROI capture given bounds                               |
|                                                                       |
| \- Log every match attempt with confidence for threshold tuning       |
|                                                                       |
| Follow .cursorrules.                                                  |
+-----------------------------------------------------------------------+

**Prompt 20 --- Update execution/level4_local_vision.py**

+-----------------------------------------------------------------------+
| Update execution/level4_local_vision.py for a hybrid AI agent.        |
|                                                                       |
| PURPOSE: Add VLM Grounding Prompt Format so Qwen2-VL receives         |
| structured                                                            |
|                                                                       |
| OmniParser output as context --- not raw screenshots. This reduces    |
|                                                                       |
| hallucinated coordinates and improves element identification          |
| accuracy.                                                             |
|                                                                       |
| CHANGES TO MAKE:                                                      |
|                                                                       |
| 1\. Add build_grounding_prompt(env: NormalisedEnvironment,            |
|                                                                       |
| action_description: str,                                              |
|                                                                       |
| element_description: str) -\> str                                     |
|                                                                       |
| \- Formats NormalisedEnvironment.interactive as JSON element list     |
|                                                                       |
| \- Assembles full prompt using the template from PRD Section 2.3.2    |
|                                                                       |
| \- Returns complete prompt string ready for VLM                       |
|                                                                       |
| 2\. Add parse_vlm_response(response: str) -\> VLMResult               |
|                                                                       |
| VLMResult dataclass:                                                  |
|                                                                       |
| element_id: str \| None                                               |
|                                                                       |
| element_label: str \| None                                            |
|                                                                       |
| action: str                                                           |
|                                                                       |
| bbox: str \| None                                                     |
|                                                                       |
| click_point: str \| None                                              |
|                                                                       |
| confidence: float                                                     |
|                                                                       |
| reasoning: str                                                        |
|                                                                       |
| not_found: bool                                                       |
|                                                                       |
| 3\. Update execute() method:                                          |
|                                                                       |
| \- Build grounding prompt from NormalisedEnvironment                  |
|                                                                       |
| \- Send \[screenshot_image, grounding_prompt\] to Qwen2-VL            |
|                                                                       |
| \- Parse response with parse_vlm_response()                           |
|                                                                       |
| \- If result.confidence \< VLM_LOCAL_CONFIDENCE_THRESHOLD: return     |
| None                                                                  |
|                                                                       |
| (caller escalates to L5)                                              |
|                                                                       |
| \- If result.not_found: return None                                   |
|                                                                       |
| \- Normalise coordinates from 1280x720 back to original resolution    |
|                                                                       |
| \- Return VLMResult                                                   |
|                                                                       |
| 4\. Add coordinate_denormalise(bbox_str, original_size) -\> str       |
|                                                                       |
| \- Converts bbox from 1280x720 space back to original screen          |
| resolution                                                            |
|                                                                       |
| RULES:                                                                |
|                                                                       |
| \- Never send raw screenshot without grounding prompt                 |
|                                                                       |
| \- VLM_LOCAL_CONFIDENCE_THRESHOLD = 0.60 from                         |
| config/latency_thresholds.py                                          |
|                                                                       |
| \- OMNIPARSER_MIN_CONFIDENCE = 0.40 --- filter before including in    |
| prompt                                                                |
|                                                                       |
| \- Log full VLM response + confidence for every call                  |
|                                                                       |
| \- Strip JSON fences from response before parsing                     |
|                                                                       |
| Follow .cursorrules.                                                  |
+-----------------------------------------------------------------------+

**Prompt 21 --- Update core/state_model.py with dirty_flag**

+-----------------------------------------------------------------------+
| Update core/state_model.py to add dirty_flag perception caching.      |
|                                                                       |
| PURPOSE: Skip DOM and UI tree re-query when screen hash is unchanged. |
|                                                                       |
| \~30-50% loop time reduction for tasks where most steps don\'t change |
| screen.                                                               |
|                                                                       |
| ADD THESE FIELDS to StateModel:                                       |
|                                                                       |
| \_dirty: bool = True                                                  |
|                                                                       |
| \_last_screen_hash: str = \'\'                                        |
|                                                                       |
| environment: NormalisedEnvironment \| None = None \# replaces raw     |
| dom_snapshot                                                          |
|                                                                       |
| ADD THESE METHODS:                                                    |
|                                                                       |
| def check_and_update_dirty(self, new_screen_hash: str) -\> bool:      |
|                                                                       |
| \'\'\'                                                                |
|                                                                       |
| Call with current screen hash before perception step.                 |
|                                                                       |
| Returns True if re-query needed (hash changed or first run).          |
|                                                                       |
| Returns False if screen unchanged --- skip DOM and UI tree query.     |
|                                                                       |
| \'\'\'                                                                |
|                                                                       |
| if new_screen_hash == self.\_last_screen_hash and not self.\_dirty:   |
|                                                                       |
| return False                                                          |
|                                                                       |
| self.\_dirty = True                                                   |
|                                                                       |
| self.\_last_screen_hash = new_screen_hash                             |
|                                                                       |
| return True                                                           |
|                                                                       |
| def update_from_normalised(self, env: NormalisedEnvironment):         |
|                                                                       |
| \'\'\'Store normalised environment and mark clean.\'\'\'              |
|                                                                       |
| self.environment = env                                                |
|                                                                       |
| self.\_dirty = False                                                  |
|                                                                       |
| def invalidate(self):                                                 |
|                                                                       |
| \'\'\'Force re-query on next iteration. Call after every              |
| action.\'\'\'                                                         |
|                                                                       |
| self.\_dirty = True                                                   |
|                                                                       |
| self.\_last_screen_hash = \'\'                                        |
|                                                                       |
| ALSO UPDATE:                                                          |
|                                                                       |
| \- snapshot() to include environment.window_title and                 |
|                                                                       |
| len(environment.interactive) if environment is not None               |
|                                                                       |
| \- clone() to deep-copy the environment field                         |
|                                                                       |
| \- diff() to use environment.elements for element-level diffing       |
|                                                                       |
| RULES:                                                                |
|                                                                       |
| \- invalidate() called in agent_loop.py after EVERY action execution  |
|                                                                       |
| \- Force invalidate on: backtrack, task start, Verifier WRONG_STATE   |
|                                                                       |
| \- Never skip perception if self.ambiguous is True                    |
|                                                                       |
| \- Log cache hit / cache miss ratio for performance monitoring        |
|                                                                       |
| Follow .cursorrules.                                                  |
+-----------------------------------------------------------------------+

**Prompt 22 --- Update config/tool_contracts.py with IDEMPOTENT +
Affinity Map**

+-----------------------------------------------------------------------+
| Update config/tool_contracts.py for a hybrid AI agent.                |
|                                                                       |
| PURPOSE: Add IDEMPOTENT risk class and TOOL_AFFINITY_MAP.             |
|                                                                       |
| CHANGES:                                                              |
|                                                                       |
| 1\. Update ToolContract dataclass:                                    |
|                                                                       |
| \- risk field: now accepts                                            |
| \                                                                     |
| 'SAFE\'\|\'IDEMPOTENT\'\|\'REVERSIBLE\'\|\'DESTRUCTIVE\'\|\'UNKNOWN\' |
|                                                                       |
| \- Add: max_auto_retries: int                                         |
|                                                                       |
| SAFE → 10, IDEMPOTENT → 5, REVERSIBLE → 2, DESTRUCTIVE → 0, UNKNOWN → |
| 0                                                                     |
|                                                                       |
| 2\. Add IDEMPOTENT contracts for:                                     |
|                                                                       |
| open_application, navigate_to_url, open_folder,                       |
|                                                                       |
| set_checkbox_checked, close_dialog, mkdir, focus_window               |
|                                                                       |
| 3\. Add TOOL_AFFINITY_MAP dict as shown in PRD Section 2.6.1          |
|                                                                       |
| Include all browser, desktop, file, system, and search action types.  |
|                                                                       |
| 4\. Update get_risk() to return \'IDEMPOTENT\' for idempotent tools   |
|                                                                       |
| 5\. Add new helper:                                                   |
|                                                                       |
| get_affinity_levels(tool_name: str) -\> list\[str\] \| None           |
|                                                                       |
| Returns list of level strings from TOOL_AFFINITY_MAP, or None if not  |
| found                                                                 |
|                                                                       |
| 6\. Add:                                                              |
|                                                                       |
| get_max_retries(tool_name: str) -\> int                               |
|                                                                       |
| Returns max_auto_retries from contract, or 0 if unknown               |
|                                                                       |
| RULES:                                                                |
|                                                                       |
| \- IDEMPOTENT actions never require confirmation                      |
|                                                                       |
| \- IDEMPOTENT actions never require compensating_action (set to None) |
|                                                                       |
| \- Affinity map levels are ORDERED --- first in list is preferred     |
|                                                                       |
| \- All file operations must be L0_PROGRAMMATIC only in affinity map   |
|                                                                       |
| Follow .cursorrules.                                                  |
+-----------------------------------------------------------------------+

**6. Final Technical Score --- All Versions**

  ---------------------- --------------- -------------- ------------------ --------------------- ------------------------
  **Architecture Area**  **v1.0**        **v2.0**       **v3.0**           **v4.0**              **v5.0**

  Hybrid execution       Basic           \+ L0          Strong             Strong                \+ Affinity Map routing
  hierarchy                              programmatic                                            

  Structured perception  DOM + UI tree   Unchanged      \+ screen hashing  Unchanged             \+ dirty_flag cache

  Environment schema     Raw             Unchanged      Unchanged          Unchanged             NormalisedEnvironment
                         heterogeneous                                                           

  Vision fallback        Screenshot only Unchanged      \+ OmniParser      \+ VLM confidence     \+ Grounding prompt
                                                                           gate                  format

  Safety classification  Keyword-based   Unchanged      Unchanged          \+                    \+ IDEMPOTENT class
                                                                           ToolContract-driven   

  Formal goal            Missing         Missing        Missing            GoalSpecCompiler      Unchanged
  constraints                                                                                    

  Verifier               Missing         Conceptual     Fully specified    \+ ExpectationMatcher \+ Uses NormEnv

  Backtracking           Missing         Linear stack   State Graph (tree) Unchanged             Unchanged

  Plan batching          Missing         Two-tier       \+ ElementID in    Unchanged             Unchanged
                                         planner        batch                                    

  Trajectory learning    Missing         Concept        4 stores + schema  Unchanged             Unchanged

  Transaction/Rollback   Missing         Missing        Missing            Full TransactionMgr   Unchanged

  Typed tool contracts   Missing         Missing        Missing            Full contracts        \+ IDEMPOTENT + affinity

  Evidence planner       Missing         Missing        Missing            Proactive proofs      Unchanged

  State diff engine      Missing         Missing        In Verifier        StateModel.diff()     \+ NormEnv element diff

  Interactive human loop Missing         Missing        Missing            Full hint→resume      Unchanged

  Governance budget      Partial         Unchanged      DeadlockDetector   Dedicated module      Unchanged
                         (deadlock)                                                              

  Pattern matching       Mentioned       Unchanged      \+ ROI restriction Unchanged             \+
                                                                                                 TemplateMatchingConfig

  VLM grounding          Missing         Missing        \+ OmniParser      Unchanged             \+ Grounding prompt
                                                        pipeline                                 format

  StateModel caching     None            None           None               None                  dirty_flag +
                                                                                                 invalidate()

  Latency routing        Goal only       Unchanged      LatencyPolicy      \+ 5 vision triggers  \+ Tool affinity map
  ---------------------- --------------- -------------- ------------------ --------------------- ------------------------

**6.1 What This System Is Now**

  ------------------ ----------------------------------------------------
  **Dimension**      **Assessment**

  Architecture tier  Research-grade --- matches UFO2, ActionEngine,
                     BacktrackAgent design patterns

  Safety model       Production-grade --- formal goal constraints + typed
                     contracts + transactional rollback

  Perception model   Hybrid structured-primary --- normalised schema +
                     vision fallback with grounding

  Recovery model     Full backtracking --- tree-structured state graph +
                     interactive human loop

  Learning model     Session and persistent --- trajectory memory reduces
                     LLM calls 60-80% over time

  Latency model      Policy-driven --- affinity map + dirty_flag + plan
                     batching + cache = sub-200ms target

  Build readiness    Complete --- 22 Cursor prompts cover every module
                     from settings.py to agent_loop.py
  ------------------ ----------------------------------------------------

**7. Quick Reference Card --- Build Order**

The order that minimises rework. Each phase depends on the previous.

  ------------- ---------- --------------------------------------- -------------------------
  **Phase**     **Week**   **Build These (in order)**              **Gate Before Next
                                                                   Phase**

  1 ---         1          settings.py → state_model.py+dirty_flag Run a task end-to-end
  Foundation               → goal_tracker.py →                     with print statements
                           governance_budget.py → planner_task.py  only
                           → planner_execution.py                  

  2 ---         2          tool_contracts.py+IDEMPOTENT+affinity → Delete a file safely with
  Execution +              transaction/manager.py →                trash backup, confirm log
  Safety                   safety/classifier.py → action_logger.py entry exists
                           → L0+L1+L2 execution                    

  3 --- Spec +  3          goal_spec/compiler.py → schemas.py →    Compile a GoalSpec, run
  Perception               normaliser.py → dom_reader.py →         normaliser, inspect
                           ui_tree_reader.py → screen_hasher.py →  NormalisedEnvironment
                           ElementID+resolver                      output

  4 ---         4          verifier/ (all 5 files) → state_graph/  Intentionally break an
  Verifier +               (3 files) → deadlock_detector.py →      action, confirm Verifier
  Graph                    evidence_planner.py                     catches it and backtrack
                                                                   fires

  5 ---         5          latency_policy/policy.py+affinity →     Run same task twice,
  Policy +                 latency_policy/profiler.py →            confirm second run uses
  Memory                   trajectory/ (all 5 files) →             fewer LLM calls
                           template_matching.py →                  
                           level3_pattern.py                       

  6 ---         6          level4_local_vision.py+grounding →      Trigger vision fallback
  Vision + HiL             level5_cloud_vision.py → all 5 adapters intentionally, confirm
                           → human_loop/ (3 files)                 grounding prompt sent
                                                                   correctly

  7 --- Harden  7          Full test suite → latency benchmarks →  All 22 test scenarios
                           threshold tuning → gradio UI →          pass, sub-200ms average
                           agent_loop.py final integration         on 80% of actions
  ------------- ---------- --------------------------------------- -------------------------

**7.1 Minimum Viable v1 --- 2 Week Build**

  -----------------------------------------------------------------------
  *If you want a working agent in 2 weeks, build only the modules marked
  YES below. These cover 80% of real tasks and include all critical
  safety and recovery mechanisms.*

  -----------------------------------------------------------------------

  -------------------------- ------------ ------------------------------------
  **Module**                 **v1         **Skip Until**
                             Build?**     

  settings.py + .env         YES          ---

  StateModel + dirty_flag    YES          ---

  NormalisedEnvironment +    YES          Core schema --- needed by everything
  Normaliser                              

  GoalSpecCompiler           YES          Full NL compilation in v2
  (simplified)                            

  ToolContracts +            YES          ---
  IDEMPOTENT + Affinity                   

  Two-tier Planner           YES          ---

  EvidencePlanner            YES          Full proof capture in v2
  (simplified)                            

  GoalTracker +              YES          ---
  GovernanceBudget                        

  DeadlockDetector           YES          Lightweight --- must have

  Verifier (diff-based)      YES          ---

  StateGraph (3-level depth) YES          Full 50-node graph in v2

  TransactionManager (files  YES          Registry and app ops in v2
  only)                                   

  Safety classifier + logger YES          ---

  L0 + L1 + L2 execution     YES          ---

  LatencyPolicy + Affinity   YES          ---
  Map                                     

  ElementID + Resolver       YES          ---

  Trajectory fingerprints    YES          Templates + patterns in v2
  only                                    

  InteractiveHumanLoop       YES          Web UI in v2
  (terminal)                              

  OmniParser                 NO           Phase 6

  Qwen2-VL + grounding       NO           Phase 6
  prompt                                  

  TemplateMatchingConfig +   NO           Phase 5
  L3                                      

  Gemini Flash L5            NO           Phase 6

  All 5 adapters             PARTIAL      Browser + Filesystem in v1
  -------------------------- ------------ ------------------------------------

*End of Document · Hybrid AI Agent PRD v5.0 · Final Complete Edition*
