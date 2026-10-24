#!/usr/bin/env python3
"""M10r source-level API parity and explicit-use QML rehearsal safety gates.

The test NEVER invokes Quickshell, creates a database, starts a process, or
claims production write authority.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
legacy = (ROOT/"services/hub/ApolloHubTodoStore.qml").read_text()
sqlite = (ROOT/"services/projects/ExperimentalTaskSqliteRecordsV2.py").read_text()
bridge = (ROOT/"services/projects/TaskSqliteAdmissionRehearsal.qml").read_text()
harness = (ROOT/"tests/tasks/fixtures/TaskSqliteAdmissionHarness.qml").read_text()
doc = (ROOT/"docs/tasks-sqlite-quickshell-inventory-m10r.md").read_text()
shell = (ROOT/"shell.qml").read_text()
host = (ROOT/"widgets/TasksW.qml").read_text()

legacy_ops = (
    "addTask", "setTaskDone", "renameTask", "updateTaskDetails",
    "createProject", "assignTaskProject", "renameProject",
    "deleteProject", "removeTask", "reloadFromDisk",
)
for name in legacy_ops:
    assert f"function {name}(" in legacy, name
    assert f"`{name}(" in doc, name
assert legacy.count("FileView {") == 1

sqlite_public = ("initialize", "read", "edit_task", "transition_local_operation")
for name in sqlite_public:
    assert f"def {name}(" in sqlite, name
for absent in ("add_task", "delete_task", "create_project", "rename_project",
               "delete_project", "assign_project", "update_task_details"):
    assert f"def {absent}(" not in sqlite, absent
assert 'FIELDS = ("title", "done", "priority", "description", "dueDate")' in sqlite
assert "SQLite" in doc and "MISSING" in doc and "PARTIAL" in doc
assert "JSON remains the sole live writer" in doc

assert 'import "../../../services/projects"' in harness
assert "Scope {" in harness and "PanelWindow {" in harness
assert harness.count("TaskSqliteAdmissionRehearsal {") == 1
assert 'property string fixturePath: ""' in harness
assert 'property string writerId: ""' in harness
assert 'readonly property bool liveStorageAuthorized: false' in harness
assert 'readonly property bool migrationAuthorized: false' in harness
assert 'readonly property bool remoteSyncAuthorized: false' in harness
for method in ("beginRehearsal()", "inspectFixture()", "simulateStage(",
               "simulateFreeze()", "simulateSaveCallback(", "stopRehearsal()"):
    assert method in harness, method
for method in ("FileView {", "Process {", "ApolloHubTodoStore",
               "Component.onCompleted:", "Timer {", "tasks.db",
               "createProject(", "addTask(", "updateTaskDetails("):
    assert method not in harness, method
for src in (shell, host, legacy):
    assert "TaskSqliteAdmissionHarness" not in src
    assert "TaskSqliteAdmissionRehearsal" not in src
assert 'readonly property bool sqliteWriteAuthorized: false' in bridge
assert 'readonly property bool liveChangePerformed: false' in bridge
assert '"--bootstrap-fixture"' not in bridge
assert "handoff-test" in bridge
print("M10r disposable QML controls + complete legacy writer API inventory: PASS")
