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
    required property var stackExecutor

    property string selectedBranch: ""
    property string selectedSha: ""
    property string editMode: "NAME"
    property string newBranchMode: "ABOVE"

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

        if (stackExecutor)
            stackExecutor.disarm("BRANCH SELECTION CHANGED");
    }

    Connections {
        target: root.branchStackStore
        enabled: root.branchStackStore !== null
        ignoreUnknownSignals: true

        function onRelationsChanged() {
            if (root.stackPlanner)
                root.stackPlanner.clear();

            if (root.stackExecutor)
                root.stackExecutor.disarm("STACK RELATIONSHIPS CHANGED");
        }
    }

    Connections {
        target: root.branchWorkspaceService
        enabled: root.branchWorkspaceService !== null
        ignoreUnknownSignals: true

        function onRefreshed() {
            if (root.stackPlanner)
                root.stackPlanner.clear();

            if (root.stackExecutor)
                root.stackExecutor.disarm("BRANCH STATE CHANGED");
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

    function cycleEditMode() {
        if (editMode === "NAME")
            editMode = "UP";
        else if (editMode === "UP")
            editMode = "PARENT";
        else
            editMode = "NAME";
    }

    function cycleNewBranchMode() {
        newBranchMode =
            newBranchMode === "ABOVE"
            ? "BELOW"
            : "ABOVE";
    }

    function triggerEditMode() {
        if (!selectedBranch)
            return;

        if (editMode === "NAME")
            renameBranchRequested(selectedBranch);
        else if (editMode === "UP")
            upstreamRequested(selectedBranch);
        else
            stackParentRequested(selectedBranch);
    }

    function triggerNewBranchMode() {
        if (!selectedBranch)
            return;

        if (newBranchMode === "ABOVE")
            stackAboveRequested(selectedBranch);
        else
            stackBelowRequested(selectedBranch);
    }

    function triggerRestackActuator() {
        if (!selectedBranch || !stackPlanner || !stackExecutor)
            return;

        if (stackExecutor.running)
            return;

        if (stackExecutor.armed) {
            stackExecutor.executeArmed();
            return;
        }

        if (stackPlanner.startBranch === selectedBranch
                && stackPlanner.executable
                && stackPlanner.requiredCount > 0) {
            stackExecutor.armFromPlanner();
            return;
        }

        stackExecutor.disarm("NEW PREVIEW");
        stackPlanner.buildPlan(selectedBranch, true);
    }

    function restackActuatorLabel() {
        if (!stackPlanner || !stackExecutor)
            return "RESTACK";

        if (stackExecutor.running)
            return "RESTACKING";

        if (stackPlanner.busy)
            return "READING";

        if (stackExecutor.armed)
            return "RESTACK";

        if (stackPlanner.startBranch === selectedBranch
                && stackPlanner.executable
                && stackPlanner.requiredCount > 0)
            return "ARM";

        return "PREVIEW";
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

    component CompoundButton: Rectangle {
        id: compoundButton

        property string actionLabel: ""
        property string modeLabel: ""
        property bool enabledAction: true
        property bool modeEnabled: true
        property bool destructive: false

        signal triggered()
        signal modeTriggered()

        height: 30
        color:
            actionMouse.pressed
            ? destructive ? Colors.red : Colors.orange
            : Colors.black

        border.width:
            actionMouse.containsMouse || modeMouse.containsMouse
            ? 2
            : 1

        border.color:
            destructive
            ? Colors.red
            : actionMouse.containsMouse || modeMouse.containsMouse
            ? Colors.orange
            : Colors.cyan

        GohuText {
            anchors {
                left: parent.left
                leftMargin: 8
                verticalCenter: parent.verticalCenter
            }
            text: compoundButton.actionLabel
            font.pixelSize: 8
            color:
                compoundButton.destructive
                ? Colors.red
                : Colors.cyan
            opacity: compoundButton.enabledAction ? 1.0 : 0.38
        }

        Rectangle {
            id: modeTag

            anchors {
                right: parent.right
                rightMargin: 5
                verticalCenter: parent.verticalCenter
            }

            width: Math.max(52, modeText.implicitWidth + 16)
            height: 22
            color:
                modeMouse.pressed
                ? Colors.magenta
                : modeMouse.containsMouse
                ? Colors.dark
                : Colors.black
            border.width: 1
            border.color:
                modeMouse.containsMouse
                ? Colors.orange
                : Colors.magenta
            opacity: compoundButton.modeEnabled ? 1.0 : 0.34

            GohuText {
                id: modeText
                anchors.centerIn: parent
                text: compoundButton.modeLabel
                font.pixelSize: 9
                color: Colors.magenta
            }

            MouseArea {
                id: modeMouse
                anchors.fill: parent
                enabled: compoundButton.modeEnabled
                hoverEnabled: true
                cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                onClicked: compoundButton.modeTriggered()
                onWheel: function(wheel) {
                    compoundButton.modeTriggered();
                    wheel.accepted = true;
                }
            }
        }

        MouseArea {
            id: actionMouse

            anchors {
                left: parent.left
                top: parent.top
                bottom: parent.bottom
                right: modeTag.left
            }

            enabled: compoundButton.enabledAction
            acceptedButtons: Qt.LeftButton | Qt.RightButton
            hoverEnabled: true
            cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor

            onClicked: function(mouse) {
                if (mouse.button === Qt.RightButton)
                    compoundButton.modeTriggered();
                else
                    compoundButton.triggered();
            }

            onWheel: function(wheel) {
                if (compoundButton.modeEnabled) {
                    compoundButton.modeTriggered();
                    wheel.accepted = true;
                }
            }
        }
    }

    component FactRow: Row {
        property string label: ""
        property string value: ""
        property color valueColor: Colors.white

        width: parent ? parent.width : 0
        height: 17
        spacing: 6

        GohuText {
            width: 54
            anchors.verticalCenter: parent.verticalCenter
            text: parent.label
            font.pixelSize: 7
            color: Colors.magenta
        }

        GohuText {
            width: parent.width - 60
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
                    id: branchSelectorStrip

                    anchors {
                        left: parent.left
                        right: parent.right
                        bottom: parent.bottom
                        leftMargin: 12
                        rightMargin: 12
                        bottomMargin: 10
                    }

                    height: 52
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.blue
                    z: 80
                    clip: true

                    Flickable {
                        id: branchStripFlick

                        anchors {
                            left: parent.left
                            right: parent.right
                            top: parent.top
                            bottom: branchStripRail.top
                            margins: 5
                            bottomMargin: 3
                        }

                        contentWidth: Math.max(width, branchStripRow.implicitWidth)
                        contentHeight: height
                        flickableDirection: Flickable.HorizontalFlick
                        boundsBehavior: Flickable.StopAtBounds
                        clip: true

                        MouseArea {
                            anchors.fill: parent
                            acceptedButtons: Qt.NoButton
                            propagateComposedEvents: true

                            onWheel: function(wheel) {
                                const step =
                                    wheel.angleDelta.y > 0
                                    ? -72
                                    : 72;

                                branchStripFlick.contentX =
                                    Math.max(
                                        0,
                                        Math.min(
                                            branchStripRail.maxContentX,
                                            branchStripFlick.contentX + step
                                        )
                                    );
                                wheel.accepted = true;
                            }
                        }

                        Row {
                            id: branchStripRow

                            height: parent.height
                            spacing: 5

                            Repeater {
                                model:
                                    branchWorkspaceService
                                    ? branchWorkspaceService.branches
                                    : []

                                Rectangle {
                                    required property var modelData

                                    height: 32
                                    anchors.verticalCenter: parent.verticalCenter
                                    width: Math.max(
                                        112,
                                        Math.min(
                                            260,
                                            branchName.implicitWidth + 24
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

                                        anchors {
                                            left: parent.left
                                            right: parent.right
                                            verticalCenter: parent.verticalCenter
                                            leftMargin: 8
                                            rightMargin: 8
                                        }

                                        text:
                                            (parent.isCurrent ? "★ " : "")
                                            + String(parent.modelData.name || "")
                                        font.pixelSize: 11
                                        color:
                                            parent.isCurrent
                                            ? Colors.yellow
                                            : parent.workspace
                                            ? Colors.magenta
                                            : parent.isSelected
                                            ? Colors.orange
                                            : Colors.cyan
                                        elide: Text.ElideMiddle
                                        horizontalAlignment: Text.AlignHCenter
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked:
                                            root.selectBranch(
                                                String(parent.modelData.name || "")
                                            )

                                        onWheel: function(wheel) {
                                            const step =
                                                wheel.angleDelta.y > 0
                                                ? -72
                                                : 72;

                                            branchStripFlick.contentX =
                                                Math.max(
                                                    0,
                                                    Math.min(
                                                        branchStripRail.maxContentX,
                                                        branchStripFlick.contentX + step
                                                    )
                                                );
                                            wheel.accepted = true;
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Rectangle {
                        id: branchStripRail

                        anchors {
                            left: parent.left
                            right: parent.right
                            bottom: parent.bottom
                            leftMargin: 5
                            rightMargin: 5
                            bottomMargin: 4
                        }

                        height: 6
                        color: Colors.cyan
                        opacity: 1.0
                        border.width: 1
                        border.color: Colors.cyan

                        Rectangle {
                            anchors.fill: parent
                            color: Colors.black
                            opacity:
                                branchStripFlick.contentWidth
                                > branchStripFlick.width + 1
                                ? 0.18
                                : 0.62
                        }

                        readonly property real maxContentX:
                            Math.max(
                                0,
                                branchStripFlick.contentWidth
                                - branchStripFlick.width
                            )

                        Rectangle {
                            id: branchStripHandle

                            height: parent.height
                            width:
                                Math.max(
                                    34,
                                    parent.width
                                    * Math.min(
                                        1,
                                        branchStripFlick.width
                                        / Math.max(
                                            branchStripFlick.contentWidth,
                                            1
                                        )
                                    )
                                )
                            x:
                                branchStripRail.maxContentX > 0
                                ? (
                                    branchStripFlick.contentX
                                    / branchStripRail.maxContentX
                                  )
                                  * Math.max(0, parent.width - width)
                                : 0
                            color: Colors.magenta
                            opacity: 1.0
                            border.width: 1
                            border.color: Colors.magenta

                            RectangularShadow {
                                anchors.fill: parent
                                spread: 1
                                z: -1
                                opacity: 0.50
                                color: Colors.magenta
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            enabled:
                                branchStripRail.maxContentX > 0
                            hoverEnabled: true
                            cursorShape:
                                enabled
                                ? Qt.PointingHandCursor
                                : Qt.ArrowCursor

                            function scrollTo(mouseX) {
                                const travel =
                                    branchStripRail.width
                                    - branchStripHandle.width;
                                const target =
                                    mouseX
                                    - branchStripHandle.width / 2;
                                const ratio =
                                    travel > 0
                                    ? Math.max(
                                        0,
                                        Math.min(
                                            1,
                                            target / travel
                                        )
                                      )
                                    : 0;

                                branchStripFlick.contentX =
                                    ratio
                                    * branchStripRail.maxContentX;
                            }

                            onPressed: function(mouse) {
                                scrollTo(mouse.x);
                            }

                            onPositionChanged: function(mouse) {
                                if (pressed)
                                    scrollTo(mouse.x);
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
                    spacing: 6

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
                        spacing: 1

                        FactRow {
                            label: "STATE"
                            value:
                                (
                                    root.selectedBranchData
                                    ? root.shortSha(root.selectedBranchData.head)
                                    : "—"
                                )
                                + " // "
                                + (
                                    root.selectedIsCurrent
                                    ? "LIVE"
                                    : root.selectedIsOccupied
                                    ? "WORKTREE"
                                    : "IDLE"
                                  )
                                + (
                                    root.selectedWorkspace
                                    ? " // "
                                      + String(
                                          root.selectedWorkspace.dirtyCount || 0
                                        )
                                      + " DIRTY"
                                    : ""
                                  )
                            valueColor:
                                root.selectedIsCurrent
                                ? Colors.yellow
                                : root.selectedIsOccupied
                                ? Colors.magenta
                                : Colors.orange
                        }

                        FactRow {
                            label: "UP"
                            value:
                                root.selectedBranchData
                                ? String(
                                    root.selectedBranchData.upstream
                                    || "NONE"
                                  )
                                : ""
                            valueColor: Colors.cyan
                        }

                        FactRow {
                            label: "WORK"
                            value:
                                root.selectedWorkspace
                                ? String(root.selectedWorkspace.path || "")
                                : "NONE"
                            valueColor:
                                root.selectedWorkspace
                                ? Colors.magenta
                                : Colors.white
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
                        rowSpacing: 5

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
                            enabledAction: false
                            onTriggered:
                                root.compareRequested(root.selectedBranch)
                        }

                        CompoundButton {
                            width: (inspector.width - 26) / 2
                            actionLabel: "EDIT"
                            modeLabel: root.editMode
                            enabledAction: false
                            modeEnabled: root.selectedBranch.length > 0
                            onTriggered: root.triggerEditMode()
                            onModeTriggered: root.cycleEditMode()
                        }

                        CompoundButton {
                            width: (inspector.width - 26) / 2
                            actionLabel: "NEW"
                            modeLabel: root.newBranchMode
                            enabledAction: false
                            modeEnabled: root.selectedBranch.length > 0
                            onTriggered: root.triggerNewBranchMode()
                            onModeTriggered: root.cycleNewBranchMode()
                        }

                        BranchButton {
                            width: (inspector.width - 26) / 2
                            label: "WORKSPACE"
                            enabledAction: false
                            onTriggered:
                                root.workspaceRequested(root.selectedBranch)
                        }

                        BranchButton {
                            width: (inspector.width - 26) / 2
                            label: "DELETE"
                            destructive: true
                            enabledAction: false
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
                        spacing: 1

                        FactRow {
                            label: "CHAIN"
                            value:
                                root.selectedBranch
                                ? (
                                    (
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
                                    + " → "
                                    + root.selectedBranch
                                    + (
                                        root.selectedStackChildren.length > 0
                                        ? " → "
                                          + root.selectedStackChildren.join(" • ")
                                        : ""
                                      )
                                  )
                                : ""
                            valueColor: Colors.cyan
                        }

                        FactRow {
                            label: "TREE"
                            value:
                                root.selectedBranch
                                ? (
                                    "ROOT "
                                    + (root.selectedStackRoot || "—")
                                    + " // "
                                    + String(
                                        root.selectedStackDescendants.length
                                      )
                                    + " BELOW"
                                  )
                                : ""
                            valueColor:
                                root.selectedStackDescendants.length > 0
                                ? Colors.magenta
                                : Colors.white
                        }
                    }

                    Grid {
                        width: parent.width
                        columns: 2
                        columnSpacing: 6
                        rowSpacing: 5

                        BranchButton {
                            width: (inspector.width - 26) / 2
                            label: root.restackActuatorLabel()
                            selectedAction:
                                stackExecutor && stackExecutor.armed
                            enabledAction:
                                root.selectedBranch.length > 0
                                && stackPlanner
                                && stackExecutor
                                && !stackExecutor.running
                                && !stackPlanner.busy
                                && (
                                    stackExecutor.armed
                                    || (
                                        stackPlanner.startBranch
                                        === root.selectedBranch
                                        && stackPlanner.executable
                                        && stackPlanner.requiredCount > 0
                                       )
                                    || root.selectedStackParent.length > 0
                                    || root.selectedStackDescendants.length > 0
                                )
                            onTriggered:
                                root.triggerRestackActuator()
                        }

                        BranchButton {
                            width: (inspector.width - 26) / 2
                            label: "SUBMIT STACK"
                            enabledAction: false
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
                                78,
                                26 + stackPlanColumn.implicitHeight
                              )
                            : 26
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
                                    stackExecutor && stackExecutor.running
                                    ? stackExecutor.stateText
                                    : stackExecutor && stackExecutor.armed
                                    ? stackExecutor.armStatus
                                    : stackExecutor && stackExecutor.lastError
                                    ? stackExecutor.lastError
                                    : stackPlanner
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
                                        ? stackPlanner.plan.slice(0, 3)
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
