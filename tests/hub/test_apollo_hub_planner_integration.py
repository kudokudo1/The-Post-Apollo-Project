#!/usr/bin/env python3
"""Phase 3: Hub reuses TASKS' read-only PLANNER without a second writer.

These source checks complement the pure planner policy tests; they do not
certify a running desktop or the TASKS scheduling transaction contract.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
explore = (ROOT / "widgets/hub/ApolloHubTodoExplore.qml").read_text()
parent = (ROOT / "widgets/tasks/TaskPlannerPane.qml").read_text()
schedule = (ROOT / "widgets/tasks/TaskPlannerSchedulePane.qml").read_text()
tile = (ROOT / "widgets/hub/ApolloHubTile.qml").read_text()
store = (ROOT / "services/hub/ApolloHubTodoStore.qml").read_text()
tasks = (ROOT / "widgets/TasksW.qml").read_text()

# H:1 remains compact, while H:2/H:3 share one full multi-tab workspace.
assert 'visible: tile.moduleId === "todo" && tile.tileRowSpan === 1' in tile
assert 'visible: tile.moduleId === "todo" && tile.tileRowSpan > 1' in tile
assert explore.count("TaskPlannerPane {") == 1
assert tasks.count("TaskPlannerPane {") == 1
for token in (
    'readonly property bool plannerMode: selectedView === "planner"',
    'readonly property string plannerStatus:',
    'plannerMode ? plannerStatus',
    'view !== "planner"',
    'label: "LIST"',
    'label: "TODAY"',
    'label: "PLANNER"',
    'label: "DETAILS"',
    'onLeftClicked: todoExplore.chooseView("planner")',
    'function chooseView(view)',
    'detailMode && (taskDetails.pendingWrite || taskDetails.dirty)',
    'function openTask(taskId)',
    'taskDetails.pendingWrite',
    'taskDetails.selectedTaskId !== taskId',
    'taskDetails.chooseTask(taskId)',
    'taskDetails.selectedTask.id !== taskId',
    'onOpenTaskRequested: function(taskId)',
    'todoExplore.openTask(taskId);',
    'id: plannerViewport',
    'visible: todoExplore.plannerMode',
    'contentHeight: taskPlanner.height',
    'boundsBehavior: Flickable.StopAtBounds',
    'height: Math.max(plannerViewport.height, 485)',
    'schedulingAllowed: false',
    'todoStore: null',
    'todoSnapshot: todoExplore.todoSnapshot',
):
    assert token in explore, f"Hub Planner missing {token}"

# The explicit scheduling capability is opt-out ONLY for Hub.
# Standalone TASKS retains its original writer and actions.
for token in (
    'property bool schedulingAllowed: true',
    'onSchedulingAllowedChanged:',
    'onScheduleModeChanged:',
    'if (!schedulingAllowed) scheduleMode = false;',
    'available: planner.schedulingAllowed',
    'if (planner.schedulingAllowed) planner.scheduleMode = true;',
    'visible: planner.scheduleMode && planner.schedulingAllowed',
    'todoStore: planner.schedulingAllowed ? planner.todoStore : null',
    'model: ["MONTH", "WEEK", "DAY", "TODAY"]',
    'model: planner.calendar.agenda',
    'onLeftClicked: planner.openTaskRequested(modelData.id)',
):
    assert token in parent, f"Host-independent TASKS Planner missing {token}"
assert 'todoStore: ApolloHubTodoStore' in tasks
assert 'onOpenTaskRequested: function(taskId)' in tasks
assert 'todoStore.updateTaskDetails(' in schedule
assert 'todoStore.addTask(' in schedule

# No implicit scheduling, file writes, duplicate store, process or poller
# inside the Hub wrapper. The parent pane's existing 60-second local-day
# refresh is permitted only when PLANNER is visible.
for forbidden in (
    "ApolloHubTodoStore {", "FileView {", "Process {", "Timer {",
    "JsonAdapter {", "Qt.openUrlExternally(", "updateTaskDetails(",
    "addTask(", "saveDate(", "createTask(", "TaskPlannerSchedulePane {",
):
    assert forbidden not in explore, f"Hub Planner cannot own {forbidden}"
assert 'Timer {' in parent
assert 'running: planner.visible' in parent
assert store.count("FileView {") == 1

print("ApolloHub Phase 3 TASKS PLANNER read-only integration: PASS")
