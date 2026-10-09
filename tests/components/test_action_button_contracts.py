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


def component_block(source: str, name: str) -> str:
    marker = f"component {name}:"
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    quote = None
    escaped = False
    line_comment = False
    block_comment = False

    i = brace
    while i < len(source):
        char = source[i]
        nxt = source[i + 1] if i + 1 < len(source) else ""

        if line_comment:
            if char == "\n":
                line_comment = False
            i += 1
            continue

        if block_comment:
            if char == "*" and nxt == "/":
                block_comment = False
                i += 2
                continue
            i += 1
            continue

        if quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            i += 1
            continue

        if char == "/" and nxt == "/":
            line_comment = True
            i += 2
            continue

        if char == "/" and nxt == "*":
            block_comment = True
            i += 2
            continue

        if char in ('"', "'"):
            quote = char
            i += 1
            continue

        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start:i + 1]

        i += 1

    raise AssertionError(f"unterminated QML component {name}")


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
    ("property real softGlowMargin: 0", "lossless halo-margin preservation"),
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
    block = component_block(source, "MiniButton")
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
    block = component_block(source, component_name)
    assert "MouseArea {" not in block, f"{relative} reintroduced local {component_name} MouseArea"
    assert "RectangularShadow {" not in block, f"{relative} reintroduced local {component_name} halo"

print("Git ActionButton batch 2: PASS")


# First AppControl proof migration: the three resource FREEZE/THAW controls
# share ActionButton state/pointer/halo machinery without absorbing selectors
# or changing their mode-specific detail indices and artwork.
APPCONTROL = (ROOT / "widgets/AppControlW.qml").read_text(encoding="utf-8")

for control_id in ("appFreezeAction", "tabFreezeAction", "windowFreezeAction"):
    marker = f"id: {control_id}"
    marker_pos = APPCONTROL.index(marker)
    block_start = APPCONTROL.rfind("ActionButton {", 0, marker_pos)
    assert block_start >= 0, f"{control_id} must be hosted by ActionButton"

    # The nearest old Rectangle declaration must not sit between the shared
    # shell and the id marker.
    rectangle_start = APPCONTROL.rfind("Rectangle {", 0, marker_pos)
    assert rectangle_start < block_start, f"{control_id} fell back to a private Rectangle"

    require(APPCONTROL[block_start:marker_pos + 2400], "available: canFreeze", f"{control_id} availability")
    require(APPCONTROL[block_start:marker_pos + 2400], "suppressHover: appControlWindow.keyboardActive", f"{control_id} keyboard/mouse separation")
    require(APPCONTROL[block_start:marker_pos + 2400], "softGlowMargin: 4", f"{control_id} preserved halo geometry")

for private_mouse in (
    "id: appFreezeActionMouse",
    "id: tabFreezeActionMouse",
    "id: windowFreezeActionMouse",
):
    assert private_mouse not in APPCONTROL, f"AppControl reintroduced private freeze pointer engine: {private_mouse}"

print("AppControl freeze ActionButton migration: PASS")


# Second AppControl proof migration: destructive APP KILL, TAB CLOSE, and
# WINDOW KILL controls use the same ActionButton engine while preserving their
# red semantics and their mode-specific activation paths.
for control_id in ("appKillAction", "tabCloseActionBelowFreeze", "windowKillAction"):
    marker = f"id: {control_id}"
    marker_pos = APPCONTROL.index(marker)
    block_start = APPCONTROL.rfind("ActionButton {", 0, marker_pos)
    assert block_start >= 0, f"{control_id} must be hosted by ActionButton"

    rectangle_start = APPCONTROL.rfind("Rectangle {", 0, marker_pos)
    assert rectangle_start < block_start, f"{control_id} fell back to a private Rectangle"

    window = APPCONTROL[block_start:marker_pos + 2600]
    require(window, "destructive: true", f"{control_id} destructive semantics")
    require(window, "pressedFillColor: Colors.red", f"{control_id} pressed fill")
    require(window, "pressedBorderColor: Colors.black", f"{control_id} pressed border")

for private_mouse in (
    "id: appKillActionMouse",
    "id: tabCloseActionBelowFreezeMouse",
    "id: windowKillActionMouse",
):
    assert private_mouse not in APPCONTROL, f"AppControl reintroduced private destructive pointer engine: {private_mouse}"

print("AppControl destructive ActionButton migration: PASS")
