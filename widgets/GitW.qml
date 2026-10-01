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

    property int panelWidth: 540
    property int panelHeight: 650
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
                : 0.28
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
                : 0.04
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

    component PageTab: Rectangle {
        id: pageTab

        property string label: ""
        property bool selected: false

        signal triggered()

        height: 36
        color: selected
               ? Colors.yellow
               : tabMouse.containsMouse
               ? Colors.dark
               : Colors.black

        border.width: 1
        border.color: selected
                      ? Colors.magenta
                      : tabMouse.containsMouse
                      ? Colors.orange
                      : Colors.blue

        GohuText {
            anchors.centerIn: parent
            text: pageTab.label
            font.pixelSize: 10
            color: pageTab.selected
                   ? Colors.magenta
                   : tabMouse.containsMouse
                   ? Colors.orange
                   : Colors.white

            layer.enabled: true
            layer.effect: DropShadow {
                radius: pageTab.selected ? 12 : 7
                samples: 13
                opacity: pageTab.selected ? 0.74 : 0.38
                color: pageTab.selected ? Colors.magenta : Colors.cyan
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
            spread: selected ? 5 : 3
            z: -1
            opacity: selected ? 0.42 : tabMouse.containsMouse ? 0.28 : 0.12
            color: selected ? Colors.magenta : tabMouse.containsMouse ? Colors.orange : Colors.blue
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
                                    spacing: 10

                                    MetaLabel {
                                        width: 100
                                        text: "WORKTREE"
                                    }

                                    Row {
                                        width: 365
                                        spacing: 0

                                        MetaValue {
                                            visible: String(gitService.worktree).indexOf("DIRTY") !== 0
                                            text: gitService.worktree
                                        }

                                        MetaValue {
                                            visible: String(gitService.worktree).indexOf("DIRTY") === 0
                                            text: "DIRTY • "
                                        }

                                        OrangeValue {
                                            visible: String(gitService.worktree).indexOf("DIRTY") === 0
                                            text: {
                                                const match = String(gitService.worktree).match(/(\d+)\s+CHANGES/);
                                                return match ? match[1] : "";
                                            }
                                        }

                                        MetaValue {
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

                                    OrangeLabel {
                                        width: 100
                                        text: "ORIGIN"
                                    }

                                    CyanValue {
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
                        spacing: 12

                        Rectangle {
                            width: parent.width
                            height: 154

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
                                    text: "REMOTE // GITHUB"
                                }

                                Row {
                                    spacing: 10

                                    OrangeLabel {
                                        width: 100
                                        text: "REPOSITORY"
                                    }

                                    CyanValue {
                                        width: 365
                                        text: githubService.repoSlug || "NOT CONNECTED"
                                    }
                                }

                                Row {
                                    spacing: 10

                                    MetaLabel {
                                        width: 100
                                        text: "CONNECTION"
                                    }

                                    OrangeValue {
                                        width: 365
                                        text: githubService.refreshing
                                              ? "READING"
                                              : githubService.available
                                              ? "LIVE // PX"
                                              : githubService.lastError || "NOT REQUESTED"
                                    }
                                }

                                Row {
                                    spacing: 10

                                    MetaLabel {
                                        width: 100
                                        text: "WORKFLOWS"
                                    }

                                    Row {
                                        width: 365
                                        spacing: 0

                                        OrangeValue {
                                            visible: githubService.available && githubService.workflowCount > 0
                                            text: String(githubService.workflowCount)
                                        }

                                        DimValue {
                                            visible: githubService.available && githubService.workflowCount === 0
                                            text: "0"
                                        }

                                        MetaValue {
                                            visible: githubService.available
                                            text: " // " + githubService.latestWorkflow
                                        }

                                        MetaValue {
                                            visible: !githubService.available
                                            text: "NOT CONNECTED"
                                        }
                                    }
                                }

                                Row {
                                    spacing: 10

                                    MetaLabel {
                                        width: 100
                                        text: "LATEST RUN"
                                    }

                                    Row {
                                        width: 365
                                        spacing: 0

                                        OrangeValue {
                                            visible: githubService.available && githubService.runCount > 0
                                            text: String(githubService.runCount)
                                        }

                                        DimValue {
                                            visible: githubService.available && githubService.runCount === 0
                                            text: "0"
                                        }

                                        MetaValue {
                                            visible: githubService.available
                                            text: " // " + githubService.latestRunStatus
                                                  + (githubService.latestRunConclusion ? " // " + githubService.latestRunConclusion : "")
                                                  + (githubService.latestRunBranch ? " // " + githubService.latestRunBranch : "")
                                        }

                                        MetaValue {
                                            visible: !githubService.available
                                            text: "NOT CONNECTED"
                                        }
                                    }
                                }
                            }
                        }

                        SectionLabel {
                            text: "PX CONTROL"
                        }

                        Row {
                            width: parent.width
                            spacing: 10

                            ActionButton {
                                label: "REFRESH"
                                enabledAction: !githubService.refreshing
                                onTriggered: githubService.refresh()
                            }

                            ActionButton {
                                label: "RUN"
                                enabledAction: false
                            }

                            ActionButton {
                                label: "RERUN"
                                enabledAction: false
                            }

                            ActionButton {
                                label: "CANCEL"
                                enabledAction: false
                            }
                        }

                        Rectangle {
                            width: parent.width
                            height: 206

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

                            Column {
                                anchors {
                                    fill: parent
                                    margins: 12
                                }

                                spacing: 10

                                SectionLabel {
                                    text: "WORKFLOW FACTORY"
                                }

                                Row {
                                    spacing: 10

                                    MetaLabel {
                                        width: 100
                                        text: "BACKEND"
                                    }

                                    OrangeValue {
                                        width: 365
                                        text: githubService.available ? "PX ONLINE" : "WAITING FOR PX"
                                    }
                                }

                                Row {
                                    spacing: 10

                                    MetaLabel {
                                        width: 100
                                        text: "CREATE"
                                    }

                                    MetaValue {
                                        width: 365
                                        text: "TEMPLATE → TRIGGER → NAME → PREVIEW → INSTALL"
                                    }
                                }

                                Row {
                                    spacing: 10

                                    MetaLabel {
                                        width: 100
                                        text: "VALIDATION"
                                    }

                                    CyanValue {
                                        width: 365
                                        text: "ACTIONLINT CONTRACT READY"
                                    }
                                }

                                Rectangle {
                                    width: parent.width
                                    height: 1
                                    color: Colors.blue
                                    opacity: 0.65
                                }

                                GohuText {
                                    width: parent.width
                                    text: "PAGE SPLIT COMPLETE // CREATOR + RUN SELECTORS NEXT"
                                    font.pixelSize: 9
                                    color: Colors.white
                                    opacity: 0.72
                                    wrapMode: Text.Wrap
                                }
                            }
                        }

                        GohuText {
                            width: parent.width
                            text: githubService.lastError
                                  ? "PX / GITHUB // " + githubService.lastError
                                  : githubService.available
                                  ? "PX BRIDGE ACTIVE // REMOTE WRITES STILL LOCKED"
                                  : "PX BRIDGE WAITING"
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
        }
    }
}
