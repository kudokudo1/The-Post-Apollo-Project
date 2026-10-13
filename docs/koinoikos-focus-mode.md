# Koinoikos // relationship-aware Focus Mode (pilot)

**Owner:** SwayFX owns only the independent keyboard mode and key dispatch;
Quickshell owns eligible widget selection, keyboard handoff, and widget
frame-glow intensity. Ordinary Sway application focus is separate.

**Operator intent:** The visual label is **Super + ~**; the physical key
is unshifted grave/backtick (`Mod4+grave`). **Hold Super and grave, THEN
press an arrow** (or HJKL) to move focus among registered Quickshell widgets.
Pressing the shortcut alone never cycles or selects. **Release Super or
grave to exit immediately**, with no Escape key. Ordinary Sway application
focus and Super+arrow bindings are independent.

## Scope / stage

This patch provides **opt-in source implementation**; it does not install
or reload Sway on the operator's computer.

- **No ordinary Sway window targets.** Kitty, browsers, games, floating Sway
  applications, and their existing native focus stay outside Koinoikos.
  There is no Sway fallback when Quickshell does not answer.
- Quickshell surfaces in this pilot: **AppControl, Hospital, Git, CPU++,
  Weather**. They publish geometry via typed `qs ipc call relationshipFocus
  snapshot`. In Focus Mode nonowner registered menus stop owning the
  keyboard, while the selected menu gets a stronger frame-glow opacity.
- Only registered, visible Quickshell widgets are candidates. **Directional
  presses while holding Super + grave** navigate spatially; the prefix alone
  does not move anything. At spatial edges focus stays on the current widget.
  With no eligible widget or absent QS IPC, native Sway focus stays unchanged.
  Releasing either held key restores the default Sway keyboard bindings.
- Other QS surfaces, including **Notifications** (search focus) and
  **Messaging** (currently explicitly non-focusable), are *not yet
  registered*. Do **not** report universal-menu acceptance based on five
  surfaces. Their on-boarding needs separate text-input focus policy.
- Existing Git/Hospital `Ctrl+Tab` is temporarily retained outside
  Koinoikos mode, not replaced with Alt+Tab. AppControl/Hospital
  `Tab/Shift+Tab` and all existing Sub Mode keys stay unchanged.
- This code has static/source unit tests; actual **Wlr layer-shell focus
  handoffs and source coordinates require operator runtime verification**.

## Opt-in setup (after checking paths on the operator's own machine)

The directory containing this repository's `shell.qml` must be the
Quickshell directory used by the running `qs` instance. The example below
assumes `~/.config/quickshell`; change it if using a different checkout.

### One-command opt-in (preferred)

After pulling the updated Quickshell repository into the installation
directory and confirming that it is your active `shell.qml`, run:

```bash
python3 ~/.config/quickshell/scripts/enable_koinoikos_focus.py
```

This installer **does not ask for or replace the contents of your custom
Sway config**. It appends only the explicit opt-in include, first creating a
temporary candidate in the same folder. For validation, it resolves the
**actual running Sway-family compositor** using the `SWAYSOCK` PID and
`/proc/<pid>/exe`, then runs that compositor's `-C -c` parser.
This matters when a custom **SwayFX / SwayPX** installation understands
`animation_duration_ms`, `shadows` and other effects that stock `sway`
would incorrectly report as unknown. The installer does **not** remove,
filter, or suppress existing effects commands.

If the running compositor cannot be identified, installation stops safely
with an explanation. An explicit validator path can be supplied with
`--sway /absolute/path/to/your/compositor`; a stock `sway` fallback is
**not** guessed, and validation failures are never bypassed.

If validation fails, your config stays untouched. On success, the installer
makes a timestamped `.bak` copy and atomically writes the validated
candidate. A second run does not duplicate the include. It **does not**
reload Sway or restart Quickshell.

**Symlinked Sway configs are supported.** If `~/.config/sway/config`
points into your dotfiles repository (including relative or chained links),
the installer follows the existing link to its final regular-file target.
It validates using a temporary candidate beside the original config path,
backs up the **real target file** next to that target, and atomically updates
only the target. All original symlinks remain intact. Dangling links,
non-file targets and failed Sway validation abort without modifying the
config. If another process changes the target during validation, the
installer refuses to overwrite newer content.

If your repository or actual Sway config lives elsewhere, use
`--config /path/to/config` or run the script from your actual checked-out
repository; the include target is resolved from the script's own directory.

### Manual include (equivalent)

In the existing Sway config, add **one** include at the desired location:

```sway
include ~/.config/quickshell/config/sway/koinoikos-focus.conf
```

This does **not** replace the operator's existing Sway configuration or
`$mod`. The binding uses `Mod4+grave`: press **Super + the backtick
key** without Shift on a US layout. Keep **Super + ~** as the visual label,
not the literal Shift-modified key chord. On other XKB layouts verify the
grave keysym before relying on it. The Sway mode is temporary: it dispatches only held
`Mod4+grave+direction` chords and exits automatically on either key release.
No Escape exit or global key listener is required. The Python router
starts the Quickshell focus session on the FIRST directional press.

### Separate native-window appearance (not Koinoikos)

SwayFX-compatible compositors can use an **additional separate include**:

```sway
include ~/.config/quickshell/config/sway/koinoikos-native-focus-glow.conf
```

**Legacy appearance option only; not part of widget focus.** This would
change ordinary SwayFX application shadows globally, even outside Koinoikos.
Do not install this to enable widget-only focus or overwrite the operator's
existing compositor effects. Quickshell widget glows remain independent.

### Preflight and reversible activation

Before adding the include, or after editing a **copy** of the config,
validate with the **same binary running the Sway session**, not an unrelated
stock `sway` binary. The installer automatically discovers that binary
from the current `SWAYSOCK` and uses its `-C -c` mode. This repository
cannot inspect or validate a live compositor in GitHub CI. Keep the prior
config for easy rollback. If even the running compositor rejects the
candidate, report the errors; never silently omit the user's own
animation/shadow directives.

After the operator chooses to activate it, Sway reload and a clean Quickshell
restart are required; this repo intentionally disables Quickshell's hot
file watcher because Qt 6.11 sampled-glow teardown previously crashed.
Use the project's safe restart instructions, not auto reload during file edits.

### Diagnostics

```bash
qs ipc show
qs ipc call relationshipFocus snapshot
python3 ~/.config/quickshell/scripts/koinoikos_focus.py snapshot
swaymsg -t get_binding_state
```

Hold **Super + unshifted backtick/grave** (displayed as **Super + ~**),
then press **Left/Right/Up/Down** or **h/j/k/l** while both prefix keys are
held. The prefix itself is inert; repeated directions move spatially and
never cycle on the prefix. **Release Super or grave to end, no Esc.**
On QS IPC failure this does not fall back to native Sway application focus.

**Recovery if a SwayFX build misses a release event:** run
`swaymsg mode default` and
`python3 ~/.config/quickshell/scripts/koinoikos_focus.py exit` manually,
then report the key-release event trace. Runtime key-up acceptance is
required before treating this as a finished hold gesture.

### Runtime verification checkpoint

Verify that holding Super+grave alone changes no widget selection, then
press one arrow and inspect `relationshipFocus.snapshot.owner` and the
focused glow. Test further directional presses and both key-release orders
(grave released first; Super released first), each returning to
`get_binding_state=default` without Esc. Confirm that the original
Kitty/browser stays on the same native Sway focus and ordinary Super+arrows
still work afterward. Test two then all five registered widgets, cross-output
geometry, overlapping widgets, edge behavior, closed widgets, and
Hospital/Git text input. No live acceptance from source CI alone.

Focus Mode is not a lock screen, Sway seat isolation mechanism, or
permission gate. It should never trigger destructive controls merely by
moving focus. Do not claim validated universal focus until every registered
surface and the original keyboard ownership restoration pass live.
