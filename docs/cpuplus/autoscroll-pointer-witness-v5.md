# CPU++ // Universal Autoscroll Stage 5 · Pointer Target Provenance

> **Status: SOURCE CONTRACT IMPLEMENTED, LIVE POINTER CAPTURE DISABLED.**
>
> This is not the Windows-style autoscroll feature working on a real mouse. No compositor-approved pointer-position witness exists on this branch, and no local host, SwayFX configuration, input device, or keyboard binding has been changed.

## The concrete problem

Sway provides `get_outputs` monitor geometry and `get_seats` **keyboard-focus** identity. Neither returns the mouse cursor's compositor-global position or proves the surface beneath the physical pointer. The Stage 2 experimental evdev driver previously used keyboard focus as its target. That is an unsound inference for mouse scrolling, especially when the pointer is over a different window, popup, overlay or output.

Stage 5 closes that unsafe entrypoint: `AutoscrollEvdevBackend.run_live` now calls `require_verified_pointer_provider()` **before opening any physical input device or creating a virtual mouse**. The default `trusted_compositor_pointer_provider()` returns `None`; consequently, even an explicitly opted-in `--live` invocation cannot grab the mouse. Synthetic evdev tests may mock the provider inside the test process, but there is **no production environment variable, CLI flag, or JSON field** to bypass this gate.

## Pointer candidate checking

`AutoscrollPointerWitness.py` contains a pure validator for a future compositor-provided event at the actual first middle-click. Input evidence must be bound to:

- An exact seat and physical device identifier, plus a current activation generation.
- A compositor output name and **output-local** x/y, converted to layout coordinates (including negative monitor origins), without guessing scale or window position.
- A positive pointer-under-cursor target node, not merely the focused keyboard window.
- A monotonic event timestamp no more than 75 ms old and no more than 1 ms in the future.
- Identical validated output geometry and scale before/after the witness.
- A position inside exactly one active output. Overlapping or changed outputs, disconnected screens, stale/replayed samples, wrong devices, missing targets and extra self-declared `authorized:true` flags are refused.

**Crucial distinction:** Passing all those checks proves only *internal consistency*. Any process can invent plausible JSON. The resulting `PointerCandidate` therefore has `source_trusted=false`, `overlay_allowed=false` and `live_input_allowed=false`. No function currently converts that candidate to an authoritative compositor witness.

## Why the existing Wayland trick is not accepted as authority

The wlroots `wl-find-cursor` approach creates a layer-shell surface and obtains `wl_pointer.enter` coordinates after synthesizing zero relative movement. That can give a cursor position **on its own temporarily input-receiving surface**, but it does not prove the original surface under the pointer. Pointer focus may also change, and that technique is not equivalent to Sway-native scene hit-testing.

A full solution needs a verified compositor-origin event containing both output-local position **and hit-tested target** at the physical middle-click, delivered to a checked same-user input broker with freshness/generation binding. It also needs evidence that an overlay can display without changing pointer/keyboard focus, a reliable Escape cancellation integration, and independent hardware tests for Brave, Kitty and Zellij.

## Safety and recovery

Stage 3 private STOP and hidden anchor overlay and Stage 4 capability inspection remain intact. Nothing starts automatically. The existing native Sway Scroll Lock remains the functional alternative, with its per-device restore snapshot.

The experimental Stage 2 backend remains testable with **fake** uinput/mouse events in CI; those simulations are not evidence of live SwayFX behavior.

## Verification

Run:

`python3 tests/cpuplus/test_autoscroll_pointer_witness.py`

`python3 tests/cpuplus/test_autoscroll_evdev_backend.py`

The dedicated CPU++ Mouse workflow also checks all previous Sway, Kitty, Zellij, STOP, overlay, Wayland-capability and native isolated Quickshell tests.

## NEXT // Trusted provider design and compositor ownership handoff

Inspect the exact SwayFX compositor version and accepted IPC/Wayland extensions. If no existing supported source emits pointer-at-click hit-testing with output and node identity, this becomes a **compositor integration dependency** requiring the owner of that repository/Room. Do not silently implement compositor changes in the CPU++ Room. After authority, source identity and cancellation have passed, an operator-approved disposable headless SwayFX test can validate end-to-end operation. Actual desktop activation remains a separate explicit authorization.
