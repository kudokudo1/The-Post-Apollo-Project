# 🏥 Nurse 3a // Stage 3 actual Tab shortcut and owner trace

**October 15, 2026. Diagnostic only. No keyboard/focus-policy changes.**

## Why stage 2 was insufficient

The operator enabled `focusKeyTrace` with `qs ipc call focusKeyTrace start`
(`status` returned `true`) and reproduced intermittent Git → Hospital
Tab delays. Yet `qs log -t 1000 | rg 'FOCUS_KEY_TRACE|SYNTAGMA_LAG_PROBE'`
returned no matching messages. The initial trace only watched
`Keys.onPressed` and `Keys.onShortcutOverride` on two navigation anchors.
Qt's `Shortcut` dispatcher can activate Tab before those anchors receive
`Keys.onPressed`. Thus a blank trace does **not** prove no Tab reception.

Also, `SYNTAGMA_LAG_PROBE` only logs when explicitly enabled at process
startup and a 100ms event-loop timer is delayed to >=350ms or a monitored
dock toggle occurs. No warning alone cannot rule out smaller freezes.

## New passive opt-in data

Reuses the same existing, default-disabled `focusKeyTrace` IPC control.

- Each **Git and Hospital existing Tab/Shift+Tab Main Mode cycle method**
  (called directly by its existing `Shortcut.onActivated`) now emits `tab-shortcut-activated` with millisecond timestamp, direction,
  previous Main Mode, Qt anchor/window activity and bounded focus-lock
  state; calls the **same existing navigation method once**; then emits
  `tab-shortcut-completed` with synchronous elapsed milliseconds and
  resulting Main Mode.
- `KeyboardOwnershipCoordinator` in `shell.qml` emits timestamps for
  **owner-changed** and **boost-changed** while tracing is enabled, allowing
  correlation with the 120ms Exclusive→OnDemand transition.
- Existing anchor `pressed`, `shortcut-override`, `anchorFocus` logs
  remain unchanged and independent.
- All logging is behind the same default-off Boolean. Logs contain no
  typed text, browser content, titles, chat messages or Patient/Room data.
- The timestamp and synchronous duration measurement do not attribute
  expensive operations to a specific service. A long handler duration
  narrows the bottleneck to the tab callback; a short duration despite
  visibly slow UI suggests asynchronous rendering/model activity or
  compositor/seat focus lag.

## Reproduce on the operator's SwayFX host

After integration and a **safe full Quickshell process restart** (not
hot-reload or panel unmap/remap):

```sh
qs ipc call focusKeyTrace start
qs ipc call focusKeyTrace status
qs log -t 1000 | rg 'FOCUS_KEY_TRACE|SYNTAGMA_LAG_PROBE'
```

Keep Git and Hospital open above Brave. Transfer pointer ownership
Git → Hospital, press Tab deliberately, then rapidly cycle Hospital's
seven modes. Repeat Hospital → Git. Compare UI effects, `owner-changed`,
`boost-changed`, `tab-shortcut-activated`, `tab-shortcut-completed`
and `elapsedMs`. The log's `tsMs` fields allow aligning the sequence.

If the UI switches yet `tab-shortcut-activated` is absent, suspect log
selection, a different navigation route, or runtime version. If the
shortcut does not fire but the coordinator says Hospital owns input,
investigate layer-shell compositor/Qt activation. A slow synchronous
callback is *not* evidence of focus failure.

Stop after testing:

```sh
qs ipc call focusKeyTrace stop
```

**Safety:** The original `Shortcut.onActivated` handlers stay exactly intact.
No changes to keyboard ownership decisions, the 48ms retry,
the 120ms boost, native SwayFX bindings, panel lifecycle, Shortcut contexts,
Shortcut enable predicates, or Main Mode navigation behavior. Clicking
Brave must still restore native typing. Source/CI success does not
establish on-device success.
