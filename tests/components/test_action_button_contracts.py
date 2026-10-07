#!/usr/bin/env python3
"""Static contracts for the reusable ActionButton control."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPONENT = (ROOT / "components/ActionButton.qml").read_text(encoding="utf-8")
TEMPLATE = (ROOT / "components/ActionButton.qml.template").read_text(encoding="utf-8")
QMLDIR = (ROOT / "components/qmldir").read_text(encoding="utf-8")


def require(text: str, needle: str, message: str) -> None:
    assert needle in text, f"{message}: missing {needle!r}"


# Protect capabilities and semantics rather than fossilizing the current
# historical style numbers. Defaults can be intentionally synchronized later.
for needle, message in (
    ("default property alias contentData: contentHost.data", "custom content slot"),
    ("property bool available: true", "semantic availability"),
    ("property bool interactive: available", "availability/interaction separation"),
    ("property bool selected: false", "selection state"),
    ("property bool keyboardSelected: false", "keyboard selection state"),
    ("property bool suppressHover: false", "mouse/keyboard hover separation"),
    ("property bool hoverWhenUnavailable: false", "optional unavailable hover tracking"),
    ("property bool destructive: false", "destructive semantic state"),
    ("property color accentColor: Colors.cyan", "accent identity"),
    ("property real unavailableOpacity:", "whole-control availability fade"),
    ("property real unavailableFillOpacity:", "layered fill availability fade"),
    ("property real unavailableBorderOpacity:", "layered border availability fade"),
    ("property real unavailableContentOpacity:", "layered content availability fade"),
    ("property real unavailableContentGlowOpacity:", "layered content-glow availability fade"),
    ("property real unavailableSoftGlowOpacity:", "layered halo availability fade"),
    ("property real unavailableWideGlowOpacity:", "layered wide-halo availability fade"),
    ("readonly property color foregroundColor:", "custom-content foreground state"),
    ("readonly property color fillColor:", "fill state contract"),
    ("readonly property color activeBorderColor:", "border state contract"),
    ("readonly property bool hovered:", "hover state contract"),
    ("readonly property bool pressed:", "press state contract"),
    ("property Item contentGlowSource:", "exact content glow targeting"),
    ("property bool wideGlowEnabled: false", "optional richer second halo"),
    ("signal triggered(var mouseEvent)", "primary action signal"),
    ("signal leftClicked(var mouseEvent)", "left-click signal"),
    ("signal rightClicked(var mouseEvent)", "right-click signal"),
    ("signal pointerMoved(var mouseEvent)", "pointer movement signal"),
    ("signal pressStateChanged(bool pressed)", "press-state forwarding"),
    ("signal wheel(var wheelEvent)", "wheel forwarding"),
    ("SafeDropShadow {", "teardown-safe content glow"),
):
    require(COMPONENT, needle, message)

require(QMLDIR, "ActionButton 1.0 ActionButton.qml", "component registration")
require(TEMPLATE, "ActionButton {", "template must compose the real component")
require(TEMPLATE, "available: true", "template must teach semantic availability")
require(TEMPLATE, "unavailableFillOpacity:", "template must document layered availability")
assert "DropShadow {" not in COMPONENT, "ActionButton must not use an unguarded direct DropShadow"

print("Action button contracts: PASS")
