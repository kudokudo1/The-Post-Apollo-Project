#!/usr/bin/env python3
"""TASKS M4 detail UI and single-writer, no accidental migration contracts."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
TASKS=(ROOT/"widgets/TasksW.qml").read_text(encoding="utf-8")
DETAILS=(ROOT/"widgets/tasks/TaskDetailsPane.qml").read_text(encoding="utf-8")
HUB=(ROOT/"widgets/ApolloHubW.qml").read_text(encoding="utf-8")
MINI=(ROOT/"widgets/hub/ApolloHubTodoMini.qml").read_text(encoding="utf-8")
STORE=(ROOT/"services/hub/ApolloHubTodoStore.qml").read_text(encoding="utf-8")
POLICY=(ROOT/"services/hub/ApolloHubTodoPolicy.js").read_text(encoding="utf-8")

assert 'import "tasks"' in TASKS
assert TASKS.count("TaskDetailsPane {") == 1
assert TASKS.count("ApolloHubTodoMini {") == 1
assert "onTaskSelected: function(taskId)" in TASKS
assert "taskDetails.chooseTask(taskId)" in TASKS
assert TASKS.count("todoStore: ApolloHubTodoStore") == 2
assert TASKS.count("todoSnapshot: ApolloHubTodoStore.snapshot") == 2
assert "todoStore: ApolloHubTodoStore" in HUB
assert "todoSnapshot: ApolloHubTodoStore.snapshot" in HUB
assert "signal taskSelected(string taskId)" in MINI
assert "TapHandler {" in MINI
assert "todoMini.taskSelected(String(todoEntry.modelData.id))" in MINI
assert "onVisibleChanged:" in DETAILS
assert "dueDateInput.focus = false;" in DETAILS
assert "descriptionInput.focus = false;" in DETAILS

# Never drop unsaved detail drafts on switching tasks, and never claim a
# disk write succeeded until the store snapshot confirms its contents.
for required in (
    "SAVE OR DISCARD FIRST", "SAVE FAILED // DRAFT KEPT", "SAVE PENDING",
    "TASK REMOVED", "DRAFT DISCARDED", "UNSAVED", "SAVED",
    "onTodoSnapshotChanged:", "selectedTask.priority === pendingPriority",
    "selectedTask.description === pendingDescription",
    "selectedTask.dueDate === pendingDueDate",
    "details.resetDraft()", "details.saveDetails()",
    "todoStore.updateTaskDetails(selectedTaskId, pendingPriority,",
    "readonly property bool fieldsValid:", "readonly property bool dirty:",
    'readonly property var priorities: ["none", "low", "medium", "high", "urgent"]',
    'text: "DESCRIPTION // PLAIN TEXT"', 'text: "YYYY-MM-DD"',
):
    assert required in DETAILS, required

assert "function updateTaskDetails(id, priority, description, dueDate)" in STORE
assert "TodoPolicy.updateDetails(document, id, priority," in STORE
assert "function updateDetails(doc, id, priority, description, dueDate, nowMs)" in POLICY
assert "var MAX_DESCRIPTION = 2000;" in POLICY
assert "var MAX_FILE_LENGTH = 1048576;" in POLICY
assert "return {version: 2, nextId: 1, tasks: []};" in POLICY
assert "doc.version !== 1 && doc.version !== 2" in POLICY
assert "if (!result.ok) {" in STORE
assert "todoFile.setText(JSON.stringify(pendingDocument, null, 2)" in STORE
assert "atomicWrites: true" in STORE
assert "watchChanges: false" in STORE
assert STORE.count("FileView {") == 1

# Not yet an external sync, no new separate disk writer, no shortcuts stealing typing.
for src in (TASKS, DETAILS, MINI):
    for token in ("FileView {", "Process {", "JsonAdapter {", "Quickshell.execDetached(", "HttpClient"):
        assert token not in src, token
assert 'focusable: root.menuOpen && root.activeMode.id === "tasks"' in TASKS

print("TASKS M4 UI/single-writer contracts: PASS")
