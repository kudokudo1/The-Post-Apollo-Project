# Post-Apollo // guarded automatic widget hotkeys

**Scope:** User Sway/SwayPX compositor configuration; eight existing Super-key widget toggles.

## What installs automatically

On Quickshell startup, `shell.qml` invokes `scripts/ensure_post_apollo_widget_hotkeys.py --install` once. The helper does **not** replace the user's Sway config. If the session runs its normal `$XDG_CONFIG_HOME/sway/config`, and **all eight** requested chords are free, it appends exactly one line:

```sway
include "/absolute/path/to/quickshell/config/sway/post-apollo-widget-hotkeys.conf"
```

The included file preserves the eight existing `qs ipc call controlMenus` commands. Their owner remains Sway's global key dispatcher; Quickshell's IPC handler toggles the same existing widget windows.

### Safety gates

- There must already be a real, inspectable Sway user config under the current user's home. An absent config is not created.
- Every nested include is inspected, including globbed includes and `set $mod` aliases. Any existing claimed chord, ambiguous Super `bindcode`, unresolvable variable, or missing include causes **no installation**. The user's binding always wins.
- The candidate config is checked with `sway -C -c` against the executable of the active Sway/SwayPX session, not blindly with stock Sway. If the session uses a different explicit `-c` config path, the default file is not modified.
- On success, the resolved file is backed up as `config.before-widget-hotkeys-*.bak` before an atomic replacement. Symlinked config paths remain symlinks.
- Repeated Quickshell startups are idempotent. An existing managed include is not appended twice.
- The helper aborts if the config or any inspected included file changes during validation.
- **No automatic Sway reload or Quickshell restart.** SwayPX's `exec_always` chain can kill and restart Quickshell during a reload.

**Effective timing:** The bindings are available at the **next Sway session start**, after the operator's currently running compositor has naturally exited. This is intentional and avoids disrupting running applications.

## Status and disabling

Quickshell logs one `POST_APOLLO_HOTKEYS` line indicating `INSTALLED`, `ALREADY`, or `SKIPPED`. A collision message reports which chord is reserved; the installer will not replace it.

Set `POST_APOLLO_AUTO_WIDGET_HOTKEYS=0` in the environment that launches Quickshell to disable future automatic provisioning. This does not remove bindings that are already included.

To check a candidate without making changes:

```bash
python3 ~/.config/quickshell/scripts/ensure_post_apollo_widget_hotkeys.py
```

To undo a completed installation **after first reviewing changes to the file**, remove only the `# Post-Apollo // guarded widget hotkey include` line and its following `include` directive from the user's actual Sway config. The pre-install `.bak` is available as a recovery reference; do **not** blindly restore it if other Sway settings were changed after installation.

## Boundaries

The script does not install packages, alter any SwayPX system setting, manipulate input devices, override user shortcuts, or activate the compositor configuration live. A merged PR alone does not mean the user's local Quickshell source has been updated.
