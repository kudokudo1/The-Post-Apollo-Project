# Meta Apollo / Post-Apollo // Window keyboard focus contract

**Authority:** Operator's direct design decisions, October 13, 2026.
**Scope:** Quickshell floating/overlay menus and normal SwayFX application focus.
**Status:** Accepted behavior; implementation staged and requires live compositor testing.
This document supersedes ad hoc rules where merely opening any menu permanently
locks the keyboard, or pointer location is required *inside* an already opened menu.

## Behavior (not optional decoration)

1. **Open:** Opening a focusable menu (button click, hotkey or IPC) immediately
   acquires keyboard input and initializes its internal navigation anchor.
   The pointer does not need to move from the launch button into the panel.
2. **Another open:** Opening a second menu transfers ownership to that menu;
   the first stays open and interactive but is no longer keyboard owner.
3. **Pointer entry:** Moving the pointer *into the actual menu* acquires focus
   for that menu without a click. Mouse exit alone does not relinquish it.
   Hover of the launch button is *not* equivalent to menu entry.
4. **External click:** Clicking any ordinary application (Kitty, Discord,
   browser, etc.) must restore its native keyboard input immediately, including
   Enter, typing, and Ctrl+Shift+V. Open menus remain visible but passive.
5. **Return:** Clicking or re-entering an already open menu reacquires
   keyboard input without closing or reopening it.
6. **Explicit navigation:** Koinoikos Super+grave+direction chooses only eligible
   Quickshell menus and uses the SAME focus acquisition mechanism. Bare
   Super+direction stays native Sway navigation. No prefix cycling and no
   persistent Esc-dependent focus mode.
7. **Internal focus:** The selected menu must activate the proper Qt control
   or navigation anchor; compositor seat ownership alone is insufficient.
   Existing text editors/dials retain their specialized focus while active.
8. **Only one owner:** Keyboard ownership among Quickshell menus is serialized.
   No second open overlay may hold indefinite exclusive keyboard interactivity.
9. **Fail-safe:** No widget may keep layer-shell `Exclusive` merely because it
   is open. Any short compositor-focus acquisition window must have a bounded
   termination and revert to ordinary, relinquishable focus. Closing a menu
   clears its ownership. If acquisition fails, the operator must still be able
   to click ordinary applications and type.
10. **Visible != focused:** Visibility, visual highlight, compositor seat
    ownership, and Qt internal focus are separate state. Track their handoffs
    rather than claiming that a glow proves key delivery.

## Protocol / engineering boundary

The Wayland wlr-layer-shell protocol defines:
- `None`: no keyboard focus on that surface.
- `OnDemand`: compositor-managed focus/unfocus, including click-to-focus;
  exact hover/open activation is compositor-specific.
- `Exclusive`: requests lockout of other windows and is intended for
  special cases such as lock screens, not an indefinitely opened dock menu.

Quickshell 0.2.x explicitly warns that OnDemand *may retain focus* on some
compositors. To fulfill open/cursor-entry acquisition reliably, the pilot may
request only a **bounded** exclusive activation pulse before reverting to
OnDemand. This is a hypothesis requiring SwayFX runtime proof; it is NOT a
verified guarantee. If the brief pulse does not both acquire and relinquish
focus correctly, stop and redesign acquisition rather than retaining
Exclusive continuously.

## Implementation order

**Pilot:** Git + Hospital, including shared ownership, on-open requests,
passive pointer-entry requests, Qt anchor restoration, release when superseded,
and a short/bounded compositor acquisition pulse. Preserve all existing
internal shortcut functions and theme geometry.

**Next lanes:** Notifications Hub has been added in a separate *source-only*
registration pilot with shared-owner + bounded Exclusive activation; live
compositor validation remains mandatory. Weather (currently perpetual
Exclusive), AppControl, Power, and other menus still need per-widget review.
Social/Messaging is a normal FloatingWindow: native Discord focus and
Koinoikos layer-shell routing remain independent. Do not regress input fields,
nested selectors, launchers or notification editors.

**Acceptance:** With two menus open, test focus after opening each; pointer
entry in either without clicking; cursor exit alone; click Kitty/Discord and
type/paste; return to menu; two menus open concurrently; Koinoikos navigation
and release; DP-5 + HDMI output. Verify actual key delivery, not only
`relationshipFocus.snapshot.owner`. Source CI alone is not acceptance.
