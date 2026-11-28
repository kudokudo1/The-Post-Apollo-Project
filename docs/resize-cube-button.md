# ResizeCubeButton // V14-A

Reusable 30x30 ActionButton for the operator-approved V14-A floating-chevron cube.
Existing directional ResizeButton controls remain unchanged. Use the same width
override as a neighboring arrow (28px compact, 30px default).

```qml
ResizeCubeButton {
    width: 30
    available: resizeAvailable
    selected: resizePopup.visible
    onLeftClicked: resizePopup.visible = !resizePopup.visible
}
```

The example names are caller-owned. This component does not open a popup, cycle
levels, change focus or resize any window on its own. It inherits normal input,
hover/press/selected, availability, keyboard-navigation and accessible activation
from ActionButton. Left click only; no second mouse handler. Use actual open
state for selection if it opens a surface.

The V14-A path order is canonical: preserve rear vertical behind inner top,
cyan back-right and magenta front-bottom junctions, outer foreground above
the inner cube. Exact geometry and 110-degree floating chevrons are preserved.
The prototype swatches are replaced with the existing Colors.qml values
(magenta #C74EC7, cyan #55CFCA, yellow #F2BE4E). Yellow border and magenta
perimeter persist; standard interaction fills are retained. A narrow dark
contrast backing is shown only on bright fills. The separate three-color
halo is drawn from the same strokes and viewBox beneath the unmodified core.
No detached effect sources, per-frame timer, or new resize engine. Static
SVG rings approximate a soft halo; native appearance is subject to operator
acceptance. The core SVG is authoritative; keep glow and contrast geometry
synchronized and run the regression check before edits.

Verify with `python3 tests/components/test_resize_cube_button_contract.py`.
Native QuickShell inspection at 28/30/44px and interaction/availability/keyboard
checks remain necessary. No widget migration or automatic size action in this PR.
