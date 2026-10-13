# Syntagma // universal widget keyboard-navigation contract

**Authority:** Operator decision, October 13, 2026. **Reference:** AppControl.
**Scope:** Quickshell widget/menu *internal navigation*. The separate
[Koinoikos widget-focus contract](koinoikos-focus-mode.md) governs movement
*between* windows and [window focus ownership](window-keyboard-focus-contract.md)
governs which window receives keys. This contract **does not change** the Sway
keymap, compositor, focus broker, or keyboard-ownership coordinator.

## Operator-approved navigation hierarchy

| Layer | Standard | Behavior |
| --- | --- | --- |
| Cross-widget focus | Hold **Super + ~** (physical `Mod4+grave`), then arrow/HJKL | Koinoikos chooses an eligible open Quickshell widget; release either held prefix key to exit |
| Main Mode | `Tab` next; `Shift+Tab` previous | Cycles the current window's actual primary modes, wrapping when cyclic |
| Top Sub Mode | `Shift+Left/Right` | Cycles the present upper secondary selector/filter |
| Bottom Sub Mode | `Ctrl+Left/Right` | Cycles the present lower secondary selector/filter |
| Within the current menu | Unmodified arrows | Spatial navigation, with vertical/horizontal/grid semantics belonging to the menu |
| Activation | `Enter` / `Return` | Activates the currently keyboard-selected *action/control* when safe |
| Exit / Back | Contextual `Escape` / Back | Returns from local layers or closes according to the owning window's existing semantics |

A widget **must not manufacture** an absent Sub Mode just to handle a
shortcut. A Main Mode, contextual selector, local focus zone, and an action
are not interchangeable. AppControl supplies the default *key grammar*, not
the internal layout or a license to replace valid local navigation.

## Interaction ownership and safety

- Navigation is **window-local**. Never use an application-wide shortcut
  without explicit focus/owner guards. Disabled or unmounted windows must
  not swallow another surface's keys.
- Keys must reach a useful non-destructive control on the first usable
  keyboard-owned opening of each interactive window. Navigation must not
  terminate processes, commit Git mutations, reboot, or confirm destructive
  actions. Selecting an action and activating it are different operations.
- Preserve actual text-entry focus, active dials, confirmation overlays,
  nested editors, operation locks and long-running work. These contexts may
  override or temporarily suspend mode keys.
- Arrows follow the current layout; preview/highlight must remain distinct
  from Enter activation. Pointer entry/movement may synchronize the keyboard
  cursor without itself triggering an action.
- Cyclic mode groups wrap; bounded selector ranges stay bounded. Dedicated
  contextual Back, history, Floor/Room/Bed and playback controls retain their
  meanings unless the operator approves a specific remapping.
- Focus indication is **not** proof of actual event delivery. Runtime
  verification requires keyboard delivery, live mode changes, input focus
  restoration and Koinoikos handoff/release to work together.

## Source rollout / compatibility ledger

This is an incremental source implementation, **not** a completed universal
on-device verification. The existing [source map](sub-mode-keyboard-contract.md)
records the old AppControl, Git and Hospital keys and their focus caveats.

| Surface | Rule implementation / boundary |
| --- | --- |
| AppControl | Existing reference handlers; its Tab behavior is context-sensitive when the result/mode rail owns focus |
| Hospital | Existing seven Main Mode Tab/Shift+Tab implementation; Floor/Room/Bed remain contextual, not artificial Sub Modes |
| Git/GitHub | Add Tab/Shift+Tab for Local/Remote main pages; Ctrl+Left/Right for the visible lower six-mode rail; Shift+Left/Right now cycles the true top Sub Mode in Git Changes, History, and Repository. Existing spatial arrows and Git Alt+Left Back remain. Shift+Up/Down are guarded **legacy primary-page aliases** pending operator acceptance |
| CPU++ | Add Tab four Main Modes; Shift+arrows for TEMP/FAN and SYSTEM submodes; Up/Down for monitor rows; no invented lower submode |
| Weather Station | Add Tab HOME/MAP/NEWS/RADIO/TERMINAL; Shift+arrows for DOMAIN; vertical rail Up/Down preview plus Enter activation |
| Power | Existing Up/Down, Enter, Escape and confirmation isolation; no artificial Main/Sub Mode |
| Social/Messaging | Tab/Shift+Tab cycles Sessions/Discord/Telegram via their normal opener. Keyboard-initiated Discord opening now requests selector focus restoration on show completion; mouse clicking or entering the separate Discord window retains native application focus. Social is a normal FloatingWindow and remains outside the QS layer-shell Koinoikos registry pending separate native-window policy and live verification |
| Notifications | **Koinoikos source-enrolled widget.** All seven visible filter buttons are Main Modes: ALL → APPS → SYSTEM → SOCIAL → APOLLO → WARNING → MANAGER (wrap). Tab advances one button and Shift+Tab reverses, continuing from a mouse-clicked filter. There is no separate top/bottom Sub Mode; Shift+arrows are not bound to these filters. Up/Down highlights history or Manager rows; Enter activates only explicitly selected History app cards, never Manager/DND actions. Shared ownership, search and confirmation guards remain; live compositor validation is pending |
| Media Deck | Dormant/unmounted, currently explicitly `WlrKeyboardFocus.None`; transport actions are not generic navigation; must not pretend source shortcuts create real keyboard focus |

**Outstanding:** Extend to other eligible interactive windows and
review specialized Git/Hospital collisions. Notifications has source
registration but needs live Koinoikos selection, text-entry and external-click
acceptance. Social's native FloatingWindow and dormant Media Deck require their
own focus-policy decisions. Static checks
must never be reported as compositor runtime acceptance. Other focus worker
owns the Koinoikos broker, Sway binding and shared focus coordinator.

## Acceptance matrix for each interactive window

1. Open the window and immediately press a harmless navigation key.
2. Test Tab/Shift+Tab on actual Main Modes and both directions on available
   top/bottom Sub Modes.
3. Test arrow highlight and safe Enter activation in each local layout.
4. Test pointer-to-keyboard cursor sync, wrap/bounds and disabled controls.
5. Type in an input, edit a dial, enter an overlay: no global shortcut theft.
6. Transfer focus to another open widget with Super+~+direction and repeat.
7. Click an ordinary Sway application, type/paste, and return to the widget.
8. Release either held Koinoikos prefix key; no persistent focus lockout.
