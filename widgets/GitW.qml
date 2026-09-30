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

    property int panelWidth: 540
    property int panelHeight: 650
    property int panelTopMargin: 0
    property int panelLeftMargin: 600
    property int frameInset: 8
    property int glowGutter: 14
    property int topGlowGutter: 12

    // Reserve transparent pixels above the visible chassis so its top glow
    // renders inside the PanelWindow instead of being clipped by the top bar.
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

    onMenuOpenChanged: {
        if (root.menuOpen) {
            gitService.refresh();
            githubService.refresh();
        }
    }

    Component.onCompleted: {
        gitService.refresh();
    }

    GitService {
        id: gitService
    }

    GitHubService {
        id: githubService
        originUrl: gitService.origin
    }

    Timer {
        interval: 3000
        repeat: true
        running: root.menuOpen

        onTriggered: gitService.refresh()
    }

    Timer {
        interval: 15000
        repeat: true
        running: root.menuOpen

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
            ? Colors.magenta
            : Colors.blue

        opacity: enabledAction ? 1.0 : 0.35

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
            font.pixelSize: 10
            color: actionButton.contentColor

            layer.enabled: !actionButton.pressed
            layer.effect: DropShadow {
                radius: 14
                samples: 15
                opacity:
                    actionButton.hovered
                    ? 0.80
                    : actionButton.selectedAction
                    ? 0.80
                    : 0.60
                color:
                    actionButton.selectedAction
                    ? Colors.magenta
                    : actionButton.hovered
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

        // Bar-module glow recipe: crisp 3px body halo + faint 10px halo.
        RectangularShadow {
            anchors.fill: parent
            spread: 3
            z: -1
            opacity:
                actionButton.pressed
                ? 0.60
                : actionButton.hovered
                ? 0.50
                : actionButton.selectedAction
                ? 0.50
                : 0.32
            color:
                actionButton.pressed
                ? Colors.magenta
                : actionButton.hovered
                ? Colors.orange
                : actionButton.selectedAction
                ? Colors.magenta
                : Colors.blue
        }

        RectangularShadow {
            anchors.fill: parent
            spread: 10
            z: -2
            opacity:
                actionButton.pressed
                ? 0.12
                : actionButton.hovered
                ? 0.09
                : actionButton.selectedAction
                ? 0.09
                : 0.05
            color:
                actionButton.pressed
                ? Colors.magenta
                : actionButton.hovered
                ? Colors.orange
                : actionButton.selectedAction
                ? Colors.magenta
                : Colors.blue
        }
    }

    // Main chassis glow: exact AppControl / CPU++ structural recipe.
    // The surface has a transparent gutter so the outer glow is not clipped.
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
        opacity: root.menuOpen ? 0.18 : 0.0
        color: Colors.orange
    }

    RectangularShadow {
        anchors.fill: chassisGeometry
        spread: 12
        z: -21
        opacity: root.menuOpen ? 0.04 : 0.0
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

                    text: "GIT // LOCAL REPOSITORY"
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

                    text: "CONTROL SURFACE // LOCAL GIT"
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
                        opacity: gitService.available ? 0.50 : 0.30
                        color: gitService.available ? Colors.orange : Colors.red
                    }

                    GohuText {
                        anchors.centerIn: parent
                        text: gitService.refreshing ? "READING" : gitService.available ? "LOCAL LIVE" : "OFFLINE"
                        font.pixelSize: 8
                        color: gitService.available ? Colors.orange : Colors.red
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

            Rectangle {
                width: parent.width
                height: 140

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

                        MetaValue {
                            width: 365
                            text: gitService.repository
                        }
                    }

                    Row {
                        spacing: 10

                        MetaLabel {
                            width: 100
                            text: "BRANCH"
                        }

                        MetaValue {
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

                        MetaValue {
                            width: 365
                            text: gitService.head
                        }
                    }

                    Row {
                        spacing: 10

                        MetaLabel {
                            width: 100
                            text: "WORKTREE"
                        }

                        MetaValue {
                            width: 365
                            text: gitService.worktree
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
                height: 90

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

                        layer.enabled: true
                        layer.effect: DropShadow {
                            radius: 5
                            samples: 7
                            opacity: 0.10
                            color: Colors.cyan
                            transparentBorder: true
                        }

                        wrapMode: Text.WrapAnywhere
                    }
                }
            }

            Rectangle {
                width: parent.width
                height: 118

                color: Colors.dark
                border.width: 1
                border.color: Colors.cyan

                RectangularShadow {
                    anchors.fill: parent
                    spread: 3
                    z: -1
                    opacity: 0.28
                    color: Colors.cyan
                }

                Column {
                    anchors {
                        fill: parent
                        margins: 12
                    }

                    spacing: 7

                    SectionLabel {
                        text: "REMOTE // GITHUB"
                    }

                    Row {
                        spacing: 10

                        MetaLabel {
                            width: 100
                            text: "ORIGIN"
                        }

                        MetaValue {
                            width: 365
                            text: gitService.origin
                        }
                    }

                    Row {
                        spacing: 10

                        MetaLabel {
                            width: 100
                            text: "GITHUB"
                        }

                        MetaValue {
                            width: 365
                            text: githubService.refreshing
                                  ? "READING"
                                  : githubService.available
                                  ? "LIVE // " + githubService.repoSlug
                                  : githubService.lastError
                                  ? githubService.lastError
                                  : "NOT REQUESTED"
                        }
                    }

                    Row {
                        spacing: 10

                        MetaLabel {
                            width: 100
                            text: "WORKFLOWS"
                        }

                        MetaValue {
                            width: 365
                            text: githubService.available
                                  ? String(githubService.workflowCount) + " // " + githubService.latestWorkflow
                                  : "NOT CONNECTED"
                        }
                    }

                    Row {
                        spacing: 10

                        MetaLabel {
                            width: 100
                            text: "LATEST RUN"
                        }

                        MetaValue {
                            width: 365
                            text: githubService.available
                                  ? githubService.latestRunStatus
                                    + (githubService.latestRunConclusion ? " // " + githubService.latestRunConclusion : "")
                                    + (githubService.latestRunBranch ? " // " + githubService.latestRunBranch : "")
                                  : "NOT CONNECTED"
                        }
                    }
                }
            }

            Row {
                width: parent.width
                spacing: 10

                ActionButton { label: "FETCH" }
                ActionButton { label: "PULL" }
                ActionButton { label: "PUSH" }

                ActionButton {
                    label: "GH REFRESH"
                    enabledAction: !githubService.refreshing
                    selectedAction: githubService.refreshing
                    onTriggered: githubService.refresh()
                }
            }

            GohuText {
                width: parent.width
                text: gitService.lastError
                      ? "LOCAL ERROR // " + gitService.lastError
                      : githubService.lastError
                      ? "GITHUB // " + githubService.lastError
                      : "LOCAL + GITHUB READERS ACTIVE // REMOTE WRITES LOCKED"
                horizontalAlignment: Text.AlignRight
                font.pixelSize: 8
                color: Colors.orange

                layer.enabled: true
                layer.effect: DropShadow {
                    radius: 8
                    samples: 7
                    opacity: 0.56
                    color: Colors.orange
                    transparentBorder: true
                }
            }
        }

    }
}
