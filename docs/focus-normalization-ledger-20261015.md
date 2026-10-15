# Syntagma / Post-Apollo // Focus system normalization ledger

**Owner:** Nurse 3a — Focus systems. **Source audit:** October 15, 2026.
**Baseline:** `kudokudo1/The-Post-Apollo-Project` main, inspected after
PR #245's acquisition reconciliation and later Git/Hospital/widget changes.
**Authority:** [Operator focus contract](window-keyboard-focus-contract.md),
[unified widget keys](unified-widget-keyboard-navigation.md) and
[Koinoikos grave contract](koinoikos-focus-mode.md).
**Status:** Source-level findings; compositor/seat behavior still needs
operator-side verification. Treat other workers' active files as owned.

## The accepted user experience

- Open an interactive menu -> it receives usable keyboard input immediately,
  even while the pointer remains at the launcher.
- Open another menu -> the newly opened menu owns input. Both may remain open.
- Enter an existing menu with the pointer -> reacquire input without a click.
  Pointer exit alone does not revoke that input.
- Click Kitty, Discord or another application -> that application promptly
  receives typing, Enter and paste, whether menus remain visible or not.
- Hold **Super + unshifted grave**, then press Left/Right/Up/Down (or HJKL)
  -> spatially navigate ONLY eligible visible Quickshell widgets. The prefix
  alone must never cycle; release either prefix key to finish, without Esc.
- For internal keys, retain the existing Syntagma mapping: Tab/Shift+Tab for
  real Main Modes; Shift+left/right top Sub; Ctrl+left/right lower Sub; plain
  arrows for local selection, Enter for safe activation. Do not create
  artificial Sub Modes in menus that lack them.

## Actual focus has four separate layers

1. **Menu presentation:** A window can be rendered or permanently mapped while
   closed; unmap/remap Git and Hospital previously crashed in live tests.
2. **Logical selection:** `RelationshipFocusBroker.owner` is the current
   Koinoikos target; `KeyboardOwnershipCoordinator.owner` is shared menu
   ownership *intent*. Neither alone proves that keys arrive.
3. **Wayland seat focus:** `WlrLayershell.keyboardFocus` or an ordinary Sway
   `FloatingWindow` determines the actual key recipient, and can disagree with
   the logical owner. Permanent `Exclusive` may trap typing away from Kitty.
4. **Internal Qt item focus:** `forceActiveFocus()`, anchors, editors and Qt
   Shortcut scopes choose the control *within* a surface. These cannot
   independently grant Wayland seat focus.

Do not merge these states into one bool. A focus glow is not evidence of
actual event delivery.

## Current widget compatibility matrix (read from source)

| Surface | Koinoikos candidate | Current seat/input mechanism | Normalization lane |
| --- | --- | --- | --- |
| Git | Yes | Shared owner; bounded 120ms Exclusive pulse -> OnDemand or None; local Qt focus anchor, window/application shortcuts | Preserve open + pointer entry; verify external click restores typing; audit duplicate open requests |
| Hospital | Yes | Same shared policy; own keys, editor/room guards | Preserve seven Main Modes, Floor/Room/Bed and intercom/reception inputs; audit duplicate open requests |
| Notifications Hub | Yes | Shared owner/pulse; conditional 48ms window-active retry; Tab handling in focus anchor | Preserve seven visible Main Modes and search; verify first-Tab receipt |
| AppControl | Yes | Independent OnDemand/conditional Koinoikos focus and search-first Qt focus | Focus adapter needed; giant host file and concurrent owner changes |
| CPU++ | Yes | `focusable` gated by Koinoikos selected state, Qt.WindowShortcut local controls | Focus adapter needed; preserve monitor/thermal controls |
| Weather | Yes | **Exclusive for whole open lifetime** outside Koinoikos; only selected widget gets Exclusive within mode | Migrate away from permanent Exclusive only with real seat-return tests |
| Power | **No** | **Exclusive whenever menu or reboot/shutdown confirmation open**; own `Keys.onPressed` | Distinct safety-critical adapter and future Koinoikos enrollment by approval; no implicit confirmation |
| Social/Messaging | **No** | Controller PanelWindow is nonfocusable; separate ordinary Sway FloatingWindow; native Discord/Vesktop handoff | Native-window adapter needed; do not treat as layer-shell menu |
| Media Deck/toasts/dock buttons | No | Dormant/passive/nonfocusable or no generic menu keys | Exclude unless an actual keyboard-interactive surface is established |

**Important:** The registry has SIX candidates but the focus coordinator
previously accepted only Git, Hospital, Notifications. This leaves the shared
owner stale when Koinoikos moves to AppControl/CPU++/Weather. This source-level
disagreement is what Stage 1 repairs. It **does not** fix independent Wayland
seat capture policies or onboard Power/Social.

## Incremental work / acceptance gates

**Stage 1 — logical parity (this branch):** Accept all six existing
Koinoikos candidates as logical owners, keep the *seat-acquisition pulse
allowlist* to the three existing consumers, and clear a pending pulse when
switching to another widget. Update the shell handoff and source-contract test.
No compositor policy, Sway binding, mapping, internal key grammar, geometry or
window lifecycle changes. Do not promote to an unverified runtime fix.

**Stage 2 — instrumentation and actual keyboard delivery:** Record input
reason, current intent owner, active Wayland/Qt window state, Qt anchor focus,
and a harmless received key. Avoid duplicate-open-path removal before evidence.
Verify both native-window click/recovery and Koinoikos gesture release. Evidence
must distinguish an IPC dispatch from actual key delivery.

**Stage 3 — focused adapters:** Under separate file ownership, bring
AppControl/CPU++/Weather and Power into the common request/release API.
Preserve their specialized input contexts. Test Weather and Power release of
perpetual Exclusive with Kitty/Discord typing and confirmations. Do not change
Power destructive action semantics incidentally.

**Stage 4 — native surface exceptions:** Social's FloatingWindow needs its
own native Sway identity and focus handoff, not blind layer-shell enrollment.
Passive/dormant surfaces remain excluded unless actually interactive.

## Runtime gate before broad rollout

1. Open Git, Hospital, Notifications without pointer repositioning: each
   immediately accepts a harmless key, with correct internal anchor.
2. Enter another panel with the pointer, then move out; focus persists
   until another intentional claim.
3. Click Kitty/Discord with the overlays open. Type, press Enter, and paste;
   nothing in Quickshell may continue stealing the keyboard.
4. Hold Super+grave, navigate in all directions and at spatial edges; no
   normal Sway application windows are targets; release grave first and Super
   first in separate trials.
5. Verify every eligible widget's owner/glow **and** actual Tab/arrows/Enter
   delivery, including editors and confirmations.
6. Preserve custom SwayFX, the symlinked config, and the known permanently
   mapped Git/Hospital/Notifications lifecycle. No runtime pass from CI alone.
