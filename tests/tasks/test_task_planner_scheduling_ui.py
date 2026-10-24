#!/usr/bin/env python3
"""M5a planner scheduling uses only existing guarded Hub task writer."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
host=(root/"widgets/TasksW.qml").read_text()
planner=(root/"widgets/tasks/TaskPlannerPane.qml").read_text()
schedule=(root/"widgets/tasks/TaskPlannerSchedulePane.qml").read_text()
policy=(root/"widgets/tasks/TaskPlannerSchedulingPolicy.js").read_text()
store=(root/"services/hub/ApolloHubTodoStore.qml").read_text()

assert host.count("TaskPlannerPane {")==1
assert host.count("todoStore: ApolloHubTodoStore")==4
mount=host.split("            TaskPlannerPane {",1)[1].split("\n            }",1)[0]
assert "todoStore: ApolloHubTodoStore" in mount
assert "todoSnapshot: ApolloHubTodoStore.snapshot" in mount
assert '|| root.activeMode.id === "planner")' in host
assert "property var todoStore: null" in planner
assert "property bool scheduleMode: false" in planner
assert 'label: "SCHEDULE"' in planner
assert "TaskPlannerSchedulePane {" in planner
assert "todoStore: planner.todoStore" in planner
assert "visible: !planner.scheduleMode" in planner
assert "visible: planner.scheduleMode" in planner

for required in (
    'import "TaskPlannerSchedulingPolicy.js" as SchedulePolicy',
    "schedule.writable && schedule.selectedProposal.ok",
    "function chooseTask(task)",
    "function createTask()",
    "function saveDate()",
    "function cancelDraft()",
    "schedule.clearTarget = true",
    "onTodoSnapshotChanged:",
    'pendingKind === "date" && SchedulePolicy.verified(snap,pendingExpected)',
    'pendingKind === "create"',
    "SchedulePolicy.created(snap,beforeCreateIds,pendingTitle)",
    'feedback = "SAVING"',
    'feedback = "SAVE FAILED // DRAFT KEPT"',
    'feedback = "SAVE NOT VERIFIED // CHECK BEFORE RETRY"',
    'feedback = "SAVE REJECTED // DRAFT KEPT"',
    'feedback = "CREATE REJECTED // INPUT KEPT"',
    'feedback = "CREATED UNDATED // READY TO SAVE DATE"',
    "var newRow = SchedulePolicy.newlyCreated(snap,beforeCreateIds,pendingTitle);",
    "selectedTaskId = newRow.id;",
    "originalTask = SchedulePolicy.signature(newRow);",
    "SchedulePolicy.candidates(",
    'property string projectFilter: "all"',
    'property string priorityFilter: "any"',
    'property bool undatedOnly: false',
    'id: filters',
    'onLeftClicked: schedule.cycleProject()',
    'onLeftClicked: schedule.cyclePriority()',
    'onLeftClicked: schedule.undatedOnly = !schedule.undatedOnly',
    'anchors.top: filters.bottom',
    "todoStore.updateTaskDetails(plan.id, plan.priority,",
    "todoStore.addTask(clean)",
    "schedule.createTask()",
    "schedule.saveDate()",
    "schedule.cancelDraft()",
):
    assert required in schedule,required
assert schedule.count("todoStore.updateTaskDetails(")==1
assert schedule.count("todoStore.addTask(")==1
assert "function proposal(snapshot, original, targetDate)" in policy
assert "function verified(snapshot,expected)" in policy
assert "function created(snapshot,ids,title)" in policy
assert "function updateTaskDetails(id, priority, description, dueDate)" in store
assert "function addTask(title)" in store
assert store.count("FileView {")==1
# No new writer, auto-follow-up write or network/subprocess in PLANNER.
for src in (planner,schedule,policy):
    for forbidden in ("FileView {","Process {","JsonAdapter {","XmlHttpRequest",
                      "Qt.openUrlExternally(","Quickshell.execDetached(","GitHubProjectsService {"):
        assert forbidden not in src,forbidden
assert schedule.count("updateTaskDetails(")==1  # Only explicit SAVE DATE handler.
print("PLANNER M5a guarded local scheduling source contracts: PASS")
