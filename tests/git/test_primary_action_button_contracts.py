#!/usr/bin/env python3
"""Git main-panel ActionButton migration: roles, ownership, keyboard, semantics."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
GIT = (ROOT / "widgets/GitW.qml").read_text(encoding="utf-8")
SHARED = (ROOT / "components/ActionButton.qml").read_text(encoding="utf-8")

assert "import qs.components as SharedComponents" in GIT
assert "component GitPrimaryAction: SharedComponents.ActionButton {" in GIT
assert "component ActionButton: Rectangle {" in GIT, (
    "keep legacy selector/workflow controls independent of the pilot"
)
assert GIT.count("\n                                GitPrimaryAction {") == 3
assert GIT.count("\n                            GitPrimaryAction {") == 4
assert len(re.findall(r"(?m)^\s*GitPrimaryAction\s*\{", GIT)) == 7
assert "default property alias contentData: contentHost.data" in SHARED

start = GIT.index("component GitPrimaryAction:")
end = GIT.index("component ActionButton: Rectangle {", start)
pilot = GIT[start:end]
for needle in (
    "Component.onCompleted: root.registerGitKeyboardControl(gitAction)",
    "Component.onDestruction: root.unregisterGitKeyboardControl(gitAction)",
    "root.gitKeyboardControl === gitAction",
    'root.gitSelectorSource === "keyboard"',
    'root.gitSelectorSource === "mouse"',
    "onHoverEntered: root.selectGitControlFromMouse(gitAction)",
    "onPointerMoved: root.selectGitControlFromMouse(gitAction)",
    "onClicked: root.selectGitControlFromMouse(gitAction)",
    "available: enabledAction",
    "keyboardSelected: gitKeyboardSelector",
    "selected: selectedAction",
    "property int keyboardRow: -1",
    "scale:",
    "contentItem.clip: true",
    "Accessible.name: label",
    "fontSizeMode: Text.HorizontalFit",
    "minimumPixelSize: 8",
    "contentGlowIdleOpacity: 0.35",
    "contentGlowHoverOpacity: 0.75",
    "contentGlowPressedOpacity: 1.0",
    "softGlowIdleOpacity: 0.25",
    "softGlowHoverOpacity: 0.55",
    "softGlowPressedOpacity: 0.60",
    "wideGlowEnabled: true",
    "wideGlowSpread: 10",
    "wideGlowPressedOpacity: 0.10",
    "unavailableContentOpacity: 0.34",
):
    assert needle in pilot, needle

start = GIT.index('label: "FETCH"')
end = GIT.index("// ===== LOCAL TOOLS", start)
sync = GIT[start:end]
for needle in (
    'onTriggered: gitService.runSyncAction("fetch")',
    'gitService.runSyncAction("pull")',
    'gitService.runSyncAction("clone")',
    'onTriggered: gitService.runSyncAction("push")',
    "gitService.pullSourceTargetValid",
    "gitService.repoIsLocal",
    "gitService.actionBusy",
    "gitService.selectedRemoteBranch",
    'keyboardRow: 0',
):
    assert needle in sync, needle

start = GIT.index('label: "STATUS"')
end = GIT.index("readonly property bool cleanIdle:", start)
local = GIT[start:end]
for needle in (
    'onTriggered: gitService.runReadAction("status")',
    'onTriggered: gitService.runReadAction("diff")',
    'onTriggered: gitService.runReadAction("log")',
    'onTriggered: gitService.launchLazygit()',
    "keyboardRow: 1",
):
    assert needle in local, needle

# Local CONTROL identities are *idle* colors only. Interaction follows the
# shared ActionButton state precedence instead of freezing action colors across
# hover/selection/press. Sampled text glow follows the visible foreground:
# selected/keyboard-selected magenta characters require magenta text glow.
assert "property color actionAccentColor: Colors.cyan" in pilot
assert ": blueAccent ? Colors.blue : actionAccentColor" in pilot

idle = {
    "idleForegroundColor": "semanticAccent",
    "idleBorderColor": "semanticAccent",
    "idleContentGlowColor": "semanticAccent",
    "idleSoftGlowColor": "semanticAccent",
    "idleWideGlowColor": "semanticAccent",
}
for key, value in idle.items():
    assert f"{key}: {value}" in pilot, f"{key} lost its idle identity"

interaction = {
    "hoverFillColor": "Colors.yellow",
    "selectedFillColor": "Colors.yellow",
    "keyboardSelectedFillColor": "Colors.yellow",
    "pressedFillColor": "redAccent ? Colors.red : Colors.magenta",
    "hoverForegroundColor": "Colors.orange",
    "selectedForegroundColor": "Colors.magenta",
    "keyboardSelectedForegroundColor": "Colors.magenta",
    "pressedForegroundColor": "Colors.black",
    "hoverBorderColor": "Colors.orange",
    "selectedBorderColor": "Colors.magenta",
    "keyboardSelectedBorderColor": "Colors.orange",
    "hoverContentGlowColor": "Colors.orange",
    "selectedContentGlowColor": "Colors.magenta",
    "keyboardSelectedContentGlowColor": "Colors.magenta",
    "pressedContentGlowColor": "Colors.magenta",
    "hoverSoftGlowColor": "Colors.orange",
    "selectedSoftGlowColor": "Colors.magenta",
    "keyboardSelectedSoftGlowColor": "Colors.orange",
    "pressedSoftGlowColor": "redAccent ? Colors.red : Colors.magenta",
    "hoverWideGlowColor": "Colors.orange",
    "selectedWideGlowColor": "Colors.magenta",
    "keyboardSelectedWideGlowColor": "Colors.orange",
    "pressedWideGlowColor": "redAccent ? Colors.red : Colors.magenta",
}
for key, value in interaction.items():
    needle = f"{key}: {value}"
    assert needle in pilot, f"Git action state must follow default: {needle}"

for key in (
    "hoverFillColor", "selectedFillColor", "hoverForegroundColor",
    "selectedForegroundColor", "pressedForegroundColor", "hoverBorderColor",
    "selectedBorderColor", "keyboardSelectedBorderColor",
):
    assert interaction[key] in SHARED, (
        f"Unexpected shared ActionButton state contract for {key}"
    )

# State precedence and external ownership stay in the shared component.
for token in (
    "readonly property color fillColor:",
    "readonly property color foregroundColor:",
    "readonly property color contentGlowColor:",
    "pressed",
    "keyboardSelected",
    "selected",
    "hovered",
):
    assert token in SHARED, f"Missing shared state machinery: {token}"

# Each action owns its identity. The remote-only CLONE retains its existing
# blue exception; the local PULL and even disabled PUSH use magenta.
action_starts = list(re.finditer(r"(?m)^( +)GitPrimaryAction \{", GIT))
assert len(action_starts) == 7, "Expected seven local Git primary actions"
action_blocks = []
for match in action_starts:
    indent = match.group(1)
    close = re.search(r"(?m)^" + re.escape(indent) + r"\}", GIT[match.end():])
    assert close, "Unclosed GitPrimaryAction instance"
    action_blocks.append(GIT[match.start():match.end() + close.end()])


def action_by_handler(handler: str) -> str:
    found = [block for block in action_blocks if handler in block]
    assert len(found) == 1, f"Expected unique local Git action: {handler}"
    return found[0]


assigned = {
    'runSyncAction("fetch")': None,
    'runSyncAction("pull")': "magenta",
    'runSyncAction("push")': "magenta",
    'runReadAction("status")': None,
    'runReadAction("diff")': "blue",
    'runReadAction("log")': "green",
    "launchLazygit()": "yellow",
}
for handler, color in assigned.items():
    block = action_by_handler(handler)
    if color is None:
        assert "actionAccentColor:" not in block, f"{handler} must inherit cyan"
    else:
        assert f"actionAccentColor: Colors.{color}" in block, (
            f"{handler} must use {color} icon/text/glow identity"
        )
assert "blueAccent: !gitService.repoIsLocal" in action_by_handler(
    'runSyncAction("pull")'
), "Preserve the separate remote-only CLONE blue identity"
assert "blueAccent:" not in action_by_handler('runSyncAction("push")'), (
    "PUSH must remain magenta, including while unavailable"
)

# Main panel selectors retain different control types and sizing.
assert "ModeActuator {" in GIT
assert 'label: gitService.pullSourceLabel' in GIT
assert 'component PageTab: Rectangle {' in GIT
assert "id: localTargetSwitchButton" in GIT
assert "id: saveWorkflowButton" in GIT

print("Git main-panel ActionButtons: PASS // seven actions, selectors preserved")
