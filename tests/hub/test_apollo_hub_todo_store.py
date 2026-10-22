#!/usr/bin/env python3
"""B7 To-do local persistence and no-background-write source contracts."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
store = (ROOT/"services/hub/ApolloHubTodoStore.qml").read_text(encoding="utf-8")
policy = (ROOT/"services/hub/ApolloHubTodoPolicy.js").read_text(encoding="utf-8")
layout_store = (ROOT/"services/hub/ApolloHubStore.qml").read_text(encoding="utf-8")
module = (ROOT/"services/hub/qmldir").read_text(encoding="utf-8")
shell = (ROOT/"shell.qml").read_text(encoding="utf-8")
layout = (ROOT/"services/hub/ApolloHubLayout.js").read_text(encoding="utf-8")
workflow = (ROOT/".github/workflows/apollo-hub-todo.yml").read_text(encoding="utf-8")

for needle in (
    "pragma Singleton", "import Quickshell.Io",
    'import "ApolloHubTodoPolicy.js" as TodoPolicy',
    'Quickshell.dataDir + "/apollo-hub-todo-v1.json"',
    'property string storageState: "loading"',
    "property var document: TodoPolicy.emptyDocument()",
    "property var pendingDocument: null",
    "readonly property var snapshot:",
    "TodoPolicy.view(storageState, document, errorCode)",
    "function acceptLoaded(raw)", "function reloadFromDisk()",
    "function stage(result)", "function addTask(title)",
    "function setTaskDone(id, done)", "function renameTask(id, title)",
    "function removeTask(id, confirmed)",
    "if (storageState !== \"ready\" && storageState !== \"empty\")",
    "pendingDocument = result.document",
    'storageState = "saving"',
    "todoFile.setText(JSON.stringify(pendingDocument, null, 2)",
    "onSaved:", "onSaveFailed: function(error)",
    'todo.errorCode = "FILE_SAVE_FAILED"',
    "onLoaded: todo.acceptLoaded(todoFile.text())",
    "onLoadFailed: function(error)",
    "error === FileViewError.FileNotFound",
    "if (todo.storageState === \"saving\")",
    "atomicWrites: true", "blockWrites: false", "watchChanges: false",
    "readonly property string storagePath:",
):
    assert needle in store, f"Missing B7 store safety contract: {needle}"

for needle in (
    ".pragma library", "function emptyDocument(", "function validate(",
    "function parse(", "function create(", "function update(",
    "function view(", "MAX_TASKS = 200", "MAX_TITLE = 160",
    '"UNSUPPORTED_VERSION"', '"INVALID_JSON"', '"DUPLICATE_ID"',
    '"SEQUENCE_REWIND"', '"CONFIRM_REQUIRED"', '"NO_CHANGE"',
):
    assert needle in policy, f"Missing B7 policy: {needle}"

assert "singleton ApolloHubTodoStore 1.0 ApolloHubTodoStore.qml" in module
assert "ApolloHubTodoStore" not in shell
assert "ApolloHubTodoStore" not in layout_store
assert "appcontrol-favorites.json" not in store
assert "apollo-hub-layout.json" not in store
assert "{ module: \"todo\", size: \"half\" }" in layout
assert store.count("FileView {") == 1
assert store.count("todoFile.setText(") == 1
# No automation, AppControl process actions, remote/task sync, or shell mutation.
for forbidden in (
    "Process {", "Quickshell.execDetached(", "SystemTelemetry {",
    "Connections {", "Timer {", "HttpClient", "XmlHttpRequest",
    "fetch(", "execute(", "run(", "FileView {",
    "writeAdapter(", "HospitalAssignment",
):
    assert forbidden not in policy, f"Forbidden B7 policy side effect: {forbidden}"
assert "onAdapterUpdated:" not in store
assert "onFileChanged:" not in store
for forbidden in ("Process {", "Timer {", "Quickshell.execDetached(",
                  "Qt.openUrlExternally(", "play(", "notify("):
    assert forbidden not in store, f"Forbidden B7 To-do store side effect: {forbidden}"

for needle in (
    '"services/hub/ApolloHubTodoPolicy.js"',
    '"services/hub/ApolloHubTodoStore.qml"',
    '"services/hub/qmldir"',
    '"tests/hub/test_apollo_hub_todo_policy.cjs"',
    '"tests/hub/test_apollo_hub_todo_store.py"',
    "node tests/hub/test_apollo_hub_todo_policy.cjs",
    "python3 tests/hub/test_apollo_hub_todo_store.py",
):
    assert needle in workflow, f"Missing B7 CI: {needle}"

print("ApolloHub B7 local To-do single-writer store source contracts passed")
