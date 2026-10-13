# Koinoikos // relationship-aware Focus Mode (pilot)

**Owner:** SwayPX for compositor bindings/navigation; Post-Apollo Quickshell for
layer-shell keyboard ownership, frame-glow intensity and eligible menu registry.

**Operator intent:** Display the shortcut as **Super + ~** (the tilde
symbolizes relationship / ghost string / spiritual connection), but trigger it
using **Super + the unshifted grave/backtick key** (`Mod4+grave`), with no Shift.
This begins a persistent *relationship focus* mode. Inside the mode, plain arrows and `h j k l` move spatial focus;
the currently selected participant glows more strongly while other open
windows remain visible. `Esc` returns to ordinary Sway.

## Scope / stage

This patch provides **opt-in source implementation**; it does not install
or reload Sway on the operator's computer.

- Native Sway focus targets: visible application leaf containers on visible
  workspaces, selected via their compositor IDs, **not** fake Qt window names.
- Quickshell surfaces in this pilot: **AppControl, Hospital, Git, CPU++,
  Weather**. They publish geometry via typed `qs ipc call relationshipFocus
  snapshot`. In Focus Mode nonowner registered menus stop owning the
  keyboard, while the selected menu gets a stronger frame-glow opacity.
- The router chooses eligible target centers in the indicated half-plane,
  preferring short distance and direct horizontal/vertical alignment.
  Closed QS menus and Sway clients on invisible workspaces are excluded.
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
grave keysym before relying on it. Sway binding modes already handle `Esc`,
`h j k l` and arrows natively; no global Python key listener is installed.
The external Python router is executed once per Focus Mode movement.

### Optional native-window glow

SwayFX-compatible compositors can use an **additional separate include**:

```sway
include ~/.config/quickshell/config/sway/koinoikos-native-focus-glow.conf
```

**Optional:** This enables compositor shadows with a bright focused and quiet
unfocused orange alpha. These native shadows also apply **outside Focus
Mode**, because they are compositor appearance settings. If another worker
or the operator already customized the compositor shadows, **do not include
or overwrite that theme** without explicit acceptance. QS menu glows remain
independent of this optional file.

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

During mode: press **Super + unshifted backtick/grave** (displayed as
**Super + ~**) to enter; use arrows or `h/j/k/l` to select a spatial
neighbor; `Esc` exits. If Quickshell IPC is absent, directional
keys fall back to native `swaymsg focus <direction>` and Escape still
restores Sway's default binding mode.

**Entry-command quoting:** Sway `binding` events confirm the chord fired,
but do not prove the mode was entered. `swaymsg` re-parses its IPC command:
keep the internal quotes around the multiword name. From a shell prompt use
`swaymsg 'mode "Koinoikos Focus"'`; in the `sh -c` shortcut the equivalent is
`swaymsg "mode \\"Koinoikos Focus\\""`. Do not split the command into
`swaymsg mode "Koinoikos Focus"` or the embedded quotes are lost.

### Runtime verification checkpoint

Check ordinary native window-to-window focus first; then two registered QS
menus, mixed native/QS, all five eligible menus, the DP-5 / HDMI-A-1
coordinate boundary, overlapping windows, focus after closing a menu,
Hospital Receptionist typing, Git nested editor/dial, and Escape after an
IPC failure. The Sway compositor may not report layer window coordinates in
the same global coordinate system as `QsWindow.x/y` on every output; verify
the live `snapshot` geometry before calling multi-monitor routing accepted.

Focus Mode is not a lock screen, Sway seat isolation mechanism, or
permission gate. It should never trigger destructive controls merely by
moving focus. Do not claim validated universal focus until every registered
surface and the original keyboard ownership restoration pass live.
