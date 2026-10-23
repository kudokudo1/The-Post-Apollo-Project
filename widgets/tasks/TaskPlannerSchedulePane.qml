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

    readonly property bool writable: todoStore !== null
        && SchedulePolicy.writable(todoSnapshot) && !pendingWrite
    readonly property var candidates: todoSnapshot && Array.isArray(todoSnapshot.items)
        ? todoSnapshot.items.filter(function(task) { return task && !task.done; })
        : []
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
            pendingWrite = false;
            pendingKind = "";
            newTaskInput.text = "";
            feedback = "CREATED UNDATED // SELECT TASK TO SCHEDULE";
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

    ListView {
        id: taskList
        anchors.top: entry.bottom
        anchors.topMargin: 8
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
