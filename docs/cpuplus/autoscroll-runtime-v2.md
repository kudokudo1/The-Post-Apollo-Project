# CPU++ Mouse // Universal Autoscroll · Experimental Runtime V2

> **STATUS: NOT ACTIVATED.** Source and synthetic tests only. No services, packages, permission grants, host configuration writes, or live mouse grabs are authorized by this PR.

## Mechanism

A selected physical mouse emits `REL_X`, `REL_Y` and `BTN_MIDDLE` events to Linux. When explicitly launched with existing permissions, `AutoscrollEvdevBackend.py` validates that it is a mouse-only character device, creates a replacement **virtual mouse** with evdev/uinput, and grabs only that physical mouse. The kernel releases the grab when the process closes/crashes; the driver also calls ungrab and closes the virtual mouse in `finally`.

The accompanying `AutoscrollMouseEngine.py` implements Windows-style click-toggle scrolling:

- First middle-click begins anchor mode, intercepting relative pointer motion.
- Movement away from the anchor establishes direction and scroll rate.
- Periodic ticks emit high-resolution Linux wheel events **even when the mouse stops moving**.
- Moving toward the anchor slows; crossing it reverses direction. Speeds and active duration are bounded.
- A second middle-click or another mouse button ends scrolling; focus loss, device disconnect, timeout, stale tick, signal or process exit cancels it.
- Outside active mode, normal mouse button, motion and wheel signals are passed to the virtual mouse except middle-click, which is reserved by this experimental service.

This is different from Sway's movement-only Scroll Lock, which remains independent. The active native Scroll Lock snapshot blocks the experimental driver. No keyboard device is opened and the virtual device never advertises keyboard keys.

## Read-only probe

`python3 -B -I services/input/AutoscrollEvdevBackend.py --probe`

The probe reports whether Python evdev, /dev/uinput write permission, SWAYSOCK, and the separate native Sway Scroll Lock snapshot are compatible. It neither opens the physical mouse nor creates a virtual device. It does not establish runtime compatibility.

## Manual experimental entrypoint (NOT approved for a user desktop)

`--live --device /dev/input/eventN` exists for an independently authorized laboratory test. It **requires** all of the following:

1. Non-root process plus `POST_APOLLO_AUTOSCROLL_EXPERIMENTAL=1` in its environment.
2. Exact operator-selected /dev/input/eventN or by-id symlink resolving to a physical event-character device.
3. Existing permission to read/grab the mouse and write to /dev/uinput. The PR grants **none**.
4. Mouse-only relative capabilities, no keyboard keys or absolute device controls.
5. A single, recognized Sway seat with focus and no concurrent native Scroll Lock snapshot.

The driver is **not wired to the CPU++ Apply button**, does not autostart, install udev rules, run as root, edit Sway/Kitty/Zellij, or restart Quickshell. All production and local changes remain operator-gated.

## Known blockers before claiming Windows parity

- **Anchor indicator**: standard Sway IPC does not expose arbitrary global pointer coordinates. A trustworthy compositor/overlay origin is required before rendering Windows-style directional arrows. This PR does not invent coordinates or steal focus with a fullscreen overlay.
- **Global Esc cancellation**: the prior pure JavaScript policy has an Escape event, but no global compositor-approved binding. This driver does not read keyboard streams just to catch Escape. SIGTERM/Ctrl+C stops the experimental process, and middle-click cancels the active scroll.
- **Target correctness**: Sway `get_seats` reports keyboard focus, which is **not** proof that the pointer was over that window at initial middle-click. A trusted pointer-target source must be added before any unattended/user activation.
- **Kernel + compositor behavior**: no real SwayFX wheel, pointer, multi-monitor, pointer-capture or hardware tests yet. Evdev/uinput semantics are unit-tested with fakes, not production-certified.
- **Security and resilience**: before live use, independently review the physical-device grab lifecycle, loss of focus during an active tick, modifier handling, device reconnect and end-to-end stop/rollback controls.

## Recovery / continuity

No recovery is needed while this branch stays unmerged/unexecuted. During an explicitly approved **foreground** test, exiting the process releases the physical mouse grab and closes the virtual device. No background daemon or service installation exists. Do **not** grant blanket `input` group access or autostart this driver as a shortcut.

## Tests

- `tests/cpuplus/test_autoscroll_evdev_engine.py`: rate with stationary mouse, reversals, deadzone, stop, target loss, invalid motion, time limits.
- `tests/cpuplus/test_autoscroll_evdev_backend.py`: fake device/uinput event path, restricted capabilities, single-seat focus, permission gate, deterministic teardown.
- Existing CPU++ Mouse workflow: Sway/Kitty/Zellij contracts and native disposable Quickshell smoke.

## Stage 3 // Private emergency stop + non-interactive anchor (source only)

- `AutoscrollStopChannel.py` creates a **private AF_UNIX socket** inside the current user's verified `XDG_RUNTIME_DIR/post-apollo`. On a live *separately approved* experimental run, `AutoscrollEvdevBackend.py` refuses to grab any mouse unless the private socket has been established, and stops if the socket disappears or is replaced. The STOP request must come from a process with the same Linux UID via `SO_PEERCRED`; any other message is refused.
- `AutoscrollStop.py --stop` sends the literal STOP command. Receipt is acknowledged, but **the ACK is not a claim that the process has fully exited**. The backend cancels and releases the grab in its cleanup. No service is started, no new permissions are installed, and no global keybinding is registered.
- `AutoscrollAnchorOverlay.qml` is a non-focusable transparent `PanelWindow` with an **empty pointer-input mask** and no reserved screen space. Its indicator is not displayed without explicit authorization, runtime verification, finite anchor coordinates, a matching trusted output name and in-bounds position. The overlay is **not instantiated by the running CPU++ application**. A disposable native Quickshell test loads it and checks the hidden/revoked behavior.
- **No actual pointer-position/target witness exists yet.** This stage does not inject unverified coordinates or claim that the anchor icon appears on the real desktop.
- Escape is **not bound globally**. The STOP channel makes a limited, same-user cancellation path available for later compositor-approved Esc binding, but keyboard hooks and arbitrary device access remain forbidden. Termination via SIGTERM/Ctrl+C is also available in a manually approved foreground test.

### Stage 3 tests

- `tests/cpuplus/test_autoscroll_stop_channel.py`: socket ownership, permission boundary, exact STOP bytes, malformed requests, existing-path protection and socket removal.
- `tests/cpuplus/test_autoscroll_overlay_stop_contract.py`: overlay click-through, no-focus, trusted origin/visibility, driver emergency-stop path.
- `tests/cpuplus/fixtures/MouseScrollNative.qml`: disposable Quickshell loads the overlay, rejects premature activation, and checks output validation/revocation when a test screen is available.

**Stage 3 is not a production-readiness or input-injection approval.**

## NEXT // Stage 3

Obtain a compositor-approved pointer-origin and target identity path, implement non-focus-stealing anchor rendering and a global Esc/cancel contract, then undertake an independent security audit. Only after operator-approved real SwayFX testing should the CPU++ runtime activation gate be revisited. This work must not collide with the independent scrollbar workstream.
