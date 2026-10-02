import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.components
import "../services/git"
import "../services/github"
import QtQuick.Effects
import Qt5Compat.GraphicalEffects

PanelWindow {
    id: root

    property bool menuOpen: false
    property string activePage: "git"
    property string githubView: "control"
    property string factoryTemplate: "smoke"
    property string factoryTrigger: "manual"
    property int selectedWorkflowIndex: 0
    property bool workflowMenuOpen: false
    property int selectedRunIndex: 0
    property string selectedGitCommitSha: ""
    property var activeTextEditor: null

    readonly property var selectedWorkflow:
        githubService.workflows.length > 0
        ? githubService.workflows[Math.min(selectedWorkflowIndex, githubService.workflows.length - 1)]
        : null

    readonly property var selectedRun:
        githubService.runs.length > 0
        ? githubService.runs[Math.min(selectedRunIndex, githubService.runs.length - 1)]
        : null

    readonly property string selectedRunStatus:
        selectedRun ? String(selectedRun.status || "").toLowerCase() : ""

    // One physical machine, two cameras. Page changes never resize the chassis.
    property int panelWidth: 920
    property int panelHeight: 790
    property int panelTopMargin: 0
    property int panelLeftMargin: 600
    property int frameInset: 8
    property int glowGutter: 14
    property int topGlowGutter: 12

    implicitWidth: panelWidth + glowGutter * 2
    implicitHeight: panelHeight + topGlowGutter + glowGutter

    anchors {
        top: true
        bottom: false
        left: true
        right: false
    }

    margins {
        top: panelTopMargin
        left: panelLeftMargin - glowGutter
        right: 0
        bottom: 0
    }

    exclusiveZone: 0
    WlrLayershell.layer: WlrLayer.Overlay

    color: "transparent"
    surfaceFormat.opaque: false
    visible: true

    // Both cameras contain typeable controls, so let Wayland grant focus
    // while the Git machine is open.
    focusable: root.menuOpen

    mask: Region {
        x: 0
        y: 0
        width: root.menuOpen ? root.width : 0
        height: root.menuOpen ? root.height : 0
    }

    function releaseTextFocusAt(item, x, y) {
        const focused = root.activeTextEditor;

        if (!focused || typeof focused.mapFromItem !== "function")
            return;

        const local = focused.mapFromItem(item, x, y);
        const inside =
            local.x >= 0
            && local.y >= 0
            && local.x <= focused.width
            && local.y <= focused.height;

        if (!inside) {
            focused.deselect();
            focused.focus = false;
            root.activeTextEditor = null;
        }
    }

    function open() {
        root.menuOpen = true;
    }

    function close() {
        root.menuOpen = false;
    }

    function toggle() {
        root.menuOpen = !root.menuOpen;
    }

    function showGitPage() {
        root.workflowMenuOpen = false;
        root.activePage = "git";
        gitService.refresh();
    }

    function showGithubPage() {
        root.activePage = "github";
        gitService.refresh();
        githubService.refresh();
    }

    function showGithubControl() {
        root.workflowMenuOpen = false;
        root.githubView = "control";
    }

    function showGithubLibrary() {
        root.workflowMenuOpen = false;
        root.githubView = "library";
    }

    function githubStateText() {
        if (githubService.factoryBusy)
            return githubService.factoryMode === "install"
                   ? "SAVING // VALIDATING + INSTALLING"
                   : "PREVIEWING // VALIDATING";

        if (githubService.factoryInstallCommit)
            return "WORKFLOW INSTALLED // "
                   + githubService.factoryInstallCommit.slice(0, 10);

        if (githubService.factoryPullRequest)
            return "WORKFLOW PR READY // " + githubService.factoryPullRequest;

        if (githubService.factoryValidationStatus === "PASS")
            return "FACTORY PASS // " + githubService.factoryPath;

        if (githubService.factoryValidationStatus === "FAIL"
                || githubService.factoryValidationStatus === "ERROR")
            return githubService.factoryValidationStatus
                   + " // "
                   + (githubService.factoryValidationMessage || "PX FACTORY ERROR");

        if (githubService.actionBusy)
            return githubService.actionResult;

        if (githubService.actionResult !== "READY")
            return githubService.actionResult;

        return githubService.available
               ? "ACTIVE // PX CONTROL READY"
               : "WAITING";
    }

    function githubStateColor() {
        if (githubService.factoryValidationStatus === "FAIL"
                || githubService.factoryValidationStatus === "ERROR"
                || githubService.lastError
                || String(githubService.actionResult || "").indexOf("ERROR") === 0)
            return Colors.red;

        if (githubService.factoryValidationStatus === "PASS"
                || githubService.factoryInstallCommit)
            return Colors.orange;

        return Colors.white;
    }

    function cycleFactoryTemplate() {
        root.factoryTemplate = root.factoryTemplate === "smoke"
                               ? "shell-check"
                               : "smoke";
        githubService.clearFactoryResult();
    }

    function cycleFactoryTrigger() {
        if (root.factoryTrigger === "manual")
            root.factoryTrigger = "push";
        else if (root.factoryTrigger === "push")
            root.factoryTrigger = "manual+push";
        else
            root.factoryTrigger = "manual";

        githubService.clearFactoryResult();
    }

    function cycleWorkflow() {
        const count = githubService.workflows.length;

        if (count <= 0)
            return;

        root.selectedWorkflowIndex = (root.selectedWorkflowIndex + 1) % count;
    }

    function selectWorkflow(index) {
        const count = githubService.workflows.length;

        if (count <= 0)
            return;

        root.selectedWorkflowIndex = Math.max(0, Math.min(count - 1, index));
        root.workflowMenuOpen = false;
    }

    function cycleRun() {
        const count = githubService.runs.length;

        if (count <= 0)
            return;

        root.selectedRunIndex = (root.selectedRunIndex + 1) % count;
    }

    onMenuOpenChanged: {
        if (!root.menuOpen)
            return;

        gitService.refresh();

        if (root.activePage === "github")
            githubService.refresh();
    }

    GitService {
        id: gitService
    }

    GitHubService {
        id: githubService
        originUrl: gitService.origin
    }

    WorkflowLibraryStore {
        id: workflowLibraryStore
        githubService: githubService
    }

    Connections {
        target: githubService

        function onWorkflowsChanged() {
            if (githubService.workflows.length === 0)
                root.selectedWorkflowIndex = 0;
            else if (root.selectedWorkflowIndex >= githubService.workflows.length)
                root.selectedWorkflowIndex = 0;
        }

        function onRunsChanged() {
            if (githubService.runs.length === 0)
                root.selectedRunIndex = 0;
            else if (root.selectedRunIndex >= githubService.runs.length)
                root.selectedRunIndex = 0;
        }
    }

    Timer {
        interval: 15000
        repeat: true
        running: root.menuOpen && root.activePage === "github"

        onTriggered: githubService.refresh()
    }

    component SectionLabel: GohuText {
        font.pixelSize: 12
        color: Colors.magenta

        layer.enabled: true
        layer.effect: DropShadow {
            radius: 6
            samples: 7
            opacity: 0.46
            color: Colors.magenta
            transparentBorder: true
        }
    }

    component MetaLabel: GohuText {
        font.pixelSize: 10
        color: Colors.cyan

        layer.enabled: true
        layer.effect: DropShadow {
            radius: 4
            samples: 5
            opacity: 0.28
            color: Colors.cyan
            transparentBorder: true
        }
    }

    component MetaValue: GohuText {
        font.pixelSize: 11
        color: Colors.white
        elide: Text.ElideRight

        layer.enabled: true
        layer.effect: DropShadow {
            radius: 5
            samples: 7
            opacity: 0.10
            color: Colors.cyan
            transparentBorder: true
        }
    }

    component OrangeValue: GohuText {
        font.pixelSize: 11
        color: Colors.orange
        elide: Text.ElideRight

        layer.enabled: true
        layer.effect: DropShadow {
            radius: 6
            samples: 9
            opacity: 0.46
            color: Colors.orange
            transparentBorder: true
        }
    }

    component BlueValue: GohuText {
        font.pixelSize: 11
        color: Colors.blue
        elide: Text.ElideRight

        layer.enabled: true
        layer.effect: DropShadow {
            radius: 7
            samples: 9
            opacity: 0.48
            color: Colors.cyan
            transparentBorder: true
        }
    }

    component DimValue: GohuText {
        font.pixelSize: 11
        color: Colors.white
        opacity: 0.68
        elide: Text.ElideRight

        layer.enabled: true
        layer.effect: DropShadow {
            radius: 3
            samples: 5
            opacity: 0.12
            color: Colors.white
            transparentBorder: true
        }
    }

    component OrangeLabel: GohuText {
        font.pixelSize: 10
        color: Colors.orange

        layer.enabled: true
        layer.effect: DropShadow {
            radius: 5
            samples: 7
            opacity: 0.38
            color: Colors.orange
            transparentBorder: true
        }
    }

    component BlueLabel: GohuText {
        font.pixelSize: 10
        color: Colors.blue

        layer.enabled: true
        layer.effect: DropShadow {
            radius: 6
            samples: 7
            opacity: 0.48
            color: Colors.cyan
            transparentBorder: true
        }
    }

    component CyanValue: GohuText {
        font.pixelSize: 11
        color: Colors.cyan
        elide: Text.ElideRight

        layer.enabled: true
        layer.effect: DropShadow {
            radius: 5
            samples: 7
            opacity: 0.30
            color: Colors.cyan
            transparentBorder: true
        }
    }

    component SelectorInput: Rectangle {
        id: selectorInput

        property string valueText: ""
        property string placeholderText: ""
        property color accentColor: Colors.cyan
        property bool editable: true

        signal submitted(string value)

        height: 28
        color: Colors.black
        border.width: 1
        border.color: input.activeFocus ? Colors.yellow : selectorInput.accentColor

        onValueTextChanged: {
            if (!input.activeFocus)
                input.text = valueText;
        }

        TextInput {
            id: input

            anchors {
                fill: parent
                leftMargin: 7
                rightMargin: 7
            }

            readOnly: !selectorInput.editable
            selectByMouse: true
            clip: true

            font.family: GohuFont.family
            font.pixelSize: 10
            color: selectorInput.accentColor
            selectionColor: Colors.orange
            selectedTextColor: Colors.black
            verticalAlignment: TextInput.AlignVCenter

            layer.enabled: true
            layer.effect: DropShadow {
                radius: 7
                samples: 9
                opacity: input.activeFocus ? 0.64 : 0.52
                color: selectorInput.accentColor
                transparentBorder: true
            }

            Component.onCompleted: text = selectorInput.valueText

            onAccepted: {
                const candidate = String(text || "").trim();

                if (candidate)
                    selectorInput.submitted(candidate);

                focus = false;
            }

            Keys.onEscapePressed: function(event) {
                text = selectorInput.valueText;
                focus = false;
                event.accepted = true;
            }

            onActiveFocusChanged: {
                if (activeFocus) {
                    root.activeTextEditor = input;
                    text = selectorInput.valueText;
                    selectAll();
                } else {
                    text = selectorInput.valueText;

                    if (root.activeTextEditor === input)
                        root.activeTextEditor = null;
                }
            }
        }

        GohuText {
            anchors {
                left: parent.left
                leftMargin: 7
                verticalCenter: parent.verticalCenter
            }

            visible: !input.activeFocus && !selectorInput.valueText
            text: selectorInput.placeholderText
            font.pixelSize: 9
            color: Colors.white
            opacity: 0.48
        }

        layer.enabled: input.activeFocus
        layer.effect: DropShadow {
            radius: 7
            samples: 9
            opacity: input.activeFocus ? 0.62 : 0.0
            color: Colors.yellow
            transparentBorder: true
        }
    }

    component ActionButton: Rectangle {
        id: actionButton

        property string label: ""
        property bool enabledAction: false
        property bool selectedAction: false
        property bool primaryBlue: false
        property string leftIcon: ""
        property string rightIcon: ""
        property int iconPixelSize: 24
        property int iconVerticalOffset: 0

        signal triggered()

        readonly property bool hovered:
            enabledAction && actionMouse.containsMouse
        readonly property bool pressed:
            enabledAction && actionMouse.pressed

        readonly property color contentColor:
            pressed
            ? Colors.black
            : primaryBlue
            ? Colors.white
            : selectedAction
            ? Colors.magenta
            : hovered
            ? Colors.orange
            : Colors.cyan

        readonly property real contentOpacity:
            pressed || hovered || selectedAction || enabledAction
            ? 1.0
            : 0.34

        width: 112
        height: 36

        scale:
            pressed
            ? 0.99
            : hovered
            ? 1.025
            : selectedAction
            ? 1.01
            : 1.0

        color:
            pressed
            ? Colors.magenta
            : primaryBlue
            ? (enabledAction ? Colors.blue : Colors.dark)
            : hovered || selectedAction
            ? Colors.yellow
            : Colors.black

        border.width: 1
        border.color:
            pressed
            ? Colors.magenta
            : primaryBlue
            ? (hovered ? Colors.cyan : Colors.blue)
            : hovered
            ? Colors.orange
            : selectedAction
            ? Colors.orange
            : Colors.cyan

        opacity: 1.0

        Behavior on scale {
            NumberAnimation {
                duration: 90
                easing.type: Easing.OutQuad
            }
        }

        GohuText {
            id: actionText
            anchors.centerIn: parent
            visible:
                actionButton.leftIcon.length === 0
                && actionButton.rightIcon.length === 0
            text: actionButton.label
            font.pixelSize: 11
            color: actionButton.contentColor
            opacity: actionButton.contentOpacity

            layer.enabled: !actionButton.pressed
            layer.effect: DropShadow {
                radius: 10
                samples: 11
                opacity:
                    actionButton.hovered
                    ? 0.64
                    : actionButton.selectedAction
                    ? 0.60
                    : actionButton.enabledAction
                    ? 0.68
                    : 0.10
                color:
                    actionButton.hovered || actionButton.selectedAction
                    ? Colors.orange
                    : Colors.cyan
                transparentBorder: true
            }
        }

        Row {
            anchors.centerIn: parent
            spacing: 6
            visible:
                actionButton.leftIcon.length > 0
                || actionButton.rightIcon.length > 0

            layer.enabled: !actionButton.pressed
            layer.effect: DropShadow {
                radius: 10
                samples: 11
                opacity:
                    actionButton.hovered
                    ? 0.64
                    : actionButton.selectedAction
                    ? 0.60
                    : actionButton.enabledAction
                    ? 0.68
                    : 0.10
                color:
                    actionButton.hovered || actionButton.selectedAction
                    ? Colors.orange
                    : Colors.cyan
                transparentBorder: true
            }

            NotoText {
                visible: actionButton.leftIcon.length > 0
                anchors.verticalCenter: parent.verticalCenter
                anchors.verticalCenterOffset: actionButton.iconVerticalOffset
                text: actionButton.leftIcon
                font.pixelSize: actionButton.iconPixelSize
                color: actionButton.contentColor
                opacity: actionButton.contentOpacity
            }

            GohuText {
                anchors.verticalCenter: parent.verticalCenter
                text: actionButton.label
                font.pixelSize: 11
                color: actionButton.contentColor
                opacity: actionButton.contentOpacity
            }

            NotoText {
                visible: actionButton.rightIcon.length > 0
                anchors.verticalCenter: parent.verticalCenter
                anchors.verticalCenterOffset: actionButton.iconVerticalOffset
                text: actionButton.rightIcon
                font.pixelSize: actionButton.iconPixelSize
                color: actionButton.contentColor
                opacity: actionButton.contentOpacity
            }
        }

        MouseArea {
            id: actionMouse
            anchors.fill: parent
            hoverEnabled: true
            enabled: actionButton.enabledAction

            onClicked: actionButton.triggered()
        }

        RectangularShadow {
            anchors.fill: parent
            spread: 3
            z: -1
            opacity:
                actionButton.pressed
                ? 0.42
                : actionButton.hovered
                ? 0.34
                : actionButton.selectedAction
                ? 0.30
                : actionButton.enabledAction
                ? 0.30
                : 0.06
            color:
                actionButton.pressed
                ? Colors.magenta
                : actionButton.primaryBlue
                ? Colors.blue
                : actionButton.hovered || actionButton.selectedAction
                ? Colors.orange
                : Colors.cyan
        }

        RectangularShadow {
            anchors.fill: parent
            spread: 10
            z: -2
            opacity:
                actionButton.pressed
                ? 0.10
                : actionButton.hovered
                ? 0.08
                : actionButton.selectedAction
                ? 0.07
                : actionButton.enabledAction
                ? 0.045
                : 0.015
            color:
                actionButton.pressed
                ? Colors.magenta
                : actionButton.primaryBlue
                ? Colors.blue
                : actionButton.hovered || actionButton.selectedAction
                ? Colors.orange
                : Colors.cyan
        }
    }

    component PageTab: Rectangle {
        id: pageTab

        property string label: ""
        property bool selected: false

        signal triggered()

        readonly property bool hovered: tabMouse.containsMouse
        readonly property bool pressed: tabMouse.pressed

        height: 36

        scale: 1.0

        color:
            pressed
            ? Colors.magenta
            : hovered || selected
            ? Colors.yellow
            : Colors.black

        border.width: 1
        border.color:
            pressed
            ? Colors.magenta
            : hovered
            ? Colors.orange
            : selected
            ? Colors.orange
            : Colors.cyan

        GohuText {
            anchors.centerIn: parent
            text: pageTab.label
            font.pixelSize: 11
            color:
                pageTab.pressed
                ? Colors.black
                : pageTab.selected
                ? Colors.magenta
                : pageTab.hovered
                ? Colors.orange
                : Colors.cyan
            opacity: 1.0

            layer.enabled: !pageTab.pressed
            layer.effect: DropShadow {
                radius: 10
                samples: 11
                opacity:
                    pageTab.hovered
                    ? 0.64
                    : pageTab.selected
                    ? 0.60
                    : 0.62
                color:
                    pageTab.hovered || pageTab.selected
                    ? Colors.orange
                    : Colors.cyan
                transparentBorder: true
            }
        }

        MouseArea {
            id: tabMouse
            anchors.fill: parent
            hoverEnabled: true
            onClicked: pageTab.triggered()
        }

        RectangularShadow {
            anchors.fill: parent
            spread: 3
            z: -1
            opacity:
                pageTab.pressed
                ? 0.42
                : pageTab.hovered
                ? 0.34
                : pageTab.selected
                ? 0.30
                : 0.26
            color:
                pageTab.pressed
                ? Colors.magenta
                : pageTab.hovered || pageTab.selected
                ? Colors.orange
                : Colors.cyan
        }

        RectangularShadow {
            anchors.fill: parent
            spread: 10
            z: -2
            opacity:
                pageTab.pressed
                ? 0.10
                : pageTab.hovered
                ? 0.08
                : pageTab.selected
                ? 0.07
                : 0.045
            color:
                pageTab.pressed
                ? Colors.magenta
                : pageTab.hovered || pageTab.selected
                ? Colors.orange
                : Colors.cyan
        }
    }

    Rectangle {
        id: chassisGeometry

        width: root.panelWidth
        height: root.panelHeight
        anchors.top: parent.top
        anchors.topMargin: root.topGlowGutter
        anchors.horizontalCenter: parent.horizontalCenter

        color: "transparent"
        opacity: root.menuOpen ? 1.0 : 0.0
    }

    RectangularShadow {
        anchors.fill: chassisGeometry
        spread: 6
        z: -20
        opacity: root.menuOpen ? 0.21 : 0.0
        color: Colors.orange
    }

    RectangularShadow {
        anchors.fill: chassisGeometry
        spread: 12
        z: -21
        opacity: root.menuOpen ? 0.05 : 0.0
        color: Colors.orange
    }

    Rectangle {
        id: frame

        width: root.panelWidth
        height: root.panelHeight
        anchors.top: parent.top
        anchors.topMargin: root.topGlowGutter
        anchors.horizontalCenter: parent.horizontalCenter

        color: Colors.black
        opacity: root.menuOpen ? 0.97 : 0.0

        border.width: 1
        border.color: Colors.orange

        TapHandler {
            acceptedButtons: Qt.LeftButton

            onTapped: function(eventPoint, button) {
                root.releaseTextFocusAt(
                    frame,
                    eventPoint.position.x,
                    eventPoint.position.y
                );
            }
        }

        Rectangle {
            anchors.fill: parent
            anchors.margins: root.frameInset

            color: "transparent"
            border.width: 1
            border.color: Colors.cyan
            opacity: 0.70
        }

        SelectorSlider {
            id: repoSlider

            visible: root.activePage === "git"
            z: 100
            anchors {
                left: parent.left
                leftMargin: 18
                top: parent.top
                topMargin: 148
                bottom: parent.bottom
                bottomMargin: 26
            }

            count: gitService.repoCount
            currentIndex: gitService.repoIndexOfPath(gitService.repoPath)
            accentColor: Colors.magenta
            handleGlowColor: Colors.orange
            sideLabel: "REPO"

            onIndexRequested: function(index) {
                gitService.selectRepo(index);
            }
        }

        SelectorSlider {
            id: remoteSlider

            visible: root.activePage === "git"
            z: 100
            anchors {
                right: parent.right
                rightMargin: 18
                top: parent.top
                topMargin: 148
                bottom: parent.bottom
                bottomMargin: 26
            }

            count: gitService.remoteBranchCount
            currentIndex: gitService.selectedRemoteIndex
            accentColor: Colors.orange
            handleGlowColor: Colors.cyan
            sideLabel: "REMOTE"

            onIndexRequested: function(index) {
                gitService.selectRemote(index);
            }
        }

        Column {
            anchors {
                fill: parent
                topMargin: 18
                bottomMargin: 18
                leftMargin: 18
                rightMargin: 18
            }

            spacing: 12

            Item {
                width: parent.width
                height: 56

                GohuText {
                    anchors {
                        left: parent.left
                        top: parent.top
                    }

                    text: root.activePage === "git"
                          ? "GIT // LOCAL REPOSITORY"
                          : "GITHUB // REMOTE AUTOMATION"
                    font.pixelSize: 20
                    color: Colors.magenta

                    layer.enabled: true
                    layer.effect: DropShadow {
                        radius: 8
                        samples: 9
                        opacity: 0.52
                        color: Colors.magenta
                        transparentBorder: true
                    }
                }

                GohuText {
                    anchors {
                        left: parent.left
                        bottom: parent.bottom
                    }

                    text: root.activePage === "git"
                          ? "CONTROL SURFACE // LOCAL GIT"
                          : "PX CONTROL SURFACE // GITHUB ACTIONS"
                    font.pixelSize: 10
                    color: Colors.cyan
                }

                Rectangle {
                    anchors {
                        right: parent.right
                        verticalCenter: parent.verticalCenter
                    }

                    width: 94
                    height: 26

                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.orange

                    RectangularShadow {
                        anchors.fill: parent
                        spread: 3
                        z: -1
                        opacity: {
                            if (root.activePage === "git")
                                return gitService.available ? 0.50 : 0.30;

                            return githubService.available ? 0.50 : 0.30;
                        }
                        color: {
                            if (root.activePage === "git")
                                return gitService.available ? Colors.orange : Colors.red;

                            return githubService.available ? Colors.orange : Colors.red;
                        }
                    }

                    GohuText {
                        id: pageStatusText
                        anchors.centerIn: parent

                        text: {
                            if (root.activePage === "git")
                                return gitService.refreshing ? "READING" : gitService.available ? "LOCAL LIVE" : "OFFLINE";

                            return githubService.refreshing ? "READING" : githubService.available ? "PX LIVE" : "OFFLINE";
                        }

                        font.pixelSize: 8
                        color: {
                            if (root.activePage === "git")
                                return gitService.available ? Colors.orange : Colors.red;

                            return githubService.available ? Colors.orange : Colors.red;
                        }

                        layer.enabled: true
                        layer.effect: DropShadow {
                            radius: 10
                            samples: 11
                            opacity: 0.82
                            color: pageStatusText.color
                            transparentBorder: true
                        }
                    }
                }
            }

            Rectangle {
                width: parent.width
                height: 2
                color: Colors.cyan

                RectangularShadow {
                    anchors.fill: parent
                    spread: 3
                    z: -1
                    opacity: 0.34
                    color: Colors.cyan
                }
            }

            Row {
                width: parent.width
                spacing: 10

                PageTab {
                    width: (parent.width - 10) / 2
                    label: "GIT // LOCAL"
                    selected: root.activePage === "git"
                    onTriggered: root.showGitPage()
                }

                PageTab {
                    width: (parent.width - 10) / 2
                    label: "GITHUB // REMOTE"
                    selected: root.activePage === "github"
                    onTriggered: root.showGithubPage()
                }
            }

            Item {
                width: parent.width
                height: parent.height - 130

                Item {
                    anchors {
                        fill: parent
                        leftMargin: 46
                        rightMargin: 46
                    }
                    visible: root.activePage === "git"

                    Column {
                        anchors.fill: parent
                        spacing: 10

                        // ===== REPOSITORY / BRANCH CONTROL STRIP =====

                        Row {
                            width: parent.width
                            height: 82
                            spacing: 10

                            Rectangle {
                                width: (parent.width - 20) / 3
                                height: parent.height
                                color: Colors.dark
                                border.width: 1
                                border.color: Colors.cyan

                                Column {
                                    anchors {
                                        fill: parent
                                        margins: 8
                                    }
                                    spacing: 5

                                    MetaLabel {
                                        text: "REPOSITORY"
                                    }

                                    Row {
                                        width: parent.width
                                        height: 28
                                        spacing: 4

                                        ActionButton {
                                            width: 28
                                            height: 28
                                            label: "‹"
                                            enabledAction: gitService.repoCount > 1
                                            onTriggered: gitService.cycleRepo(-1)
                                        }

                                        SelectorInput {
                                            width: parent.width - 64
                                            valueText: gitService.repoLabel
                                            placeholderText: "TYPE REPO NAME"
                                            accentColor: Colors.orange

                                            onSubmitted: function(value) {
                                                gitService.selectRepoText(value);
                                            }
                                        }

                                        ActionButton {
                                            width: 28
                                            height: 28
                                            label: "›"
                                            enabledAction: gitService.repoCount > 1
                                            onTriggered: gitService.cycleRepo(1)
                                        }
                                    }

                                    DimValue {
                                        width: parent.width
                                        text: gitService.repository + "  //  " + gitService.repoRoot
                                        font.pixelSize: 8
                                    }
                                }
                            }

                            Rectangle {
                                width: (parent.width - 20) / 3
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

                                    OrangeLabel {
                                        text: "CURRENT LOCAL"
                                    }

                                    CyanValue {
                                        width: parent.width
                                        text: gitService.branch
                                        font.pixelSize: 12
                                    }

                                    Row {
                                        width: parent.width
                                        spacing: 8

                                        MetaLabel {
                                            text: "HEAD"
                                        }

                                        BlueValue {
                                            width: 82
                                            text: gitService.head
                                            font.pixelSize: 9
                                        }

                                        MetaValue {
                                            width: parent.width - 120
                                            text: gitService.worktree
                                            font.pixelSize: 9
                                        }
                                    }
                                }
                            }

                            Rectangle {
                                width: (parent.width - 20) / 3
                                height: parent.height
                                color: Colors.dark
                                border.width: 1
                                border.color:
                                    gitService.selectedRemoteExists
                                    ? Colors.cyan
                                    : Colors.magenta

                                Column {
                                    anchors {
                                        fill: parent
                                        margins: 8
                                    }
                                    spacing: 5

                                    MetaLabel {
                                        text: "REMOTE TARGET"
                                    }

                                    Row {
                                        width: parent.width
                                        height: 28
                                        spacing: 4

                                        ActionButton {
                                            width: 28
                                            height: 28
                                            label: "‹"
                                            enabledAction: gitService.remoteBranchCount > 0
                                            onTriggered: gitService.cycleRemote(-1)
                                        }

                                        SelectorInput {
                                            width: parent.width - 64
                                            valueText: gitService.selectedRemoteBranch
                                            placeholderText: "TYPE REMOTE BRANCH"
                                            accentColor:
                                                gitService.selectedRemoteExists
                                                ? Colors.cyan
                                                : Colors.magenta

                                            onSubmitted: function(value) {
                                                gitService.selectRemoteText(value);
                                            }
                                        }

                                        ActionButton {
                                            width: 28
                                            height: 28
                                            label: "›"
                                            enabledAction: gitService.remoteBranchCount > 0
                                            onTriggered: gitService.cycleRemote(1)
                                        }
                                    }

                                    GohuText {
                                        width: parent.width
                                        text:
                                            gitService.selectedRemoteExists
                                            ? "EXISTING REMOTE BRANCH"
                                            : gitService.selectedRemoteBranch
                                              ? "WILL CREATE THIS REMOTE BRANCH"
                                              : "NO REMOTE BRANCH AVAILABLE"
                                        font.pixelSize: 8
                                        color:
                                            gitService.selectedRemoteExists
                                            ? Colors.white
                                            : Colors.magenta
                                        elide: Text.ElideRight
                                    }
                                }
                            }
                        }

                        // ===== BRANCH MAP ==============================

                        BranchMap {
                            width: parent.width
                            height: 250

                            topologyService: gitService
                            titleText: "REPOSITORY BRANCH MAP"
                            selectedSha: root.selectedGitCommitSha

                            onCommitSelected: function(sha) {
                                const candidate = String(sha || "");
                                root.selectedGitCommitSha =
                                    root.selectedGitCommitSha === candidate
                                    ? ""
                                    : candidate;
                            }
                        }

                        // ===== SYNC CONTROLS ===========================

                        Rectangle {
                            width: parent.width
                            height: 58
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
                                    width: parent.width - 422
                                    height: parent.height
                                    spacing: 3

                                    SectionLabel {
                                        text: "SYNC // EXPLICIT DIRECTION"
                                    }

                                    GohuText {
                                        width: parent.width
                                        text:
                                            "PULL "
                                            + (
                                                gitService.selectedRemoteBranch
                                                ? gitService.selectedRemoteBranch
                                                : "REMOTE"
                                            )
                                            + " → "
                                            + gitService.branch
                                            + " // PUSH "
                                            + gitService.branch
                                            + " → "
                                            + (
                                                gitService.selectedRemoteBranch
                                                ? gitService.selectedRemoteBranch
                                                : "REMOTE"
                                            )
                                        font.pixelSize: 8
                                        color: Colors.white
                                        elide: Text.ElideRight
                                    }

                                    GohuText {
                                        width: parent.width
                                        text:
                                            gitService.upstream
                                            ? "TRACKING "
                                              + gitService.upstream
                                              + "  //  LOCAL +"
                                              + gitService.ahead
                                              + "  //  REMOTE +"
                                              + gitService.behind
                                            : "NO TRACKING BRANCH // PICK A REMOTE TARGET ABOVE"
                                        font.pixelSize: 8
                                        color:
                                            gitService.upstream
                                            ? Colors.cyan
                                            : Colors.magenta
                                        elide: Text.ElideRight
                                    }
                                }

                                ActionButton {
                                    width: 94
                                    height: 36
                                    anchors.verticalCenter: parent.verticalCenter
                                    label: "FETCH"
                                    enabledAction: !gitService.actionBusy
                                    selectedAction: gitService.actionTitle === "FETCH"
                                    onTriggered: gitService.runSyncAction("fetch")
                                }

                                ActionButton {
                                    width: 104
                                    height: 36
                                    anchors.verticalCenter: parent.verticalCenter
                                    label: "PULL"
                                    leftIcon: "◂"
                                    iconPixelSize: 29
                                    enabledAction:
                                        !gitService.actionBusy
                                        && gitService.selectedRemoteExists
                                    selectedAction: gitService.actionTitle === "PULL"
                                    onTriggered: gitService.runSyncAction("pull")
                                }

                                ModeActuator {
                                    width: 52
                                    height: 36
                                    anchors.verticalCenter: parent.verticalCenter
                                    icon: gitService.pullModeIcon
                                    tag: gitService.pullModeLabel
                                    active: true
                                    modeColor:
                                        gitService.pullMode === "ff-only"
                                        ? Colors.magenta
                                        : Colors.orange
                                    enabledAction: !gitService.actionBusy
                                    onTriggered: gitService.cyclePullMode()
                                }

                                ActionButton {
                                    width: 124
                                    height: 36
                                    anchors.verticalCenter: parent.verticalCenter
                                    label:
                                        gitService.selectedRemoteExists
                                        ? "PUSH"
                                        : "CREATE REMOTE"
                                    rightIcon:
                                        gitService.selectedRemoteExists
                                        ? "▸"
                                        : ""
                                    iconPixelSize: 29
                                    enabledAction:
                                        !gitService.actionBusy
                                        && !!gitService.selectedRemoteBranch
                                    selectedAction: gitService.actionTitle === "PUSH"
                                    onTriggered: gitService.runSyncAction("push")
                                }
                            }
                        }

                        // ===== LOCAL TOOLS =============================

                        Row {
                            width: parent.width
                            height: 36
                            spacing: 10

                            ActionButton {
                                width: 124
                                height: 36
                                label: "STATUS"
                                enabledAction: !gitService.actionBusy
                                selectedAction: gitService.actionTitle === "STATUS"
                                onTriggered: gitService.runReadAction("status")
                            }

                            ActionButton {
                                width: 124
                                height: 36
                                label: "DIFF"
                                enabledAction: !gitService.actionBusy
                                selectedAction: gitService.actionTitle === "DIFF"
                                onTriggered: gitService.runReadAction("diff")
                            }

                            ActionButton {
                                width: 124
                                height: 36
                                label: "LOG"
                                enabledAction: !gitService.actionBusy
                                selectedAction: gitService.actionTitle === "LOG"
                                onTriggered: gitService.runReadAction("log")
                            }

                            ActionButton {
                                width: 124
                                height: 36
                                label: "LAZYGIT"
                                enabledAction: true
                                onTriggered: gitService.launchLazygit()
                            }

                            Rectangle {
                                width: parent.width - 536
                                height: parent.height

                                readonly property bool cleanIdle:
                                    !gitService.actionBusy
                                    && gitService.worktree === "CLEAN"

                                color: Colors.dark
                                border.width: 1
                                border.color:
                                    gitService.actionExitCode === 0
                                    ? Colors.cyan
                                    : Colors.red

                                GohuText {
                                    anchors.centerIn: parent
                                    text:
                                        gitService.actionBusy
                                        ? gitService.actionTitle + " // RUNNING"
                                        : gitService.worktree
                                    font.pixelSize: 11
                                    color:
                                        gitService.actionExitCode === 0
                                        ? Colors.cyan
                                        : Colors.red
                                    opacity:
                                        parent.cleanIdle
                                        ? 0.34
                                        : 1.0
                                }
                            }
                        }

                        Rectangle {
                            width: parent.width
                            height: 112
                            color: Colors.dark
                            border.width: 1
                            border.color:
                                gitService.actionExitCode === 0
                                ? Colors.cyan
                                : Colors.red

                            GohuText {
                                anchors {
                                    top: parent.top
                                    left: parent.left
                                    right: parent.right
                                }
                                anchors.topMargin: 7
                                anchors.leftMargin: 9
                                anchors.rightMargin: 9
                                text:
                                    gitService.actionBusy
                                    ? gitService.actionTitle + " // RUNNING"
                                    : gitService.actionTitle + " // OUTPUT"
                                font.pixelSize: 9
                                color:
                                    gitService.actionExitCode === 0
                                    ? Colors.orange
                                    : Colors.red

                                layer.enabled: true
                                layer.effect: DropShadow {
                                    radius: 8
                                    samples: 9
                                    opacity: 0.62
                                    color:
                                        gitService.actionExitCode === 0
                                        ? Colors.orange
                                        : Colors.red
                                    transparentBorder: true
                                }
                            }

                            Flickable {
                                anchors {
                                    top: parent.top
                                    bottom: parent.bottom
                                    left: parent.left
                                    right: parent.right
                                }
                                anchors.topMargin: 24
                                anchors.bottomMargin: 7
                                anchors.leftMargin: 9
                                anchors.rightMargin: 9

                                clip: true
                                contentWidth: width
                                contentHeight: Math.max(height, localOutputText.implicitHeight)
                                boundsBehavior: Flickable.StopAtBounds

                                GohuText {
                                    id: localOutputText
                                    width: parent.width
                                    text: gitService.actionOutput
                                    font.pixelSize: 9
                                    color: Colors.white
                                    wrapMode: Text.WrapAnywhere

                                    layer.enabled: true
                                    layer.effect: DropShadow {
                                        radius: 5
                                        samples: 7
                                        opacity:
                                            gitService.actionExitCode === 0
                                            ? 0.24
                                            : 0.40
                                        color:
                                            gitService.actionExitCode === 0
                                            ? Colors.cyan
                                            : Colors.red
                                        transparentBorder: true
                                    }
                                }
                            }
                        }
                    }
                }

                Item {
                    id: githubPage

                    anchors.fill: parent
                    visible: root.activePage === "github"

                    Column {
                        anchors.fill: parent
                        spacing: 10

                        // ===== REMOTE IDENTITY + PX TELEMETRY =========

                        Rectangle {
                            width: parent.width
                            height: 100

                            color: Colors.dark
                            border.width: 1
                            border.color: Colors.cyan

                            RectangularShadow {
                                anchors.fill: parent
                                spread: 4
                                z: -1
                                opacity: 0.25
                                color: Colors.cyan
                            }

                            Column {
                                anchors {
                                    fill: parent
                                    margins: 9
                                }

                                spacing: 4

                                Row {
                                    width: parent.width
                                    height: 18

                                    SectionLabel {
                                        width: parent.width - 120
                                        text: "REMOTE // GITHUB"
                                    }

                                    GohuText {
                                        width: 120
                                        text:
                                            githubService.refreshing
                                            ? "READING"
                                            : githubService.available
                                            ? "LIVE // PX"
                                            : "OFFLINE"
                                        horizontalAlignment: Text.AlignRight
                                        font.pixelSize: 9
                                        color:
                                            githubService.available
                                            ? Colors.orange
                                            : Colors.red
                                    }
                                }

                                Row {
                                    width: parent.width
                                    height: 15
                                    spacing: 10

                                    OrangeLabel {
                                        width: 92
                                        text: "REPOSITORY"
                                    }

                                    CyanValue {
                                        width: parent.width - 102
                                        text: githubService.repoSlug || "NOT CONNECTED"
                                    }
                                }

                                Row {
                                    width: parent.width
                                    height: 15
                                    spacing: 10

                                    MetaLabel {
                                        width: 92
                                        text: "BRIDGE"
                                    }

                                    MetaValue {
                                        width: parent.width - 102
                                        text:
                                            githubService.lastError
                                            ? "ERROR // " + githubService.lastError
                                            : githubService.available
                                            ? "PX CONTROL READY"
                                            : "WAITING"
                                        color:
                                            githubService.lastError
                                            ? Colors.red
                                            : Colors.white
                                    }
                                }

                                Row {
                                    width: parent.width
                                    height: 18
                                    spacing: 10

                                    BlueLabel {
                                        width: 92
                                        text: "PX / STATE"
                                    }

                                    GohuText {
                                        width: parent.width - 102
                                        text: root.githubStateText()
                                        font.pixelSize: 9
                                        color: root.githubStateColor()
                                        elide: Text.ElideRight
                                    }
                                }
                            }
                        }

                        // ===== ACTIVE GITHUB CAMERA ====================

                        Item {
                            id: githubCameraBody

                            width: parent.width
                            height: parent.height - 178

                            Item {
                                id: githubControlCamera

                                anchors.fill: parent
                                visible: root.githubView === "control"

                                Column {
                                    anchors.fill: parent
                                    spacing: 10

                                    Rectangle {
                                                                width: parent.width
                                                                height: 242
                                    
                                                                color: Colors.dark
                                                                border.width: 1
                                                                border.color: Colors.orange
                                    
                                                                RectangularShadow {
                                                                    anchors.fill: parent
                                                                    spread: 4
                                                                    z: -1
                                                                    opacity: 0.22
                                                                    color: Colors.orange
                                                                }
                                    
                                                                SectionLabel {
                                                                    anchors {
                                                                        left: parent.left
                                                                        top: parent.top
                                                                        leftMargin: 10
                                                                        topMargin: 8
                                                                    }
                                    
                                                                    text: "WORKFLOW FACTORY // MIXER"
                                                                }
                                    
                                                                GohuText {
                                                                    anchors {
                                                                        right: parent.right
                                                                        top: parent.top
                                                                        rightMargin: 10
                                                                        topMargin: 9
                                                                    }
                                    
                                                                    text: "STATE → CONFIGURE → PREVIEW → SAVE"
                                                                    font.pixelSize: 8
                                                                    color: Colors.white
                                                                    opacity: 0.72
                                                                }
                                    
                                                                Row {
                                                                    id: factoryBody
                                    
                                                                    anchors {
                                                                        left: parent.left
                                                                        right: parent.right
                                                                        top: parent.top
                                                                        leftMargin: 10
                                                                        rightMargin: 10
                                                                        topMargin: 31
                                                                    }
                                    
                                                                    height: 160
                                                                    spacing: 10
                                    
                                                                    Row {
                                                                        id: dialBayRow
                                    
                                                                        width: 444
                                                                        height: parent.height
                                                                        spacing: 8
                                    
                                                                        Rectangle {
                                                                            width: (dialBayRow.width - 16) / 3
                                                                            height: parent.height
                                    
                                                                            color: Colors.black
                                                                            border.width: 1
                                                                            border.color: Colors.cyan
                                    
                                                                            SelectorDial {
                                                                                anchors {
                                                                                    fill: parent
                                                                                    margins: 3
                                                                                }
                                    
                                                                                labelText: "IGNITION"
                                                                                options: ["manual", "push", "manual+push"]
                                                                                displayOptions: ["MAN", "PUSH", "M+P"]
                                                                                currentIndex: root.factoryTrigger === "push"
                                                                                              ? 1
                                                                                              : root.factoryTrigger === "manual+push"
                                                                                              ? 2
                                                                                              : 0
                                                                                readoutText: root.factoryTrigger.toUpperCase()
                                    
                                                                                onSelectionRequested: function(index, value) {
                                                                                    const next = String(value);
                                    
                                                                                    if (root.factoryTrigger === next)
                                                                                        return;
                                    
                                                                                    root.factoryTrigger = next;
                                                                                    githubService.clearFactoryResult();
                                                                                }
                                                                            }
                                                                        }
                                    
                                                                        Rectangle {
                                                                            width: (dialBayRow.width - 16) / 3
                                                                            height: parent.height
                                    
                                                                            color: Colors.black
                                                                            border.width: 1
                                                                            border.color: Colors.cyan
                                    
                                                                            SelectorDial {
                                                                                anchors {
                                                                                    fill: parent
                                                                                    margins: 3
                                                                                }
                                    
                                                                                labelText: "OPERATION"
                                                                                options: ["smoke", "shell-check"]
                                                                                displayOptions: ["SMOKE", "SHELL"]
                                                                                currentIndex: root.factoryTemplate === "shell-check" ? 1 : 0
                                                                                readoutText: root.factoryTemplate.toUpperCase()
                                    
                                                                                onSelectionRequested: function(index, value) {
                                                                                    const next = String(value);
                                    
                                                                                    if (root.factoryTemplate === next)
                                                                                        return;
                                    
                                                                                    root.factoryTemplate = next;
                                                                                    githubService.clearFactoryResult();
                                                                                }
                                                                            }
                                                                        }
                                    
                                                                        Rectangle {
                                                                            width: (dialBayRow.width - 16) / 3
                                                                            height: parent.height
                                    
                                                                            color: Colors.black
                                                                            border.width: 1
                                                                            border.color: Colors.cyan
                                    
                                                                            SelectorDial {
                                                                                anchors {
                                                                                    fill: parent
                                                                                    margins: 3
                                                                                }
                                    
                                                                                labelText: "TARGET"
                                                                                options: ["current-repo"]
                                                                                displayOptions: ["REPO"]
                                                                                currentIndex: 0
                                                                                interactive: false
                                                                                readoutText: "CURRENT REPO"
                                                                            }
                                                                        }
                                                                    }
                                    
                                                                    Rectangle {
                                                                        width: factoryBody.width - dialBayRow.width - 10
                                                                        height: parent.height
                                    
                                                                        color: Colors.black
                                                                        border.width: 1
                                                                        border.color: Colors.magenta
                                    
                                                                        Column {
                                                                            anchors {
                                                                                fill: parent
                                                                                margins: 8
                                                                            }
                                    
                                                                            spacing: 5
                                    
                                                                            Row {
                                                                                width: parent.width
                                    
                                                                                GohuText {
                                                                                    width: parent.width - 76
                                                                                    text: "CODE // UNDER THE HOOD"
                                                                                    font.pixelSize: 10
                                                                                    color: Colors.magenta
                                                                                }
                                    
                                                                                GohuText {
                                                                                    width: 76
                                                                                    text: githubService.factoryValidationStatus
                                                                                    horizontalAlignment: Text.AlignRight
                                                                                    font.pixelSize: 7
                                                                                    color: githubService.factoryValidationStatus === "PASS"
                                                                                           ? Colors.orange
                                                                                           : githubService.factoryValidationStatus === "FAIL"
                                                                                             || githubService.factoryValidationStatus === "ERROR"
                                                                                           ? Colors.red
                                                                                           : Colors.white
                                                                                }
                                                                            }
                                    
                                                                            Rectangle {
                                                                                width: parent.width
                                                                                height: 123
                                                                                color: Colors.dark
                                                                                border.width: 1
                                                                                border.color: Colors.blue
                                                                                clip: true
                                    
                                                                                GohuText {
                                                                                    anchors {
                                                                                        fill: parent
                                                                                        margins: 7
                                                                                    }
                                    
                                                                                    text: githubService.factoryYaml
                                                                                          ? githubService.factoryYaml
                                                                                          : "PREVIEW WILL RENDER THE REAL GITHUB WORKFLOW YAML HERE.\n\nTHE DIALS CHANGE THE CODE; THEY DO NOT HIDE IT."
                                                                                    textFormat: Text.PlainText
                                                                                    wrapMode: Text.WrapAnywhere
                                                                                    font.pixelSize: 8
                                                                                    color: githubService.factoryYaml ? Colors.white : Colors.cyan
                                                                                }
                                                                            }
                                                                        }
                                                                    }
                                                                }
                                    
                                                                Row {
                                                                    anchors {
                                                                        left: parent.left
                                                                        right: parent.right
                                                                        bottom: parent.bottom
                                                                        leftMargin: 10
                                                                        rightMargin: 10
                                                                        bottomMargin: 9
                                                                    }
                                    
                                                                    height: 38
                                                                    spacing: 8
                                    
                                                                    Rectangle {
                                                                        width: parent.width - 348
                                                                        height: 34
                                                                        color: Colors.black
                                                                        border.width: 1
                                                                        border.color: factoryNameInput.activeFocus ? Colors.magenta : Colors.orange
                                    
                                                                        GohuText {
                                                                            anchors {
                                                                                left: parent.left
                                                                                verticalCenter: parent.verticalCenter
                                                                                leftMargin: 8
                                                                            }
                                    
                                                                            visible: factoryNameInput.text.length === 0 && !factoryNameInput.activeFocus
                                                                            text: "WORKFLOW NAME"
                                                                            font.pixelSize: 9
                                                                            color: Colors.white
                                                                            opacity: 0.45
                                                                        }
                                    
                                                                        TextInput {
                                                                            id: factoryNameInput
                                    
                                                                            anchors {
                                                                                fill: parent
                                                                                margins: 6
                                                                            }
                                    
                                                                            activeFocusOnPress: true
                                                                            selectByMouse: true
                                                                            verticalAlignment: TextInput.AlignVCenter
                                                                            clip: true
                                                                            font.family: "GohuFont 11 Nerd Font Mono"
                                                                            font.pixelSize: 10
                                                                            color: Colors.white
                                                                            selectionColor: Colors.magenta
                                                                            selectedTextColor: Colors.black
                                    
                                                                            onTextChanged: githubService.clearFactoryResult()
                                    
                                                                            onActiveFocusChanged: {
                                                                                if (activeFocus)
                                                                                    root.activeTextEditor = factoryNameInput;
                                                                                else if (root.activeTextEditor === factoryNameInput)
                                                                                    root.activeTextEditor = null;
                                                                            }
                                                                        }
                                                                    }
                                    
                                                                    ActionButton {
                                                                        width: 148
                                                                        height: 34
                                                                        label: githubService.factoryBusy && githubService.factoryMode === "preview"
                                                                               ? "PREVIEWING"
                                                                               : "PREVIEW CODE"
                                                                        enabledAction: githubService.available
                                                                                       && !githubService.factoryBusy
                                                                                       && factoryNameInput.text.trim().length > 0
                                                                        onTriggered: githubService.previewWorkflow(
                                                                            root.factoryTemplate,
                                                                            factoryNameInput.text.trim(),
                                                                            root.factoryTrigger
                                                                        )
                                                                    }
                                    
                                                                    ActionButton {
                                                                        width: 184
                                                                        height: 38
                                                                        primaryBlue: true
                                                                        label: githubService.factoryBusy && githubService.factoryMode === "install"
                                                                               ? "SAVING"
                                                                               : "SAVE WORKFLOW"
                                                                        enabledAction: githubService.available
                                                                                       && !githubService.factoryBusy
                                                                                       && githubService.factoryMode === "preview"
                                                                                       && githubService.factoryValidationStatus === "PASS"
                                                                                       && githubService.factoryLastTemplate === root.factoryTemplate
                                                                                       && githubService.factoryLastTrigger === root.factoryTrigger
                                                                                       && githubService.factoryLastSlug === factoryNameInput.text.trim()
                                                                        onTriggered: githubService.installWorkflow(
                                                                            root.factoryTemplate,
                                                                            factoryNameInput.text.trim(),
                                                                            root.factoryTrigger
                                                                        )
                                                                    }
                                                                }
                                                            }

                                    Rectangle {
                                                                id: workflowLibrary
                                    
                                                                width: parent.width
                                                                height: 92
                                                                z: root.workflowMenuOpen ? 300 : 0
                                    
                                                                color: Colors.dark
                                                                border.width: 1
                                                                border.color: Colors.cyan
                                    
                                                                RectangularShadow {
                                                                    anchors.fill: parent
                                                                    spread: 3
                                                                    z: -1
                                                                    opacity: 0.20
                                                                    color: Colors.cyan
                                                                }
                                    
                                                                Column {
                                                                    anchors {
                                                                        fill: parent
                                                                        margins: 9
                                                                    }
                                    
                                                                    spacing: 6
                                    
                                                                    Row {
                                                                        width: parent.width
                                    
                                                                        SectionLabel {
                                                                            width: parent.width - 90
                                                                            text: "WORKFLOW LIBRARY // SAVED MACHINES"
                                                                        }
                                    
                                                                        GohuText {
                                                                            width: 90
                                                                            text: String(githubService.workflowCount) + " INSTALLED"
                                                                            horizontalAlignment: Text.AlignRight
                                                                            font.pixelSize: 8
                                                                            color: Colors.orange
                                                                        }
                                                                    }
                                    
                                                                    Row {
                                                                        width: parent.width
                                                                        height: 32
                                                                        spacing: 8
                                    
                                                                        ActionButton {
                                                                            width: parent.width - 258
                                                                            height: 30
                                                                            enabledAction: githubService.available
                                                                                           && githubService.workflowCount > 0
                                                                                           && !githubService.refreshing
                                                                                           && !githubService.actionBusy
                                                                            label: root.selectedWorkflow
                                                                                   ? String(root.selectedWorkflowIndex + 1)
                                                                                     + "/" + String(githubService.workflowCount)
                                                                                     + " // "
                                                                                     + String(root.selectedWorkflow.name || root.selectedWorkflow.path || "UNKNOWN")
                                                                                   : "0 // NO WORKFLOWS"
                                                                            onTriggered: root.cycleWorkflow()
                                                                        }
                                    
                                                                        ActionButton {
                                                                            width: 34
                                                                            height: 30
                                                                            label: root.workflowMenuOpen ? "▴" : "▾"
                                                                            enabledAction: githubService.available
                                                                                           && githubService.workflowCount > 0
                                                                                           && !githubService.refreshing
                                                                                           && !githubService.actionBusy
                                                                            selectedAction: root.workflowMenuOpen
                                                                            onTriggered: root.workflowMenuOpen = !root.workflowMenuOpen
                                                                        }
                                    
                                                                        ActionButton {
                                                                            width: 100
                                                                            height: 30
                                                                            label: "REFRESH"
                                                                            enabledAction: !githubService.refreshing
                                                                                           && !githubService.actionBusy
                                                                                           && !githubService.factoryBusy
                                                                            onTriggered: githubService.refresh()
                                                                        }
                                    
                                                                        ActionButton {
                                                                            width: 100
                                                                            height: 30
                                                                            label: githubService.actionBusy && githubService.actionKind === "run"
                                                                                   ? "RUNNING"
                                                                                   : "RUN"
                                                                            enabledAction: root.selectedWorkflow
                                                                                           && !githubService.refreshing
                                                                                           && !githubService.actionBusy
                                                                                           && !githubService.factoryBusy
                                                                            onTriggered: githubService.runWorkflow(
                                                                                String(root.selectedWorkflow.path || root.selectedWorkflow.name || "")
                                                                            )
                                                                        }
                                                                    }
                                                                }
                                                            }

                                    Rectangle {
                                                                width: parent.width
                                                                height: 92
                                    
                                                                color: Colors.dark
                                                                border.width: 1
                                                                border.color: Colors.blue
                                    
                                                                RectangularShadow {
                                                                    anchors.fill: parent
                                                                    spread: 3
                                                                    z: -1
                                                                    opacity: 0.20
                                                                    color: Colors.blue
                                                                }
                                    
                                                                Column {
                                                                    anchors {
                                                                        fill: parent
                                                                        margins: 9
                                                                    }
                                    
                                                                    spacing: 6
                                    
                                                                    Row {
                                                                        width: parent.width
                                    
                                                                        SectionLabel {
                                                                            width: parent.width - 90
                                                                            text: "RUNS // RESULT STATE"
                                                                        }
                                    
                                                                        GohuText {
                                                                            width: 90
                                                                            text: String(githubService.runCount) + " RECENT"
                                                                            horizontalAlignment: Text.AlignRight
                                                                            font.pixelSize: 8
                                                                            color: Colors.orange
                                                                        }
                                                                    }
                                    
                                                                    Row {
                                                                        width: parent.width
                                                                        height: 32
                                                                        spacing: 8
                                    
                                                                        ActionButton {
                                                                            width: parent.width - 220
                                                                            height: 30
                                                                            enabledAction: githubService.available
                                                                                           && githubService.runCount > 0
                                                                                           && !githubService.refreshing
                                                                                           && !githubService.actionBusy
                                                                            label: root.selectedRun
                                                                                   ? String(root.selectedRunIndex + 1)
                                                                                     + "/" + String(githubService.runCount)
                                                                                     + " // #"
                                                                                     + String(root.selectedRun.databaseId || "?")
                                                                                     + " // "
                                                                                     + String(root.selectedRun.status || "UNKNOWN").toUpperCase()
                                                                                     + " // "
                                                                                     + String(root.selectedRun.conclusion || "")
                                                                                   : "0 // NO RUNS"
                                                                            onTriggered: root.cycleRun()
                                                                        }
                                    
                                                                        ActionButton {
                                                                            width: 102
                                                                            height: 30
                                                                            label: githubService.actionBusy && githubService.actionKind === "rerun"
                                                                                   ? "RERUNNING"
                                                                                   : "RERUN"
                                                                            enabledAction: root.selectedRun
                                                                                           && root.selectedRunStatus === "completed"
                                                                                           && !githubService.refreshing
                                                                                           && !githubService.actionBusy
                                                                                           && !githubService.factoryBusy
                                                                            onTriggered: githubService.rerunRun(root.selectedRun.databaseId)
                                                                        }
                                    
                                                                        ActionButton {
                                                                            width: 102
                                                                            height: 30
                                                                            label: githubService.actionBusy && githubService.actionKind === "cancel"
                                                                                   ? "CANCELLING"
                                                                                   : "CANCEL"
                                                                            enabledAction: root.selectedRun
                                                                                           && root.selectedRunStatus !== "completed"
                                                                                           && !githubService.refreshing
                                                                                           && !githubService.actionBusy
                                                                                           && !githubService.factoryBusy
                                                                            onTriggered: githubService.cancelRun(root.selectedRun.databaseId)
                                                                        }
                                                                    }
                                                                }
                                                            }
                                }

                                Rectangle {
                                                            id: workflowDropdown
                                
                                                            visible: root.workflowMenuOpen
                                                                     && githubService.workflowCount > 0
                                                            z: 500
                                
                                                            x: 9
                                                            y: 348
                                                            width: parent.width - 18
                                
                                                            height: Math.min(githubService.workflowCount, 5) * 30 + 8
                                                            color: Colors.black
                                                            border.width: 1
                                                            border.color: Colors.orange
                                                            clip: true
                                
                                                            RectangularShadow {
                                                                anchors.fill: parent
                                                                spread: 4
                                                                z: -1
                                                                opacity: 0.28
                                                                color: Colors.orange
                                                            }
                                
                                                            Flickable {
                                                                anchors {
                                                                    fill: parent
                                                                    margins: 4
                                                                }
                                
                                                                clip: true
                                                                contentWidth: width
                                                                contentHeight: workflowMenuColumn.height
                                                                boundsBehavior: Flickable.StopAtBounds
                                
                                                                Column {
                                                                    id: workflowMenuColumn
                                                                    width: parent.width
                                                                    spacing: 0
                                
                                                                    Repeater {
                                                                        model: githubService.workflows
                                
                                                                        Rectangle {
                                                                            required property int index
                                                                            required property var modelData
                                
                                                                            width: workflowMenuColumn.width
                                                                            height: 30
                                
                                                                            readonly property bool selected:
                                                                                index === root.selectedWorkflowIndex
                                
                                                                            color:
                                                                                selected
                                                                                ? Colors.yellow
                                                                                : workflowChoiceMouse.containsMouse
                                                                                ? Colors.dark
                                                                                : Colors.black
                                
                                                                            border.width: 0
                                
                                                                            GohuText {
                                                                                anchors {
                                                                                    left: parent.left
                                                                                    right: parent.right
                                                                                    verticalCenter: parent.verticalCenter
                                                                                    leftMargin: 8
                                                                                    rightMargin: 8
                                                                                }
                                
                                                                                text:
                                                                                    String(index + 1)
                                                                                    + " // "
                                                                                    + String(
                                                                                        modelData.name
                                                                                        || modelData.path
                                                                                        || "UNKNOWN"
                                                                                    )
                                                                                font.pixelSize: 9
                                                                                color:
                                                                                    parent.selected
                                                                                    ? Colors.magenta
                                                                                    : workflowChoiceMouse.containsMouse
                                                                                    ? Colors.orange
                                                                                    : Colors.cyan
                                                                                elide: Text.ElideRight
                                                                            }
                                
                                                                            Rectangle {
                                                                                anchors {
                                                                                    left: parent.left
                                                                                    right: parent.right
                                                                                    bottom: parent.bottom
                                                                                }
                                                                                height: 1
                                                                                color: Colors.cyan
                                                                                opacity: 0.18
                                                                            }
                                
                                                                            MouseArea {
                                                                                id: workflowChoiceMouse
                                                                                anchors.fill: parent
                                                                                hoverEnabled: true
                                                                                cursorShape: Qt.PointingHandCursor
                                                                                onClicked: root.selectWorkflow(index)
                                                                            }
                                                                        }
                                                                    }
                                                                }
                                                            }
                                                        }
                            }

                            WorkflowLibraryView {
                                anchors.fill: parent
                                visible: root.githubView === "library"

                                githubService: githubService
                                libraryStore: workflowLibraryStore

                                onWorkflowSelected: function(index) {
                                    root.selectedWorkflowIndex = index;
                                    root.showGithubControl();
                                }
                            }
                        }

                        // ===== APPCONTROL-STYLE GITHUB MODE RAIL ======

                        Row {
                            id: githubModeButtonRow

                            width: parent.width
                            height: 58
                            spacing: 8

                            Repeater {
                                model: [
                                    {
                                        name: "CONTROL",
                                        key: "control",
                                        symbol: "◎"
                                    },
                                    {
                                        name: "LIBRARY",
                                        key: "library",
                                        symbol: "▤"
                                    }
                                ]

                                Rectangle {
                                    id: githubModeButton

                                    required property int index
                                    required property var modelData

                                    readonly property bool isSelected:
                                        root.githubView === modelData.key

                                    readonly property bool isHovered:
                                        githubModeMouse.containsMouse

                                    readonly property bool isPressed:
                                        githubModeMouse.pressed

                                    readonly property color contentColor:
                                        isPressed
                                        ? Colors.black
                                        : isSelected
                                        ? Colors.magenta
                                        : isHovered
                                        ? Colors.orange
                                        : Colors.cyan

                                    width:
                                        (
                                            githubModeButtonRow.width
                                            - githubModeButtonRow.spacing
                                        )
                                        / 2

                                    height: parent.height

                                    scale:
                                        isPressed
                                        ? 0.99
                                        : isHovered
                                        ? 1.025
                                        : isSelected
                                        ? 1.01
                                        : 1.0

                                    color:
                                        isPressed
                                        ? Colors.magenta
                                        : isHovered || isSelected
                                        ? Colors.yellow
                                        : Colors.black

                                    border.width: 1
                                    border.color:
                                        isHovered || isPressed || isSelected
                                        ? Colors.orange
                                        : Colors.cyan

                                    Behavior on scale {
                                        NumberAnimation {
                                            duration: 90
                                            easing.type: Easing.OutQuad
                                        }
                                    }

                                    Column {
                                        width: parent.width
                                        anchors.centerIn: parent
                                        spacing: 1

                                        NotoText {
                                            width: parent.width
                                            text: modelData.symbol
                                            horizontalAlignment: Text.AlignHCenter
                                            font.pixelSize: 19
                                            color: githubModeButton.contentColor
                                        }

                                        GohuText {
                                            width: parent.width
                                            text: modelData.name
                                            horizontalAlignment: Text.AlignHCenter
                                            font.pixelSize: 10
                                            color: githubModeButton.contentColor
                                        }
                                    }

                                    MouseArea {
                                        id: githubModeMouse

                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor

                                        onClicked: {
                                            if (modelData.key === "library")
                                                root.showGithubLibrary();
                                            else
                                                root.showGithubControl();
                                        }
                                    }

                                    RectangularShadow {
                                        anchors.fill: parent

                                        spread:
                                            githubModeButton.isHovered
                                            ? 6
                                            : githubModeButton.isSelected
                                            ? 4
                                            : 2

                                        z: -1

                                        opacity:
                                            githubModeButton.isPressed
                                            ? 0.62
                                            : githubModeButton.isHovered
                                            ? 0.56
                                            : githubModeButton.isSelected
                                            ? 0.46
                                            : 0.10

                                        color: Colors.orange
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
