#!/usr/bin/env python3
"""Static contracts for the reusable ActionButton control."""

from pathlib import Path
import re

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
    ("id: contentHost", "custom content host"),
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
assert not re.search(r"(?m)^\s*DropShadow\s*\{", COMPONENT), (
    "ActionButton must not use an unguarded direct DropShadow"
)

print("Action button contracts: PASS")


# First Git proof migration: three historically identical MiniButton families
# now inherit ActionButton while preserving their current appearance. These
# values are migration-fidelity checks, not a declaration of final style.
GIT_MINI_BUTTONS = (
    "widgets/GitChangesView.qml",
    "widgets/GitHistoryView.qml",
    "widgets/GitRepositoryView.qml",
)

for relative in GIT_MINI_BUTTONS:
    source = (ROOT / relative).read_text(encoding="utf-8")
    require(source, "component MiniButton: ActionButton {", f"{relative} must inherit ActionButton")
    for needle in (
        "height: 28",
        "available: enabledAction",
        "acceptedButtons: Qt.LeftButton",
        "idleFillColor: Colors.black",
        "hoverFillColor: Colors.dark",
        "pressedFillColor: accent",
        "selectedFillColor: Colors.dark",
        "idleForegroundColor: accent",
        "selectedForegroundColor: Colors.white",
        "selectedBorderWidth: 2",
        "unavailableOpacity: 0.26",
        "contentGlowEnabled: false",
        "softGlowEnabled: false",
        "wideGlowEnabled: false",
    ):
        require(source, needle, f"preserve Git MiniButton values in {relative}")

    # The adapter may contain content, but must not rebuild the button engine.
    block = source[source.index("component MiniButton: ActionButton {"):]
    next_component = block.find("\n    component ", 1)
    if next_component >= 0:
        block = block[:next_component]
    assert "MouseArea {" not in block, f"{relative} reintroduced local MiniButton MouseArea"
    assert "RectangularShadow {" not in block, f"{relative} reintroduced local MiniButton halo"

print("Git MiniButton ActionButton migration: PASS")


GIT_ACTIONBUTTON_BATCH2 = {
    "widgets/GitBranchesView.qml": (
        "component BranchButton: ActionButton {",
        "height: 30",
        "available: enabledAction",
        "selected: selectedAction",
        "pressedFillColor:",
        "destructive ? Colors.red : Colors.orange",
        "selectedFillColor: Colors.dark",
        "hoverBorderWidth: 2",
        "selectedBorderWidth: 2",
        "unavailableOpacity: 1.0",
        "unavailableContentOpacity: 0.34",
        "contentGlowEnabled: false",
        "softGlowEnabled: false",
    ),
    "widgets/GitInteractiveRebaseView.qml": (
        "component RebaseButton: ActionButton {",
        "height: 30",
        "accentColor: accent",
        "available: enabledAction",
        "selected: selectedAction",
        "idleFillColor: Colors.dark",
        "hoverFillColor: Colors.black",
        "unavailableOpacity: 0.34",
        "labelPixelSize: 9",
        "contentPadding: 8",
        "contentGlowEnabled: false",
        "softGlowEnabled: false",
    ),
    "widgets/GitChangeTransferView.qml": (
        "component TransferButton: ActionButton {",
        "height: 32",
        "accentColor: accent",
        "available: enabledAction",
        "selected: selectedAction",
        "idleFillColor: Colors.dark",
        "hoverFillColor: Colors.black",
        "unavailableOpacity: 0.34",
        "labelPixelSize: 9",
        "contentPadding: 8",
        "contentGlowEnabled: false",
        "softGlowEnabled: false",
    ),
}

for relative, needles in GIT_ACTIONBUTTON_BATCH2.items():
    source = (ROOT / relative).read_text(encoding="utf-8")
    for needle in needles:
        require(source, needle, f"preserve Git ActionButton batch-2 values in {relative}")

    component_name = (
        "BranchButton"
        if "GitBranchesView" in relative
        else "RebaseButton"
        if "GitInteractiveRebaseView" in relative
        else "TransferButton"
    )
    block = source[source.index(f"component {component_name}: ActionButton {{"):]
    next_component = block.find("\n    component ", 1)
    if next_component >= 0:
        block = block[:next_component]
    assert "MouseArea {" not in block, f"{relative} reintroduced local {component_name} MouseArea"
    assert "RectangularShadow {" not in block, f"{relative} reintroduced local {component_name} halo"

print("Git ActionButton batch 2: PASS")
