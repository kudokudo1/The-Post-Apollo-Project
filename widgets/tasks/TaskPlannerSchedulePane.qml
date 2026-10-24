import QtQuick
import "../../components"
import "TaskPlannerSchedulingPolicy.js" as SchedulePolicy

// M5a: explicit local task creation and due-date edits via the existing
// ApolloHubTodoStore writer. No second FileView, no network, no automatic sync.
Item {
    id: schedule
    property var todoStore: null
    property var todoSnapshot: null
    property string selectedDate: ""
    property string selectedTaskId: ""
    property var originalTask: null
    property bool clearTarget: false
    property bool pendingWrite: false
    property string pendingKind: ""
    property var pendingExpected: null
    property string pendingTitle: ""
    property var beforeCreateIds: []
    property string feedback: ""
    property string projectFilter: "all"
    property string priorityFilter: "any"
    property bool undatedOnly: false

    readonly property var projectChoices: {
        var rows=[{id:"all",label:"ALL"}, {id:"unassigned",label:"UNASSIGNED"}];
        var projects=todoSnapshot && Array.isArray(todoSnapshot.projects)
            ? todoSnapshot.projects : [];
        for (var i=0;i<projects.length;i++)
            if (projects[i] && typeof projects[i].id==="string")
                rows.push({id:projects[i].id,label:projects[i].name});
        return rows;
    }
    readonly property var priorityChoices: ["any","none","low","medium","high","urgent"]
    readonly property var chosenProject: {
        for (var i=0;i<projectChoices.length;i++)
            if (projectChoices[i].id===projectFilter) return projectChoices[i];
        return {id:"missing",label:"MISSING"};
    }
    function cycleProject() {
        var choices=projectChoices, index=-1;
        for (var i=0;i<choices.length;i++)
            if (choices[i].id===projectFilter) { index=i; break; }
        projectFilter=choices[(index+1)%choices.length].id;
    }
    function cyclePriority() {
        var choices=priorityChoices, index=choices.indexOf(priorityFilter);
        priorityFilter=choices[(index+1)%choices.length];
    }

    readonly property bool writable: todoStore !== null
        && SchedulePolicy.writable(todoSnapshot) && !pendingWrite
    readonly property var candidates: SchedulePolicy.candidates(
        todoSnapshot,projectFilter,priorityFilter,undatedOnly)
    readonly property var selectedProposal: SchedulePolicy.proposal(
        todoSnapshot, originalTask, clearTarget ? null : selectedDate)

    function chooseTask(task) {
        if (!writable) { feedback = "STORAGE LOCKED"; return; }
        if (originalTask && selectedTaskId !== task.id
            && selectedProposal.ok) {
            feedback = "CANCEL DRAFT FIRST";
            return;
        }
        originalTask = SchedulePolicy.signature(task);
        selectedTaskId = task.id;
        clearTarget = false;
        feedback = "REVIEW DATE // SAVE TO APPLY";
    }
    function cancelDraft() {
        if (pendingWrite) return;
        selectedTaskId = "";
        originalTask = null;
        clearTarget = false;
        feedback = "DRAFT DISCARDED";
    }
    function saveDate() {
        if (pendingWrite || !writable) return;
        var plan = selectedProposal;
        if (!plan.ok) { feedback = plan.reason; return; }
        pendingExpected = plan.expected;
        pendingKind = "date";
        pendingWrite = true;
        feedback = "SAVING";
        if (!todoStore.updateTaskDetails(plan.id, plan.priority,
                                         plan.description, plan.targetDate)) {
            pendingWrite = false;
            pendingKind = "";
            feedback = "SAVE REJECTED // DRAFT KEPT";
        }
    }
    function createTask() {
        if (pendingWrite || !SchedulePolicy.canCreate(todoSnapshot, newTaskInput.text)
            || todoStore === null) return;
        if (originalTask && selectedProposal.ok) {
            feedback = "CANCEL DRAFT FIRST";
            return;
        }
        var clean=newTaskInput.text.trim();
        beforeCreateIds = todoSnapshot.items.map(function(row) { return row.id; });
        pendingTitle = clean;
        pendingKind = "create";
        pendingWrite = true;
        feedback = "SAVING";
        // The existing API creates an UNDATED task. The user then deliberately
        // selects it from the list and saves its date as a second operation.
        // Never claim both writes were atomic or queue the second automatically.
        if (!todoStore.addTask(clean)) {
            pendingWrite = false;
            pendingKind = "";
            feedback = "CREATE REJECTED // INPUT KEPT";
        }
    }
    onSelectedDateChanged: {
        if (!pendingWrite) clearTarget = false;
    }
    onTodoSnapshotChanged: {
        if (!pendingWrite) return;
        var snap = todoSnapshot;
        if (!snap || snap.state === "saving" || snap.state === "loading") return;
        if (snap.state === "error" || snap.state === "unsupported") {
            pendingWrite = false;
            pendingKind = "";
            feedback = "SAVE FAILED // DRAFT KEPT";
            return;
        }
        if (snap.state !== "ready" && snap.state !== "empty") return;
        if (pendingKind === "date" && SchedulePolicy.verified(snap,pendingExpected)) {
            pendingWrite = false;
            pendingKind = "";
            selectedTaskId = "";
            originalTask = null;
            clearTarget = false;
            feedback = "SAVED // DATE CONFIRMED";
        } else if (pendingKind === "create"
                   && SchedulePolicy.created(snap,beforeCreateIds,pendingTitle)) {
            var newRow = SchedulePolicy.newlyCreated(snap,beforeCreateIds,pendingTitle);
            pendingWrite = false;
            pendingKind = "";
            newTaskInput.text = "";
            if (newRow) {
                originalTask = SchedulePolicy.signature(newRow);
                selectedTaskId = newRow.id;
                clearTarget = false;
                feedback = "CREATED UNDATED // READY TO SAVE DATE";
            } else {
                feedback = "SAVE NOT VERIFIED // CHECK BEFORE RETRY";
            }
        } else {
            pendingWrite = false;
            pendingKind = "";
            feedback = "SAVE NOT VERIFIED // CHECK BEFORE RETRY";
        }
    }
    onVisibleChanged: {
        if (!visible) newTaskInput.focus = false;
    }

    Column {
        id: entry
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: 5
        GohuText {
            width: parent.width
            text: "NEW TASK // CREATED UNDATED FIRST"
            color: Colors.magenta
            font.pixelSize: 10
            elide: Text.ElideRight
        }
        Row {
            width: parent.width
            height: 28
            spacing: 5
            Rectangle {
                width: parent.width - 59
                height: 28
                color: Colors.black
                border.width: 1
                border.color: newTaskInput.activeFocus ? Colors.magenta : Colors.cyan
                TextInput {
                    id: newTaskInput
                    anchors.fill: parent
                    anchors.margins: 5
                    font.family: "GohuFont 11 Nerd Font Mono"
                    font.pixelSize: 10
                    color: Colors.white
                    selectionColor: Colors.magenta
                    selectedTextColor: Colors.black
                    selectByMouse: true
                    maximumLength: 160
                    enabled: schedule.writable
                    onAccepted: schedule.createTask()
                }
            }
            ActionButton {
                width: 54
                height: 28
                label: "ADD"
                labelPixelSize: 10
                available: schedule.writable
                    && !(schedule.originalTask && schedule.selectedProposal.ok)
                    && SchedulePolicy.canCreate(schedule.todoSnapshot,newTaskInput.text)
                onLeftClicked: schedule.createTask()
            }
        }
        GohuText {
            width: parent.width
            text: schedule.feedback || "PICK TASK // CHOOSE DATE // SAVE"
            font.pixelSize: 9
            color: schedule.feedback.indexOf("FAILED")>=0
                || schedule.feedback.indexOf("REJECTED")>=0
                || schedule.feedback.indexOf("NOT VERIFIED")>=0
                ? Colors.orange : Colors.cyan
            elide: Text.ElideRight
        }
    }

    Column {
        id: confirm
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: 5
        GohuText {
            width: parent.width
            font.pixelSize: 10
            color: Colors.white
            elide: Text.ElideRight
            text: schedule.originalTask
                ? "TASK // " + schedule.originalTask.title
                : "SELECT AN EXISTING OR NEW TASK"
        }
        GohuText {
            width: parent.width
            font.pixelSize: 10
            color: Colors.magenta
            elide: Text.ElideRight
            text: "TARGET // " + (schedule.clearTarget ? "UNDATED" : schedule.selectedDate)
        }
        Row {
            width: parent.width
            height: 26
            spacing: 5
            ActionButton {
                width: (parent.width - 10) / 3
                height: 26
                label: "UNDATE"
                labelPixelSize: 9
                available: schedule.writable && schedule.originalTask !== null
                onLeftClicked: schedule.clearTarget = true
            }
            ActionButton {
                width: (parent.width - 10) / 3
                height: 26
                label: "SAVE DATE"
                labelPixelSize: 9
                available: schedule.writable && schedule.selectedProposal.ok
                onLeftClicked: schedule.saveDate()
            }
            ActionButton {
                width: (parent.width - 10) / 3
                height: 26
                label: "CANCEL"
                labelPixelSize: 9
                available: !schedule.pendingWrite && schedule.originalTask !== null
                onLeftClicked: schedule.cancelDraft()
            }
        }
    }

    Column {
        id: filters
        anchors.top: entry.bottom
        anchors.topMargin: 7
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: 4
        Row {
            width: parent.width
            height: 27
            spacing: 4
            ActionButton {
                width: (parent.width - 8) / 3
                height: 27
                label: "PROJECT: " + schedule.chosenProject.label.slice(0,9)
                labelPixelSize: 8
                onLeftClicked: schedule.cycleProject()
            }
            ActionButton {
                width: (parent.width - 8) / 3
                height: 27
                label: "P: " + schedule.priorityFilter.toUpperCase()
                labelPixelSize: 9
                onLeftClicked: schedule.cyclePriority()
            }
            ActionButton {
                width: (parent.width - 8) / 3
                height: 27
                label: schedule.undatedOnly ? "UNDATED" : "ALL DATES"
                labelPixelSize: 9
                selected: schedule.undatedOnly
                onLeftClicked: schedule.undatedOnly = !schedule.undatedOnly
            }
        }
        GohuText {
            width: parent.width
            font.pixelSize: 9
            color: Colors.cyan
            text: schedule.candidates.length + " OPEN TASKS // FILTERED"
            elide: Text.ElideRight
        }
    }
    ListView {
        id: taskList
        anchors.top: filters.bottom
        anchors.topMargin: 7
        anchors.bottom: confirm.top
        anchors.bottomMargin: 8
        anchors.left: parent.left
        anchors.right: parent.right
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        spacing: 3
        model: schedule.candidates
        delegate: Item {
            id: candidate
            required property var modelData
            width: taskList.width
            height: 42
            GohuText {
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: pickButton.left
                anchors.rightMargin: 5
                text: candidate.modelData.title
                color: candidate.modelData.id === schedule.selectedTaskId
                       ? Colors.magenta : Colors.white
                font.pixelSize: 10
                elide: Text.ElideRight
            }
            GohuText {
                anchors.bottom: parent.bottom
                anchors.left: parent.left
                text: candidate.modelData.dueDate || "UNDATED"
                color: Colors.cyan
                font.pixelSize: 9
            }
            ActionButton {
                id: pickButton
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                width: 44
                height: 25
                label: "PICK"
                labelPixelSize: 9
                available: schedule.writable
                onLeftClicked: schedule.chooseTask(candidate.modelData)
            }
        }
    }
}
