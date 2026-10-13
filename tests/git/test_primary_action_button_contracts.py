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

# Main panel selectors retain different control types and sizing.
assert "ModeActuator {" in GIT
assert 'label: gitService.pullSourceLabel' in GIT
assert 'component PageTab: Rectangle {' in GIT
assert "id: localTargetSwitchButton" in GIT
assert "id: saveWorkflowButton" in GIT

print("Git main-panel ActionButtons: PASS // seven actions, selectors preserved")
