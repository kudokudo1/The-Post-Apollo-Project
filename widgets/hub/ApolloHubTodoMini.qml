import QtQuick
import "../../components"

// B7 personal checklist UI. One injected ApolloHubTodoStore owns ALL data
// and atomic writes. This component never creates files, timers, or services.
// Store methods only start asynchronous writes; SAVING is not SAVED.
Item {
    id: todoMini

    property var todoStore: null
    property var todoSnapshot: null
    // Enabled only by the standalone TASKS page; ApolloHub's mini tile
    // keeps its existing wheel-scrolling layout and no additional rail.
    property bool taskScrollbarEnabled: false
    property string editingTaskId: ""
    property string savedAddDraft: ""
    property string confirmDeleteId: ""
    property string pendingWriteKind: ""
    property string feedback: ""

    signal textFocusChanged(bool focused)
    // Optional host navigation into richer task details. Hub remains unchanged.
    signal taskSelected(string taskId)

    readonly property string storeState:
        todoSnapshot && todoSnapshot.state ? String(todoSnapshot.state) : "loading"
    readonly property bool writable:
        todoStore !== null && todoSnapshot !== null
        && todoSnapshot.writable === true
        && (storeState === "ready" || storeState === "empty")
        && pendingWriteKind === ""
    readonly property var entries:
        todoSnapshot && Array.isArray(todoSnapshot.items) ? todoSnapshot.items : []
    readonly property int remaining:
        todoSnapshot && Number.isInteger(todoSnapshot.remaining)
        ? Math.max(0, todoSnapshot.remaining) : 0
    readonly property int total:
        todoSnapshot && Number.isInteger(todoSnapshot.total)
        ? Math.max(0, todoSnapshot.total) : 0
    readonly property bool editingTitle: editingTaskId.length > 0
    readonly property bool titleValid: entryInput.text.trim().length > 0
        && entryInput.text.trim().length <= 160
        && !/[\x00-\x1f\x7f]/.test(entryInput.text)
    readonly property string statusLine: {
        if (storeState === "saving")
            return "TO-DO // SAVING // NOT YET CONFIRMED";
        if (storeState === "error" || storeState === "unsupported")
            return "TO-DO // " + storeState.toUpperCase() + " // WRITES LOCKED";
        if (storeState === "loading")
            return "TO-DO // LOADING";
        if (feedback.length)
            return "TO-DO // " + feedback;
        return "TO-DO // " + remaining + " OPEN / " + total + " TOTAL";
    }

    onTodoSnapshotChanged: {
        if (pendingWriteKind === "")
            return;
        // Only the store's completed onSaved transition confirms a write.
        if (storeState === "ready" || storeState === "empty") {
            if (pendingWriteKind === "add")
                entryInput.text = "";
            if (pendingWriteKind === "rename") {
                editingTaskId = "";
                entryInput.text = savedAddDraft;
                savedAddDraft = "";
            }
            if (pendingWriteKind === "remove")
                confirmDeleteId = "";
            pendingWriteKind = "";
            feedback = "";
        } else if (storeState === "error" || storeState === "unsupported") {
            // Keep unsaved input and any confirmation on disk failure.
            pendingWriteKind = "";
        }
    }

    onVisibleChanged: {
        if (!visible) {
            entryInput.focus = false;
            textFocusChanged(false);
        }
    }

    function cancelRename() {
        if (pendingWriteKind !== "")
            return;
        editingTaskId = "";
        entryInput.text = savedAddDraft;
        savedAddDraft = "";
        entryInput.focus = false;
    }

    function startRename(task) {
        if (!writable || !task || !task.id)
            return;
        confirmDeleteId = "";
        if (!editingTitle)
            savedAddDraft = entryInput.text;
        editingTaskId = String(task.id);
        entryInput.text = String(task.title || "");
        feedback = "";
        entryInput.forceActiveFocus();
        entryInput.selectAll();
    }

    function commitText() {
        if (!writable || !titleValid)
            return;
        const value = entryInput.text;
        const kind = editingTitle ? "rename" : "add";
        const target = editingTaskId;
        pendingWriteKind = kind;
        const started = kind === "rename"
            ? todoStore.renameTask(target, value)
            : todoStore.addTask(value);
        if (!started) {
            pendingWriteKind = "";
            feedback = "ACTION REJECTED";
        }
        // Do not clear the typed text here: stage() is NOT a saved file.
    }

    function toggleDone(task) {
        if (!writable || !task)
            return;
        pendingWriteKind = "done";
        if (!todoStore.setTaskDone(task.id, task.done !== true)) {
            pendingWriteKind = "";
            feedback = "ACTION REJECTED";
        }
    }

    function requestDelete(task) {
        if (!writable || !task)
            return;
        // First click only arms confirmation. Never delete on selection.
        confirmDeleteId = String(task.id);
        feedback = "";
    }

    function confirmDelete(task) {
        if (!writable || !task || confirmDeleteId !== task.id)
            return;
        pendingWriteKind = "remove";
        // Backend refuses deletion without this explicit confirmed=true.
        if (!todoStore.removeTask(task.id, true)) {
            pendingWriteKind = "";
            feedback = "ACTION REJECTED";
        }
    }

    // One right-hand control rail: RELOAD directly over ADD/SAVE, equal
    // widths and one aligned right edge. The count stays left and the
    // entry field stays opposite ADD; no extra vertical row is added.
    Item {
        id: editorArea
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: 44

        Column {
            id: controlStack
            anchors.top: parent.top
            anchors.right: parent.right
            width: 47
            spacing: 3

            ActionButton {
                id: reloadButton
                width: parent.width
                height: 20
                trackLabelGlowLocally: true
                softGlowEnabled: false
                labelPixelSize: 9
                label: "RELOAD"
                // Explicit recovery; never discard an in-flight save.
                available: todoMini.todoStore !== null
                           && todoMini.storeState !== "saving"
                           && todoMini.pendingWriteKind === ""
                onLeftClicked: {
                    if (todoMini.todoStore && todoMini.todoStore.reloadFromDisk()) {
                        todoMini.confirmDeleteId = "";
                        todoMini.feedback = "";
                    }
                }
            }

            ActionButton {
                id: submitButton
                width: parent.width
                height: 21
                trackLabelGlowLocally: true
                softGlowEnabled: false
                labelPixelSize: 10
                label: todoMini.editingTitle ? "SAVE" : "ADD"
                available: todoMini.writable && todoMini.titleValid
                onLeftClicked: todoMini.commitText()
            }
        }

        GohuText {
            id: countRow
            anchors.left: parent.left
            anchors.right: controlStack.left
            anchors.rightMargin: 5
            anchors.top: parent.top
            height: 17
            verticalAlignment: Text.AlignVCenter
            font.pixelSize: 10
            color: todoMini.storeState === "error"
                   || todoMini.storeState === "unsupported" ? Colors.orange : Colors.cyan
            elide: Text.ElideRight
            text: todoMini.storeState === "error"
                  || todoMini.storeState === "unsupported"
                  ? "STORAGE // " + String(todoMini.todoSnapshot.error || "ERROR")
                  : todoMini.storeState === "loading" ? "READING CHECKLIST..."
                  : todoMini.storeState === "saving" ? "SAVING // AWAITING DISK"
                  : todoMini.remaining + " OPEN // " + todoMini.total + " TOTAL"
        }

        Row {
            id: entryRow
            anchors.left: parent.left
            anchors.right: controlStack.left
            anchors.rightMargin: 5
            anchors.bottom: parent.bottom
            height: 23
            spacing: 5

            Rectangle {
                width: Math.max(30, entryRow.width
                                - (cancelButton.visible
                                   ? cancelButton.width + entryRow.spacing : 0))
                height: parent.height
                color: Colors.black
                border.width: 1
                border.color: entryInput.activeFocus ? Colors.magenta : Colors.cyan

                TextInput {
                    id: entryInput
                    anchors.fill: parent
                    anchors.leftMargin: 5
                    anchors.rightMargin: 5
                    verticalAlignment: TextInput.AlignVCenter
                    font.family: "GohuFont 11 Nerd Font Mono"
                    font.pixelSize: 12
                    color: Colors.white
                    selectionColor: Colors.magenta
                    selectedTextColor: Colors.black
                    clip: true
                    selectByMouse: true
                    maximumLength: 160
                    enabled: todoMini.writable
                    onAccepted: todoMini.commitText()
                    onActiveFocusChanged: todoMini.textFocusChanged(activeFocus)
                    Keys.onEscapePressed: function(event) {
                        if (todoMini.editingTitle)
                            todoMini.cancelRename();
                        else
                            entryInput.focus = false;
                        event.accepted = true;
                    }
                }
                GohuText {
                    anchors {
                        left: parent.left
                        leftMargin: 6
                        verticalCenter: parent.verticalCenter
                    }
                    visible: entryInput.text.length === 0 && !entryInput.activeFocus
                    font.pixelSize: 11
                    color: Colors.cyan
                    opacity: 0.6
                    text: todoMini.editingTitle ? "RENAME TASK" : "NEW TASK"
                }
            }

            ActionButton {
                id: cancelButton
                visible: todoMini.editingTitle
                width: 43
                height: parent.height
                trackLabelGlowLocally: true
                softGlowEnabled: false
                labelPixelSize: 10
                label: "BACK"
                available: todoMini.writable
                onLeftClicked: todoMini.cancelRename()
            }
        }
    }

    ListView {
        id: todoList
        anchors {
            top: editorArea.bottom
            topMargin: 4
            bottom: parent.bottom
            left: parent.left
            right: parent.right
        }
        clip: true
        spacing: 2
        boundsBehavior: Flickable.StopAtBounds
        model: todoMini.entries
        delegate: Item {
            id: todoEntry
            required property var modelData
            width: todoList.width
            height: 22
            readonly property bool awaitingDelete:
                todoMini.confirmDeleteId === modelData.id

            Row {
                id: actions
                anchors.fill: parent
                // Protect EDIT/DEL from the list's right-hand star rail.
                // No empty gutter is reserved until scrolling is needed.
                anchors.rightMargin: todoMini.taskScrollbarEnabled
                                     && taskListRail.scrollable
                                     ? taskListRail.reservedExtent : 0
                spacing: 5

                ActionButton {
                    width: 23
                    height: parent.height
                    trackLabelGlowLocally: true
                    softGlowEnabled: false
                    labelPixelSize: 12
                    label: todoEntry.modelData.done ? "✓" : "□"
                    accentColor: todoEntry.modelData.done ? Colors.magenta : Colors.cyan
                    available: todoMini.writable
                    onLeftClicked: todoMini.toggleDone(todoEntry.modelData)
                }
                GohuText {
                    width: Math.max(24, actions.width - 23 - 44 - 40
                                    - 3 * actions.spacing)
                    height: parent.height
                    verticalAlignment: Text.AlignVCenter
                    font.pixelSize: 11
                    color: todoEntry.modelData.done ? Colors.cyan : Colors.white
                    opacity: todoEntry.modelData.done ? 0.6 : 1.0
                    elide: Text.ElideRight
                    text: todoEntry.awaitingDelete
                          ? "DELETE THIS TASK?" : todoEntry.modelData.title

                    TapHandler {
                        enabled: !todoEntry.awaitingDelete
                        onTapped: todoMini.taskSelected(String(todoEntry.modelData.id))
                    }
                }
                ActionButton {
                    width: 44
                    height: parent.height
                    trackLabelGlowLocally: true
                    softGlowEnabled: false
                    labelPixelSize: 10
                    label: todoEntry.awaitingDelete ? "NO" : "EDIT"
                    available: todoMini.writable
                    onLeftClicked: {
                        if (todoEntry.awaitingDelete)
                            todoMini.confirmDeleteId = "";
                        else
                            todoMini.startRename(todoEntry.modelData);
                    }
                }
                ActionButton {
                    width: 40
                    height: parent.height
                    trackLabelGlowLocally: true
                    softGlowEnabled: false
                    labelPixelSize: 10
                    destructive: true
                    accentColor: Colors.red
                    label: todoEntry.awaitingDelete ? "YES" : "DEL"
                    available: todoMini.writable
                    onLeftClicked: {
                        if (todoEntry.awaitingDelete)
                            todoMini.confirmDelete(todoEntry.modelData);
                        else
                            todoMini.requestDelete(todoEntry.modelData);
                    }
                }
            }
        }
    }

    // Shared neon scrollbar belongs to the task-list viewport, not the
    // editor/header. It is mounted next to the ListView so row clipping and
    // pointer hit testing remain independent of the star drag target.
    NeonScrollBar {
        id: taskListRail
        parent: todoMini
        flickable: todoMini.taskScrollbarEnabled ? todoList : null
        geometryMode: "viewport"
        accountForContentOrigin: true
        handleStyle: "star"
        // Screenshot: track is visible but Canvas star does not paint here.
        // Keep standard NeonScrollBar mechanics; draw the same star as a Shape.
        starSceneGraphRenderer: todoMini.taskScrollbarEnabled
        handleColor: Colors.magenta
        railColor: Colors.cyan
    }

    GohuText {
        anchors.centerIn: todoList
        visible: todoMini.entries.length === 0
        width: parent.width
        height: 20
        font.pixelSize: 11
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        color: todoMini.storeState === "empty" ? Colors.cyan : Colors.orange
        text: todoMini.storeState === "empty" ? "NO TASKS"
              : todoMini.storeState === "error" ? "STORAGE LOCKED"
              : todoMini.storeState === "unsupported" ? "UNSUPPORTED FILE"
              : todoMini.storeState === "loading" ? "LOADING..."
              : "NO TASKS VISIBLE"
    }
}
