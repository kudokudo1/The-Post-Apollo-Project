# MACHINE M1o // Read-only recovery review surfaces

**Status:** Operator-requested functionality milestone, draft implementation.
No executable recovery control, operator approval, automatic retry, rollback,
local workstation change or Hospital/PX authority is added.

## STORED menu

After selecting a saved checkpoint:

1. **OPEN SAVED METADATA** then **RESOLVE LIVE** (existing controls).
2. Select a live candidate with the existing arrows.
3. **REVIEW MOVE** is enabled only when the selected candidate is uniquely
   classified as `candidate`. It sends the saved checkpoint ID/document and
   transient candidate metadata to a fixed read-only Python adapter on stdin.
   The adapter performs a new Sway read and M1n's review/preflight validation,
   but **discards the in-memory approval challenge** and returns only a
   non-executable app/source/destination description.
4. **CHECK INTERRUPTS** reads pending M1l operations from the suggested
   separate operations journal and runs M1n's read-only reconciliation once.
   It shows a clean state when the journal does not exist, or one advisory
   interrupted entry at a time with previous/target workspaces and warnings.

These are **reviews**, not approval buttons. No `CONFIRM`, `APPLY`,
`RETRY`, `UNDO`, `DISMISS PENDING` or token-generation action exists in
TimeW. Move reviews never call `MoveApprovalGate.approve()`.
`MachineMoveReviewRead.py` supports exactly `preview` and `pending`.
It cannot write to the SQLite journal and has no movement command dispatch.
It uses the current Sway read-only API and the separate operations journal
only on demand, with no new poller or background service.

## Safety boundaries

- Request bodies are bounded and submitted on stdin, not exposed in argv.
- An action review is usable only for an opened checkpoint and selected
  candidate; changing checkpoint, live selection or recapturing clears it.
- Current Sway state is revalidated at review time. It is not frozen, and
  moving windows later would require **another** fresh action validation and
  a separate operator approval step.
- The interrupted-operation result is advisory. Sway container IDs are not
  historical process identity. An apparent success never clears a journal
  safety lock or replays a move.
- Journal absent: `NO UNRESOLVED MOVE OPERATIONS`; no DB created.
- Error, unsafe journal or malformed input: explicit unavailable state.
- No titles, process IDs, browser data, screenshots or commands in the UI.

## UI debt retained

This milestone adds one compact row and conditional detail lines in STORED.
The operator asked to defer broader UI redesign, button ordering,
color semantics and marker overflow repairs until core behavior works.
Those decisions remain open and are **not** solved here.

## Verification

Run `python3 -B -I tests/timew/test_machine_move_review_read.py` and
`python3 -B -I tests/timew/test_machine_move_review_ui.py`.
They cover missing/unsafe candidates, private metadata rejection,
no-op/pending journal, read-only result fields and unavailable paths.
The TimeW foundation suite continues checking existing functionality.
A live click-through acceptance test remains operator-owned after merge.

**No production live move path is enabled by this milestone.**
