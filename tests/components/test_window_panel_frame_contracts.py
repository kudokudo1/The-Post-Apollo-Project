#!/usr/bin/env python3
"""Static contracts for the shared large-window visual chassis."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPONENT = (ROOT / "components/WindowPanelFrame.qml").read_text(encoding="utf-8")
QMLDIR = (ROOT / "components/qmldir").read_text(encoding="utf-8")
APP_CONTROL = (ROOT / "widgets/AppControlW.qml").read_text(encoding="utf-8")
HOSPITAL = (ROOT / "widgets/HospitalW.qml").read_text(encoding="utf-8")
CPU_PLUS = (ROOT / "widgets/CpuPlusW.qml").read_text(encoding="utf-8")
WEATHER = (ROOT / "widgets/weather/WeatherStationW.qml").read_text(encoding="utf-8")
SOCIAL = (ROOT / "widgets/messanger/MessagingW.qml").read_text(encoding="utf-8")


def require(text: str, needle: str, message: str) -> None:
    assert needle in text, f"{message}: missing {needle!r}"


for needle, message in (
    ("default property alias contentData: surface.contentData", "content forwarding"),
    ("SurfaceFrame {", "shared surface composition"),
    ("property real surfaceOpacity: 1.0", "independent surface opacity"),
    ("property bool glowVisible: true", "glow visibility contract"),
    ("property color glowColor: borderColor", "semantic glow color"),
    ("property real closeGlowSpread: 6", "close glow spread"),
    ("property real closeGlowOpacity: 0.38", "close glow opacity"),
    ("property real wideGlowSpread: 12", "wide glow spread"),
    ("property real wideGlowOpacity: 0.12", "wide glow opacity"),
):
    require(COMPONENT, needle, message)

assert COMPONENT.count("RectangularShadow {") == 2
assert COMPONENT.count("SurfaceFrame {") == 1

for forbidden in (
    "PanelWindow {",
    "FloatingWindow {",
    "MouseArea {",
    "TapHandler {",
    "Keys.on",
    "WlrLayershell",
):
    assert forbidden not in COMPONENT, (
        "WindowPanelFrame must remain visual-only: " + forbidden
    )

require(QMLDIR, "WindowPanelFrame 1.0 WindowPanelFrame.qml", "component registration")

for needle, message in (
    ("WindowPanelFrame {\n        id: background", "AppControl shared chassis"),
    ("anchors.margins: 12\n\n        // Geometry anchor for the outer border/glow only.", "AppControl 12px glow gutter"),
    ("glowColor: Colors.orange\n        closeGlowSpread: 6\n        closeGlowOpacity: 0.38\n        wideGlowSpread: 12\n        wideGlowOpacity: 0.12", "AppControl glow values"),
):
    require(APP_CONTROL, needle, message)

for needle, message in (
    ("WindowPanelFrame {\n        id: frame", "Hospital shared chassis"),
    ("fillColor: Colors.black\n        borderWidth: 1\n        borderColor: Colors.magenta\n        surfaceOpacity: root.menuOpen ? 0.97 : 0.0", "Hospital surface values"),
    ("glowVisible: root.menuOpen\n        glowColor: Colors.magenta\n        closeGlowSpread: 6\n        closeGlowOpacity: 0.21\n        wideGlowSpread: 12\n        wideGlowOpacity: 0.05", "Hospital glow values"),
):
    require(HOSPITAL, needle, message)
assert "id: chassisGeometry" not in HOSPITAL

for needle, message in (
    ("WindowPanelFrame {\n        id: background", "CPU++ shared chassis"),
    ("glowColor: Colors.orange\n        closeGlowSpread: 6\n        closeGlowOpacity: 0.38\n        wideGlowSpread: 12\n        wideGlowOpacity: 0.12", "CPU++ glow values"),
):
    require(CPU_PLUS, needle, message)

for needle, message in (
    ("WindowPanelFrame {\n        id: stationBackground", "Weather shared chassis"),
    ("glowColor: Colors.cyan\n        closeGlowSpread: 4\n        closeGlowOpacity: 0.30\n        wideGlowSpread: 14\n        wideGlowOpacity: 0.10", "Weather glow values"),
):
    require(WEATHER, needle, message)

for needle, message in (
    ("WindowPanelFrame {\n        id: messagingContent", "Social shared chassis"),
    ("parent: socialWindow.contentItem\n        anchors.fill: parent", "Social FloatingWindow attachment"),
    ("fillColor: Colors.black\n        fillOpacity: 0.20\n        borderVisible: false\n        radius: 0", "Social translucent surface"),
    ("glowVisible: false", "Social preserves internal glow composition"),
):
    require(SOCIAL, needle, message)
assert "id: messagingBackground" not in SOCIAL

print("Window panel frame contracts: PASS")
