# MACHINE M1k // Single-window recovery pilot

**State:** Isolated implementation and mock-fixture test only. **NOT a live
desktop capability.** No Quickshell button, on-disk activation, default
command runner, or production CLI. Never infer authorization to execute a move
from a stored checkpoint, a preview, or an earlier user approval.

## Scope

One existing and uniquely identified *Sway window*, moving from a currently
known workspace to a different **existing numbered workspace** (1 through 999)
on an active output. The saved checkpoint's expected app class, workspace,
floating state and destination output must match freshly read Sway metadata.

Sway documents the selector `[con_id=N]` and `move container to workspace
number N`. The pilot produces exactly one no-shell argv command, and the
command runner is **required by the caller** (only synthetic runners are used
in CI). The source does not provide a CLI, Qt/Quickshell action, background
polling, a privileged helper or an automatic mode.

## Explicit approval contract for a future operation

The request contains only:

- `intent="single-existing-window-workspace-move"`
- `approved=true` for the test execution path
- `app_id` from the saved allowlisted checkpoint
- `con_id` from a transient live Sway read
- `from_workspace` from the currently observed window
- `to_workspace` from the approved saved destination

Preview does not require approval and **cannot execute anything**. The fixture
executor requires `approved=True` in its request *and* an explicitly injected
runner; no default command runner or connection to real Sway is supplied.
This is not sufficient authority for production. A future UI must require
contemporaneous operator approval tied to an immutable action ID, checkpoint,
current window identity and exact destination, and re-check at the moment of
execution. Old approvals must never be reused.

## Failure, before-state and rollback

The pilot produces a bounded before-state (`con_id`, `app_id`, source and
destination workspaces) and a **non-executable manual Undo preview**. It
re-queries Sway just before sending a move and immediately after sending it.
Only an accepted single Sway response plus a verified new window position
can produce `verified_moved`.

If Sway refuses and the original placement is still confirmed, it reports
`refused_no_confirmed_move`. All other ambiguous or raced results are
`uncertain_requires_manual_review`. It never tries an automatic rollback.
The in-memory before-state is **not a durable operation journal** and cannot
guarantee recovery if the process crashes.

A production gate still needs: a durable before-state journal prior to move,
verified Sway/SwayFX version behavior, cancellation/expiration handling,
real disposable-compositor acceptance tests, possible focus behavior review,
and explicit operator authorization before any live desktop mutation.

## Forbidden

No app launch/restart, window close, kill, focus command, screenshot, clipboard
read/write, workspace creation/deletion, floating/fullscreen toggle, UI
activation, network access, shell interpolation, or automatic Undo.

## UI later

Keep the existing **RESOLVE LIVE** result read-only and do not add an Apply
button in this pilot. Future UI should show exact source → destination,
what will change, before-state / Undo limits, and a per-window approval dialog.
The operator's deferred UI debt remains: sequencing guidance, marker/menu
overflow, and semantic color differentiation. Functionality is prioritized.

## Verification

`tests/timew/test_machine_window_move_pilot.py` injects synthetic Sway
responses and a fake command runner. It checks explicit approval, unique
candidate gating, stale IDs, duplicate windows, malformed/injected destinations,
command refusal, no movement, contradictory postflight, output drift, and
read-only Undo previews. No real compositor is touched.
