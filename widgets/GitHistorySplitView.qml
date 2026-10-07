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
        property color accent: Colors.orange
        property var keyboardOwner: null

        height: 30
        color: Colors.black
        border.width: 1
        border.color: editor.activeFocus ? Colors.cyan : accent
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
        property color accent: Colors.orange

        signal triggered()

        height: 30
        opacity: enabledAction ? 1.0 : 0.30
        color:
            selectedAction || mouse.containsMouse
            ? Colors.black
            : Colors.dark
        border.width: selectedAction ? 2 : 1
        border.color: selectedAction ? Colors.cyan : accent

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

        Rectangle {
            width: parent.width
            height: 52
            color: Colors.black
            border.width: 1
            border.color:
                splitService.lastError
                ? Colors.red
                : splitService.armed
                ? Colors.cyan
                : Colors.orange

            Row {
                anchors.fill: parent
                anchors.margins: 7
                spacing: 8

                Column {
                    width: parent.width - 270
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
                            ? Colors.cyan
                            : Colors.orange
                        elide: Text.ElideRight
                    }
                }

                GohuText {
                    width: 262
                    anchors.verticalCenter: parent.verticalCenter
                    horizontalAlignment: Text.AlignRight
                    text:
                        splitService.targetSha
                        ? (
                            String(splitService.targetSha).slice(0, 10)
                            + " // "
                            + String(splitService.targetSubject || "")
                          )
                        : "NO TARGET"
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
                    ? "READING TARGET"
                    : "PREVIEW SPLIT"
                accent: Colors.green
                enabledAction:
                    targetInput.text.trim().length > 0
                    && !splitService.previewBusy
                    && !splitService.executionBusy
                onTriggered:
                    splitService.preview(targetInput.text.trim())
            }
        }

        Row {
            width: parent.width
            height: 28
            spacing: 6

            Rectangle {
                width: (parent.width - 12) / 3
                height: 28
                color: Colors.black
                border.width: 1
                border.color: Colors.orange

                GohuText {
                    anchors.centerIn: parent
                    text: "FILE // LIVE"
                    font.pixelSize: 9
                    color: Colors.orange
                }
            }

            Rectangle {
                width: (parent.width - 12) / 3
                height: 28
                opacity: 0.30
                color: Colors.dark
                border.width: 1
                border.color: Colors.cyan

                GohuText {
                    anchors.centerIn: parent
                    text: "HUNK // LATER"
                    font.pixelSize: 9
                    color: Colors.cyan
                }
            }

            Rectangle {
                width: (parent.width - 12) / 3
                height: 28
                opacity: 0.30
                color: Colors.dark
                border.width: 1
                border.color: Colors.magenta

                GohuText {
                    anchors.centerIn: parent
                    text: "LINE // LATER"
                    font.pixelSize: 9
                    color: Colors.magenta
                }
            }
        }

        Row {
            width: parent.width
            height: parent.height - 270
            spacing: 8

            Rectangle {
                width: Math.floor(parent.width * 0.56)
                height: parent.height
                color: Colors.black
                border.width: 1
                border.color: Colors.orange

                Column {
                    anchors.fill: parent
                    anchors.margins: 7
                    spacing: 5

                    GohuText {
                        width: parent.width
                        text:
                            "TARGET FILES // "
                            + String(splitService.files.length)
                            + " // FIRST "
                            + String(splitService.firstFiles.length)
                            + " // SECOND "
                            + String(splitService.secondFiles().length)
                        font.pixelSize: 10
                        color: Colors.orange
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

                            readonly property bool inFirst:
                                splitService.selectedForFirst(
                                    String(modelData.path || "")
                                )

                            width: ListView.view.width
                            height: 42
                            color:
                                rowMouse.containsMouse
                                ? Colors.dark
                                : Colors.black
                            border.width: 1
                            border.color:
                                inFirst
                                ? Colors.cyan
                                : Colors.magenta

                            Row {
                                anchors.fill: parent
                                anchors.margins: 6
                                spacing: 7

                                GohuText {
                                    width: 70
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: fileRow.inFirst ? "FIRST" : "SECOND"
                                    font.pixelSize: 9
                                    color:
                                        fileRow.inFirst
                                        ? Colors.cyan
                                        : Colors.magenta
                                }

                                GohuText {
                                    width: 30
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: String(modelData.status || "?")
                                    font.pixelSize: 9
                                    color: Colors.orange
                                }

                                GohuText {
                                    width: parent.width - 108
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
                                enabled: !splitService.executionBusy
                                onClicked:
                                    splitService.toggleFirst(
                                        String(fileRow.modelData.path || "")
                                    )
                            }
                        }

                        GohuText {
                            anchors.centerIn: parent
                            visible:
                                !splitService.previewBusy
                                && splitService.files.length === 0
                            text:
                                "PREVIEW A COMMIT THAT CHANGES 2+ FILES"
                            font.pixelSize: 10
                            color: Colors.orange
                            opacity: 0.7
                        }
                    }
                }
            }

            Rectangle {
                width: parent.width - Math.floor(parent.width * 0.56) - 8
                height: parent.height
                color: Colors.black
                border.width: 1
                border.color: Colors.cyan

                Column {
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 7

                    GohuText {
                        width: parent.width
                        text: "REPLACEMENT COMMITS"
                        font.pixelSize: 10
                        color: Colors.cyan
                    }

                    InputBox {
                        id: firstMessageInput
                        width: parent.width
                        placeholder: "FIRST COMMIT MESSAGE"
                        accent: Colors.cyan
                        keyboardOwner: root.keyboardHost

                        onTextChanged: {
                            if (text !== splitService.firstMessage)
                                splitService.setFirstMessage(text);
                        }
                    }

                    InputBox {
                        id: secondMessageInput
                        width: parent.width
                        placeholder: "SECOND COMMIT MESSAGE"
                        accent: Colors.magenta
                        keyboardOwner: root.keyboardHost

                        onTextChanged: {
                            if (text !== splitService.secondMessage)
                                splitService.setSecondMessage(text);
                        }
                    }

                    Rectangle {
                        width: parent.width
                        height: 96
                        color: Colors.dark
                        border.width: 1
                        border.color: Colors.orange

                        GohuText {
                            anchors.fill: parent
                            anchors.margins: 7
                            text:
                                "INVARIANTS\n"
                                + "• non-empty strict FIRST subset\n"
                                + "• SECOND receives every remaining path\n"
                                + "• both preserve original author identity\n"
                                + "• replacement tree = original target tree\n"
                                + "• final tree = original HEAD tree"
                            font.pixelSize: 8
                            color: Colors.orange
                            wrapMode: Text.Wrap
                        }
                    }

                    Item {
                        width: parent.width
                        height: Math.max(0, parent.height - 264)
                    }

                    SplitButton {
                        width: parent.width
                        height: 34
                        label:
                            splitService.armed
                            ? "ARMED // FILE GROUPS FROZEN"
                            : "ARM SPLIT"
                        accent: Colors.cyan
                        selectedAction: splitService.armed
                        enabledAction:
                            splitService.files.length >= 2
                            && splitService.firstFiles.length >= 1
                            && splitService.secondFiles().length >= 1
                            && firstMessageInput.text.trim().length > 0
                            && secondMessageInput.text.trim().length > 0
                            && !splitService.previewBusy
                            && !splitService.executionBusy
                        onTriggered: {
                            splitService.setFirstMessage(
                                firstMessageInput.text.trim()
                            );
                            splitService.setSecondMessage(
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

        Rectangle {
            width: parent.width
            height: 42
            color: Colors.black
            border.width: 1
            border.color: Colors.orange

            GohuText {
                anchors.fill: parent
                anchors.margins: 7
                verticalAlignment: Text.AlignVCenter
                text:
                    "OPERATIONS UNDO RESTORES THE EXACT PRE-SPLIT HEAD "
                    + "WHILE THE REWRITTEN BRANCH STILL MATCHES"
                font.pixelSize: 9
                color: Colors.orange
                elide: Text.ElideRight
            }
        }
    }

    Connections {
        target: splitService
        ignoreUnknownSignals: true

        function onPreviewReady() {
            firstMessageInput.text =
                String(splitService.firstMessage || "");
            secondMessageInput.text =
                String(splitService.secondMessage || "");
        }
    }
}
