import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.components
import "../services/git"
import "../services/hospital"
import QtQuick.Effects
import Qt5Compat.GraphicalEffects

PanelWindow {
    id: root

    property bool menuOpen: false

    property int panelWidth: 700
    property int panelHeight: 875
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

    Timer {
        interval: 3000
        repeat: true
        running: root.menuOpen

        onTriggered: hospitalGitService.refresh()
    }

    Timer {
        interval: 5000
        repeat: true
        running: root.menuOpen

        onTriggered: patientService.refresh()
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

    component RoomRow: Rectangle {
        id: roomRow

        property string team: ""
        property string responsibility: ""
        property string stateText: "UNVERIFIED"

        width: roomsColumn.width
        height: 30

        color: Colors.dark
        border.width: 1
        border.color: Colors.magenta

        RectangularShadow {
            anchors.fill: parent
            spread: 3
            z: -1
            opacity: 0.28
            color: Colors.magenta
        }

        GohuText {
            anchors {
                left: parent.left
                verticalCenter: parent.verticalCenter
                leftMargin: 10
            }

            text: roomRow.team
            font.pixelSize: 12
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
                leftMargin: 62
            }

            width: 440
            text: roomRow.responsibility
            font.pixelSize: 11
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
            font.pixelSize: 9
            color: Colors.cyan
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

        Column {
            id: content

            anchors {
                fill: parent
                margins: 18
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

            Rectangle {
                id: topologyFrame

                width: parent.width
                height: 190

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
                        margins: 10
                    }

                    spacing: 6

                    Item {
                        width: parent.width
                        height: 18

                        SectionLabel {
                            anchors.left: parent.left
                            anchors.verticalCenter: parent.verticalCenter
                            text: "PATIENT TOPOLOGY"
                        }

                        Row {
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 3

                            MetaLabel {
                                visible: patientService.refreshing
                                text: "READING GIT GRAPH"
                            }

                            GohuText {
                                visible: !patientService.refreshing
                                text: String(patientService.commitCount)
                                font.pixelSize: 10
                                color: Colors.orange

                                layer.enabled: true
                                layer.effect: DropShadow {
                                    radius: 5
                                    samples: 7
                                    opacity: 0.42
                                    color: Colors.orange
                                    transparentBorder: true
                                }
                            }

                            MetaLabel {
                                visible: !patientService.refreshing
                                text: "COMMITS //"
                            }

                            GohuText {
                                visible: !patientService.refreshing
                                text: String(patientService.branchCount)
                                font.pixelSize: 10
                                color: Colors.orange

                                layer.enabled: true
                                layer.effect: DropShadow {
                                    radius: 5
                                    samples: 7
                                    opacity: 0.42
                                    color: Colors.orange
                                    transparentBorder: true
                                }
                            }

                            MetaLabel {
                                visible: !patientService.refreshing
                                text: "REFS"
                            }
                        }
                    }

                    Flickable {
                        id: topologyFlick

                        width: parent.width
                        height: 146

                        clip: true
                        boundsBehavior: Flickable.StopAtBounds
                        contentWidth: width
                        contentHeight: Math.max(height, patientService.commitCount * topologyBody.rowHeight)

                        Item {
                            id: topologyBody

                            width: topologyFlick.width
                            height: topologyFlick.contentHeight

                            property real rowHeight: 24
                            property real laneWidth: 22
                            property real laneAreaWidth:
                                Math.min(190, 44 + (patientService.maxLane + 1) * laneWidth)

                            function laneColor(laneNumber) {
                                const lane = Number(laneNumber || 0) % 6;

                                if (lane === 0)
                                    return Colors.orange;
                                if (lane === 1)
                                    return Colors.cyan;
                                if (lane === 2)
                                    return Colors.magenta;
                                if (lane === 3)
                                    return Colors.blue;
                                if (lane === 4)
                                    return Colors.green;

                                return Colors.red;
                            }

                            function nodeX(laneNumber) {
                                return 14 + Number(laneNumber || 0) * laneWidth;
                            }

                            function escapeStyled(value) {
                                return String(value || "")
                                    .replace(/&/g, "&amp;")
                                    .replace(/</g, "&lt;")
                                    .replace(/>/g, "&gt;");
                            }

                            function graphMetadataMarkup(refValue, subjectValue, headRow) {
                                const refs = String(refValue || "")
                                    .split(" • ")
                                    .filter(function(name) { return name.length > 0; });
                                const pieces = [];

                                for (let i = 0; i < refs.length; ++i) {
                                    const name = refs[i];
                                    const color = name.indexOf("origin/") === 0
                                        ? String(Colors.white)
                                        : String(Colors.cyan);

                                    pieces.push(
                                        "<font color=\"" + color + "\">"
                                        + escapeStyled(name)
                                        + "</font>"
                                    );
                                }

                                let result = pieces.join(
                                    "<font color=\"" + String(Colors.white) + "\"> • </font>"
                                );

                                const subject = String(subjectValue || "");

                                if (subject) {
                                    if (result)
                                        result += "<font color=\"" + String(Colors.white) + "\">  //  </font>";
                                    else
                                        result += "<font color=\"" + String(Colors.white) + "\">//  </font>";

                                    result += "<font color=\""
                                        + String(
                                            headRow
                                            ? Colors.yellow
                                            : refs.length > 0
                                            ? Colors.cyan
                                            : Colors.blue
                                        )
                                        + "\">"
                                        + escapeStyled(subject)
                                        + "</font>";
                                }

                                return result;
                            }

                            Canvas {
                                id: graphCanvas

                                anchors.fill: parent

                                onWidthChanged: requestPaint()
                                onHeightChanged: requestPaint()

                                onPaint: {
                                    const ctx = getContext("2d");

                                    ctx.globalAlpha = 1.0;
                                    ctx.clearRect(0, 0, width, height);
                                    ctx.lineWidth = 1.35;

                                    for (let i = 0; i < patientService.commitCount; ++i) {
                                        const row = patientService.commitAt(i);

                                        if (!row)
                                            continue;

                                        const parents = String(row.parents || "").trim();

                                        if (!parents)
                                            continue;

                                        const parentList = parents.split(/\s+/);
                                        const x1 = topologyBody.nodeX(row.lane);
                                        const y1 = i * topologyBody.rowHeight + topologyBody.rowHeight / 2;

                                        for (let p = 0; p < parentList.length; ++p) {
                                            const parentIndex = patientService.indexOfSha(parentList[p]);

                                            if (parentIndex < 0)
                                                continue;

                                            const parentRow = patientService.commitAt(parentIndex);

                                            if (!parentRow)
                                                continue;

                                            const x2 = topologyBody.nodeX(parentRow.lane);
                                            const y2 = parentIndex * topologyBody.rowHeight
                                                     + topologyBody.rowHeight / 2;
                                            const middleY = y1 + (y2 - y1) * 0.52;

                                            ctx.beginPath();
                                            ctx.strokeStyle = String(topologyBody.laneColor(row.lane));
                                            ctx.globalAlpha = 0.72;
                                            ctx.moveTo(x1, y1);
                                            ctx.lineTo(x1, middleY);
                                            ctx.lineTo(x2, middleY);
                                            ctx.lineTo(x2, y2);
                                            ctx.stroke();
                                        }
                                    }

                                    ctx.globalAlpha = 1.0;
                                }
                            }

                            Repeater {
                                model: patientService.topologyModel

                                delegate: Item {
                                    width: topologyBody.width
                                    height: topologyBody.rowHeight
                                    y: index * topologyBody.rowHeight

                                    Rectangle {
                                        width: isHead || String(refsText || "").length > 0 ? 10 : 8
                                        height: width
                                        radius: width / 2
                                        x: topologyBody.nodeX(lane) - width / 2
                                        anchors.verticalCenter: parent.verticalCenter
                                        color: Colors.dark
                                        z: 1
                                    }

                                    NotoText {
                                        id: topologyStar

                                        width: 20
                                        height: parent.height
                                        x: topologyBody.nodeX(lane) - width / 2
                                        anchors.verticalCenter: parent.verticalCenter
                                        z: 2

                                        readonly property bool refLandmark:
                                            String(refsText || "").length > 0
                                        readonly property color starColor:
                                            isHead
                                            ? Colors.yellow
                                            : topologyBody.laneColor(lane)

                                        text: isHead || refLandmark ? "★" : "✧"
                                        font.pixelSize: isHead ? 15 : refLandmark ? 13 : 13
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                        color: starColor

                                        layer.enabled: true
                                        layer.effect: DropShadow {
                                            radius: isHead ? 7 : topologyStar.refLandmark ? 5 : 5
                                            samples: isHead ? 9 : 7
                                            opacity: isHead ? 0.78 : topologyStar.refLandmark ? 0.48 : 0.38
                                            color: topologyStar.starColor
                                            transparentBorder: true
                                        }
                                    }

                                    Row {
                                        x: topologyBody.laneAreaWidth
                                        width: parent.width - x - 6
                                        anchors.verticalCenter: parent.verticalCenter
                                        spacing: 4

                                        GohuText {
                                            text: shortSha
                                            font.pixelSize: 9
                                            color: Colors.orange

                                            layer.enabled: true
                                            layer.effect: DropShadow {
                                                radius: 5
                                                samples: 7
                                                opacity: 0.40
                                                color: Colors.orange
                                                transparentBorder: true
                                            }
                                        }

                                        GohuText {
                                            width: parent.width - implicitWidth - 4
                                            text: topologyBody.graphMetadataMarkup(refsText, subject, isHead)
                                            textFormat: Text.StyledText
                                            font.pixelSize: 9
                                            color: Colors.white
                                            elide: Text.ElideRight

                                            layer.enabled: true
                                            layer.effect: DropShadow {
                                                radius: isHead ? 6 : 6
                                                samples: isHead ? 7 : 9
                                                opacity: isHead ? 0.46 : 0.38
                                                color: isHead ? Colors.yellow : Colors.cyan
                                                transparentBorder: true
                                            }
                                        }
                                    }
                                }
                            }

                            Connections {
                                target: patientService

                                function onTopologyRevisionChanged() {
                                    graphCanvas.requestPaint();
                                }
                            }
                        }
                    }
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

                        MetaLabel {
                            width: 110
                            text: "BRANCH"
                        }

                        MetaValue {
                            width: 500
                            text: patientService.branch

                            layer.effect: DropShadow {
                                radius: 7
                                samples: 9
                                opacity: 0.34
                                color: Colors.cyan
                                transparentBorder: true
                            }
                        }
                    }

                    Row {
                        spacing: 10

                        MetaLabel {
                            width: 110
                            text: "PATIENT HEAD"
                        }

                        MetaValue {
                            width: 500
                            text: patientService.head + " // " + patientService.worktree

                            layer.effect: DropShadow {
                                radius: 7
                                samples: 9
                                opacity: 0.34
                                color: Colors.white
                                transparentBorder: true
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
                spacing: 4

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
                        text: "REFRESH"
                        font.pixelSize: 10
                        color: Colors.cyan
                        opacity: 0.45
                    }

                    GohuText {
                        text: "AUDIT"
                        font.pixelSize: 10
                        color: Colors.cyan
                        opacity: 0.45
                    }

                    GohuText {
                        text: "GITHUB"
                        font.pixelSize: 10
                        color: Colors.cyan
                        opacity: 0.45
                    }
                }

                GohuText {
                    anchors {
                        right: parent.right
                        bottom: parent.bottom
                        rightMargin: 8
                        bottomMargin: 5
                    }

                    text: hospitalGitService.available
                          ? "LOCAL PATIENT LIVE // ACTUATORS OFFLINE"
                          : "LOCAL PATIENT OFFLINE"
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
}
