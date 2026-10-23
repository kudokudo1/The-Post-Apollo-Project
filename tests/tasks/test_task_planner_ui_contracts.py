#!/usr/bin/env python3
"""PLANNER M1 remains read-only and independent of central store and host."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
pane=(root/"widgets/tasks/TaskPlannerPane.qml").read_text()
policy=(root/"widgets/tasks/TaskPlannerPolicy.js").read_text()
host=(root/"widgets/TasksW.qml").read_text()
assert 'property var todoSnapshot: null' in pane
assert 'signal openTaskRequested(string taskId)' in pane
assert 'Planner.view(todoSnapshot, monthKey, selectedDate, todayKey)' in pane
assert 'Grid {' in pane and 'ListView {' in pane
assert 'onLeftClicked: planner.openTaskRequested(modelData.id)' in pane
assert 'function view(snapshot, monthKey, selectedKey, todayKey)' in policy
assert 'days.push(' in policy and 'agenda=agenda.slice().sort(' in policy
assert 'TaskPlannerPane {' not in host, "M1 must not edit shared host"
for text in (pane,policy):
    for forbidden in ('FileView {','Process {','XmlHttpRequest','setTaskDone(',
                      'removeTask(','renameTask(','addTask(','ApolloHubTodoStore'):
        assert forbidden not in text, forbidden
print("PLANNER M1 isolated read-only source contracts: PASS")
