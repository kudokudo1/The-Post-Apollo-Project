import QtQuick
import QtQuick.Effects
import qs.components

Item {
    id: root

    property var repositoryService: null
    property var gitService: null
    property var branchWorkspaceService: null
    property var keyboardHost: null

    property int selectedRemoteIndex: -1
    property string selectedRemoteName: ""

    function takeEditorFocus(editor) {
        if (!root.keyboardHost)
            return;

        if (editor.activeFocus)
            root.keyboardHost.activeTextEditor = editor;
        else if (root.keyboardHost.activeTextEditor === editor)
            root.keyboardHost.activeTextEditor = null;
    }

    function selectRemote(index, row) {
        root.selectedRemoteIndex = index;
        root.selectedRemoteName = String((row || {}).name || "");
        remoteNameInput.text = root.selectedRemoteName;
        remoteUrlInput.text = String((row || {}).url || "");
    }


    component SectionLabel: GohuText {
        font.pixelSize: 12
        color: Colors.magenta
    }

    component MetaLabel: GohuText {
        font.pixelSize: 10
        color: Colors.cyan
    }

    component GreenLabel: GohuText {
        font.pixelSize: 10
        color: Colors.green
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

    component EditorBox: Rectangle {
        id: editorBox

        property alias text: input.text
        property string placeholder: ""
        property color accent: Colors.cyan
        property var keyboardOwner: null

        height: 30
        color: Colors.black
        border.width: 1
        border.color: input.activeFocus ? Colors.orange : accent

        TextInput {
            id: input

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
            font.pixelSize: 9
            clip: true

            onActiveFocusChanged: {
                if (!editorBox.keyboardOwner)
                    return;

                if (activeFocus)
                    editorBox.keyboardOwner.activeTextEditor = input;
                else if (
                    editorBox.keyboardOwner.activeTextEditor === input
                )
                    editorBox.keyboardOwner.activeTextEditor = null;
            }
        }

        GohuText {
            anchors {
                left: parent.left
                verticalCenter: parent.verticalCenter
                leftMargin: 8
            }
            visible: input.text.length === 0
            text: editorBox.placeholder
            font.pixelSize: 8
            color: Colors.white
            opacity: 0.30
        }
    }

    Column {
        anchors.fill: parent
        spacing: 10

        Rectangle {
            width: parent.width
            height: 66
            color: Colors.dark
            border.width: 1
            border.color: Colors.orange

            Row {
                anchors {
                    fill: parent
                    margins: 9
                }
                spacing: 12

                Column {
                    width: parent.width - 330
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 4

                    SectionLabel {
                        text: "REPOSITORY // LOCAL CONFIGURATION"
                    }

                    GohuText {
                        width: parent.width
                        text:
                            root.gitService
                            ? String(root.gitService.repoRoot || "NO LOCAL REPOSITORY")
                            : "NO LOCAL REPOSITORY"
                        font.pixelSize: 9
                        color: Colors.cyan
                        elide: Text.ElideMiddle
                    }
                }

                MiniButton {
                    width: 104
                    anchors.verticalCenter: parent.verticalCenter
                    label: "LAZYGIT"
                    accent: Colors.magenta
                    enabledAction:
                        root.gitService
                        && root.gitService.repoIsLocal
                    onTriggered: root.gitService.launchLazygit()
                }

                MiniButton {
                    width: 98
                    anchors.verticalCenter: parent.verticalCenter
                    label:
                        root.repositoryService
                        && root.repositoryService.refreshing
                        ? "READING"
                        : "REFRESH"
                    accent: Colors.cyan
                    enabledAction:
                        root.repositoryService
                        && !root.repositoryService.refreshing
                        && !root.repositoryService.actionBusy
                    onTriggered: {
                        root.repositoryService.refresh();
                        if (root.branchWorkspaceService)
                            root.branchWorkspaceService.refresh();
                    }
                }

                Rectangle {
                    width: 104
                    height: 28
                    anchors.verticalCenter: parent.verticalCenter
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.green

                    GohuText {
                        anchors.centerIn: parent
                        text:
                            root.repositoryService
                            ? String(root.repositoryService.remotes.length)
                              + " REMOTES"
                            : "0 REMOTES"
                        font.pixelSize: 8
                        color: Colors.green
                    }
                }
            }
        }

        Row {
            width: parent.width
            height: 336
            spacing: 10

            Rectangle {
                width: (parent.width - 10) / 2
                height: parent.height
                color: Colors.dark
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
                        height: 22

                        MetaLabel {
                            width: parent.width - 90
                            text: "REMOTES"
                        }

                        GohuText {
                            width: 90
                            horizontalAlignment: Text.AlignRight
                            text:
                                root.selectedRemoteName
                                ? root.selectedRemoteName
                                : "SELECT"
                            font.pixelSize: 8
                            color: Colors.cyan
                            elide: Text.ElideRight
                        }
                    }

                    Flickable {
                        width: parent.width
                        height: 154
                        clip: true
                        contentWidth: width
                        contentHeight: remoteColumn.implicitHeight
                        boundsBehavior: Flickable.StopAtBounds

                        Column {
                            id: remoteColumn
                            width: parent.width
                            spacing: 3

                            GohuText {
                                visible:
                                    root.repositoryService
                                    && root.repositoryService.remotes.length === 0
                                width: parent.width
                                topPadding: 18
                                text: "NO REMOTES"
                                horizontalAlignment: Text.AlignHCenter
                                font.pixelSize: 10
                                color: Colors.white
                                opacity: 0.44
                            }

                            Repeater {
                                model:
                                    root.repositoryService
                                    ? root.repositoryService.remotes
                                    : []

                                Rectangle {
                                    id: remoteRow
                                    required property int index
                                    required property var modelData

                                    width: remoteColumn.width
                                    height: 43
                                    color:
                                        remoteMouse.containsMouse
                                        || root.selectedRemoteIndex === index
                                        ? Colors.black
                                        : "transparent"
                                    border.width:
                                        root.selectedRemoteIndex === index
                                        ? 1 : 0
                                    border.color: Colors.magenta

                                    Column {
                                        anchors {
                                            left: parent.left
                                            right: fetchButton.left
                                            verticalCenter: parent.verticalCenter
                                            leftMargin: 7
                                            rightMargin: 7
                                        }
                                        spacing: 2

                                        GohuText {
                                            width: parent.width
                                            text: String(remoteRow.modelData.name || "")
                                            font.pixelSize: 9
                                            color: Colors.magenta
                                        }

                                        GohuText {
                                            width: parent.width
                                            text: String(remoteRow.modelData.url || "")
                                            font.pixelSize: 7
                                            color: Colors.white
                                            opacity: 0.66
                                            elide: Text.ElideMiddle
                                        }
                                    }

                                    MiniButton {
                                        id: fetchButton
                                        width: 66
                                        height: 26
                                        anchors {
                                            right: parent.right
                                            rightMargin: 5
                                            verticalCenter: parent.verticalCenter
                                        }
                                        label: "FETCH"
                                        accent: Colors.green
                                        enabledAction:
                                            root.repositoryService
                                            && !root.repositoryService.actionBusy
                                        onTriggered:
                                            root.repositoryService.fetchRemote(
                                                remoteRow.modelData.name
                                            )
                                    }

                                    MouseArea {
                                        id: remoteMouse
                                        anchors {
                                            left: parent.left
                                            right: fetchButton.left
                                            top: parent.top
                                            bottom: parent.bottom
                                        }
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked:
                                            root.selectRemote(
                                                remoteRow.index,
                                                remoteRow.modelData
                                            )
                                    }
                                }
                            }
                        }
                    }

                    Row {
                        width: parent.width
                        height: 30
                        spacing: 6

                        EditorBox {
                            id: remoteNameInput
                            width: 118
                            placeholder: "REMOTE NAME"
                            accent: Colors.magenta
                            keyboardOwner: root.keyboardHost
                        }

                        EditorBox {
                            id: remoteUrlInput
                            width: parent.width - 118 - 6
                            placeholder: "REMOTE URL"
                            accent: Colors.cyan
                            keyboardOwner: root.keyboardHost
                        }
                    }

                    Row {
                        width: parent.width
                        height: 28
                        spacing: 6

                        MiniButton {
                            width: (parent.width - 6) / 2
                            label: "ADD REMOTE"
                            accent: Colors.green
                            enabledAction:
                                root.repositoryService
                                && remoteNameInput.text.trim().length > 0
                                && remoteUrlInput.text.trim().length > 0
                                && !root.repositoryService.actionBusy
                            onTriggered:
                                root.repositoryService.addRemote(
                                    remoteNameInput.text,
                                    remoteUrlInput.text
                                )
                        }

                        MiniButton {
                            width: (parent.width - 6) / 2
                            label: "SET URL"
                            accent: Colors.orange
                            enabledAction:
                                root.repositoryService
                                && root.selectedRemoteName.length > 0
                                && remoteUrlInput.text.trim().length > 0
                                && !root.repositoryService.actionBusy
                            onTriggered:
                                root.repositoryService.setRemoteUrl(
                                    root.selectedRemoteName,
                                    remoteUrlInput.text
                                )
                        }
                    }

                    GohuText {
                        width: parent.width
                        text:
                            root.repositoryService
                            ? (
                                root.repositoryService.lastError
                                ? "REFUSED // " + root.repositoryService.lastError
                                : root.repositoryService.actionBusy
                                ? root.repositoryService.actionName + " // RUNNING"
                                : root.repositoryService.actionStatus
                              )
                            : "NO REPOSITORY SERVICE"
                        font.pixelSize: 8
                        color:
                            root.repositoryService
                            && root.repositoryService.lastError
                            ? Colors.red
                            : Colors.cyan
                        elide: Text.ElideRight
                    }
                }
            }

            Rectangle {
                width: (parent.width - 10) / 2
                height: parent.height
                color: Colors.dark
                border.width: 1
                border.color: Colors.cyan

                Column {
                    anchors {
                        fill: parent
                        margins: 8
                    }
                    spacing: 6

                    Row {
                        width: parent.width
                        height: 22

                        SectionLabel {
                            width: parent.width - 100
                            text: "WORKTREES"
                        }

                        GohuText {
                            width: 100
                            horizontalAlignment: Text.AlignRight
                            text:
                                root.branchWorkspaceService
                                ? String(root.branchWorkspaceService.worktrees.length)
                                  + " TOTAL"
                                : "0 TOTAL"
                            font.pixelSize: 8
                            color: Colors.cyan
                        }
                    }

                    Flickable {
                        width: parent.width
                        height: parent.height - 28
                        clip: true
                        contentWidth: width
                        contentHeight: worktreeColumn.implicitHeight
                        boundsBehavior: Flickable.StopAtBounds

                        Column {
                            id: worktreeColumn
                            width: parent.width
                            spacing: 4

                            Repeater {
                                model:
                                    root.branchWorkspaceService
                                    ? root.branchWorkspaceService.worktrees
                                    : []

                                Rectangle {
                                    required property var modelData

                                    width: worktreeColumn.width
                                    height: 54
                                    color: Colors.black
                                    border.width: 1
                                    border.color:
                                        Number(modelData.dirtyCount || 0) > 0
                                        ? Colors.orange
                                        : Colors.green

                                    Column {
                                        anchors {
                                            fill: parent
                                            margins: 7
                                        }
                                        spacing: 3

                                        Row {
                                            width: parent.width
                                            height: 15

                                            GohuText {
                                                width: parent.width - 90
                                                text:
                                                    String(modelData.branch || "")
                                                    || "DETACHED"
                                                font.pixelSize: 9
                                                color: Colors.white
                                                elide: Text.ElideRight
                                            }

                                            GohuText {
                                                width: 90
                                                horizontalAlignment: Text.AlignRight
                                                text:
                                                    Number(modelData.dirtyCount || 0) > 0
                                                    ? String(modelData.dirtyCount)
                                                      + " CHANGES"
                                                    : "CLEAN"
                                                font.pixelSize: 8
                                                color:
                                                    Number(modelData.dirtyCount || 0) > 0
                                                    ? Colors.orange
                                                    : Colors.green
                                            }
                                        }

                                        GohuText {
                                            width: parent.width
                                            text: String(modelData.path || "")
                                            font.pixelSize: 7
                                            color: Colors.cyan
                                            elide: Text.ElideMiddle
                                        }

                                        GohuText {
                                            width: parent.width
                                            text:
                                                "HEAD "
                                                + String(modelData.head || "").slice(0, 10)
                                                + (
                                                    modelData.locked
                                                    ? "  //  LOCKED"
                                                    : ""
                                                  )
                                            font.pixelSize: 7
                                            color: Colors.white
                                            opacity: 0.52
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        Rectangle {
            width: parent.width
            height: parent.height - 412
            color: Colors.dark
            border.width: 1
            border.color: Colors.green

            Row {
                anchors {
                    fill: parent
                    margins: 8
                }
                spacing: 10

                Rectangle {
                    width: 456
                    height: parent.height
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.green

                    Column {
                        anchors {
                            fill: parent
                            margins: 7
                        }
                        spacing: 5

                        GreenLabel {
                            text: "LOCAL CONFIG"
                        }

                        Flickable {
                            width: parent.width
                            height: parent.height - 22
                            clip: true
                            contentWidth: width
                            contentHeight: configColumn.implicitHeight
                            boundsBehavior: Flickable.StopAtBounds

                            Column {
                                id: configColumn
                                width: parent.width
                                spacing: 3

                                Repeater {
                                    model:
                                        root.repositoryService
                                        ? root.repositoryService.configRows
                                        : []

                                    Rectangle {
                                        id: configRow
                                        required property var modelData

                                        width: configColumn.width
                                        height: 30
                                        color:
                                            configMouse.containsMouse
                                            ? Colors.dark
                                            : "transparent"

                                        GohuText {
                                            anchors {
                                                left: parent.left
                                                verticalCenter: parent.verticalCenter
                                            }
                                            width: 190
                                            text: String(configRow.modelData.key || "")
                                            font.pixelSize: 8
                                            color: Colors.green
                                            elide: Text.ElideRight
                                        }

                                        GohuText {
                                            anchors {
                                                left: parent.left
                                                right: parent.right
                                                verticalCenter: parent.verticalCenter
                                                leftMargin: 196
                                            }
                                            text: String(configRow.modelData.value || "")
                                            font.pixelSize: 8
                                            color: Colors.white
                                            elide: Text.ElideRight
                                        }

                                        MouseArea {
                                            id: configMouse
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: {
                                                configKeyInput.text =
                                                    String(configRow.modelData.key || "");
                                                configValueInput.text =
                                                    String(configRow.modelData.value || "");
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                Column {
                    width: parent.width - 466
                    height: parent.height
                    spacing: 6

                    MetaLabel {
                        text: "SET REPO-LOCAL CONFIG"
                    }

                    EditorBox {
                        id: configKeyInput
                        width: parent.width
                        placeholder: "KEY // e.g. fetch.prune"
                        accent: Colors.green
                        keyboardOwner: root.keyboardHost
                    }

                    EditorBox {
                        id: configValueInput
                        width: parent.width
                        placeholder: "VALUE // e.g. true"
                        accent: Colors.cyan
                        keyboardOwner: root.keyboardHost
                    }

                    Row {
                        width: parent.width
                        height: 30
                        spacing: 6

                        MiniButton {
                            width: (parent.width - 6) / 2
                            label: "SET CONFIG"
                            accent: Colors.green
                            enabledAction:
                                root.repositoryService
                                && configKeyInput.text.trim().length > 0
                                && configValueInput.text.trim().length > 0
                                && !root.repositoryService.actionBusy
                            onTriggered:
                                root.repositoryService.setConfig(
                                    configKeyInput.text,
                                    configValueInput.text
                                )
                        }

                        MiniButton {
                            width: (parent.width - 6) / 2
                            label: "FETCH ORIGIN"
                            accent: Colors.orange
                            enabledAction:
                                root.repositoryService
                                && !root.repositoryService.actionBusy
                            onTriggered:
                                root.repositoryService.fetchRemote("origin")
                        }
                    }
                }
            }
        }
    }
}
