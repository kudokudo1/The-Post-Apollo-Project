# CPU++ Universal Autoscroll // Stage 4: Capability Inspection and STOP

> **Source-only, not activated.** This stage follows the green Stage 2 input driver and Stage 3 private STOP/overlay contracts. It cannot start the driver, move the cursor, add a keyboard binding, or turn on Windows-style autoscroll.

## Implemented mechanisms

`services/input/AutoscrollOriginProbe.py --inspect` performs a **read-only** capability inventory:

1. Checks whether Sway and Wayland session sockets are advertised.
2. Queries Sway `GET_OUTPUTS` for active output names, sizes, signed layout coordinates and scale; validates duplicate names, bounds and scale.
3. Queries Sway `GET_SEATS` to detect one unambiguous seat; **seat focus is not pointer position**.
4. Optionally runs `wayland-info` to inspect advertisements of `zwlr_layer_shell_v1` and `zwlr_virtual_pointer_manager_v1`.
5. Reports whether `evdev` and `/dev/uinput` appear accessible (no device opens), and whether the current private STOP endpoint exists.

No discovery result proves pointer position, pointer-under-cursor window, overlay provenance, or permission to inject virtual scroll events. Thus **every response sets `pointer_origin_verified=false`, `runtime_enabled=false` and (for complete inventory) `overlay_allowed=false`.**

`ScrollModeSettings.qml` exposes two operator-facing actions exclusively from the existing Universal Autoscroll preview in CPU++ Mouse:

- **CHECK GLOBAL INPUT SUPPORT** invokes the read-only probe, displays protocol and output count, and continues to refuse Universal Autoscroll activation.
- **EMERGENCY STOP EXPERIMENT** invokes `AutoscrollStop.py --stop` as a one-shot command, which sends a same-user `STOP\n` to any separately approved foreground experimental run. An acknowledgment means **the request was received**, not that process exit has been verified. No new experimental service is launched by this action.

No Sway Scroll Lock, Kitty, Zellij, shared scrollbar, production permissions or shell root is modified.

## Why the final anchor is still blocked

Standard Sway IPC (GET_SEATS/GET_TREE) does not provide the global pointer position. The pointer-enter method used by wlroots cursor-location tools involves temporarily mapping an input-receiving layer-shell surface and triggering a zero-motion virtual-pointer event. That is an interesting proof of concept but it can take pointer focus and lacks a validated output/target attestation contract for this multi-monitor Post-Apollo use case.

Before production, we need independently verified, compositor-specific output-local cursor coordinates captured **at the triggering physical middle-click**, the target identity under the pointer, a non-focus-stealing overlay, and an operator-approved Escape cancellation binding (not broad keyboard capture). The Stage 3 overlay remains hidden without that witness.

Useful references:
- https://github.com/swaywm/sway/blob/master/sway/sway-ipc.7.scd
- https://github.com/cjacker/wl-find-cursor
- https://quickshell.org/docs/v0.3.2/types/Quickshell/QsWindow/

## Verification

- `tests/cpuplus/test_autoscroll_origin_probe.py` verifies two-output topology, negative origins, scale, invalid/duplicate outputs, no Sway socket, missing optional Wayland inventory, and proof the runtime gate never opens.
- `tests/cpuplus/test_autoscroll_capability_stop_ui.py` verifies manual-only probe/STOP buttons, accurate acknowledgment, and unchanged `autoscrollRuntimeAvailable: false`.
- Disposable Quickshell native smoke simulates capability/STOP responses; it never runs the real probe or emits scroll events.

## NEXT

Work remains to choose and independently verify the origin/target provider on real SwayFX. Preserve the STOP channel and the already-working Sway Scroll Lock fallback. Do **not** install a global Escape binding, grant raw input privileges, or enable uinput on the operator desktop until those gates pass and the operator separately approves the live change.
