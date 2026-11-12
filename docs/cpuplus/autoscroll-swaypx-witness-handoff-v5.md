# CPU++ → SwayPX // Autoscroll Pointer Witness Handoff

> **READ-ONLY SOURCE AUDIT / CROSS-ROOM DEPENDENCY.** No compositor changes, SwayPX ownership transfer, production activation, privileges or local machine edits are authorized here.

## Verified source

PATIENT (current) // `kudokudo1/The-Post-Apollo-Project`

ROOM // CPU++ Mouse & Touchpad / Universal Autoscroll · Stage 5

STAFF ROLE // Hospital-compatible external DOC

DOWNSTREAM PATIENT // `kudokudo1/Post-Apollo-SwayPx` (compositor), current audited `master` head `2d91c5926b1a86679a64a53511667cba54a417c2`; recheck before surgery.

The compositor source includes:

- `sway/input/cursor.c`: `node_at_coords(seat, lx, ly, surface, sx, sy)` calls `wlr_scene_node_at`, walks scene descriptors (including view/container/popups/layer shells), and resolves the output/workspace if no suitable window is hit. It can return no view/target for layers and unmanaged surfaces. The cursor exists inside the compositor as `seat->cursor->cursor->x/y`; this code should not be approximated by client-side `GET_TREE` rectangles.
- `sway/ipc-server.c`: the inherited public i3/Sway IPC server handles general requests. Its `GET_SEATS` focus is keyboard focus, not a pointer-under-cursor witness.
- `sway/scene_descriptor.h`: source-side scene descriptor typing for window/view/layer targets. A compositor-origin witness should distinguish pointer target type, and **refuse** unsupported cases rather than fall back to the keyboard-focused window.

The Stage 5 CPU++ validator (`services/input/AutoscrollPointerWitness.py`) implements a candidate-data contract but does **not** authenticate the producer. The experimental evdev driver now rejects live operation before mouse access until that verified compositor source exists.

## Proposed narrow compositor contract (not yet approved)

The owning SwayPX team should evaluate a strictly opt-in, temporary witness handoff associated with a single physically selected middle-button press.

Evidence should bind, in one compositor-owned event:

1. Exact seat and source physical-pointer identifier.
2. Monotonic timestamp and one-time activation generation, with no reusable/replayable event.
3. Actual pointer hit-test at that moment, with a positive target identity; popup/layer/unmanaged cases explicitly differentiated or denied.
4. Output name, output-local logical coordinates, output geometry, scale, and generation so the CPU++ broker can detect monitor rearrangement.
5. A trusted, broker-specific delivery channel with a revocable lifetime, process/peer authentication, and no permanent public global-cursor-position API.

Privacy/safety: revealing arbitrary global cursor location and target through generic Sway IPC to all clients would weaken Wayland's normal isolation. Prefer one dedicated, explicitly authorized broker witness, and reject stale/missing target or any concurrent native Scroll Lock ownership. Do not install keylogging hooks or broad input-group privileges as a workaround.

The overlay must remain **input-transparent** and unmount when its witness is revoked. It must never change the real pointer's focus in order to discover the target. A compositor-owned Escape cancellation path should be independently scoped to an actively authorized autoscroll session, with an immediate STOP even on service loss.

## Suggested independent tests in a disposable compositor

- Correct output and compositor hit-test target at middle-click, including Brave, Kitty, Zellij, popups, a layer-shell overlay, and an unfocused window beneath the pointer.
- Monitors with negative logical coordinates, differing scales, disconnected/rearranged outputs, and stale event timestamps.
- Wrong UID/broker, replaced process, duplicate activation generation, concurrent Scroll Lock, and revoked subscription.
- No source when no trusted target exists. No output after focus/target loss, Escape, second middle click, STOP command, driver crash or compositor shutdown.
- Confirm visual arrow position without click interception or pointer/keyboard focus change.
- Production stays disabled until operator-authorized actual SwayFX hardware testing.

## Ownership / authority

This document is a **Chart Suggestion / handoff**, not a registered live Hospital assignment or approval to edit SwayPX. The compositor owner must explicitly accept the dependency and change scope. Stage 5 in CPU++ stays bounded to source contracts, tests, and fail-closed gating. Current validated application PRs are [#1940](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1940) (reconciliation) and its dependent [#1943](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1943) (witness gate).

## Recovery / NEXT

Keep `trusted_compositor_pointer_provider()` returning `None` until an authenticated producer passes independent review. Maintain the existing Sway Scroll Lock fallback; no live autoscroll or global Escape installation from the CPU++ Room. Once SwayPX ownership is assigned and a real pointer witness producer is proved in an isolated compositor, update the CPU++ broker and repeat the full input/overlay/STOP matrix. Final user acceptance remains separate from CI success.
