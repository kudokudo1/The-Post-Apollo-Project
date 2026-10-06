import QtQuick
import QtQuick.Effects
import Qt5Compat.GraphicalEffects
import qs.components

Item {
    id: root

    required property var gitService
    required property var branchWorkspaceService
    required property var branchStackStore
    required property var stackPlanner

    property string selectedBranch: ""
    property string selectedSha: ""

    readonly property var selectedBranchData:
        branchWorkspaceService && selectedBranch
        ? branchWorkspaceService.branchForName(selectedBranch)
        : null

    readonly property var selectedWorkspace:
        branchWorkspaceService && selectedBranch
        ? branchWorkspaceService.worktreeForBranch(selectedBranch)
        : null

    readonly property bool selectedIsCurrent:
        selectedBranch.length > 0
        && branchWorkspaceService
        && selectedBranch === branchWorkspaceService.currentBranch

    readonly property bool selectedIsOccupied:
        selectedWorkspace !== null

    readonly property string selectedStackParent:
        branchStackStore && selectedBranch
        ? branchStackStore.parentOf(selectedBranch)
        : ""

    readonly property var selectedStackChildren:
        branchStackStore && selectedBranch
        ? branchStackStore.childrenOf(selectedBranch)
        : []

    readonly property string selectedStackRoot:
        branchStackStore && selectedBranch
        ? branchStackStore.stackRoot(selectedBranch)
        : ""

    readonly property var selectedStackDescendants:
        branchStackStore && selectedBranch
        ? branchStackStore.descendantsOf(selectedBranch)
        : []

    signal createBranchRequested(string startPoint)
    signal renameBranchRequested(string branch)
    signal deleteBranchRequested(string branch)
    signal upstreamRequested(string branch)
    signal workspaceRequested(string branch)
    signal stackAboveRequested(string branch)
    signal stackBelowRequested(string branch)
    signal stackParentRequested(string branch)
    signal restackRequested(string branch)
    signal submitStackRequested(string branch)
    signal compareRequested(string branch)

    onSelectedBranchChanged: {
        if (stackPlanner)
            stackPlanner.clear();
    }

    Connections {
        target: root.branchStackStore
        enabled: root.branchStackStore !== null
        ignoreUnknownSignals: true

        function onRelationsChanged() {
            if (root.stackPlanner)
                root.stackPlanner.clear();
        }
    }

    Connections {
        target: root.branchWorkspaceService
        enabled: root.branchWorkspaceService !== null
        ignoreUnknownSignals: true

        function onRefreshed() {
            if (root.stackPlanner)
                root.stackPlanner.clear();
        }
    }

    function branchForHead(sha) {
        const needle = String(sha || "");

        if (!needle || !branchWorkspaceService)
            return "";

        const rows = branchWorkspaceService.branches || [];

        for (let i = 0; i < rows.length; ++i) {
            if (String((rows[i] || {}).head || "") === needle)
                return String((rows[i] || {}).name || "");
        }

        return "";
    }

    function selectBranch(name) {
        const candidate = String(name || "");

        selectedBranch = candidate;

        const row = branchWorkspaceService
            ? branchWorkspaceService.branchForName(candidate)
            : null;

        selectedSha = row ? String(row.head || "") : "";
    }

    function selectCommit(sha) {
        const candidate = String(sha || "");
        selectedSha = selectedSha === candidate ? "" : candidate;

        if (!selectedSha)
            return;

        const branch = branchForHead(selectedSha);

        if (branch)
            selectedBranch = branch;
    }

    function shortSha(value) {
        const sha = String(value || "");
        return sha.length > 10 ? sha.slice(0, 10) : sha;
    }

    component BranchButton: Rectangle {
        id: button

        property string label: ""
        property bool enabledAction: true
        property bool destructive: false
        property bool selectedAction: false
        signal triggered()

        height: 30
        color:
            !enabledAction
            ? Colors.black
            : mouse.pressed
            ? destructive ? Colors.red : Colors.orange
            : selectedAction
            ? Colors.dark
            : Colors.black

        border.width:
            enabledAction && (mouse.containsMouse || selectedAction)
            ? 2
            : 1

        border.color:
            !enabledAction
            ? Colors.cyan
            : destructive
            ? Colors.red
            : selectedAction
            ? Colors.magenta
            : mouse.containsMouse
            ? Colors.orange
            : Colors.cyan

        GohuText {
            anchors.centerIn: parent
            text: button.label
            font.pixelSize: 8
            color:
                mouse.pressed
                ? Colors.black
                : button.destructive
                ? Colors.red
                : button.selectedAction
                ? Colors.magenta
                : Colors.cyan
            opacity: button.enabledAction ? 1.0 : 0.34
        }

        MouseArea {
            id: mouse
            anchors.fill: parent
            enabled: button.enabledAction
            hoverEnabled: true
            cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
            onClicked: button.triggered()
        }
    }

    component FactRow: Row {
        property string label: ""
        property string value: ""
        property color valueColor: Colors.white

        width: parent ? parent.width : 0
        height: 18
        spacing: 8

        GohuText {
            width: 92
            anchors.verticalCenter: parent.verticalCenter
            text: parent.label
            font.pixelSize: 7
            color: Colors.magenta
        }

        GohuText {
            width: parent.width - 100
            anchors.verticalCenter: parent.verticalCenter
            text: parent.value || "—"
            font.pixelSize: 8
            color: parent.valueColor
            elide: Text.ElideMiddle
        }
    }

    Column {
        anchors.fill: parent
        spacing: 8

        Rectangle {
            width: parent.width
            height: 42
            color: Colors.dark
            border.width: 1
            border.color: Colors.magenta

            Row {
                anchors {
                    fill: parent
                    margins: 8
                }
                spacing: 12

                GohuText {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "BRANCHES // OPERATING MAP"
                    font.pixelSize: 12
                    color: Colors.magenta

                    layer.enabled: true
                    layer.effect: DropShadow {
                        radius: 7
                        samples: 9
                        opacity: 0.48
                        color: Colors.magenta
                        transparentBorder: true
                    }
                }

                GohuText {
                    anchors.verticalCenter: parent.verticalCenter
                    text:
                        branchWorkspaceService
                        ? String((branchWorkspaceService.branches || []).length)
                          + " LOCAL // "
                          + String((branchWorkspaceService.worktrees || []).length)
                          + " WORKSPACES"
                          + (
                              branchStackStore
                              ? " // "
                                + String(
                                    (branchStackStore.repositoryRelations || []).length
                                  )
                                + " STACK LINKS"
                              : ""
                            )
                        : "NO BRANCH SERVICE"
                    font.pixelSize: 8
                    color: Colors.cyan
                }

                Item {
                    width: Math.max(
                        0,
                        parent.width
                        - parent.children[0].implicitWidth
                        - parent.children[1].implicitWidth
                        - refreshButton.width
                        - parent.spacing * 3
                    )
                    height: 1
                }

                BranchButton {
                    id: refreshButton
                    width: 92
                    anchors.verticalCenter: parent.verticalCenter
                    label:
                        branchWorkspaceService
                        && branchWorkspaceService.refreshing
                        ? "READING"
                        : "REFRESH"
                    enabledAction:
                        branchWorkspaceService
                        && !branchWorkspaceService.refreshing
                        && !branchWorkspaceService.actionBusy

                    onTriggered: branchWorkspaceService.refresh()
                }
            }
        }

        Row {
            width: parent.width
            height: parent.height - 50
            spacing: 8

            Rectangle {
                id: mapPane

                width: parent.width * 0.70
                height: parent.height
                color: Colors.dark
                border.width: 1
                border.color: Colors.cyan

                BranchMap {
                    anchors {
                        fill: parent
                        margins: 1
                    }

                    topologyService: root.gitService
                    titleText:
                        root.selectedBranch
                        ? "REPOSITORY TOPOLOGY // " + root.selectedBranch
                        : "REPOSITORY TOPOLOGY"
                    selectedSha: root.selectedSha

                    onCommitSelected: function(sha) {
                        root.selectCommit(sha);
                    }
                }

                Rectangle {
                    anchors {
                        left: parent.left
                        bottom: parent.bottom
                        leftMargin: 12
                        bottomMargin: 10
                    }

                    width: Math.min(parent.width - 24, branchStripRow.implicitWidth + 12)
                    height: 32
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.blue
                    z: 80
                    clip: true

                    Flickable {
                        anchors {
                            fill: parent
                            margins: 4
                        }

                        contentWidth: branchStripRow.implicitWidth
                        contentHeight: height
                        boundsBehavior: Flickable.StopAtBounds
                        clip: true

                        Row {
                            id: branchStripRow
                            height: parent.height
                            spacing: 4

                            Repeater {
                                model:
                                    branchWorkspaceService
                                    ? branchWorkspaceService.branches
                                    : []

                                Rectangle {
                                    required property var modelData

                                    height: 22
                                    width: Math.max(
                                        92,
                                        Math.min(
                                            220,
                                            branchName.implicitWidth + 18
                                        )
                                    )

                                    readonly property bool isSelected:
                                        root.selectedBranch
                                        === String(modelData.name || "")

                                    readonly property bool isCurrent:
                                        branchWorkspaceService
                                        && String(modelData.name || "")
                                        === branchWorkspaceService.currentBranch

                                    readonly property var workspace:
                                        branchWorkspaceService
                                        ? branchWorkspaceService.worktreeForBranch(
                                              String(modelData.name || "")
                                          )
                                        : null

                                    color:
                                        isSelected
                                        ? Colors.dark
                                        : Colors.black
                                    border.width: isSelected ? 2 : 1
                                    border.color:
                                        isCurrent
                                        ? Colors.yellow
                                        : workspace
                                        ? Colors.magenta
                                        : isSelected
                                        ? Colors.orange
                                        : Colors.blue

                                    GohuText {
                                        id: branchName
                                        anchors.centerIn: parent
                                        text:
                                            (parent.isCurrent ? "★ " : "")
                                            + String(parent.modelData.name || "")
                                        font.pixelSize: 7
                                        color:
                                            parent.isCurrent
                                            ? Colors.yellow
                                            : parent.workspace
                                            ? Colors.magenta
                                            : parent.isSelected
                                            ? Colors.orange
                                            : Colors.cyan
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked:
                                            root.selectBranch(
                                                String(parent.modelData.name || "")
                                            )
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Rectangle {
                id: inspector

                width: parent.width - mapPane.width - parent.spacing
                height: parent.height
                color: Colors.dark
                border.width: 1
                border.color:
                    root.selectedBranch
                    ? Colors.magenta
                    : Colors.cyan

                Column {
                    anchors {
                        fill: parent
                        margins: 10
                    }
                    spacing: 8

                    GohuText {
                        width: parent.width
                        text:
                            root.selectedBranch
                            ? "SELECTED // " + root.selectedBranch
                            : "SELECT A BRANCH"
                        font.pixelSize: 11
                        color:
                            root.selectedBranch
                            ? Colors.magenta
                            : Colors.cyan
                        elide: Text.ElideMiddle
                    }

                    Rectangle {
                        width: parent.width
                        height: 1
                        color: Colors.cyan
                        opacity: 0.36
                    }

                    Column {
                        width: parent.width
                        spacing: 2

                        FactRow {
                            label: "HEAD"
                            value:
                                root.selectedBranchData
                                ? root.shortSha(root.selectedBranchData.head)
                                : ""
                            valueColor: Colors.orange
                        }

                        FactRow {
                            label: "UPSTREAM"
                            value:
                                root.selectedBranchData
                                ? String(root.selectedBranchData.upstream || "")
                                : ""
                            valueColor: Colors.cyan
                        }

                        FactRow {
                            label: "CHECKOUT"
                            value:
                                root.selectedIsCurrent
                                ? "LIVE"
                                : root.selectedIsOccupied
                                ? "OTHER WORKTREE"
                                : "NOT CHECKED OUT"
                            valueColor:
                                root.selectedIsCurrent
                                ? Colors.yellow
                                : root.selectedIsOccupied
                                ? Colors.magenta
                                : Colors.white
                        }

                        FactRow {
                            label: "WORKSPACE"
                            value:
                                root.selectedWorkspace
                                ? String(root.selectedWorkspace.path || "")
                                : "NONE"
                            valueColor:
                                root.selectedWorkspace
                                ? Colors.magenta
                                : Colors.white
                        }

                        FactRow {
                            label: "CHANGES"
                            value:
                                root.selectedWorkspace
                                ? String(root.selectedWorkspace.dirtyCount || 0)
                                  + " DIRTY"
                                : "—"
                            valueColor:
                                root.selectedWorkspace
                                && Number(root.selectedWorkspace.dirtyCount || 0) > 0
                                ? Colors.orange
                                : Colors.cyan
                        }
                    }

                    Rectangle {
                        width: parent.width
                        height: 1
                        color: Colors.cyan
                        opacity: 0.24
                    }

                    GohuText {
                        text: "BRANCH"
                        font.pixelSize: 8
                        color: Colors.orange
                    }

                    Grid {
                        width: parent.width
                        columns: 2
                        columnSpacing: 6
                        rowSpacing: 6

                        BranchButton {
                            width: (inspector.width - 26) / 2
                            label:
                                root.selectedIsCurrent
                                ? "LIVE"
                                : "SWITCH"
                            selectedAction: root.selectedIsCurrent
                            enabledAction:
                                root.selectedBranch.length > 0
                                && !root.selectedIsCurrent
                                && !root.selectedIsOccupied
                                && branchWorkspaceService
                                && !branchWorkspaceService.actionBusy
                                && !branchWorkspaceService.refreshing

                            onTriggered:
                                branchWorkspaceService.switchBranch(
                                    root.selectedBranch,
                                    "origin",
                                    false
                                )
                        }

                        BranchButton {
                            width: (inspector.width - 26) / 2
                            label: "COMPARE"
                            enabledAction: root.selectedBranch.length > 0
                            onTriggered:
                                root.compareRequested(root.selectedBranch)
                        }

                        BranchButton {
                            width: (inspector.width - 26) / 2
                            label: "RENAME"
                            enabledAction: root.selectedBranch.length > 0
                            onTriggered:
                                root.renameBranchRequested(root.selectedBranch)
                        }

                        BranchButton {
                            width: (inspector.width - 26) / 2
                            label: "UPSTREAM"
                            enabledAction: root.selectedBranch.length > 0
                            onTriggered:
                                root.upstreamRequested(root.selectedBranch)
                        }

                        BranchButton {
                            width: (inspector.width - 26) / 2
                            label: "NEW ABOVE"
                            enabledAction: root.selectedBranch.length > 0
                            onTriggered:
                                root.stackAboveRequested(root.selectedBranch)
                        }

                        BranchButton {
                            width: (inspector.width - 26) / 2
                            label: "NEW BELOW"
                            enabledAction: root.selectedBranch.length > 0
                            onTriggered:
                                root.stackBelowRequested(root.selectedBranch)
                        }

                        BranchButton {
                            width: (inspector.width - 26) / 2
                            label: "WORKSPACE"
                            enabledAction: root.selectedBranch.length > 0
                            onTriggered:
                                root.workspaceRequested(root.selectedBranch)
                        }

                        BranchButton {
                            width: (inspector.width - 26) / 2
                            label: "DELETE"
                            destructive: true
                            enabledAction:
                                root.selectedBranch.length > 0
                                && !root.selectedIsCurrent
                                && !root.selectedIsOccupied
                            onTriggered:
                                root.deleteBranchRequested(root.selectedBranch)
                        }
                    }

                    Rectangle {
                        width: parent.width
                        height: 1
                        color: Colors.cyan
                        opacity: 0.24
                    }

                    GohuText {
                        text: "STACK"
                        font.pixelSize: 8
                        color: Colors.orange
                    }

                    Column {
                        width: parent.width
                        spacing: 2

                        FactRow {
                            label: "ROOT"
                            value:
                                root.selectedBranch
                                ? root.selectedStackRoot
                                : ""
                            valueColor: Colors.orange
                        }

                        FactRow {
                            label: "PARENT"
                            value:
                                root.selectedBranch
                                ? (
                                    root.selectedStackParent
                                    || (
                                        root.selectedBranch
                                        === String(
                                            branchStackStore
                                            ? branchStackStore.trunkBranch
                                            : ""
                                        )
                                        ? "TRUNK"
                                        : "UNSET"
                                    )
                                  )
                                : ""
                            valueColor:
                                root.selectedStackParent
                                ? Colors.cyan
                                : Colors.white
                        }

                        FactRow {
                            label: "CHILDREN"
                            value:
                                root.selectedStackChildren.length > 0
                                ? root.selectedStackChildren.join(" • ")
                                : "NONE"
                            valueColor:
                                root.selectedStackChildren.length > 0
                                ? Colors.magenta
                                : Colors.white
                        }

                        FactRow {
                            label: "BELOW"
                            value:
                                root.selectedStackDescendants.length > 0
                                ? String(root.selectedStackDescendants.length)
                                  + " DESCENDANTS"
                                : "NONE"
                            valueColor:
                                root.selectedStackDescendants.length > 0
                                ? Colors.cyan
                                : Colors.white
                        }
                    }

                    Grid {
                        width: parent.width
                        columns: 2
                        columnSpacing: 6
                        rowSpacing: 6

                        BranchButton {
                            width: (inspector.width - 26) / 2
                            label: "SET PARENT"
                            enabledAction:
                                root.selectedBranch.length > 0
                                && branchStackStore !== null
                            onTriggered:
                                root.stackParentRequested(root.selectedBranch)
                        }

                        BranchButton {
                            width: (inspector.width - 26) / 2
                            label:
                                stackPlanner && stackPlanner.busy
                                ? "READING"
                                : "PREVIEW"
                            enabledAction:
                                root.selectedBranch.length > 0
                                && stackPlanner
                                && !stackPlanner.busy
                                && (
                                    root.selectedStackParent.length > 0
                                    || root.selectedStackDescendants.length > 0
                                )
                            onTriggered:
                                stackPlanner.buildPlan(
                                    root.selectedBranch,
                                    true
                                )
                        }

                        BranchButton {
                            width: (inspector.width - 26) / 2
                            label: "RESTACK"
                            enabledAction:
                                stackPlanner
                                && stackPlanner.startBranch === root.selectedBranch
                                && stackPlanner.executable
                                && stackPlanner.requiredCount > 0
                            onTriggered:
                                root.restackRequested(root.selectedBranch)
                        }

                        BranchButton {
                            width: inspector.width - 20
                            label: "SUBMIT STACK"
                            enabledAction:
                                root.selectedBranch.length > 0
                                && (
                                    root.selectedStackParent.length > 0
                                    || root.selectedStackChildren.length > 0
                                )
                            onTriggered:
                                root.submitStackRequested(root.selectedBranch)
                        }
                    }

                    Rectangle {
                        width: parent.width
                        height:
                            stackPlanner
                            && stackPlanner.plan.length > 0
                            ? Math.min(
                                112,
                                28 + stackPlanColumn.implicitHeight
                              )
                            : 30
                        color: Colors.black
                        border.width: 1
                        border.color:
                            stackPlanner && stackPlanner.invalidCount > 0
                            ? Colors.red
                            : stackPlanner && stackPlanner.requiredCount > 0
                            ? Colors.orange
                            : Colors.cyan
                        clip: true

                        Column {
                            anchors {
                                fill: parent
                                margins: 6
                            }
                            spacing: 3

                            GohuText {
                                width: parent.width
                                text:
                                    stackPlanner
                                    ? stackPlanner.stateText
                                    : "RESTACK PREVIEW // NOT CONNECTED"
                                font.pixelSize: 7
                                color:
                                    stackPlanner && stackPlanner.invalidCount > 0
                                    ? Colors.red
                                    : stackPlanner && stackPlanner.requiredCount > 0
                                    ? Colors.orange
                                    : Colors.cyan
                                elide: Text.ElideRight
                            }

                            Column {
                                id: stackPlanColumn

                                width: parent.width
                                spacing: 1

                                Repeater {
                                    model:
                                        stackPlanner
                                        ? stackPlanner.plan.slice(0, 4)
                                        : []

                                    GohuText {
                                        required property var modelData

                                        width: stackPlanColumn.width
                                        text:
                                            String(modelData.branch || "")
                                            + " → "
                                            + String(modelData.parent || "")
                                            + " // "
                                            + String(modelData.status || "")
                                        font.pixelSize: 7
                                        color:
                                            String(modelData.status || "")
                                            === "RESTACK_REQUIRED"
                                            ? Colors.orange
                                            : String(modelData.status || "")
                                              === "UP_TO_DATE"
                                            ? Colors.cyan
                                            : Colors.red
                                        elide: Text.ElideMiddle
                                    }
                                }
                            }
                        }
                    }

                    Item {
                        width: 1
                        height: Math.max(
                            0,
                            parent.height - y - serviceState.height
                        )
                    }

                    GohuText {
                        id: serviceState

                        width: parent.width
                        text:
                            !branchWorkspaceService
                            ? "BRANCH CORE // NOT CONNECTED"
                            : branchWorkspaceService.lastError
                            ? "ERR // " + branchWorkspaceService.lastError
                            : branchWorkspaceService.actionBusy
                            ? branchWorkspaceService.actionStatus
                            : branchWorkspaceService.refreshing
                            ? "READING BRANCH + WORKTREE STATE"
                            : "BRANCH CORE // READY"
                        font.pixelSize: 7
                        color:
                            branchWorkspaceService
                            && branchWorkspaceService.lastError
                            ? Colors.red
                            : Colors.cyan
                        wrapMode: Text.WrapAnywhere
                    }
                }
            }
        }
    }
}
