#!/usr/bin/env python3
"""M2 static boundary and isolated harness behavior contracts."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
h=(root/"tests/fixtures/TaskPlannerPreview.qml").read_text()
p=(root/"widgets/tasks/TaskPlannerPane.qml").read_text()
host=(root/"widgets/TasksW.qml").read_text()
assert 'import "../../widgets/tasks"' in h
assert 'TaskPlannerPane {' in h
assert 'todoSnapshot: preview.demoSnapshot' in h
assert 'onOpenTaskRequested: function(taskId)' in h
assert 'id:"t3"' in h and 'dueDate:null' in h
assert 'FileView {' not in h and 'Process {' not in h
assert 'ApolloHubTodoStore' not in h
assert 'TaskPlannerPane {' not in host
assert 'anchors.bottom: parent.bottom' in p
assert 'boundsBehavior: Flickable.StopAtBounds' in p
print("PLANNER M2 isolated preview contracts: PASS")
