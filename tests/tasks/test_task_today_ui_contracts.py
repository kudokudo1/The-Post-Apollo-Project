#!/usr/bin/env python3
"""M5 TODAY is an on-demand local due-date view of the one existing store."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TASKS = (ROOT / "widgets/TasksW.qml").read_text(encoding="utf-8")
PANE = (ROOT / "widgets/tasks/TaskTodayPane.qml").read_text(encoding="utf-8")
POLICY = (ROOT / "widgets/tasks/TaskTodayPolicy.js").read_text(encoding="utf-8")
STORE = (ROOT / "services/hub/ApolloHubTodoStore.qml").read_text(encoding="utf-8")

assert TASKS.count("TaskTodayPane {") == 1
assert "visible: root.menuOpen && root.activeMode.id === \"today\"" in TASKS
assert 'visible: root.activeMode.id !== "tasks" && root.activeMode.id !== "today"' in TASKS
assert '&& root.activeMode.id !== "projects"' in TASKS
assert "todoSnapshot: ApolloHubTodoStore.snapshot" in TASKS
assert "onOpenTaskRequested: function(taskId)" in TASKS
assert "root.selectMainMode(0);" in TASKS
assert "taskDetails.chooseTask(taskId);" in TASKS
assert 'activeMode.id !== "tasks" && activeMode.id !== "today"' in TASKS
assert '&& activeMode.id !== "projects"' in TASKS
assert '&& activeMode.id !== "planner" ? "NO FEED"' in TASKS

assert 'import "TaskDateSegments.js" as DateSegments' in PANE
assert 'import "TaskTodayPolicy.js" as TodayPolicy' in PANE
assert "TodayPolicy.view(todoSnapshot, todayKey)" in PANE
assert "DateSegments.format({" in PANE
assert "now.getFullYear()" in PANE
assert "now.getMonth() + 1" in PANE
assert "now.getDate()" in PANE
assert "onVisibleChanged:" in PANE
assert "if (visible) refreshToday();" in PANE
assert "Timer {" in PANE
assert "interval: 60000" in PANE
assert "running: todayPane.visible" in PANE
assert "onTriggered: todayPane.refreshToday()" in PANE
assert "signal openTaskRequested(string taskId)" in PANE
assert "todayPane.openTaskRequested(rowItem.modelData.id)" in PANE
assert "ListView {" in PANE
assert "boundsBehavior: Flickable.StopAtBounds" in PANE
assert "NO OVERDUE OR DUE-TODAY TASKS" in PANE
assert "DONE (DUE TODAY)" in PANE
assert "UNSCHEDULED" not in PANE

assert "function view(snapshot, today)" in POLICY
assert 'addSection("OVERDUE"' in POLICY
assert 'addSection("DUE TODAY"' in POLICY
assert 'addSection("DONE // DUE TODAY"' in POLICY
assert 'item.dueDate === today && item.done' in POLICY
assert 'item.dueDate < today && !item.done' in POLICY
assert "completedAtMs" not in POLICY and "finishedAt" not in POLICY

# No second FileView, no GitHub or Obsidian sync, no task mutation from TODAY.
assert STORE.count("FileView {") == 1
for src in (TASKS, PANE, POLICY):
    for forbidden in ("FileView {", "Process {", "JsonAdapter {",
                      "Quickshell.execDetached(", "XmlHttpRequest",
                      "setTaskDone(", "renameTask(", "removeTask("):
        assert forbidden not in src, forbidden
print("TASKS M5 TODAY view and single-store source contracts: PASS")
