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

    implicitWidth: panelWidth
    implicitHeight: panelHeight

    anchors {
        top: true
        bottom: false
        left: true
        right: false
    }

    margins {
        top: panelTopMargin
        left: panelLeftMargin
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
        color: Colors.orange
    }

    component MetaLabel: GohuText {
        font.pixelSize: 10
        color: Colors.cyan
    }

    component MetaValue: GohuText {
        font.pixelSize: 11
        color: Colors.white
        elide: Text.ElideRight
    }

    component ActionButton: Rectangle {
        id: actionButton

        property string label: ""
        property bool enabledAction: false

        signal triggered()

        readonly property bool hovered: actionMouse.containsMouse
        readonly property bool pressed: actionMouse.pressed

        width: 112
        height: 36

        color: pressed ? Colors.magenta : hovered && enabledAction ? Colors.yellow : Colors.dark
        border.width: 1
        border.color: enabledAction ? (pressed ? Colors.magenta : hovered ? Colors.yellow : Colors.orange) : Colors.cyan
        opacity: enabledAction ? 1.0 : 0.35

        GohuText {
            anchors.centerIn: parent
            text: actionButton.label
            font.pixelSize: 10
            color: actionButton.enabledAction
                   ? (actionButton.pressed ? Colors.black : Colors.orange)
                   : Colors.cyan
        }

        MouseArea {
            id: actionMouse
            anchors.fill: parent
            hoverEnabled: true
            enabled: actionButton.enabledAction

            onClicked: actionButton.triggered()
        }
    }

    // Background halo. Inset slightly so the drop shadow has room to
    // render inside the always-mapped PanelWindow surface.
    Rectangle {
        id: backgroundGlowSource

        anchors.fill: parent
        anchors.margins: 8

        color: Colors.black
        opacity: root.menuOpen ? 0.92 : 0.0

        z: -4
    }

    DropShadow {
        anchors.fill: backgroundGlowSource
        source: backgroundGlowSource

        horizontalOffset: 0
        verticalOffset: 3

        radius: 30
        samples: 31

        color: Colors.orange
        opacity: root.menuOpen ? 0.42 : 0.0

        z: -5

        transparentBorder: true
    }

    // Active outer frame glow. Kept inside the surface bounds so the
    // menu can remain flush with the top edge.
    Rectangle {
        id: frameGlowSource

        anchors.fill: parent

        color: "transparent"
        border.width: 2
        border.color: Colors.orange

        opacity: root.menuOpen ? 1.0 : 0.0

        z: 2
    }

    DropShadow {
        anchors.fill: frameGlowSource
        source: frameGlowSource

        horizontalOffset: 0
        verticalOffset: 0

        radius: 18
        samples: 23

        color: Colors.orange
        opacity: root.menuOpen ? 0.76 : 0.0

        z: 3

        transparentBorder: true
    }

    Rectangle {
        id: frame
        anchors.fill: parent

        color: Colors.black
        opacity: root.menuOpen ? 0.97 : 0.0

        border.width: 2
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
                    color: Colors.orange
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
                color: Colors.orange
            }

            Rectangle {
                width: parent.width
                height: 140

                color: Colors.dark
                border.width: 1
                border.color: Colors.orange

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
                    onTriggered: gitService.runReadAction("status")
                }

                ActionButton {
                    label: "DIFF"
                    enabledAction: !gitService.actionBusy
                    onTriggered: gitService.runReadAction("diff")
                }

                ActionButton {
                    label: "LOG"
                    enabledAction: !gitService.actionBusy
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
                    }
                }
            }

            Rectangle {
                width: parent.width
                height: 118

                color: Colors.dark
                border.width: 1
                border.color: Colors.cyan

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
            }
        }

    }
}
