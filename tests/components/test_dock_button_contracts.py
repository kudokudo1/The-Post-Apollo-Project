#!/usr/bin/env python3
"""Static contracts for the reusable Git-derived dock button grammar."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPONENT = (ROOT / "components/DockButton.qml").read_text(encoding="utf-8")
GIT = (ROOT / "modules/Git.qml").read_text(encoding="utf-8")
TEMPLATE = (ROOT / "components/Basicbutton.qml.template").read_text(encoding="utf-8")
QMLDIR = (ROOT / "components/qmldir").read_text(encoding="utf-8")


def require(text: str, needle: str, message: str) -> None:
    assert needle in text, f"{message}: missing {needle!r}"


for needle, message in (
    ("default property alias contentData: contentHost.data", "custom module artwork slot"),
    ("property bool open: false", "persistent open state"),
    ("property Item contentGlowSource: contentHost", "exact custom artwork glow source"),
    ("property color openFillColor: Colors.yellow", "canonical yellow open fill"),
    ("property color openForegroundColor: Colors.magenta", "canonical magenta open foreground"),
    ("property color openGlowColor: Colors.magenta", "canonical magenta open glow"),
    ("property real contentGlowOpenOpacity: 1.0", "Git content glow energy"),
    ("property real softGlowOpenOpacity: 0.86", "Git tight halo energy"),
    ("property real wideGlowOpenOpacity: 0.22", "Git front wash energy"),
    ("property real softGlowSpread: 3", "Git tight halo spread"),
    ("property real wideGlowSpread: 10", "Git wide wash spread"),
    ("signal leftClicked(var mouseEvent)", "left-click contract"),
    ("signal rightClicked(var mouseEvent)", "right-click contract"),
    ("readonly property bool hovered:", "hover state contract"),
    ("readonly property bool pressed:", "pressed state contract"),
):
    require(COMPONENT, needle, message)

require(QMLDIR, "DockButton 1.0 DockButton.qml", "component registration")
require(GIT, "DockButton {", "Git must prove the reusable component")
require(GIT, "open: menuOpen", "Git open state must drive the component")
require(GIT, "contentGlowSource: gitMark", "Git glow must stay attached to the exact mark")
require(GIT, "onLeftClicked:", "Git must use component left-click behavior")
assert "signal rightClicked" not in GIT, "Git must inherit DockButton right-click signal without redeclaring it"
assert "onRightClicked:" not in GIT, "Git must not recursively re-emit the inherited right-click signal"
require(TEMPLATE, "DockButton {", "future button template must use reusable component")
require(TEMPLATE, "contentGlowSource: templateText", "template must demonstrate exact content glow targeting")

for forbidden in ("RectangularShadow {", "DropShadow {", "MouseArea {"):
    assert forbidden not in GIT, f"Git should not duplicate DockButton internals: {forbidden}"

print("Dock button contracts: PASS")
