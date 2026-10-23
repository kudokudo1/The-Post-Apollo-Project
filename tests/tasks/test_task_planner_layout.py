#!/usr/bin/env python3
"""PLANNER M2 layout guards, isolated from central storage and task host."""
from pathlib import Path
root = Path(__file__).resolve().parents[2]
pane = (root / "widgets/tasks/TaskPlannerPane.qml").read_text()
assert '["MO", "TU", "WE", "TH", "FR", "SA", "SU"]' in pane
assert "Math.min(237, Math.max(150, planner.height * 0.38))" in pane
assert "(calendarArea.height - weekdays.height - 10) / 6" in pane
assert "anchors.top: agendaTitle.bottom" in pane
assert "anchors.bottom: parent.bottom" in pane
assert "boundsBehavior: Flickable.StopAtBounds" in pane
for forbidden in ("FileView {", "Process {", "ApolloHubTodoStore", "XmlHttpRequest"):
    assert forbidden not in pane
print("PLANNER M2 layout source guards: PASS")
