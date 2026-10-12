#!/usr/bin/env python3
"""AppControl shared Main Mode migration invariants."""
from pathlib import Path
r = Path(__file__).resolve().parents[2]
source = (r / "widgets/AppControlW.qml").read_text()
mode = (r / "components/ModeButton.qml").read_text()
rail = source[source.index("id: modeButton"):source.index("// SEARCH / RESULTS PANE")]
assert rail.count("ModeButton {") == 1
assert "id: systemModeButton" in rail
for needle in ("onPointerMoved:", "onPointerExited:", "onWheel:", "onTriggered:",
               "customPrimaryGlowSource: modeSymbol",
               "customPrimaryGlowSource: systemModeSymbol",
               "customLabelGlowSource: modeLabel",
               "favoritesFaceClickPulse = true", "fireKillRailOnce()",
               "sourceComponent: visible ? thermalIconComponent : undefined",
               "appControlWindow.switchMode(", "searchInput.forceActiveFocus()"):
    assert needle in rail, needle
assert "id: modeMouse" not in rail and "id: systemModeMouse" not in rail
assert "RectangularShadow {" not in rail and "DropShadow {" not in rail
for n in ("signal pointerExited()", "signal wheel(var wheelEvent)",
          "onExited: modeButton.pointerExited()", "onWheel: function(wheelEvent)"):
    assert n in mode, n
print("AppControl Main Mode: PASS")
