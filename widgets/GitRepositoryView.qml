import QtQuick
import QtQuick.Effects
import qs.components

Item {
    id: root

    property var repositoryService: null
    property var gitService: null
    property var branchWorkspaceService: null
    property var keyboardHost: null

    property string subMode: "remotes"

    property int selectedRemoteIndex: -1
    property string selectedRemoteName: ""
    property string selectedRemoteBranch: ""
    property string selectedTag: ""
    property string tagMode: "lightweight"
    property string selectedWorktreePath: ""
    property bool selectedWorktreeLocked: false
    property string projectFileKind: "ignore"
    property int selectedProjectLine: -1
    property string armedAction: ""

    function selectRemote(index, row) {
        const data = row || {};
        root.selectedRemoteIndex = index;
        root.selectedRemoteName = String(data.name || "");
        remoteNameInput.text = root.selectedRemoteName;
        remoteUrlInput.text = String(data.url || "");
        pushUrlInput.text = String(data.pushUrl || "");
        fetchSpecInput.text = String(data.fetchSpec || "");
        pushSpecInput.text = String(data.pushSpec || "");
        root.selectedRemoteBranch = "";
        root.armedAction = "";
    }

    function remoteBranchRows() {
        if (!root.repositoryService)
            return [];

        const rows = root.repositoryService.remoteBranches || [];

        if (!root.selectedRemoteName)
            return rows;

        const out = [];

        for (let i = 0; i < rows.length; ++i) {
            const row = rows[i] || {};
            if (String(row.remote || "") === root.selectedRemoteName)
                out.push(row);
        }

        return out;
    }

    function armOrRun(key, callback) {
        if (root.armedAction !== key) {
            root.armedAction = key;
            return;
        }

        root.armedAction = "";
        callback();
    }

    function projectLines() {
        if (!root.repositoryService)
            return [];

        return root.projectFileKind === "attributes"
            ? root.repositoryService.attributeLines
            : root.repositoryService.ignoreLines;
    }

    function cycleTagMode() {
        if (root.tagMode === "lightweight")
            root.tagMode = "annotated";
        else if (root.tagMode === "annotated")
            root.tagMode = "signed";
        else
            root.tagMode = "lightweight";
    }

    function tagModeLabel() {
        if (root.tagMode === "annotated")
            return "ANNOTATED";
        if (root.tagMode === "signed")
            return "SIGNED";
        return "LIGHTWEIGHT";
    }

    component SectionLabel: GohuText {
        font.pixelSize: 14
        color: Colors.magenta
    }

    component MiniButton: Rectangle {
        id: button

        property string label: ""
        property color accent: Colors.cyan
        property bool enabledAction: true
        property bool selected: false
        signal triggered()

        height: 28
        color:
            mouse.pressed
            ? accent
            : selected
            ? Colors.dark
            : mouse.containsMouse
            ? Colors.dark
            : Colors.black
        border.width: selected ? 2 : 1
        border.color: accent
        opacity: enabledAction ? 1.0 : 0.26

        GohuText {
            anchors.centerIn: parent
            text: button.label
            font.pixelSize: 10
            color:
                mouse.pressed
                ? Colors.black
                : selected
                ? Colors.white
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
            font.pixelSize: 11
            clip: true

            onActiveFocusChanged: {
                if (!editorBox.keyboardOwner)
                    return;

                if (activeFocus)
                    editorBox.keyboardOwner.activeTextEditor = editor;
                else if (
                    editorBox.keyboardOwner.activeTextEditor === editor
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
            visible: editor.text.length === 0
            text: editorBox.placeholder
            font.pixelSize: 10
            color: Colors.white
            opacity: 0.30
        }
    }

    Column {
        anchors.fill: parent
        spacing: 8

        Rectangle {
            width: parent.width
            height: 62
            color: Colors.dark
            border.width: 1
            border.color: Colors.orange

            Row {
                anchors {
                    fill: parent
                    margins: 8
                }
                spacing: 8

                Column {
                    width: parent.width - 236
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 4

                    SectionLabel {
                        text: "REPOSITORY // MECHANICS"
                    }

                    GohuText {
                        width: parent.width
                        text:
                            root.gitService
                            ? String(root.gitService.repoRoot || "NO LOCAL REPOSITORY")
                            : "NO LOCAL REPOSITORY"
                        font.pixelSize: 10
                        color: Colors.cyan
                        elide: Text.ElideMiddle
                    }
                }

                MiniButton {
                    width: 106
                    anchors.verticalCenter: parent.verticalCenter
                    label: "LAZYGIT"
                    accent: Colors.magenta
                    enabledAction:
                        root.gitService
                        && root.gitService.repoIsLocal
                    onTriggered: root.gitService.launchLazygit()
                }

                MiniButton {
                    width: 114
                    anchors.verticalCenter: parent.verticalCenter
                    label:
                        root.repositoryService
                        && root.repositoryService.refreshing
                        ? "READING"
                        : "REFRESH ALL"
                    accent: Colors.green
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
            }
        }

        Row {
            width: parent.width
            height: 34
            spacing: 5

            Repeater {
                model: [
                    { key: "remotes", label: "REMOTES", color: Colors.magenta },
                    { key: "tags", label: "TAGS", color: Colors.orange },
                    { key: "worktrees", label: "WORKTREES", color: Colors.cyan },
                    { key: "config", label: "CONFIG", color: Colors.green },
                    { key: "files", label: "FILES", color: Colors.yellow },
                    { key: "hooks", label: "HOOKS", color: Colors.blue },
                    { key: "health", label: "HEALTH", color: Colors.red }
                ]

                MiniButton {
                    required property var modelData
                    width:
                        (
                            parent.width
                            - parent.spacing * 6
                        ) / 7
                    height: 34
                    label: modelData.label
                    accent: modelData.color
                    selected: root.subMode === modelData.key
                    onTriggered: {
                        root.subMode = modelData.key;
                        root.armedAction = "";
                    }
                }
            }
        }

        Item {
            width: parent.width
            height: parent.height - 154

            // ===== REMOTES ===============================================
            Row {
                anchors.fill: parent
                spacing: 8
                visible: root.subMode === "remotes"

                Rectangle {
                    width: 360
                    height: parent.height
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.magenta

                    Column {
                        anchors {
                            fill: parent
                            margins: 7
                        }
                        spacing: 5

                        GohuText {
                            width: parent.width
                            text:
                                "REMOTES // "
                                + String(
                                    root.repositoryService
                                    ? root.repositoryService.remotes.length
                                    : 0
                                  )
                            font.pixelSize: 12
                            color: Colors.magenta
                        }

                        Flickable {
                            id: repositoryScroll1
                            width: parent.width
                            height: parent.height - 24
                            clip: true
                            contentWidth: width
                            contentHeight: remoteColumn.implicitHeight
                            boundsBehavior: Flickable.StopAtBounds

                            Column {
                                id: remoteColumn
                                width: parent.width
                                spacing: 3

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
                                        height: 58
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
                                                fill: parent
                                                margins: 7
                                            }
                                            spacing: 2

                                            GohuText {
                                                width: parent.width
                                                text:
                                                    String(
                                                        remoteRow.modelData.name
                                                        || ""
                                                    )
                                                font.pixelSize: 11
                                                color: Colors.magenta
                                            }

                                            GohuText {
                                                width: parent.width
                                                text:
                                                    "FETCH // "
                                                    + String(
                                                        remoteRow.modelData.url
                                                        || ""
                                                      )
                                                font.pixelSize: 9
                                                color: Colors.white
                                                elide: Text.ElideMiddle
                                            }

                                            GohuText {
                                                width: parent.width
                                                text:
                                                    "PUSH  // "
                                                    + String(
                                                        remoteRow.modelData.pushUrl
                                                        || ""
                                                      )
                                                font.pixelSize: 9
                                                color: Colors.cyan
                                                elide: Text.ElideMiddle
                                            }
                                        }

                                        MouseArea {
                                            id: remoteMouse
                                            anchors.fill: parent
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
                        
                            NeonScrollBar {
                                flickable: repositoryScroll1
                            }
}
                    }
                }

                Rectangle {
                    width: parent.width - 368
                    height: parent.height
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.cyan

                    Column {
                        anchors {
                            fill: parent
                            margins: 7
                        }
                        spacing: 5

                        Row {
                            width: parent.width
                            height: 30
                            spacing: 5

                            EditorBox {
                                id: remoteNameInput
                                width: 160
                                placeholder: "REMOTE NAME"
                                accent: Colors.magenta
                                keyboardOwner: root.keyboardHost
                            }

                            MiniButton {
                                width: 76
                                height: 30
                                label: "FETCH"
                                accent: Colors.green
                                enabledAction:
                                    root.selectedRemoteName
                                    && root.repositoryService
                                    && !root.repositoryService.actionBusy
                                onTriggered:
                                    root.repositoryService.fetchRemote(
                                        root.selectedRemoteName
                                    )
                            }

                            MiniButton {
                                width: 76
                                height: 30
                                label: "PRUNE"
                                accent: Colors.orange
                                enabledAction:
                                    root.selectedRemoteName
                                    && root.repositoryService
                                    && !root.repositoryService.actionBusy
                                onTriggered:
                                    root.repositoryService.pruneRemote(
                                        root.selectedRemoteName
                                    )
                            }

                            MiniButton {
                                width: 88
                                height: 30
                                label: "SYNC HEAD"
                                accent: Colors.cyan
                                enabledAction:
                                    root.selectedRemoteName
                                    && root.repositoryService
                                    && !root.repositoryService.actionBusy
                                onTriggered:
                                    root.repositoryService.syncRemoteHead(
                                        root.selectedRemoteName
                                    )
                            }

                            MiniButton {
                                width: 94
                                height: 30
                                label:
                                    root.armedAction === "remove-remote"
                                    ? "CONFIRM"
                                    : "REMOVE"
                                accent: Colors.red
                                enabledAction:
                                    root.selectedRemoteName
                                    && root.repositoryService
                                    && !root.repositoryService.actionBusy
                                onTriggered:
                                    root.armOrRun(
                                        "remove-remote",
                                        function() {
                                            root.repositoryService.removeRemote(
                                                root.selectedRemoteName,
                                                true
                                            );
                                            root.selectedRemoteIndex = -1;
                                            root.selectedRemoteName = "";
                                        }
                                    )
                            }

                            MiniButton {
                                width:
                                    parent.width
                                    - 160
                                    - 76
                                    - 76
                                    - 88
                                    - 94
                                    - 25
                                height: 30
                                label: "ADD / RENAME"
                                accent: Colors.cyan
                                enabledAction:
                                    root.repositoryService
                                    && remoteNameInput.text.trim().length > 0
                                    && !root.repositoryService.actionBusy
                                onTriggered: {
                                    if (root.selectedRemoteName
                                            && remoteNameInput.text.trim()
                                               !== root.selectedRemoteName) {
                                        root.repositoryService.renameRemote(
                                            root.selectedRemoteName,
                                            remoteNameInput.text.trim()
                                        );
                                        root.selectedRemoteName =
                                            remoteNameInput.text.trim();
                                    } else if (!root.selectedRemoteName
                                               && remoteUrlInput.text.trim()) {
                                        root.repositoryService.addRemote(
                                            remoteNameInput.text.trim(),
                                            remoteUrlInput.text.trim()
                                        );
                                    }
                                }
                            }
                        }

                        Row {
                            width: parent.width
                            height: 30
                            spacing: 5

                            EditorBox {
                                id: remoteUrlInput
                                width: parent.width - 112
                                placeholder: "FETCH URL"
                                accent: Colors.cyan
                                keyboardOwner: root.keyboardHost
                            }

                            MiniButton {
                                width: 107
                                height: 30
                                label: "SET FETCH URL"
                                accent: Colors.cyan
                                enabledAction:
                                    root.selectedRemoteName
                                    && remoteUrlInput.text.trim().length > 0
                                    && root.repositoryService
                                onTriggered:
                                    root.repositoryService.setRemoteUrl(
                                        root.selectedRemoteName,
                                        remoteUrlInput.text.trim()
                                    )
                            }
                        }

                        Row {
                            width: parent.width
                            height: 30
                            spacing: 5

                            EditorBox {
                                id: pushUrlInput
                                width: parent.width - 112
                                placeholder: "PUSH URL"
                                accent: Colors.orange
                                keyboardOwner: root.keyboardHost
                            }

                            MiniButton {
                                width: 107
                                height: 30
                                label: "SET PUSH URL"
                                accent: Colors.orange
                                enabledAction:
                                    root.selectedRemoteName
                                    && pushUrlInput.text.trim().length > 0
                                    && root.repositoryService
                                onTriggered:
                                    root.repositoryService.setPushUrl(
                                        root.selectedRemoteName,
                                        pushUrlInput.text.trim()
                                    )
                            }
                        }

                        Row {
                            width: parent.width
                            height: 30
                            spacing: 5

                            EditorBox {
                                id: fetchSpecInput
                                width: (parent.width - 112 - 5) / 2
                                placeholder: "FETCH REFSPEC"
                                accent: Colors.green
                                keyboardOwner: root.keyboardHost
                            }

                            EditorBox {
                                id: pushSpecInput
                                width: (parent.width - 112 - 5) / 2
                                placeholder: "PUSH REFSPEC"
                                accent: Colors.magenta
                                keyboardOwner: root.keyboardHost
                            }

                            MiniButton {
                                width: 107
                                height: 30
                                label: "SAVE SPECS"
                                accent: Colors.green
                                enabledAction:
                                    root.selectedRemoteName
                                    && root.repositoryService
                                onTriggered: {
                                    if (fetchSpecInput.text.trim())
                                        root.repositoryService.setFetchSpec(
                                            root.selectedRemoteName,
                                            fetchSpecInput.text.trim()
                                        );
                                    if (pushSpecInput.text.trim())
                                        root.repositoryService.setPushSpec(
                                            root.selectedRemoteName,
                                            pushSpecInput.text.trim()
                                        );
                                }
                            }
                        }

                        Rectangle {
                            width: parent.width
                            height: 1
                            color: Colors.cyan
                            opacity: 0.22
                        }

                        GohuText {
                            width: parent.width
                            text:
                                "REMOTE BRANCHES // "
                                + String(root.remoteBranchRows().length)
                            font.pixelSize: 11
                            color: Colors.cyan
                        }

                        Flickable {
                            id: repositoryScroll2
                            width: parent.width
                            height: parent.height - 190
                            clip: true
                            contentWidth: width
                            contentHeight: remoteBranchColumn.implicitHeight
                            boundsBehavior: Flickable.StopAtBounds

                            Column {
                                id: remoteBranchColumn
                                width: parent.width
                                spacing: 3

                                Repeater {
                                    model: root.remoteBranchRows()

                                    Rectangle {
                                        id: remoteBranchRow
                                        required property var modelData

                                        width: remoteBranchColumn.width
                                        height: 34
                                        color:
                                            remoteBranchMouse.containsMouse
                                            || root.selectedRemoteBranch
                                               === String(modelData.name || "")
                                            ? Colors.dark
                                            : "transparent"
                                        border.width:
                                            root.selectedRemoteBranch
                                            === String(modelData.name || "")
                                            ? 1 : 0
                                        border.color: Colors.orange

                                        GohuText {
                                            anchors {
                                                left: parent.left
                                                verticalCenter:
                                                    parent.verticalCenter
                                            }
                                            width: parent.width - 98
                                            text:
                                                String(
                                                    remoteBranchRow.modelData.name
                                                    || ""
                                                )
                                                + " // "
                                                + String(
                                                    remoteBranchRow.modelData.shortSha
                                                    || ""
                                                )
                                            font.pixelSize: 10
                                            color: Colors.white
                                            elide: Text.ElideMiddle
                                        }

                                        MiniButton {
                                            width: 92
                                            height: 26
                                            anchors {
                                                right: parent.right
                                                verticalCenter:
                                                    parent.verticalCenter
                                            }
                                            label:
                                                root.armedAction
                                                === "delete-rbranch:"
                                                   + String(
                                                       remoteBranchRow.modelData.name
                                                       || ""
                                                     )
                                                ? "CONFIRM"
                                                : "DELETE"
                                            accent: Colors.red
                                            enabledAction:
                                                root.repositoryService
                                                && !root.repositoryService.actionBusy
                                            onTriggered: {
                                                const full = String(
                                                    remoteBranchRow.modelData.name
                                                    || ""
                                                );
                                                const slash = full.indexOf("/");
                                                if (slash <= 0)
                                                    return;
                                                const remote = full.slice(0, slash);
                                                const branchName = full.slice(slash + 1);
                                                root.armOrRun(
                                                    "delete-rbranch:" + full,
                                                    function() {
                                                        root.repositoryService
                                                            .deleteRemoteBranch(
                                                                remote,
                                                                branchName,
                                                                true
                                                            );
                                                    }
                                                );
                                            }
                                        }

                                        MouseArea {
                                            id: remoteBranchMouse
                                            anchors {
                                                left: parent.left
                                                right: parent.right
                                                rightMargin: 98
                                                top: parent.top
                                                bottom: parent.bottom
                                            }
                                            hoverEnabled: true
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked:
                                                root.selectedRemoteBranch =
                                                    String(
                                                        remoteBranchRow.modelData.name
                                                        || ""
                                                    )
                                        }
                                    }
                                }
                            }
                        
                            NeonScrollBar {
                                flickable: repositoryScroll2
                            }
}
                    }
                }
            }

            // ===== TAGS ==================================================
            Row {
                anchors.fill: parent
                spacing: 8
                visible: root.subMode === "tags"

                Rectangle {
                    width: 470
                    height: parent.height
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.orange

                    Flickable {
                        id: repositoryScroll3
                        anchors {
                            fill: parent
                            margins: 7
                        }
                        clip: true
                        contentWidth: width
                        contentHeight: tagColumn.implicitHeight
                        boundsBehavior: Flickable.StopAtBounds

                        Column {
                            id: tagColumn
                            width: parent.width
                            spacing: 3

                            Repeater {
                                model:
                                    root.repositoryService
                                    ? root.repositoryService.tags
                                    : []

                                Rectangle {
                                    id: tagRow
                                    required property var modelData

                                    width: tagColumn.width
                                    height: 48
                                    color:
                                        tagMouse.containsMouse
                                        || root.selectedTag
                                           === String(modelData.name || "")
                                        ? Colors.black
                                        : "transparent"
                                    border.width:
                                        root.selectedTag
                                        === String(modelData.name || "")
                                        ? 1 : 0
                                    border.color: Colors.orange

                                    Column {
                                        anchors {
                                            fill: parent
                                            margins: 7
                                        }
                                        spacing: 2

                                        GohuText {
                                            width: parent.width
                                            text:
                                                String(tagRow.modelData.name || "")
                                                + " // "
                                                + String(
                                                    tagRow.modelData.shortSha || ""
                                                  )
                                            font.pixelSize: 11
                                            color: Colors.orange
                                        }

                                        GohuText {
                                            width: parent.width
                                            text:
                                                String(
                                                    tagRow.modelData.subject || ""
                                                )
                                            font.pixelSize: 9
                                            color: Colors.white
                                            elide: Text.ElideRight
                                        }
                                    }

                                    MouseArea {
                                        id: tagMouse
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            root.selectedTag =
                                                String(
                                                    tagRow.modelData.name || ""
                                                );
                                            tagNameInput.text =
                                                root.selectedTag;
                                        }
                                    }
                                }
                            }
                        }
                    
                        NeonScrollBar {
                            flickable: repositoryScroll3
                        }
}
                }

                Rectangle {
                    width: parent.width - 478
                    height: parent.height
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.magenta

                    Column {
                        anchors {
                            fill: parent
                            margins: 8
                        }
                        spacing: 7

                        SectionLabel {
                            text: "TAG OPERATIONS"
                        }

                        EditorBox {
                            id: tagNameInput
                            width: parent.width
                            placeholder: "TAG NAME"
                            accent: Colors.orange
                            keyboardOwner: root.keyboardHost
                        }

                        EditorBox {
                            id: tagTargetInput
                            width: parent.width
                            placeholder: "TARGET // HEAD OR SHA"
                            accent: Colors.cyan
                            keyboardOwner: root.keyboardHost
                            text: "HEAD"
                        }

                        Row {
                            width: parent.width
                            height: 30
                            spacing: 6

                            MiniButton {
                                width: 136
                                height: 30
                                label:
                                    "MODE "
                                    + root.tagModeLabel()
                                accent:
                                    root.tagMode === "signed"
                                    ? Colors.magenta
                                    : root.tagMode === "annotated"
                                    ? Colors.orange
                                    : Colors.cyan
                                onTriggered: root.cycleTagMode()
                            }

                            EditorBox {
                                id: tagMessageInput
                                width: parent.width - 142
                                placeholder:
                                    root.tagMode === "lightweight"
                                    ? "MESSAGE // UNUSED FOR LIGHTWEIGHT"
                                    : "TAG MESSAGE"
                                accent: Colors.green
                                keyboardOwner: root.keyboardHost
                            }
                        }

                        MiniButton {
                            width: parent.width
                            label:
                                "CREATE "
                                + root.tagModeLabel()
                                + " TAG"
                            accent: Colors.green
                            enabledAction:
                                root.repositoryService
                                && tagNameInput.text.trim().length > 0
                            onTriggered:
                                root.repositoryService.createTag(
                                    tagNameInput.text.trim(),
                                    tagTargetInput.text.trim(),
                                    root.tagMode,
                                    tagMessageInput.text
                                )
                        }

                        EditorBox {
                            id: tagRemoteInput
                            width: parent.width
                            placeholder: "REMOTE FOR TAG PUSH"
                            accent: Colors.magenta
                            keyboardOwner: root.keyboardHost
                            text: "origin"
                        }

                        Row {
                            width: parent.width
                            height: 30
                            spacing: 6

                            MiniButton {
                                width: (parent.width - 6) / 2
                                height: 30
                                label: "PUSH SELECTED TAG"
                                accent: Colors.magenta
                                enabledAction:
                                    root.selectedTag
                                    && tagRemoteInput.text.trim()
                                    && root.repositoryService
                                onTriggered:
                                    root.repositoryService.pushTag(
                                        tagRemoteInput.text.trim(),
                                        root.selectedTag
                                    )
                            }

                            MiniButton {
                                width: (parent.width - 6) / 2
                                height: 30
                                label: "PUSH ALL TAGS"
                                accent: Colors.cyan
                                enabledAction:
                                    tagRemoteInput.text.trim()
                                    && root.repositoryService
                                onTriggered:
                                    root.repositoryService.pushAllTags(
                                        tagRemoteInput.text.trim()
                                    )
                            }
                        }

                        Row {
                            width: parent.width
                            height: 30
                            spacing: 6

                            MiniButton {
                                width: (parent.width - 6) / 2
                                height: 30
                                label:
                                    root.armedAction === "delete-tag"
                                    ? "CONFIRM LOCAL"
                                    : "DELETE LOCAL TAG"
                                accent: Colors.red
                                enabledAction:
                                    root.selectedTag
                                    && root.repositoryService
                                onTriggered:
                                    root.armOrRun(
                                        "delete-tag",
                                        function() {
                                            root.repositoryService.deleteTag(
                                                root.selectedTag,
                                                true
                                            );
                                            root.selectedTag = "";
                                        }
                                    )
                            }

                            MiniButton {
                                width: (parent.width - 6) / 2
                                height: 30
                                label:
                                    root.armedAction === "delete-remote-tag"
                                    ? "CONFIRM REMOTE"
                                    : "DELETE REMOTE TAG"
                                accent: Colors.red
                                enabledAction:
                                    root.selectedTag
                                    && tagRemoteInput.text.trim()
                                    && root.repositoryService
                                onTriggered:
                                    root.armOrRun(
                                        "delete-remote-tag",
                                        function() {
                                            root.repositoryService
                                                .deleteRemoteTag(
                                                    tagRemoteInput.text.trim(),
                                                    root.selectedTag,
                                                    true
                                                );
                                        }
                                    )
                            }
                        }
                    }
                }
            }

            // ===== WORKTREES + SUBMODULES ================================
            Row {
                anchors.fill: parent
                spacing: 8
                visible: root.subMode === "worktrees"

                Rectangle {
                    width: 560
                    height: parent.height
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.cyan

                    Column {
                        anchors {
                            fill: parent
                            margins: 7
                        }
                        spacing: 5

                        Row {
                            width: parent.width
                            height: 28

                            GohuText {
                                width: parent.width - 110
                                anchors.verticalCenter: parent.verticalCenter
                                text:
                                    "WORKTREES // "
                                    + String(
                                        root.branchWorkspaceService
                                        ? root.branchWorkspaceService.worktrees.length
                                        : 0
                                      )
                                font.pixelSize: 12
                                color: Colors.cyan
                            }

                            MiniButton {
                                width: 110
                                label: "PRUNE STALE"
                                accent: Colors.orange
                                enabledAction:
                                    root.repositoryService
                                    && !root.repositoryService.actionBusy
                                onTriggered:
                                    root.repositoryService.pruneWorktrees()
                            }
                        }

                        Flickable {
                            id: repositoryScroll4
                            width: parent.width
                            height: parent.height - 34
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
                                        id: worktreeRow
                                        required property var modelData

                                        width: worktreeColumn.width
                                        height: 68
                                        color:
                                            worktreeMouse.containsMouse
                                            || root.selectedWorktreePath
                                               === String(modelData.path || "")
                                            ? Colors.black
                                            : "transparent"
                                        border.width:
                                            root.selectedWorktreePath
                                            === String(modelData.path || "")
                                            ? 1 : 0
                                        border.color:
                                            Number(modelData.dirtyCount || 0) > 0
                                            ? Colors.orange
                                            : Colors.green

                                        Column {
                                            anchors {
                                                left: parent.left
                                                right: lockButton.left
                                                verticalCenter:
                                                    parent.verticalCenter
                                                leftMargin: 7
                                                rightMargin: 7
                                            }
                                            spacing: 3

                                            GohuText {
                                                width: parent.width
                                                text:
                                                    String(
                                                        worktreeRow.modelData.branch
                                                        || "DETACHED"
                                                    )
                                                    + " // "
                                                    + String(
                                                        worktreeRow.modelData.head
                                                        || ""
                                                      ).slice(0, 10)
                                                font.pixelSize: 11
                                                color: Colors.white
                                                elide: Text.ElideRight
                                            }

                                            GohuText {
                                                width: parent.width
                                                text:
                                                    String(
                                                        worktreeRow.modelData.path
                                                        || ""
                                                    )
                                                font.pixelSize: 9
                                                color: Colors.cyan
                                                elide: Text.ElideMiddle
                                            }

                                            GohuText {
                                                width: parent.width
                                                text:
                                                    Number(
                                                        worktreeRow.modelData.dirtyCount
                                                        || 0
                                                    ) > 0
                                                    ? String(
                                                        worktreeRow.modelData.dirtyCount
                                                      ) + " CHANGES"
                                                    : "CLEAN"
                                                font.pixelSize: 9
                                                color:
                                                    Number(
                                                        worktreeRow.modelData.dirtyCount
                                                        || 0
                                                    ) > 0
                                                    ? Colors.orange
                                                    : Colors.green
                                            }
                                        }

                                        MiniButton {
                                            id: lockButton
                                            width: 88
                                            height: 28
                                            anchors {
                                                right: parent.right
                                                rightMargin: 6
                                                verticalCenter:
                                                    parent.verticalCenter
                                            }
                                            label:
                                                Boolean(
                                                    worktreeRow.modelData.locked
                                                )
                                                ? "UNLOCK"
                                                : "LOCK"
                                            accent:
                                                Boolean(
                                                    worktreeRow.modelData.locked
                                                )
                                                ? Colors.orange
                                                : Colors.cyan
                                            enabledAction:
                                                root.repositoryService
                                                && !root.repositoryService.actionBusy
                                            onTriggered: {
                                                if (Boolean(
                                                        worktreeRow.modelData.locked
                                                    ))
                                                    root.repositoryService
                                                        .unlockWorktree(
                                                            worktreeRow.modelData.path
                                                        );
                                                else
                                                    root.repositoryService
                                                        .lockWorktree(
                                                            worktreeRow.modelData.path
                                                        );
                                            }
                                        }

                                        MouseArea {
                                            id: worktreeMouse
                                            anchors {
                                                left: parent.left
                                                right: lockButton.left
                                                top: parent.top
                                                bottom: parent.bottom
                                            }
                                            hoverEnabled: true
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked:
                                                root.selectedWorktreePath =
                                                    String(
                                                        worktreeRow.modelData.path
                                                        || ""
                                                    )
                                        }
                                    }
                                }
                            }
                        
                            NeonScrollBar {
                                flickable: repositoryScroll4
                            }
}
                    }
                }

                Rectangle {
                    width: parent.width - 568
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
                            height: 28

                            GohuText {
                                width: parent.width - 200
                                anchors.verticalCenter: parent.verticalCenter
                                text:
                                    "SUBMODULES // "
                                    + String(
                                        root.repositoryService
                                        ? root.repositoryService.submodules.length
                                        : 0
                                      )
                                font.pixelSize: 12
                                color: Colors.magenta
                            }

                            MiniButton {
                                width: 92
                                label: "SYNC"
                                accent: Colors.cyan
                                enabledAction:
                                    root.repositoryService
                                    && !root.repositoryService.actionBusy
                                onTriggered:
                                    root.repositoryService.syncSubmodules()
                            }

                            MiniButton {
                                width: 104
                                label: "INIT + UPDATE"
                                accent: Colors.green
                                enabledAction:
                                    root.repositoryService
                                    && !root.repositoryService.actionBusy
                                onTriggered:
                                    root.repositoryService.updateSubmodules()
                            }
                        }

                        Flickable {
                            id: repositoryScroll5
                            width: parent.width
                            height: parent.height - 34
                            clip: true
                            contentWidth: width
                            contentHeight: submoduleColumn.implicitHeight
                            boundsBehavior: Flickable.StopAtBounds

                            Column {
                                id: submoduleColumn
                                width: parent.width
                                spacing: 4

                                GohuText {
                                    visible:
                                        root.repositoryService
                                        && root.repositoryService.submodules.length === 0
                                    width: parent.width
                                    topPadding: 24
                                    text: "NO SUBMODULES"
                                    horizontalAlignment: Text.AlignHCenter
                                    font.pixelSize: 12
                                    color: Colors.cyan
                                }

                                Repeater {
                                    model:
                                        root.repositoryService
                                        ? root.repositoryService.submodules
                                        : []

                                    Rectangle {
                                        id: submoduleRow
                                        required property var modelData

                                        width: submoduleColumn.width
                                        height: 50
                                        color: Colors.dark
                                        border.width: 1
                                        border.color:
                                            String(modelData.state || "") === "-"
                                            ? Colors.orange
                                            : String(modelData.state || "") === "+"
                                            ? Colors.magenta
                                            : Colors.green

                                        Column {
                                            anchors {
                                                fill: parent
                                                margins: 7
                                            }
                                            spacing: 3

                                            GohuText {
                                                width: parent.width
                                                text:
                                                    String(
                                                        submoduleRow.modelData.path
                                                        || ""
                                                    )
                                                font.pixelSize: 11
                                                color: Colors.white
                                                elide: Text.ElideMiddle
                                            }

                                            GohuText {
                                                width: parent.width
                                                text:
                                                    String(
                                                        submoduleRow.modelData.state
                                                        || " "
                                                    )
                                                    + " // "
                                                    + String(
                                                        submoduleRow.modelData.sha
                                                        || ""
                                                      ).slice(0, 10)
                                                font.pixelSize: 9
                                                color: Colors.cyan
                                            }
                                        }
                                    }
                                }
                            }
                        
                            NeonScrollBar {
                                flickable: repositoryScroll5
                            }
}
                    }
                }
            }

            // ===== CONFIG ================================================
            Row {
                anchors.fill: parent
                spacing: 8
                visible: root.subMode === "config"

                Rectangle {
                    width: 520
                    height: parent.height
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.green

                    Flickable {
                        id: repositoryScroll6
                        anchors {
                            fill: parent
                            margins: 7
                        }
                        clip: true
                        contentWidth: width
                        contentHeight: configColumn.implicitHeight
                        boundsBehavior: Flickable.StopAtBounds

                        Column {
                            id: configColumn
                            width: parent.width
                            spacing: 2

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
                                        ? Colors.black
                                        : "transparent"

                                    GohuText {
                                        anchors {
                                            left: parent.left
                                            verticalCenter:
                                                parent.verticalCenter
                                        }
                                        width: 205
                                        text:
                                            String(configRow.modelData.key || "")
                                        font.pixelSize: 10
                                        color: Colors.green
                                        elide: Text.ElideRight
                                    }

                                    GohuText {
                                        anchors {
                                            left: parent.left
                                            right: parent.right
                                            verticalCenter:
                                                parent.verticalCenter
                                            leftMargin: 212
                                        }
                                        text:
                                            String(
                                                configRow.modelData.value || ""
                                            )
                                        font.pixelSize: 10
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
                                                String(
                                                    configRow.modelData.key || ""
                                                );
                                            configValueInput.text =
                                                String(
                                                    configRow.modelData.value || ""
                                                );
                                        }
                                    }
                                }
                            }
                        }
                    
                        NeonScrollBar {
                            flickable: repositoryScroll6
                            starHandle: true
                        }
}
                }

                Rectangle {
                    width: parent.width - 528
                    height: parent.height
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.cyan

                    Column {
                        anchors {
                            fill: parent
                            margins: 8
                        }
                        spacing: 7

                        SectionLabel {
                            text: "REPO-LOCAL CONFIG"
                        }

                        EditorBox {
                            id: configKeyInput
                            width: parent.width
                            placeholder: "KEY // user.name / pull.ff / fetch.prune"
                            accent: Colors.green
                            keyboardOwner: root.keyboardHost
                        }

                        EditorBox {
                            id: configValueInput
                            width: parent.width
                            placeholder: "VALUE"
                            accent: Colors.cyan
                            keyboardOwner: root.keyboardHost
                        }

                        MiniButton {
                            width: parent.width
                            label: "SET / REPLACE LOCAL CONFIG"
                            accent: Colors.green
                            enabledAction:
                                root.repositoryService
                                && configKeyInput.text.trim().length > 0
                                && configValueInput.text.trim().length > 0
                            onTriggered:
                                root.repositoryService.setConfig(
                                    configKeyInput.text.trim(),
                                    configValueInput.text
                                )
                        }

                        MiniButton {
                            width: parent.width
                            label:
                                root.armedAction === "unset-config"
                                ? "CONFIRM UNSET"
                                : "UNSET LOCAL CONFIG KEY"
                            accent: Colors.red
                            enabledAction:
                                root.repositoryService
                                && configKeyInput.text.trim().length > 0
                            onTriggered:
                                root.armOrRun(
                                    "unset-config",
                                    function() {
                                        root.repositoryService.unsetConfig(
                                            configKeyInput.text.trim()
                                        );
                                    }
                                )
                        }

                        GohuText {
                            width: parent.width
                            text:
                                "This editor is deliberately repo-local. "
                                + "Global identity/credentials remain outside this surface."
                            font.pixelSize: 10
                            color: Colors.white
                            opacity: 0.50
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }

            // ===== PROJECT FILES =========================================
            Row {
                anchors.fill: parent
                spacing: 8
                visible: root.subMode === "files"

                Rectangle {
                    width: 520
                    height: parent.height
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.yellow

                    Column {
                        anchors {
                            fill: parent
                            margins: 7
                        }
                        spacing: 5

                        Row {
                            width: parent.width
                            height: 28
                            spacing: 5

                            MiniButton {
                                width: 112
                                label: ".GITIGNORE"
                                accent: Colors.yellow
                                selected:
                                    root.projectFileKind === "ignore"
                                onTriggered: {
                                    root.projectFileKind = "ignore";
                                    root.selectedProjectLine = -1;
                                    root.armedAction = "";
                                }
                            }

                            MiniButton {
                                width: 132
                                label: ".GITATTRIBUTES"
                                accent: Colors.cyan
                                selected:
                                    root.projectFileKind === "attributes"
                                onTriggered: {
                                    root.projectFileKind = "attributes";
                                    root.selectedProjectLine = -1;
                                    root.armedAction = "";
                                }
                            }
                        }

                        Item {
                            id: projectFilesViewport

                            width: parent.width
                            height: Math.max(0, parent.height - 33)
                            clip: true

                            Flickable {
                                id: repositoryScroll7

                                anchors.fill: parent
                                clip: true
                                contentWidth: width
                                contentHeight: projectLineColumn.implicitHeight
                                boundsBehavior: Flickable.StopAtBounds

                                Column {
                                    id: projectLineColumn
                                    width: parent.width
                                    spacing: 2

                                    Repeater {
                                        model: root.projectLines()

                                        Rectangle {
                                            id: projectLineRow
                                            required property var modelData

                                            width: projectLineColumn.width
                                            height: 28
                                            color:
                                                projectLineMouse.containsMouse
                                                || root.selectedProjectLine
                                                   === Number(modelData.line || 0)
                                                ? Colors.black
                                                : "transparent"
                                            border.width:
                                                root.selectedProjectLine
                                                === Number(modelData.line || 0)
                                                ? 1 : 0
                                            border.color: Colors.yellow

                                            GohuText {
                                                anchors {
                                                    left: parent.left
                                                    verticalCenter:
                                                        parent.verticalCenter
                                                }
                                                width: 38
                                                text:
                                                    String(
                                                        projectLineRow.modelData.line
                                                        || 0
                                                    )
                                                font.pixelSize: 9
                                                color: Colors.cyan
                                            }

                                            GohuText {
                                                anchors {
                                                    left: parent.left
                                                    right: parent.right
                                                    verticalCenter:
                                                        parent.verticalCenter
                                                    leftMargin: 42
                                                }
                                                text:
                                                    String(
                                                        projectLineRow.modelData.text
                                                        || ""
                                                    )
                                                font.pixelSize: 10
                                                color: Colors.white
                                                elide: Text.ElideRight
                                            }

                                            MouseArea {
                                                id: projectLineMouse
                                                anchors.fill: parent
                                                hoverEnabled: true
                                                cursorShape: Qt.PointingHandCursor
                                                onClicked:
                                                    root.selectedProjectLine =
                                                        Number(
                                                            projectLineRow.modelData.line
                                                            || -1
                                                        )
                                            }
                                        }
                                    }
                                }

                                NeonScrollBar {
                                    flickable: repositoryScroll7
                                    starHandle: true
                                    rightInset: 2
                                }
                            }
                        }
                    }
                }

                Rectangle {
                    width: parent.width - 528
                    height: parent.height
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.cyan

                    Column {
                        anchors {
                            fill: parent
                            margins: 8
                        }
                        spacing: 7

                        SectionLabel {
                            text:
                                root.projectFileKind === "attributes"
                                ? ".GITATTRIBUTES"
                                : ".GITIGNORE"
                        }

                        EditorBox {
                            id: projectLineInput
                            width: parent.width
                            placeholder:
                                root.projectFileKind === "attributes"
                                ? "RULE // *.png binary"
                                : "PATTERN // build/"
                            accent:
                                root.projectFileKind === "attributes"
                                ? Colors.cyan
                                : Colors.yellow
                            keyboardOwner: root.keyboardHost
                        }

                        MiniButton {
                            width: parent.width
                            label: "APPEND UNIQUE LINE"
                            accent: Colors.green
                            enabledAction:
                                root.repositoryService
                                && projectLineInput.text.trim().length > 0
                            onTriggered:
                                root.repositoryService.appendProjectLine(
                                    root.projectFileKind,
                                    projectLineInput.text
                                )
                        }

                        MiniButton {
                            width: parent.width
                            label:
                                root.armedAction === "remove-project-line"
                                ? "CONFIRM REMOVE LINE "
                                  + String(root.selectedProjectLine)
                                : "REMOVE SELECTED LINE"
                            accent: Colors.red
                            enabledAction:
                                root.repositoryService
                                && root.selectedProjectLine > 0
                            onTriggered:
                                root.armOrRun(
                                    "remove-project-line",
                                    function() {
                                        root.repositoryService.removeProjectLine(
                                            root.projectFileKind,
                                            root.selectedProjectLine,
                                            true
                                        );
                                        root.selectedProjectLine = -1;
                                    }
                                )
                        }
                    }
                }
            }

            // ===== HOOKS =================================================
            Row {
                anchors.fill: parent
                spacing: 8
                visible: root.subMode === "hooks"

                Rectangle {
                    width: 520
                    height: parent.height
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.blue

                    Flickable {
                        id: repositoryScroll8
                        anchors {
                            fill: parent
                            margins: 7
                        }
                        clip: true
                        contentWidth: width
                        contentHeight: hookColumn.implicitHeight
                        boundsBehavior: Flickable.StopAtBounds

                        Column {
                            id: hookColumn
                            width: parent.width
                            spacing: 4

                            GohuText {
                                visible:
                                    root.repositoryService
                                    && root.repositoryService.hooks.length === 0
                                width: parent.width
                                topPadding: 24
                                text: "NO ACTIVE HOOK FILES"
                                horizontalAlignment: Text.AlignHCenter
                                font.pixelSize: 12
                                color: Colors.cyan
                            }

                            Repeater {
                                model:
                                    root.repositoryService
                                    ? root.repositoryService.hooks
                                    : []

                                Rectangle {
                                    id: hookRow
                                    required property var modelData

                                    width: hookColumn.width
                                    height: 42
                                    color: Colors.black
                                    border.width: 1
                                    border.color:
                                        Boolean(modelData.enabled)
                                        ? Colors.green
                                        : Colors.orange

                                    GohuText {
                                        anchors {
                                            left: parent.left
                                            verticalCenter:
                                                parent.verticalCenter
                                            leftMargin: 7
                                        }
                                        width: parent.width - 112
                                        text:
                                            String(hookRow.modelData.name || "")
                                        font.pixelSize: 11
                                        color: Colors.white
                                        elide: Text.ElideRight
                                    }

                                    MiniButton {
                                        width: 98
                                        height: 28
                                        anchors {
                                            right: parent.right
                                            rightMargin: 6
                                            verticalCenter:
                                                parent.verticalCenter
                                        }
                                        label:
                                            Boolean(hookRow.modelData.enabled)
                                            ? "DISABLE"
                                            : "ENABLE"
                                        accent:
                                            Boolean(hookRow.modelData.enabled)
                                            ? Colors.orange
                                            : Colors.green
                                        enabledAction:
                                            root.repositoryService
                                            && !root.repositoryService.actionBusy
                                        onTriggered:
                                            root.repositoryService
                                                .setHookEnabled(
                                                    hookRow.modelData.name,
                                                    !Boolean(
                                                        hookRow.modelData.enabled
                                                    )
                                                )
                                    }
                                }
                            }
                        }
                    
                        NeonScrollBar {
                            flickable: repositoryScroll8
                        }
}
                }

                Rectangle {
                    width: parent.width - 528
                    height: parent.height
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.cyan

                    Column {
                        anchors {
                            fill: parent
                            margins: 8
                        }
                        spacing: 8

                        SectionLabel {
                            text: "HOOK EXECUTION STATE"
                        }

                        GohuText {
                            width: parent.width
                            text:
                                "This surface only enables/disables existing "
                                + "repository hook files by executable bit. "
                                + "It does not generate hook scripts or rewrite hook contents."
                            font.pixelSize: 11
                            color: Colors.white
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }

            // ===== HEALTH ================================================
            Row {
                anchors.fill: parent
                spacing: 8
                visible: root.subMode === "health"

                Rectangle {
                    width: 450
                    height: parent.height
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.red

                    Column {
                        anchors {
                            fill: parent
                            margins: 8
                        }
                        spacing: 7

                        SectionLabel {
                            text: "OBJECT DATABASE"
                        }

                        Flickable {
                            id: repositoryScroll9
                            width: parent.width
                            height: 170
                            clip: true
                            contentWidth: width
                            contentHeight: objectText.implicitHeight

                            GohuText {
                                id: objectText
                                width: parent.width
                                text:
                                    root.repositoryService
                                    ? root.repositoryService.objectInfo
                                    : ""
                                font.pixelSize: 11
                                color: Colors.white
                                wrapMode: Text.WrapAnywhere
                            }
                        
                            NeonScrollBar {
                                flickable: repositoryScroll9
                            }
}

                        MiniButton {
                            width: parent.width
                            label: "FSCK // VERIFY OBJECT GRAPH"
                            accent: Colors.red
                            enabledAction:
                                root.repositoryService
                                && !root.repositoryService.actionBusy
                            onTriggered:
                                root.repositoryService.runFsck()
                        }

                        MiniButton {
                            width: parent.width
                            label: "GC --AUTO"
                            accent: Colors.orange
                            enabledAction:
                                root.repositoryService
                                && !root.repositoryService.actionBusy
                            onTriggered:
                                root.repositoryService.runGcAuto()
                        }

                        MiniButton {
                            width: parent.width
                            label: "MAINTENANCE RUN --AUTO"
                            accent: Colors.cyan
                            enabledAction:
                                root.repositoryService
                                && !root.repositoryService.actionBusy
                            onTriggered:
                                root.repositoryService.runMaintenance()
                        }
                    }
                }

                Rectangle {
                    width: parent.width - 458
                    height: parent.height
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.cyan

                    Flickable {
                        id: repositoryScroll10
                        anchors {
                            fill: parent
                            margins: 8
                        }
                        clip: true
                        contentWidth: width
                        contentHeight: healthText.implicitHeight

                        GohuText {
                            id: healthText
                            width: parent.width
                            text:
                                root.repositoryService
                                ? root.repositoryService.healthOutput
                                : "NO REPOSITORY SERVICE"
                            font.pixelSize: 11
                            color:
                                root.repositoryService
                                && root.repositoryService.lastError
                                ? Colors.red
                                : Colors.white
                            wrapMode: Text.WrapAnywhere
                        }
                    
                        NeonScrollBar {
                            flickable: repositoryScroll10
                        }
}
                }
            }
        }

        Rectangle {
            width: parent.width
            height: 34
            color: Colors.black
            border.width: 1
            border.color:
                root.repositoryService
                && root.repositoryService.lastError
                ? Colors.red
                : Colors.cyan

            GohuText {
                anchors {
                    fill: parent
                    leftMargin: 8
                    rightMargin: 8
                }
                verticalAlignment: Text.AlignVCenter
                text:
                    root.armedAction
                    ? "ARMED // "
                      + root.armedAction.toUpperCase()
                      + " // repeat destructive control to confirm"
                    : root.repositoryService
                    ? (
                        root.repositoryService.lastError
                        ? "REFUSED // " + root.repositoryService.lastError
                        : root.repositoryService.actionBusy
                        ? root.repositoryService.actionName + " // RUNNING"
                        : root.repositoryService.actionStatus
                      )
                    : "NO REPOSITORY SERVICE"
                font.pixelSize: 10
                color:
                    root.armedAction
                    ? Colors.orange
                    : root.repositoryService
                      && root.repositoryService.lastError
                    ? Colors.red
                    : Colors.cyan
                elide: Text.ElideRight
            }
        }
    }
}
