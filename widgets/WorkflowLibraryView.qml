import QtQuick
import Quickshell
import qs.components

Item {
    id: root

    required property var githubService
    required property var libraryStore

    property var keyboardHost: null
    property string setNameDraft: ""

    signal workflowSelected(int index)

    component LibraryButton: Rectangle {
        id: button

        property string label: ""
        property bool enabledAction: true
        property bool selectedAction: false
        property bool destructive: false
        property bool keyboardNavigable:
            label !== "↑"
            && label !== "↓"
        readonly property bool keyboardSelected:
            !!root.keyboardHost
            && root.keyboardHost.gitKeyboardControl === button
        readonly property bool keyboardSelector:
            keyboardSelected
            && root.keyboardHost.gitSelectorSource === "keyboard"
        readonly property bool mouseSelector:
            keyboardSelected
            && root.keyboardHost.gitSelectorSource === "mouse"

        signal triggered()

        Component.onCompleted: {
            if (root.keyboardHost)
                root.keyboardHost.registerGitKeyboardControl(button);
        }

        Component.onDestruction: {
            if (root.keyboardHost)
                root.keyboardHost.unregisterGitKeyboardControl(button);
        }

        height: 28
        opacity:
            destructive
            ? (enabledAction ? 1.0 : 0.34)
            : 1.0

        color:
            !enabledAction
            ? Colors.black
            : keyboardSelector || selectedAction
            ? Colors.yellow
            : Colors.black

        border.width:
            keyboardSelector || mouseSelector
            ? 2 : 1
        border.color:
            keyboardSelector || mouseSelector
            ? Colors.orange
            : selectedAction
            ? Colors.magenta
            : mouse.containsMouse
            ? Colors.orange
            : destructive
            ? Colors.red
            : Colors.cyan

        GohuText {
            anchors.centerIn: parent

            text: button.label
            font.pixelSize: 8

            color:
                button.keyboardSelector || button.selectedAction
                ? Colors.magenta
                : button.destructive
                ? Colors.red
                : Colors.cyan

            opacity:
                button.destructive
                ? 1.0
                : button.enabledAction ? 1.0 : 0.34
        }

        MouseArea {
            id: mouse

            anchors.fill: parent
            enabled: button.enabledAction
            hoverEnabled: true
            cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor

            onEntered: {
                if (root.keyboardHost)
                    root.keyboardHost.selectGitControlFromMouse(button);
            }

            onPositionChanged: {
                if (root.keyboardHost)
                    root.keyboardHost.selectGitControlFromMouse(button);
            }

            onClicked: {
                if (root.keyboardHost)
                    root.keyboardHost.selectGitControlFromMouse(button);

                button.triggered();
            }
        }
    }

    Row {
        anchors.fill: parent
        spacing: 10

        // ===== EXECUTION / SAVED SETS ==========================

        Column {
            id: executionPane

            width: (parent.width - 10) * 0.46
            height: parent.height
            spacing: 10

            Rectangle {
                id: queuePane

                width: parent.width
                height: (parent.height - 10) * 0.58

                color: Colors.dark
                border.width: 1
                border.color: Colors.orange

                Column {
                    anchors {
                        fill: parent
                        margins: 8
                    }

                    spacing: 6

                    Row {
                        width: parent.width - 2
                        height: 26
                        spacing: 6

                        GohuText {
                            width: parent.width - 146
                            text: "RUN QUEUE // ORDER"
                            font.pixelSize: 11
                            color: Colors.magenta
                        }

                        LibraryButton {
                            width: 62
                            label: "CLEAR"
                            enabledAction: root.libraryStore.queue.length > 0

                            onTriggered: root.libraryStore.clearQueue()
                        }

                        LibraryButton {
                            width: 72
                            label:
                                root.githubService.actionBusy
                                ? "RUNNING"
                                : "RUN QUEUE"

                            enabledAction:
                                root.libraryStore.queue.length > 0
                                && root.libraryStore.missingQueueCount === 0
                                && !root.githubService.actionBusy

                            onTriggered: root.libraryStore.runQueue()
                        }
                    }

                    GohuText {
                        width: parent.width

                        text:
                            root.libraryStore.missingQueueCount > 0
                            ? String(root.libraryStore.missingQueueCount)
                              + " MISSING // RUN BLOCKED"
                            : root.githubService.actionResult !== "READY"
                            ? root.githubService.actionResult
                            : String(root.libraryStore.queue.length) + " READY"

                        font.pixelSize: 7
                        color:
                            root.libraryStore.missingQueueCount > 0
                            ? Colors.red
                            : Colors.cyan
                    }

                    Flickable {
                        width: parent.width
                        height: parent.height - 92

                        clip: true
                        contentWidth: width
                        contentHeight: queueColumn.height
                        boundsBehavior: Flickable.StopAtBounds

                        Column {
                            id: queueColumn

                            width: parent.width
                            spacing: 4

                            Repeater {
                                model: root.libraryStore.queue

                                Rectangle {
                                    required property int index
                                    required property var modelData

                                    width: queueColumn.width
                                    height: 34

                                    color: Colors.black
                                    border.width: 1
                                    border.color:
                                        root.libraryStore.workflowAvailable(modelData.path)
                                        ? Colors.cyan
                                        : Colors.red

                                    Row {
                                        anchors {
                                            fill: parent
                                            margins: 3
                                        }

                                        spacing: 3

                                        GohuText {
                                            width: parent.width - 114
                                            anchors.verticalCenter: parent.verticalCenter

                                            text:
                                                String(index + 1)
                                                + " // "
                                                + String(modelData.name || modelData.path || "UNKNOWN")
                                                + (
                                                    root.libraryStore.workflowAvailable(modelData.path)
                                                    ? ""
                                                    : " // MISSING"
                                                )

                                            font.pixelSize: 7
                                            color:
                                                root.libraryStore.workflowAvailable(modelData.path)
                                                ? Colors.white
                                                : Colors.red
                                            elide: Text.ElideRight
                                        }

                                        LibraryButton {
                                            width: 32
                                            height: 26
                                            label: "↑"
                                            enabledAction: index > 0

                                            onTriggered: root.libraryStore.moveQueueIndex(index, -1)
                                        }

                                        LibraryButton {
                                            width: 32
                                            height: 26
                                            label: "↓"
                                            enabledAction: index < root.libraryStore.queue.length - 1

                                            onTriggered: root.libraryStore.moveQueueIndex(index, 1)
                                        }

                                        LibraryButton {
                                            width: 38
                                            height: 26
                                            label: "×"

                                            onTriggered: root.libraryStore.removeQueueIndex(index)
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Row {
                        width: parent.width
                        height: 28
                        spacing: 6

                        Rectangle {
                            width: parent.width - 98
                            height: 28

                            color: Colors.black
                            border.width: 1
                            border.color:
                                setNameInput.activeFocus
                                ? Colors.magenta
                                : Colors.orange

                            GohuText {
                                anchors {
                                    left: parent.left
                                    verticalCenter: parent.verticalCenter
                                    leftMargin: 6
                                }

                                visible:
                                    setNameInput.text.length === 0
                                    && !setNameInput.activeFocus

                                text: "SET NAME"
                                font.pixelSize: 8
                                color: Colors.white
                                opacity: 0.40
                            }

                            TextInput {
                                id: setNameInput

                                anchors {
                                    fill: parent
                                    margins: 5
                                }

                                activeFocusOnPress: true
                                selectByMouse: true
                                verticalAlignment: TextInput.AlignVCenter
                                font.family: "GohuFont 11 Nerd Font Mono"
                                font.pixelSize: 8
                                color: Colors.white
                                selectionColor: Colors.magenta
                                selectedTextColor: Colors.black

                                text: root.setNameDraft

                                onTextChanged: root.setNameDraft = text

                                onAccepted: {
                                    focus = false;

                                    if (root.keyboardHost) {
                                        root.keyboardHost.activeTextEditor = null;
                                        root.keyboardHost.restoreGitKeyboardFocus(false);
                                    }
                                }

                                Keys.onEscapePressed: function(event) {
                                    focus = false;

                                    if (root.keyboardHost) {
                                        root.keyboardHost.activeTextEditor = null;
                                        root.keyboardHost.restoreGitKeyboardFocus(false);
                                    }

                                    event.accepted = true;
                                }

                                onActiveFocusChanged: {
                                    if (!root.keyboardHost)
                                        return;

                                    if (activeFocus)
                                        root.keyboardHost.activeTextEditor = setNameInput;
                                    else if (root.keyboardHost.activeTextEditor === setNameInput)
                                        root.keyboardHost.activeTextEditor = null;
                                }
                            }
                        }

                        LibraryButton {
                            width: 92
                            label: "SAVE SET"

                            enabledAction:
                                root.libraryStore.queue.length > 0
                                && root.setNameDraft.trim().length > 0

                            onTriggered: {
                                root.libraryStore.saveQueueAsSet(root.setNameDraft);
                                root.setNameDraft = "";
                            }
                        }
                    }
                }
            }

            Rectangle {
                width: parent.width
                height: parent.height - queuePane.height - 10

                color: Colors.dark
                border.width: 1
                border.color: Colors.blue

                Column {
                    anchors {
                        fill: parent
                        margins: 8
                    }

                    spacing: 6

                    Row {
                        width: parent.width
                        height: 22

                        GohuText {
                            width: parent.width - 82
                            text: "SAVED SETS // ORDERS"
                            font.pixelSize: 11
                            color: Colors.magenta
                        }

                        GohuText {
                            width: 82
                            text: String(root.libraryStore.repoSets.length) + " SETS"
                            horizontalAlignment: Text.AlignRight
                            font.pixelSize: 8
                            color: Colors.orange
                        }
                    }

                    Flickable {
                        width: parent.width
                        height: parent.height - 28

                        clip: true
                        contentWidth: width
                        contentHeight: setColumn.height
                        boundsBehavior: Flickable.StopAtBounds

                        Column {
                            id: setColumn

                            width: parent.width
                            spacing: 4

                            Repeater {
                                model: root.libraryStore.repoSets

                                Rectangle {
                                    required property int index
                                    required property var modelData

                                    width: setColumn.width
                                    height: 38

                                    color: Colors.black
                                    border.width: 1
                                    border.color:
                                        root.libraryStore.setMissingCount(modelData) > 0
                                        ? Colors.red
                                        : Colors.blue

                                    Row {
                                        anchors {
                                            fill: parent
                                            margins: 4
                                        }

                                        spacing: 4

                                        Column {
                                            width: parent.width - 166
                                            anchors.verticalCenter: parent.verticalCenter
                                            spacing: 1

                                            GohuText {
                                                width: parent.width
                                                text: String(modelData.name || "UNNAMED SET")
                                                font.pixelSize: 8
                                                color: Colors.white
                                                elide: Text.ElideRight
                                            }

                                            GohuText {
                                                width: parent.width
                                                text:
                                                    String(
                                                        Array.isArray(modelData.items)
                                                        ? modelData.items.length
                                                        : 0
                                                    )
                                                    + " WORKFLOWS"
                                                    + (
                                                        root.libraryStore.setMissingCount(modelData) > 0
                                                        ? " // MISSING "
                                                          + String(root.libraryStore.setMissingCount(modelData))
                                                        : ""
                                                    )
                                                font.pixelSize: 7
                                                color:
                                                    root.libraryStore.setMissingCount(modelData) > 0
                                                    ? Colors.red
                                                    : Colors.cyan
                                            }
                                        }

                                        LibraryButton {
                                            width: 48
                                            height: 26
                                            label: "LOAD"

                                            onTriggered: root.libraryStore.loadSet(modelData)
                                        }

                                        LibraryButton {
                                            width: 48
                                            height: 26
                                            label: "RUN"

                                            enabledAction:
                                                root.libraryStore.setMissingCount(modelData) === 0
                                                && !root.githubService.actionBusy

                                            onTriggered: root.libraryStore.runSet(modelData)
                                        }

                                        LibraryButton {
                                            width: 58
                                            height: 26
                                            label: "DELETE"

                                            onTriggered: root.libraryStore.deleteSet(modelData)
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        // ===== COMPLETE WORKFLOW LIBRARY =======================

        Rectangle {
            id: workflowPane

            width: (parent.width - 10) * 0.54
            height: parent.height

            color: Colors.dark
            border.width: 1
            border.color: Colors.cyan

            Column {
                anchors {
                    fill: parent
                    margins: 9
                }

                spacing: 7

                Row {
                    width: parent.width
                    height: 24

                    GohuText {
                        width: parent.width - 100
                        text: "ALL WORKFLOWS"
                        font.pixelSize: 12
                        color: Colors.magenta
                    }

                    GohuText {
                        width: 100
                        text: String(root.libraryStore.workflows.length) + " MACHINES"
                        horizontalAlignment: Text.AlignRight
                        font.pixelSize: 8
                        color: Colors.orange
                    }
                }

                Item {
                    width: parent.width
                    height: parent.height - 31

                    Flickable {
                        id: workflowFlick

                        anchors {
                            left: parent.left
                            right: workflowScrollTrack.left
                            top: parent.top
                            bottom: parent.bottom
                            rightMargin: 7
                        }

                        clip: true
                        contentWidth: width
                        contentHeight: workflowColumn.height
                        boundsBehavior: Flickable.StopAtBounds

                        Column {
                            id: workflowColumn

                            width: parent.width
                            spacing: 5

                            Repeater {
                                model: root.libraryStore.workflows

                                Rectangle {
                                    required property int index
                                    required property var modelData

                                    width: workflowColumn.width
                                    height: 48

                                    color: Colors.black
                                    border.width: 1
                                    border.color: Colors.orange

                                    Row {
                                        anchors {
                                            fill: parent
                                            margins: 6
                                        }

                                        spacing: 6

                                        Column {
                                            width: parent.width - 182
                                            anchors.verticalCenter: parent.verticalCenter
                                            spacing: 2

                                            GohuText {
                                                width: parent.width
                                                text: String(modelData.name || modelData.path || "UNKNOWN")
                                                font.pixelSize: 9
                                                color: Colors.white
                                                elide: Text.ElideRight
                                            }

                                            GohuText {
                                                width: parent.width
                                                text: String(modelData.path || "")
                                                font.pixelSize: 9
                                                color: Colors.orange
                                                opacity: 0.78
                                                elide: Text.ElideMiddle
                                            }
                                        }

                                        LibraryButton {
                                            width: 62
                                            label: "LOAD"

                                            onTriggered: root.workflowSelected(index)
                                        }

                                        LibraryButton {
                                            width: 68
                                            label: "+ QUEUE"

                                            onTriggered: root.libraryStore.addWorkflow(modelData)
                                        }

                                        LibraryButton {
                                            width: 34
                                            label: "X"
                                            destructive: true
                                            enabledAction: !root.githubService.actionBusy

                                            onTriggered:
                                                root.githubService.deleteWorkflow(
                                                    String(modelData.path || "")
                                                )
                                        }
                                    }
                                }
                            }

                            GohuText {
                                width: parent.width
                                visible: root.libraryStore.workflows.length === 0

                                text: "NO SAVED WORKFLOWS"
                                horizontalAlignment: Text.AlignHCenter
                                font.pixelSize: 9
                                color: Colors.cyan
                                opacity: 0.42
                            }
                        }
                    }

                    Rectangle {
                        id: workflowScrollTrack

                        anchors {
                            right: parent.right
                            top: parent.top
                            bottom: parent.bottom
                        }

                        width: 9
                        color: Colors.black
                        border.width: 1
                        border.color: Colors.orange
                        opacity:
                            workflowFlick.contentHeight > workflowFlick.height
                            ? 1.0
                            : 0.28

                        readonly property real maxContentY:
                            Math.max(
                                0,
                                workflowFlick.contentHeight - workflowFlick.height
                            )

                        readonly property real thumbTravel:
                            Math.max(0, height - workflowScrollThumb.height)

                        Rectangle {
                            id: workflowScrollThumb

                            x: 2
                            width: parent.width - 4

                            height:
                                Math.max(
                                    26,
                                    parent.height
                                    * Math.min(
                                        1,
                                        workflowFlick.height
                                        / Math.max(workflowFlick.contentHeight, 1)
                                    )
                                )

                            y:
                                workflowScrollTrack.maxContentY > 0
                                ? (
                                      workflowFlick.contentY
                                      / workflowScrollTrack.maxContentY
                                  )
                                  * workflowScrollTrack.thumbTravel
                                : 0

                            color: Colors.orange
                            opacity:
                                workflowFlick.contentHeight > workflowFlick.height
                                ? 0.92
                                : 0.24
                        }

                        MouseArea {
                            id: workflowScrollMouse

                            anchors.fill: parent
                            enabled:
                                workflowFlick.contentHeight > workflowFlick.height

                            property real dragOffset: 0

                            onPressed: function(mouse) {
                                if (mouse.y >= workflowScrollThumb.y
                                        && mouse.y <= workflowScrollThumb.y
                                                           + workflowScrollThumb.height) {
                                    dragOffset = mouse.y - workflowScrollThumb.y;
                                } else {
                                    dragOffset = workflowScrollThumb.height / 2;
                                    updateScroll(mouse.y);
                                }
                            }

                            onPositionChanged: function(mouse) {
                                if (pressed)
                                    updateScroll(mouse.y);
                            }

                            function updateScroll(pointerY) {
                                const travel = workflowScrollTrack.thumbTravel;

                                if (travel <= 0)
                                    return;

                                const thumbY = Math.max(
                                    0,
                                    Math.min(
                                        travel,
                                        pointerY - dragOffset
                                    )
                                );

                                workflowFlick.contentY =
                                    (thumbY / travel)
                                    * workflowScrollTrack.maxContentY;
                            }
                        }
                    }
                }
            }
        }
    }
}
