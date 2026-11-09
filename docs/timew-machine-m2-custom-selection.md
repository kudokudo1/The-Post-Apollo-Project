# MACHINE M2 // Optional custom selection in automatic SAVE

**Patient:** The-Post-Apollo-Project  
**Room:** TimeW MACHINE / exact desktop restoration  
**Role:** DOC succession · GitHub repository scope only  
**Status:** Dormant backend proposal, not connected to live TimeW UI  
**Parent:** M2 automatic capture coordinator #1637, native SAVE gate #1638

## Operator intent

Saving the desktop should require **one SAVE DESKTOP click**, without first
clicking CAPTURE PREVIEW. All monitors, workspaces and windows are included
by default. A user may optionally select individual monitors, workspaces
and windows to save only part of their working layout, while preserving
the ability to save everything.

The selected window must be unambiguous even when there are many Brave
windows with the same app ID. An app ID alone is never sufficient identity.

## Implementation

`services/time/MachineCaptureSelectionV2.py` provides pure
`select_geometry(geometry, selection=None)`. The optional selection
object contains only these **include** allowlists:

| Field | Entry | If omitted or null | If [] |
| --- | --- | --- | --- |
| `outputs` | Connector names | All outputs | Invalid: need at least one |
| `workspaces` | Workspace names | Every workspace on selected outputs | Save no workspaces |
| `windows` | Checkpoint-local canonical window UUIDs | All windows in selected workspaces | Save no windows |

An explicit list never silently adds a missing entry. Invalid, duplicate
or stale identifiers are refused. Choosing a window on a workspace not
selected, or a workspace on a monitor not selected, is an error, not
implicit parent inclusion.

A saved window's tiling branch is kept only when selected. Unselected
windows and now-empty nested container branches are pruned. Retained
container layout, original split ratios and measured window rectangles
are **not** reflowed, scaled or altered. A partial checkpoint therefore
describes where the selected windows *used to be*, not a claim that the
remaining windows would retile into an equivalent full arrangement.

The complete resulting tree is validated against its indexed windows and
workspace/output relationships by the existing v2 storage validator.
All included window rectangles must match their corresponding tiling
branches. This is crucial for a future exact-placement restoration planner.

`MachineCaptureSaveV2.capture_and_save(..., selection=None)` applies
the filter **after** two complete Sway observation rounds have verified
no observed layout changes and **before** deriving v1 compatibility data.
Then it invokes the existing atomic `save_pair` writer. There is no
second storage path, standalone preview prerequisite, database schema
migration or new user-visible button.

## Stable selection identity limitation

The current M2 capture coordinator allocates checkpoint-local UUIDs
fresh for each SAVE request. These UUIDs are not stable between captures
or across reboots. Therefore a future CUSTOMIZE interface cannot hold
a key from a stale preview and simply pass it to an unrelated capture.

Before binding the custom UI, build one explicit same-capture selection
transaction: show a current capture's window keys to the operator, let
them select, then revalidate that same capture and its ephemeral Sway
identity mapping immediately before committing. If any selected window
has changed, refuse and offer a fresh selection. Do not infer identity
by identical app IDs, titles or ordering. The current work establishes
filtering semantics and a test seam, **not** that future UI binding.

## Verification

`tests/timew/test_machine_capture_selection_v2.py` uses two fictional
monitors, two Brave windows, and a floating Kitty client. It verifies:

- default SAVE includes all three windows and both outputs;
- output selection keeps dependent workspaces and windows;
- selecting one Brave window prunes only the other Brave branch;
- selecting no windows/workspaces can represent an empty workspace layout;
- duplicate and stale identifiers, orphan windows, unknown fields and
  excluded monitor dependencies refuse before persistence;
- no private window titles, PIDs or monitor serials are stored;
- invalid scope does not create a database;
- successful scoped and complete SAVEs share the existing atomic SQLite
  writer and retain separate independently loadable checkpoints.

The existing isolated two-output stock Sway test additionally saves
**both** a full desktop checkpoint and a first-monitor-only checkpoint,
then rereads both from private temporary SQLite. Both runs use the
same guarded capture coordinator.

## Permissions and recovery

- No changes to `MachineCheckpointStore.py` or saved v1 rows.
- No writes to the operator's real home directory, browser profiles,
  Quickshell settings or running compositor.
- No app session/tab capture, local activation, shell command replay or
  restoration. The custom scope API is dormant until user-facing workflow
  decisions and approvals are verified.
- CI validates headless **stock Sway**, not Fedora SwayPX pixel-fidelity.
- No merge or production activation without required authority.

## NEXT

1. Pass custom scope CI and real headless Sway scoped-save test.
2. Design the custom selection **UI-to-capture identity binding** so
   multiple Brave windows can be distinguished meaningfully by the operator.
3. Add checkpoint naming and optional notes to the same stored record.
4. Replace mandatory CAPTURE PREVIEW with one-click normal SAVE, retaining
   optional inspection and advanced tools.
5. Continue Brave session capture and exact geometry restore only after
   verified app identity correlation and safe conflict policy.
