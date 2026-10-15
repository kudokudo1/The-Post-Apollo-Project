# Focus test // Brave beneath Git + Hospital (Nurse 3a)

**Date:** October 15, 2026. **Status:** diagnostic test plan, not a
verified fix. **Purpose:** reproduce focus fall-through and distinguish a
SwayFX chord dispatch bug, a Quickshell logical-owner mismatch, a layer-shell
seat-key acquisition failure, and Qt internal-Tab handling failures.

Brave is a **negative control** during Koinoikos widget-only navigation.
It is an ordinary Sway application, deliberately placed **under** Git and
Hospital; it must never be selected by Super+grave+direction. But when the
operator clicks Brave, it MUST regain typing immediately. We are testing both
halves of the contract, not permanently blocking the browser.

## Source-safe diagnostic surface

The read-only `qs ipc call relationshipFocus diagnose` IPC exposes:
- Koinoikos active/selected widget, shared logical owner and focus boost owner.
- Registered/open menu candidates and per-widget visibility.
- Best-effort Qt window active/internal active-focus-item data (null if not
  exposed by the window). None of these alone establishes compositor seat
  focus.

`python3 ~/.config/quickshell/scripts/focus_diagnostics.py snapshot`
combines this with Sway's `get_tree` focused **native container**, reported
without window titles or page contents. The focused native tree entry can
remain Brave while a layer-shell widget receives keys: **never equate this
field to actual keyboard event delivery.** No user keypress data or browser
content is captured.

`python3 ~/.config/quickshell/scripts/focus_diagnostics.py watch --limit 30`
also listens to read-only `swaymsg -m -t subscribe` binding/mode/window
events, producing a bounded stream of JSON diagnostic samples. It does not
run Sway focus or mode commands or change any keyboard shortcut. The operator
may press Ctrl+C at any point. Only enable while deliberately reproducing
focus bugs: additional IPC sampling can itself influence timing.

## Browser-under-overlays reproduction

1. Place **Brave** (ordinary native Sway client) on DP-5 beneath both Git
   and Hospital so a portion of Brave is visible and clickable. Keep a
   harmless browser tab available; do not test by submitting a live form.
   Launch the read-only diagnostic watcher in a separate Kitty window.
2. **Open Git** using the bar button, leaving the pointer on the launcher.
   Immediately press **Tab** and Shift+Tab. Expected: Git's Main Modes
   change, not Brave's address bar or web-page keyboard focus. Take a
   diagnostic snapshot before and after if convenient.
3. **Open Hospital** with Git still open. Immediately press Tab and
   Shift+Tab. Expected: Hospital's seven Main Modes change and the page
   underneath does not react. Pointer entry into Git (without click)
   should reacquire its navigation; pointer exit alone should not lose it.
4. **Koinoikos:** Hold physical **Super + unshifted grave**, then press
   left/right/up/down separately to select registered visible widgets.
   Try both directions and a spatial edge. With the two overlays above
   Brave, Brave must **never become the Koinoikos selection**. The
   compositor log should show the **Koinoikos Focus** mode and its held
   direction binding, not a regular `focus left/right/up/down` binding.
   Releasing either prefix key must end the mode without Escape.
5. With either widget selected, press Tab once and visually confirm the
   selected widget changes its intended **internal mode**. If Brave reacts
   instead, record the active Koinoikos selection, shared logical owner,
   Qt focus and Sway mode events from the watcher. The mismatch, not the
   glow alone, is the failure evidence.
6. **Positive Brave handoff:** Click the visible portion of Brave while
   Git and Hospital remain open. Press **Ctrl+L** and type a harmless
   phrase into Brave's address bar **without Enter**, then delete it.
   Brave must receive this input immediately; Quickshell menus must not
   steal it. Click or enter Git again; Tab must once more operate Git.
7. Repeat step 4 with a second registered widget (e.g. Notifications).
   Test both release orders (grave first, Super first). Check the
   still-open overlays do not trap Brave keyboard when clicked.

## Evidence classification

- **Sway wrong key dispatch:** mode did not enter, directional bindings
  target default Sway `focus` instead of the temporary widget router.
- **Broker/owner desync:** a valid widget `koinoikosOwner` differs from
  `logicalKeyboardOwner` while the held navigation session is active.
- **Compositor seat failure:** selected Qt widget is logically correct,
  but Brave actually reacts to Tab. Source-level `owner` and Sway's
  native tree focus cannot prove or disprove this alone.
- **Qt internal shortcut failure:** the widget really receives the key
  but no Main Mode or intended control changes.
- **Recovery failure:** deliberate clicking Brave fails to allow typing,
  Enter or paste; an overlay may still hold exclusive keyboard focus.

Collect **which action**, **which surface changed**, relevant diagnostic
snapshots/binding events and whether Brave visibly responded. Do not alter
SwayFX, the symlinked config, permanently mapped Git/Hospital windows,
other widgets' internal key handlers, or the 120ms/48ms focus timers during
this diagnostic stage.

**Acceptance requires real operator-side desktop evidence**, not static CI.
