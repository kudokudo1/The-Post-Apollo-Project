import QtQuick
import QtQuick.Effects
import qs.components
import "../services/git"

Item {
    id: root

    property var changesService: null
    property var gitService: null
    property var transferService: null
    property var branchWorkspaceService: null
    property var conflictEditorService: null
    property var keyboardHost: null

    property bool transferOpen: false
    property string transferScope: "file"
    property string transferLayer: "worktree"
    property int transferHunkIndex: -1
    property int transferLineIndex: -1

    property string subMode: "files"
    property string selectedPath: ""
    property string pendingFocusPath: ""
    property var selectedFile: null

    signal historyRequested(string path)
    property string selectedStashRef: ""
    property int selectedHunkIndex: -1
    property int selectedLineIndex: -1
    property string diffMode: "combined"
    property string hunkMode: "worktree"

    property bool commitAmend: false
    property bool commitSign: false
    property bool commitAllowEmpty: false
    property bool commitNoVerify: false

    property string stashMode: "all"
    property bool stashRestoreIndex: false

    property string armedAction: ""

    GitLineTransferService {
        id: lineTransferService
        operationJournal:
            root.transferService
            ? root.transferService.operationJournal
            : null
        snapshotService:
            root.transferService
            ? root.transferService.snapshotService
            : null
        repositoryPath:
            root.gitService
            ? String(root.gitService.repoRoot || "")
            : ""
    }

    function worktreeFileTransferEligible() {
        const row = root.selectedFile || {};

        return !!root.changesService
            && !!root.transferService
            && !!root.branchWorkspaceService
            && root.selectedPath.length > 0
            && Boolean(row.unstaged)
            && !Boolean(row.staged)
            && !Boolean(row.untracked)
            && !Boolean(row.conflict)
            && !root.changesService.actionBusy
            && !root.transferService.previewBusy
            && !root.transferService.transferBusy;
    }

    function stagedFileTransferEligible() {
        const row = root.selectedFile || {};

        return !!root.changesService
            && !!root.transferService
            && !!root.branchWorkspaceService
            && root.selectedPath.length > 0
            && Boolean(row.staged)
            && !Boolean(row.unstaged)
            && !Boolean(row.untracked)
            && !Boolean(row.conflict)
            && !root.changesService.actionBusy
            && !root.transferService.previewBusy
            && !root.transferService.transferBusy;
    }

    function fileTransferEligible() {
        return root.worktreeFileTransferEligible()
            || root.stagedFileTransferEligible();
    }

    function transferEligible() {
        return root.fileTransferEligible();
    }

    function hunkTransferEligible() {
        return root.worktreeFileTransferEligible()
            && root.hunkMode === "worktree"
            && root.selectedHunkIndex >= 0
            && !root.changesService.hunkBusy;
    }

    function lineTransferEligible() {
        const line = root.selectedLine();

        return root.worktreeFileTransferEligible()
            && root.hunkMode === "worktree"
            && root.selectedHunkIndex >= 0
            && root.selectedLineIndex >= 0
            && line
            && Boolean(line.selectable)
            && !root.changesService.hunkBusy
            && !lineTransferService.previewBusy
            && !lineTransferService.transferBusy;
    }

    function openTransfer(scope) {
        const token = String(scope || "file");
        const requested =
            token === "line"
            ? "line"
            : token === "hunk"
            ? "hunk"
            : "file";
        const eligible =
            requested === "line"
            ? root.lineTransferEligible()
            : requested === "hunk"
            ? root.hunkTransferEligible()
            : root.fileTransferEligible();

        if (!eligible)
            return false;

        root.clearArm();

        if (root.transferService)
            root.transferService.clearPreview();
        lineTransferService.clearPreview();

        root.transferScope = requested;
        root.transferLayer =
            requested === "file"
            && root.stagedFileTransferEligible()
            ? "staged"
            : "worktree";
        root.transferHunkIndex =
            requested === "hunk" || requested === "line"
            ? root.selectedHunkIndex
            : -1;
        root.transferLineIndex =
            requested === "line"
            ? root.selectedLineIndex
            : -1;
        root.transferOpen = true;

        if (!root.branchWorkspaceService.refreshing)
            root.branchWorkspaceService.refresh();

        return true;
    }

    function closeTransfer() {
        root.transferOpen = false;
        root.transferScope = "file";
        root.transferLayer = "worktree";
        root.transferHunkIndex = -1;
        root.transferLineIndex = -1;

        if (root.transferService)
            root.transferService.clearPreview();
        lineTransferService.clearPreview();
    }

    function focusPath(path) {
        root.pendingFocusPath = String(path || "");
        root.applyPendingFocus();
    }

    function applyPendingFocus() {
        const target = String(root.pendingFocusPath || "");

        if (!target || !root.changesService)
            return;

        const conflicts = root.changesService.conflicts || [];

        for (let i = 0; i < conflicts.length; ++i) {
            const row = conflicts[i] || {};

            if (String(row.path || "") !== target)
                continue;

            root.pendingFocusPath = "";
            root.subMode = "conflicts";
            root.selectFile(row);
            return;
        }

        const rows = root.changesService.files || [];

        for (let i = 0; i < rows.length; ++i) {
            const row = rows[i] || {};

            if (String(row.path || "") !== target)
                continue;

            root.pendingFocusPath = "";
            root.subMode = "files";
            root.selectFile(row);
            return;
        }
    }

    function reconcileSelectedFile() {
        if (!root.changesService)
            return;

        if (!root.selectedPath) {
            root.selectedFile = null;
            return;
        }

        const rows = root.changesService.files || [];
        let fresh = null;

        for (let i = 0; i < rows.length; ++i) {
            const row = rows[i] || {};

            if (String(row.path || "") === root.selectedPath) {
                fresh = row;
                break;
            }
        }

        if (!fresh) {
            root.selectedFile = null;
            root.selectedPath = "";
            root.selectedHunkIndex = -1;
            root.selectedLineIndex = -1;
            root.clearArm();
            root.changesService.hunks = [];
            root.changesService.hunkPath = "";
            return;
        }

        root.selectedFile = fresh;

        if (Boolean(fresh.untracked)) {
            root.selectedHunkIndex = -1;
            root.selectedLineIndex = -1;
            root.changesService.hunks = [];
            root.changesService.hunkPath = root.selectedPath;
            return;
        }

        let nextMode = root.hunkMode;

        if (nextMode === "worktree"
                && !Boolean(fresh.unstaged)
                && Boolean(fresh.staged))
            nextMode = "staged";
        else if (nextMode === "staged"
                && !Boolean(fresh.staged)
                && Boolean(fresh.unstaged))
            nextMode = "worktree";

        if (nextMode !== root.hunkMode) {
            root.hunkMode = nextMode;
            root.selectedHunkIndex = -1;
            root.selectedLineIndex = -1;
            root.clearArm();
        }

        if (root.subMode === "hunks"
                && !root.changesService.hunkBusy)
            root.changesService.loadHunks(
                root.selectedPath,
                root.hunkMode
            );
    }

    function selectFile(row) {
        const data = row || {};
        root.selectedFile = data;
        root.selectedPath = String(data.path || "");
        root.selectedHunkIndex = -1;
        root.selectedLineIndex = -1;
        root.clearArm();

        if (!root.selectedPath || !root.changesService)
            return;

        root.changesService.preview(root.selectedPath, root.diffMode);

        if (root.subMode === "conflicts"
                && root.conflictEditorService)
            root.conflictEditorService.load(
                root.selectedPath
            );

        if (!Boolean(data.untracked)) {
            root.hunkMode = Boolean(data.unstaged)
                ? "worktree"
                : "staged";
            root.changesService.loadHunks(
                root.selectedPath,
                root.hunkMode
            );
        } else {
            root.changesService.hunks = [];
            root.changesService.hunkPath = root.selectedPath;
        }
    }

    function cycleDiffMode() {
        if (root.diffMode === "combined")
            root.diffMode = "worktree";
        else if (root.diffMode === "worktree")
            root.diffMode = "staged";
        else if (root.diffMode === "staged")
            root.diffMode = "word";
        else
            root.diffMode = "combined";

        if (root.selectedPath && root.changesService)
            root.changesService.preview(root.selectedPath, root.diffMode);
    }

    function setHunkMode(mode) {
        root.hunkMode = String(mode || "worktree");
        root.selectedHunkIndex = -1;
        root.selectedLineIndex = -1;
        root.clearArm();

        if (root.selectedPath && root.changesService)
            root.changesService.loadHunks(
                root.selectedPath,
                root.hunkMode
            );
    }

    function selectedHunk() {
        if (!root.changesService)
            return null;

        return root.changesService.hunkAt(
            root.selectedHunkIndex
        );
    }

    function selectedHunkLines() {
        const hunk = root.selectedHunk();
        return hunk && hunk.lines
            ? hunk.lines
            : [];
    }

    function selectedLine() {
        const lines = root.selectedHunkLines();

        if (
            root.selectedLineIndex < 0
            || root.selectedLineIndex >= lines.length
        )
            return null;

        return lines[root.selectedLineIndex];
    }

    function hunkDirectionText() {
        return root.hunkMode === "staged"
            ? "INDEX → WORKTREE"
            : "WORKTREE → INDEX";
    }

    function selectedHunkSummary() {
        const hunk = root.selectedHunk();

        if (!hunk)
            return "SELECT A HUNK // " + root.hunkDirectionText();

        return (
            "HUNK "
            + String(root.selectedHunkIndex + 1)
            + " // +"
            + String(hunk.added || 0)
            + " -"
            + String(hunk.removed || 0)
            + " // "
            + root.hunkDirectionText()
        );
    }

    function selectedLineSummary() {
        const line = root.selectedLine();

        if (!line)
            return "SELECT A +/- LINE // " + root.hunkDirectionText();

        const number =
            line.kind === "+"
            ? line.newLine
            : line.oldLine;
        const action =
            root.hunkMode === "staged"
            ? "UNSTAGE"
            : "STAGE";

        return (
            "LINE "
            + String(number || "?")
            + " // "
            + (
                line.kind === "+"
                ? "ADD"
                : "REMOVE"
              )
            + " // "
            + action
        );
    }

    function armOrRun(key, callback) {
        const token = String(key || "");
        if (root.armedAction !== token) {
            root.armedAction = token;
            return;
        }

        root.armedAction = "";
        callback();
    }

    function clearArm() {
        root.armedAction = "";
    }

    function cycleStashMode() {
        if (root.stashMode === "all")
            root.stashMode = "keep-index";
        else if (root.stashMode === "keep-index")
            root.stashMode = "staged";
        else
            root.stashMode = "all";
    }

    function shortCommitSha(value) {
        const sha = String(value || "");
        return sha.length > 8 ? sha.slice(0, 8) : sha;
    }

    function commitPayloadText() {
        if (!root.changesService)
            return "NO CHANGE SERVICE";

        let text =
            String(root.changesService.stagedCount)
            + " FILE"
            + (root.changesService.stagedCount === 1 ? "" : "S")
            + " // +"
            + String(root.changesService.stagedInsertions)
            + " -"
            + String(root.changesService.stagedDeletions);

        if (root.changesService.stagedBinaryFiles > 0)
            text +=
                " // "
                + String(root.changesService.stagedBinaryFiles)
                + " BIN";

        if (root.changesService.conflictCount > 0)
            text +=
                " // "
                + String(root.changesService.conflictCount)
                + " CONFLICT";

        return text;
    }

    function commitTargetText() {
        if (!root.changesService)
            return "NO TARGET";

        if (root.commitAmend) {
            return (
                "AMEND "
                + (
                    root.shortCommitSha(
                        root.changesService.headSha
                    )
                    || "NO HEAD"
                  )
                + (
                    root.changesService.headSubject
                    ? " // " + root.changesService.headSubject
                    : ""
                  )
            );
        }

        const branch =
            String(
                root.changesService.currentBranch
                || (
                    root.gitService
                    ? root.gitService.branch
                    : ""
                   )
                || "DETACHED"
            );
        const upstream =
            String(root.changesService.upstreamBranch || "");

        if (!upstream)
            return branch + " // NO UPSTREAM";

        return (
            branch
            + " // "
            + upstream
            + " // +"
            + String(root.changesService.upstreamAhead)
            + " -"
            + String(root.changesService.upstreamBehind)
        );
    }

    function commitSigningText() {
        if (!root.changesService)
            return "UNKNOWN";

        let state =
            root.commitSign
            ? "FORCED ON"
            : root.changesService.signingDefault
            ? "CONFIG ON"
            : "OFF";

        state +=
            " // "
            + String(
                root.changesService.signingFormat
                || "openpgp"
              ).toUpperCase();

        const key = String(root.changesService.signingKey || "");
        if (key)
            state += " // " + key.slice(Math.max(0, key.length - 12));

        return state;
    }

    function commitTrailerRisk() {
        return Boolean(
            root.commitAmend
            && root.changesService
            && root.changesService.headTrailers.length > 0
            && commitInput.text.trim().length > 0
        );
    }

    function commitPolicyText() {
        if (!root.changesService)
            return "UNKNOWN";

        const hooks = root.changesService.commitHooks || [];
        const trailers = root.changesService.headTrailers || [];
        let text =
            root.commitNoVerify
            ? "NO VERIFY // "
            : "HOOKS // ";

        text += hooks.length > 0
            ? hooks.join(" • ")
            : "NONE";

        if (root.changesService.commitTemplate)
            text += " // TEMPLATE";

        if (root.commitAmend && trailers.length > 0) {
            text +=
                root.commitTrailerRisk()
                ? " // REPLACES "
                  + String(trailers.length)
                  + " HEAD TRAILER"
                  + (trailers.length === 1 ? "" : "S")
                : " // PRESERVES "
                  + String(trailers.length)
                  + " HEAD TRAILER"
                  + (trailers.length === 1 ? "" : "S");
        }

        return text;
    }

    component LabelText: GohuText {
        font.pixelSize: 12
        color: Colors.cyan
    }

    component SectionLabel: GohuText {
        font.pixelSize: 14
        color: Colors.magenta
    }

    component CommitFact: Rectangle {
        id: fact

        property string label: ""
        property string value: ""
        property color accent: Colors.cyan

        height: 30
        color: Colors.black
        border.width: 1
        border.color: fact.accent
        clip: true

        Row {
            anchors {
                fill: parent
                leftMargin: 7
                rightMargin: 7
            }
            spacing: 6

            GohuText {
                width: Math.min(58, implicitWidth)
                anchors.verticalCenter: parent.verticalCenter
                text: fact.label
                font.pixelSize: 9
                color: fact.accent
            }

            GohuText {
                width: parent.width - 64
                anchors.verticalCenter: parent.verticalCenter
                text: fact.value
                font.pixelSize: 9
                color: Colors.white
                elide: Text.ElideMiddle
            }
        }
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
            border.color: Colors.cyan

            Row {
                anchors {
                    fill: parent
                    margins: 8
                }
                spacing: 8

                Column {
                    width: parent.width - 520
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 4

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
                        font.pixelSize: 10
                        color: Colors.white
                        elide: Text.ElideMiddle
                    }
                }

                Repeater {
                    model: [
                        {
                            key: "files",
                            label: "FILES",
                            count:
                                root.changesService
                                ? root.changesService.changedCount
                                : 0,
                            color: Colors.cyan
                        },
                        {
                            key: "hunks",
                            label: "HUNKS",
                            count:
                                root.changesService
                                ? root.changesService.hunks.length
                                : 0,
                            color: Colors.orange
                        },
                        {
                            key: "stashes",
                            label: "STASHES",
                            count:
                                root.changesService
                                ? root.changesService.stashes.length
                                : 0,
                            color: Colors.magenta
                        },
                        {
                            key: "conflicts",
                            label: "CONFLICTS",
                            count:
                                root.changesService
                                ? root.changesService.conflictCount
                                : 0,
                            color: Colors.red
                        }
                    ]

                    MiniButton {
                        required property var modelData
                        width: 94
                        anchors.verticalCenter: parent.verticalCenter
                        label:
                            modelData.label
                            + " "
                            + String(modelData.count)
                        accent: modelData.color
                        selected: root.subMode === modelData.key
                        onTriggered: {
                            root.subMode = modelData.key;
                            root.clearArm();
                        }
                    }
                }

                MiniButton {
                    width: 92
                    anchors.verticalCenter: parent.verticalCenter
                    label:
                        root.changesService
                        && root.changesService.refreshing
                        ? "READING"
                        : "REFRESH"
                    accent: Colors.green
                    enabledAction:
                        root.changesService
                        && !root.changesService.refreshing
                        && !root.changesService.actionBusy
                    onTriggered: root.changesService.refresh()
                }
            }
        }

        Item {
            width: parent.width
            height: parent.height - 210

            // ===== FILES =================================================
            Row {
                anchors.fill: parent
                spacing: 8
                visible: root.subMode === "files"

                Rectangle {
                    width: 430
                    height: parent.height
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.orange

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
                                width: 92
                                label: "STAGE ALL"
                                accent: Colors.green
                                enabledAction:
                                    root.changesService
                                    && root.changesService.changedCount > 0
                                    && !root.changesService.actionBusy
                                onTriggered:
                                    root.changesService.stageAll()
                            }

                            MiniButton {
                                width: 102
                                label: "UNSTAGE ALL"
                                accent: Colors.orange
                                enabledAction:
                                    root.changesService
                                    && root.changesService.stagedCount > 0
                                    && !root.changesService.actionBusy
                                onTriggered:
                                    root.changesService.unstageAll()
                            }

                            Rectangle {
                                width: parent.width - 204
                                height: 28
                                color: Colors.black
                                border.width: 1
                                border.color: Colors.cyan

                                GohuText {
                                    anchors.centerIn: parent
                                    text:
                                        "S "
                                        + String(
                                            root.changesService
                                            ? root.changesService.stagedCount
                                            : 0
                                          )
                                        + "  //  W "
                                        + String(
                                            root.changesService
                                            ? root.changesService.unstagedCount
                                            : 0
                                          )
                                        + "  //  N "
                                        + String(
                                            root.changesService
                                            ? root.changesService.untrackedCount
                                            : 0
                                          )
                                    font.pixelSize: 10
                                    color: Colors.cyan
                                }
                            }
                        }

                        Flickable {
                            id: changesScroll1
                            width: parent.width
                            height: parent.height - 34
                            clip: true
                            contentWidth: width
                            contentHeight: fileColumn.implicitHeight
                            boundsBehavior: Flickable.StopAtBounds

                            Column {
                                id: fileColumn
                                width: parent.width
                                spacing: 3

                                GohuText {
                                    visible:
                                        root.changesService
                                        && root.changesService.changedCount === 0
                                    width: parent.width
                                    topPadding: 24
                                    horizontalAlignment: Text.AlignHCenter
                                    text: "WORKTREE CLEAN"
                                    font.pixelSize: 13
                                    color: Colors.green
                                }

                                Repeater {
                                    model:
                                        root.changesService
                                        ? root.changesService.files
                                        : []

                                    Rectangle {
                                        id: fileRow
                                        required property var modelData

                                        width: fileColumn.width
                                        height: 44
                                        color:
                                            fileMouse.containsMouse
                                            || root.selectedPath
                                               === String(modelData.path || "")
                                            ? Colors.black
                                            : "transparent"
                                        border.width:
                                            root.selectedPath
                                            === String(modelData.path || "")
                                            ? 1 : 0
                                        border.color:
                                            modelData.conflict
                                            ? Colors.red
                                            : modelData.staged
                                            ? Colors.green
                                            : modelData.untracked
                                            ? Colors.magenta
                                            : Colors.orange

                                        Rectangle {
                                            width: 4
                                            anchors {
                                                top: parent.top
                                                bottom: parent.bottom
                                                left: parent.left
                                            }
                                            color:
                                                modelData.conflict
                                                ? Colors.red
                                                : modelData.staged
                                                ? Colors.green
                                                : modelData.untracked
                                                ? Colors.magenta
                                                : Colors.orange
                                        }

                                        Column {
                                            anchors {
                                                left: parent.left
                                                right: parent.right
                                                verticalCenter: parent.verticalCenter
                                                leftMargin: 10
                                                rightMargin: 8
                                            }
                                            spacing: 2

                                            GohuText {
                                                width: parent.width
                                                text: String(fileRow.modelData.path || "")
                                                font.pixelSize: 11
                                                color: Colors.white
                                                elide: Text.ElideMiddle
                                            }

                                            GohuText {
                                                width: parent.width
                                                text:
                                                    String(fileRow.modelData.label || "")
                                                    + "  //  "
                                                    + String(fileRow.modelData.indexStatus || " ")
                                                    + String(fileRow.modelData.worktreeStatus || " ")
                                                    + (
                                                        fileRow.modelData.originalPath
                                                        ? "  //  FROM "
                                                          + String(
                                                              fileRow.modelData.originalPath
                                                            )
                                                        : ""
                                                      )
                                                font.pixelSize: 9
                                                color:
                                                    fileRow.modelData.conflict
                                                    ? Colors.red
                                                    : fileRow.modelData.staged
                                                    ? Colors.green
                                                    : fileRow.modelData.untracked
                                                    ? Colors.magenta
                                                    : Colors.orange
                                                elide: Text.ElideMiddle
                                            }
                                        }

                                        MouseArea {
                                            id: fileMouse
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked:
                                                root.selectFile(
                                                    fileRow.modelData
                                                )
                                        }
                                    }
                                }
                            }
                        
                            NeonScrollBar {
                                flickable: changesScroll1
                            }
}
                    }
                }

                Rectangle {
                    width: parent.width - 438
                    height: parent.height
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.magenta

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

                            LabelText {
                                width: parent.width - 546
                                anchors.verticalCenter: parent.verticalCenter
                                text:
                                    root.selectedPath
                                    ? "DIFF // " + root.selectedPath
                                    : "DIFF PREVIEW"
                                elide: Text.ElideMiddle
                            }

                            MiniButton {
                                width: 92
                                label:
                                    "MODE "
                                    + root.diffMode.toUpperCase()
                                accent: Colors.cyan
                                onTriggered: root.cycleDiffMode()
                            }

                            MiniButton {
                                width: 76
                                label: "STAGE"
                                accent: Colors.green
                                enabledAction:
                                    root.changesService
                                    && root.selectedPath
                                    && root.selectedFile
                                    && (
                                        Boolean(root.selectedFile.unstaged)
                                        || Boolean(root.selectedFile.untracked)
                                      )
                                    && !root.changesService.actionBusy
                                onTriggered:
                                    root.changesService.stage(
                                        root.selectedPath
                                    )
                            }

                            MiniButton {
                                width: 82
                                label: "UNSTAGE"
                                accent: Colors.orange
                                enabledAction:
                                    root.changesService
                                    && root.selectedPath
                                    && root.selectedFile
                                    && Boolean(root.selectedFile.staged)
                                    && !root.changesService.actionBusy
                                onTriggered:
                                    root.changesService.unstage(
                                        root.selectedPath
                                    )
                            }

                            MiniButton {
                                width: 92
                                label:
                                    root.armedAction
                                    === "discard-file"
                                    ? "CONFIRM"
                                    : "DISCARD"
                                accent: Colors.red
                                enabledAction:
                                    root.changesService
                                    && root.selectedPath
                                    && root.selectedFile
                                    && Boolean(root.selectedFile.unstaged)
                                    && !root.changesService.actionBusy
                                onTriggered:
                                    root.armOrRun(
                                        "discard-file",
                                        function() {
                                            root.changesService.discardFile(
                                                root.selectedPath,
                                                true
                                            );
                                        }
                                    )
                            }

                            MiniButton {
                                width: 86
                                label: "TRANSFER"
                                accent: Colors.blue
                                enabledAction: root.fileTransferEligible()
                                onTriggered: root.openTransfer("file")
                            }

                            MiniButton {
                                width: 90
                                label: "HISTORY"
                                accent: Colors.magenta
                                enabledAction:
                                    root.selectedPath.length > 0
                                onTriggered:
                                    root.historyRequested(
                                        root.selectedPath
                                    )
                            }
                        }

                        Flickable {
                            id: changesScroll2
                            width: parent.width
                            height: parent.height - 34
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
                                font.pixelSize: 11
                                color:
                                    root.changesService
                                    && root.changesService.lastError
                                    ? Colors.red
                                    : Colors.white
                                wrapMode: Text.WrapAnywhere
                            }
                        
                            NeonScrollBar {
                                flickable: changesScroll2
                            }
}
                    }
                }
            }

            // ===== HUNKS =================================================
            Row {
                anchors.fill: parent
                spacing: 8
                visible: root.subMode === "hunks"

                Rectangle {
                    width: 410
                    height: parent.height
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.orange

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
                                width: 104
                                label: "WORKTREE"
                                accent: Colors.orange
                                selected: root.hunkMode === "worktree"
                                enabledAction:
                                    root.selectedFile
                                    && !Boolean(root.selectedFile.untracked)
                                    && Boolean(root.selectedFile.unstaged)
                                    && root.changesService
                                    && !root.changesService.actionBusy
                                onTriggered:
                                    root.setHunkMode("worktree")
                            }

                            MiniButton {
                                width: 92
                                label: "STAGED"
                                accent: Colors.green
                                selected: root.hunkMode === "staged"
                                enabledAction:
                                    root.selectedFile
                                    && !Boolean(root.selectedFile.untracked)
                                    && Boolean(root.selectedFile.staged)
                                    && root.changesService
                                    && !root.changesService.actionBusy
                                onTriggered:
                                    root.setHunkMode("staged")
                            }

                            LabelText {
                                width: parent.width - 206
                                anchors.verticalCenter: parent.verticalCenter
                                horizontalAlignment: Text.AlignRight
                                text:
                                    root.selectedPath
                                    ? root.selectedPath
                                    : "SELECT FILE IN FILES"
                                elide: Text.ElideMiddle
                            }
                        }

                        Flickable {
                            id: changesScroll3
                            width: parent.width
                            height: parent.height - 34
                            clip: true
                            contentWidth: width
                            contentHeight: hunkColumn.implicitHeight
                            boundsBehavior: Flickable.StopAtBounds

                            Column {
                                id: hunkColumn
                                width: parent.width
                                spacing: 4

                                GohuText {
                                    visible:
                                        root.selectedFile
                                        && Boolean(root.selectedFile.untracked)
                                    width: parent.width
                                    topPadding: 20
                                    text:
                                        "UNTRACKED FILE // STAGE WHOLE FILE FIRST"
                                    horizontalAlignment: Text.AlignHCenter
                                    font.pixelSize: 11
                                    color: Colors.magenta
                                }

                                GohuText {
                                    visible:
                                        root.changesService
                                        && !root.changesService.hunkBusy
                                        && root.changesService.hunks.length === 0
                                        && root.selectedPath
                                        && !(
                                            root.selectedFile
                                            && Boolean(root.selectedFile.untracked)
                                        )
                                    width: parent.width
                                    topPadding: 20
                                    text: "NO HUNKS IN THIS SIDE"
                                    horizontalAlignment: Text.AlignHCenter
                                    font.pixelSize: 11
                                    color: Colors.cyan
                                }

                                Repeater {
                                    model:
                                        root.changesService
                                        ? root.changesService.hunks
                                        : []

                                    Rectangle {
                                        id: hunkRow
                                        required property int index
                                        required property var modelData

                                        width: hunkColumn.width
                                        height: 54
                                        color:
                                            hunkMouse.containsMouse
                                            || root.selectedHunkIndex === index
                                            ? Colors.black
                                            : "transparent"
                                        border.width:
                                            root.selectedHunkIndex === index
                                            ? 1 : 0
                                        border.color: Colors.orange

                                        Column {
                                            anchors {
                                                fill: parent
                                                margins: 7
                                            }
                                            spacing: 3

                                            GohuText {
                                                width: parent.width
                                                text: String(hunkRow.modelData.header || "")
                                                font.pixelSize: 10
                                                color: Colors.orange
                                                elide: Text.ElideRight
                                            }

                                            GohuText {
                                                width: parent.width
                                                text:
                                                    "+"
                                                    + String(
                                                        hunkRow.modelData.added || 0
                                                      )
                                                    + "  -"
                                                    + String(
                                                        hunkRow.modelData.removed || 0
                                                      )
                                                font.pixelSize: 10
                                                color: Colors.cyan
                                            }
                                        }

                                        MouseArea {
                                            id: hunkMouse
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: {
                                                root.selectedHunkIndex =
                                                    hunkRow.index;
                                                root.selectedLineIndex = -1;
                                                root.clearArm();
                                            }
                                        }
                                    }
                                }
                            }
                        
                            NeonScrollBar {
                                flickable: changesScroll3
                            }
}
                    }
                }

                Rectangle {
                    width: parent.width - 418
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
                            height: 28
                            spacing: 5

                            LabelText {
                                width: parent.width - 435
                                anchors.verticalCenter: parent.verticalCenter
                                text: root.selectedHunkSummary()
                                color:
                                    root.hunkMode === "staged"
                                    ? Colors.orange
                                    : Colors.green
                                elide: Text.ElideRight
                            }

                            MiniButton {
                                width: 116
                                label:
                                    root.hunkMode === "staged"
                                    ? "UNSTAGE HUNK"
                                    : "STAGE HUNK"
                                accent:
                                    root.hunkMode === "staged"
                                    ? Colors.orange
                                    : Colors.green
                                enabledAction:
                                    root.changesService
                                    && root.selectedHunkIndex >= 0
                                    && !root.changesService.actionBusy
                                onTriggered: {
                                    root.selectedLineIndex = -1;

                                    if (root.hunkMode === "staged")
                                        root.changesService.unstageHunk(
                                            root.selectedPath,
                                            root.selectedHunkIndex
                                        );
                                    else
                                        root.changesService.stageHunk(
                                            root.selectedPath,
                                            root.selectedHunkIndex
                                        );
                                }
                            }

                            MiniButton {
                                width: 110
                                label:
                                    root.armedAction === "discard-hunk"
                                    ? "CONFIRM HUNK"
                                    : "DISCARD HUNK"
                                accent: Colors.red
                                enabledAction:
                                    root.hunkMode === "worktree"
                                    && root.changesService
                                    && root.selectedHunkIndex >= 0
                                    && !root.changesService.actionBusy
                                onTriggered:
                                    root.armOrRun(
                                        "discard-hunk",
                                        function() {
                                            root.selectedLineIndex = -1;
                                            root.changesService.discardHunk(
                                                root.selectedPath,
                                                root.selectedHunkIndex,
                                                true
                                            );
                                        }
                                    )
                            }

                            MiniButton {
                                width: 86
                                label: "TRANSFER"
                                accent: Colors.blue
                                enabledAction: root.hunkTransferEligible()
                                onTriggered: root.openTransfer("hunk")
                            }

                            MiniButton {
                                width: 108
                                label: "RELOAD"
                                accent: Colors.cyan
                                enabledAction:
                                    root.changesService
                                    && root.selectedPath
                                    && !root.changesService.hunkBusy
                                onTriggered: {
                                    root.selectedLineIndex = -1;
                                    root.changesService.loadHunks(
                                        root.selectedPath,
                                        root.hunkMode
                                    );
                                }
                            }
                        }

                        Row {
                            width: parent.width
                            height: 28
                            spacing: 5

                            LabelText {
                                width: parent.width - 321
                                anchors.verticalCenter: parent.verticalCenter
                                text: root.selectedLineSummary()
                                color:
                                    root.selectedLine()
                                    && root.selectedLine().kind === "+"
                                    ? Colors.green
                                    : root.selectedLine()
                                      && root.selectedLine().kind === "-"
                                    ? Colors.orange
                                    : Colors.cyan
                            }

                            MiniButton {
                                width: 108
                                label:
                                    root.hunkMode === "staged"
                                    ? "UNSTAGE LINE"
                                    : "STAGE LINE"
                                accent:
                                    root.hunkMode === "staged"
                                    ? Colors.orange
                                    : Colors.green
                                enabledAction:
                                    root.changesService
                                    && root.selectedHunkIndex >= 0
                                    && root.selectedLineIndex >= 0
                                    && root.selectedLine()
                                    && Boolean(
                                        root.selectedLine().selectable
                                    )
                                    && !root.changesService.actionBusy
                                onTriggered: {
                                    if (root.hunkMode === "staged")
                                        root.changesService.unstageLine(
                                            root.selectedPath,
                                            root.selectedHunkIndex,
                                            root.selectedLineIndex
                                        );
                                    else
                                        root.changesService.stageLine(
                                            root.selectedPath,
                                            root.selectedHunkIndex,
                                            root.selectedLineIndex
                                        );

                                    root.selectedLineIndex = -1;
                                    root.clearArm();
                                }
                            }

                            MiniButton {
                                width: 112
                                label:
                                    root.armedAction === "discard-line"
                                    ? "CONFIRM LINE"
                                    : "DISCARD LINE"
                                accent: Colors.red
                                enabledAction:
                                    root.hunkMode === "worktree"
                                    && root.changesService
                                    && root.selectedHunkIndex >= 0
                                    && root.selectedLineIndex >= 0
                                    && root.selectedLine()
                                    && Boolean(
                                        root.selectedLine().selectable
                                    )
                                    && !root.changesService.actionBusy
                                onTriggered:
                                    root.armOrRun(
                                        "discard-line",
                                        function() {
                                            root.changesService.discardLine(
                                                root.selectedPath,
                                                root.selectedHunkIndex,
                                                root.selectedLineIndex,
                                                true
                                            );
                                            root.selectedLineIndex = -1;
                                        }
                                    )
                            }

                            MiniButton {
                                width: 86
                                label: "TRANSFER"
                                accent: Colors.blue
                                enabledAction: root.lineTransferEligible()
                                onTriggered: root.openTransfer("line")
                            }

                        }

                        Flickable {
                            id: changesScroll4

                            width: parent.width
                            height: parent.height - 66
                            clip: true
                            contentWidth: width
                            contentHeight: lineColumn.implicitHeight
                            boundsBehavior: Flickable.StopAtBounds

                            Column {
                                id: lineColumn

                                width: parent.width
                                spacing: 1

                                GohuText {
                                    visible:
                                        root.selectedHunkIndex < 0
                                    width: parent.width
                                    topPadding: 24
                                    text: "SELECT A HUNK"
                                    horizontalAlignment:
                                        Text.AlignHCenter
                                    font.pixelSize: 11
                                    color: Colors.cyan
                                }

                                Repeater {
                                    model: root.selectedHunkLines()

                                    Rectangle {
                                        id: lineRow

                                        required property int index
                                        required property var modelData

                                        width: lineColumn.width
                                        height: 25

                                        color:
                                            root.selectedLineIndex
                                            === index
                                            ? Colors.dark
                                            : lineMouse.containsMouse
                                              && Boolean(
                                                  modelData.selectable
                                              )
                                            ? Colors.black
                                            : "transparent"

                                        border.width:
                                            root.selectedLineIndex
                                            === index
                                            ? 1
                                            : 0

                                        border.color:
                                            modelData.kind === "+"
                                            ? Colors.green
                                            : modelData.kind === "-"
                                            ? Colors.orange
                                            : Colors.cyan

                                        GohuText {
                                            anchors {
                                                left: parent.left
                                                verticalCenter:
                                                    parent.verticalCenter
                                            }
                                            width: 42
                                            horizontalAlignment:
                                                Text.AlignRight
                                            text:
                                                lineRow.modelData.oldLine
                                                ? String(
                                                    lineRow.modelData.oldLine
                                                  )
                                                : ""
                                            font.pixelSize: 9
                                            color: Colors.white
                                            opacity: 0.44
                                        }

                                        GohuText {
                                            anchors {
                                                left: parent.left
                                                verticalCenter:
                                                    parent.verticalCenter
                                                leftMargin: 48
                                            }
                                            width: 42
                                            horizontalAlignment:
                                                Text.AlignRight
                                            text:
                                                lineRow.modelData.newLine
                                                ? String(
                                                    lineRow.modelData.newLine
                                                  )
                                                : ""
                                            font.pixelSize: 9
                                            color: Colors.white
                                            opacity: 0.44
                                        }

                                        GohuText {
                                            anchors {
                                                left: parent.left
                                                verticalCenter:
                                                    parent.verticalCenter
                                                leftMargin: 98
                                            }
                                            width: 18
                                            horizontalAlignment:
                                                Text.AlignHCenter
                                            text:
                                                String(
                                                    lineRow.modelData.kind
                                                    || " "
                                                )
                                            font.pixelSize: 11
                                            color:
                                                lineRow.modelData.kind === "+"
                                                ? Colors.green
                                                : lineRow.modelData.kind === "-"
                                                ? Colors.orange
                                                : Colors.cyan
                                        }

                                        GohuText {
                                            anchors {
                                                left: parent.left
                                                right: parent.right
                                                verticalCenter:
                                                    parent.verticalCenter
                                                leftMargin: 122
                                                rightMargin: 12
                                            }
                                            text:
                                                String(
                                                    lineRow.modelData.text
                                                    || ""
                                                )
                                            font.pixelSize: 10
                                            color:
                                                lineRow.modelData.kind === "+"
                                                ? Colors.green
                                                : lineRow.modelData.kind === "-"
                                                ? Colors.orange
                                                : Colors.white
                                            opacity:
                                                Boolean(
                                                    lineRow
                                                        .modelData
                                                        .selectable
                                                )
                                                ? 1.0
                                                : 0.58
                                            elide: Text.ElideRight
                                        }

                                        MouseArea {
                                            id: lineMouse

                                            anchors.fill: parent
                                            enabled:
                                                Boolean(
                                                    lineRow
                                                        .modelData
                                                        .selectable
                                                )
                                            hoverEnabled: true
                                            cursorShape:
                                                enabled
                                                ? Qt.PointingHandCursor
                                                : Qt.ArrowCursor

                                            onClicked: {
                                                root.selectedLineIndex =
                                                    lineRow.index;
                                                root.clearArm();
                                            }
                                        }
                                    }
                                }
                            }

                            NeonScrollBar {
                                flickable: changesScroll4
                            }
                        }
                    }
                }
            }

            // ===== STASHES ===============================================
            Row {
                anchors.fill: parent
                spacing: 8
                visible: root.subMode === "stashes"

                Rectangle {
                    width: 410
                    height: parent.height
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.magenta

                    Flickable {
                        id: changesScroll5
                        anchors {
                            fill: parent
                            margins: 7
                        }
                        clip: true
                        contentWidth: width
                        contentHeight: stashColumn.implicitHeight
                        boundsBehavior: Flickable.StopAtBounds

                        Column {
                            id: stashColumn
                            width: parent.width
                            spacing: 4

                            GohuText {
                                visible:
                                    root.changesService
                                    && root.changesService.stashes.length === 0
                                width: parent.width
                                topPadding: 24
                                text: "NO STASHES"
                                horizontalAlignment: Text.AlignHCenter
                                font.pixelSize: 12
                                color: Colors.cyan
                            }

                            Repeater {
                                model:
                                    root.changesService
                                    ? root.changesService.stashes
                                    : []

                                Rectangle {
                                    id: stashRow
                                    required property var modelData

                                    width: stashColumn.width
                                    height: 54
                                    color:
                                        stashMouse.containsMouse
                                        || root.selectedStashRef
                                           === String(modelData.ref || "")
                                        ? Colors.black
                                        : "transparent"
                                    border.width:
                                        root.selectedStashRef
                                        === String(modelData.ref || "")
                                        ? 1 : 0
                                    border.color: Colors.magenta

                                    Column {
                                        anchors {
                                            fill: parent
                                            margins: 7
                                        }
                                        spacing: 3

                                        GohuText {
                                            width: parent.width
                                            text:
                                                String(stashRow.modelData.ref || "")
                                                + "  //  "
                                                + String(
                                                    stashRow.modelData.sha || ""
                                                  ).slice(0, 8)
                                            font.pixelSize: 10
                                            color: Colors.magenta
                                        }

                                        GohuText {
                                            width: parent.width
                                            text:
                                                String(
                                                    stashRow.modelData.message || ""
                                                )
                                            font.pixelSize: 11
                                            color: Colors.white
                                            elide: Text.ElideRight
                                        }
                                    }

                                    MouseArea {
                                        id: stashMouse
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            root.selectedStashRef =
                                                String(
                                                    stashRow.modelData.ref || ""
                                                );
                                            root.changesService.previewStash(
                                                root.selectedStashRef
                                            );
                                            root.clearArm();
                                        }
                                    }
                                }
                            }
                        }
                    
                        NeonScrollBar {
                            flickable: changesScroll5
                        }
}
                }

                Rectangle {
                    width: parent.width - 418
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
                            height: 28
                            spacing: 5

                            LabelText {
                                width: parent.width - 378
                                anchors.verticalCenter: parent.verticalCenter
                                text:
                                    root.selectedStashRef
                                    ? "STASH // " + root.selectedStashRef
                                    : "SELECT A STASH"
                            }

                            MiniButton {
                                width: 86
                                label: "INDEX"
                                accent: Colors.cyan
                                selected: root.stashRestoreIndex
                                onTriggered:
                                    root.stashRestoreIndex =
                                        !root.stashRestoreIndex
                            }

                            MiniButton {
                                width: 82
                                label: "APPLY"
                                accent: Colors.green
                                enabledAction:
                                    root.selectedStashRef
                                    && root.changesService
                                    && !root.changesService.actionBusy
                                onTriggered:
                                    root.changesService.applyStash(
                                        root.selectedStashRef,
                                        root.stashRestoreIndex
                                    )
                            }

                            MiniButton {
                                width: 82
                                label: "POP"
                                accent: Colors.orange
                                enabledAction:
                                    root.selectedStashRef
                                    && root.changesService
                                    && !root.changesService.actionBusy
                                onTriggered:
                                    root.changesService.popStash(
                                        root.selectedStashRef,
                                        root.stashRestoreIndex
                                    )
                            }

                            MiniButton {
                                width: 112
                                label:
                                    root.armedAction === "drop-stash"
                                    ? "CONFIRM DROP"
                                    : "DROP"
                                accent: Colors.red
                                enabledAction:
                                    root.selectedStashRef
                                    && root.changesService
                                    && !root.changesService.actionBusy
                                onTriggered:
                                    root.armOrRun(
                                        "drop-stash",
                                        function() {
                                            root.changesService.dropStash(
                                                root.selectedStashRef,
                                                true
                                            );
                                            root.selectedStashRef = "";
                                        }
                                    )
                            }
                        }

                        Flickable {
                            id: changesScroll6
                            width: parent.width
                            height: parent.height - 34
                            clip: true
                            contentWidth: width
                            contentHeight: stashDiff.implicitHeight
                            boundsBehavior: Flickable.StopAtBounds

                            GohuText {
                                id: stashDiff
                                width: parent.width
                                text:
                                    root.changesService
                                    ? root.changesService.previewText
                                    : "NO CHANGE SERVICE"
                                font.pixelSize: 11
                                color: Colors.white
                                wrapMode: Text.WrapAnywhere
                            }
                        
                            NeonScrollBar {
                                flickable: changesScroll6
                            }
}
                    }
                }
            }

            // ===== CONFLICTS =============================================
            Row {
                anchors.fill: parent
                spacing: 8
                visible: root.subMode === "conflicts"

                Rectangle {
                    width: 430
                    height: parent.height
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.red

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
                                width: parent.width - 130
                                anchors.verticalCenter: parent.verticalCenter
                                text:
                                    "STATE // "
                                    + (
                                        root.changesService
                                        ? root.changesService.operationState
                                        : "NONE"
                                      )
                                font.pixelSize: 12
                                color:
                                    root.changesService
                                    && root.changesService.operationState !== "NONE"
                                    ? Colors.orange
                                    : Colors.cyan
                            }

                            GohuText {
                                width: 130
                                anchors.verticalCenter: parent.verticalCenter
                                horizontalAlignment: Text.AlignRight
                                text:
                                    String(
                                        root.changesService
                                        ? root.changesService.conflictCount
                                        : 0
                                    )
                                    + " CONFLICTS"
                                font.pixelSize: 11
                                color: Colors.red
                            }
                        }

                        Flickable {
                            id: changesScroll7
                            width: parent.width
                            height: parent.height - 34
                            clip: true
                            contentWidth: width
                            contentHeight: conflictColumn.implicitHeight
                            boundsBehavior: Flickable.StopAtBounds

                            Column {
                                id: conflictColumn
                                width: parent.width
                                spacing: 4

                                GohuText {
                                    visible:
                                        root.changesService
                                        && root.changesService.conflictCount === 0
                                    width: parent.width
                                    topPadding: 24
                                    text: "NO UNRESOLVED CONFLICTS"
                                    horizontalAlignment: Text.AlignHCenter
                                    font.pixelSize: 12
                                    color: Colors.green
                                }

                                Repeater {
                                    model:
                                        root.changesService
                                        ? root.changesService.conflicts
                                        : []

                                    Rectangle {
                                        id: conflictRow
                                        required property var modelData

                                        width: conflictColumn.width
                                        height: 44
                                        color:
                                            conflictMouse.containsMouse
                                            || root.selectedPath
                                               === String(modelData.path || "")
                                            ? Colors.black
                                            : "transparent"
                                        border.width:
                                            root.selectedPath
                                            === String(modelData.path || "")
                                            ? 1 : 0
                                        border.color: Colors.red

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
                                                        conflictRow.modelData.path || ""
                                                    )
                                                font.pixelSize: 11
                                                color: Colors.white
                                                elide: Text.ElideMiddle
                                            }

                                            GohuText {
                                                width: parent.width
                                                text:
                                                    "CONFLICT // "
                                                    + String(
                                                        conflictRow.modelData.indexStatus
                                                        || " "
                                                    )
                                                    + String(
                                                        conflictRow.modelData.worktreeStatus
                                                        || " "
                                                    )
                                                font.pixelSize: 9
                                                color: Colors.red
                                            }
                                        }

                                        MouseArea {
                                            id: conflictMouse
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked:
                                                root.selectFile(
                                                    conflictRow.modelData
                                                )
                                        }
                                    }
                                }
                            }
                        
                            NeonScrollBar {
                                flickable: changesScroll7
                            }
}
                    }
                }

                Rectangle {
                    width: parent.width - 438
                    height: parent.height
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.orange

                    Column {
                        anchors {
                            fill: parent
                            margins: 8
                        }
                        spacing: 8

                        LabelText {
                            width: parent.width
                            text:
                                root.selectedPath
                                ? "RESOLVE // " + root.selectedPath
                                : "SELECT A CONFLICT"
                            elide: Text.ElideMiddle
                        }

                        Row {
                            width: parent.width
                            height: 32
                            spacing: 6

                            MiniButton {
                                width: (parent.width - 12) / 3
                                height: 32
                                label: "TAKE OURS"
                                accent: Colors.cyan
                                enabledAction:
                                    root.selectedPath
                                    && root.changesService
                                    && !root.changesService.actionBusy
                                onTriggered:
                                    root.changesService.resolveOurs(
                                        root.selectedPath
                                    )
                            }

                            MiniButton {
                                width: (parent.width - 12) / 3
                                height: 32
                                label: "TAKE THEIRS"
                                accent: Colors.magenta
                                enabledAction:
                                    root.selectedPath
                                    && root.changesService
                                    && !root.changesService.actionBusy
                                onTriggered:
                                    root.changesService.resolveTheirs(
                                        root.selectedPath
                                    )
                            }

                            MiniButton {
                                width: (parent.width - 12) / 3
                                height: 32
                                label: "MARK RESOLVED"
                                accent: Colors.green
                                enabledAction:
                                    root.selectedPath
                                    && root.changesService
                                    && !root.changesService.actionBusy
                                onTriggered:
                                    root.changesService.markResolved(
                                        root.selectedPath
                                    )
                            }
                        }

                        Rectangle {
                            width: parent.width
                            height: 1
                            color: Colors.cyan
                            opacity: 0.24
                        }

                        Row {
                            width: parent.width
                            height: 34
                            spacing: 8

                            MiniButton {
                                width: (parent.width - 16) / 3
                                height: 34
                                label:
                                    "CONTINUE "
                                    + (
                                        root.changesService
                                        ? root.changesService.operationState
                                        : ""
                                      )
                                accent: Colors.green
                                enabledAction:
                                    root.changesService
                                    && root.changesService.operationState !== "NONE"
                                    && root.changesService.conflictCount === 0
                                    && !root.changesService.actionBusy
                                onTriggered:
                                    root.changesService.continueOperation()
                            }

                            MiniButton {
                                width: (parent.width - 16) / 3
                                height: 34
                                label: "SKIP STEP"
                                accent: Colors.orange
                                enabledAction:
                                    root.changesService
                                    && (
                                        root.changesService.operationState === "REBASE"
                                        || root.changesService.operationState === "CHERRY_PICK"
                                        || root.changesService.operationState === "REVERT"
                                      )
                                    && !root.changesService.actionBusy
                                onTriggered:
                                    root.changesService.skipOperation()
                            }

                            MiniButton {
                                width: (parent.width - 16) / 3
                                height: 34
                                label:
                                    root.armedAction === "abort-operation"
                                    ? "CONFIRM ABORT"
                                    : "ABORT OPERATION"
                                accent: Colors.red
                                enabledAction:
                                    root.changesService
                                    && root.changesService.operationState !== "NONE"
                                    && !root.changesService.actionBusy
                                onTriggered:
                                    root.armOrRun(
                                        "abort-operation",
                                        function() {
                                            root.changesService.abortOperation(
                                                true
                                            );
                                        }
                                    )
                            }
                        }

                        GitConflictEditorView {
                            width: parent.width
                            height: parent.height - 118

                            conflictService:
                                root.conflictEditorService
                            keyboardHost: root.keyboardHost
                        }
                    }
                }
            }
        }

        Rectangle {
            width: parent.width
            height: 132
            color: Colors.dark
            border.width: 1
            border.color:
                root.changesService
                && root.changesService.lastError
                ? Colors.red
                : Colors.green

            Column {
                anchors {
                    fill: parent
                    margins: 7
                }
                spacing: 5

                Row {
                    width: parent.width
                    height: 30
                    spacing: 6

                    CommitFact {
                        width: (parent.width - 18) / 4
                        label: "PAYLOAD"
                        value: root.commitPayloadText()
                        accent:
                            root.changesService
                            && root.changesService.conflictCount > 0
                            ? Colors.red
                            : root.changesService
                              && root.changesService.stagedCount > 0
                            ? Colors.green
                            : Colors.cyan
                    }

                    CommitFact {
                        width: (parent.width - 18) / 4
                        label: "TARGET"
                        value: root.commitTargetText()
                        accent:
                            root.commitAmend
                            ? Colors.orange
                            : Colors.cyan
                    }

                    CommitFact {
                        width: (parent.width - 18) / 4
                        label: "SIGN"
                        value: root.commitSigningText()
                        accent:
                            root.commitSign
                            || (
                                root.changesService
                                && root.changesService.signingDefault
                               )
                            ? Colors.magenta
                            : Colors.cyan
                    }

                    CommitFact {
                        width: (parent.width - 18) / 4
                        label: "POLICY"
                        value: root.commitPolicyText()
                        accent:
                            root.commitNoVerify
                            ? Colors.red
                            : root.commitTrailerRisk()
                            ? Colors.orange
                            : root.changesService
                              && root.changesService.commitHooks.length > 0
                            ? Colors.orange
                            : Colors.cyan
                    }
                }

                Row {
                    width: parent.width
                    height: 30
                    spacing: 6

                    EditorBox {
                        id: commitInput
                        width: parent.width - 532
                        placeholder:
                            root.commitAmend
                            ? "NEW MESSAGE // EMPTY KEEPS CURRENT MESSAGE"
                            : "COMMIT MESSAGE..."
                        accent: Colors.cyan
                        keyboardOwner: root.keyboardHost
                    }

                    MiniButton {
                        width: 72
                        height: 30
                        label: "AMEND"
                        accent: Colors.orange
                        selected: root.commitAmend
                        onTriggered:
                            root.commitAmend = !root.commitAmend
                    }

                    MiniButton {
                        width: 68
                        height: 30
                        label: "SIGN"
                        accent: Colors.magenta
                        selected: root.commitSign
                        onTriggered:
                            root.commitSign = !root.commitSign
                    }

                    MiniButton {
                        width: 92
                        height: 30
                        label: "NO VERIFY"
                        accent: Colors.red
                        selected: root.commitNoVerify
                        onTriggered:
                            root.commitNoVerify = !root.commitNoVerify
                    }

                    MiniButton {
                        width: 72
                        height: 30
                        label: "EMPTY"
                        accent: Colors.cyan
                        selected: root.commitAllowEmpty
                        enabledAction: !root.commitAmend
                        onTriggered:
                            root.commitAllowEmpty =
                                !root.commitAllowEmpty
                    }

                    MiniButton {
                        width: 114
                        height: 30
                        label:
                            root.commitAmend
                            ? "AMEND HEAD"
                            : "COMMIT"
                        accent: Colors.green
                        enabledAction:
                            root.changesService
                            && !root.changesService.actionBusy
                            && root.changesService.conflictCount === 0
                            && (
                                root.commitAmend
                                || root.commitAllowEmpty
                                || (
                                    root.changesService.stagedCount > 0
                                    && commitInput.text.trim().length > 0
                                )
                              )
                        onTriggered:
                            root.changesService.commit(
                                commitInput.text,
                                root.commitAmend,
                                root.commitSign,
                                root.commitAllowEmpty,
                                root.commitNoVerify
                            )
                    }

                    MiniButton {
                        width: 84
                        height: 30
                        label: "CLEAR"
                        accent: Colors.cyan
                        enabledAction:
                            root.armedAction.length > 0
                        onTriggered: root.clearArm()
                    }
                }

                Row {
                    width: parent.width
                    height: 30
                    spacing: 6

                    MiniButton {
                        width: 150
                        height: 30
                        label:
                            "STASH "
                            + root.stashMode.toUpperCase()
                        accent: Colors.magenta
                        onTriggered: root.cycleStashMode()
                    }

                    MiniButton {
                        width: 118
                        height: 30
                        label: "STASH NOW"
                        accent: Colors.magenta
                        enabledAction:
                            root.changesService
                            && root.changesService.changedCount > 0
                            && !root.changesService.actionBusy
                        onTriggered:
                            root.changesService.stash(
                                commitInput.text.trim().length > 0
                                ? commitInput.text
                                : "Post-Apollo stash",
                                root.stashMode
                            )
                    }

                    GohuText {
                        width: parent.width - 280
                        anchors.verticalCenter: parent.verticalCenter
                        text:
                            root.stashMode === "staged"
                            ? "STAGED ONLY"
                            : root.stashMode === "keep-index"
                            ? "STASH WORKTREE + UNTRACKED, KEEP INDEX"
                            : "STASH TRACKED + UNTRACKED"
                        font.pixelSize: 10
                        color: Colors.cyan
                        elide: Text.ElideRight
                    }
                }

                GohuText {
                    width: parent.width
                    text:
                        root.armedAction
                        ? "ARMED // "
                          + root.armedAction.toUpperCase()
                          + " // press the same destructive control again to confirm"
                        : root.changesService
                        ? (
                            root.changesService.lastError
                            ? "REFUSED // " + root.changesService.lastError
                            : root.changesService.actionBusy
                            ? root.changesService.actionName + " // RUNNING"
                            : root.changesService.actionStatus
                          )
                        : "NO CHANGE SERVICE"
                    font.pixelSize: 10
                    color:
                        root.armedAction
                        ? Colors.orange
                        : root.changesService
                          && root.changesService.lastError
                        ? Colors.red
                        : Colors.cyan
                    elide: Text.ElideRight
                }
            }
        }
    }

    GitChangeTransferView {
        id: changeTransferView

        anchors.fill: parent
        visible:
            root.transferOpen
            && root.transferScope !== "line"
        z: 5000

        transferService: root.transferService
        branchWorkspaceService: root.branchWorkspaceService
        sourcePath:
            root.gitService
            ? String(root.gitService.repoRoot || "")
            : ""
        filePath: root.selectedPath
        transferScope: root.transferScope
        transferLayer: root.transferLayer
        hunkIndex: root.transferHunkIndex
        hunkSummary:
            root.transferScope === "hunk"
            ? root.selectedHunkSummary()
            : ""

        onCloseRequested: root.closeTransfer()
    }

    GitLineTransferView {
        id: lineTransferView

        anchors.fill: parent
        visible:
            root.transferOpen
            && root.transferScope === "line"
        z: 5000

        lineTransferService: lineTransferService
        branchWorkspaceService: root.branchWorkspaceService
        sourcePath:
            root.gitService
            ? String(root.gitService.repoRoot || "")
            : ""
        filePath: root.selectedPath
        hunkIndex: root.transferHunkIndex
        lineIndex: root.transferLineIndex
        lineSummary: root.selectedLineSummary()

        onCloseRequested: root.closeTransfer()
    }

    Connections {
        target: lineTransferService
        ignoreUnknownSignals: true

        function onTransferFinished(success, detail) {
            if (!success)
                return;

            root.closeTransfer();
            root.clearArm();

            if (root.changesService)
                root.changesService.refresh();

            if (root.branchWorkspaceService)
                root.branchWorkspaceService.refresh();
        }
    }

    Connections {
        target: root.transferService
        enabled: root.transferService !== null
        ignoreUnknownSignals: true

        function onTransferFinished(success, detail) {
            if (!success)
                return;

            root.closeTransfer();
            root.clearArm();

            if (root.changesService)
                root.changesService.refresh();

            if (root.branchWorkspaceService)
                root.branchWorkspaceService.refresh();
        }
    }

    Connections {
        target: root.conflictEditorService
        enabled: root.conflictEditorService !== null
        ignoreUnknownSignals: true

        function onResultSaved(path, staged, success, detail) {
            if (!success)
                return;

            root.clearArm();

            if (root.changesService)
                root.changesService.refresh();
        }
    }

    Connections {
        target: root.changesService

        function onRefreshed() {
            root.applyPendingFocus();
            root.reconcileSelectedFile();
        }

        function onActionFinished(action, success, detail) {
            if (!success)
                return;

            root.clearArm();

            const actionText = String(action || "");

            if (
                actionText.indexOf("LINE") >= 0
                || actionText.indexOf("HUNK") >= 0
            ) {
                root.selectedHunkIndex = -1;
                root.selectedLineIndex = -1;
            }

            if (actionText === "COMMIT") {
                commitInput.text = "";
                root.commitAmend = false;
                root.commitAllowEmpty = false;
                root.commitNoVerify = false;
            }

            if (root.selectedPath)
                Qt.callLater(function() {
                    root.changesService.preview(
                        root.selectedPath,
                        root.diffMode
                    );
                });
        }
    }
}
