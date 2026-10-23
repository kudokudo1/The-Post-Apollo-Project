#!/usr/bin/env python3
"""M6 PROJECTS uses only the existing guarded local task store."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
TASKS=(ROOT/"widgets/TasksW.qml").read_text(encoding="utf-8")
PANE=(ROOT/"widgets/tasks/TaskProjectsPane.qml").read_text(encoding="utf-8")
POLICY=(ROOT/"services/hub/ApolloHubTodoPolicy.js").read_text(encoding="utf-8")
STORE=(ROOT/"services/hub/ApolloHubTodoStore.qml").read_text(encoding="utf-8")

assert TASKS.count("TaskProjectsPane {") == 1
assert 'visible: root.menuOpen && root.activeMode.id === "projects"' in TASKS
assert "todoStore: ApolloHubTodoStore" in TASKS
assert "todoSnapshot: ApolloHubTodoStore.snapshot" in TASKS
assert "taskDetails.chooseTask(taskId)" in TASKS
assert 'root.activeMode.id === "projects"' in TASKS
assert "WlrKeyboardFocus.OnDemand" in TASKS
assert TASKS.count("TaskTodayPane {") == 1
assert TASKS.count("TaskDetailsPane {") == 1
assert TASKS.count("ApolloHubTodoMini {") == 1

for phrase in (
    "function createProject()",
    "function setProject(task)",
    "todoStore.createProject(pendingProjectName)",
    "todoStore.assignTaskProject(task.id, pendingTargetProjectId)",
    "pendingWrite = true",
    'feedback = "SAVING"',
    'feedback = "SAVE FAILED // INPUT KEPT"',
    'feedback = "SAVED"',
    "onTodoSnapshotChanged:",
    "selectedProjectId = found.id",
    "projectsPane.selectedProjectId === modelData.id",
    "pendingTargetProjectId = task.projectId === selectedProjectId",
    "signal openTaskRequested(string taskId)",
    "projectsPane.openTaskRequested(row.modelData.id)",
    'text: "NEW PROJECT NAME"',
    'label: "ASSIGN"',
):
    if phrase == 'label: "ASSIGN"':
        continue # ASSIGN is conditional in QML, tested through source below.
    assert phrase in PANE, phrase
assert '"ASSIGN"' in PANE and '"CLEAR"' in PANE
assert "newProjectInput.focus = false" in PANE
assert "readonly property bool validProjectName:" in PANE
assert "pendingProjectName = newProjectInput.text.trim()" in PANE

assert "function createProject(doc, name, nowMs)" in POLICY
assert "function assignProject(doc, taskId, projectId, nowMs)" in POLICY
assert "version: 3" in POLICY
assert "doc.version !== 1 && doc.version !== 2 && doc.version !== 3" in POLICY
assert "UNKNOWN_PROJECT_REFERENCE" in POLICY
assert "DUPLICATE_PROJECT_NAME" in POLICY
assert "PROJECT_SEQUENCE_REWIND" in POLICY
assert "function createProject(name)" in STORE
assert "function assignTaskProject(taskId, projectId)" in STORE
assert "TodoPolicy.createProject(document, name, Date.now())" in STORE
assert "TodoPolicy.assignProject(document, taskId," in STORE
assert "atomicWrites: true" in STORE
assert "watchChanges: false" in STORE
assert STORE.count("FileView {") == 1
assert STORE.count("todoFile.setText(") == 1

# No remote integration, extra writers, hidden sync, file operations in QML.
for src in (PANE,TASKS):
    for forbidden in ("FileView {", "Process {", "JsonAdapter {",
                      "Quickshell.execDetached(", "XmlHttpRequest"):
        assert forbidden not in src, forbidden
print("TASKS M6 local project UI and single-writer contracts: PASS")
