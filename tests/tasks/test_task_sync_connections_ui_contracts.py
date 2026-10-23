#!/usr/bin/env python3
"""TASKS M9a: connection overview is local; GitW remains remote project owner."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SHELL=(ROOT/"shell.qml").read_text(encoding="utf-8")
MENU=(ROOT/"widgets/TasksW.qml").read_text(encoding="utf-8")
PANE=(ROOT/"widgets/tasks/TaskSyncConnectionsPane.qml").read_text(encoding="utf-8")
MAPPING=(ROOT/"widgets/tasks/TaskSyncPreviewPane.qml").read_text(encoding="utf-8")
GITW=(ROOT/"widgets/GitW.qml").read_text(encoding="utf-8")
GITHUB=(ROOT/"services/github/GitHubProjectsService.qml").read_text(encoding="utf-8")
STORE=(ROOT/"services/hub/ApolloHubTodoStore.qml").read_text(encoding="utf-8")

assert MENU.count("TaskSyncConnectionsPane {")==1
assert 'visible: root.menuOpen && root.activeMode.id === "sync"' in MENU
assert 'todoSnapshot: ApolloHubTodoStore.snapshot' in MENU
assert "signal openGithubProjectsRequested()" in MENU
assert "onOpenGithubProjectsRequested: root.openGithubProjectsRequested()" in MENU
assert 'activeMode.id === "sync" ? "PREVIEW"' in MENU
assert 'feedStatus === "LOCAL" || feedStatus === "PREVIEW"' in MENU

assert PANE.count("ModeButton {")==1
assert 'bordered: false' in PANE
for name in ('"overview"', '"mappings"', '"review"', '"history"'):
    assert name in PANE, name
assert 'property string selectedSubmode: "overview"' in PANE
assert "syncConnections.selectedSubmode = modelData.id" in PANE
assert 'visible: syncConnections.selectedSubmode === "overview"' in PANE
assert 'visible: syncConnections.selectedSubmode === "mappings"' in PANE
assert 'visible: syncConnections.selectedSubmode === "review"' in PANE
assert 'visible: syncConnections.selectedSubmode === "history"' in PANE
assert PANE.count("TaskSyncPreviewPane {")==1
assert 'todoSnapshot: syncConnections.todoSnapshot' in PANE
assert 'readonly property var plan: MappingPolicy.preview(todoSnapshot)' in PANE

for exact in (
    'TASKS LINK // NOT ATTACHED', 'SERVICE OWNER // GIT MENU',
    'REMOTE PROJECTS // NOT READ HERE', 'REMOTE LINKS // 0 VERIFIED',
    'WRITE READY // 0', 'NO PULL // NO PUSH // NO AUTO-SYNC',
    'REVIEW // NO COMPARISON', 'HISTORY // NOT CONNECTED',
    'PULL / PUSH // DISABLED', 'OPEN GITHUB PROJECTS',
):
    assert exact in PANE, exact
assert "signal openGithubProjectsRequested()" in PANE
assert "onLeftClicked: syncConnections.openGithubProjectsRequested()" in PANE
assert 'TaskGitHubMappingPolicy.js' in PANE
assert "TaskGitHubMappingPolicy.js" not in SHELL
assert "TaskSyncPreviewPane {" in PANE
assert "GITHUB // MAPPING PREVIEW" in MAPPING

# Existing GitW controls the ONLY service with gh project list.
assert "GitHubProjectsService {" in GITW
assert "function showGithubPage()" in GITW
assert "function showGithubProjects()" in GITW
assert "function refreshProjects()" in GITHUB
assert 'gh project list --owner' in GITHUB
assert SHELL.count("onOpenGithubProjectsRequested: {")==1
segment=SHELL[SHELL.index("onOpenGithubProjectsRequested: {"):]
segment=segment[:segment.index("\n                }")]
for phrase in (
    "tasksWindow.menuOpen = false;",
    "if (!gitWindow.menuOpen)",
    "gitWindow.open();",
    "gitWindow.showGithubPage();",
    "gitWindow.showGithubProjects();",
    'shellRoot.requestControlKeyboard("git", "cross-widget");',
):
    assert phrase in segment,phrase

for source in (MENU,PANE):
    for forbidden in ("GitHubProjectsService {", "FileView {", "Process {",
                      "JsonAdapter {", "gh project ", "Quickshell.execDetached(",
                      "Qt.openUrlExternally(", "fetch(", "XmlHttpRequest"):
        assert forbidden not in source,forbidden
for token in ("GitHubProjectsService {", "Process {", "FileView {"):
    assert token not in SHELL,token
assert STORE.count("FileView {")==1
assert "atomicWrites: true" in STORE
print("TASKS M9a read-only Connections and existing GitW navigation: PASS")
