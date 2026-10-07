import QtQuick
import qs.components

Rectangle {
    id: root

    required property var hunkService
    property var historyService: null
    property var keyboardHost: null

    color: Colors.dark
    border.width: 1
    border.color: Colors.orange

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

    component HunkButton: Rectangle {
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
        border.color: selectedAction ? Colors.orange : accent

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

    function firstCount() {
        return hunkService.selectedHunkIndexes().length;
    }

    Column {
        anchors.fill: parent
        anchors.margins: 8
        spacing: 7

        Rectangle {
            width: parent.width
            height: 50
            color: Colors.black
            border.width: 1
            border.color:
                hunkService.lastError
                ? Colors.red
                : hunkService.armed
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
                        text: "HISTORY SURGERY // SPLIT BY HUNK"
                        font.pixelSize: 12
                        color: Colors.orange
                    }

                    GohuText {
                        width: parent.width
                        text:
                            hunkService.lastError
                            ? "REFUSED // " + hunkService.lastError
                            : String(hunkService.state || "READY")
                        font.pixelSize: 9
                        color:
                            hunkService.lastError
                            ? Colors.red
                            : hunkService.armed
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
                        hunkService.branchName
                        ? (
                            hunkService.branchName
                            + " // "
                            + String(hunkService.headSha || "").slice(0, 10)
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
                id: targetInput
                width: Math.floor((parent.width - 302) * 0.48)
                placeholder: "TARGET COMMIT SHA / REF"
                accent: Colors.orange
                keyboardOwner: root.keyboardHost
            }

            InputBox {
                id: pathInput
                width: parent.width
                    - Math.floor((parent.width - 302) * 0.48)
                    - 302
                placeholder: "PATH IN TARGET COMMIT"
                accent: Colors.cyan
                keyboardOwner: root.keyboardHost
            }

            HunkButton {
                width: 142
                label: "USE SELECTED"
                accent: Colors.cyan
                enabledAction:
                    root.historyService
                    && String(root.historyService.selectedSha || "").length > 0
                    && !hunkService.executionBusy
                onTriggered:
                    targetInput.text =
                        String(root.historyService.selectedSha || "")
            }

            HunkButton {
                width: 148
                label:
                    hunkService.previewBusy
                    ? "READING HUNKS"
                    : "PREVIEW HUNKS"
                accent: Colors.green
                enabledAction:
                    !hunkService.previewBusy
                    && !hunkService.executionBusy
                    && targetInput.text.trim().length > 0
                    && pathInput.text.trim().length > 0
                onTriggered:
                    hunkService.preview(
                        targetInput.text.trim(),
                        pathInput.text.trim()
                    )
            }
        }

        Row {
            width: parent.width
            height: parent.height - 184
            spacing: 8

            Rectangle {
                width: Math.floor(parent.width * 0.59)
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
                            "HUNK PARTITION // PART 1 "
                            + String(root.firstCount())
                            + " // TOTAL "
                            + String(hunkService.hunks.length)
                        font.pixelSize: 10
                        color: Colors.cyan
                    }

                    ListView {
                        width: parent.width
                        height: parent.height - 28
                        clip: true
                        spacing: 4
                        model: hunkService.hunks

                        delegate: Rectangle {
                            id: hunkRow

                            required property int index
                            required property var modelData

                            width: ListView.view.width
                            height: 74
                            color:
                                rowMouse.containsMouse
                                ? Colors.dark
                                : "transparent"
                            border.width: 1
                            border.color:
                                Boolean(modelData.first)
                                ? Colors.orange
                                : Colors.magenta

                            Column {
                                anchors.fill: parent
                                anchors.margins: 6
                                spacing: 3

                                Row {
                                    width: parent.width
                                    spacing: 8

                                    GohuText {
                                        width: 72
                                        text:
                                            Boolean(modelData.first)
                                            ? "PART 1"
                                            : "PART 2"
                                        font.pixelSize: 9
                                        color:
                                            Boolean(modelData.first)
                                            ? Colors.orange
                                            : Colors.magenta
                                    }

                                    GohuText {
                                        width: parent.width - 80
                                        text:
                                            String(modelData.header || "")
                                            + " // +"
                                            + String(modelData.added || 0)
                                            + " -"
                                            + String(modelData.removed || 0)
                                        font.pixelSize: 9
                                        color: Colors.white
                                        elide: Text.ElideRight
                                    }
                                }

                                GohuText {
                                    width: parent.width
                                    height: 38
                                    text: String(modelData.preview || "")
                                    font.pixelSize: 8
                                    color: Colors.cyan
                                    wrapMode: Text.WrapAnywhere
                                    elide: Text.ElideRight
                                }
                            }

                            MouseArea {
                                id: rowMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor

                                onClicked:
                                    hunkService.setFirstHunk(
                                        hunkRow.index,
                                        !Boolean(hunkRow.modelData.first)
                                    )
                            }
                        }

                        GohuText {
                            anchors.centerIn: parent
                            visible:
                                !hunkService.previewBusy
                                && hunkService.hunks.length === 0
                            text: "PREVIEW A HISTORICAL TEXT PATH"
                            font.pixelSize: 10
                            color: Colors.orange
                            opacity: 0.7
                        }
                    }
                }
            }

            Rectangle {
                width: parent.width - Math.floor(parent.width * 0.59) - 8
                height: parent.height
                color: Colors.black
                border.width: 1
                border.color: Colors.orange

                Column {
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 7

                    GohuText {
                        width: parent.width
                        text: "REPLACEMENT COMMITS"
                        font.pixelSize: 10
                        color: Colors.orange
                    }

                    InputBox {
                        id: firstMessageInput
                        width: parent.width
                        placeholder: "PART 1 COMMIT MESSAGE"
                        accent: Colors.orange
                        keyboardOwner: root.keyboardHost
                    }

                    InputBox {
                        id: secondMessageInput
                        width: parent.width
                        placeholder: "PART 2 COMMIT MESSAGE"
                        accent: Colors.magenta
                        keyboardOwner: root.keyboardHost
                    }

                    Rectangle {
                        width: parent.width
                        height: 92
                        color: Colors.dark
                        border.width: 1
                        border.color: Colors.orange

                        GohuText {
                            anchors.fill: parent
                            anchors.margins: 7
                            text:
                                "STRICT HUNK SPLIT\n"
                                + "• selected hunks -> part 1\n"
                                + "• every remaining target change -> part 2\n"
                                + "• binary / rename / copy paths refused\n"
                                + "• descendants replay only after rehearsal"
                            font.pixelSize: 8
                            color: Colors.orange
                            wrapMode: Text.Wrap
                        }
                    }

                    Item {
                        width: parent.width
                        height: Math.max(0, parent.height - 272)
                    }

                    HunkButton {
                        width: parent.width
                        height: 34
                        label:
                            hunkService.armed
                            ? "ARMED // HUNKS FROZEN"
                            : "ARM HUNK SPLIT"
                        accent: Colors.orange
                        selectedAction: hunkService.armed
                        enabledAction:
                            hunkService.hunks.length > 0
                            && hunkService.hasRemainder()
                            && firstMessageInput.text.trim().length > 0
                            && secondMessageInput.text.trim().length > 0
                            && !hunkService.previewBusy
                            && !hunkService.executionBusy
                        onTriggered: {
                            hunkService.setMessages(
                                firstMessageInput.text.trim(),
                                secondMessageInput.text.trim()
                            );
                            hunkService.arm();
                        }
                    }

                    HunkButton {
                        width: parent.width
                        height: 38
                        label:
                            hunkService.executionBusy
                            ? "REHEARSING / SPLITTING"
                            : "EXECUTE HUNK SPLIT"
                        accent: Colors.red
                        enabledAction:
                            hunkService.armed
                            && !hunkService.previewBusy
                            && !hunkService.executionBusy
                        onTriggered: hunkService.executeArmed()
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
                    "CLICK HUNKS TO TOGGLE PART 1 / PART 2 // "
                    + "OPERATIONS UNDO RESTORES THE EXACT PRE-SPLIT HEAD"
                font.pixelSize: 9
                color: Colors.cyan
                elide: Text.ElideRight
            }
        }
    }

    Connections {
        target: hunkService
        ignoreUnknownSignals: true

        function onPreviewReady(hunks) {
            firstMessageInput.text =
                String(hunkService.firstMessage || "");
            secondMessageInput.text =
                String(hunkService.secondMessage || "");
        }
    }
}
