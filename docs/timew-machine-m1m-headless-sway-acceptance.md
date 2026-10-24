# MACHINE M1m // Disposable Sway integration verification

**Status:** CI-only headless compositor test, not a live user feature.
**Scope:** one isolated existing-window move from workspace 1 to an already
populated workspace 2, using M1k's injected action pilot and M1l's durable
before-state journal. No changes to TimeW, live desktop, Fedora, SwayFX
configuration, connected user application windows, or actual user databases.

## Isolation boundary

The test refuses to run without BOTH `CI=true` and
`GITHUB_ACTIONS=true`. It creates a private temporary XDG runtime/data/config
directory, removes inherited `SWAYSOCK`, `I3SOCK`, `WAYLAND_DISPLAY`,
`DISPLAY`, `WAYLAND_SOCKET` and D-Bus session details from the child process
environment, then launches its **own new headless Sway process** with
`WLR_BACKENDS=headless` and pixman rendering.

**Every** Sway IPC call uses `swaymsg -s <private child socket>`, whose resolved
path must live inside that temporary runtime directory. Thus the test cannot
use the operator's active compositor socket even if a surrounding
environment inadvertently defines one. All subprocesses run in their own
process groups and are stopped in cleanup. Temporary journal data and process
logs are removed with the temporary directory.

The isolated workspace is populated using two `foot` terminals with
distinct synthetic app IDs (`machine-ci-window`, `machine-ci-anchor`).
A saved metadata-only checkpoint asks for a move of the first unique window
from workspace 1 to existing workspace 2; the second terminal anchors
workspace 2 in the tree.

## Acceptance checks

1. The headless IPC endpoint and Wayland display belong to the disposable Sway.
2. Both windows appear on the expected original workspace.
3. A manual preview of the move has `executable=false` and makes no commands.
4. A deliberately wrong transient window ID is rejected without creating a
   journal entry or dispatching a move.
5. Exactly one eligible move is sent, scoped by `[con_id=N]`, and the target
   workspace is explicitly named.
6. The command reply is accepted and a **fresh** `get_tree`, `get_workspaces`
   and `get_outputs` observation confirms the same window reached workspace 2.
7. M1l's private journal shows `verified_moved` and records the prior
   placement; there are no pending operations or automatic Undo.
8. The anchored, unrelated window stays on workspace 2.
9. Reuse of the stale approved request is refused.
10. Cleanup terminates disposable clients and compositor only.

CI installs stock Ubuntu `sway` and `foot` in a dedicated GitHub Actions
workflow `.github/workflows/timew-machine-headless.yml`; it does not alter
the operator's local system or run from `TimeW.qml`.

## What this does not certify

One working synthetic headless session is **not** proof of SwayFX on the
operator's real dual-monitor workstation. No focus/keyboard handoff,
hot-unplug recovery, security boundary under adversarial IPC changes,
compositor crash recovery, or production per-action consent has been
accepted. It does not activate the M1k pilot or store any local operator data.

The next gate is an explicit, nonce-bound *operator-reviewed approval* with a
fresh revalidation and separately approved opt-in live movement. Before any
live operation, review actual SwayFX behavior on a disposable session using
a matching version. UI cleanup remains intentionally deferred.
