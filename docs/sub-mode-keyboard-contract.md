# Sub Mode keyboard-navigation contract

**Status:** Source-verified existing behavior, recorded October 12, 2026 (EDT).
This is an audit of current keyboard handling, **not** a new shortcut assignment or
a claim of on-device Qt testing. Do not replace a menu's working keyboard
ownership or change its mode semantics just to apply a visual component.

Sub Modes are subordinate choices **within** a selected Main Mode. A Main
Mode change, a secondary filter change, a selection highlight, and execution
of a selected item are different operations; keep their key bindings separate.

## Cross-menu Main Mode versus Sub Mode key comparison

**2026-10-12 source verification.** This is about **keyboard keys**, not
visual button color, size or QML widget identity. "Main"/"Sub" below
describes the navigation hierarchy; Hospital Floors and Beds are
repository/checkout selectors, not literal instances of `ModeButton.qml`.

| Menu | Main / primary context key | Sub / secondary context key | Important focus or meaning difference |
| --- | --- | --- | --- |
| **AppControl** | `Tab` next Main Mode, `Shift+Tab` previous when in ordinary selector context | `Shift+Left/Right` top/source selector; `Ctrl+Left/Right` bottom/launch selector | `Tab` instead moves within mode rail or between results while mode-rail/detail focus owns it |
| **Git / GitHub** | `Shift+Left/Up` selects Git Local, `Shift+Right/Down` selects GitHub Remote | **GitHub Remote only:** `Alt+Left/Up` previous bottom mode, `Alt+Right/Down` next | Git Main Mode keys choose a **specific page**, not a generic next/previous cycle. Git Local `Alt+Left` means navigation **Back** if history exists; nested Git Local subModes have no matching global cycle shortcut |
| **Hospital** | **Plain `Left/Right`** cycles repository **Floors** while in Room selector | `Shift+Left/Right` cycles local-checkout **Beds** | Plain arrows become navigation inside Room/Bed controls; no universal `Tab` main-mode key or `Ctrl+Left/Right` secondary key in audited Hospital root |

### Collision to settle before normalizing shortcuts

`Shift+Left/Right` already has **three incompatible meanings**:
AppControl top Sub Mode, Git/GitHub primary page, Hospital Bed selection.
A future shared keyboard grammar therefore **requires an operator-approved
remapping plan**, not a mechanical reuse of Main Mode or Sub Mode QML
components. Do not change any existing key bindings as part of documenting
this audit.

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

## Hospital // Floors, Beds and Room-control ownership

Source: [`widgets/HospitalW.qml`](../widgets/HospitalW.qml).
The root-level `Shortcut` declarations call `moveRoomControl(dx,dy)`
for plain arrows, `cycleBed(delta)` for `Shift+Left/Right`, and
`handleRoomEnter()` for `Enter/Return`.

| Keys | Only when | Action |
| --- | --- | --- |
| **Left / Right** | Room selector, no nested Room/Bed control mode and no operations surface | Previous/next **Floor (repository)** via `moveRoomControl` → `cycleFloor` |
| **Up / Down** | Room selector | Previous/next **Room** |
| **Shift + Left / Right** | Hospital open, keyboard active, not typing in Intercom/Receptionist | Previous/next **Bed (local checkout)** via `cycleBed` |
| **Arrow keys** | Room action grid or Bed-control focus | Navigate active controls / return to Room selection, **not** Floor switching |
| **Enter / Return** | Room selector/controls | Enter or activate currently selected Room control; in Bed-control mode invokes Move Bed action if enabled |

The **Floor** has separate mouse prev/next buttons and a persistent
`SelectorSlider` that call `cycleFloor` / `selectFloor`; the **Bed**
has mouse prev/next controls plus the keyboard Shift arrows. The Floor
shortcut is **contextual plain Left/Right**, not a global `Shortcut`
with the floor name. `floorSwitchEnabled` and `bedSwitchEnabled`
block changes during unsupported/ongoing operations. Hospital's
`Shortcut` keys require open menu and keyboard ownership, and ordinary
movement keys are disabled while `intercomTyping` or
`receptionistTyping`.

**Do not treat Hospital's `Shift+Left/Right` as Main Mode navigation**
just because the same keys select the Git primary page, or as generic
Sub Mode navigation outside Beds just because AppControl uses them for
its top selector. Also do not bind operation-confirmation actions to
generic mode-navigation keys.

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
