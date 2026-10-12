# Sub Mode keyboard-navigation contract

**Status:** Source-verified existing behavior, recorded October 12, 2026 (EDT).
This is an audit of current keyboard handling, **not** a new shortcut assignment or
a claim of on-device Qt testing. Do not replace a menu's working keyboard
ownership or change its mode semantics just to apply a visual component.

Sub Modes are subordinate choices **within** a selected Main Mode. A Main
Mode change, a secondary filter change, a selection highlight, and execution
of a selected item are different operations; keep their key bindings separate.

## AppControl // dedicated top and bottom Sub Mode keys

Source: [`widgets/AppControlW.qml`](../widgets/AppControlW.qml),
`Keys.onPressed: appControlWindow.handleKey(event)`;
`handleKey()`, `cycleTopSubmodeOrFilter()`,
`cycleBottomSubmodeOrFilter()`. The focused search input explicitly
reserves modified **Left** in several source modes via
`Keys.onShortcutOverride`.

| Binding | Existing command | Direction / meaning |
| --- | --- | --- |
| **Shift + Left** | `cycleTopSubmodeOrFilter(-1)` | Previous top/source Sub Mode or filter |
| **Shift + Right** | `cycleTopSubmodeOrFilter(1)` | Next top/source Sub Mode or filter |
| **Ctrl + Left** | `cycleBottomSubmodeOrFilter(-1)` | Previous bottom/launch Sub Mode or filter |
| **Ctrl + Right** | `cycleBottomSubmodeOrFilter(1)` | Next bottom/launch Sub Mode or filter |
| **Ctrl + Tab** | Toggle Thermal ↔ Fans | Thermal view only; when not on mode rail or detail pane |
| Tab / Shift + Tab | Main Mode or contextual result navigation | **Not** a dedicated Sub Mode shortcut |

The generic handlers consume the modified arrows even if the current Main
Mode has no corresponding top/bottom selector; do not infer an absent
selector from a swallowed key.

**Top row** (where implemented): FAVORITES filter; FILES Browse/Search;
REMOTE Configured/Known/All; APPS Native/Flatpak/Hidden; RUN
User/Terminal/System (`runListAll` internally); WINDOWS Windows/Tabs;
THERMAL Thermal/Fans; KILL Normal/Hunter.

**Bottom row** (where implemented): FAVORITES copied secondary/tertiary
filters; APPS Normal/Bottle/Toolbox launch mode; RUN Normal/Kitty/Toolbox
prefix; KILL Hunter metric selection (Combined/CPU/Memory/I/O/Age).
The bottom KILL cycling is available only in Hunter view.

**Keyboard ownership:** These shortcuts are handled by the active AppControl
input routing, after destructive confirmation's own keyboard handling.
The source's `Keys.onShortcutOverride` explicitly reserves modified
**Left** for RUN, FILES, REMOTE, APPS, WINDOWS and THERMAL, whereas the
general key handler also defines modified **Right**, FAVORITES and KILL.
Confirm delivery under text-input focus separately before treating every
path as runtime-certified. The selected item changes immediately; ordinary
Left/Right navigation and existing mouse-vs-keyboard arbitration must remain
unchanged.

## Git // primary page, GitHub bottom rail, and local Sub Modes

Source: [`widgets/GitW.qml`](../widgets/GitW.qml),
`Shortcut` declarations and the `selectPrimaryMode()` /
`selectBottomMode()` implementations.

| Binding | Location | Existing result |
| --- | --- | --- |
| **Shift + Left** or **Shift + Up** | Git window | Select **Git Local** main page |
| **Shift + Right** or **Shift + Down** | Git window | Select **GitHub Remote** main page |
| **Alt + Left** or **Alt + Up** | GitHub Remote | Previous bottom-mode page |
| **Alt + Right** or **Alt + Down** | GitHub Remote | Next bottom-mode page |
| **Alt + Left** | Git Local, with navigation history | **Go Back**, not a Sub Mode change |
| Plain arrow keys, then **Enter / Return** | Git Local and other keyboard-navigable controls | Move spatial keyboard selection and activate the focused control; not a dedicated per-Sub-Mode cycling key |

Git/GitHub bottom-mode cycle order is
**Control → Library → Profile → Projects → Issues → Pulls → Control**
(wraps in both directions).

**Do not confuse primary and secondary navigation.** Git's `Shift` arrows
choose one of two **main pages**; they do not advance through Git Local's
Changes/History/Repository/etc. Sub Mode selectors. Existing nested Git
views have their own selectable Sub Mode controls (`subMode` properties),
but this audit found **no separate global `Shift/Ctrl+arrow`-style cycle
shortcut for those Git Local nested Sub Modes**. They are reachable through
the registered keyboard-control navigation and activation model where
the control is keyboard-navigable.

Git shortcuts use application-scope `Shortcut` entries gated by
`menuOpen && keyboardActive`. Individual plain arrow shortcuts are further
disabled while a text editor or dial owns focus. Git Local `Alt+Left` is
only enabled when a navigation-back target exists and no text editor owns
the input. GitHub `Alt` navigation requires the GitHub page.

## Shared migration/verification rules

1. Keep **Main Mode page** keys separate from **Sub Mode** keys, focus
   navigation, and destructive action confirmation.
2. Preserve selection, direction, wrapping, disabled/unavailable modes,
   pointer-versus-keyboard authority and text-input focus.
3. Do not blanket-copy AppControl's Shift/Ctrl mapping onto Git: its
   primary Shift and GitHub Alt semantics are already implemented differently.
4. When extracting reusable Sub Mode buttons, preserve the host widget's
   existing keyboard handler; the button's glow/visual layer must not become
   the new navigation owner.
5. Static source inspection **does not prove every key reaches the handler
   under every active-focus state**. Before changing or claiming runtime
   correctness, test both directions, source row versus launch row, input
   focus, mode-rail focus, and Git versus GitHub page selection live.

**Related:** [visual-language recipes](visual-language-recipes.md) for
color, glow, semantic identity, and the distinct Main Mode button family.
