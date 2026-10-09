#!/usr/bin/env python3
"""Static contracts for the reusable inset-aware section frame."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPONENT = (ROOT / "components/SectionFrame.qml").read_text(encoding="utf-8")
QMLDIR = (ROOT / "components/qmldir").read_text(encoding="utf-8")


def require(text: str, needle: str, message: str) -> None:
    assert needle in text, f"{message}: missing {needle!r}"


for needle, message in (
    ("default property alias contentData: contentHost.data", "arbitrary section content slot"),
    ("SurfaceFrame {", "section must compose the neutral surface primitive"),
    ("property alias fillColor: surface.fillColor", "fill forwarding"),
    ("property alias fillOpacity: surface.fillOpacity", "fill-opacity forwarding"),
    ("property alias fillVisible: surface.fillVisible", "fill visibility forwarding"),
    ("property alias borderColor: surface.borderColor", "border forwarding"),
    ("property alias borderOpacity: surface.borderOpacity", "border-opacity forwarding"),
    ("property alias borderWidth: surface.borderWidth", "border-width forwarding"),
    ("property alias borderVisible: surface.borderVisible", "border visibility forwarding"),
    ("property alias radius: surface.radius", "radius forwarding"),
    ("property alias clipContent: surface.clipContent", "clip forwarding"),
    ("property real inset: 0", "lossless zero-inset default"),
    ("property real leftInset: inset", "left inset override contract"),
    ("property real rightInset: inset", "right inset override contract"),
    ("property real topInset: inset", "top inset override contract"),
    ("property real bottomInset: inset", "bottom inset override contract"),
    ("leftMargin: sectionFrame.leftInset", "left inset geometry"),
    ("rightMargin: sectionFrame.rightInset", "right inset geometry"),
    ("topMargin: sectionFrame.topInset", "top inset geometry"),
    ("bottomMargin: sectionFrame.bottomInset", "bottom inset geometry"),
    ("readonly property Item frameSource: surface.frameSource", "external frame effect source"),
    ("readonly property Item fillSource: surface.fillSource", "external fill effect source"),
    ("readonly property Item contentItem: contentHost", "content host exposure"),
):
    require(COMPONENT, needle, message)

require(QMLDIR, "SectionFrame 1.0 SectionFrame.qml", "component registration")

for forbidden in (
    "MouseArea {",
    "TapHandler {",
    "DropShadow {",
    "SafeDropShadow {",
    "RectangularShadow {",
    "Row {",
    "Column {",
    "RowLayout {",
    "ColumnLayout {",
):
    assert forbidden not in COMPONENT, (
        "SectionFrame must own inset geometry only, not interaction/layout/effects: "
        + forbidden
    )

assert COMPONENT.count("SurfaceFrame {") == 1, (
    "SectionFrame must have exactly one shared surface implementation"
)
assert "property real inset: 7" not in COMPONENT
assert "property real inset: 8" not in COMPONENT

print("Section frame contracts: PASS")
