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
    property string factoryTemplate: "smoke"
    property string factoryTrigger: "manual"
    property int selectedWorkflowIndex: 0
    property int selectedRunIndex: 0

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

    // Local Git stays compact. The automation mixer gets enough chassis
    // space for three physical selector bays, generated code, library, and runs.
    property int panelWidth: root.activePage === "github" ? 860 : 540
    property int panelHeight: root.activePage === "github" ? 790 : 650
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

    // PanelWindow defaults to non-focusable. The GitHub factory contains a
    // TextInput, so let Wayland grant keyboard focus while that page is open.
    focusable: root.menuOpen && root.activePage === "github"

    mask: Region {
        x: 0
        y: 0
        width: root.menuOpen ? root.width : 0
        height: root.menuOpen ? root.height : 0
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
        root.activePage = "git";
        gitService.refresh();
    }

    function showGithubPage() {
        root.activePage = "github";
        gitService.refresh();
        githubService.refresh();
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

    Component.onCompleted: gitService.refresh()

    GitService {
        id: gitService
    }

    GitHubService {
        id: githubService
        originUrl: gitService.origin
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
        interval: 3000
        repeat: true
        running: root.menuOpen && root.activePage === "git"

        onTriggered: gitService.refresh()
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

    component ActionButton: Rectangle {
        id: actionButton

        property string label: ""
        property bool enabledAction: false
        property bool selectedAction: false

        signal triggered()

        readonly property bool hovered:
            enabledAction && actionMouse.containsMouse
        readonly property bool pressed:
            enabledAction && actionMouse.pressed

        readonly property color contentColor:
            pressed
            ? Colors.black
            : selectedAction
            ? Colors.magenta
            : hovered
            ? Colors.orange
            : Colors.white

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
            : hovered || selectedAction
            ? Colors.yellow
            : Colors.black

        border.width: 1
        border.color:
            pressed
            ? Colors.magenta
            : hovered
            ? Colors.orange
            : selectedAction
            ? Colors.orange
            : Colors.cyan

        opacity: enabledAction ? 1.0 : 0.22

        Behavior on scale {
            NumberAnimation {
                duration: 90
                easing.type: Easing.OutQuad
            }
        }

        GohuText {
            id: actionText
            anchors.centerIn: parent
            text: actionButton.label
            font.pixelSize: 11
            color: actionButton.contentColor
            opacity: 1.0

            layer.enabled: !actionButton.pressed
            layer.effect: DropShadow {
                radius: 10
                samples: 11
                opacity:
                    actionButton.hovered
                    ? 0.72
                    : actionButton.selectedAction
                    ? 0.68
                    : actionButton.enabledAction
                    ? 0.62
                    : 0.12
                color:
                    actionButton.hovered || actionButton.selectedAction
                    ? Colors.orange
                    : Colors.cyan
                transparentBorder: true
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
                ? 0.48
                : actionButton.hovered
                ? 0.40
                : actionButton.selectedAction
                ? 0.36
                : actionButton.enabledAction
                ? 0.26
                : 0.07
            color:
                actionButton.pressed
                ? Colors.magenta
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

        scale:
            pressed
            ? 0.99
            : hovered
            ? 1.025
            : selected
            ? 1.01
            : 1.0

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

        Behavior on scale {
            NumberAnimation {
                duration: 90
                easing.type: Easing.OutQuad
            }
        }

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
                : Colors.white
            opacity: 1.0

            layer.enabled: !pageTab.pressed
            layer.effect: DropShadow {
                radius: 10
                samples: 11
                opacity:
                    pageTab.hovered
                    ? 0.72
                    : pageTab.selected
                    ? 0.68
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
                ? 0.48
                : pageTab.hovered
                ? 0.40
                : pageTab.selected
                ? 0.36
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

        Rectangle {
            anchors.fill: parent
            anchors.margins: root.frameInset

            color: "transparent"
            border.width: 1
            border.color: Colors.cyan
            opacity: 0.70
        }

        Column {
            anchors {
                fill: parent
                margins: 18
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
                    anchors.fill: parent
                    visible: root.activePage === "git"

                    Column {
                        anchors.fill: parent
                        spacing: 12

                        Rectangle {
                            width: parent.width
                            height: 140

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
                                    margins: 12
                                }

                                spacing: 8

                                SectionLabel {
                                    text: "LOCAL TRUTH"
                                }

                                Row {
                                    spacing: 10

                                    MetaLabel {
                                        width: 100
                                        text: "REPOSITORY"
                                    }

                                    OrangeValue {
                                        width: 365
                                        text: gitService.repository
                                    }
                                }

                                Row {
                                    spacing: 10

                                    OrangeLabel {
                                        width: 100
                                        text: "BRANCH"
                                    }

                                    CyanValue {
                                        width: 365
                                        text: gitService.branch
                                    }
                                }

                                Row {
                                    spacing: 10

                                    MetaLabel {
                                        width: 100
                                        text: "HEAD"
                                    }

                                    BlueValue {
                                        width: 365
                                        text: gitService.head
                                    }
                                }

                                Row {
                                    width: parent.width
                                    height: 16
                                    spacing: 10

                                    MetaLabel {
                                        width: 100
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: "WORKTREE"
                                    }

                                    Row {
                                        width: 365
                                        height: parent.height
                                        spacing: 0

                                        MetaValue {
                                            anchors.verticalCenter: parent.verticalCenter
                                            visible: String(gitService.worktree).indexOf("DIRTY") !== 0
                                            text: gitService.worktree
                                        }

                                        MetaValue {
                                            anchors.verticalCenter: parent.verticalCenter
                                            visible: String(gitService.worktree).indexOf("DIRTY") === 0
                                            text: "DIRTY • "
                                        }

                                        OrangeValue {
                                            anchors.verticalCenter: parent.verticalCenter
                                            visible: String(gitService.worktree).indexOf("DIRTY") === 0
                                            text: {
                                                const match = String(gitService.worktree).match(/(\d+)\s+CHANGES/);
                                                return match ? match[1] : "";
                                            }
                                        }

                                        MetaValue {
                                            anchors.verticalCenter: parent.verticalCenter
                                            visible: String(gitService.worktree).indexOf("DIRTY") === 0
                                            text: " CHANGES"
                                        }
                                    }
                                }
                            }
                        }

                        SectionLabel {
                            text: "LOCAL ACTIONS"
                        }

                        Row {
                            width: parent.width
                            spacing: 10

                            ActionButton {
                                label: "STATUS"
                                enabledAction: !gitService.actionBusy
                                selectedAction: gitService.actionTitle === "STATUS"
                                onTriggered: gitService.runReadAction("status")
                            }

                            ActionButton {
                                label: "DIFF"
                                enabledAction: !gitService.actionBusy
                                selectedAction: gitService.actionTitle === "DIFF"
                                onTriggered: gitService.runReadAction("diff")
                            }

                            ActionButton {
                                label: "LOG"
                                enabledAction: !gitService.actionBusy
                                selectedAction: gitService.actionTitle === "LOG"
                                onTriggered: gitService.runReadAction("log")
                            }

                            ActionButton {
                                label: "LAZYGIT"
                                enabledAction: true
                                onTriggered: gitService.launchLazygit()
                            }
                        }

                        Rectangle {
                            width: parent.width
                            height: 166

                            color: Colors.dark
                            border.width: 1
                            border.color: Colors.orange

                            RectangularShadow {
                                anchors.fill: parent
                                spread: 4
                                z: -1
                                opacity: 0.18
                                color: Colors.orange
                            }

                            GohuText {
                                anchors {
                                    top: parent.top
                                    left: parent.left
                                    right: parent.right
                                }

                                anchors.topMargin: 8
                                anchors.leftMargin: 10
                                anchors.rightMargin: 10

                                text: gitService.actionBusy ? gitService.actionTitle + " // RUNNING" : gitService.actionTitle
                                font.pixelSize: 10
                                color: Colors.orange
                            }

                            Flickable {
                                anchors {
                                    top: parent.top
                                    bottom: parent.bottom
                                    left: parent.left
                                    right: parent.right
                                }

                                anchors.topMargin: 27
                                anchors.bottomMargin: 8
                                anchors.leftMargin: 10
                                anchors.rightMargin: 10

                                clip: true
                                contentWidth: width
                                contentHeight: Math.max(height, outputText.implicitHeight)
                                boundsBehavior: Flickable.StopAtBounds

                                GohuText {
                                    id: outputText
                                    width: parent.width
                                    text: gitService.actionOutput
                                    font.pixelSize: 9
                                    color: Colors.white
                                    wrapMode: Text.WrapAnywhere

                                    layer.enabled: true
                                    layer.effect: DropShadow {
                                        radius: 5
                                        samples: 7
                                        opacity: 0.10
                                        color: Colors.cyan
                                        transparentBorder: true
                                    }
                                }
                            }
                        }

                        Rectangle {
                            width: parent.width
                            height: 70

                            color: Colors.dark
                            border.width: 1
                            border.color: Colors.cyan

                            Column {
                                anchors {
                                    fill: parent
                                    margins: 10
                                }

                                spacing: 7

                                SectionLabel {
                                    text: "REMOTE ENDPOINT"
                                }

                                Row {
                                    spacing: 10

                                    BlueLabel {
                                        width: 100
                                        text: "ORIGIN"
                                    }

                                    OrangeValue {
                                        width: 365
                                        text: gitService.origin
                                    }
                                }
                            }
                        }
                    }
                }

                Item {
                    anchors.fill: parent
                    visible: root.activePage === "github"

                    Column {
                        anchors.fill: parent
                        spacing: 10

                        // ===== REMOTE IDENTITY =========================

                        Rectangle {
                            width: parent.width
                            height: 80

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
                                    margins: 10
                                }

                                spacing: 5

                                Row {
                                    width: parent.width
                                    height: 18

                                    SectionLabel {
                                        width: parent.width - 120
                                        text: "REMOTE // GITHUB"
                                    }

                                    GohuText {
                                        width: 120
                                        text: githubService.refreshing
                                              ? "READING"
                                              : githubService.available
                                              ? "LIVE // PX"
                                              : "OFFLINE"
                                        horizontalAlignment: Text.AlignRight
                                        font.pixelSize: 9
                                        color: githubService.available ? Colors.orange : Colors.red
                                    }
                                }

                                Row {
                                    width: parent.width
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
                                    spacing: 10

                                    MetaLabel {
                                        width: 92
                                        text: "BRIDGE"
                                    }

                                    MetaValue {
                                        width: parent.width - 102
                                        text: githubService.lastError
                                              ? "ERROR // " + githubService.lastError
                                              : githubService.available
                                              ? "PX CONTROL READY"
                                              : "WAITING"
                                        color: githubService.lastError ? Colors.red : Colors.white
                                    }
                                }
                            }
                        }

                        // ===== WORKFLOW FACTORY / MIXER ===============

                        Rectangle {
                            width: parent.width
                            height: 250

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

                                        Column {
                                            anchors {
                                                fill: parent
                                                margins: 8
                                            }

                                            spacing: 5

                                            GohuText {
                                                width: parent.width
                                                text: "IGNITION"
                                                horizontalAlignment: Text.AlignHCenter
                                                font.pixelSize: 10
                                                color: Colors.magenta
                                            }

                                            Item {
                                                width: parent.width
                                                height: 94

                                                Rectangle {
                                                    anchors.centerIn: parent
                                                    width: 88
                                                    height: 88
                                                    radius: 44
                                                    color: Colors.dark
                                                    border.width: 2
                                                    border.color: Colors.cyan

                                                    Rectangle {
                                                        anchors.centerIn: parent
                                                        width: 62
                                                        height: 62
                                                        radius: 31
                                                        color: Colors.black
                                                        border.width: 1
                                                        border.color: Colors.orange
                                                    }

                                                    GohuText {
                                                        anchors.centerIn: parent
                                                        text: root.factoryTrigger.toUpperCase()
                                                        font.pixelSize: 9
                                                        color: Colors.orange
                                                    }
                                                }
                                            }

                                            GohuText {
                                                width: parent.width
                                                text: "DIAL BAY // TEMP CLICK"
                                                horizontalAlignment: Text.AlignHCenter
                                                font.pixelSize: 7
                                                color: Colors.white
                                                opacity: 0.65
                                            }
                                        }

                                        MouseArea {
                                            anchors.fill: parent
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: root.cycleFactoryTrigger()
                                        }
                                    }

                                    Rectangle {
                                        width: (dialBayRow.width - 16) / 3
                                        height: parent.height

                                        color: Colors.black
                                        border.width: 1
                                        border.color: Colors.cyan

                                        Column {
                                            anchors {
                                                fill: parent
                                                margins: 8
                                            }

                                            spacing: 5

                                            GohuText {
                                                width: parent.width
                                                text: "OPERATION"
                                                horizontalAlignment: Text.AlignHCenter
                                                font.pixelSize: 10
                                                color: Colors.magenta
                                            }

                                            Item {
                                                width: parent.width
                                                height: 94

                                                Rectangle {
                                                    anchors.centerIn: parent
                                                    width: 88
                                                    height: 88
                                                    radius: 44
                                                    color: Colors.dark
                                                    border.width: 2
                                                    border.color: Colors.cyan

                                                    Rectangle {
                                                        anchors.centerIn: parent
                                                        width: 62
                                                        height: 62
                                                        radius: 31
                                                        color: Colors.black
                                                        border.width: 1
                                                        border.color: Colors.orange
                                                    }

                                                    GohuText {
                                                        anchors.centerIn: parent
                                                        width: 56
                                                        text: root.factoryTemplate.toUpperCase()
                                                        horizontalAlignment: Text.AlignHCenter
                                                        wrapMode: Text.Wrap
                                                        font.pixelSize: 8
                                                        color: Colors.orange
                                                    }
                                                }
                                            }

                                            GohuText {
                                                width: parent.width
                                                text: "DIAL BAY // TEMP CLICK"
                                                horizontalAlignment: Text.AlignHCenter
                                                font.pixelSize: 7
                                                color: Colors.white
                                                opacity: 0.65
                                            }
                                        }

                                        MouseArea {
                                            anchors.fill: parent
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: root.cycleFactoryTemplate()
                                        }
                                    }

                                    Rectangle {
                                        width: (dialBayRow.width - 16) / 3
                                        height: parent.height

                                        color: Colors.black
                                        border.width: 1
                                        border.color: Colors.cyan

                                        Column {
                                            anchors {
                                                fill: parent
                                                margins: 8
                                            }

                                            spacing: 5

                                            GohuText {
                                                width: parent.width
                                                text: "TARGET"
                                                horizontalAlignment: Text.AlignHCenter
                                                font.pixelSize: 10
                                                color: Colors.magenta
                                            }

                                            Item {
                                                width: parent.width
                                                height: 94

                                                Rectangle {
                                                    anchors.centerIn: parent
                                                    width: 88
                                                    height: 88
                                                    radius: 44
                                                    color: Colors.dark
                                                    border.width: 2
                                                    border.color: Colors.cyan

                                                    Rectangle {
                                                        anchors.centerIn: parent
                                                        width: 62
                                                        height: 62
                                                        radius: 31
                                                        color: Colors.black
                                                        border.width: 1
                                                        border.color: Colors.orange
                                                    }

                                                    GohuText {
                                                        anchors.centerIn: parent
                                                        width: 56
                                                        text: "CURRENT\nREPO"
                                                        horizontalAlignment: Text.AlignHCenter
                                                        font.pixelSize: 8
                                                        color: Colors.orange
                                                    }
                                                }
                                            }

                                            GohuText {
                                                width: parent.width
                                                text: "DIAL BAY // RESERVED"
                                                horizontalAlignment: Text.AlignHCenter
                                                font.pixelSize: 7
                                                color: Colors.white
                                                opacity: 0.65
                                            }
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

                                height: 32
                                spacing: 8

                                Rectangle {
                                    width: parent.width - 312
                                    height: 30
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
                                    }
                                }

                                ActionButton {
                                    width: 148
                                    height: 30
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
                                    width: 148
                                    height: 30
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

                        // ===== SAVED MACHINES ==========================

                        Rectangle {
                            width: parent.width
                            height: 92

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
                                        width: parent.width - 328
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

                                    Rectangle {
                                        width: 104
                                        height: 30
                                        color: Colors.black
                                        border.width: 1
                                        border.color: Colors.blue

                                        GohuText {
                                            anchors.centerIn: parent
                                            text: "ASSIGN // NEXT"
                                            font.pixelSize: 8
                                            color: Colors.white
                                        }
                                    }
                                }
                            }
                        }

                        // ===== RUNS / RESULT STATE =====================

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

                        // ===== BRIDGE / FACTORY FEEDBACK ===============

                        Rectangle {
                            width: parent.width
                            height: 50

                            color: Colors.dark
                            border.width: 1
                            border.color: Colors.magenta

                            Row {
                                anchors {
                                    fill: parent
                                    margins: 9
                                }

                                spacing: 10

                                BlueLabel {
                                    width: 90
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: "PX / STATE"
                                }

                                GohuText {
                                    width: parent.width - 100
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: {
                                        if (githubService.factoryBusy)
                                            return githubService.factoryMode === "install"
                                                   ? "SAVING // VALIDATING + OPENING PR"
                                                   : "PREVIEWING // VALIDATING";

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

                                    font.pixelSize: 9
                                    color: githubService.factoryValidationStatus === "FAIL"
                                           || githubService.factoryValidationStatus === "ERROR"
                                           || githubService.lastError
                                           ? Colors.red
                                           : githubService.factoryValidationStatus === "PASS"
                                           ? Colors.orange
                                           : Colors.white
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
