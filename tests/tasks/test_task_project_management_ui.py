#!/usr/bin/env python3
"""M7 project rename/delete through the same single guarded checklist writer."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PANE=(ROOT/"widgets/tasks/TaskProjectsPane.qml").read_text(encoding="utf-8")
POLICY=(ROOT/"services/hub/ApolloHubTodoPolicy.js").read_text(encoding="utf-8")
ACK=(ROOT/"widgets/tasks/TaskProjectsAck.js").read_text(encoding="utf-8")
STORE=(ROOT/"services/hub/ApolloHubTodoStore.qml").read_text(encoding="utf-8")

for phrase in (
    "function renameSelectedProject()",
    "function discardRename()",
    "function deleteSelectedProject()",
    "function chooseProject(projectId)",
    "SAVE OR RESET RENAME FIRST",
    "DELETE PROJECT? TASKS KEPT",
    "TASKS BECOME UNASSIGNED",
    "PROJECT REMOVED // TASKS UNASSIGNED",
    "DELETE CANCELED",
    "SAVE FAILED // INPUT KEPT",
    "SAVING",
    "RENAME REJECTED",
    "DELETE REJECTED",
    "pendingWrite = true",
    "pendingTaskTotal = tasks.length",
    "ProjectAck.status(",
    "onStoreStateChanged: reconcilePending()",
    'feedback = "SAVE NOT VERIFIED // INPUT KEPT"',
    "const snap = todoSnapshot;",
    "const rawProjects = Array.isArray(snap.projects)",
    "const wasDelete = pendingKind === \"delete\";",
    "onTodoSnapshotChanged: reconcilePending()",
    "pendingProjectId = selectedProjectId",
    "todoStore.renameProject(pendingProjectId, pendingProjectName)",
    "todoStore.deleteProject(pendingProjectId, true)",
    "renameInput.text = found.name;",
    'label: "RENAME"',
    'label: "RESET"',
    'label: projectsPane.confirmDeleteProject ? "YES" : "DEL PROJECT"',
    'label: "NO"',
    "destructive: true",
    "onVisibleChanged:",
    "renameInput.focus = false",
):
    assert phrase in PANE, phrase

assert 'import "TaskProjectsAck.js" as ProjectAck' in PANE
assert "function status(snapshot, kind, projectId, projectName, taskId," in ACK
assert "snapshot.state === \"saving\"" in ACK
assert 'return "unconfirmed"' in ACK
assert 'return "confirmed"' in ACK
assert 'return "failed"' in ACK
assert "tasks.length !== expectedTaskCount" in ACK
assert "ProjectAck.status(" in PANE
assert "onStoreStateChanged: reconcilePending()" in PANE
assert "if (!writable || !selectedProject || !confirmDeleteProject) return;" in PANE
assert 'feedback = "DELETE CANCELED"' in PANE
assert "onLeftClicked: projectsPane.chooseProject(modelData.id)" in PANE
assert "if (renameDirty)" in PANE
assert "function renameProject(doc, projectId, name, nowMs)" in POLICY
assert "function deleteProject(doc, projectId, nowMs, confirmed)" in POLICY
assert "if (confirmed !== true)" in POLICY
assert "next.projects.splice(index, 1)" in POLICY
assert "next.tasks[j].projectId = null;" in POLICY
assert "next.tasks[j].updatedAtMs = nowMs;" in POLICY
assert "function renameProject(projectId, name)" in STORE
assert "function deleteProject(projectId, confirmed)" in STORE
assert "TodoPolicy.renameProject(document, projectId," in STORE
assert "TodoPolicy.deleteProject(document, projectId," in STORE
assert STORE.count("FileView {") == 1
assert STORE.count("todoFile.setText(") == 1
assert "atomicWrites: true" in STORE
assert "watchChanges: false" in STORE
# Projects mode must not smuggle in a second writer or remote connection.
for forbidden in ("FileView {", "Process {", "JsonAdapter {",
                  "XmlHttpRequest", "Quickshell.execDetached("):
    assert forbidden not in PANE, forbidden
print("TASKS M7 project rename/delete source safety: PASS")
