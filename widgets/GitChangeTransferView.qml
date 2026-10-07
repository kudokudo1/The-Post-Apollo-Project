import QtQuick
import qs.components

Rectangle {
    id: root

    required property var transferService
    required property var branchWorkspaceService

    property string sourcePath: ""
    property string filePath: ""
    property bool untrackedSource: false
    property string transferScope: "file"
    property string transferLayer: "worktree"
    property int hunkIndex: -1
    property string hunkSummary: ""
    property string selectedDestinationPath: ""
    property string transferMode: "move"
    property bool createDestinationOpen: false
    property string pendingCreatedDestinationPath: ""
    property string pendingCreatedDestinationBranch: ""
    property string createDestinationMessage: ""

    signal closeRequested()

    color: Colors.dark
    border.width: 1
    border.color: Colors.magenta

    readonly property var candidates:
        branchWorkspaceService
        && Array.isArray(branchWorkspaceService.worktrees)
        ? branchWorkspaceService.worktrees.filter(function(row) {
            const path = String((row || {}).path || "");
            return path && path !== String(root.sourcePath || "");
        })
        : []

    readonly property var selectedWorktree: {
        const needle = String(selectedDestinationPath || "");

        for (let i = 0; i < candidates.length; ++i) {
            const row = candidates[i] || {};
            if (String(row.path || "") === needle)
                return row;
        }

        return null;
    }

    readonly property bool destinationEligible:
        selectedWorktree
        && String(selectedWorktree.branch || "").length > 0
        && !Boolean(selectedWorktree.detached)
        && Number(selectedWorktree.dirtyCount || 0) === 0

    readonly property string effectiveLayer:
        untrackedSource
        ? "untracked"
        : String(transferLayer || "worktree").toLowerCase() === "conflict-result"
        ? "conflict-result"
        : String(transferLayer || "worktree").toLowerCase() === "partial"
        ? "partial"
        : String(transferLayer || "worktree").toLowerCase() === "staged"
        ? "staged"
        : "worktree"

    readonly property bool conflictResultLayer:
        transferScope === "file"
        && effectiveLayer === "conflict-result"

    readonly property bool stagedLayer:
        transferScope === "file"
        && effectiveLayer === "staged"

    readonly property bool previewMatchesSelection:
        transferService
        && transferService.hasPreview
        && String(transferService.previewDestinationPath || "")
            === String(selectedDestinationPath || "")
        && String(transferService.previewMode || "")
            === String(transferMode || "")
        && String(transferService.previewScope || "file")
            === String(transferScope || "file")
        && String(transferService.previewLayer || "worktree")
            === String(root.effectiveLayer || "worktree")
        && (
            transferScope !== "hunk"
            || Number(transferService.previewHunkIndex)
                === Number(hunkIndex)
           )
        && transferService.previewFiles.length === 1
        && String(transferService.previewFiles[0] || "")
            === String(filePath || "")

    function invalidatePreview() {
        if (transferService && transferService.hasPreview)
            transferService.clearPreview();
    }

    function chooseDestination(path) {
        const next = String(path || "");

        if (selectedDestinationPath === next)
            return;

        selectedDestinationPath = next;
        invalidatePreview();
    }

    function chooseMode(mode) {
        const requested =
            String(mode || "").toLowerCase() === "copy"
            ? "copy"
            : "move";
        const next =
            root.conflictResultLayer
            ? "copy"
            : requested;

        if (transferMode === next)
            return;

        transferMode = next;
        invalidatePreview();
    }

    function defaultDestinationPath(branchName) {
        const source = String(root.sourcePath || "").trim();
        const branch =
            String(branchName || "").trim().split("/").join("-");

        if (!source || !branch)
            return "";

        return source + "-wt-" + branch;
    }

    function openCreateDestination() {
        root.createDestinationOpen = !root.createDestinationOpen;
        root.createDestinationMessage = "";
        root.invalidatePreview();

        if (!root.createDestinationOpen)
            return;

        newDestinationBranchEditor.text = "";
        newDestinationPathEditor.text = "";
        Qt.callLater(function() {
            newDestinationBranchEditor.focusEditor();
        });
    }

    function createDestination() {
        if (!root.branchWorkspaceService
                || root.branchWorkspaceService.actionBusy
                || root.branchWorkspaceService.refreshing
                || root.transferService.previewBusy
                || root.transferService.transferBusy)
            return false;

        const branch =
            String(newDestinationBranchEditor.text || "").trim();
        const enteredPath =
            String(newDestinationPathEditor.text || "").trim();
        const path =
            enteredPath || root.defaultDestinationPath(branch);

        if (!branch) {
            root.createDestinationMessage =
                "REFUSED // NEW BRANCH NAME REQUIRED";
            return false;
        }

        if (!path) {
            root.createDestinationMessage =
                "REFUSED // DESTINATION PATH REQUIRED";
            return false;
        }

        if (root.branchWorkspaceService.branchForName(branch)) {
            root.createDestinationMessage =
                "REFUSED // LOCAL BRANCH ALREADY EXISTS";
            return false;
        }

        root.pendingCreatedDestinationBranch = branch;
        root.pendingCreatedDestinationPath = path;
        root.createDestinationMessage =
            "CREATING // " + branch;

        if (!root.branchWorkspaceService.createWorktree(
                path,
                branch,
                "HEAD"
            )) {
            root.pendingCreatedDestinationBranch = "";
            root.pendingCreatedDestinationPath = "";
            root.createDestinationMessage =
                "REFUSED // BRANCH CORE BUSY";
            return false;
        }

        return true;
    }

    function requestPreview() {
        if (!transferService
                || !destinationEligible
                || !filePath
                || transferService.previewBusy
                || transferService.transferBusy)
            return false;

        if (transferScope === "hunk") {
            return transferService.previewHunk(
                selectedDestinationPath,
                filePath,
                hunkIndex,
                transferMode
            );
        }

        if (root.effectiveLayer === "conflict-result") {
            return transferService.previewConflictResult(
                selectedDestinationPath,
                filePath,
                "copy"
            );
        }

        if (root.effectiveLayer === "untracked") {
            return transferService.previewUntracked(
                selectedDestinationPath,
                [filePath],
                transferMode
            );
        }

        if (root.effectiveLayer === "partial") {
            return transferService.previewPartial(
                selectedDestinationPath,
                [filePath],
                transferMode
            );
        }

        if (root.effectiveLayer === "staged") {
            return transferService.previewStaged(
                selectedDestinationPath,
                [filePath],
                transferMode
            );
        }

        return transferService.preview(
            selectedDestinationPath,
            [filePath],
            transferMode
        );
    }

    function executeTransfer() {
        if (!transferService
                || !previewMatchesSelection
                || transferService.transferBusy)
            return false;

        return transferService.execute();
    }

    onFilePathChanged: invalidatePreview()
    onUntrackedSourceChanged: invalidatePreview()
    onSourcePathChanged: invalidatePreview()
    onTransferScopeChanged: invalidatePreview()
    onTransferLayerChanged: {
        if (root.conflictResultLayer)
            root.transferMode = "copy";
        invalidatePreview();
    }
    onHunkIndexChanged: invalidatePreview()

    Connections {
        target: branchWorkspaceService
        ignoreUnknownSignals: true

        function onActionFinished(action, success, detail) {
            if (String(action || "") !== "NEW-WORKTREE"
                    || !root.pendingCreatedDestinationPath)
                return;

            root.createDestinationMessage =
                success
                ? "OK // DESTINATION CREATED // SELECTING"
                : "REFUSED // " + String(detail || "CREATE FAILED");

            if (!success) {
                root.pendingCreatedDestinationBranch = "";
                root.pendingCreatedDestinationPath = "";
            }
        }

        function onRefreshed() {
            if (root.pendingCreatedDestinationPath) {
                const createdPath =
                    String(root.pendingCreatedDestinationPath || "");
                const rows =
                    Array.isArray(branchWorkspaceService.worktrees)
                    ? branchWorkspaceService.worktrees
                    : [];
                let found = false;

                for (let i = 0; i < rows.length; ++i) {
                    if (String((rows[i] || {}).path || "")
                            === createdPath) {
                        found = true;
                        break;
                    }
                }

                if (found) {
                    root.chooseDestination(createdPath);
                    root.createDestinationMessage =
                        "OK // NEW DESTINATION SELECTED // PREVIEW REQUIRED";
                    root.pendingCreatedDestinationBranch = "";
                    root.pendingCreatedDestinationPath = "";
                    root.createDestinationOpen = false;
                    return;
                }
            }

            const selected = root.selectedWorktree;

            if (!selected)
                root.selectedDestinationPath = "";
        }
    }

    component DestinationEditor: Rectangle {
        id: editorBox

        property alias text: editor.text
        property string placeholder: ""

        function focusEditor() {
            editor.forceActiveFocus();
        }

        height: 28
        color: Colors.dark
        border.width: 1
        border.color:
            editor.activeFocus
            ? Colors.orange
            : Colors.cyan

        TextInput {
            id: editor

            anchors {
                fill: parent
                leftMargin: 7
                rightMargin: 7
            }

            verticalAlignment: Text.AlignVCenter
            color: Colors.white
            selectionColor: Colors.magenta
            selectedTextColor: Colors.black
            font.family: "GohuFont 11 Nerd Font Mono"
            font.pixelSize: 9
            clip: true
        }

        GohuText {
            anchors {
                left: parent.left
                verticalCenter: parent.verticalCenter
                leftMargin: 7
            }
            visible: editor.text.length === 0
            text: editorBox.placeholder
            font.pixelSize: 8
            color: Colors.white
            opacity: 0.34
        }
    }

    component TransferButton: Rectangle {
        id: button

        property string label: ""
        property bool enabledAction: true
        property bool selectedAction: false
        property color accent: Colors.cyan

        signal triggered()

        height: 32
        opacity: enabledAction ? 1.0 : 0.34
        color:
            selectedAction || mouse.containsMouse
            ? Colors.black
            : Colors.dark
        border.width: 1
        border.color:
            selectedAction || mouse.containsMouse
            ? accent
            : Colors.cyan

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
        anchors.margins: 10
        spacing: 8

        Row {
            width: parent.width
            height: 36
            spacing: 8

            Column {
                width: parent.width - 46
                anchors.verticalCenter: parent.verticalCenter
                spacing: 2

                GohuText {
                    text:
                        root.transferScope === "hunk"
                        ? "TRANSFER // HUNK "
                            + String(root.hunkIndex + 1)
                        : root.effectiveLayer === "conflict-result"
                        ? "TRANSFER // CONFLICT RESULT COPY"
                        : root.effectiveLayer === "untracked"
                        ? "TRANSFER // UNTRACKED WHOLE FILE"
                        : root.effectiveLayer === "partial"
                        ? "TRANSFER // PARTIALLY STAGED WHOLE FILE"
                        : root.effectiveLayer === "staged"
                        ? "TRANSFER // STAGED WHOLE FILE"
                        : "TRANSFER // WORKTREE WHOLE FILE"
                    font.pixelSize: 13
                    color: Colors.magenta
                }

                GohuText {
                    width: parent.width
                    text:
                        filePath
                        ? (
                            root.transferScope === "hunk"
                            && root.hunkSummary
                            ? filePath + " // " + root.hunkSummary
                            : filePath
                          )
                        : "NO FILE SELECTED"
                    font.pixelSize: 9
                    color: Colors.white
                    elide: Text.ElideMiddle
                }
            }

            TransferButton {
                width: 38
                label: "X"
                accent: Colors.red
                onTriggered: root.closeRequested()
            }
        }

        Rectangle {
            width: parent.width
            height: 46
            color: Colors.black
            border.width: 1
            border.color: Colors.orange

            GohuText {
                anchors.fill: parent
                anchors.margins: 7
                verticalAlignment: Text.AlignVCenter
                text:
                    root.transferScope === "hunk"
                    ? (
                        "HUNK SLICE // WORKTREE HUNK ONLY // "
                        + "DESTINATION MUST BE A CLEAN EXISTING WORKTREE"
                      )
                    : root.effectiveLayer === "conflict-result"
                    ? (
                        "COPY CURRENT CONFLICT RESULT ONLY // "
                        + "BASE / OURS / THEIRS STAY WITH SOURCE OPERATION // "
                        + "MOVE IS REFUSED"
                      )
                    : root.effectiveLayer === "untracked"
                    ? (
                        "UNTRACKED REGULAR FILE // "
                        + "DESTINATION PATH MUST NOT EXIST // "
                        + "DESTINATION WORKTREE MUST BE CLEAN"
                      )
                    : root.effectiveLayer === "partial"
                    ? (
                        "TRACKED + PARTIALLY STAGED WHOLE FILE // "
                        + "PRESERVE INDEX + WORKTREE LAYERS // "
                        + "DESTINATION MUST BE A CLEAN EXISTING WORKTREE"
                      )
                    : root.effectiveLayer === "staged"
                    ? (
                        "TRACKED + STAGED WHOLE FILE // INDEX LAYER // "
                        + "DESTINATION MUST BE A CLEAN EXISTING WORKTREE"
                      )
                    : (
                        "TRACKED + UNSTAGED WHOLE FILE // WORKTREE LAYER // "
                        + "DESTINATION MUST BE A CLEAN EXISTING WORKTREE"
                      )
                font.pixelSize: 9
                color: Colors.orange
                wrapMode: Text.Wrap
            }
        }

        Row {
            width: parent.width
            height: parent.height - 148
            spacing: 8

            Rectangle {
                width: 430
                height: parent.height
                color: Colors.black
                border.width: 1
                border.color: Colors.cyan

                Column {
                    anchors.fill: parent
                    anchors.margins: 7
                    spacing: 5

                    Row {
                        width: parent.width
                        height: 30
                        spacing: 6

                        GohuText {
                            width: parent.width - 194
                            anchors.verticalCenter: parent.verticalCenter
                            text:
                                "DESTINATION WORKTREE // "
                                + String(root.candidates.length)
                            font.pixelSize: 10
                            color: Colors.cyan
                        }

                        TransferButton {
                            width: 88
                            height: 30
                            label:
                                root.createDestinationOpen
                                ? "CANCEL"
                                : "NEW"
                            accent:
                                root.createDestinationOpen
                                ? Colors.red
                                : Colors.orange
                            enabledAction:
                                branchWorkspaceService
                                && !branchWorkspaceService.actionBusy
                                && !transferService.previewBusy
                                && !transferService.transferBusy
                            onTriggered:
                                root.openCreateDestination()
                        }

                        TransferButton {
                            width: 94
                            height: 30
                            label:
                                branchWorkspaceService
                                && branchWorkspaceService.refreshing
                                ? "READING"
                                : "REFRESH"
                            accent: Colors.green
                            enabledAction:
                                branchWorkspaceService
                                && !branchWorkspaceService.refreshing
                                && !transferService.transferBusy
                            onTriggered:
                                branchWorkspaceService.refresh()
                        }
                    }

                    Rectangle {
                        width: parent.width
                        height: root.createDestinationOpen ? 104 : 0
                        visible: root.createDestinationOpen
                        color: Colors.dark
                        border.width: 1
                        border.color: Colors.orange
                        clip: true

                        Column {
                            anchors.fill: parent
                            anchors.margins: 6
                            spacing: 5

                            Row {
                                width: parent.width
                                height: 28
                                spacing: 5

                                DestinationEditor {
                                    id: newDestinationBranchEditor
                                    width: 150
                                    placeholder: "NEW BRANCH"
                                }

                                DestinationEditor {
                                    id: newDestinationPathEditor
                                    width: parent.width - 237
                                    placeholder:
                                        root.defaultDestinationPath(
                                            newDestinationBranchEditor.text
                                        )
                                        || "PATH // AUTO FROM BRANCH"
                                }

                                TransferButton {
                                    width: 77
                                    height: 28
                                    label:
                                        branchWorkspaceService.actionBusy
                                        ? "CREATING"
                                        : "CREATE"
                                    accent: Colors.orange
                                    enabledAction:
                                        newDestinationBranchEditor.text.length > 0
                                        && !branchWorkspaceService.actionBusy
                                        && !branchWorkspaceService.refreshing
                                        && !transferService.previewBusy
                                        && !transferService.transferBusy
                                    onTriggered: root.createDestination()
                                }
                            }

                            GohuText {
                                width: parent.width
                                text:
                                    root.createDestinationMessage
                                    || (
                                        "CREATE FROM SOURCE HEAD // "
                                        + "SEPARATE GUARDED OPERATION // "
                                        + "PREVIEW STILL REQUIRED"
                                       )
                                font.pixelSize: 8
                                color:
                                    root.createDestinationMessage.indexOf(
                                        "REFUSED"
                                    ) === 0
                                    ? Colors.red
                                    : Colors.cyan
                                wrapMode: Text.Wrap
                            }
                        }
                    }

                    Flickable {
                        id: worktreeScroll

                        width: parent.width
                        height:
                            parent.height
                            - 35
                            - (root.createDestinationOpen ? 109 : 0)
                        clip: true
                        contentWidth: width
                        contentHeight: worktreeColumn.implicitHeight
                        boundsBehavior: Flickable.StopAtBounds

                        Column {
                            id: worktreeColumn

                            width: parent.width
                            spacing: 4

                            GohuText {
                                visible: root.candidates.length === 0
                                width: parent.width
                                topPadding: 22
                                horizontalAlignment: Text.AlignHCenter
                                text:
                                    "NO OTHER WORKTREES // "
                                    + "USE NEW TO CREATE ONE HERE"
                                font.pixelSize: 10
                                color: Colors.orange
                            }

                            Repeater {
                                model: root.candidates

                                Rectangle {
                                    id: worktreeRow

                                    required property var modelData

                                    readonly property bool eligible:
                                        String(modelData.branch || "").length > 0
                                        && !Boolean(modelData.detached)
                                        && Number(modelData.dirtyCount || 0) === 0
                                    readonly property bool selected:
                                        String(root.selectedDestinationPath || "")
                                        === String(modelData.path || "")

                                    width: worktreeColumn.width
                                    height: 58
                                    color:
                                        selected || rowMouse.containsMouse
                                        ? Colors.dark
                                        : "transparent"
                                    border.width: selected ? 1 : 0
                                    border.color:
                                        eligible
                                        ? Colors.green
                                        : Colors.red
                                    opacity: eligible ? 1.0 : 0.48

                                    Column {
                                        anchors.fill: parent
                                        anchors.margins: 6
                                        spacing: 3

                                        Row {
                                            width: parent.width

                                            GohuText {
                                                width: parent.width - 90
                                                text:
                                                    String(
                                                        worktreeRow.modelData.branch
                                                        || "DETACHED"
                                                    )
                                                font.pixelSize: 10
                                                color:
                                                    worktreeRow.eligible
                                                    ? Colors.green
                                                    : Colors.red
                                                elide: Text.ElideRight
                                            }

                                            GohuText {
                                                width: 90
                                                horizontalAlignment:
                                                    Text.AlignRight
                                                text:
                                                    worktreeRow.eligible
                                                    ? "READY"
                                                    : Number(
                                                        worktreeRow.modelData.dirtyCount
                                                        || 0
                                                      ) > 0
                                                    ? "DIRTY"
                                                    : "REFUSED"
                                                font.pixelSize: 8
                                                color:
                                                    worktreeRow.eligible
                                                    ? Colors.cyan
                                                    : Colors.red
                                            }
                                        }

                                        GohuText {
                                            width: parent.width
                                            text:
                                                String(
                                                    worktreeRow.modelData.path
                                                    || ""
                                                )
                                            font.pixelSize: 8
                                            color: Colors.white
                                            elide: Text.ElideMiddle
                                        }
                                    }

                                    MouseArea {
                                        id: rowMouse

                                        anchors.fill: parent
                                        enabled: worktreeRow.eligible
                                        hoverEnabled: true
                                        cursorShape:
                                            enabled
                                            ? Qt.PointingHandCursor
                                            : Qt.ArrowCursor
                                        onClicked:
                                            root.chooseDestination(
                                                worktreeRow.modelData.path
                                            )
                                    }
                                }
                            }
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
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 7

                    GohuText {
                        width: parent.width
                        text:
                            root.selectedWorktree
                            ? (
                                "TARGET // "
                                + String(
                                    root.selectedWorktree.branch
                                    || "DETACHED"
                                  )
                              )
                            : "SELECT A DESTINATION"
                        font.pixelSize: 11
                        color: Colors.magenta
                        elide: Text.ElideRight
                    }

                    GohuText {
                        width: parent.width
                        text:
                            root.selectedWorktree
                            ? String(root.selectedWorktree.path || "")
                            : "—"
                        font.pixelSize: 9
                        color: Colors.white
                        elide: Text.ElideMiddle
                    }

                    Row {
                        width: parent.width
                        height: 32
                        spacing: 6

                        TransferButton {
                            width: (parent.width - 6) / 2
                            label: "MOVE"
                            accent: Colors.orange
                            selectedAction: root.transferMode === "move"
                            enabledAction:
                                !root.conflictResultLayer
                                && !transferService.previewBusy
                                && !transferService.transferBusy
                            onTriggered: root.chooseMode("move")
                        }

                        TransferButton {
                            width: (parent.width - 6) / 2
                            label: "COPY"
                            accent: Colors.cyan
                            selectedAction: root.transferMode === "copy"
                            enabledAction:
                                !transferService.previewBusy
                                && !transferService.transferBusy
                            onTriggered: root.chooseMode("copy")
                        }
                    }

                    Rectangle {
                        width: parent.width
                        height: 108
                        color: Colors.dark
                        border.width: 1
                        border.color:
                            root.previewMatchesSelection
                            ? Colors.green
                            : Colors.cyan

                        Column {
                            anchors.fill: parent
                            anchors.margins: 7
                            spacing: 4

                            GohuText {
                                text:
                                    root.previewMatchesSelection
                                    ? "PREVIEW // VERIFIED"
                                    : "PREVIEW // REQUIRED"
                                font.pixelSize: 9
                                color:
                                    root.previewMatchesSelection
                                    ? Colors.green
                                    : Colors.cyan
                            }

                            GohuText {
                                width: parent.width
                                text:
                                    root.previewMatchesSelection
                                    ? (
                                        "PATCH "
                                        + String(
                                            transferService.previewPatchBytes
                                        )
                                        + " B // "
                                        + String(
                                            transferService.previewPatchLines
                                        )
                                        + " LINES"
                                      )
                                    : String(
                                        transferService.status
                                        || "TRANSFER // READY"
                                      )
                                font.pixelSize: 9
                                color: Colors.white
                                wrapMode: Text.Wrap
                            }

                            GohuText {
                                visible: root.previewMatchesSelection
                                width: parent.width
                                text:
                                    root.previewMatchesSelection
                                    ? (
                                        transferService.previewSourceHead.slice(0, 10)
                                        + " → "
                                        + transferService.previewDestinationHead.slice(0, 10)
                                      )
                                    : ""
                                font.pixelSize: 8
                                color: Colors.orange
                                elide: Text.ElideRight
                            }
                        }
                    }

                    GohuText {
                        width: parent.width
                        height: 48
                        text:
                            transferService.lastError
                            ? "REFUSED // " + transferService.lastError
                            : String(transferService.status || "")
                        font.pixelSize: 9
                        color:
                            transferService.lastError
                            ? Colors.red
                            : Colors.cyan
                        wrapMode: Text.Wrap
                    }

                    Item {
                        width: parent.width
                        height: Math.max(0, parent.height - 314)
                    }

                    Row {
                        width: parent.width
                        height: 36
                        spacing: 6

                        TransferButton {
                            width: (parent.width - 6) / 2
                            height: 36
                            label:
                                transferService.previewBusy
                                ? "PREVIEWING"
                                : "PREVIEW"
                            accent: Colors.cyan
                            enabledAction:
                                root.destinationEligible
                                && root.filePath.length > 0
                                && !transferService.previewBusy
                                && !transferService.transferBusy
                            onTriggered: root.requestPreview()
                        }

                        TransferButton {
                            width: (parent.width - 6) / 2
                            height: 36
                            label:
                                transferService.transferBusy
                                ? "TRANSFERRING"
                                : root.previewMatchesSelection
                                ? "EXECUTE "
                                    + root.transferMode.toUpperCase()
                                : "EXECUTE"
                            accent: Colors.orange
                            enabledAction:
                                root.previewMatchesSelection
                                && !transferService.previewBusy
                                && !transferService.transferBusy
                            onTriggered: root.executeTransfer()
                        }
                    }
                }
            }
        }

        Rectangle {
            width: parent.width
            height: 42
            color: Colors.black
            border.width: 1
            border.color:
                transferService.lastError
                ? Colors.red
                : Colors.cyan

            GohuText {
                anchors.fill: parent
                anchors.margins: 7
                verticalAlignment: Text.AlignVCenter
                text:
                    transferService.lastError
                    ? transferService.lastError
                    : String(
                        transferService.status
                        || "TRANSFER // READY"
                      )
                font.pixelSize: 9
                color:
                    transferService.lastError
                    ? Colors.red
                    : Colors.cyan
                elide: Text.ElideRight
            }
        }
    }
}
