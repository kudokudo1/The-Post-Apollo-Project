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

    property int panelWidth: 700
    property int panelHeight: 1040
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
        hospitalGitService.refresh();
        patientService.refresh();
    }

    GitService {
        id: hospitalGitService
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

    Connections {
        target: patientService

        function onRefreshed() {
            githubService.refresh();
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
        height: 44

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
                verticalCenter: parent.verticalCenter
                leftMargin: 12
            }

            text: roomRow.team
            font.pixelSize: 14
            color: Colors.orange

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
                verticalCenter: parent.verticalCenter
                leftMargin: 74
            }

            width: 340
            text: roomRow.responsibility
            font.pixelSize: 13
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
            anchors {
                right: parent.right
                verticalCenter: parent.verticalCenter
                rightMargin: 10
            }

            text: roomRow.stateText
            font.pixelSize: 11
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
            anchors.fill: parent
            anchors.margins: root.frameInset

            color: "transparent"
            border.width: 1
            border.color: Colors.cyan
            opacity: 0.70
        }

        Flickable {
            id: hospitalScroll

            anchors {
                fill: parent
                leftMargin: 18
                topMargin: 18
                rightMargin: 58
                bottomMargin: 18
            }

            clip: true
            contentWidth: width
            contentHeight: content.height
            boundsBehavior: Flickable.StopAtBounds
            flickDeceleration: 1800

            Column {
                id: content

                width: hospitalScroll.width
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

            Rectangle {
                width: parent.width
                height: 118

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

                    spacing: 7

                    SectionLabel {
                        text: "PATIENT"
                    }

                    Row {
                        spacing: 10

                        MetaLabel {
                            width: 110
                            text: "REPOSITORY"
                        }

                        MetaValue {
                            width: 500
                            text: patientService.repository
                            color: Colors.orange

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
                        spacing: 10

                        OrangeLabel {
                            width: 110
                            text: "BRANCH"
                        }

                        CyanValue {
                            width: 500
                            text: patientService.branch
                        }
                    }

                    Row {
                        spacing: 10

                        MetaLabel {
                            width: 110
                            text: "PATIENT HEAD"
                        }

                        Row {
                            width: 500
                            spacing: 0

                            BlueValue {
                                text: patientService.head + " // "
                            }

                            GohuText {
                                readonly property bool cleanState:
                                    String(patientService.worktree || "")
                                        .trim()
                                        .toUpperCase() === "CLEAN"

                                text: patientService.worktree
                                font.pixelSize: 11
                                opacity: 1.0
                                color: cleanState ? Colors.orange : Colors.white

                                layer.enabled: true
                                layer.effect: DropShadow {
                                    radius: cleanState ? 9 : 7
                                    samples: cleanState ? 13 : 9
                                    opacity: cleanState ? 0.76 : 0.34
                                    color: cleanState ? Colors.orange : Colors.cyan
                                    transparentBorder: true
                                }
                            }
                        }
                    }
                }
            }

            // ===== OPERATING ROOMS ==============================

            SectionLabel {
                text: "OPERATING ROOMS"
            }

            Column {
                id: roomsColumn

                width: parent.width
                spacing: 7

                RoomRow { team: "T1"; responsibility: "SYSTEM / HUNTER" }
                RoomRow { team: "T2"; responsibility: "FAVORITES" }
                RoomRow { team: "T3-F"; responsibility: "FILES" }
                RoomRow { team: "T3-R"; responsibility: "REMOTE" }
                RoomRow { team: "T4"; responsibility: "CPU++" }
                RoomRow { team: "T5"; responsibility: "TABS / SURFACE" }
                RoomRow { team: "T6"; responsibility: "APPLICATION AUDIO" }
                RoomRow { team: "T7"; responsibility: "DESKTOP IDENTITY" }
                RoomRow { team: "T8"; responsibility: "APPS" }
            }

            Rectangle {
                id: roomDetail

                width: parent.width
                height: visible ? 170 : 0
                visible: root.selectedRoomTeam.length > 0

                color: Colors.dark
                border.width: 1
                border.color: Colors.orange

                RectangularShadow {
                    anchors.fill: parent
                    spread: 4
                    z: -1
                    opacity: 0.30
                    color: Colors.orange
                }

                Column {
                    anchors {
                        fill: parent
                        margins: 12
                    }

                    spacing: 7

                    GohuText {
                        text: {
                            const room = root.selectedRoomData || {};
                            const responsibility =
                                String(room.responsibility || "");
                            return "ROOM // " + root.selectedRoomTeam
                                   + (responsibility
                                      ? " // " + responsibility
                                      : "");
                        }
                        font.pixelSize: 13
                        color: Colors.orange
                    }

                    Row {
                        spacing: 10

                        MetaLabel {
                            width: 92
                            text: "BRANCH"
                        }

                        CyanValue {
                            width: roomDetail.width - 130
                            text: {
                                const room = root.selectedRoomData || {};
                                return String(room.branch || "NO DATA");
                            }
                        }
                    }

                    Row {
                        spacing: 10

                        MetaLabel {
                            width: 92
                            text: "HEAD"
                        }

                        BlueValue {
                            width: roomDetail.width - 130
                            text: {
                                const room = root.selectedRoomData || {};
                                const head = String(room.head || "");
                                return head ? head.slice(0, 12) : "NO DATA";
                            }
                        }
                    }

                    Row {
                        spacing: 10

                        MetaLabel {
                            width: 92
                            text: "RELATION"
                        }

                        GohuText {
                            text: {
                                const room = root.selectedRoomData || {};
                                const state =
                                    String(room.state || "WAITING");
                                const ahead = Number(room.ahead || 0);
                                const behind = Number(room.behind || 0);
                                return state + " // +" + ahead
                                       + " / -" + behind;
                            }
                            font.pixelSize: 11
                            color: Colors.magenta
                        }
                    }

                    Row {
                        spacing: 10

                        MetaLabel {
                            width: 92
                            text: "LAST TOUCH"
                        }

                        MetaValue {
                            width: roomDetail.width - 130
                            text: {
                                const room = root.selectedRoomData || {};
                                return String(room.updated_at || "NO DATA");
                            }
                        }
                    }

                    GohuText {
                        text: "CLICK SELECTED ROOM AGAIN TO CLOSE"
                        font.pixelSize: 9
                        color: Colors.cyan
                        opacity: 0.64
                    }
                }
            }

            // ===== ACTION BAY ===================================

            Rectangle {
                width: parent.width
                height: 54

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
        }
        }

        // AppControl / CPU++ selector scrollbar geometry.
        Rectangle {
            id: scrollRail

            width: 10

            anchors {
                top: parent.top
                bottom: parent.bottom
                right: parent.right
                topMargin: 20
                bottomMargin: 20
                rightMargin: 10
            }

            color: Colors.cyan

            readonly property bool scrollable:
                hospitalScroll.contentHeight
                > hospitalScroll.height

            opacity: scrollable ? 0.90 : 0.38
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
                opacity: scrollRail.scrollable ? 1.0 : 0.72

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
