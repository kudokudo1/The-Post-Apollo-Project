import QtQuick
import "../../components"

// TASKS M4: edits only the user's local task fields. No new writer.
// Choosing a different task cannot silently discard an unsaved detail draft.
SectionFrame {
    id: details

    property var todoStore: null
    property var todoSnapshot: null
    property string selectedTaskId: ""
    property string priorityDraft: "none"
    property string dueDateDraft: ""
    property bool pendingWrite: false
    property string feedback: ""
    property string pendingPriority: ""
    property string pendingDescription: ""
    property var pendingDueDate: null

    readonly property var priorities: ["none", "low", "medium", "high", "urgent"]
    readonly property var selectedTask: {
        const rows = todoSnapshot && Array.isArray(todoSnapshot.items)
                     ? todoSnapshot.items : [];
        for (let i = 0; i < rows.length; ++i)
            if (rows[i].id === selectedTaskId)
                return rows[i];
        return null;
    }
    readonly property string storeState:
        todoSnapshot && todoSnapshot.state ? String(todoSnapshot.state) : "loading"
    readonly property bool writable:
        todoStore !== null && todoSnapshot && todoSnapshot.writable === true
        && (storeState === "ready" || storeState === "empty")
        && !pendingWrite
    readonly property bool dirty: !!selectedTask && (
        priorityDraft !== selectedTask.priority
        || descriptionInput.text !== selectedTask.description
        || dueDateDraft.trim() !== (selectedTask.dueDate || "")
    )
    readonly property bool dateValid:
        dueDateDraft.trim() === ""
        || /^\d{4}-\d{2}-\d{2}$/.test(dueDateDraft.trim())
        // Full calendar validation is repeated by the domain policy on save.
    readonly property bool fieldsValid: descriptionInput.text.length <= 2000
        && !/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/.test(descriptionInput.text)
        && dateValid

    fillColor: Colors.black
    fillOpacity: 0.25
    borderColor: Colors.cyan
    borderOpacity: 0.7
    borderWidth: 1
    inset: 7

    function resetDraft() {
        if (selectedTask) {
            priorityDraft = selectedTask.priority;
            dueDateDraft = selectedTask.dueDate || "";
            descriptionInput.text = selectedTask.description;
        } else {
            priorityDraft = "none";
            dueDateDraft = "";
            descriptionInput.text = "";
        }
    }
    function chooseTask(taskId) {
        if (pendingWrite) {
            feedback = "SAVE PENDING";
            return;
        }
        if (selectedTaskId !== taskId && dirty) {
            feedback = "SAVE OR DISCARD FIRST";
            return;
        }
        if (selectedTaskId !== taskId) {
            selectedTaskId = taskId;
            resetDraft();
        }
        feedback = "";
    }
    function saveDetails() {
        if (!selectedTask || !writable || !dirty || !fieldsValid)
            return;
        pendingPriority = priorityDraft;
        pendingDescription = descriptionInput.text;
        pendingDueDate = dueDateDraft.trim() === "" ? null : dueDateDraft.trim();
        pendingWrite = true;
        feedback = "SAVING";
        if (!todoStore.updateTaskDetails(selectedTaskId, pendingPriority,
                                         pendingDescription, pendingDueDate)) {
            pendingWrite = false;
            feedback = "SAVE REJECTED";
        }
    }
    onTodoSnapshotChanged: {
        if (pendingWrite) {
            if (storeState === "error" || storeState === "unsupported") {
                pendingWrite = false;
                feedback = "SAVE FAILED // DRAFT KEPT";
            } else if ((storeState === "ready" || storeState === "empty")
                       && selectedTask
                       && selectedTask.priority === pendingPriority
                       && selectedTask.description === pendingDescription
                       && selectedTask.dueDate === pendingDueDate) {
                pendingWrite = false;
                feedback = "SAVED";
            }
        } else if (!dirty && selectedTask) {
            // External Hub edits are reflected unless there is an unsaved draft.
            resetDraft();
        }
    }
    onSelectedTaskChanged: {
        if (selectedTaskId.length > 0 && selectedTask === null && !pendingWrite) {
            selectedTaskId = "";
            resetDraft();
            feedback = "TASK REMOVED";
        }
    }

    Column {
        anchors.fill: parent
        spacing: 6

        GohuText {
            width: parent.width
            text: details.selectedTask ? "DETAILS // " + details.selectedTask.title
                 : "DETAILS // SELECT A TASK TITLE"
            font.pixelSize: 11
            font.bold: true
            color: Colors.magenta
            elide: Text.ElideRight
        }

        Row {
            width: parent.width
            spacing: 5
            ActionButton {
                width: Math.floor((parent.width - 5) / 2)
                height: 26
                labelPixelSize: 9
                label: "P: " + details.priorityDraft.toUpperCase()
                available: details.selectedTask !== null && details.writable
                onLeftClicked: {
                    const at = details.priorities.indexOf(details.priorityDraft);
                    details.priorityDraft = details.priorities[
                        (at + 1) % details.priorities.length
                    ];
                    details.feedback = "";
                }
            }
            Rectangle {
                width: parent.width - Math.floor((parent.width - 5) / 2) - 5
                height: 26
                color: Colors.black
                border.width: 1
                border.color: dueDateInput.activeFocus ? Colors.magenta : Colors.cyan
                TextInput {
                    id: dueDateInput
                    anchors.fill: parent
                    anchors.leftMargin: 4
                    anchors.rightMargin: 4
                    verticalAlignment: TextInput.AlignVCenter
                    text: details.dueDateDraft
                    onTextEdited: details.dueDateDraft = text
                    color: Colors.white
                    font.family: "GohuFont 11 Nerd Font Mono"
                    font.pixelSize: 10
                    selectByMouse: true
                    maximumLength: 10
                    enabled: details.selectedTask !== null && details.writable
                    clip: true
                }
                GohuText {
                    visible: dueDateInput.text.length === 0
                             && !dueDateInput.activeFocus
                    anchors.centerIn: parent
                    text: "YYYY-MM-DD"
                    color: Colors.cyan
                    opacity: 0.6
                    font.pixelSize: 10
                }
            }
        }

        GohuText {
            width: parent.width
            text: "DESCRIPTION // PLAIN TEXT"
            font.pixelSize: 10
            color: Colors.cyan
        }

        Rectangle {
            width: parent.width
            height: Math.max(55, details.height - 129)
            color: Colors.black
            border.width: 1
            border.color: descriptionInput.activeFocus ? Colors.magenta : Colors.cyan
            clip: true

            Flickable {
                anchors.fill: parent
                anchors.margins: 5
                clip: true
                contentHeight: Math.max(height, descriptionInput.paintedHeight + 4)
                boundsBehavior: Flickable.StopAtBounds

                TextEdit {
                    id: descriptionInput
                    width: parent.width
                    height: Math.max(parent.height, paintedHeight + 4)
                    wrapMode: TextEdit.Wrap
                    textFormat: TextEdit.PlainText
                    font.family: "GohuFont 11 Nerd Font Mono"
                    font.pixelSize: 11
                    color: Colors.white
                    selectByMouse: true
                    enabled: details.selectedTask !== null && details.writable
                    selectionColor: Colors.magenta
                    selectedTextColor: Colors.black
                    onTextChanged: {
                        if (details.feedback === "SAVED")
                            details.feedback = "";
                    }
                }
            }
        }

        Row {
            spacing: 5
            width: parent.width
            ActionButton {
                width: 60
                height: 25
                label: "SAVE"
                available: details.selectedTask !== null && details.writable
                           && details.dirty && details.fieldsValid
                onLeftClicked: details.saveDetails()
            }
            ActionButton {
                width: 70
                height: 25
                label: "DISCARD"
                available: details.selectedTask !== null && details.writable
                           && details.dirty
                onLeftClicked: {
                    details.resetDraft();
                    details.feedback = "DRAFT DISCARDED";
                }
            }
            GohuText {
                width: Math.max(30, parent.width - 140)
                height: 25
                verticalAlignment: Text.AlignVCenter
                horizontalAlignment: Text.AlignRight
                elide: Text.ElideRight
                font.pixelSize: 9
                color: details.fieldsValid ? Colors.cyan : Colors.orange
                text: details.feedback
                      || (!details.fieldsValid ? "INVALID FIELDS"
                      : details.dirty ? "UNSAVED" : "")
            }
        }
    }
}
