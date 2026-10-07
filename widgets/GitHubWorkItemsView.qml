import QtQuick
import Quickshell
import qs.components

Item {
    id: root

    required property var workService
    required property var projectService
    required property var gitService

    property string kind: "issues"
    property string stateFilter: "all"
    property string projectFilter: "all"
    property string searchText: ""
    property string armedProjectRemoveUrl: ""

    readonly property bool isPulls: kind === "pulls"
    readonly property var sourceRows:
        isPulls
        ? workService.pulls
        : workService.issues
    readonly property bool busy:
        isPulls
        ? workService.pullsBusy
        : workService.issuesBusy
    readonly property string lastError:
        isPulls
        ? workService.pullsError
        : workService.issuesError
    readonly property var visibleRows:
        filteredRows()

    function filteredRows() {
        const rows = Array.isArray(sourceRows) ? sourceRows : [];
        const state = String(stateFilter || "all").toLowerCase();
        const projectMode =
            String(projectFilter || "all").toLowerCase();
        const query = String(searchText || "").trim().toLowerCase();
        const out = [];

        for (let i = 0; i < rows.length; ++i) {
            const row = rows[i] || {};
            const rowState = workService.rowState(row).toLowerCase();
            const closedLike =
                rowState === "closed"
                || rowState === "merged";

            if (state === "open" && rowState !== "open")
                continue;

            if (state === "closed" && !closedLike)
                continue;

            const itemUrl = workService.rowUrl(row);
            const inProject =
                projectService.selectedNumber() > 0
                && projectService.containsItemUrl(itemUrl);

            if (projectMode === "in" && !inProject)
                continue;

            if (projectMode === "out" && inProject)
                continue;

            if (query) {
                const haystack = [
                    workService.rowNumber(row),
                    workService.rowTitle(row),
                    workService.rowAuthor(row),
                    workService.rowState(row),
                    isPulls
                    ? workService.pullBranches(row)
                    : workService.issueLabels(row).join(" "),
                    inProject
                    ? projectService.itemStatusByUrl(itemUrl)
                    : ""
                ].join(" ").toLowerCase();

                if (haystack.indexOf(query) < 0)
                    continue;
            }

            out.push(row);
        }

        return out;
    }

    function refresh() {
        armedProjectRemoveUrl = "";

        if (isPulls)
            workService.refreshPulls(gitService.repoRemoteSlug);
        else
            workService.refreshIssues(gitService.repoRemoteSlug);

        if (!projectService.busy
                && projectService.projects.length === 0)
            projectService.refreshProjects();
        else if (!projectService.busy
                && projectService.selectedNumber() > 0)
            projectService.refreshSelectedProject();
    }

    function stepProjectStatus(url, delta) {
        armedProjectRemoveUrl = "";
        projectService.moveItemStatusByUrl(url, delta);
    }

    function removeFromProject(url) {
        const clean = String(url || "");

        if (!clean)
            return;

        if (armedProjectRemoveUrl !== clean) {
            armedProjectRemoveUrl = clean;
            return;
        }

        armedProjectRemoveUrl = "";
        projectService.removeItemByUrl(clean, true);
    }

    component ViewButton: Rectangle {
        id: button

        property string label: ""
        property bool selectedAction: false
        property bool enabledAction: true
        property bool primaryBlue: false

        signal triggered()

        height: 28
        opacity: enabledAction ? 1.0 : 0.34
        color: selectedAction ? Colors.yellow : Colors.black
        border.width: 1
        border.color:
            selectedAction
            ? Colors.orange
            : primaryBlue
            ? Colors.blue
            : mouse.containsMouse
            ? Colors.orange
            : Colors.cyan

        GohuText {
            anchors.centerIn: parent
            text: button.label
            font.pixelSize: 8
            color:
                button.selectedAction
                ? Colors.magenta
                : button.primaryBlue
                ? Colors.blue
                : Colors.cyan
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

    component SearchField: Rectangle {
        id: field

        property alias text: editor.text
        property string placeholderText: "SEARCH"

        height: 28
        color: Colors.black
        border.width: 1
        border.color: editor.activeFocus ? Colors.orange : Colors.cyan

        TextInput {
            id: editor
            anchors {
                fill: parent
                leftMargin: 8
                rightMargin: 8
            }

            verticalAlignment: TextInput.AlignVCenter
            font.family: "GohuFont 11 Nerd Font Mono"
            font.pixelSize: 9
            color: Colors.white
            selectionColor: Colors.magenta
            selectedTextColor: Colors.black
            clip: true

            Text {
                anchors.verticalCenter: parent.verticalCenter
                visible: !editor.text && !editor.activeFocus
                text: field.placeholderText
                font.family: editor.font.family
                font.pixelSize: editor.font.pixelSize
                color: Colors.cyan
                opacity: 0.40
            }
        }
    }

    onVisibleChanged: {
        if (visible)
            refresh();
    }

    Connections {
        target: root.gitService

        function onRepoRemoteSlugChanged() {
            if (root.visible)
                root.refresh();
        }
    }

    Column {
        anchors.fill: parent
        spacing: 8

        Rectangle {
            width: parent.width
            height: 54
            color: Colors.dark
            border.width: 1
            border.color: Colors.cyan

            Column {
                anchors {
                    fill: parent
                    margins: 8
                }
                spacing: 3

                Row {
                    width: parent.width
                    height: 20

                    GohuText {
                        width: parent.width - 210
                        anchors.verticalCenter: parent.verticalCenter
                        text:
                            (root.isPulls ? "ALL PULL REQUESTS // " : "ALL ISSUES // ")
                            + String(root.visibleRows.length)
                        font.pixelSize: 12
                        color: Colors.magenta
                        elide: Text.ElideRight
                    }

                    GohuText {
                        width: 210
                        anchors.verticalCenter: parent.verticalCenter
                        horizontalAlignment: Text.AlignRight
                        text:
                            root.gitService.repoRemoteSlug
                            || "NO ACTIVE REPOSITORY"
                        font.pixelSize: 8
                        color:
                            root.gitService.repoRemoteSlug
                            ? Colors.blue
                            : Colors.orange
                        elide: Text.ElideLeft
                    }
                }

                GohuText {
                    width: parent.width
                    text:
                        "PROJECT TARGET // "
                        + (
                            root.projectService.selectedNumber() > 0
                            ? (
                                "#"
                                + String(root.projectService.selectedNumber())
                                + " // "
                                + root.projectService.selectedTitle()
                              )
                            : "NO PROJECT SELECTED"
                          )
                    font.pixelSize: 8
                    color:
                        root.projectService.selectedNumber() > 0
                        ? Colors.cyan
                        : Colors.orange
                    elide: Text.ElideRight
                }
            }
        }

        Row {
            width: parent.width
            height: 28
            spacing: 6

            ViewButton {
                width: 52
                height: parent.height
                label: "ALL"
                selectedAction: root.stateFilter === "all"
                onTriggered: root.stateFilter = "all"
            }

            ViewButton {
                width: 58
                height: parent.height
                label: "OPEN"
                selectedAction: root.stateFilter === "open"
                onTriggered: root.stateFilter = "open"
            }

            ViewButton {
                width: 64
                height: parent.height
                label: "CLOSED"
                selectedAction: root.stateFilter === "closed"
                onTriggered: root.stateFilter = "closed"
            }

            SearchField {
                id: searchField
                width: parent.width - 264
                height: parent.height
                placeholderText:
                    root.isPulls
                    ? "SEARCH PULL REQUESTS"
                    : "SEARCH ISSUES"

                onTextChanged:
                    root.searchText = text
            }

            ViewButton {
                width: 72
                height: parent.height
                label: root.busy ? "..." : "REFRESH"
                primaryBlue: true
                enabledAction: !root.busy && !!root.gitService.repoRemoteSlug
                onTriggered: root.refresh()
            }
        }

        Row {
            width: parent.width
            height: 28
            spacing: 6

            GohuText {
                width: 96
                anchors.verticalCenter: parent.verticalCenter
                text: "PROJECT FILTER"
                font.pixelSize: 8
                color: Colors.magenta
            }

            ViewButton {
                width: 62
                height: parent.height
                label: "ALL"
                selectedAction: root.projectFilter === "all"
                onTriggered: {
                    root.projectFilter = "all";
                    root.armedProjectRemoveUrl = "";
                }
            }

            ViewButton {
                width: 88
                height: parent.height
                label: "IN PROJECT"
                selectedAction: root.projectFilter === "in"
                enabledAction:
                    root.projectService.selectedNumber() > 0
                onTriggered: {
                    root.projectFilter = "in";
                    root.armedProjectRemoveUrl = "";
                }
            }

            ViewButton {
                width: 92
                height: parent.height
                label: "OUTSIDE"
                selectedAction: root.projectFilter === "out"
                enabledAction:
                    root.projectService.selectedNumber() > 0
                onTriggered: {
                    root.projectFilter = "out";
                    root.armedProjectRemoveUrl = "";
                }
            }

            GohuText {
                width: parent.width - 356
                anchors.verticalCenter: parent.verticalCenter
                horizontalAlignment: Text.AlignRight
                text:
                    root.projectService.selectedNumber() > 0
                    ? (
                        "#"
                        + String(root.projectService.selectedNumber())
                        + " // "
                        + root.projectService.selectedTitle()
                      )
                    : "NO PROJECT SELECTED"
                font.pixelSize: 8
                color:
                    root.projectService.selectedNumber() > 0
                    ? Colors.cyan
                    : Colors.orange
                elide: Text.ElideLeft
            }
        }

        Rectangle {
            width: parent.width
            height: parent.height - 134
            color: Colors.black
            border.width: 1
            border.color: root.lastError ? Colors.red : Colors.cyan

            ListView {
                id: sourceList

                anchors {
                    fill: parent
                    margins: 8
                    rightMargin: 13
                }

                clip: true
                spacing: 5
                model: root.visibleRows
                boundsBehavior: Flickable.StopAtBounds

                delegate: Rectangle {
                    id: sourceRow

                    required property int index
                    required property var modelData

                    readonly property string itemUrl:
                        root.workService.rowUrl(modelData)
                    readonly property bool alreadyAdded:
                        root.projectService.containsItemUrl(itemUrl)
                    readonly property string projectStatus:
                        alreadyAdded
                        ? (
                            root.projectService.itemStatusByUrl(itemUrl)
                            || "NO STATUS"
                          )
                        : ""
                    readonly property string checkState:
                        root.isPulls
                        ? root.workService.pullCheckState(modelData)
                        : ""
                    readonly property string reviewState:
                        root.isPulls
                        ? root.workService.pullReviewState(modelData)
                        : ""
                    readonly property string mergeState:
                        root.isPulls
                        ? root.workService.pullMergeState(modelData)
                        : ""

                    width: sourceList.width
                    height: 104
                    color: Colors.dark
                    border.width: 1
                    border.color:
                        rowMouse.containsMouse
                        ? Colors.orange
                        : Colors.blue

                    Column {
                        anchors {
                            left: parent.left
                            right: actionColumn.left
                            top: parent.top
                            bottom: parent.bottom
                            margins: 7
                            rightMargin: 8
                        }
                        spacing: 4

                        Row {
                            id: workTitleRow

                            width: parent.width
                            height: 22
                            spacing: 3

                            GohuText {
                                id: workNumberLabel

                                width: implicitWidth
                                anchors.verticalCenter: parent.verticalCenter
                                text:
                                    "#"
                                    + String(
                                        root.workService.rowNumber(
                                            sourceRow.modelData
                                        )
                                      )
                                font.pixelSize: 10
                                color: Colors.orange
                            }

                            GohuText {
                                width:
                                    parent.width
                                    - workNumberLabel.width
                                    - workTitleRow.spacing
                                anchors.verticalCenter: parent.verticalCenter
                                text:
                                    root.workService.rowTitle(
                                        sourceRow.modelData
                                    )
                                font.pixelSize: 11
                                color: Colors.white
                                elide: Text.ElideRight
                            }
                        }

                        GohuText {
                            width: parent.width
                            text:
                                root.workService.rowState(sourceRow.modelData)
                                + (
                                    root.workService.pullIsDraft(sourceRow.modelData)
                                    ? " // DRAFT"
                                    : ""
                                  )
                                + (
                                    root.workService.rowAuthor(sourceRow.modelData)
                                    ? " // @"
                                      + root.workService.rowAuthor(
                                          sourceRow.modelData
                                        )
                                    : ""
                                  )
                            font.pixelSize: 8
                            color:
                                root.workService.rowState(sourceRow.modelData)
                                === "OPEN"
                                ? Colors.cyan
                                : Colors.orange
                            elide: Text.ElideRight
                        }

                        Row {
                            width: parent.width
                            height: root.isPulls ? 15 : 0
                            visible: root.isPulls
                            spacing: 8

                            GohuText {
                                width: (parent.width - 16) / 3
                                anchors.verticalCenter: parent.verticalCenter
                                text:
                                    "CHECKS // "
                                    + root.workService.pullCheckSummary(
                                        sourceRow.modelData
                                    )
                                font.pixelSize: 8
                                color:
                                    sourceRow.checkState === "FAIL"
                                    || sourceRow.checkState === "ERROR"
                                    ? Colors.red
                                    : sourceRow.checkState === "PENDING"
                                    ? Colors.orange
                                    : sourceRow.checkState === "PASS"
                                    ? Colors.cyan
                                    : Colors.white
                                opacity:
                                    sourceRow.checkState === "NONE"
                                    ? 0.46
                                    : 1.0
                                elide: Text.ElideRight
                            }

                            GohuText {
                                width: (parent.width - 16) / 3
                                anchors.verticalCenter: parent.verticalCenter
                                text:
                                    "APPROVAL // "
                                    + root.workService.pullReviewSummary(
                                        sourceRow.modelData
                                    )
                                font.pixelSize: 8
                                color:
                                    sourceRow.reviewState === "CHANGES_REQUESTED"
                                    || sourceRow.reviewState === "ERROR"
                                    ? Colors.red
                                    : sourceRow.reviewState === "REVIEW_REQUIRED"
                                    ? Colors.orange
                                    : sourceRow.reviewState === "APPROVED"
                                    ? Colors.cyan
                                    : Colors.white
                                opacity:
                                    sourceRow.reviewState === "NONE"
                                    ? 0.46
                                    : 1.0
                                elide: Text.ElideRight
                            }

                            GohuText {
                                width: (parent.width - 16) / 3
                                anchors.verticalCenter: parent.verticalCenter
                                text:
                                    "MERGE // "
                                    + root.workService.pullMergeSummary(
                                        sourceRow.modelData
                                    )
                                font.pixelSize: 8
                                color:
                                    sourceRow.mergeState === "BLOCKED"
                                    || sourceRow.mergeState === "DIRTY"
                                    ? Colors.red
                                    : sourceRow.mergeState === "BEHIND"
                                    || sourceRow.mergeState === "UNSTABLE"
                                    ? Colors.orange
                                    : sourceRow.mergeState === "CLEAN"
                                    ? Colors.cyan
                                    : Colors.white
                                elide: Text.ElideRight
                            }
                        }

                        GohuText {
                            width: parent.width
                            text:
                                (
                                    root.isPulls
                                    ? (
                                        root.workService.pullBranches(
                                            sourceRow.modelData
                                        )
                                        || "BRANCH DATA UNAVAILABLE"
                                      )
                                    : (
                                        root.workService.issueLabels(
                                            sourceRow.modelData
                                        ).join(" // ")
                                        || "NO LABELS"
                                      )
                                )
                                + (
                                    sourceRow.alreadyAdded
                                    ? (
                                        " // PROJECT "
                                        + sourceRow.projectStatus
                                      )
                                    : ""
                                  )
                            font.pixelSize: 7
                            color: Colors.cyan
                            opacity: 0.60
                            elide: Text.ElideRight
                        }
                    }

                    Column {
                        id: actionColumn

                        anchors {
                            right: parent.right
                            verticalCenter: parent.verticalCenter
                            rightMargin: 7
                        }

                        width: 126
                        spacing: 5

                        ViewButton {
                            width: parent.width
                            height: 25
                            label: "OPEN"
                            enabledAction: !!sourceRow.itemUrl
                            onTriggered: {
                                root.armedProjectRemoveUrl = "";
                                Qt.openUrlExternally(sourceRow.itemUrl);
                            }
                        }

                        ViewButton {
                            visible: !sourceRow.alreadyAdded
                            width: parent.width
                            height: 25
                            label: "ADD TO PROJECT"
                            primaryBlue: true
                            enabledAction:
                                !root.projectService.busy
                                && root.projectService.selectedNumber() > 0
                                && !!sourceRow.itemUrl
                            onTriggered: {
                                root.armedProjectRemoveUrl = "";
                                root.projectService.addExistingItem(
                                    sourceRow.itemUrl,
                                    root.isPulls ? "pull" : "issue"
                                );
                            }
                        }

                        Row {
                            visible: sourceRow.alreadyAdded
                            width: parent.width
                            height: 25
                            spacing: 4

                            ViewButton {
                                width: (parent.width - 4) / 2
                                height: parent.height
                                label: "◀ STATUS"
                                enabledAction:
                                    !root.projectService.busy
                                    && root.projectService.statusOptions().length > 0
                                onTriggered:
                                    root.stepProjectStatus(
                                        sourceRow.itemUrl,
                                        -1
                                    )
                            }

                            ViewButton {
                                width: (parent.width - 4) / 2
                                height: parent.height
                                label: "STATUS ▶"
                                enabledAction:
                                    !root.projectService.busy
                                    && root.projectService.statusOptions().length > 0
                                onTriggered:
                                    root.stepProjectStatus(
                                        sourceRow.itemUrl,
                                        1
                                    )
                            }
                        }

                        ViewButton {
                            visible: sourceRow.alreadyAdded
                            width: parent.width
                            height: 25
                            label:
                                root.armedProjectRemoveUrl
                                === sourceRow.itemUrl
                                ? "CONFIRM REMOVE"
                                : "REMOVE PROJECT"
                            enabledAction:
                                !root.projectService.busy
                            onTriggered:
                                root.removeFromProject(
                                    sourceRow.itemUrl
                                )
                        }
                    }

                    MouseArea {
                        id: rowMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        acceptedButtons: Qt.NoButton
                    }
                }

                GohuText {
                    anchors.centerIn: parent
                    visible:
                        !root.busy
                        && root.visibleRows.length === 0
                    text:
                        root.lastError
                        ? "ERROR // " + root.lastError
                        : root.gitService.repoRemoteSlug
                        ? (
                            root.searchText
                            || root.stateFilter !== "all"
                            ? "NO MATCHING ITEMS"
                            : root.isPulls
                            ? "NO PULL REQUESTS"
                            : "NO ISSUES"
                          )
                        : "SELECT A REPOSITORY"
                    font.pixelSize: 10
                    color:
                        root.lastError
                        ? Colors.red
                        : Colors.white
                    opacity: root.lastError ? 1.0 : 0.40
                }
            }

            Rectangle {
                id: scrollTrack

                width: 4
                anchors {
                    top: parent.top
                    bottom: parent.bottom
                    right: parent.right
                    margins: 5
                }

                color: Colors.dark
                visible: sourceList.contentHeight > sourceList.height

                Rectangle {
                    width: parent.width
                    height:
                        Math.max(
                            18,
                            parent.height
                            * sourceList.height
                            / Math.max(
                                sourceList.height,
                                sourceList.contentHeight
                            )
                        )
                    y:
                        (
                            parent.height - height
                        )
                        * (
                            sourceList.contentY
                            / Math.max(
                                1,
                                sourceList.contentHeight
                                - sourceList.height
                            )
                          )
                    color: Colors.magenta
                }
            }
        }
    }
}
