import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.components
import "../services/git"
import "../services/hospital"
import "../services/github"
import QtQuick.Effects
import Qt5Compat.GraphicalEffects

PanelWindow {
    id: root

    property bool menuOpen: false
    property string selectedCommitSha: ""
    property string selectedRoomTeam: ""
    readonly property var selectedRoomData:
        auditService.roomFor(selectedRoomTeam)

    function toggleCommitSelection(sha) {
        const candidate = String(sha || "");
        selectedCommitSha = selectedCommitSha === candidate ? "" : candidate;
    }

    function toggleRoomSelection(team) {
        const candidate = String(team || "");
        selectedRoomTeam = selectedRoomTeam === candidate ? "" : candidate;
    }

    onSelectedRoomTeamChanged: {
        roomService.clearResult();
        certificationCoordinator.bindRoom(roomService);
    }

    property int panelWidth: 700
    property int panelHeight: 1320
    property int panelTopMargin: 0
    property int panelLeftMargin: 50
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

    // Keep the real surface mapped. Closed state is invisible + click-through.
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
            hospitalGitService.refresh();
            patientService.refresh();
        }
    }

    Component.onCompleted: {
        certificationCoordinator.bindRoom(roomService);
        hospitalGitService.refresh();
        patientService.refresh();
    }

    GitService {
        id: hospitalGitService
    }

    GitService {
        id: hospitalEvidenceGitService
        repoPath: patientService.repoRoot
        repoLabel: "HOSPITAL PATIENT"
    }

    HospitalService {
        id: patientService
    }

    GitHubService {
        id: githubService
        originUrl: patientService.origin
    }

    HospitalAuditService {
        id: auditService
        repository: githubService.repoSlug
    }

    HospitalRoomService {
        id: roomService
        repository: githubService.repoSlug
        team: root.selectedRoomTeam
        localRepoPath: patientService.repoRoot
    }

    GitEvidenceProvider {
        id: gitEvidenceProvider
        gitService: hospitalEvidenceGitService
        githubService: githubService
    }

    HospitalCertificationCoordinator {
        id: certificationCoordinator
        evidenceProvider: gitEvidenceProvider
    }

    Connections {
        target: patientService

        function onRefreshed() {
            githubService.refresh();
            auditService.runAudit();
        }
    }

    Connections {
        target: roomService

        function onPostOpFinished() {
            patientService.refresh();
            githubService.refresh();
            auditService.runAudit();
        }
    }

    Timer {
        interval: 3000
        repeat: true
        running: root.menuOpen

        onTriggered: hospitalGitService.refresh()
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

    component RoomRow: Rectangle {
        id: roomRow

        property string team: ""
        property string responsibility: ""
        property string stateText: auditService.roomLabel(roomRow.team)
        readonly property string telemetryState:
            auditService.roomState(roomRow.team)
        readonly property color stateColor:
            telemetryState === "MISSING"
            ? Colors.red
            : telemetryState === "IN_MAIN"
              || telemetryState === "AT_MAIN"
            ? Colors.orange
            : telemetryState === "DIVERGED"
            ? Colors.magenta
            : Colors.cyan

        readonly property bool selected:
            root.selectedRoomTeam === roomRow.team

        width: roomsColumn.width
        height: 54

        color: Colors.dark
        border.width: selected ? 2 : 1
        border.color: selected ? Colors.orange : Colors.magenta

        RectangularShadow {
            anchors.fill: parent
            spread: selected ? 5 : 3
            z: -1
            opacity: selected ? 0.42 : 0.28
            color: selected ? Colors.orange : Colors.magenta
        }

        GohuText {
            anchors {
                left: parent.left
                right: roomStateText.left
                top: parent.top
                leftMargin: 12
                rightMargin: 10
                topMargin: 7
            }

            text: roomRow.team
            font.pixelSize: 13
            color: Colors.orange
            elide: Text.ElideRight

            layer.enabled: true
            layer.effect: DropShadow {
                radius: 5
                samples: 7
                opacity: 0.34
                color: Colors.orange
                transparentBorder: true
            }
        }

        GohuText {
            anchors {
                left: parent.left
                right: roomStateText.left
                bottom: parent.bottom
                leftMargin: 12
                rightMargin: 10
                bottomMargin: 7
            }

            text: roomRow.responsibility
            font.pixelSize: 9
            color: Colors.cyan
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

        GohuText {
            id: roomStateText

            anchors {
                right: parent.right
                verticalCenter: parent.verticalCenter
                rightMargin: 10
            }

            width: 105
            horizontalAlignment: Text.AlignRight
            text: roomRow.stateText
            font.pixelSize: 9
            color: roomRow.stateColor
            opacity: roomRow.telemetryState === "WAITING" ? 0.58 : 1.0

            layer.enabled: true
            layer.effect: DropShadow {
                radius: 5
                samples: 7
                opacity: roomRow.telemetryState === "WAITING" ? 0.14 : 0.38
                color: roomRow.stateColor
                transparentBorder: true
            }
        }

        MouseArea {
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor

            onClicked: root.toggleRoomSelection(roomRow.team)
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
        opacity: root.menuOpen ? 0.21 : 0.0
        color: Colors.magenta
    }

    RectangularShadow {
        anchors.fill: chassisGeometry
        spread: 12
        z: -21
        opacity: root.menuOpen ? 0.05 : 0.0
        color: Colors.magenta
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
        border.color: Colors.magenta

        Rectangle {
            id: innerFrame

            anchors.fill: parent
            anchors.margins: root.frameInset

            color: "transparent"
            border.width: 1
            border.color: Colors.cyan
            opacity: 0.70
        }

        Rectangle {
            id: bottomStop

            height: 2
            anchors {
                left: parent.left
                right: parent.right
                bottom: parent.bottom
                leftMargin: root.frameInset
                rightMargin: root.frameInset
                bottomMargin: root.frameInset
            }

            color: Colors.cyan
            opacity: 1.0

            RectangularShadow {
                anchors.fill: parent
                spread: 3
                z: -1
                opacity: 0.34
                color: Colors.cyan
            }
        }

        // Fixed diagnostic/header zone. Nothing above OPERATING ROOMS scrolls.
        Column {
            id: fixedTop

            anchors {
                top: parent.top
                left: parent.left
                right: parent.right
                topMargin: 18
                leftMargin: 18
                rightMargin: 18
            }

            spacing: 12

            // ===== HEADER =======================================

            Item {
                width: parent.width
                height: 56

                GohuText {
                    anchors {
                        left: parent.left
                        top: parent.top
                    }

                    text: "HOSPITAL // SURGERY ROOM"
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

                    text: "CONTROL SURFACE // LOCAL PATIENT"
                    font.pixelSize: 10
                    color: Colors.cyan

                    layer.enabled: true
                    layer.effect: DropShadow {
                        radius: 6
                        samples: 7
                        opacity: 0.40
                        color: Colors.cyan
                        transparentBorder: true
                    }
                }

                Rectangle {
                    anchors {
                        right: parent.right
                        verticalCenter: parent.verticalCenter
                    }

                    width: 86
                    height: 26

                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.magenta

                    RectangularShadow {
                        anchors.fill: parent
                        spread: 3
                        z: -1
                        opacity: 0.38
                        color: Colors.magenta
                    }

                    GohuText {
                        id: hospitalLocalStatusText

                        anchors.centerIn: parent
                        text: hospitalGitService.refreshing
                              ? "READING"
                              : hospitalGitService.available
                              ? "LOCAL LIVE"
                              : "OFFLINE"
                        font.pixelSize: 9
                        color: hospitalGitService.available ? Colors.magenta : Colors.red

                        layer.enabled: true
                        layer.effect: DropShadow {
                            radius: 10
                            samples: 11
                            opacity: hospitalGitService.available ? 0.82 : 0.44
                            color: hospitalLocalStatusText.color
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

            // ===== PATIENT TOPOLOGY =============================

            BranchMap {
                id: topologyFrame

                width: parent.width
                height: 190

                topologyService: patientService
                titleText: "PATIENT TOPOLOGY"
                selectedSha: root.selectedCommitSha

                onCommitSelected: function(sha) {
                    root.toggleCommitSelection(sha);
                }
            }

            // ===== PATIENT ======================================

            Row {
                id: patientRoomRow

                width: parent.width
                height: 328
                spacing: 10

                Rectangle {
                    id: patientPane

                    width: (parent.width - parent.spacing) / 2
                    height: parent.height

                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.magenta

                    RectangularShadow {
                        anchors.fill: parent
                        spread: 4
                        z: -1
                        opacity: 0.22
                        color: Colors.magenta
                    }

                    Column {
                        anchors {
                            fill: parent
                            margins: 12
                        }

                        spacing: 8

                        SectionLabel {
                            text: "PATIENT"
                        }

                        Row {
                            spacing: 8

                            MetaLabel {
                                width: 76
                                text: "REPOSITORY"
                            }

                            MetaValue {
                                width: patientPane.width - 108
                                text: patientService.repository
                                color: Colors.orange
                                elide: Text.ElideRight

                                layer.effect: DropShadow {
                                    radius: 5
                                    samples: 7
                                    opacity: 0.28
                                    color: Colors.orange
                                    transparentBorder: true
                                }
                            }
                        }

                        Row {
                            spacing: 8

                            OrangeLabel {
                                width: 76
                                text: "BRANCH"
                            }

                            CyanValue {
                                width: patientPane.width - 108
                                text: patientService.branch
                                elide: Text.ElideRight
                            }
                        }

                        Row {
                            spacing: 8

                            MetaLabel {
                                width: 76
                                text: "HEAD"
                            }

                            BlueValue {
                                width: patientPane.width - 108
                                text: patientService.head
                                elide: Text.ElideRight
                            }
                        }

                        Row {
                            spacing: 8

                            MetaLabel {
                                width: 76
                                text: "WORKTREE"
                            }

                            GohuText {
                                id: worktreeValue

                                readonly property bool cleanState:
                                    String(patientService.worktree || "")
                                        .trim()
                                        .toUpperCase() === "CLEAN"

                                width: patientPane.width - 108
                                text: patientService.worktree
                                font.pixelSize: 10
                                elide: Text.ElideRight
                                color: cleanState ? Colors.orange : Colors.white

                                layer.enabled: true
                                layer.effect: DropShadow {
                                    radius: worktreeValue.cleanState ? 9 : 7
                                    samples: worktreeValue.cleanState ? 13 : 9
                                    opacity: worktreeValue.cleanState ? 0.76 : 0.34
                                    color: worktreeValue.cleanState ? Colors.orange : Colors.cyan
                                    transparentBorder: true
                                }
                            }
                        }
                    }
                }

                Rectangle {
                    id: roomPane

                    width: (parent.width - parent.spacing) / 2
                    height: parent.height

                    color: Colors.dark
                    border.width: 1
                    border.color:
                        root.selectedRoomTeam.length > 0
                        ? Colors.orange
                        : Colors.magenta

                    RectangularShadow {
                        anchors.fill: parent
                        spread: 4
                        z: -1
                        opacity:
                            root.selectedRoomTeam.length > 0
                            ? 0.30
                            : 0.18
                        color:
                            root.selectedRoomTeam.length > 0
                            ? Colors.orange
                            : Colors.magenta
                    }

                    Column {
                        anchors {
                            fill: parent
                            margins: 12
                        }

                        spacing: 8

                        SectionLabel {
                            width: parent.width
                            text:
                                root.selectedRoomTeam.length > 0
                                ? "ROOM // " + root.selectedRoomTeam
                                : "ROOM // NONE SELECTED"
                            elide: Text.ElideRight
                        }

                        GohuText {
                            width: parent.width
                            text: {
                                const room = root.selectedRoomData || {};
                                return String(
                                    room.responsibility
                                    || "SELECT AN OPERATING ROOM"
                                );
                            }
                            font.pixelSize: 10
                            color: Colors.orange
                            elide: Text.ElideRight
                        }

                        Row {
                            spacing: 8

                            MetaLabel {
                                width: 66
                                text: "BRANCH"
                            }

                            CyanValue {
                                width: roomPane.width - 98
                                text: {
                                    const room = root.selectedRoomData || {};
                                    return String(room.branch || "NO DATA");
                                }
                                elide: Text.ElideRight
                            }
                        }

                        Row {
                            spacing: 8

                            MetaLabel {
                                width: 66
                                text: "HEAD"
                            }

                            BlueValue {
                                width: roomPane.width - 98
                                text: {
                                    const room = root.selectedRoomData || {};
                                    const head = String(room.head || "");
                                    return head ? head.slice(0, 12) : "NO DATA";
                                }
                                elide: Text.ElideRight
                            }
                        }

                        Row {
                            spacing: 8

                            MetaLabel {
                                width: 66
                                text: "RELATION"
                            }

                            GohuText {
                                width: roomPane.width - 98
                                text: {
                                    const room = root.selectedRoomData || {};

                                    if (!root.selectedRoomTeam.length)
                                        return "WAITING";

                                    const state =
                                        String(room.state || "WAITING");
                                    const ahead = Number(room.ahead || 0);
                                    const behind = Number(room.behind || 0);

                                    return state
                                           + " // +" + ahead
                                           + " / -" + behind;
                                }
                                font.pixelSize: 10
                                color: Colors.magenta
                                elide: Text.ElideRight
                            }
                        }

                        Row {
                            spacing: 8

                            MetaLabel {
                                width: 66
                                text: "TOUCHED"
                            }

                            MetaValue {
                                width: roomPane.width - 98
                                text: {
                                    const room = root.selectedRoomData || {};
                                    return String(
                                        room.updated_at
                                        || "NO DATA"
                                    );
                                }
                                elide: Text.ElideRight
                            }
                        }


                        Row {
                            id: roomInspectActions

                            width: parent.width
                            height: 24
                            spacing: 6

                            Repeater {
                                model: ["STATUS", "DIFF", "LOG"]

                                Rectangle {
                                    id: roomInspectButton

                                    required property string modelData
                                    readonly property bool selectedAction:
                                        roomService.action === modelData
                                    readonly property bool enabledAction:
                                        root.selectedRoomTeam.length > 0
                                        && !roomService.running
                                        && !roomService.rehearsing
                                        && !roomService.integrating
                                        && !roomService.postOpRunning
                                        && !roomService.armed

                                    width:
                                        (
                                            roomInspectActions.width
                                            - roomInspectActions.spacing * 2
                                        ) / 3
                                    height: parent.height

                                    color:
                                        roomInspectMouse.pressed
                                        ? Colors.orange
                                        : selectedAction
                                        ? Colors.magenta
                                        : Colors.black
                                    border.width: 1
                                    border.color:
                                        roomInspectMouse.containsMouse
                                        ? Colors.orange
                                        : selectedAction
                                        ? Colors.magenta
                                        : Colors.cyan
                                    opacity: enabledAction ? 1.0 : 0.48

                                    GohuText {
                                        anchors.centerIn: parent
                                        text:
                                            roomService.running
                                            && roomService.action
                                               === roomInspectButton.modelData
                                            ? "READING"
                                            : roomInspectButton.modelData
                                        font.pixelSize: 9
                                        color:
                                            roomInspectMouse.pressed
                                            ? Colors.black
                                            : Colors.cyan
                                    }

                                    MouseArea {
                                        id: roomInspectMouse

                                        anchors.fill: parent
                                        hoverEnabled: true
                                        enabled: roomInspectButton.enabledAction
                                        cursorShape:
                                            enabled
                                            ? Qt.PointingHandCursor
                                            : Qt.ArrowCursor

                                        onClicked:
                                            roomService.runInspection(
                                                roomInspectButton.modelData
                                                    .toLowerCase()
                                            )
                                    }
                                }
                            }
                        }

                        Row {
                            id: roomOperationActions

                            width: parent.width
                            height: 24
                            spacing: 6

                            Repeater {
                                model: ["REFRESH", "LAZYGIT", "PREPARE"]

                                Rectangle {
                                    id: roomOperationButton

                                    required property string modelData
                                    readonly property bool enabledAction:
                                        root.selectedRoomTeam.length > 0
                                        && !roomService.running
                                        && !roomService.rehearsing
                                        && !roomService.integrating
                                        && !roomService.postOpRunning
                                        && !roomService.armed

                                    width:
                                        (
                                            roomOperationActions.width
                                            - roomOperationActions.spacing * 2
                                        ) / 3
                                    height: parent.height

                                    color:
                                        roomOperationMouse.pressed
                                        ? Colors.orange
                                        : roomService.action === modelData
                                        ? Colors.magenta
                                        : Colors.black
                                    border.width: 1
                                    border.color:
                                        roomOperationMouse.containsMouse
                                        ? Colors.orange
                                        : modelData === "PREPARE"
                                          && roomService.action === "PREPARE"
                                        ? Colors.magenta
                                        : Colors.cyan
                                    opacity: enabledAction ? 1.0 : 0.48

                                    GohuText {
                                        anchors.centerIn: parent
                                        text:
                                            roomService.running
                                            && roomService.action
                                               === roomOperationButton.modelData
                                            ? "READING"
                                            : roomOperationButton.modelData
                                        font.pixelSize: 8
                                        color:
                                            roomOperationMouse.pressed
                                            ? Colors.black
                                            : Colors.cyan
                                    }

                                    MouseArea {
                                        id: roomOperationMouse

                                        anchors.fill: parent
                                        hoverEnabled: true
                                        enabled: roomOperationButton.enabledAction
                                        cursorShape:
                                            enabled
                                            ? Qt.PointingHandCursor
                                            : Qt.ArrowCursor

                                        onClicked: {
                                            if (roomOperationButton.modelData
                                                    === "REFRESH") {
                                                patientService.refresh();
                                                auditService.runAudit();
                                                roomService.runInspection(
                                                    "status"
                                                );
                                                return;
                                            }

                                            if (roomOperationButton.modelData
                                                    === "LAZYGIT") {
                                                roomService.launchLazygit();
                                                return;
                                            }

                                            certificationCoordinator.prepare();
                                        }
                                    }
                                }
                            }
                        }

                        Rectangle {
                            id: rehearseButton

                            readonly property bool enabledAction:
                                roomService.canRehearse
                                && !roomService.running
                                && !roomService.rehearsing
                                && !roomService.integrating
                                && !roomService.postOpRunning
                                && !roomService.armed

                            width: parent.width
                            height: 24

                            color:
                                rehearseMouse.pressed
                                ? Colors.orange
                                : roomService.rehearsing
                                ? Colors.magenta
                                : Colors.black
                            border.width:
                                roomService.rehearsalStatus.length > 0
                                ? 2 : 1
                            border.color:
                                roomService.rehearsalStatus === "CONFLICTS"
                                ? Colors.red
                                : roomService.rehearsalStatus === "CLEAN_MERGE"
                                ? Colors.orange
                                : rehearseMouse.containsMouse
                                ? Colors.orange
                                : Colors.cyan
                            opacity:
                                enabledAction
                                || roomService.rehearsing
                                || roomService.rehearsalStatus.length > 0
                                ? 1.0 : 0.42

                            RectangularShadow {
                                anchors.fill: parent
                                spread:
                                    roomService.rehearsalStatus.length > 0
                                    ? 4 : 2
                                z: -1
                                opacity:
                                    roomService.rehearsalStatus.length > 0
                                    ? 0.34 : 0.12
                                color:
                                    roomService.rehearsalStatus === "CONFLICTS"
                                    ? Colors.red
                                    : roomService.rehearsalStatus === "CLEAN_MERGE"
                                    ? Colors.orange
                                    : Colors.cyan
                            }

                            GohuText {
                                anchors.centerIn: parent
                                text:
                                    roomService.rehearsing
                                    ? "REHEARSING // ISOLATED"
                                    : roomService.rehearsalStatus === "CONFLICTS"
                                    ? "REHEARSE // CONFLICTS"
                                    : roomService.rehearsalStatus === "CLEAN_MERGE"
                                    ? "REHEARSE // CLEAN MERGE"
                                    : "REHEARSE MERGE"
                                font.pixelSize: 9
                                color:
                                    rehearseMouse.pressed
                                    ? Colors.black
                                    : roomService.rehearsalStatus === "CONFLICTS"
                                    ? Colors.red
                                    : roomService.rehearsalStatus === "CLEAN_MERGE"
                                    ? Colors.orange
                                    : Colors.cyan
                            }

                            MouseArea {
                                id: rehearseMouse

                                anchors.fill: parent
                                hoverEnabled: true
                                enabled: rehearseButton.enabledAction
                                cursorShape:
                                    enabled
                                    ? Qt.PointingHandCursor
                                    : Qt.ArrowCursor

                                onClicked: certificationCoordinator.rehearse()
                            }
                        }

                        Row {
                            id: integrationGateActions

                            width: parent.width
                            height: 24
                            spacing: 6

                            Rectangle {
                                id: armButton

                                readonly property string gateState:
                                    certificationCoordinator.state
                                readonly property bool rehearsalReady:
                                    roomService.integrationMode !== "DIVERGED"
                                    || roomService.rehearsalStatus === "CLEAN_MERGE"
                                readonly property bool enabledAction:
                                    !roomService.running
                                    && !roomService.rehearsing
                                    && !roomService.integrating
                                    && !roomService.postOpRunning
                                    && (
                                        (
                                            gateState === "CANDIDATE"
                                            && rehearsalReady
                                            && certificationCoordinator.canRequestVerification
                                        )
                                        || (
                                            gateState === "VERIFIED"
                                            && certificationCoordinator.canCertify
                                        )
                                        || (
                                            gateState === "CERTIFIED"
                                            && certificationCoordinator.canArm
                                        )
                                    )

                                width:
                                    (
                                        integrationGateActions.width
                                        - integrationGateActions.spacing
                                    ) / 2
                                height: parent.height

                                color:
                                    armMouse.pressed
                                    ? Colors.orange
                                    : roomService.armed
                                    ? Colors.orange
                                    : gateState === "VERIFIED"
                                      || gateState === "CERTIFIED"
                                    ? Colors.magenta
                                    : Colors.black
                                border.width:
                                    roomService.armed
                                    || gateState === "VERIFIED"
                                    || gateState === "CERTIFIED"
                                    ? 2 : 1
                                border.color:
                                    roomService.armed
                                    ? Colors.orange
                                    : gateState === "VERIFIED"
                                      || gateState === "CERTIFIED"
                                    ? Colors.magenta
                                    : armMouse.containsMouse
                                    ? Colors.orange
                                    : Colors.cyan
                                opacity:
                                    enabledAction
                                    || roomService.armed
                                    || gateState === "VERIFIED"
                                    || gateState === "CERTIFIED"
                                    ? 1.0 : 0.42

                                RectangularShadow {
                                    anchors.fill: parent
                                    spread:
                                        roomService.armed
                                        || armButton.gateState === "VERIFIED"
                                        || armButton.gateState === "CERTIFIED"
                                        ? 4 : 2
                                    z: -1
                                    opacity:
                                        roomService.armed
                                        || armButton.gateState === "VERIFIED"
                                        || armButton.gateState === "CERTIFIED"
                                        ? 0.38 : 0.14
                                    color:
                                        roomService.armed
                                        ? Colors.orange
                                        : armButton.gateState === "VERIFIED"
                                          || armButton.gateState === "CERTIFIED"
                                        ? Colors.magenta
                                        : Colors.cyan
                                }

                                GohuText {
                                    anchors.centerIn: parent
                                    text:
                                        roomService.armed
                                        ? (
                                            roomService.armedMode === "MERGE"
                                            ? "MERGE ARMED"
                                            : "ARMED"
                                          )
                                        : armButton.gateState === "CANDIDATE"
                                        ? (
                                            gitEvidenceProvider.requestBusy
                                            ? "VERIFYING"
                                            : "VERIFY"
                                          )
                                        : armButton.gateState === "VERIFIED"
                                        ? "CERTIFY"
                                        : armButton.gateState === "CERTIFIED"
                                        ? (
                                            roomService.canArmMerge
                                            ? "ARM MERGE"
                                            : "ARM"
                                          )
                                        : "ARM"
                                    font.pixelSize: 9
                                    color:
                                        roomService.armed
                                        ? Colors.black
                                        : armButton.gateState === "VERIFIED"
                                          || armButton.gateState === "CERTIFIED"
                                        ? Colors.magenta
                                        : Colors.cyan
                                }

                                MouseArea {
                                    id: armMouse

                                    anchors.fill: parent
                                    hoverEnabled: true
                                    enabled:
                                        armButton.enabledAction
                                        && !roomService.armed
                                    cursorShape:
                                        enabled
                                        ? Qt.PointingHandCursor
                                        : Qt.ArrowCursor

                                    onClicked: {
                                        if (armButton.gateState === "CANDIDATE") {
                                            certificationCoordinator.requestVerification("");
                                            return;
                                        }

                                        if (armButton.gateState === "VERIFIED") {
                                            certificationCoordinator.certify();
                                            return;
                                        }

                                        if (armButton.gateState === "CERTIFIED")
                                            certificationCoordinator.arm();
                                    }
                                }
                            }

                            Rectangle {
                                id: integrateButton

                                readonly property bool enabledAction:
                                    roomService.armed
                                    && certificationCoordinator.canIntegrate
                                    && !roomService.running
                                    && !roomService.rehearsing
                                    && !roomService.integrating
                                    && !roomService.postOpRunning

                                width:
                                    (
                                        integrationGateActions.width
                                        - integrationGateActions.spacing
                                    ) / 2
                                height: parent.height

                                color:
                                    integrateMouse.pressed
                                    ? Colors.orange
                                    : roomService.integrating
                                    ? Colors.magenta
                                    : Colors.black
                                border.width: roomService.armed ? 2 : 1
                                border.color:
                                    roomService.armed
                                    ? Colors.red
                                    : Colors.cyan
                                opacity: enabledAction
                                         || roomService.integrating
                                         ? 1.0 : 0.42

                                RectangularShadow {
                                    anchors.fill: parent
                                    spread: roomService.armed ? 4 : 2
                                    z: -1
                                    opacity: roomService.armed ? 0.34 : 0.12
                                    color:
                                        roomService.armed
                                        ? Colors.red
                                        : Colors.cyan
                                }

                                GohuText {
                                    anchors.centerIn: parent
                                    text:
                                        roomService.postOpRunning
                                        ? "POST-OP"
                                        : roomService.integrating
                                        ? "VERIFYING"
                                        : roomService.armedMode === "MERGE"
                                        ? "MERGE"
                                        : "INTEGRATE"
                                    font.pixelSize: 9
                                    color:
                                        integrateMouse.pressed
                                        ? Colors.black
                                        : roomService.armed
                                        ? Colors.red
                                        : Colors.cyan
                                }

                                MouseArea {
                                    id: integrateMouse

                                    anchors.fill: parent
                                    hoverEnabled: true
                                    enabled: integrateButton.enabledAction
                                    cursorShape:
                                        enabled
                                        ? Qt.PointingHandCursor
                                        : Qt.ArrowCursor

                                    onClicked: certificationCoordinator.integrate()
                                }
                            }
                        }

                        GohuText {
                            width: parent.width
                            text:
                                certificationCoordinator.state !== "IDLE"
                                ? "CERT // "
                                  + certificationCoordinator.state
                                  + " // "
                                  + (
                                      certificationCoordinator.lastError
                                      ? certificationCoordinator.lastError
                                      : roomService.summary
                                    )
                                : roomService.summary
                            font.pixelSize: 9
                            color:
                                certificationCoordinator.lastError
                                || roomService.lastError
                                ? Colors.red
                                : roomService.postOpStatus === "POST_OP_CLEAN"
                                ? Colors.cyan
                                : roomService.postOpRunning
                                ? Colors.orange
                                : roomService.armed
                                ? Colors.orange
                                : roomService.integrationMode === "DIVERGED"
                                ? Colors.magenta
                                : roomService.integrationMode === "FAST_FORWARD"
                                ? Colors.orange
                                : roomService.available
                                ? Colors.cyan
                                : Colors.magenta
                            elide: Text.ElideRight
                        }

                        GohuText {
                            width: parent.width
                            visible: roomService.rehearsalDetail.length > 0
                            text: roomService.rehearsalDetail
                            font.pixelSize: 8
                            color:
                                roomService.rehearsalStatus === "CONFLICTS"
                                ? Colors.red
                                : Colors.orange
                            elide: Text.ElideRight
                        }

                        GohuText {
                            width: parent.width
                            visible: roomService.postOpDetail.length > 0
                            text: roomService.postOpDetail
                            font.pixelSize: 8
                            color: Colors.cyan
                            elide: Text.ElideRight
                        }
                    }
                }
            }

            // ===== OPERATING ROOMS ==============================

            SectionLabel {
                text: "OPERATING ROOMS"
            }


        }

        // Only the operating-room selector/detail surface scrolls.
        Flickable {
            id: hospitalScroll

            anchors {
                top: fixedTop.bottom
                bottom: actionBay.top
                left: parent.left
                right: parent.right
                topMargin: 8
                bottomMargin: 10
                leftMargin: 18
                rightMargin: 18
            }

            clip: true
            contentWidth: width
            contentHeight: scrollContent.height
            boundsBehavior: Flickable.StopAtBounds
            flickDeceleration: 1800

            Column {
                id: scrollContent

                width: hospitalScroll.width
                spacing: 12

            Column {
                id: roomsColumn

                width: parent.width
                spacing: 7

                Repeater {
                    model: auditService.rooms

                    RoomRow {
                        team: String(
                            modelData.team
                            || modelData.branch
                            || ""
                        )

                        responsibility: String(
                            modelData.responsibility
                            || "AUTO DISCOVERED"
                        )
                    }
                }
            }


            }
        }

        Rectangle {
            id: actionBay

            height: 54
            anchors {
                left: parent.left
                right: parent.right
                bottom: bottomStop.top
                leftMargin: 18
                rightMargin: 18
                bottomMargin: 8
            }

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

                Row {
                    anchors.centerIn: parent
                    spacing: 22

                    GohuText {
                        id: refreshAction

                        text: patientService.refreshing ? "READING" : "REFRESH"
                        font.pixelSize: 10
                        color: refreshMouse.containsMouse ? Colors.orange : Colors.cyan
                        opacity: patientService.refreshing ? 0.55 : 1.0

                        layer.enabled: true
                        layer.effect: DropShadow {
                            radius: 5
                            samples: 7
                            opacity: refreshMouse.containsMouse ? 0.52 : 0.28
                            color: refreshAction.color
                            transparentBorder: true
                        }

                        MouseArea {
                            id: refreshMouse
                            anchors.fill: parent
                            anchors.margins: -8
                            hoverEnabled: true
                            enabled: !patientService.refreshing
                            cursorShape: Qt.PointingHandCursor

                            onClicked: {
                                hospitalGitService.refresh();
                                patientService.refresh();
                            }
                        }
                    }

                    GohuText {
                        id: auditAction

                        text: auditService.running
                              ? "AUDIT // RUNNING"
                              : auditService.available
                              ? "AUDIT // " + auditService.status
                              : "AUDIT"
                        font.pixelSize: 10
                        color: auditMouse.containsMouse
                               ? Colors.orange
                               : auditService.available
                               ? Colors.magenta
                               : auditService.lastError
                               ? Colors.red
                               : Colors.cyan
                        opacity: auditService.running ? 0.60 : 1.0

                        layer.enabled: true
                        layer.effect: DropShadow {
                            radius: 5
                            samples: 7
                            opacity: auditMouse.containsMouse
                                     ? 0.52
                                     : auditService.available
                                     ? 0.42
                                     : auditService.lastError
                                     ? 0.44
                                     : 0.28
                            color: auditAction.color
                            transparentBorder: true
                        }

                        MouseArea {
                            id: auditMouse
                            anchors.fill: parent
                            anchors.margins: -8
                            hoverEnabled: true
                            enabled: !auditService.running && auditService.repository.length > 0
                            cursorShape: Qt.PointingHandCursor

                            onClicked: auditService.runAudit()
                        }
                    }

                    GohuText {
                        id: githubAction

                        text: githubService.refreshing
                              ? "GITHUB // READING"
                              : githubService.available
                              ? "GITHUB // LIVE"
                              : "GITHUB"
                        font.pixelSize: 10
                        color: githubMouse.containsMouse
                               ? Colors.orange
                               : githubService.available
                               ? Colors.magenta
                               : Colors.cyan
                        opacity: githubService.refreshing ? 0.60 : 1.0

                        layer.enabled: true
                        layer.effect: DropShadow {
                            radius: 5
                            samples: 7
                            opacity: githubMouse.containsMouse
                                     ? 0.52
                                     : githubService.available
                                     ? 0.42
                                     : 0.28
                            color: githubAction.color
                            transparentBorder: true
                        }

                        MouseArea {
                            id: githubMouse
                            anchors.fill: parent
                            anchors.margins: -8
                            hoverEnabled: true
                            enabled: !githubService.refreshing && githubService.repoSlug.length > 0
                            cursorShape: Qt.PointingHandCursor

                            onClicked: githubService.refresh()
                        }
                    }
                }

                GohuText {
                    anchors {
                        right: parent.right
                        bottom: parent.bottom
                        rightMargin: 8
                        bottomMargin: 5
                    }

                    text: auditService.running
                          ? "PX AUDIT RUNNING // " + auditService.repository
                          : auditService.available
                          ? "AUDIT " + auditService.status
                            + " // " + String(auditService.workflowCount) + " WORKFLOWS"
                            + " // " + String(auditService.runCount) + " RECENT RUNS"
                            + " // " + String(auditService.rooms.length) + " ROOMS"
                          : auditService.lastError
                          ? "AUDIT ERROR // " + auditService.lastError
                          : !hospitalGitService.available
                          ? "LOCAL PATIENT OFFLINE"
                          : githubService.refreshing
                          ? "LOCAL LIVE // PX → GITHUB READING"
                          : githubService.available
                          ? "LOCAL + PX/GITHUB LIVE // WRITE ACTUATORS OFFLINE"
                          : githubService.lastError
                          ? "LOCAL LIVE // PX/GITHUB OFFLINE"
                          : "LOCAL LIVE // PX/GITHUB NOT REQUESTED"
                    font.pixelSize: 8
                    color: Colors.magenta

                    layer.enabled: true
                    layer.effect: DropShadow {
                        radius: 8
                        samples: 7
                        opacity: 0.56
                        color: Colors.magenta
                        transparentBorder: true
                    }
                }
            }

        // AppControl / CPU++ selector scrollbar geometry.
        Rectangle {
            id: scrollRail

            width: 10

            anchors {
                top: hospitalScroll.top
                bottom: hospitalScroll.bottom
                right: parent.right
                topMargin: 0
                bottomMargin: 0
                rightMargin: 3
            }

            color: Colors.cyan

            readonly property bool scrollable:
                hospitalScroll.contentHeight
                > hospitalScroll.height

            opacity: 1.0
            visible: true
            z: 300

            property real maxContentY:
                Math.max(
                    0,
                    hospitalScroll.contentHeight
                    - hospitalScroll.height
                )

            property real handleTravel:
                Math.max(
                    0,
                    height - scrollThumb.height
                )

            function setScrollFromHandleY(handleY) {
                if (maxContentY <= 0 || handleTravel <= 0)
                    return;

                const clampedY =
                    Math.max(
                        0,
                        Math.min(handleTravel, handleY)
                    );

                hospitalScroll.contentY =
                    (clampedY / handleTravel) * maxContentY;
            }

            RectangularShadow {
                anchors.fill: parent
                spread: 2
                z: -1
                opacity: 0.24
                color: parent.color
            }

            Rectangle {
                id: scrollThumb

                width: 6
                anchors.horizontalCenter: parent.horizontalCenter

                height:
                    scrollRail.scrollable
                    ? Math.max(
                        30,
                        parent.height
                        * Math.min(
                            1.0,
                            hospitalScroll.visibleArea.heightRatio
                        )
                    )
                    : 42

                y: {
                    if (!scrollRail.scrollable)
                        return 0;

                    const ratio =
                        Math.max(
                            0.0,
                            Math.min(
                                1.0,
                                Number(
                                    hospitalScroll.visibleArea.heightRatio
                                    || 0
                                )
                            )
                        );

                    const maxPosition =
                        Math.max(0.0, 1.0 - ratio);

                    const position =
                        Math.max(
                            0.0,
                            Math.min(
                                maxPosition,
                                Number(
                                    hospitalScroll.visibleArea.yPosition
                                    || 0
                                )
                            )
                        );

                    if (maxPosition <= 0
                            || scrollRail.handleTravel <= 0)
                        return 0;

                    return (
                        position / maxPosition
                    ) * scrollRail.handleTravel;
                }

                color: Colors.magenta
                opacity: 1.0

                RectangularShadow {
                    anchors.fill: parent
                    spread: 2
                    z: -1
                    opacity: 0.28
                    color: Colors.magenta
                }
            }

            MouseArea {
                id: scrollMouse

                anchors.fill: parent
                hoverEnabled: true
                acceptedButtons: Qt.LeftButton
                enabled: scrollRail.scrollable
                cursorShape: scrollRail.scrollable
                             ? Qt.SizeVerCursor
                             : Qt.ArrowCursor

                property real dragOffset: 0

                onPressed: function(mouse) {
                    const handleTop = scrollThumb.y;
                    const handleBottom =
                        scrollThumb.y
                        + scrollThumb.height;

                    dragOffset =
                        mouse.y >= handleTop
                        && mouse.y <= handleBottom
                        ? mouse.y - handleTop
                        : scrollThumb.height / 2;

                    scrollRail.setScrollFromHandleY(
                        mouse.y - dragOffset
                    );
                }

                onPositionChanged: function(mouse) {
                    if (pressed)
                        scrollRail.setScrollFromHandleY(
                            mouse.y - dragOffset
                        );
                }

                onWheel: function(wheel) {
                    const step =
                        wheel.angleDelta.y > 0
                        ? -90
                        : 90;

                    hospitalScroll.contentY =
                        Math.max(
                            0,
                            Math.min(
                                scrollRail.maxContentY,
                                hospitalScroll.contentY
                                + step
                            )
                        );

                    wheel.accepted = true;
                }
            }
        }
    }
}
