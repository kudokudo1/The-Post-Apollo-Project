import QtQuick
import "../../components"
import "../tasks"

// Stage 8G: reuse the exact TASKS editor and the existing single TodoStore.
// Swapping views never writes or silently discards a task-details draft.
Item {
    id: todoExplore
    property var todoStore: null
    property var todoSnapshot: null
    property string selectedView: "list"
    signal textFocusChanged(bool focused)
    readonly property bool detailMode: selectedView === "details"
    readonly property string statusLine:
        detailMode
        ? (taskDetails.pendingWrite ? "TO-DO // DETAILS // SAVING // NOT YET CONFIRMED"
           : taskDetails.dirty ? "TO-DO // DETAILS // UNSAVED DRAFT"
           : taskDetails.feedback.length > 0
             ? "TO-DO // DETAILS // " + taskDetails.feedback
             : taskDetails.selectedTask
               ? "TO-DO // TASK DETAILS // " + String(taskDetails.selectedTask.title)
               : "TO-DO // SELECT A TASK")
        : taskList.statusLine

    // DETAILS contains date/description text editors. Don't let Hub
    // spatial keyboard shortcuts consume those keystrokes.
    onDetailModeChanged: textFocusChanged(detailMode)
    onVisibleChanged: {
        if (!visible)
            textFocusChanged(false);
        else if (detailMode)
            textFocusChanged(true);
    }

    Row {
        id: modeSelector
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: todoExplore.height >= 300 ? 30 : 26
        spacing: 6
        ActionButton {
            width: Math.max(1, (modeSelector.width - modeSelector.spacing) / 2)
            height: parent.height
            label: "LIST"
            selected: !todoExplore.detailMode
            trackLabelGlowLocally: true
            softGlowEnabled: false
            onLeftClicked: todoExplore.selectedView = "list"
        }
        ActionButton {
            width: Math.max(1, (modeSelector.width - modeSelector.spacing) / 2)
            height: parent.height
            label: "DETAILS"
            selected: todoExplore.detailMode
            available: taskDetails.selectedTask !== null
            trackLabelGlowLocally: true
            softGlowEnabled: false
            onLeftClicked: todoExplore.selectedView = "details"
        }
    }

    ApolloHubTodoMini {
        id: taskList
        visible: !todoExplore.detailMode
        todoStore: todoExplore.todoStore
        todoSnapshot: todoExplore.todoSnapshot
        anchors.top: modeSelector.bottom
        anchors.topMargin: 6
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        onTextFocusChanged: function(focused) {
            if (!todoExplore.detailMode)
                todoExplore.textFocusChanged(focused);
        }
        onTaskSelected: function(taskId) {
            // The canonical editor refuses a different task when its
            // current details are dirty or a write remains pending.
            taskDetails.chooseTask(taskId);
            // Show its existing SAVE OR DISCARD FIRST feedback rather than
            // concealing the guarded refusal behind the list.
            todoExplore.selectedView = "details";
        }
    }

    TaskDetailsPane {
        id: taskDetails
        visible: todoExplore.detailMode
        todoStore: todoExplore.todoStore
        todoSnapshot: todoExplore.todoSnapshot
        anchors.top: modeSelector.bottom
        anchors.topMargin: 6
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
    }
}
