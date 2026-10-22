#!/usr/bin/env python3
"""B8 Notes backend: isolated single-writer, revision checks, no autosave."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
store=(ROOT/"services/hub/ApolloHubNotesStore.qml").read_text()
policy=(ROOT/"services/hub/ApolloHubNotesPolicy.js").read_text()
qmdir=(ROOT/"services/hub/qmldir").read_text()
layout=(ROOT/"services/hub/ApolloHubLayout.js").read_text()
shell=(ROOT/"shell.qml").read_text()
todo=(ROOT/"services/hub/ApolloHubTodoStore.qml").read_text()
workflow=(ROOT/".github/workflows/apollo-hub-notes.yml").read_text()

for needle in (
    "pragma Singleton", "import Quickshell.Io",
    'import "ApolloHubNotesPolicy.js" as NotesPolicy',
    'Quickshell.dataDir + "/apollo-hub-notes-v1.json"',
    'property string storageState: "loading"',
    "property var document: NotesPolicy.emptyDocument()",
    "property var pendingDocument: null",
    "readonly property var snapshot:",
    "NotesPolicy.displayList(storageState,document,errorCode)",
    "function getNote(id)", "function acceptLoaded(raw)",
    "function reloadFromDisk()", "function stage(result)",
    "function createNote(title, body)",
    "function saveNote(id, expectedRevision, title, body)",
    "function deleteNote(id, expectedRevision, confirmed)",
    "NotesPolicy.update(", "NotesPolicy.remove(",
    'storageState="saving"', "onSaved:", "onSaveFailed: function(error)",
    'notes.errorCode="FILE_SAVE_FAILED"',
    "onLoaded: notes.acceptLoaded(notesFile.text())",
    "onLoadFailed: function(error)", "FileViewError.FileNotFound",
    'if (notes.storageState === "saving")',
    "atomicWrites: true", "blockWrites: false", "watchChanges: false",
    "notesFile.setText(JSON.stringify(pendingDocument,null,2)",
):
    assert needle in store, "Missing Notes persistence contract: "+needle

for needle in (
    ".pragma library", "function validate(", "function parse(",
    "function create(", "function update(", "function remove(",
    "function displayList(", "function detail(",
    "MAX_NOTES = 100", "MAX_TITLE_LENGTH = 120",
    "MAX_BODY_LENGTH = 8192", '"UNSUPPORTED_VERSION"',
    '"INVALID_JSON"', '"DUPLICATE_ID"', '"SEQUENCE_REWIND"',
    '"STALE_REVISION"', '"CONFIRM_REQUIRED"',
    "current.revision+1", "updatedAtMs:",
):
    assert needle in policy, "Missing Notes model contract: "+needle

assert "singleton ApolloHubNotesStore 1.0 ApolloHubNotesStore.qml" in qmdir
assert "ApolloHubNotesStore" not in shell
assert "ApolloHubNotesStore" not in todo
assert "apollo-hub-notes-v1.json" not in todo
assert 'apollo-hub-todo-v1.json' not in store
assert "ApolloHubNotesStore" not in layout
assert 'module: "notes"' in layout
assert store.count("FileView {")==1
assert store.count("notesFile.setText(")==1
assert store.count("onSaved:")==1
assert "onAdapterUpdated:" not in store
assert "onFileChanged:" not in store

for forbidden in (
    "Process {", "Timer {", "Quickshell.execDetached(", "SystemTelemetry {",
    "Connections {", "onTextChanged:", "writeAdapter(",
    "Qt.openUrlExternally(", ".execute(", ".launch(",
):
    assert forbidden not in store+policy, "Notes unexpectedly runs actions: "+forbidden

for needle in (
    '"services/hub/ApolloHubNotesPolicy.js"',
    '"services/hub/ApolloHubNotesStore.qml"',
    '"services/hub/qmldir"',
    '"tests/hub/test_apollo_hub_notes_policy.cjs"',
    '"tests/hub/test_apollo_hub_notes_store.py"',
    'node tests/hub/test_apollo_hub_notes_policy.cjs',
    'python3 tests/hub/test_apollo_hub_notes_store.py',
):
    assert needle in workflow, "Missing CI registration: "+needle
print("ApolloHub B8 local Notes singleton and no-autosave source contracts passed")
