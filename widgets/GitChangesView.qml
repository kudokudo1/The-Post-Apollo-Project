import QtQuick
import QtQuick.Effects
import qs.components

Item {
    id: root

    property var changesService: null
    property var gitService: null
    property var keyboardHost: null


    component SectionLabel: GohuText {
        font.pixelSize: 12
        color: Colors.magenta
    }

    component MetaLabel: GohuText {
        font.pixelSize: 10
        color: Colors.cyan
    }

    component OrangeLabel: GohuText {
        font.pixelSize: 10
        color: Colors.orange
    }

    component MiniButton: Rectangle {
        id: button

        property string label: ""
        property color accent: Colors.cyan
        property bool enabledAction: true
        signal triggered()

        height: 28
        color:
            mouse.pressed
            ? accent
            : mouse.containsMouse
            ? Colors.dark
            : Colors.black
        border.width: 1
        border.color: accent
        opacity: enabledAction ? 1.0 : 0.28

        GohuText {
            anchors.centerIn: parent
            text: button.label
            font.pixelSize: 9
            color:
                mouse.pressed
                ? Colors.black
                : mouse.containsMouse
                ? Colors.orange
                : button.accent
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
        spacing: 10

        Rectangle {
            width: parent.width
            height: 76
            color: Colors.dark
            border.width: 1
            border.color: Colors.cyan

            Row {
                anchors {
                    fill: parent
                    margins: 9
                }
                spacing: 12

                Column {
                    width: parent.width - 392
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 5

                    SectionLabel {
                        text: "WORKTREE // CHANGES"
                    }

                    GohuText {
                        width: parent.width
                        text:
                            root.gitService
                            ? (
                                String(root.gitService.branch || "DETACHED")
                                + "  //  "
                                + String(root.gitService.repoRoot || "")
                              )
                            : "NO REPOSITORY"
                        font.pixelSize: 9
                        color: Colors.white
                        elide: Text.ElideMiddle
                    }
                }

                Row {
                    width: 268
                    height: 28
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 6

                    Rectangle {
                        width: 82
                        height: 28
                        color: Colors.black
                        border.width: 1
                        border.color: Colors.green

                        GohuText {
                            anchors.centerIn: parent
                            text:
                                "STAGED "
                                + String(
                                    root.changesService
                                    ? root.changesService.stagedCount
                                    : 0
                                )
                            font.pixelSize: 8
                            color: Colors.green
                        }
                    }

                    Rectangle {
                        width: 82
                        height: 28
                        color: Colors.black
                        border.width: 1
                        border.color: Colors.orange

                        GohuText {
                            anchors.centerIn: parent
                            text:
                                "WORK "
                                + String(
                                    root.changesService
                                    ? root.changesService.unstagedCount
                                    : 0
                                )
                            font.pixelSize: 8
                            color: Colors.orange
                        }
                    }

                    Rectangle {
                        width: 92
                        height: 28
                        color: Colors.black
                        border.width: 1
                        border.color: Colors.magenta

                        GohuText {
                            anchors.centerIn: parent
                            text:
                                "NEW "
                                + String(
                                    root.changesService
                                    ? root.changesService.untrackedCount
                                    : 0
                                )
                            font.pixelSize: 8
                            color: Colors.magenta
                        }
                    }
                }

                MiniButton {
                    width: 88
                    anchors.verticalCenter: parent.verticalCenter
                    label:
                        root.changesService
                        && root.changesService.refreshing
                        ? "READING"
                        : "REFRESH"
                    accent: Colors.cyan
                    enabledAction:
                        root.changesService
                        && !root.changesService.refreshing
                        && !root.changesService.actionBusy
                    onTriggered: root.changesService.refresh()
                }
            }
        }

        Row {
            width: parent.width
            height: parent.height - 210
            spacing: 10

            Rectangle {
                width: 408
                height: parent.height
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
                        width: parent.width
                        height: 28
                        spacing: 6

                        OrangeLabel {
                            width: 114
                            anchors.verticalCenter: parent.verticalCenter
                            text: "CHANGED FILES"
                        }

                        Item {
                            width: parent.width - 114 - 196
                            height: 1
                        }

                        MiniButton {
                            width: 92
                            label: "STAGE ALL"
                            accent: Colors.green
                            enabledAction:
                                root.changesService
                                && root.changesService.changedCount > 0
                                && !root.changesService.actionBusy
                            onTriggered: root.changesService.stageAll()
                        }

                        MiniButton {
                            width: 98
                            label: "UNSTAGE ALL"
                            accent: Colors.orange
                            enabledAction:
                                root.changesService
                                && root.changesService.stagedCount > 0
                                && !root.changesService.actionBusy
                            onTriggered: root.changesService.unstageAll()
                        }
                    }

                    Flickable {
                        id: fileFlick

                        width: parent.width
                        height: parent.height - 34
                        clip: true
                        contentWidth: width
                        contentHeight: fileColumn.implicitHeight
                        boundsBehavior: Flickable.StopAtBounds

                        Column {
                            id: fileColumn
                            width: parent.width
                            spacing: 4

                            GohuText {
                                visible:
                                    root.changesService
                                    && root.changesService.changedCount === 0
                                width: parent.width
                                topPadding: 20
                                text: "WORKTREE CLEAN"
                                horizontalAlignment: Text.AlignHCenter
                                font.pixelSize: 11
                                color: Colors.cyan
                                opacity: 0.72
                            }

                            Repeater {
                                model:
                                    root.changesService
                                    ? root.changesService.files
                                    : []

                                Rectangle {
                                    id: fileRow
                                    required property int index
                                    required property var modelData

                                    width: fileColumn.width
                                    height: 40
                                    color:
                                        fileMouse.containsMouse
                                        || (
                                            root.changesService
                                            && root.changesService.previewPath
                                               === String(modelData.path || "")
                                        )
                                        ? Colors.black
                                        : "transparent"
                                    border.width: 1
                                    border.color:
                                        modelData.staged
                                        ? Colors.green
                                        : modelData.untracked
                                        ? Colors.magenta
                                        : Colors.orange

                                    Rectangle {
                                        width: 4
                                        anchors {
                                            left: parent.left
                                            top: parent.top
                                            bottom: parent.bottom
                                        }
                                        color:
                                            modelData.staged
                                            ? Colors.green
                                            : modelData.untracked
                                            ? Colors.magenta
                                            : Colors.orange
                                    }

                                    Column {
                                        anchors {
                                            left: parent.left
                                            right: actionButton.left
                                            verticalCenter: parent.verticalCenter
                                            leftMargin: 10
                                            rightMargin: 8
                                        }
                                        spacing: 2

                                        GohuText {
                                            width: parent.width
                                            text: String(fileRow.modelData.path || "")
                                            font.pixelSize: 9
                                            color: Colors.white
                                            elide: Text.ElideMiddle
                                        }

                                        GohuText {
                                            width: parent.width
                                            text:
                                                String(fileRow.modelData.label || "CHANGED")
                                                + "  //  "
                                                + String(fileRow.modelData.indexStatus || " ")
                                                + String(fileRow.modelData.worktreeStatus || " ")
                                            font.pixelSize: 7
                                            color:
                                                fileRow.modelData.staged
                                                ? Colors.green
                                                : fileRow.modelData.untracked
                                                ? Colors.magenta
                                                : Colors.orange
                                        }
                                    }

                                    MiniButton {
                                        id: actionButton
                                        width: 78
                                        height: 26
                                        anchors {
                                            right: parent.right
                                            rightMargin: 6
                                            verticalCenter: parent.verticalCenter
                                        }
                                        label:
                                            fileRow.modelData.staged
                                            && !fileRow.modelData.unstaged
                                            ? "UNSTAGE"
                                            : fileRow.modelData.staged
                                            ? "+ STAGE"
                                            : "STAGE"
                                        accent:
                                            fileRow.modelData.staged
                                            ? Colors.orange
                                            : Colors.green
                                        enabledAction:
                                            root.changesService
                                            && !root.changesService.actionBusy
                                        onTriggered: {
                                            if (
                                                fileRow.modelData.staged
                                                && !fileRow.modelData.unstaged
                                            ) {
                                                root.changesService.unstage(
                                                    fileRow.modelData.path
                                                );
                                            } else {
                                                root.changesService.stage(
                                                    fileRow.modelData.path
                                                );
                                            }
                                        }
                                    }

                                    MouseArea {
                                        id: fileMouse
                                        anchors {
                                            left: parent.left
                                            right: actionButton.left
                                            top: parent.top
                                            bottom: parent.bottom
                                        }
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked:
                                            root.changesService.preview(
                                                fileRow.modelData.path
                                            )
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Rectangle {
                width: parent.width - 418
                height: parent.height
                color: Colors.black
                border.width: 1
                border.color: Colors.magenta

                Column {
                    anchors {
                        fill: parent
                        margins: 8
                    }
                    spacing: 6

                    Row {
                        width: parent.width
                        height: 20

                        MetaLabel {
                            width: parent.width - 110
                            text:
                                root.changesService
                                && root.changesService.previewPath
                                ? "DIFF // "
                                  + root.changesService.previewPath
                                : "DIFF PREVIEW"
                        }

                        GohuText {
                            width: 110
                            text:
                                root.changesService
                                && root.changesService.previewBusy
                                ? "READING"
                                : "STAGED + WORKTREE"
                            horizontalAlignment: Text.AlignRight
                            font.pixelSize: 7
                            color: Colors.cyan
                        }
                    }

                    Flickable {
                        width: parent.width
                        height: parent.height - 26
                        clip: true
                        contentWidth: width
                        contentHeight: diffText.implicitHeight
                        boundsBehavior: Flickable.StopAtBounds

                        GohuText {
                            id: diffText
                            width: parent.width
                            text:
                                root.changesService
                                ? root.changesService.previewText
                                : "NO CHANGE SERVICE"
                            font.pixelSize: 9
                            color: Colors.white
                            wrapMode: Text.WrapAnywhere
                        }
                    }
                }
            }
        }

        Rectangle {
            width: parent.width
            height: 104
            color: Colors.dark
            border.width: 1
            border.color: Colors.green

            Column {
                anchors {
                    fill: parent
                    margins: 8
                }
                spacing: 6

                Row {
                    width: parent.width
                    height: 32
                    spacing: 8

                    Rectangle {
                        width: parent.width - 370
                        height: 32
                        color: Colors.black
                        border.width: 1
                        border.color:
                            commitInput.activeFocus
                            ? Colors.orange
                            : Colors.cyan

                        TextInput {
                            id: commitInput

                            anchors {
                                fill: parent
                                leftMargin: 9
                                rightMargin: 9
                            }
                            verticalAlignment: Text.AlignVCenter
                            text: ""
                            color: Colors.white
                            selectionColor: Colors.magenta
                            selectedTextColor: Colors.black
                            font.family: "GohuFont 11 Nerd Font Mono"
                            font.pixelSize: 10
                            clip: true

                            onActiveFocusChanged: {
                                if (!root.keyboardHost)
                                    return;

                                if (activeFocus)
                                    root.keyboardHost.activeTextEditor = commitInput;
                                else if (
                                    root.keyboardHost.activeTextEditor
                                    === commitInput
                                )
                                    root.keyboardHost.activeTextEditor = null;
                            }

                            Keys.onReturnPressed: function(event) {
                                if (
                                    root.changesService
                                    && root.changesService.stagedCount > 0
                                    && text.trim().length > 0
                                    && !root.changesService.actionBusy
                                )
                                    root.changesService.commit(text);

                                event.accepted = true;
                            }
                        }

                        GohuText {
                            anchors {
                                left: parent.left
                                verticalCenter: parent.verticalCenter
                                leftMargin: 9
                            }
                            visible: commitInput.text.length === 0
                            text: "COMMIT MESSAGE..."
                            font.pixelSize: 9
                            color: Colors.white
                            opacity: 0.34
                        }
                    }

                    MiniButton {
                        width: 112
                        height: 32
                        label: "COMMIT STAGED"
                        accent: Colors.green
                        enabledAction:
                            root.changesService
                            && root.changesService.stagedCount > 0
                            && commitInput.text.trim().length > 0
                            && !root.changesService.actionBusy
                        onTriggered:
                            root.changesService.commit(commitInput.text)
                    }

                    MiniButton {
                        width: 112
                        height: 32
                        label: "STASH ALL"
                        accent: Colors.magenta
                        enabledAction:
                            root.changesService
                            && root.changesService.changedCount > 0
                            && !root.changesService.actionBusy
                        onTriggered:
                            root.changesService.stash(
                                commitInput.text.trim().length > 0
                                ? commitInput.text
                                : "Post-Apollo stash"
                            )
                    }

                    MiniButton {
                        width: 122
                        height: 32
                        label: "POP STASH"
                        accent: Colors.orange
                        enabledAction:
                            root.changesService
                            && !root.changesService.actionBusy
                        onTriggered: root.changesService.stashPop()
                    }
                }

                GohuText {
                    width: parent.width
                    text:
                        root.changesService
                        ? (
                            root.changesService.lastError
                            ? "REFUSED // " + root.changesService.lastError
                            : root.changesService.actionBusy
                            ? root.changesService.actionName + " // RUNNING"
                            : root.changesService.actionStatus
                          )
                        : "NO CHANGE SERVICE"
                    font.pixelSize: 9
                    color:
                        root.changesService
                        && root.changesService.lastError
                        ? Colors.red
                        : Colors.cyan
                    elide: Text.ElideRight
                }
            }
        }
    }

    Connections {
        target: root.changesService

        function onActionFinished(action, success, detail) {
            if (success && String(action || "") === "COMMIT")
                commitInput.text = "";
        }
    }
}
