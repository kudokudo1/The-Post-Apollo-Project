# Post-Apollo // Super-key widget hotkeys

**Status:** Staged, opt-in. **Authority:** Operator request, 2026-11-02.
**Scope:** Launch/close the *existing* widget windows via Sway's global keybindings.
**Not:** A new Quickshell process, global Qt shortcut, keyboard focus broker,
login manager, or automatic modification of the operator's live Sway config.

## Requested keys

| Physical chord | Result | Quickshell IPC method |
| --- | --- | --- |
| Super + T | To Do / Tasks panel toggle | `controlMenus todo` |
| Super + M | Social panel toggle | `controlMenus social` |
| Super + Shift + M | Finance panel toggle | `controlMenus finance` |
| Super + N | Notifications Hub toggle | `controlMenus notifications` |
| Super + A | Apollo Hub toggle | `controlMenus apolloHub` |
| Super + Shift + T | Clock / TimeW toggle | `controlMenus clock` |
| Super + Shift + W | Weather Station toggle | `controlMenus weatherStation` |
| Super + R | MP3 / Hi-Fi deck toggle (includes its Radio source) | `controlMenus media` |

These are **toggles**: repeat a chord to close the corresponding menu. The
`Super+R` chord opens the MP3/Hi-Fi deck and does **not** automatically
change its currently selected source, load a station or start playback.

## Mechanism

Sway receives the physical global chord and runs `qs ipc call controlMenus
<method>`. The existing `IpcHandler` in `shell.qml` invokes the existing
widget's toggle. In particular, MP3 uses `sharedMediaDock.toggleDeck()`:
both the dock click and IPC call share the same placement and `deckOpen`
state; Escape's close request still returns to this owner, so the QML
`menuOpen: mediaRoot.deckOpen` binding must not be overwritten.

Koinoikos (`Mod4+grave` focus gesture) and its focus coordinator are
untouched. No permanent exclusive keyboard acquisition is introduced.

## Safe opt-in on the operator's machine

**Do not run these activation steps automatically.** Local file writes,
Quickshell restarts, and Sway reloads require separate operator approval.

1. First update the local Post-Apollo repository to the reviewed/merged
   revision using the operator-approved deployment procedure, then use
   `qs ipc call controlMenus todo` to test whether the IPC endpoint is
   available. Close To Do by repeating the same IPC call.
2. Inspect the **running** Sway config and every imported include for existing
   Super shortcuts. For an initial inspection (requires `jq`):
   `swaymsg -t get_config | jq -r '.config' | grep -nE 'bindsym.*(Mod4|\\$mod)'`.
   Check all eight exact chords, including shifted variants. In common
   Sway keymaps, Super+T may select tabbed layout and Super+R may enter
   resize mode. Other systems may use them for terminals, launchers,
   workspaces, or native actions. These bindings are NOT automatically safe
   to activate just because repository CI passes.
3. If there is a collision, decide deliberately which old shortcut to retain.
   Do not silently override it, and do not just append duplicates. The
   repository cannot verify the active user's separate Sway keymap.
4. Only after approval and conflict resolution, add **one** include directive
   pointing to the actual deployed absolute path of
   `config/sway/post-apollo-widget-hotkeys.conf` inside the real Sway config.
   Prefer using the already-established symlink-aware config workflow; keep
   a rollback copy of the original. No relative-path guesses.
5. Validate the complete candidate Sway config with
   `sway -C -c /absolute/path/to/the/real/sway/config` before applying it.
   Do not reload if validation fails. After approval, use `swaymsg reload`
   to activate the bindings.
6. Verify all eight keys in the running SwayFX session. Test a first press
   after opening, repeated open/close, Escape then keyboard re-open for MP3,
   and returning focus to Kitty/Discord after an external click.

## Verification and recovery

**Source CI** checks the Sway table and the eight IPC methods, that no global
Qt shortcuts or extra window instances were created, and that Media's
placement and Escape-close bindings remain owned by its dock.

**Not verified by CI:** an operator's live Sway binding inventory, conflicting
user dotfiles, actual keyboard delivery or focus acquisition, Quickshell
process selection, or multi-monitor geometry. If a chord fails, test its IPC
call first to separate Sway mapping problems from widget-state problems.

**Rollback:** remove the one opt-in Sway include and reload the operator's
validated previous Sway config. Revert the feature PR for repository rollback.
Neither action touches widget data, stored accounts, or media playback.
