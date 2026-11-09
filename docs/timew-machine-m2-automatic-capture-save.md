# MACHINE // M2 automatic capture-to-checkpoint coordinator

**PATIENT:** The-Post-Apollo-Project  
**ROOM:** TimeW MACHINE desktop restoration  
**STATE:** Proposed dormant coordinator, no TimeW/Quickshell activation  
**OWNERSHIP:** TimeW/MACHINE; preserves MachineCheckpointStore.py and the additive geometry owner from PR #1633  
**OPERATOR INTENT:** One SAVE action must automatically read and persist desktop state, without a mandatory CAPTURE PREVIEW step

## What changes

`services/time/MachineCaptureSaveV2.py` adds a single explicit
`capture_and_save(label=..., read_runner=..., store_adapter=...)` call.

When the user eventually presses **SAVE DESKTOP**, the approved UI should
invoke this operation rather than demanding a separate preview:

1. Read Sway `get_outputs`, `get_workspaces`, and `get_tree` on demand.
2. Generate distinct checkpoint-local UUID keys for each observed window
   container (including native `floating_con`), bound to the current
   compositor ID **only during capture**.
3. Project exact monitor geometry, nested workspace tiling and per-window
   rectangles through existing `MachineGeometryV2`.
4. Re-read the same three Sway observations immediately before saving and
   refuse a missing/replaced/moved/changed window, workspace or monitor.
5. Derive a strict v1-compatible checkpoint from the validated v2 projection,
   using one UTC instant for durable storage (display time is a future
   shared-Clock UI responsibility).
6. Call the already merged atomic `MachineGeometryStoreV2.save_pair` so
   v1 metadata and v2 detailed geometry are committed or rolled back together.

No intermediate CAPTURE PREVIEW or MARK is needed. The current widget is
**not wired** to this service yet. Optional monitor/workspace/window
selection and editable named checkpoints/notes are separate following
milestones; they will operate on the same underlying data, not a parallel
reimplementation.

## Exact guarantees and limitations

- Sway IPC provides **three separate queries**, not one atomic
  compositor snapshot. The second three-query observation detects changes
  visible across capture rounds; there remains a theoretical mutation window
  between the final check and SQLite commit. This stage must not be described
  as a provably atomic native compositor snapshot.
- If the desktop differs on the second round, the coordinator returns a
  bounded failure and does **not** touch the checkpoint database. It never
  tries an ambiguous best-effort association.
- It reads only fixed `swaymsg -r -t` data queries. No `command` IPC,
  compositor move, process launch, browser/terminal inspection, dynamic shell
  commands or continuous observer is introduced.
- Local per-checkpoint UUIDs are not durable Brave/Kitty session identities.
  No saved tab URLs, browser profiles, login contents, terminal commands,
  unsaved editor content, arbitrary app memory or filesystem data. Future
  native adapter and privacy/security decisions remain separate.
- The original v1 record schema stays intact. The additive writer preserves
  old checkpoint rows and rejects incomplete geometry writes.
- This implementation is dormant: a Python function with no CLI and no QML
  reference. It performs disk writes **only if explicitly invoked**.
  No change to live user data or local system is authorized by this PR.
- Captured timestamps are UTC internally, for unambiguous ordering. Future
  UI display must use shared Clock/local timezone rather than showing raw UTC.

## Verification

Synthetic test in `tests/timew/test_machine_capture_save_v2.py` supplies
two fake monitors, two Brave windows, and one floating Kitty window.
The test runner must observe exactly six fixed read-only IPC requests,
then confirms a full geometry record was stored atomically in a temporary
`XDG_DATA_HOME`. It also verifies:

- saved window dimensions, tiling, independent same-app identities,
  floating windows, output/workspace relationships;
- a pre-existing v1 checkpoint stays readable and in the original order;
- private titles, PIDs and output serials do not enter the geometry row;
- changed layout, changed ephemeral window ID, and altered floating position
  are refused without a save;
- duplicated generated checkpoint keys and invalid labels refuse;
- exceptions from the storage owner never appear as successful saves;
- all data is synthetic and isolated from the operator desktop.

The next acceptance gate is a disposable **real headless Sway** invocation
that uses the coordinator against a private compositor socket and temporary
SQLite storage, followed by an approved Fedora/SwayPX compatibility test.
Native Sway success is not production-ready desktop restoration.

## NEXT

1. Pass exact-head synthetic/source CI and existing v1/v2 regressions.
2. Verify the coordinator on an isolated real Sway compositor.
3. Add optional selection and checkpoint names/notes to the same transaction.
4. Build a simple SAVE DESKTOP UI that runs the coordinator without a
   separate preview step, using the shared local Clock time.
5. Extend to supported Brave/Kitty sessions with explicit permissions, then
   implement exact restoration with user visual acceptance.

No merge, local filesystem mutation, Quickshell reload or live activation is
authorized by drafting this contract.
