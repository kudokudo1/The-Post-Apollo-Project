import QtQuick
import "../../components"
import "../tasks"

// Phase 3 TASKS / TODAY: use canonical TaskTodayPane and TaskDetailsPane
// against the ONE existing TodoStore. No second writer or task poller.
// Switching internal tabs cannot discard a pending or dirty details draft.
Item {
    id: todoExplore
    property var todoStore: null
    property var todoSnapshot: null
    property string selectedView: "list"
    property string navigationFeedback: ""
    signal textFocusChanged(bool focused)

    readonly property bool detailMode: selectedView === "details"
    readonly property bool todayMode: selectedView === "today"
    readonly property string todayStatus:
        !taskToday.projection.available
        ? "TO-DO // TODAY // " + taskToday.storeState.toUpperCase()
        : "TO-DO // TODAY // " + taskToday.projection.overdue
          + " OVERDUE / " + taskToday.projection.dueToday + " DUE"
    readonly property string statusLine:
        navigationFeedback.length > 0
        ? "TO-DO // " + navigationFeedback
        : detailMode
        ? (taskDetails.pendingWrite ? "TO-DO // DETAILS // SAVING // NOT YET CONFIRMED"
           : taskDetails.dirty ? "TO-DO // DETAILS // UNSAVED DRAFT"
           : taskDetails.feedback.length > 0
             ? "TO-DO // DETAILS // " + taskDetails.feedback
             : taskDetails.selectedTask
               ? "TO-DO // TASK DETAILS // " + String(taskDetails.selectedTask.title)
               : "TO-DO // SELECT A TASK")
        : todayMode ? todayStatus
        : taskList.statusLine

    // Dirty details remain mounted on an internal tab switch, but keep the
    // tab itself visible until the operator explicitly saves or discards.
    function chooseView(view) {
        if (view !== "list" && view !== "today" && view !== "details")
            return;
        if (view === selectedView) {
            navigationFeedback = "";
            return;
        }
        if (detailMode && (taskDetails.pendingWrite || taskDetails.dirty)) {
            navigationFeedback = taskDetails.pendingWrite
                                 ? "SAVE PENDING" : "SAVE OR DISCARD FIRST";
            taskDetails.feedback = navigationFeedback;
            return;
        }
        navigationFeedback = "";
        selectedView = view;
    }

    // Both LIST title taps and TODAY's explicit OPEN request reuse the same
    // selected task and revision-safe TASKS details workflow. A different
    // target may not replace an unsaved or in-flight details draft.
    function openTask(taskId) {
        if (typeof taskId !== "string" || taskId.length === 0)
            return;
        if (taskDetails.pendingWrite
                || (taskDetails.dirty && taskDetails.selectedTaskId !== taskId)) {
            navigationFeedback = taskDetails.pendingWrite
                                 ? "SAVE PENDING" : "SAVE OR DISCARD FIRST";
            taskDetails.feedback = navigationFeedback;
            return;
        }
        taskDetails.chooseTask(taskId);
        if (!taskDetails.selectedTask || taskDetails.selectedTask.id !== taskId) {
            navigationFeedback = taskDetails.feedback || "TASK UNAVAILABLE";
            return;
        }
        navigationFeedback = "";
        selectedView = "details";
    }

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
            width: Math.max(1, (modeSelector.width - 2 * modeSelector.spacing) / 3)
            height: parent.height
            label: "LIST"
            selected: todoExplore.selectedView === "list"
            trackLabelGlowLocally: true
            softGlowEnabled: false
            onLeftClicked: todoExplore.chooseView("list")
        }
        ActionButton {
            width: Math.max(1, (modeSelector.width - 2 * modeSelector.spacing) / 3)
            height: parent.height
            label: "TODAY"
            selected: todoExplore.todayMode
            trackLabelGlowLocally: true
            softGlowEnabled: false
            onLeftClicked: todoExplore.chooseView("today")
        }
        ActionButton {
            width: Math.max(1, (modeSelector.width - 2 * modeSelector.spacing) / 3)
            height: parent.height
            label: "DETAILS"
            selected: todoExplore.detailMode
            available: taskDetails.selectedTask !== null
            trackLabelGlowLocally: true
            softGlowEnabled: false
            onLeftClicked: todoExplore.chooseView("details")
        }
    }

    ApolloHubTodoMini {
        id: taskList
        visible: todoExplore.selectedView === "list"
        todoStore: todoExplore.todoStore
        todoSnapshot: todoExplore.todoSnapshot
        anchors.top: modeSelector.bottom
        anchors.topMargin: 6
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        onTextFocusChanged: function(focused) {
            if (todoExplore.selectedView === "list")
                todoExplore.textFocusChanged(focused);
        }
        onTaskSelected: function(taskId) {
            todoExplore.openTask(taskId);
        }
    }

    // The actual TASKS TODAY pane: pure due-date projection, existing local
    // civil-date refresh and owner-owned OPEN navigation. The pane's minute
    // timer runs only while TODAY is visible; no new task/file polling.
    TaskTodayPane {
        id: taskToday
        visible: todoExplore.todayMode
        todoSnapshot: todoExplore.todoSnapshot
        anchors.top: modeSelector.bottom
        anchors.topMargin: 6
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        onOpenTaskRequested: function(taskId) {
            todoExplore.openTask(taskId);
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
