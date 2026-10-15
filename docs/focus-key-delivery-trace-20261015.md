# Syntagma // opt-in Git + Hospital keyboard delivery trace

**Stage:** diagnostic only. **Date:** 2026-10-15.
**Owner:** Nurse 3a / cross-widget focusing.
**Status:** default OFF; source checks and on-device verification required.

## Reproduction boundary

The operator's **installed** `main` at `0983c67` is clean and matches
GitHub main. Koinoikos now returns numeric Git/Hospital geometry; the SwayFX
mode and QS broker both enter and exit. Yet with Brave underneath those panels,
Tab still sometimes goes to Brave. Neither the Koinoikos `owner` nor Qt's
internal selected item proves which surface received the physical key.

The layer-shell focus protocol permits compositor-specific `OnDemand`
delivery; a 120ms bounded `Exclusive` pulse is not a proven durable focus
handoff. Do not react by making `Exclusive` permanent.

## What this diagnostic does

An opt-in QS IPC control `focusKeyTrace` enables passive, instrumented
`Keys.onShortcutOverride` and `Keys.onPressed` logging on the existing Git
and Hospital navigation anchor Items. Each diagnostic handler explicitly
leaves `event.accepted=false` so the existing shortcut, editor and focus
behavior is preserved. The log contains **only** navigation-key codes (Tab,
Backtab, arrows, Enter/Return) and per-widget state:

- Quickshell's reported attached `Window.active` for the focused Item.
- Whether the existing keyboard navigation anchor has Qt `activeFocus`.
- Existing menu/keyboard/temporary keyboardLock and Koinoikos owner flags.
- Whether this was `shortcut-override` or an actual `pressed` signal.

It **never logs browser contents, text typed, passwords, page titles, non-
navigation keypresses, raw keystroke streams or application data**.
Existing UI states are not changed, and no new Sway binding is installed.

## Enable and stop without restarting

After this code has reached the installed Quickshell configuration and
the normal **safe full process restart** is complete:

```sh
qs ipc call focusKeyTrace status
qs ipc call focusKeyTrace start
qs ipc call focusKeyTrace status
```

The first status should be `false`, and the second status should be
`true`. Use your normal Quickshell runtime-log viewer/terminal to watch
the temporary `FOCUS_KEY_TRACE` messages.

In the established test scene, keep **Brave underneath Git and Hospital**.
With your pointer stationary in a suitable safe location:
1. Open Git and try Tab; record whether Git advances Main Mode and whether
   its passive `FOCUS_KEY_TRACE` includes a navigation event.
2. Open Hospital and try Tab; record whether Hospital advances its Main Mode
   and whether the Hospital trace records the event.
3. Hold **Super + grave**, press **Left** to choose Hospital, release both.
   Then press Tab. Repeat in the other direction selecting Git.
4. Deliberately click Brave: its Ctrl+L and harmless typing should work.
   Return to the menu with a pointer entry and check Tab again.

Classify each observation carefully:
- Broker owner changed, but **Qt `Window.active` never true and no key
  receipt logged**: consistent with failed compositor acquisition, but not
  definitive proof in isolation.
- Qt reports active and `shortcut-override` logs Tab, but no `pressed`
  event or Main Mode change: investigate Qt shortcut/tab chain.
- Widget advances its Main Mode: end-to-end key delivery **worked for this
  particular test** even if Sway's `get_tree` still labels Brave focused.
- Brave reacts instead: actual underlay fallthrough; a source-level
  coordinator owner never overrides that observation.
- No anchor log during active editor/dial contexts is **not** alone evidence
  of an acquisition failure; those contexts intentionally own internal Qt
  focus. Return to normal Main Mode navigation first.

Always stop after the bounded test:

```sh
qs ipc call focusKeyTrace stop
qs ipc call focusKeyTrace status
```

The status should return `false`. The trace toggle is intentionally not
persistent across Quickshell process restarts.

## Acceptance/safety gates

No `focusable`, `WlrLayershell.keyboardFocus`, 120ms coordinator timer,
menu-open lifecycle, native SwayFX action, Tab mapping, Git service, Hospital
assignment service, input editor, or power-confirmation changes. Do not merge
untested focus policy changes based on diagnostic source CI alone.

This stage is **only** a diagnostic instrument that can distinguish several
classes of failure. It is not a fix and should not be described as such.
