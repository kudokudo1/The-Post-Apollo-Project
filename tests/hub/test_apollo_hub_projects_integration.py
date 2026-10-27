#!/usr/bin/env python3
"""Phase 3: Hub reuses local TASKS PROJECTS as a read-only view.

Source contracts, not a substitute for a real Quickshell desktop acceptance.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
hub = (ROOT / "widgets/hub/ApolloHubTodoExplore.qml").read_text()
tile = (ROOT / "widgets/hub/ApolloHubTile.qml").read_text()
projects = (ROOT / "widgets/tasks/TaskProjectsPane.qml").read_text()
tasks = (ROOT / "widgets/TasksW.qml").read_text()
store = (ROOT / "services/hub/ApolloHubTodoStore.qml").read_text()

# H:1 stays the compact editor; H:2/H:3 share a mounted expanded view.
assert 'visible: tile.moduleId === "todo" && tile.tileRowSpan === 1' in tile
assert 'visible: tile.moduleId === "todo" && tile.tileRowSpan > 1' in tile
assert hub.count("TaskProjectsPane {") == 1
assert tasks.count("TaskProjectsPane {") == 1
for token in (
    'readonly property bool projectsMode: selectedView === "projects"',
    'readonly property string projectsStatus:',
    'projectsMode ? projectsStatus',
    'view !== "projects"',
    'label: "LIST"', 'label: "TODAY"', 'label: "PLANNER"',
    'label: "PROJECTS"', 'label: "DETAILS"',
    'onLeftClicked: todoExplore.chooseView("projects")',
    'detailMode && (taskDetails.pendingWrite || taskDetails.dirty)',
    'function openTask(taskId)',
    'taskDetails.pendingWrite',
    'taskDetails.selectedTaskId !== taskId',
    'taskDetails.chooseTask(taskId)',
    'taskDetails.selectedTask.id !== taskId',
    'id: projectsViewport',
    'visible: todoExplore.projectsMode',
    'contentHeight: taskProjects.y + taskProjects.height',
    'height: Math.max(projectsViewport.height - y, 520)',
    'text: "LOCAL PROJECTS // READ ONLY IN HUB"',
    'todoSnapshot: todoExplore.todoSnapshot',
    'todoStore: null',
    'onOpenTaskRequested: function(taskId)',
    'todoExplore.openTask(taskId);',
):
    assert token in hub, f"Hub PROJECTS missing {token}"
assert hub.count('width: Math.max(1, (modeSelector.width - 4 * modeSelector.spacing) / 5)') == 5

# Existing pane stays interactive for selection and OPEN; all mutations
# are gated by writable, which is false when Hub supplies no store.
for token in (
    'readonly property bool writable:',
    'todoStore !== null && todoSnapshot && todoSnapshot.writable === true',
    'function chooseProject(projectId)',
    'if (pendingWrite)',
    'if (renameDirty)',
    'function createProject()',
    'if (!writable || !validProjectName) return;',
    'function renameSelectedProject()',
    'if (!writable || !validRename || !selectedProject)',
    'function deleteSelectedProject()',
    'if (!writable || !selectedProject || !confirmDeleteProject) return;',
    'function setProject(task)',
    'if (!writable || !selectedProject || !task) return;',
    'available: projectsPane.writable',
    'available: projectsPane.writable && projectsPane.validRename',
    'available: projectsPane.writable && projectsPane.renameDirty',
    'available: projectsPane.writable && projectsPane.selectedProject !== null',
    'onLeftClicked: projectsPane.openTaskRequested(row.modelData.id)',
    'onTodoSnapshotChanged: reconcilePending()',
):
    assert token in projects, f"PROJECTS owner safety contract missing {token}"

# Standalone TASKS still has the same writer and owner action semantics.
assert 'todoStore: ApolloHubTodoStore' in tasks
assert 'todoSnapshot: ApolloHubTodoStore.snapshot' in tasks
assert 'root.activeMode.id === "projects"' in tasks
assert 'root.selectMainMode(0);' in tasks
assert 'taskDetails.chooseTask(taskId);' in tasks
assert store.count("FileView {") == 1

# Hub wrapper never writes, polls, creates a second store, or bypasses
# the parent pane's guarded operations.
for forbidden in (
    "ApolloHubTodoStore {", "FileView {", "Process {", "Timer {",
    "JsonAdapter {", "Qt.openUrlExternally(", "createProject(",
    "renameProject(", "deleteProject(", "assignTaskProject(",
    "updateTaskDetails(", "setTaskDone(", "removeTask(",
):
    assert forbidden not in hub, f"Hub PROJECTS cannot own {forbidden}"

print("ApolloHub Phase 3 TASKS PROJECTS read-only integration: PASS")
