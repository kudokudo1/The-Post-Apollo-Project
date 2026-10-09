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
    ("property alias interactionData: interactionHost.data", "interactive overlay data slot"),
    ("property alias interactionItem: interactionHost", "interactive overlay item"),
    ("id: interactionHost", "interactive overlay host"),
    ("z: 20", "interactive overlay above pointer layer"),
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


# Third AppControl proof migration: LAUNCH and repeated desktop actions carry
# nested favorite-star controls. Their shared action pointer engine stays below
# the explicit ActionButton interaction overlay so the star remains independent.
for control_id, root_mouse, star_id in (
    ("launchAction", "launchMouse", "launchActionFavoriteStar"),
    ("desktopActionButton", "desktopActionMouse", "desktopActionFavoriteStar"),
):
    marker = f"id: {control_id}"
    marker_pos = APPCONTROL.index(marker)
    block_start = APPCONTROL.rfind("ActionButton {", 0, marker_pos)
    assert block_start >= 0, f"{control_id} must be hosted by ActionButton"

    window = APPCONTROL[block_start:marker_pos + 7000]
    assert f"id: {root_mouse}" not in window, f"{control_id} reintroduced its root pointer engine"
    require(window, f"id: {star_id}", f"{control_id} favorite star survives migration")
    require(window, f"parent: {control_id}.interactionItem", f"{control_id} favorite star uses interaction overlay")
    require(window, "suppressHover: appControlWindow.keyboardActive", f"{control_id} keyboard/mouse separation")

launch_marker = APPCONTROL.index("id: launchAction")
launch_window = APPCONTROL[launch_marker:launch_marker + 3800]
for needle in (
    "property var currentResult:",
    "property var sourceResult:",
    "property bool canLaunch:",
    "property bool targetIsFlatpak:",
):
    require(launch_window, needle, "launch target-state preservation")

print("AppControl star-bearing ActionButton migration: PASS")


# Fourth AppControl proof migration: RUN actions share ActionButton while each
# variant keeps its own idle accent language and independent favorite star.
RUN_ACTIONS = {
    "runAction": ("runActionMouse", "runActionFavoriteStar", "Colors.cyan", "Colors.cyan", 0),
    "runKittyAction": ("runKittyActionMouse", "runKittyActionFavoriteStar", "Colors.magenta", "Colors.magenta", 1),
    "runFloatAction": ("runFloatActionMouse", "runFloatActionFavoriteStar", "Colors.white", "Colors.cyan", 2),
    "runFullscreenAction": ("runFullscreenActionMouse", "runFullscreenActionFavoriteStar", "Colors.omnitrix", "Colors.omnitrix", 3),
    "runToolboxAction": ("runToolboxActionMouse", "runToolboxActionFavoriteStar", "Colors.omnitrix", "Colors.omnitrix", 4),
}

for control_id, (root_mouse, star_id, idle_border, idle_glow, action_index) in RUN_ACTIONS.items():
    marker = f"id: {control_id}"
    marker_pos = APPCONTROL.index(marker)
    block_start = APPCONTROL.rfind("ActionButton {", 0, marker_pos)
    assert block_start >= 0, f"{control_id} must be hosted by ActionButton"

    window = APPCONTROL[block_start:marker_pos + 7600]
    assert f"id: {root_mouse}" not in window, f"{control_id} reintroduced its root pointer engine"
    require(window, f"id: {star_id}", f"{control_id} favorite star survives migration")
    require(window, f"parent: {control_id}.interactionItem", f"{control_id} favorite star uses interaction overlay")
    require(window, f"selectedDetailActionIndex === {action_index}", f"{control_id} action index")
    require(window, f"idleBorderColor: {idle_border}", f"{control_id} idle border identity")
    require(window, f"idleSoftGlowColor: {idle_glow}", f"{control_id} idle halo identity")

run_toolbox_marker = APPCONTROL.index("id: runToolboxAction")
run_toolbox_window = APPCONTROL[run_toolbox_marker:run_toolbox_marker + 3200]
require(run_toolbox_window, "property bool canLaunch:", "RUN toolbox availability state")
require(run_toolbox_window, "available: canLaunch", "RUN toolbox ActionButton availability")
require(run_toolbox_window, "unavailableOpacity: 0.48", "RUN toolbox unavailable fade")

print("AppControl RUN ActionButton migration: PASS")


# Fifth AppControl proof migration: hidden-command and application alternate
# launch actions share ActionButton without flattening their accent identities.
ALT_LAUNCH_ACTIONS = {
    "hiddenActionButton": ("hiddenActionMouse", None),
    "hiddenBottleAction": ("hiddenBottleActionMouse", None),
    "hiddenToolboxAction": ("hiddenToolboxActionMouse", None),
    "appBottleAction": ("appBottleActionMouse", "appBottleActionFavoriteStar"),
    "appToolboxAction": ("appToolboxActionMouse", "appToolboxActionFavoriteStar"),
}

for control_id, (root_mouse, star_id) in ALT_LAUNCH_ACTIONS.items():
    marker = f"id: {control_id}"
    marker_pos = APPCONTROL.index(marker)
    block_start = APPCONTROL.rfind("ActionButton {", 0, marker_pos)
    assert block_start >= 0, f"{control_id} must be hosted by ActionButton"
    window = APPCONTROL[block_start:marker_pos + 9000]
    assert f"id: {root_mouse}" not in window, f"{control_id} reintroduced its root pointer engine"
    require(window, "acceptedButtons: Qt.LeftButton", f"{control_id} left-click-only donor contract")
    if star_id is not None:
        require(window, f"id: {star_id}", f"{control_id} favorite star survives migration")
        require(window, f"parent: {control_id}.interactionItem", f"{control_id} favorite star uses interaction overlay")

hidden_marker = APPCONTROL.index("id: hiddenActionButton")
hidden_window = APPCONTROL[hidden_marker:hidden_marker + 3900]
require(hidden_window, "readonly property color haloColor:", "hidden action dynamic halo")
require(hidden_window, "modelData.label === \"FLOAT\"", "hidden FLOAT cyan halo exception")
require(hidden_window, "idleBorderColor: modelData.accent", "hidden action per-row accent border")

hidden_bottle_marker = APPCONTROL.index("id: hiddenBottleAction")
hidden_bottle_window = APPCONTROL[hidden_bottle_marker:hidden_bottle_marker + 3000]
require(hidden_bottle_window, "property bool canRun:", "hidden BOTTLES availability state")
require(hidden_bottle_window, "available: canRun", "hidden BOTTLES ActionButton availability")
require(hidden_bottle_window, "unavailableOpacity: 0.38", "hidden BOTTLES unavailable fade")

app_bottle_marker = APPCONTROL.index("id: appBottleAction")
app_bottle_window = APPCONTROL[app_bottle_marker:app_bottle_marker + 4300]
for needle in ("property var currentResult:", "property int detailIndex:", "property bool hasBottle:"):
    require(app_bottle_window, needle, "application BOTTLES target state")
require(app_bottle_window, "available: hasBottle && !appControlWindow.bottlesLoading", "application BOTTLES availability")

app_toolbox_marker = APPCONTROL.index("id: appToolboxAction")
app_toolbox_window = APPCONTROL[app_toolbox_marker:app_toolbox_marker + 4300]
for needle in ("property var currentResult:", "property int detailIndex:", "property bool canLaunch:"):
    require(app_toolbox_window, needle, "application TOOLBOX target state")
require(app_toolbox_window, "available: canLaunch", "application TOOLBOX availability")

# Every AppControl action migrated so far came from a default MouseArea, whose
# acceptedButtons contract is left-click-only. Shared ActionButton defaults to
# left+right, so each adapter must preserve the donor behavior explicitly.
APPCONTROL_LEFT_ONLY_ACTIONS = (
    "appFreezeAction", "tabFreezeAction", "windowFreezeAction",
    "appKillAction", "tabCloseActionBelowFreeze", "windowKillAction",
    "launchAction", "desktopActionButton",
    "runAction", "runKittyAction", "runFloatAction", "runFullscreenAction", "runToolboxAction",
    "hiddenActionButton", "hiddenBottleAction", "hiddenToolboxAction",
    "appBottleAction", "appToolboxAction",
    "hiddenKillAction", "appMuteAction", "windowMuteAction", "runKillAction",
    "windowPrimaryActionButton",
    "fileActionButton", "remoteActionButton",
    "appTabControlButton",
)
for control_id in APPCONTROL_LEFT_ONLY_ACTIONS:
    marker_pos = APPCONTROL.index(f"id: {control_id}")
    block_start = APPCONTROL.rfind("ActionButton {", 0, marker_pos)
    root_prefix = APPCONTROL[block_start:marker_pos + 1800]
    assert re.search(
        r"pointerCursorShape:\s*Qt\.ArrowCursor\s*\n\s*acceptedButtons:\s*Qt\.LeftButton",
        root_prefix,
    ), f"{control_id} root accepted-buttons fidelity"

print("AppControl alternate launch ActionButton migration: PASS")


# Sixth AppControl proof migration: remaining simple mute/kill surfaces share
# ActionButton while preserving green audio identity and destructive red states.
MUTE_KILL_ACTIONS = {
    "hiddenKillAction": "hiddenKillActionMouse",
    "appMuteAction": "appMuteActionMouse",
    "windowMuteAction": "windowMuteActionMouse",
    "runKillAction": "runKillActionMouse",
}

for control_id, root_mouse in MUTE_KILL_ACTIONS.items():
    marker = f"id: {control_id}"
    marker_pos = APPCONTROL.index(marker)
    block_start = APPCONTROL.rfind("ActionButton {", 0, marker_pos)
    assert block_start >= 0, f"{control_id} must be hosted by ActionButton"
    window = APPCONTROL[block_start:marker_pos + 7800]
    assert f"id: {root_mouse}" not in window, f"{control_id} reintroduced its root pointer engine"
    assert re.search(
        r"pointerCursorShape:\s*Qt\.ArrowCursor\s*\n\s*acceptedButtons:\s*Qt\.LeftButton",
        window,
    ), f"{control_id} left-click-only donor contract"

hidden_kill_marker = APPCONTROL.index("id: hiddenKillAction")
hidden_kill_window = APPCONTROL[hidden_kill_marker:hidden_kill_marker + 2600]
for needle in (
    "destructive: true",
    "pressedFillColor: Colors.red",
    "pressedBorderColor: Colors.black",
    "softGlowMargin: 4",
    "softGlowPressedOpacity: 0.92",
):
    require(hidden_kill_window, needle, "hidden KILL destructive fidelity")
require(hidden_kill_window, "selectedDetailActionIndex === 6", "hidden KILL action index")

app_mute_marker = APPCONTROL.index("id: appMuteAction")
app_mute_window = APPCONTROL[app_mute_marker:app_mute_marker + 4400]
for needle in (
    "property var currentResult:",
    "property int detailIndex:",
    "property bool canMute:",
    "available: canMute",
    "unavailableOpacity: 0.42",
    "idleSoftGlowColor: Colors.green",
    "hoverSoftGlowColor: Colors.green",
):
    require(app_mute_window, needle, "application MUTE fidelity")

window_mute_marker = APPCONTROL.index("id: windowMuteAction")
window_mute_window = APPCONTROL[window_mute_marker:window_mute_marker + 3700]
require(window_mute_window, "selectedDetailActionIndex === 5", "window MUTE action index")
require(window_mute_window, "idleSoftGlowColor: Colors.green", "window MUTE green halo")
require(window_mute_window, "hoverSoftGlowColor: Colors.green", "window MUTE hover halo")

run_kill_marker = APPCONTROL.index("id: runKillAction")
run_kill_window = APPCONTROL[run_kill_marker:run_kill_marker + 9000]
for needle in (
    "available: appControlWindow.runKillAvailable",
    "unavailableOpacity: 0.48",
    "destructive: true",
    "pressedFillColor: Colors.red",
    "pressedBorderColor: Colors.black",
    "softGlowPressedOpacity: 0.92",
    "selectedDetailActionIndex === 5",
    "id: runKillActionFavoriteStar",
    "parent: runKillAction.interactionItem",
):
    require(run_kill_window, needle, "RUN KILL fidelity")

print("AppControl mute/kill ActionButton migration: PASS")


# Seventh AppControl proof migration: the five primary window operations are
# immediate actions, but retain their index-specific cyan/white/omnitrix visual
# identities through one ActionButton delegate.
window_primary_marker = APPCONTROL.index("id: windowPrimaryActionButton")
window_primary_start = APPCONTROL.rfind("delegate: ActionButton {", 0, window_primary_marker)
assert window_primary_start >= 0, "window primary delegate must use ActionButton"
window_primary = APPCONTROL[window_primary_start:window_primary_marker + 7600]

repeater_prefix = APPCONTROL[max(0, window_primary_start - 180):window_primary_start]
require(repeater_prefix, "model: 5", "window primary repeater cardinality")

for needle in (
    "acceptedButtons: Qt.LeftButton",
    "index === 2 || index === 4",
    "index === 2\n                            ? Colors.white",
    "index === 4\n                            ? Colors.omnitrix",
    "index === 0 ? Colors.dark : Colors.black",
    "idleBorderColor: inactiveAccent",
    "idleSoftGlowColor: glowAccent",
    "softGlowPressedOpacity: 0.0",
    "selectedDetailActionIndex = index;",
):
    require(window_primary, needle, "window primary ActionButton fidelity")

assert "id: windowPrimaryActionMouse" not in window_primary, (
    "window primary actions reintroduced private pointer engine"
)
for old_alias in (
    "windowPrimaryActionButton.isPressed",
    "windowPrimaryActionButton.isHovered",
    "windowPrimaryActionButton.isSelected",
):
    assert old_alias not in window_primary, f"window primary action retained old state alias: {old_alias}"

print("AppControl window-primary ActionButton migration: PASS")


# Eighth AppControl proof migration: FILES and REMOTE rows are immediate
# operations, not navigation selectors. Both repeaters now share ActionButton
# while preserving their model-provided accent colors and magenta selection.
for repeater_id, control_id, old_mouse, expected_count in (
    ("fileActionsRepeater", "fileActionButton", "fileActionMouse", 4),
    ("remoteActionsRepeater", "remoteActionButton", "remoteActionMouse", 6),
):
    repeater_marker = APPCONTROL.index(f"id: {repeater_id}")
    control_marker = APPCONTROL.index(f"id: {control_id}", repeater_marker)
    block_start = APPCONTROL.rfind("ActionButton {", repeater_marker, control_marker)
    assert block_start >= 0, f"{control_id} must use ActionButton"
    window = APPCONTROL[block_start:control_marker + 4400]

    assert f"id: {old_mouse}" not in window, f"{control_id} reintroduced private pointer engine"
    for needle in (
        "acceptedButtons: Qt.LeftButton",
        "idleFillColor: Colors.dark",
        "idleBorderColor: modelData.accent",
        "hoverBorderColor: Colors.orange",
        "selectedBorderColor: Colors.magenta",
        "pressedBorderColor:",
        "selected ? Colors.magenta",
        "softGlowSpread: selected || hovered ? 4 : 2",
        "idleSoftGlowColor: modelData.accent",
        "selectedSoftGlowColor: Colors.magenta",
        "softGlowIdleOpacity: 0.22",
        "softGlowHoverOpacity: 0.48",
        "selectedDetailActionIndex = index;",
    ):
        require(window, needle, f"{control_id} action-row fidelity")

    repeater_window = APPCONTROL[repeater_marker:control_marker]
    require(repeater_window, f"model: [", f"{repeater_id} retains explicit model")
    # Cardinality is protected through the existing detail-action contract:
    # FILES exposes 4 actions and REMOTE exposes 6.
    detail_count_needle = (
        "if (selectedResultIsFile())\n            return 4;"
        if expected_count == 4
        else "if (selectedResultIsRemote())\n            return 6;"
    )
    require(APPCONTROL, detail_count_needle, f"{repeater_id} action count")

print("AppControl file/remote ActionButton migration: PASS")


# Ninth AppControl proof migration: dynamic TAB controls are immediate actions,
# but retain semantic subtypes (mute/new-tab/builtin) and keep CLOSE delegated
# to the dedicated destructive close control.
tab_action_marker = APPCONTROL.index("id: appTabControlButton")
tab_action_start = APPCONTROL.rfind("delegate: ActionButton {", 0, tab_action_marker)
assert tab_action_start >= 0, "TAB control delegate must use ActionButton"
tab_action = APPCONTROL[tab_action_start:tab_action_marker + 9200]

for needle in (
    "visible: !isCloseAction",
    "acceptedButtons: Qt.LeftButton",
    "readonly property bool isMuteAction:",
    "readonly property bool isNewTabAction:",
    "readonly property bool isBuiltinDesktopAction:",
    "isCloseAction\n                            ? Colors.red",
    "isMuteAction\n                            ? Colors.omnitrix",
    "isBuiltinDesktopAction\n                            ? Colors.orange",
    "hovered || selected\n                            ? Colors.orange",
    "hoverFillColor:\n                            isCloseAction ? Colors.black : Colors.yellow",
    "pressedFillColor:\n                            isCloseAction ? Colors.red : Colors.magenta",
    "softGlowHoverOpacity:\n                            isCloseAction ? 0.78 : 0.46",
    "softGlowPressedOpacity:\n                            isCloseAction ? 0.92 : 0.0",
    "selectedDetailActionIndex = index;",
):
    require(tab_action, needle, "dynamic TAB ActionButton fidelity")

assert "id: appTabControlMouse" not in tab_action, (
    "dynamic TAB controls reintroduced private pointer engine"
)
for old_alias in (
    "appTabControlButton.isPressed",
    "appTabControlButton.isHovered",
    "appTabControlButton.isSelected",
):
    assert old_alias not in tab_action, f"TAB control retained old state alias: {old_alias}"

require(
    APPCONTROL,
    "id: tabCloseActionBelowFreeze",
    "dedicated TAB close action remains separate",
)

print("AppControl TAB ActionButton migration: PASS")


# Extracted AppControl action-family proof: Task Manager process actions and
# System Monitor component actions use the shared ActionButton engine without
# absorbing the LIMIT slider, safety lock, or mode/selector controls.
TASK_MANAGER = (ROOT / "widgets/appcontrol/TaskManagerView.qml").read_text(encoding="utf-8")
SYSTEM_MONITOR = (ROOT / "widgets/appcontrol/SystemMonitorView.qml").read_text(encoding="utf-8")

for control_id in ("taskRestartAction", "taskFreezeAction", "taskEndAction"):
    marker = f"id: {control_id}"
    marker_pos = TASK_MANAGER.index(marker)
    block_start = TASK_MANAGER.rfind("ActionButton {", 0, marker_pos)
    assert block_start >= 0, f"{control_id} must inherit ActionButton"
    rectangle_start = TASK_MANAGER.rfind("Rectangle {", 0, marker_pos)
    assert rectangle_start < block_start, f"{control_id} fell back to a private Rectangle"

for private_mouse in (
    "id: taskRestartActionMouse",
    "id: taskFreezeActionMouse",
    "id: taskEndActionMouse",
):
    assert private_mouse not in TASK_MANAGER, f"Task Manager reintroduced private action pointer engine: {private_mouse}"

for needle, message in (
    ("id: taskRestartAction", "restart action remains present"),
    ("property bool canRestart:", "restart availability guard remains"),
    ("property bool canFreeze:", "freeze availability guard remains"),
    ("property bool canEnd:", "end-process availability guard remains"),
    ("dangerActionUnlocked(\n                                   taskManagerBody.currentTask, \"freeze\"", "freeze danger unlock remains"),
    ("dangerActionUnlocked(\n                                   taskManagerBody.currentTask, \"kill\"", "kill danger unlock remains"),
    ("destructive: true", "destructive task actions preserve semantics"),
    ("softGlowMargin: 4", "restart/freeze halo gutter preservation"),
    ("softGlowMargin: 5", "end-process halo gutter preservation"),
    ("id: taskLimitSlider", "LIMIT remains a dedicated continuous control"),
    ("id: taskActionSafetyLockPlate", "safety lock remains a separate toggle family"),
):
    require(TASK_MANAGER, needle, message)

system_marker = SYSTEM_MONITOR.index("id: systemControlActionButton")
system_block = SYSTEM_MONITOR.rfind("ActionButton {", 0, system_marker)
assert system_block >= 0, "system component actions must inherit ActionButton"
assert SYSTEM_MONITOR.rfind("Rectangle {", 0, system_marker) < system_block, (
    "system component actions fell back to a private Rectangle"
)
for needle, message in (
    ("label: modelData.label", "system action label delegation"),
    ("available: canRun", "system action availability"),
    ("isRebootAction ? Colors.red : Colors.yellow", "reboot-specific hover fill"),
    ("onTriggered: {", "system action trigger delegation"),
):
    require(SYSTEM_MONITOR[system_block:system_marker + 2600], needle, message)
assert "id: systemControlMouse" not in SYSTEM_MONITOR, (
    "System Monitor reintroduced a private action pointer engine"
)

print("Extracted AppControl action families: PASS")
