# MACHINE // one-click SAVE DESKTOP + capture-bound CUSTOMIZE UI

**PATIENT:** The-Post-Apollo-Project  
**ROOM:** TimeW MACHINE / desktop session restoration  
**ROLE:** DOC succession, external Hospital-compatible  
**STATE:** Repository implementation pending CI / operator visual acceptance; no local activation  
**Predecessors:** #1633 atomic store, #1637 automatic capture, #1638 native SAVE, #1640 selective capture

## IMPLEMENTATION

The root `widgets/TimeW.qml` MACHINE capture pane becomes scrollable and
places the ordinary daily workflow first:

- An optional checkpoint **name** input (blank = `DESKTOP CHECKPOINT`).
- **SAVE DESKTOP**: launches `MachineSaveBridgeV2.py save`, sends one
  bounded JSON request via **stdin** with `selection=null` and
  `review=null`; it performs its own two Sway read rounds and commits v1
  compatible metadata plus detailed v2 geometry in one SQLite transaction.
  No CAPTURE PREVIEW click is required.
- **STORED**: keeps the existing checkpoint listing and diagnostic/restore UI.
- **CUSTOMIZE**: an explicit read-only inspect; pick monitors, workspaces
  and individual windows, then click **SAVE SELECTED DESKTOP**.
  Refresh the capture if the layout changes.
- **ADVANCED**: retained older CAPTURE PREVIEW, manual timeline markers,
  inspect/exclusion and v1 metadata-only save. Legacy save is expressly
  labeled `SAVE V1 METADATA`, not a full desktop save.

The capture pane uses `Flickable` + existing `NeonScrollBar` pattern to
preserve control reachability in the 790px TimeW window, with orange SAVE
and navigation, magenta active customization/advanced controls, cyan
display/readouts, and the existing red close behavior untouched.

Local time displayed in the main MACHINE pane reuses `timew.clockReadoutText`
from shared TimeSettings/Clock presentation, not a separate UTC-only UI
clock. SQLite continues to store UTC absolute instants correctly.

## HOW CUSTOM WINDOW SELECTION BINDS

Two process actions share the already approved M2 capture/storage core.

**`inspect`** (no disk write):
1. Read Sway outputs, workspaces, and tree twice; refuse a changing layout.
2. Generate a random per-inspection UUID namespace.
3. Derive an opaque checkpoint-local window UUID from that namespace and
   the current Sway container ID, without exposing the numeric ID itself.
4. Compute a SHA-256 digest over the allowlisted geometry of the whole
   inspection frame, including those derived UUIDs.
5. Return the namespace/digest and display-only list of monitors,
   workspaces, app IDs and *measured* window rectangles. No titles, URLs,
   PIDs or browser data are returned.

**`save` with selection**:
1. Read another two Sway frames.
2. Reconstruct opaque window IDs using the inspection namespace.
3. Reject if any output/window/workspace geometry or compositor container
   identity differs from the reviewed full-frame digest.
4. Filter selected outputs/workspaces/window UUIDs through the existing
   strict `MachineCaptureSelectionV2` tree-pruning validator.
5. Atomically write one v1/v2 checkpoint using
   `MachineGeometryStoreV2.save_pair`.

A normal **SAVE DESKTOP** does not need the inspection or namespace.

The digest is **not** an authentication token or compositor transaction
lock. Sway IPC supplies successive reads, and the coordinator's checks
reduce but do not eliminate the time-of-check/time-of-use window. Identical
new application windows that happen to reuse a compositor ID and every
geometry detail could still escape detection, so this is not yet a native
stable application-session identity system.

## UX boundary and preservation

- CUSTOMIZE shows each Brave window by app ID, workspace, output and
  precise x/y/width/height. Distinct identical-app windows have distinct
  selection UUIDs, but titles/tabs are deliberately not inspected.
- The existing `MachineSelectionPolicy.validate` is reused for parent
  monitor/workspace/window selection consistency. Invalid dependencies
  show an actionable LOCATE ISSUE button; no silent dropping of selected
  child windows.
- CUSTOMIZE does **not** persist inspection data. Returning to CUSTOMIZE
  after a successful SAVE triggers fresh inspection, not a stale token.
- Normal SAVE remains all-inclusive. The old v1 metadata-only flow is
  still present under ADVANCED for continuity, not as the default.
- The stored checkpoint can contain precise geometry, but existing
  restore logic does not yet reconstruct exact positions or browser tabs.
  The interface explicitly warns of this limitation.
- Session-local MARK remains preserved under ADVANCED until the dedicated
  restorable named checkpoint/notes transition is implemented. It is
  labeled non-restorable rather than being silently redefined.

## VERIFY

`tests/timew/test_machine_save_bridge_v2.py` performs synthetic two-monitor
Brave/Kitty inventory review, one-window selected SAVE, default whole
desktop SAVE, original legacy-compatible SQLite reload, and changed-frame,
stale-layout, replaced-ephemeral-window and invalid-request rejection.

`tests/timew/test_machine_save_ui_contract.py` checks that the actual
TimeW root interface offers one-click SAVE, separate/custom actions, input
via stdin, current UI clock, scrollable capture pane, original advanced
controls and no legacy schema mutation.

The existing isolated stock Sway headless geometry workflow additionally
uses the new bridge to review **one actual** same-app window and persist
it to a temporary SQLite store, then verifies the window key, rectangle
and count after load.

CI is **not** live Fedora/SwayPX visual verification. Before production
activation, the operator must review the new controls, confirm layout
interaction, and grant separate local-write/Quickshell reload permission.

## WATCH OUT FOR

No real Brave tabs, groups, live page contents, Kitty shell sessions,
workspace tile-tree reconstruction or exact post-reboot window placement
is supported by this UI milestone. Existing v1 records are not
backfilled. The metadata-only v1 RESTORE path still operates separately.
The service does **not** launch apps, move windows or restore anything.

Only the new bridge `save` action may write the existing user-owned
`machine.db`, using the established atomic geometry writer. It has no
background task and is invoked only by an explicit user action.

## NEXT

1. Confirm exact-head CI and independent review.
2. Operator visual acceptance and separately authorized local activation.
3. Add real checkpoint notes/rename and unify non-restorable MARK into
   restorable annotated checkpoints.
4. Start native Brave window/session identity capture, with privacy
   controls and distinguishing page labels when authorized.
5. Implement geometry-aware exact RESTORE and reboot acceptance on SwayPX.

**No merge or production activation is performed by this PR.**
