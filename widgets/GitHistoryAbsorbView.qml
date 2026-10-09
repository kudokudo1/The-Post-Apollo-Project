import QtQuick
import qs.components

Rectangle {
    id: root

    required property var absorbService
    property var historyService: null
    property var keyboardHost: null

    color: Colors.dark
    border.width: 1
    border.color: Colors.magenta

    component InputBox: Rectangle {
        id: inputBox

        property alias text: editor.text
        property string placeholder: ""
        property color accent: Colors.magenta
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

    component AbsorbButton: Rectangle {
        id: button

        property string label: ""
        property bool enabledAction: true
        property bool selectedAction: false
        property color accent: Colors.magenta

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
                absorbService.lastError
                ? Colors.red
                : absorbService.armed
                ? Colors.orange
                : Colors.magenta

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
                        text: "HISTORY SURGERY // ABSORB STAGED"
                        font.pixelSize: 12
                        color: Colors.magenta
                    }

                    GohuText {
                        width: parent.width
                        text:
                            absorbService.lastError
                            ? "REFUSED // " + absorbService.lastError
                            : String(absorbService.state || "READY")
                        font.pixelSize: 9
                        color:
                            absorbService.lastError
                            ? Colors.red
                            : absorbService.armed
                            ? Colors.orange
                            : Colors.cyan
                        elide: Text.ElideRight
                    }
                }

                GohuText {
                    width: 262
                    anchors.verticalCenter: parent.verticalCenter
                    horizontalAlignment: Text.AlignRight
                    text:
                        absorbService.branchName
                        ? (
                            absorbService.branchName
                            + " // "
                            + String(absorbService.headSha || "").slice(0, 10)
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
                placeholder: "EARLIER TARGET COMMIT SHA / REF"
                accent: Colors.magenta
                keyboardOwner: root.keyboardHost
            }

            AbsorbButton {
                width: 148
                label: "USE SELECTED"
                accent: Colors.cyan
                enabledAction:
                    root.historyService
                    && String(root.historyService.selectedSha || "").length > 0
                    && !absorbService.executionBusy
                onTriggered:
                    targetInput.text =
                        String(root.historyService.selectedSha || "")
            }

            AbsorbButton {
                width: 154
                label:
                    absorbService.previewBusy
                    ? "READING STAGED"
                    : "PREVIEW ABSORB"
                accent: Colors.green
                enabledAction:
                    targetInput.text.trim().length > 0
                    && !absorbService.previewBusy
                    && !absorbService.executionBusy
                onTriggered:
                    absorbService.preview(targetInput.text.trim())
            }
        }

        Rectangle {
            width: parent.width
            height: 62
            color: Colors.black
            border.width: 1
            border.color: Colors.cyan

            Grid {
                anchors.fill: parent
                anchors.margins: 7
                columns: 2
                columnSpacing: 12
                rowSpacing: 4

                GohuText {
                    width: 112
                    text: "TARGET"
                    font.pixelSize: 9
                    color: Colors.cyan
                }

                GohuText {
                    width: parent.width - 124
                    text:
                        absorbService.targetSha
                        ? (
                            String(absorbService.targetSha).slice(0, 10)
                            + " // "
                            + String(absorbService.targetSubject || "")
                          )
                        : "NO TARGET"
                    font.pixelSize: 9
                    color: Colors.white
                    elide: Text.ElideRight
                }

                GohuText {
                    width: 112
                    text: "PATCH"
                    font.pixelSize: 9
                    color: Colors.cyan
                }

                GohuText {
                    width: parent.width - 124
                    text:
                        absorbService.patchBytes > 0
                        ? (
                            String(absorbService.patchBytes)
                            + " BYTES // SHA256 "
                            + String(absorbService.fingerprint || "").slice(0, 16)
                          )
                        : "NO STAGED PATCH"
                    font.pixelSize: 9
                    color: Colors.white
                    elide: Text.ElideRight
                }
            }
        }

        Row {
            width: parent.width
            height: parent.height - 235
            spacing: 8

            Rectangle {
                width: Math.floor(parent.width * 0.56)
                height: parent.height
                color: Colors.black
                border.width: 1
                border.color: Colors.magenta

                Column {
                    anchors.fill: parent
                    anchors.margins: 7
                    spacing: 5

                    GohuText {
                        width: parent.width
                        text:
                            "STAGED FILES // "
                            + String(absorbService.files.length)
                        font.pixelSize: 10
                        color: Colors.magenta
                    }

                    ListView {
                        width: parent.width
                        height: parent.height - 28
                        clip: true
                        spacing: 4
                        model: absorbService.files

                        delegate: Rectangle {
                            id: fileRow
                            required property var modelData

                            width: ListView.view.width
                            height: 34
                            color: Colors.dark
                            border.width: 1
                            border.color: Colors.magenta

                            GohuText {
                                anchors {
                                    fill: parent
                                    leftMargin: 7
                                    rightMargin: 7
                                }
                                verticalAlignment: Text.AlignVCenter
                                text: String(fileRow.modelData || "")
                                font.pixelSize: 9
                                color: Colors.white
                                elide: Text.ElideMiddle
                            }
                        }

                        GohuText {
                            anchors.centerIn: parent
                            visible:
                                !absorbService.previewBusy
                                && absorbService.files.length === 0
                            text:
                                "STAGE TRACKED CHANGES, THEN PREVIEW"
                            font.pixelSize: 10
                            color: Colors.orange
                            opacity: 0.7
                        }
                    }
                }
            }

            SectionFrame {
                width: parent.width - Math.floor(parent.width * 0.56) - 8
                height: parent.height
                fillColor: Colors.black
                borderWidth: 1
                borderColor: Colors.orange
                inset: 8

                Column {
                    anchors.fill: parent
                    spacing: 7

                    GohuText {
                        width: parent.width
                        text: "STRICT FIRST SLICE"
                        font.pixelSize: 10
                        color: Colors.orange
                    }

                    GohuText {
                        width: parent.width
                        text:
                            "• staged tracked changes only\n"
                            + "• no unstaged changes\n"
                            + "• no untracked files\n"
                            + "• no conflicts\n"
                            + "• earlier non-merge target\n"
                            + "• patch ≤ 512 KiB"
                        font.pixelSize: 8
                        color: Colors.orange
                        wrapMode: Text.Wrap
                    }

                    SectionFrame {
                        width: parent.width
                        height: 70
                        fillColor: Colors.dark
                        borderWidth: 1
                        borderColor: Colors.cyan
                        inset: 7

                        GohuText {
                            anchors.fill: parent
                            text:
                                "UNDO CONTRACT\n"
                                + "RESTORE OLD HEAD + EXACT STAGED PATCH "
                                + "BACK INTO THE INDEX"
                            font.pixelSize: 8
                            color: Colors.cyan
                            wrapMode: Text.Wrap
                        }
                    }

                    Item {
                        width: parent.width
                        height: Math.max(0, parent.height - 246)
                    }

                    AbsorbButton {
                        width: parent.width
                        height: 34
                        label:
                            absorbService.armed
                            ? "ARMED // PATCH + TARGET FROZEN"
                            : "ARM ABSORB"
                        accent: Colors.orange
                        selectedAction: absorbService.armed
                        enabledAction:
                            absorbService.patchBytes > 0
                            && absorbService.targetSha
                            && !absorbService.previewBusy
                            && !absorbService.executionBusy
                        onTriggered: absorbService.arm()
                    }

                    AbsorbButton {
                        width: parent.width
                        height: 38
                        label:
                            absorbService.executionBusy
                            ? "REHEARSING / ABSORBING"
                            : "EXECUTE REHEARSED ABSORB"
                        accent: Colors.red
                        enabledAction:
                            absorbService.armed
                            && !absorbService.previewBusy
                            && !absorbService.executionBusy
                        onTriggered: absorbService.executeArmed()
                    }
                }
            }
        }

        SectionFrame {
            width: parent.width
            height: 42
            fillColor: Colors.black
            borderWidth: 1
            borderColor: Colors.magenta
            inset: 7

            GohuText {
                anchors.fill: parent
                verticalAlignment: Text.AlignVCenter
                text:
                    "ABSORB REHEARSES A FIXUP + AUTOSQUASH IN A TEMP WORKTREE "
                    + "BEFORE THE LIVE BRANCH OR INDEX CAN CHANGE"
                font.pixelSize: 9
                color: Colors.magenta
                elide: Text.ElideRight
            }
        }
    }
}
