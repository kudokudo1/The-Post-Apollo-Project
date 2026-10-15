✦︎✦︎✦︎ Meta Apollo Logos //

# SELECTOR FAMILY // FOUNDATION CONTRACT

> **STATE //** approved architecture foundation; implementation evidence is tracked per slice below (updated 2026-10-15)  
> **OWNER //** Nurse 3A / Team 3, subject to Hospital coordination and shared-file ownership  
> **AUDIT //** 2026-10-14, default branch `main`  
> **SCOPE //** `SelectorDial` + `SelectorSlider`; `IndexRail` is adjacent and **not** silently folded into this family  
> **WRITE SAFETY //** this document alone changes no runtime QML or Git operations

## 0 // DECISION AND INTENT

The operator approved (a) keeping all 35 accepted SelectorSlider design decisions, (b) pausing Question 036, and (c) reorganizing the family around shared behavioral meaning, complete semantic profiles, explicit overrides, and deferred capabilities.

The Dial and Slider are **siblings, not clones**. Shared selection semantics should be consistent; circular and linear mechanics need not expose the same features or visual geometry. Do not back-port proposed Slider capabilities into a functioning Dial merely to achieve nominal feature parity.

An approval of a possible configuration is **not** an instruction to immediately implement every variant, expose a property for each detail, or retrofit live users.

## 1 // VERIFIED RUNTIME BASELINE

Read against `main` on 2026-10-14:

- `components/SelectorDial.qml` (blob `f1fd52fe200dba8151e67d8c44fac9655fc65d0e`): modes `discrete`, `continuous`, `zones`; discrete rotation uses the circular option ring, while bounded continuous/zones modes default to a 300-degree active arc with a 60-degree gap centered at six o'clock. Existing numeric operations report after settling, not as continuous live updates. Includes pending preview/commit state, keyboard stepping, deliberate flick inertia, typed selection/value requests, colored option and focus feedback, and independently supplied operation progress/status.
- `components/SelectorSlider.qml` (blob `f16a95897b18597784741b81e9c1636e85036e6f`): vertical discrete-index selector, 40px width; count/currentIndex and indexRequested; track/ruler, animated 28x52 thumb, wheel + pointer interaction, per-position activityPoints and separate accent/handle/activity colors. Index requests occur while dragging across selections; this is **not** a release-to-commit implementation.
- `components/IndexRail.qml` (blob `27ddb578c6fa77385271a715b564f360bdbdb53a`): an adjacent, simpler index rail. Audit independently before proposing its migration.
- `widgets/GitW.qml` (blob `352c022058949f49b69bf121fd31e963b91082fa`): REPO and REMOTE are the concrete live Slider users, mounted on the Git control page. REPO calls `gitService.selectRepo(index)` on `indexRequested`; REMOTE selects the chosen branch. Existing colors, geometry, immediate-change behavior, remote activity illumination, and service implications are compatibility constraints.
- `tests/fixtures/SelectorDialVariants.qml` (blob `236084af5473016f6951d6511dc5672520e2b2e2`): current temperature numeric and named-zone demonstration variants.

The above are the **2026-10-14 historical source snapshot**, not the
current full implementation inventory. Subsequent operator runtime tests
confirmed the Git REPO and REMOTE pilots and Hospital FLOOR interaction;
Git experimental controls were later removed by operator request. Immediate
repo/floor context updates while dragging remain the intended normal
workflow. Do not reinterpret release-preview as a replacement default.

## 2 // FAMILY CONTRACT (CORE)

These terms must mean the same thing in both controls:

| Concept | Family meaning | Invariant |
| --- | --- | --- |
| **Committed value** | Value acknowledged by the owning module as selected | A visualization may not imply unacknowledged execution |
| **Preview value** | Candidate value indicated during pointer/key/wheel motion or pending travel | May differ from committed value; must be visibly identifiable when shown |
| **Request** | Intent emitted to the owner to perform/update the selection | Owner remains authoritative about accepted state; avoid duplicate or late stale requests |
| **Commit policy** | When requests are emitted: live changes or release/settling | A profile establishes the default; a legacy instance may override it |
| **Operation state** | External idle/loading/success/error/progress feedback | Never infer real external activity merely from hover, animation, selection, or a glow |
| **Cancellation** | End an unfinished preview without committing it | Revert uncommitted preview to last owner-acknowledged value; already-live committed effects are not retroactively undone |
| **Interruption** | New pointer/input intent supersedes motion toward a previous destination | Resume direct control at current visual position; do not teleport or queue stale target commits |
| **Focus/input** | Keyboard, wheel, pointer and track requests reach the same logical selection machinery | Focus must be visible without hover; steps must not accidentally acquire flick inertia |
| **Semantic color** | Colors communicate component/operation identity independently of interaction intensity | Focus, hover, press, preview and operation feedback do not indiscriminately replace identity colors |

An interaction may drive several visual layers (focus, hover, drag, pressed). Compose configured layers coherently, preserve stacking, and limit excessive combined bloom. Per-cluster glow is a visual recipe; it is not separate application state.

## 3 // SEMANTIC PROFILES (PROPOSED COMPLETE DEFAULTS)

A profile supplies coherent behavior. Instances provide the owner/data model and specific visual identity. No per-instance checklist of dozens of settings should be necessary.

| Profile | Model and commit | Motion and input | Track/readout default | Intended use |
| --- | --- | --- | --- | --- |
| **INDEX** | Named discrete index; preview then commit on release/settle for **new** instances | Single handle, one-position keyboard/wheel steps, gentle settling, hard endpoints, inertia off | Unfilled track; readable ruler; committed readout fixed; preview readout follows handle | Repo/remote and other item indexes |
| **VALUE** | Continuous numeric value; live commitment for **new** instances | Single freely movable handle; hard endpoints; no flick inertia by default | Filled minimum-to-value track; sensible unit/precision display | Volume, brightness |
| **STEP** | Discrete numeric increments; preview then commit on release/settle | Single handle with physical detents by default; animated steps and settling | Major/minor ticks with readable labels, optionally filled, numeric/unit readout | Zoom, stepped controls |
| **RANGE** | Lower/upper bounds; preview then commit on release for **new** instances | Dual handles; individual and whole-range dragging; hard stop when handles meet | Highlight selected interval; two distinguishable readouts; no inertia | Frequency/interval filters |

Common across profiles unless specifically overridden: direct track interaction, boundary-safe visual movement, visible keyboard focus, cancel-uncommitted-preview semantics, configurable disabled appearance (dim-all default), per-cluster glow recipes, meaningful readout formatting, automatic label-density and collision-avoidance defaults.

**Orientation** is a geometric option, not a reason to multiply profiles: vertical/horizontal, reversed endpoints, and minimum/maximum/center/custom track-fill origin are possibilities. **Default profile recipes are suggestions pending isolated verification**, not automatic migrations of existing live instances.

**RANGE limits are not settled**: Decision 034 permits a zero-width interval at hard collision. Decision 036 (minimum/maximum permitted width) remains paused. Do not invent a required minimum or maximum range width. Existing track endpoints always bound values.

## 4 // OVERRIDE ORDER AND PUBLIC SURFACE

Preferred precedence:

1. **Core invariants**, which cannot be overridden into invalid state or false operational feedback.
2. **Profile recipe**, which supplies complete defaults for purpose.
3. **Application identity recipe**, such as REPO/REMOTE palette, activity treatment and semantic labels.
4. **Explicit per-instance overrides**, used only to preserve legacy behavior or meet a demonstrated need.
5. **Owner state**, which is authoritative over commit acknowledgment and external operation status.

These layers do not imply five QML objects or a large public API. Build the smallest implementation that demonstrates the contract. Favor internal helpers and small cohesive configuration objects over per-effect settings. Do not introduce a new shared base-class dependency until two actual consumers need it.

Illustrative future usage, **not existing API**:

~~~qml
SelectorSlider {
    profile: "index"
    // owner supplies items/current selection + request handling
    // appearance inherited from application identity
    // legacy Git immediate requests use a documented compatibility override
}
~~~

Never treat this example as usable current QML until the properties actually exist and are verified.

## 5 // CLASSIFICATION OF APPROVED SLIDER DECISIONS

| Decision IDs | Class | Treatment |
| --- | --- | --- |
| 001–003 | Core + profile | Both commit modes; discrete preview/release vs continuous live; independent preview/commit states |
| 004–007 | Profile + reserved | Free vs detent, settling, optional deliberate-flick inertia (off by default on Slider), hard vs elastic endpoints (hard default) |
| 008–014 | Core | Catch current motion; redirect latest intent; animated keyboard/wheel and track clicks; track-to-drag handoff; pointer outside track; safe cancellation |
| 015 | Core + override | Disable input; dim all by default; optionally keep informational content readable |
| 016–021 | Visual recipe | Independent per-cluster intensity/timing/extent/layering and front/rear arrangement; no need for settings on every instance |
| 022 | Reserved | Movement glow and optional trailing effect, with trails off by default; never fabricate activity |
| 023–024 | Core visual grammar | Focus visible without hover; compose simultaneous interaction glow layers without overwhelming bloom |
| 025–029 | Readout recipe | Distinct preview and committed readouts; placement, collision, timing, unit/name/number/custom formatting; fixed committed + handle-following preview defaults |
| 030–032 | Geometry/profile | Fixed/adaptive/custom tick placement, major/minor tick labels/glows; fill/segmented/custom ranges; orientation and fill origin |
| 033–035 | RANGE | Single default for ordinary sliders; dual range handles, optional hard/push/cross collision (hard default), whole-range drag default preserving width |
| 036 | **Paused** | Do not decide or implement additional minimum/maximum range-size policy without a concrete use case and operator decision |

Approved configuration capability should be represented as documented future potential when unnecessary for the first working profile. No previously approved decision is revoked.

## 6 // LEGACY COMPATIBILITY BOUNDARIES

### Git REPO / REMOTE

- Preserve **REPO left**, **REMOTE right**, sizing, placements, labels and existing handle/slot/ruler composition.
- Preserve magenta/orange REPO treatment and orange/cyan REMOTE treatment, including true remote-activity lights and their click-to-select behavior.
- Preserve **immediate request-on-index-change** and wheel/index semantics until the operator separately approves changing them. Generic INDEX's release-to-commit default must **not** automatically apply to these legacy instances.
- Preserve GitService repo-refresh and branch-selection consequences. The slider shall not issue extra requests as a side effect of preview, delayed animation or readout rendering.
- Keep the existing closed-menu guard that avoids repeated remote activity-model scans.
- Runtime verification must be performed on operator's actual Quickshell setup; source inspection alone cannot certify no regressions.

### SelectorDial

- Preserve discrete circular rotation and the bounded 300-degree arc / 60-degree six-o'clock gap for continuous and zone modes.
- Preserve current release/settle commit timing for numeric mode until an approved migration; VALUE's proposed live default must **not** silently change current Dial.
- Preserve deliberate-flick motion, center operation ring/status, options and focus behaviors; avoid forced superficial parity with Slider.
- Operation state is supplied by owner; failure or activity states must not be mistaken for a selection commit.
- Shared behavior should be extracted only after observing at least two real consumers or a narrow test-backed duplication.

### IndexRail

Outside this foundation's implementation scope. Treat as a separate audit target; do not replace it solely because the names resemble one another.

## 7 // MINIMUM IMPLEMENTATION SLICES AND GATES

| Slice | Intended work | Merge/acceptance gate |
| --- | --- | --- |
| **F0 // Foundation** | This MODEL contract, profile recipes, legacy compatibility and test matrix | Operator review; no runtime source edits |
| **F1 // INDEX mechanics** | Preview/committed separation, input motion/cancel safety, coherent preset, focused tests | New fixture passes; Git REPO/REMOTE side effects unchanged; operator runtime sign-off before replacing legacy behavior |
| **F2 // VALUE** | Single-handle numeric domain, fill/readout defaults, live vs release profiles | Numeric boundary, precision, input and owner-request tests; existing Dial stays unchanged |
| **F3 // STEP** | Quantized values, detents, readable ticks, test demonstration | Detent stability, keyboard/wheel one-step and preview/commit verification |
| **F4 // Dial parity audit** | Compare actual semantics and shared reusable patterns | No unrequested Dial behavior change; demonstrated benefit before extraction |
| **F5 // RANGE (deferred)** | Dual handles, whole-range dragging, collision modes, dimensioned bounds | Only after concrete use case and Decision 036 resolution |

No slice automatically grants merge authorization. Check shared-file ownership, current main, QML imports and concurrent Hospital work before edits. Prefer narrow branches/PRs and independent tests.

## 8 // ACCEPTANCE TEST MATRIX (REQUIRED BEFORE LIVE MIGRATION)

### Shared behavior

- Preview differs visibly from committed value without falsely indicating completed operation.
- Release-to-commit produces **one** final request after settling; live mode produces only actual value changes, without duplicate requests.
- Escape/cancel/disable during unfinished release-based interaction restores owner-committed selection and halts pending animations.
- Mid-animation pointer catch and second target request redirect from visible position with no teleport and no stale late commit.
- Track click animates; press-and-drag transitions smoothly; keyboard/wheel emits one mechanical step and does not acquire inertia.
- Out-of-bounds pointer motion respects configured retention/stop policy while handle stays physically clamped.
- Empty/single-entry models, disabled state and invalid range endpoints do not produce invalid values or requests.
- Focus/hover/drag glow stacking remains legible, hue-consistent and clipped only where explicitly intended.
- Value formatting does not change underlying numeric state or round away required precision.

### Legacy Git and Dial regression

- REPO drag/wheel/activity behavior remains equivalent, and repo switches/refreshes only for actual selected changes.
- REMOTE selection remains equivalent; activity indicators reflect real model points and can be clicked.
- Git layout/colors/glows and overlay hitboxes do not change without individual approval.
- Dial discrete, numeric and zone fixture behavior remains intact, including gap position and selected/preview relationship.
- No QML load errors, binding loops or missing imports; no new owner-service calls from passive visual animations.

### Deferred RANGE tests (only when implemented)

- Hard collision allows handles to meet without crossing; push and role exchange modes retain valid ordered bounds.
- Dragging the whole interval preserves its width and clamps at track boundaries.
- Handle-specific preview/commit and visual feedback stay distinguishable; pending Decision 036 is resolved first.

## 9 // IMPLEMENTATION STATUS // 2026-10-15

- **F0 // Foundation:** accepted architectural direction; this contract is
  retained as a design reference, not a claim that all profiles exist.
- **F1 // INDEX:** opt-in preview-release mechanics implemented and the
  release flick corrected (PR #270). The operator verified Git REPO, REMOTE
  and Hospital FLOOR pilot behavior. At the operator's direction, Git's
  INDEX LAB / LIVE REPO / LIVE REMOTE test buttons were removed (PR #274)
  and both Git selectors use immediate navigation again. Hospital's
  unobtrusive LIVE FLOOR test toggle was deliberately kept.
- **F2 // VALUE:** initial opt-in vertical numeric slider and mock
  percentage/temperature fixtures implemented (PR #278). Standalone
  Quickshell launch fixed in #279. The operator confirmed the demos work
  and look right. This is a first-slice runtime PASS, not comprehensive
  edge-case/device-integration certification.
- **F3 // STEP:** initial opt-in numeric detent profile, standalone
  mock, and source contracts implemented (PR #282). Operator runtime
  PASS: smooth, subtle and individually perceptible detents, without
  abrupt snapping. Preserve its accepted movement character.
- **F4 // Dial parity:** read-only source audit documented in
  `MODEL/components/selector-dial-slider-parity-20261015.md`. Common
  selection/owner semantics align; Dial inertia, curved geometry and
  settle-commit timing remain deliberately separate. No Dial code
  refactor proposed.
- **IndexRail:** read-only findings are in
  `MODEL/components/index-rail-audit-20261015.md`. No code migration.
- **F5 // RANGE:** first isolated dual-handle prototype implemented under
  `selectorProfile: "range"` with an internal `SelectorRangeSurface`
  and separate `SelectorRangeTest.qml` mock. Both endpoints can be moved
  individually, or the whole interval moved without changing its width;
  hard collision allows zero-width intervals. Owner request commits on
  pointer release. **Operator Quickshell runtime acceptance is pending**.
  Decision 036 remains paused: no additional minimum/maximum span imposed.
  Push/cross collision alternatives and other advanced recipes are reserved,
  **not implemented or implied to be approved**.

**Operator priority:** moving a Git/Hospital index must continue to show the
real repository, branch map, and floor context changing during the drag.
An isolated preview number is not a substitute for that live information.

No decision marathon is required to use a selector: choose a profile for
normal behavior, inherit the application's visual recipe, and override
only demonstrated exceptions.
