import QtQuick
import qs.components

Rectangle {
    id: root

    required property var lineTransferService
    required property var branchWorkspaceService

    property string sourcePath: ""
    property string filePath: ""
    property int hunkIndex: -1
    property int lineIndex: -1
    property string lineSummary: ""
    property string selectedDestinationPath: ""
    property string transferMode: "move"

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

    readonly property bool previewMatchesSelection:
        lineTransferService
        && lineTransferService.hasPreview
        && String(lineTransferService.destinationPath || "")
            === String(selectedDestinationPath || "")
        && String(lineTransferService.transferMode || "")
            === String(transferMode || "")
        && String(lineTransferService.filePath || "")
            === String(filePath || "")
        && Number(lineTransferService.hunkIndex) === Number(hunkIndex)
        && Number(lineTransferService.lineIndex) === Number(lineIndex)

    function invalidatePreview() {
        if (lineTransferService && lineTransferService.hasPreview)
            lineTransferService.clearPreview();
    }

    function chooseDestination(path) {
        const next = String(path || "");

        if (selectedDestinationPath === next)
            return;

        selectedDestinationPath = next;
        invalidatePreview();
    }

    function chooseMode(mode) {
        const next =
            String(mode || "").toLowerCase() === "copy"
            ? "copy"
            : "move";

        if (transferMode === next)
            return;

        transferMode = next;
        invalidatePreview();
    }

    function requestPreview() {
        if (!lineTransferService
                || !destinationEligible
                || !filePath
                || hunkIndex < 0
                || lineIndex < 0
                || lineTransferService.previewBusy
                || lineTransferService.transferBusy)
            return false;

        return lineTransferService.preview(
            selectedDestinationPath,
            filePath,
            hunkIndex,
            lineIndex,
            transferMode
        );
    }

    function executeTransfer() {
        if (!lineTransferService
                || !previewMatchesSelection
                || lineTransferService.transferBusy)
            return false;

        return lineTransferService.execute();
    }

    onFilePathChanged: invalidatePreview()
    onHunkIndexChanged: invalidatePreview()
    onLineIndexChanged: invalidatePreview()
    onSourcePathChanged: invalidatePreview()

    Connections {
        target: branchWorkspaceService
        ignoreUnknownSignals: true

        function onRefreshed() {
            if (!root.selectedWorktree)
                root.selectedDestinationPath = "";
        }
    }

    component LineTransferButton: Rectangle {
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
            height: 38
            spacing: 8

            Column {
                width: parent.width - 46
                anchors.verticalCenter: parent.verticalCenter
                spacing: 2

                GohuText {
                    text:
                        "TRANSFER // LINE "
                        + String(root.lineIndex + 1)
                    font.pixelSize: 13
                    color: Colors.magenta
                }

                GohuText {
                    width: parent.width
                    text:
                        root.filePath
                        ? (
                            root.lineSummary
                            ? root.filePath + " // " + root.lineSummary
                            : root.filePath
                          )
                        : "NO LINE SELECTED"
                    font.pixelSize: 9
                    color: Colors.white
                    elide: Text.ElideMiddle
                }
            }

            LineTransferButton {
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
                    "WORKTREE +/- LINE ONLY // NO STAGED OVERLAP // "
                    + "DESTINATION MUST BE A CLEAN EXISTING WORKTREE"
                font.pixelSize: 9
                color: Colors.orange
                wrapMode: Text.Wrap
            }
        }

        Row {
            width: parent.width
            height: parent.height - 150
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
                            width: parent.width - 100
                            anchors.verticalCenter: parent.verticalCenter
                            text:
                                "DESTINATION WORKTREE // "
                                + String(root.candidates.length)
                            font.pixelSize: 10
                            color: Colors.cyan
                        }

                        LineTransferButton {
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
                                && !lineTransferService.transferBusy
                            onTriggered:
                                branchWorkspaceService.refresh()
                        }
                    }

                    Flickable {
                        id: worktreeScroll

                        width: parent.width
                        height: parent.height - 35
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
                                    + "CREATE ONE IN BRANCHES"
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

                        LineTransferButton {
                            width: (parent.width - 6) / 2
                            label: "MOVE"
                            accent: Colors.orange
                            selectedAction: root.transferMode === "move"
                            enabledAction:
                                !lineTransferService.previewBusy
                                && !lineTransferService.transferBusy
                            onTriggered: root.chooseMode("move")
                        }

                        LineTransferButton {
                            width: (parent.width - 6) / 2
                            label: "COPY"
                            accent: Colors.cyan
                            selectedAction: root.transferMode === "copy"
                            enabledAction:
                                !lineTransferService.previewBusy
                                && !lineTransferService.transferBusy
                            onTriggered: root.chooseMode("copy")
                        }
                    }

                    Rectangle {
                        width: parent.width
                        height: 110
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
                                        + String(lineTransferService.patchBytes)
                                        + " B // "
                                        + String(lineTransferService.patchLines)
                                        + " LINES"
                                      )
                                    : String(
                                        lineTransferService.status
                                        || "LINE TRANSFER // READY"
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
                                        lineTransferService.sourceHead.slice(0, 10)
                                        + " → "
                                        + lineTransferService.destinationHead.slice(0, 10)
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
                            lineTransferService.lastError
                            ? "REFUSED // " + lineTransferService.lastError
                            : String(lineTransferService.status || "")
                        font.pixelSize: 9
                        color:
                            lineTransferService.lastError
                            ? Colors.red
                            : Colors.cyan
                        wrapMode: Text.Wrap
                    }

                    Item {
                        width: parent.width
                        height: Math.max(0, parent.height - 316)
                    }

                    Row {
                        width: parent.width
                        height: 36
                        spacing: 6

                        LineTransferButton {
                            width: (parent.width - 6) / 2
                            height: 36
                            label:
                                lineTransferService.previewBusy
                                ? "PREVIEWING"
                                : "PREVIEW"
                            accent: Colors.cyan
                            enabledAction:
                                root.destinationEligible
                                && root.filePath.length > 0
                                && root.hunkIndex >= 0
                                && root.lineIndex >= 0
                                && !lineTransferService.previewBusy
                                && !lineTransferService.transferBusy
                            onTriggered: root.requestPreview()
                        }

                        LineTransferButton {
                            width: (parent.width - 6) / 2
                            height: 36
                            label:
                                lineTransferService.transferBusy
                                ? "TRANSFERRING"
                                : root.previewMatchesSelection
                                ? "EXECUTE "
                                    + root.transferMode.toUpperCase()
                                : "EXECUTE"
                            accent: Colors.orange
                            enabledAction:
                                root.previewMatchesSelection
                                && !lineTransferService.previewBusy
                                && !lineTransferService.transferBusy
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
                lineTransferService.lastError
                ? Colors.red
                : Colors.cyan

            GohuText {
                anchors.fill: parent
                anchors.margins: 7
                verticalAlignment: Text.AlignVCenter
                text:
                    lineTransferService.lastError
                    ? lineTransferService.lastError
                    : String(
                        lineTransferService.status
                        || "LINE TRANSFER // READY"
                      )
                font.pixelSize: 9
                color:
                    lineTransferService.lastError
                    ? Colors.red
                    : Colors.cyan
                elide: Text.ElideRight
            }
        }
    }
}
