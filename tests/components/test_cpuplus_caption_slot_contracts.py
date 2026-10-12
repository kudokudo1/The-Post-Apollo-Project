#!/usr/bin/env python3
"""CPU++ Main Mode must retain icon/caption slots and specialized behavior."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
qml = (ROOT / "widgets/CpuPlusW.qml").read_text(encoding="utf-8")
mode = qml[qml.index("id: modeButton\n"):qml.index("// TWO-BODY MONITOR ADAPTER")]
assert "ModeButton {" in qml[:qml.index("id: modeButton\n")]
for token in (
    "customArtwork: true", "sampledTextActive ? textModeIcon : null",
    "sampledTextActive ? modeCaption : null",
    'sampledTextActive && modelData.kind !== "thermal"',
    "id: modeIconSlot", "id: modeCaptionSlot",
    "id: textModeIcon", "id: modeCaption", "QuietText {",
    "width: modeCaption.implicitWidth",
    "height: modeCaption.implicitHeight",
    "anchors.horizontalCenter: parent.horizontalCenter",
    "clip: false", "onTriggered:", "favoritesFaceClickPulse = true",
    "cpuPlusWindow.selectMode(index)", "scale:",
    "duration: 90", "Easing.OutQuad",
):
    assert token in mode, token
for forbidden in ("TextHashGlow {", "MouseArea {", "ModeButtonCloseHalo {",
                  "ModeButtonWideHalo {", "RectangularShadow {"):
    assert forbidden not in mode, forbidden
assert 'import "thermal"' in qml
assert qml.count("id: thermalIconComponent") == 1
component = qml[qml.index("id: thermalIconComponent"):qml.index("// WINDOW", qml.index("id: thermalIconComponent"))]
assert component.count("ThermalIcon { }") == 1
assert "id: thermalIconRoot" not in qml
assert "item.glowColor" not in qml
assert qml.count("item.iconColor = Qt.binding") == 4
assert qml.count("item.glowOpacity =") == 4
assert qml.count("item.pressed = Qt.binding") == 3
shared = (ROOT / "widgets/thermal/ThermalIcon.qml").read_text(encoding="utf-8")
for token in ("property color iconColor:", "property real glowOpacity:",
              "property bool pressed:"):
    assert token in shared, token
print("CPU++ main-mode caption and artwork: PASS")
