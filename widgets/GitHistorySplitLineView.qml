import QtQuick
import qs.components

Rectangle {
    id: root

    required property var lineService
    property var historyService: null
    property var keyboardHost: null

    color: Colors.dark
    border.width: 1
    border.color: Colors.magenta

    function firstCount() {
        return lineService.selectedLineIndexes().length;
    }

    component InputBox: Rectangle {
        id: inputBox

        property alias text: editor.text
        property string placeholder: ""
        property color accent: Colors.cyan
        property var keyboardOwner: null

        height: 30
        color: Colors.black
        border.width: 1
        border.color:
            editor.activeFocus
            ? Colors.orange
            : accent
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

    component LineButton: Rectangle {
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

        Rectangle {
            width: parent.width
            height: 50
            color: Colors.black
            border.width: 1
            border.color:
                lineService.lastError
                ? Colors.red
                : lineService.armed
                ? Colors.orange
                : Colors.magenta

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
                        text: "HISTORY SURGERY // SPLIT BY LINE"
                        font.pixelSize: 12
                        color: Colors.magenta
                    }

                    GohuText {
                        width: parent.width
                        text:
                            lineService.lastError
                            ? "REFUSED // " + lineService.lastError
                            : String(lineService.state || "READY")
                        font.pixelSize: 9
                        color:
                            lineService.lastError
                            ? Colors.red
                            : lineService.armed
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
                        lineService.branchName
                        ? (
                            lineService.branchName
                            + " // "
                            + String(lineService.headSha || "").slice(0, 10)
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
                accent: Colors.magenta
                keyboardOwner: root.keyboardHost
            }

            InputBox {
                id: pathInput
                width:
                    parent.width
                    - Math.floor((parent.width - 302) * 0.48)
                    - 302
                placeholder: "MODIFIED TEXT PATH"
                accent: Colors.cyan
                keyboardOwner: root.keyboardHost
            }

            LineButton {
                width: 142
                label: "USE SELECTED"
                accent: Colors.cyan
                enabledAction:
                    root.historyService
                    && String(
                        root.historyService.selectedSha || ""
                    ).length > 0
                    && !lineService.executionBusy
                onTriggered:
                    targetInput.text =
                        String(root.historyService.selectedSha || "")
            }

            LineButton {
                width: 148
                label:
                    lineService.previewBusy
                    ? "READING LINES"
                    : "PREVIEW LINES"
                accent: Colors.green
                enabledAction:
                    !lineService.previewBusy
                    && !lineService.executionBusy
                    && targetInput.text.trim().length > 0
                    && pathInput.text.trim().length > 0
                onTriggered:
                    lineService.preview(
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
                            "LINE PARTITION // PART 1 "
                            + String(root.firstCount())
                            + " // TOTAL "
                            + String(lineService.lines.length)
                        font.pixelSize: 10
                        color: Colors.cyan
                    }

                    ListView {
                        id: lineList

                        width: parent.width
                        height: parent.height - 28
                        clip: true
                        spacing: 4
                        model: lineService.lines

                        delegate: Rectangle {
                            id: lineRow

                            required property int index
                            required property var modelData

                            width: lineList.width
                            height:
                                String(modelData.kind || "") === "replace"
                                ? 58
                                : 42
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
                                anchors.margins: 5
                                spacing: 2

                                Row {
                                    width: parent.width
                                    spacing: 7

                                    GohuText {
                                        width: 66
                                        text:
                                            Boolean(modelData.first)
                                            ? "PART 1"
                                            : "PART 2"
                                        font.pixelSize: 8
                                        color:
                                            Boolean(modelData.first)
                                            ? Colors.orange
                                            : Colors.magenta
                                    }

                                    GohuText {
                                        width: 78
                                        text:
                                            String(
                                                modelData.kind || "change"
                                            ).toUpperCase()
                                        font.pixelSize: 8
                                        color:
                                            String(modelData.kind || "")
                                            === "delete"
                                            ? Colors.red
                                            : String(modelData.kind || "")
                                              === "insert"
                                            ? Colors.green
                                            : Colors.cyan
                                    }

                                    GohuText {
                                        width: parent.width - 158
                                        text:
                                            "OLD "
                                            + String(modelData.oldLine || 0)
                                            + " // NEW "
                                            + String(modelData.newLine || 0)
                                        font.pixelSize: 8
                                        color: Colors.white
                                        horizontalAlignment: Text.AlignRight
                                    }
                                }

                                GohuText {
                                    width: parent.width
                                    text:
                                        String(modelData.kind || "")
                                        === "insert"
                                        ? "+ " + String(modelData.newText || "")
                                        : String(modelData.kind || "")
                                          === "delete"
                                        ? "- " + String(modelData.oldText || "")
                                        : (
                                            "- "
                                            + String(modelData.oldText || "")
                                            + "  →  + "
                                            + String(modelData.newText || "")
                                          )
                                    font.pixelSize: 8
                                    color:
                                        Boolean(modelData.first)
                                        ? Colors.orange
                                        : Colors.cyan
                                    elide: Text.ElideRight
                                }
                            }

                            MouseArea {
                                id: rowMouse

                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor

                                onClicked:
                                    lineService.setFirstLine(
                                        lineRow.index,
                                        !Boolean(lineRow.modelData.first)
                                    )
                            }
                        }

                        GohuText {
                            anchors.centerIn: parent
                            visible:
                                !lineService.previewBusy
                                && lineService.lines.length === 0
                            text: "PREVIEW A MODIFIED HISTORICAL TEXT PATH"
                            font.pixelSize: 10
                            color: Colors.magenta
                            opacity: 0.7
                        }

                        NeonScrollBar {
                            flickable: lineList
                        }
                    }
                }
            }

            Rectangle {
                width:
                    parent.width
                    - Math.floor(parent.width * 0.59)
                    - 8
                height: parent.height
                color: Colors.black
                border.width: 1
                border.color: Colors.magenta

                Column {
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 7

                    GohuText {
                        width: parent.width
                        text: "REPLACEMENT COMMITS"
                        font.pixelSize: 10
                        color: Colors.magenta
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
                        height: 104
                        fillColor: Colors.dark
                        borderWidth: 1
                        borderColor: Colors.magenta
                        inset: 7

                        GohuText {
                            anchors.fill: parent
                            text:
                                "STRICT LINE SPLIT\n"
                                + "• selected atomic edits -> part 1\n"
                                + "• every unselected edit -> part 2\n"
                                + "• other target paths -> part 2\n"
                                + "• simple modified text paths only\n"
                                + "• descendants replay only after rehearsal"
                            font.pixelSize: 8
                            color: Colors.magenta
                            wrapMode: Text.Wrap
                        }
                    }

                    Item {
                        width: parent.width
                        height: Math.max(0, parent.height - 284)
                    }

                    LineButton {
                        width: parent.width
                        height: 34
                        label:
                            lineService.armed
                            ? "ARMED // LINES FROZEN"
                            : "ARM LINE SPLIT"
                        accent: Colors.orange
                        selectedAction: lineService.armed
                        enabledAction:
                            lineService.lines.length > 0
                            && lineService.hasRemainder()
                            && firstMessageInput.text.trim().length > 0
                            && secondMessageInput.text.trim().length > 0
                            && !lineService.previewBusy
                            && !lineService.executionBusy
                        onTriggered: {
                            lineService.setMessages(
                                firstMessageInput.text.trim(),
                                secondMessageInput.text.trim()
                            );
                            lineService.arm();
                        }
                    }

                    LineButton {
                        width: parent.width
                        height: 38
                        label:
                            lineService.executionBusy
                            ? "REHEARSING / SPLITTING"
                            : "EXECUTE LINE SPLIT"
                        accent: Colors.red
                        enabledAction:
                            lineService.armed
                            && !lineService.previewBusy
                            && !lineService.executionBusy
                        onTriggered: lineService.executeArmed()
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
                    "OPERATIONS UNDO RESTORES THE EXACT PRE-SPLIT BRANCH HEAD "
                    + "ONLY WHILE THE REWRITTEN REF STILL MATCHES"
                font.pixelSize: 9
                color: Colors.cyan
                elide: Text.ElideRight
            }
        }
    }

    Connections {
        target: lineService
        ignoreUnknownSignals: true

        function onPreviewReady(rows) {
            if (rows.length <= 0)
                return;

            firstMessageInput.text =
                String(lineService.firstMessage || "");
            secondMessageInput.text =
                String(lineService.secondMessage || "");
        }
    }
}
