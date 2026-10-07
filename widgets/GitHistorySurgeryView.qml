import QtQuick
import qs.components

Rectangle {
    id: root

    required property var foldService
    required property var splitService
    required property var splitPatchService
    required property var splitLineService
    required property var absorbService
    property var historyService: null
    property var keyboardHost: null
    property string mode: "fold"

    color: Colors.dark
    border.width: 1
    border.color: Colors.red

    component InputBox: Rectangle {
        id: inputBox

        property alias text: editor.text
        property string placeholder: ""
        property color accent: Colors.cyan
        property var keyboardOwner: null

        height: 30
        color: Colors.black
        border.width: 1
        border.color: editor.activeFocus ? Colors.orange : accent
        clip: true

        TextInput {
            id: editor

            anchors {
                fill: parent
                leftMargin: 8
                rightMargin: 8
            }

            verticalAlignment: Text.AlignVCenter
            color: Colors.white
            selectionColor: Colors.magenta
            selectedTextColor: Colors.black
            font.family: "GohuFont 11 Nerd Font Mono"
            font.pixelSize: 10
            clip: true

            onActiveFocusChanged: {
                if (!inputBox.keyboardOwner)
                    return;

                if (activeFocus)
                    inputBox.keyboardOwner.activeTextEditor = editor;
                else if (
                    inputBox.keyboardOwner.activeTextEditor === editor
                )
                    inputBox.keyboardOwner.activeTextEditor = null;
            }
        }

        GohuText {
            anchors {
                fill: parent
                leftMargin: 8
                rightMargin: 8
            }
            visible: editor.text.length === 0
            verticalAlignment: Text.AlignVCenter
            text: inputBox.placeholder
            font.pixelSize: 9
            color: Colors.white
            opacity: 0.30
            elide: Text.ElideRight
        }
    }

    component SurgeryButton: Rectangle {
        id: button

        property string label: ""
        property bool enabledAction: true
        property bool selectedAction: false
        property color accent: Colors.cyan

        signal triggered()

        height: 30
        opacity: enabledAction ? 1.0 : 0.30
        color:
            selectedAction || mouse.containsMouse
            ? Colors.black
            : Colors.dark
        border.width: selectedAction ? 2 : 1
        border.color:
            selectedAction
            ? Colors.orange
            : accent

        GohuText {
            anchors.centerIn: parent
            width: parent.width - 8
            horizontalAlignment: Text.AlignHCenter
            text: button.label
            font.pixelSize: 9
            color: button.accent
            elide: Text.ElideRight
        }

        MouseArea {
            id: mouse
            anchors.fill: parent
            enabled: button.enabledAction
            hoverEnabled: true
            cursorShape:
                enabled
                ? Qt.PointingHandCursor
                : Qt.ArrowCursor
            onClicked: button.triggered()
        }
    }

    Column {
        anchors.fill: parent
        anchors.margins: 8
        spacing: 7

        Row {
            width: parent.width
            height: 30
            spacing: 6

            SurgeryButton {
                width: (parent.width - 12) / 3
                label: "FOLD"
                accent: Colors.red
                selectedAction: root.mode === "fold"
                enabledAction:
                    !foldService.executionBusy
                    && !splitService.executionBusy
                    && !splitPatchService.executionBusy
                    && !splitLineService.executionBusy
                    && !absorbService.executionBusy
                onTriggered: root.mode = "fold"
            }

            SurgeryButton {
                width: (parent.width - 12) / 3
                label: "SPLIT"
                accent: Colors.orange
                selectedAction: root.mode === "split"
                enabledAction:
                    !foldService.executionBusy
                    && !splitService.executionBusy
                    && !splitPatchService.executionBusy
                    && !splitLineService.executionBusy
                    && !absorbService.executionBusy
                onTriggered: root.mode = "split"
            }

            SurgeryButton {
                width: (parent.width - 12) / 3
                label: "ABSORB"
                accent: Colors.magenta
                selectedAction: root.mode === "absorb"
                enabledAction:
                    !foldService.executionBusy
                    && !splitService.executionBusy
                    && !splitPatchService.executionBusy
                    && !splitLineService.executionBusy
                    && !absorbService.executionBusy
                onTriggered: root.mode = "absorb"
            }
        }

        Rectangle {
            width: parent.width
            height: 50
            color: Colors.black
            border.width: 1
            border.color:
                foldService.lastError
                ? Colors.red
                : foldService.armed
                ? Colors.orange
                : Colors.cyan

            Row {
                anchors.fill: parent
                anchors.margins: 7
                spacing: 8

                Column {
                    width: parent.width - 250
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 2

                    GohuText {
                        width: parent.width
                        text: "HISTORY SURGERY // FOLD"
                        font.pixelSize: 12
                        color: Colors.red
                    }

                    GohuText {
                        width: parent.width
                        text:
                            foldService.lastError
                            ? "REFUSED // " + foldService.lastError
                            : String(foldService.state || "READY")
                        font.pixelSize: 9
                        color:
                            foldService.lastError
                            ? Colors.red
                            : foldService.armed
                            ? Colors.orange
                            : Colors.cyan
                        elide: Text.ElideRight
                    }
                }

                GohuText {
                    width: 242
                    anchors.verticalCenter: parent.verticalCenter
                    horizontalAlignment: Text.AlignRight
                    text:
                        foldService.branchName
                        ? (
                            foldService.branchName
                            + " // "
                            + String(foldService.headSha || "").slice(0, 10)
                          )
                        : "CURRENT BRANCH"
                    font.pixelSize: 9
                    color: Colors.white
                    elide: Text.ElideLeft
                }
            }
        }

        Row {
            width: parent.width
            height: 30
            spacing: 6

            InputBox {
                id: oldestInput
                width: (parent.width - 160) / 2
                placeholder: "OLDEST COMMIT SHA / REF"
                accent: Colors.cyan
                keyboardOwner: root.keyboardHost
            }

            InputBox {
                id: newestInput
                width: (parent.width - 160) / 2
                placeholder: "NEWEST COMMIT SHA / REF"
                accent: Colors.magenta
                keyboardOwner: root.keyboardHost
            }

            SurgeryButton {
                width: 148
                label:
                    foldService.previewBusy
                    ? "READING RANGE"
                    : "PREVIEW FOLD"
                accent: Colors.green
                enabledAction:
                    !foldService.previewBusy
                    && !foldService.executionBusy
                    && oldestInput.text.trim().length > 0
                    && newestInput.text.trim().length > 0
                onTriggered:
                    foldService.preview(
                        oldestInput.text.trim(),
                        newestInput.text.trim()
                    )
            }
        }

        Row {
            width: parent.width
            height: 28
            spacing: 6

            SurgeryButton {
                width: (parent.width - 6) / 2
                label: "USE SELECTED AS OLDEST"
                accent: Colors.cyan
                enabledAction:
                    root.historyService
                    && String(root.historyService.selectedSha || "").length > 0
                    && !foldService.executionBusy
                onTriggered:
                    oldestInput.text =
                        String(root.historyService.selectedSha || "")
            }

            SurgeryButton {
                width: (parent.width - 6) / 2
                label: "USE SELECTED AS NEWEST"
                accent: Colors.magenta
                enabledAction:
                    root.historyService
                    && String(root.historyService.selectedSha || "").length > 0
                    && !foldService.executionBusy
                onTriggered:
                    newestInput.text =
                        String(root.historyService.selectedSha || "")
            }
        }

        Row {
            width: parent.width
            height: parent.height - 236
            spacing: 8

            Rectangle {
                width: Math.floor(parent.width * 0.57)
                height: parent.height
                color: Colors.black
                border.width: 1
                border.color: Colors.cyan

                Column {
                    anchors.fill: parent
                    anchors.margins: 7
                    spacing: 5

                    GohuText {
                        width: parent.width
                        text:
                            "FOLD RANGE // "
                            + String(foldService.commits.length)
                            + " COMMITS"
                        font.pixelSize: 10
                        color: Colors.cyan
                    }

                    ListView {
                        width: parent.width
                        height: parent.height - 28
                        clip: true
                        spacing: 4
                        model: foldService.commits

                        delegate: Rectangle {
                            id: commitRow

                            required property int index
                            required property var modelData

                            width: ListView.view.width
                            height: 42
                            color: Colors.dark
                            border.width: 1
                            border.color:
                                index === 0
                                ? Colors.red
                                : Colors.orange

                            Row {
                                anchors.fill: parent
                                anchors.margins: 6
                                spacing: 8

                                GohuText {
                                    width: 76
                                    anchors.verticalCenter: parent.verticalCenter
                                    text:
                                        index === 0
                                        ? "KEEP"
                                        : "FOLD"
                                    font.pixelSize: 9
                                    color:
                                        index === 0
                                        ? Colors.red
                                        : Colors.orange
                                }

                                GohuText {
                                    width: parent.width - 84
                                    anchors.verticalCenter: parent.verticalCenter
                                    text:
                                        String(modelData.sha || "").slice(0, 10)
                                        + " // "
                                        + String(modelData.subject || "")
                                    font.pixelSize: 9
                                    color: Colors.white
                                    elide: Text.ElideRight
                                }
                            }
                        }

                        GohuText {
                            anchors.centerIn: parent
                            visible:
                                !foldService.previewBusy
                                && foldService.commits.length === 0
                            text:
                                "SELECT A CONTIGUOUS OLDEST → NEWEST RANGE"
                            font.pixelSize: 10
                            color: Colors.orange
                            opacity: 0.7
                        }
                    }
                }
            }

            Rectangle {
                width: parent.width - Math.floor(parent.width * 0.57) - 8
                height: parent.height
                color: Colors.black
                border.width: 1
                border.color: Colors.red

                Column {
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 7

                    GohuText {
                        width: parent.width
                        text: "FOLDED COMMIT"
                        font.pixelSize: 10
                        color: Colors.red
                    }

                    InputBox {
                        id: messageInput
                        width: parent.width
                        placeholder: "FOLDED COMMIT MESSAGE"
                        accent: Colors.red
                        keyboardOwner: root.keyboardHost

                        onTextChanged: {
                            if (text !== foldService.foldMessage)
                                foldService.setMessage(text);
                        }
                    }

                    SurgeryButton {
                        width: parent.width
                        label: "LOAD DEFAULT MESSAGE"
                        accent: Colors.cyan
                        enabledAction:
                            foldService.commits.length > 0
                            && !foldService.executionBusy
                        onTriggered:
                            messageInput.text =
                                String(
                                    (foldService.commits[0] || {}).subject
                                    || ""
                                )
                    }

                    Rectangle {
                        width: parent.width
                        height: 76
                        color: Colors.dark
                        border.width: 1
                        border.color: Colors.orange

                        GohuText {
                            anchors.fill: parent
                            anchors.margins: 7
                            text:
                                "STRICT FIRST SLICE\n"
                                + "• contiguous commits only\n"
                                + "• no merge-containing rewrite range\n"
                                + "• rehearsal before live ref movement"
                            font.pixelSize: 8
                            color: Colors.orange
                            wrapMode: Text.Wrap
                        }
                    }

                    Item {
                        width: parent.width
                        height: Math.max(0, parent.height - 232)
                    }

                    SurgeryButton {
                        width: parent.width
                        height: 34
                        label:
                            foldService.armed
                            ? "ARMED // EXACT RANGE FROZEN"
                            : "ARM FOLD"
                        accent: Colors.orange
                        selectedAction: foldService.armed
                        enabledAction:
                            foldService.commits.length >= 2
                            && messageInput.text.trim().length > 0
                            && !foldService.previewBusy
                            && !foldService.executionBusy
                        onTriggered: {
                            foldService.setMessage(
                                messageInput.text.trim()
                            );
                            foldService.arm();
                        }
                    }

                    SurgeryButton {
                        width: parent.width
                        height: 38
                        label:
                            foldService.executionBusy
                            ? "REHEARSING / FOLDING"
                            : "EXECUTE REHEARSED FOLD"
                        accent: Colors.red
                        enabledAction:
                            foldService.armed
                            && !foldService.previewBusy
                            && !foldService.executionBusy
                        onTriggered: foldService.executeArmed()
                    }
                }
            }
        }

        Rectangle {
            width: parent.width
            height: 42
            color: Colors.black
            border.width: 1
            border.color: Colors.cyan

            GohuText {
                anchors.fill: parent
                anchors.margins: 7
                verticalAlignment: Text.AlignVCenter
                text:
                    "OPERATIONS UNDO RESTORES THE EXACT PRE-FOLD BRANCH HEAD "
                    + "ONLY WHILE THE REWRITTEN REF STILL MATCHES"
                font.pixelSize: 9
                color: Colors.cyan
                elide: Text.ElideRight
            }
        }
    }

    GitHistorySplitHubView {
        anchors {
            top: parent.top
            left: parent.left
            right: parent.right
            bottom: parent.bottom
            topMargin: 45
            leftMargin: 8
            rightMargin: 8
            bottomMargin: 8
        }

        visible: root.mode === "split"
        z: 1000

        fileService: root.splitService
        hunkService: root.splitPatchService
        lineService: root.splitLineService
        historyService: root.historyService
        keyboardHost: root.keyboardHost
    }

    GitHistoryAbsorbView {
        anchors {
            top: parent.top
            left: parent.left
            right: parent.right
            bottom: parent.bottom
            topMargin: 45
            leftMargin: 8
            rightMargin: 8
            bottomMargin: 8
        }

        visible: root.mode === "absorb"
        z: 1000

        absorbService: root.absorbService
        historyService: root.historyService
        keyboardHost: root.keyboardHost
    }

    Connections {
        target: foldService
        ignoreUnknownSignals: true

        function onPreviewReady(commits) {
            if (commits.length > 0)
                messageInput.text =
                    String((commits[0] || {}).subject || "");
        }
    }
}
