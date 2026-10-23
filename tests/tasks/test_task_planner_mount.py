#!/usr/bin/env python3
"""M3 host wiring must remain a minimal read-only presentation change."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
host = (root / "widgets/TasksW.qml").read_text()
start = host.index("            TaskPlannerPane {")
end = host.index("            // M9a SYNC Overview", start)
mount = host[start:end]
assert host.count("TaskPlannerPane {") == 1
assert 'visible: root.menuOpen && root.activeMode.id === "planner"' in mount
assert "todoSnapshot: ApolloHubTodoStore.snapshot" in mount
assert "onOpenTaskRequested: function(taskId)" in mount
assert "root.selectMainMode(0);" in mount
assert "taskDetails.chooseTask(taskId);" in mount
assert '&& activeMode.id !== "planner" ? "NO FEED"' in host
assert '&& root.activeMode.id !== "planner"' in host
for prohibited in ("FileView {", "Process {", "updateTask", "createTask",
                   "removeTask", "save", "sync", "push", "pull"):
    assert prohibited not in mount, prohibited
print("PLANNER M3 live read-only host mount: PASS")
