#!/usr/bin/env python3
"""PLANNER M4 read-only mode-switching contract; cosmetic polish is deferred."""
from pathlib import Path
root = Path(__file__).resolve().parents[2]
pane = (root / "widgets/tasks/TaskPlannerPane.qml").read_text()
policy = (root / "widgets/tasks/TaskPlannerPolicy.js").read_text()
host = (root / "widgets/TasksW.qml").read_text()
for required in (
    'property string viewMode: "month"',
    'model: ["MONTH", "WEEK", "DAY", "TODAY"]',
    'else planner.viewMode = modelData.toLowerCase();',
    'readonly property var weekRows: Planner.weekDays(todoSnapshot, selectedDate, todayKey)',
    'onLeftClicked: planner.navigate(-1)',
    'onLeftClicked: planner.navigate(1)',
    'planner.viewMode === "day" ? 0',
    'visible: planner.viewMode === "week"',
    'visible: planner.viewMode === "month"',
    'model: planner.calendar.available ? planner.weekRows : []',
    'onClicked: planner.selectDate(weekRow.modelData.date)',
    'onClicked: planner.selectDate(parent.modelData.date)',
    'onLeftClicked: planner.openTaskRequested(modelData.id)',
    'function jumpToday()',
    'function selectDate(dateKey)',
):
    assert required in pane, required
assert "function moveDay(dateKey, delta)" in policy
assert "function weekDays(snapshot, selectedKey, todayKey)" in policy
assert host.count("TaskPlannerPane {") == 1
assert "todoSnapshot: ApolloHubTodoStore.snapshot" in host
for src in (pane, policy):
    for forbidden in ("FileView {", "Process {", "ApolloHubTodoStore",
                      "updateTaskDetails(", "setTaskDone(", "removeTask(",
                      "XmlHttpRequest", "Quickshell.execDetached("):
        assert forbidden not in src, forbidden
print("PLANNER M4 week/day UI and read-only boundaries: PASS")
