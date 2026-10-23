#!/usr/bin/env python3
"""The new SYNC preview must remain a local-only, read-only mapping boundary."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
MENU=(ROOT/"widgets/TasksW.qml").read_text(encoding="utf-8")
PANE=(ROOT/"widgets/tasks/TaskSyncPreviewPane.qml").read_text(encoding="utf-8")
WRAPPER=(ROOT/"widgets/tasks/TaskSyncConnectionsPane.qml").read_text(encoding="utf-8")
POLICY=(ROOT/"widgets/tasks/TaskGitHubMappingPolicy.js").read_text(encoding="utf-8")
GITHUB=(ROOT/"services/github/GitHubProjectsService.qml").read_text(encoding="utf-8")
STORE=(ROOT/"services/hub/ApolloHubTodoStore.qml").read_text(encoding="utf-8")

assert MENU.count("TaskSyncConnectionsPane {")==1
assert WRAPPER.count("TaskSyncPreviewPane {")==1
assert 'visible: root.menuOpen && root.activeMode.id === "sync"' in MENU
assert 'visible: syncConnections.selectedSubmode === "mappings"' in WRAPPER
assert 'todoSnapshot: ApolloHubTodoStore.snapshot' in MENU
assert '&& root.activeMode.id !== "sync"' in MENU
assert 'import "TaskGitHubMappingPolicy.js" as MappingPolicy' in PANE
assert 'MappingPolicy.preview(todoSnapshot)' in PANE
for phrase in ('GITHUB // MAPPING PREVIEW', 'LOCAL ONLY // NO REMOTE ACTIONS',
               'REMOTE LINKS // 0 VERIFIED', 'WRITE READY // ',
               'FIELD REQUIREMENTS', 'LOCAL INVENTORY // NO UPLOAD',
               'REMOTE PROJECT ID', 'REMOTE ITEM ID',
               'Title matches are NOT identity matches'):
    assert phrase in PANE,phrase

for phrase in ('NEEDS_VERIFIED_REMOTE_PROJECT_ID',
               'NEEDS_VERIFIED_REMOTE_ITEM_ID',
               'NEEDS_FIELD_AND_OPTION_IDS', 'NEEDS_DATE_FIELD_ID',
               'NEEDS_EXPLICIT_STATUS_SEMANTICS',
               'NEEDS_CONTENT_TYPE_AND_ID', 'writeReady:0'):
    assert phrase in POLICY,phrase
assert 'function preview(snapshot)' in POLICY
assert 'snapshot.projects.forEach' in POLICY
assert 'snapshot.items.forEach' in POLICY
assert 't.description.length > 0' in POLICY
assert 'title:t.title' in POLICY
assert "description: t.description" not in POLICY

# Git owns the only existing GitHubProjectsService. SYNC only illustrates
# requirements and must not activate it, call gh, or allocate another writer.
assert "function refreshProjects()" in GITHUB
for src in (PANE,POLICY):
    for forbidden in ("FileView {", "Process {", "JsonAdapter {",
                      "XmlHttpRequest", "Qt.openUrlExternally(",
                      "Quickshell.execDetached(", "refreshProjects(",
                      "setItemStatus(", "editItemField(", "assignTaskProject(",
                      "createProject(", "deleteProject(",
                      "GitHubProjectsService {", "ApolloHubTodoStore {"):
        assert forbidden not in src,forbidden
for forbidden in ("GitHubProjectsService {", "FileView {", "Process {",
                  "Quickshell.execDetached("):
    assert forbidden not in MENU,forbidden
assert STORE.count("FileView {")==1
assert 'atomicWrites: true' in STORE
print("TASKS SYNC read-only GitHub mapping preview contracts: PASS")
