import QtQuick
import qs.components

Rectangle {
    id: root

    required property var splitService
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

    component SplitButton: Rectangle {
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

    function firstCount() {
        return splitService.selectedFirstPaths().length;
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
                splitService.lastError
                ? Colors.red
                : splitService.armed
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
                        text: "HISTORY SURGERY // SPLIT BY FILE"
                        font.pixelSize: 12
                        color: Colors.orange
                    }

                    GohuText {
                        width: parent.width
                        text:
                            splitService.lastError
                            ? "REFUSED // " + splitService.lastError
                            : String(splitService.state || "READY")
                        font.pixelSize: 9
                        color:
                            splitService.lastError
                            ? Colors.red
                            : splitService.armed
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
                        splitService.branchName
                        ? (
                            splitService.branchName
                            + " // "
                            + String(splitService.headSha || "").slice(0, 10)
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
                width: parent.width - 314
                placeholder: "TARGET COMMIT SHA / REF"
                accent: Colors.orange
                keyboardOwner: root.keyboardHost
            }

            SplitButton {
                width: 148
                label: "USE SELECTED"
                accent: Colors.cyan
                enabledAction:
                    root.historyService
                    && String(root.historyService.selectedSha || "").length > 0
                    && !splitService.executionBusy
                onTriggered:
                    targetInput.text =
                        String(root.historyService.selectedSha || "")
            }

            SplitButton {
                width: 154
                label:
                    splitService.previewBusy
                    ? "READING COMMIT"
                    : "PREVIEW SPLIT"
                accent: Colors.green
                enabledAction:
                    !splitService.previewBusy
                    && !splitService.executionBusy
                    && targetInput.text.trim().length > 0
                onTriggered:
                    splitService.preview(targetInput.text.trim())
            }
        }

        Row {
            width: parent.width
            height: parent.height - 184
            spacing: 8

            Rectangle {
                width: Math.floor(parent.width * 0.55)
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
                            "FILE PARTITION // PART 1 "
                            + String(root.firstCount())
                            + " // PART 2 "
                            + String(
                                Math.max(
                                    0,
                                    splitService.files.length
                                    - root.firstCount()
                                )
                              )
                        font.pixelSize: 10
                        color: Colors.cyan
                    }

                    ListView {
                        width: parent.width
                        height: parent.height - 28
                        clip: true
                        spacing: 4
                        model: splitService.files

                        delegate: Rectangle {
                            id: fileRow

                            required property int index
                            required property var modelData

                            width: ListView.view.width
                            height: 42
                            color:
                                rowMouse.containsMouse
                                ? Colors.dark
                                : "transparent"
                            border.width: 1
                            border.color:
                                Boolean(modelData.first)
                                ? Colors.orange
                                : Colors.magenta

                            Row {
                                anchors.fill: parent
                                anchors.margins: 6
                                spacing: 8

                                GohuText {
                                    width: 72
                                    anchors.verticalCenter: parent.verticalCenter
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
                                    width: 34
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: String(modelData.status || "")
                                    font.pixelSize: 9
                                    color: Colors.cyan
                                }

                                GohuText {
                                    width: parent.width - 114
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: String(modelData.path || "")
                                    font.pixelSize: 9
                                    color: Colors.white
                                    elide: Text.ElideMiddle
                                }
                            }

                            MouseArea {
                                id: rowMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor

                                onClicked:
                                    splitService.setFirstFile(
                                        fileRow.index,
                                        !Boolean(fileRow.modelData.first)
                                    )
                            }
                        }

                        GohuText {
                            anchors.centerIn: parent
                            visible:
                                !splitService.previewBusy
                                && splitService.files.length === 0
                            text:
                                "PREVIEW A COMMIT WITH 2+ CHANGED FILES"
                            font.pixelSize: 10
                            color: Colors.orange
                            opacity: 0.7
                        }
                    }
                }
            }

            Rectangle {
                width: parent.width - Math.floor(parent.width * 0.55) - 8
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

                    SectionFrame {
                        width: parent.width
                        height: 86
                        fillColor: Colors.dark
                        borderWidth: 1
                        borderColor: Colors.orange
                        inset: 7

                        GohuText {
                            anchors.fill: parent
                            text:
                                "STRICT FILE SPLIT SLICE\n"
                                + "• one non-merge commit\n"
                                + "• both file groups must be non-empty\n"
                                + "• renames/copies refused for now\n"
                                + "• descendants replay after rehearsal"
                            font.pixelSize: 8
                            color: Colors.orange
                            wrapMode: Text.Wrap
                        }
                    }

                    Item {
                        width: parent.width
                        height: Math.max(0, parent.height - 266)
                    }

                    SplitButton {
                        width: parent.width
                        height: 34
                        label:
                            splitService.armed
                            ? "ARMED // PARTITION FROZEN"
                            : "ARM SPLIT"
                        accent: Colors.orange
                        selectedAction: splitService.armed
                        enabledAction:
                            splitService.files.length >= 2
                            && root.firstCount() > 0
                            && root.firstCount() < splitService.files.length
                            && firstMessageInput.text.trim().length > 0
                            && secondMessageInput.text.trim().length > 0
                            && !splitService.previewBusy
                            && !splitService.executionBusy
                        onTriggered: {
                            splitService.setMessages(
                                firstMessageInput.text.trim(),
                                secondMessageInput.text.trim()
                            );
                            splitService.arm();
                        }
                    }

                    SplitButton {
                        width: parent.width
                        height: 38
                        label:
                            splitService.executionBusy
                            ? "REHEARSING / SPLITTING"
                            : "EXECUTE REHEARSED SPLIT"
                        accent: Colors.red
                        enabledAction:
                            splitService.armed
                            && !splitService.previewBusy
                            && !splitService.executionBusy
                        onTriggered: splitService.executeArmed()
                    }
                }
            }
        }

        SectionFrame {
            width: parent.width
            height: 42
            fillColor: Colors.black
            borderWidth: 1
            borderColor: Colors.cyan
            inset: 7

            GohuText {
                anchors.fill: parent
                verticalAlignment: Text.AlignVCenter
                text:
                    "CLICK FILE ROWS TO TOGGLE PART 1 / PART 2 // "
                    + "OPERATIONS UNDO RESTORES THE EXACT PRE-SPLIT HEAD"
                font.pixelSize: 9
                color: Colors.cyan
                elide: Text.ElideRight
            }
        }
    }

    Connections {
        target: splitService
        ignoreUnknownSignals: true

        function onPreviewReady(files) {
            firstMessageInput.text =
                String(splitService.firstMessage || "");
            secondMessageInput.text =
                String(splitService.secondMessage || "");
        }
    }
}
