#!/usr/bin/env python3
"""Static contracts for the neutral reusable surface frame."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPONENT = (ROOT / "components/SurfaceFrame.qml").read_text(encoding="utf-8")
QMLDIR = (ROOT / "components/qmldir").read_text(encoding="utf-8")


def require(text: str, needle: str, message: str) -> None:
    assert needle in text, f"{message}: missing {needle!r}"


for needle, message in (
    ("default property alias contentData: contentHost.data", "arbitrary child-content slot"),
    ("property color fillColor: Colors.black", "default workbench fill"),
    ("property real fillOpacity: 1.0", "independent fill opacity"),
    ("property bool fillVisible: true", "independent fill visibility"),
    ("property color borderColor: Colors.cyan", "default accent border"),
    ("property real borderOpacity: 1.0", "independent border opacity"),
    ("property real borderWidth: 1.0", "canonical one-pixel frame default"),
    ("property bool borderVisible: true", "independent border visibility"),
    ("property real radius: 0", "square-first radius contract"),
    ("property bool clipContent: false", "opt-in content clipping"),
    ("readonly property Item frameSource: frameVisual", "clean border effect source"),
    ("readonly property Item fillSource: fillLayer", "clean fill effect source"),
    ("readonly property Item contentItem: contentHost", "content-host exposure"),
    ("opacity: surfaceFrame.fillOpacity", "fill-only opacity"),
    ("radius: surfaceFrame.radius", "shared fill/frame radius"),
    ("clip: surfaceFrame.clipContent", "content clipping must not require clipping the frame"),
    ("surfaceFrame.borderColor.a * surfaceFrame.borderOpacity", "border-only opacity"),
):
    require(COMPONENT, needle, message)

require(QMLDIR, "SurfaceFrame 1.0 SurfaceFrame.qml", "component registration")

for forbidden in (
    "MouseArea {",
    "DropShadow {",
    "SafeDropShadow {",
    "RectangularShadow {",
    "TapHandler {",
):
    assert forbidden not in COMPONENT, (
        "SurfaceFrame must remain structural and non-interactive/effect-neutral: "
        + forbidden
    )

assert "margins:" not in COMPONENT, (
    "SurfaceFrame must not own section padding; that belongs to composition/SectionFrame"
)
assert COMPONENT.count("Rectangle {") == 2, (
    "SurfaceFrame should contain only its independent fill and border visuals"
)

print("Surface frame contracts: PASS")
