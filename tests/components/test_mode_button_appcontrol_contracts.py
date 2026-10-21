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
# KILL's wider hover/firing faces change the centered wrapper width.
# Its only icon glow must share that moving parent. Other AppControl modes
# keep their existing default independent glow plane.
assert """primaryGlowHost:
                        index === appControlWindow.killModeIndex
                        ? modeSymbol.parent : null""" in rail
assert rail.count("primaryGlowHost:") == 1
assert rail.count("customPrimaryGlowSource: modeSymbol") == 1

hash_glow = (r / "components/TextHashGlow.qml").read_text()
assert "sourceSharesGlowHost:" in hash_glow
assert "safeSource.parent === parent" in hash_glow
assert "sourceSharesGlowHost ? Qt.point(safeSource.x, safeSource.y)" in hash_glow
assert "safeSource.mapToItem(parent, 0, 0)" in hash_glow
assert "sourceAttached && parent !== null" in hash_glow
assert "id: modeMouse" not in rail and "id: systemModeMouse" not in rail
assert "RectangularShadow {" not in rail and "DropShadow {" not in rail
for n in ("signal pointerExited()", "signal wheel(var wheelEvent)",
          "onExited: modeButton.pointerExited()", "onWheel: function(wheelEvent)"):
    assert n in mode, n
print("AppControl Main Mode: PASS")
