import QtQuick
import Quickshell
import qs.components

Item {
    id: root

    required property var historyService

    property string teamFilter: ""
    property string stateFilter: ""
    property int selectedIndex: -1

    readonly property var stateOptions: [
        "",
        "CANDIDATE",
        "VERIFIED",
        "CERTIFIED",
        "ARMED",
        "INTEGRATING",
        "POST_OP",
        "IN_MAIN",
        "BLOCKED",
        "REOPENED"
    ]

    readonly property var teamOptions: {
        const source =
            root.historyService
            && Array.isArray(root.historyService.events)
            ? root.historyService.events
            : [];
        const seen = {};
        const teams = [""];

        for (let i = 0; i < source.length; ++i) {
            const team = String((source[i] || {}).team || "");

            if (team && !seen[team]) {
                seen[team] = true;
                teams.push(team);
            }
        }

        return teams;
    }

    readonly property var filteredEvents: {
        const source =
            root.historyService
            && Array.isArray(root.historyService.events)
            ? root.historyService.events
            : [];
        const team = String(root.teamFilter || "");
        const state = String(root.stateFilter || "");

        return source
            .filter(function(event) {
                const row = event || {};
                return (!team || String(row.team || "") === team)
                    && (!state || String(row.state || "") === state);
            })
            .slice()
            .reverse();
    }

    readonly property var selectedEvent: {
        if (root.selectedIndex < 0
                || root.selectedIndex >= root.filteredEvents.length)
            return null;

        return root.filteredEvents[root.selectedIndex] || null;
    }

    signal eventActivated(var event)

    function shortSha(value) {
        const sha = String(value || "");
        return sha.length > 10 ? sha.slice(0, 10) : sha;
    }

    function packetFor(event) {
        const details = (event || {}).details || {};
        return details.packet || {};
    }

    function eventRepository(event) {
        const details = (event || {}).details || {};
        const packet = packetFor(event);
        return String(packet.repository || details.repository || "");
    }

    function eventBranch(event) {
        const details = (event || {}).details || {};
        const packet = packetFor(event);
        return String(packet.branch || details.branch || "");
    }

    function eventHead(event) {
        const details = (event || {}).details || {};
        const packet = packetFor(event);
        return String(packet.head || details.head || "");
    }

    function eventBaseHead(event) {
        const details = (event || {}).details || {};
        const packet = packetFor(event);
        return String(packet.baseHead || details.baseHead || "");
    }

    function eventReason(event) {
        const details = (event || {}).details || {};
        const packet = packetFor(event);
        return String(packet.reason || details.reason || "");
    }

    function cycleOption(options, current, delta) {
        if (!Array.isArray(options) || options.length === 0)
            return "";

        let index = options.indexOf(current);
        if (index < 0)
            index = 0;

        index =
            (index + Number(delta || 0) + options.length)
            % options.length;

        return String(options[index] || "");
    }

    function cycleTeam(delta) {
        teamFilter =
            cycleOption(teamOptions, teamFilter, delta);
        selectedIndex =
            filteredEvents.length > 0 ? 0 : -1;
    }

    function cycleState(delta) {
        stateFilter =
            cycleOption(stateOptions, stateFilter, delta);
        selectedIndex =
            filteredEvents.length > 0 ? 0 : -1;
    }

    function selectEvent(index) {
        const requested = Number(index);

        if (requested < 0
                || requested >= filteredEvents.length)
            return false;

        selectedIndex = requested;
        eventActivated(selectedEvent);
        return true;
    }

    onFilteredEventsChanged: {
        if (filteredEvents.length === 0)
            selectedIndex = -1;
        else if (selectedIndex < 0
                || selectedIndex >= filteredEvents.length)
            selectedIndex = 0;
    }

    component ReportButton: Rectangle {
        id: button

        property string label: ""
        property bool enabledAction: true
        signal triggered()

        height: 32
        color:
            !enabledAction
            ? Colors.black
            : mouse.pressed
            ? Colors.orange
            : Colors.black
        border.width: mouse.containsMouse ? 2 : 1
        border.color:
            !enabledAction
            ? Colors.cyan
            : mouse.containsMouse
            ? Colors.orange
            : Colors.cyan

        GohuText {
            anchors.centerIn: parent
            text: button.label
            font.pixelSize: 11
            color: mouse.pressed ? Colors.black : Colors.cyan
            opacity: button.enabledAction ? 1.0 : 0.34
        }

        MouseArea {
            id: mouse
            anchors.fill: parent
            enabled: button.enabledAction
            hoverEnabled: true
            cursorShape: enabled
                         ? Qt.PointingHandCursor
                         : Qt.ArrowCursor
            onClicked: button.triggered()
        }
    }

    component EvidenceRow: Row {
        property string label: ""
        property string value: ""
        property color valueColor: Colors.cyan

        height: 24
        spacing: 8

        GohuText {
            width: 88
            text: parent.label
            font.pixelSize: 10
            color: Colors.magenta
        }

        GohuText {
            width: parent.width - 96
            text: parent.value || "—"
            font.pixelSize: 10
            color: parent.valueColor
            elide: Text.ElideRight
        }
    }

    Rectangle {
        anchors.fill: parent
        color: Colors.dark
        border.width: 1
        border.color: Colors.magenta

        MouseArea {
            anchors.fill: parent
            hoverEnabled: true
            acceptedButtons: Qt.AllButtons

            onWheel: function(wheel) {
                wheel.accepted = true;
            }
        }

        Column {
            anchors {
                fill: parent
                margins: 10
            }
            spacing: 8

            Row {
                width: parent.width
                height: 36
                spacing: 8

                GohuText {
                    width: parent.width - 286
                    anchors.verticalCenter: parent.verticalCenter
                    text:
                        "REPORTS // "
                        + String(root.filteredEvents.length)
                        + " / "
                        + String(
                            root.historyService
                            && Array.isArray(root.historyService.events)
                            ? root.historyService.events.length
                            : 0
                        )
                    font.pixelSize: 13
                    color: Colors.magenta
                }

                ReportButton {
                    width: 82
                    label: "TEAM ◀"
                    onTriggered: root.cycleTeam(-1)
                }

                ReportButton {
                    width: 82
                    label: "TEAM ▶"
                    onTriggered: root.cycleTeam(1)
                }

                ReportButton {
                    width: 98
                    label: "CLEAR FILTER"
                    enabledAction:
                        root.teamFilter.length > 0
                        || root.stateFilter.length > 0

                    onTriggered: {
                        root.teamFilter = "";
                        root.stateFilter = "";
                        root.selectedIndex =
                            root.filteredEvents.length > 0 ? 0 : -1;
                    }
                }
            }

            Rectangle {
                width: parent.width
                height: 40
                color: Colors.black
                border.width: 1
                border.color: Colors.cyan

                Row {
                    anchors {
                        fill: parent
                        margins: 5
                    }
                    spacing: 8

                    GohuText {
                        width: 42
                        anchors.verticalCenter: parent.verticalCenter
                        text: "TEAM"
                        font.pixelSize: 10
                        color: Colors.magenta
                    }

                    GohuText {
                        width: (parent.width - 176) * 0.5
                        anchors.verticalCenter: parent.verticalCenter
                        text: root.teamFilter || "ALL ROOMS"
                        font.pixelSize: 11
                        color: Colors.cyan
                        elide: Text.ElideRight
                    }

                    ReportButton {
                        width: 26
                        height: 28
                        anchors.verticalCenter: parent.verticalCenter
                        label: "◀"
                        onTriggered: root.cycleState(-1)
                    }

                    GohuText {
                        width: (parent.width - 176) * 0.5
                        anchors.verticalCenter: parent.verticalCenter
                        text: root.stateFilter || "ALL STATES"
                        font.pixelSize: 11
                        color:
                            root.stateFilter === "BLOCKED"
                            ? Colors.red
                            : root.stateFilter === "IN_MAIN"
                            ? Colors.green
                            : Colors.orange
                        horizontalAlignment: Text.AlignHCenter
                        elide: Text.ElideRight
                    }

                    ReportButton {
                        width: 26
                        height: 28
                        anchors.verticalCenter: parent.verticalCenter
                        label: "▶"
                        onTriggered: root.cycleState(1)
                    }
                }
            }

            Row {
                width: parent.width
                height: parent.height - 92
                spacing: 10

                Rectangle {
                    width: (parent.width - 10) * 0.43
                    height: parent.height
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.orange

                    Flickable {
                        id: reportList
                        anchors {
                            fill: parent
                            margins: 6
                        }
                        clip: true
                        contentWidth: width
                        contentHeight: reportColumn.height
                        boundsBehavior: Flickable.StopAtBounds

                        Column {
                            id: reportColumn
                            width: reportList.width
                            spacing: 5

                            Repeater {
                                model: root.filteredEvents

                                Rectangle {
                                    required property int index
                                    required property var modelData

                                    width: reportColumn.width
                                    height: 92
                                    color:
                                        root.selectedIndex === index
                                        ? Colors.yellow
                                        : Colors.dark
                                    border.width:
                                        root.selectedIndex === index
                                        || reportMouse.containsMouse
                                        ? 2 : 1
                                    border.color:
                                        root.selectedIndex === index
                                        ? Colors.orange
                                        : reportMouse.containsMouse
                                        ? Colors.orange
                                        : modelData.state === "BLOCKED"
                                        ? Colors.red
                                        : modelData.state === "IN_MAIN"
                                        ? Colors.green
                                        : Colors.cyan

                                    Column {
                                        anchors {
                                            fill: parent
                                            margins: 6
                                        }
                                        spacing: 3

                                        Row {
                                            width: parent.width

                                            GohuText {
                                                width: parent.width * 0.62
                                                text: String(
                                                    modelData.eventType
                                                    || "EVENT"
                                                )
                                                font.pixelSize: 11
                                                color:
                                                    root.selectedIndex === index
                                                    ? Colors.magenta
                                                    : Colors.cyan
                                                elide: Text.ElideRight
                                            }

                                            GohuText {
                                                width: parent.width * 0.38
                                                text: String(
                                                    modelData.state
                                                    || "UNKNOWN"
                                                )
                                                font.pixelSize: 11
                                                horizontalAlignment:
                                                    Text.AlignRight
                                                color:
                                                    modelData.state === "BLOCKED"
                                                    ? Colors.red
                                                    : modelData.state === "IN_MAIN"
                                                    ? Colors.green
                                                    : Colors.orange
                                                elide: Text.ElideRight
                                            }
                                        }

                                        GohuText {
                                            width: parent.width
                                            text: String(
                                                modelData.team
                                                || "NO ROOM"
                                            )
                                            font.pixelSize: 10
                                            color:
                                                root.selectedIndex === index
                                                ? Colors.magenta
                                                : Colors.white
                                            elide: Text.ElideRight
                                        }

                                        GohuText {
                                            width: parent.width
                                            text:
                                                root.eventBranch(modelData)
                                                + (
                                                    root.eventHead(modelData)
                                                    ? " // "
                                                      + root.shortSha(
                                                          root.eventHead(modelData)
                                                      )
                                                    : ""
                                                )
                                            font.pixelSize: 10
                                            color: Colors.cyan
                                            opacity: 0.82
                                            elide: Text.ElideRight
                                        }

                                        GohuText {
                                            width: parent.width
                                            text: String(
                                                modelData.recordedAt
                                                || ""
                                            )
                                            font.pixelSize: 9
                                            color: Colors.white
                                            opacity: 0.58
                                            elide: Text.ElideRight
                                        }
                                    }

                                    MouseArea {
                                        id: reportMouse
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: root.selectEvent(index)
                                    }
                                }
                            }

                            GohuText {
                                width: parent.width
                                visible: root.filteredEvents.length === 0
                                text: "NO REPORTS MATCH THIS FILTER"
                                font.pixelSize: 11
                                color: Colors.cyan
                                opacity: 0.52
                                horizontalAlignment: Text.AlignHCenter
                            }
                        }
                    }
                }

                Rectangle {
                    width: (parent.width - 10) * 0.57
                    height: parent.height
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.cyan

                    Flickable {
                        id: detailFlick
                        anchors {
                            fill: parent
                            margins: 8
                        }
                        clip: true
                        contentWidth: width
                        contentHeight: detailColumn.height
                        boundsBehavior: Flickable.StopAtBounds

                        Column {
                            id: detailColumn
                            width: detailFlick.width
                            spacing: 7

                            readonly property var event:
                                root.selectedEvent || ({})
                            readonly property var packet:
                                root.packetFor(event)
                            readonly property var diff:
                                packet.diff || ({})
                            readonly property var checks:
                                packet.checks || ({})
                            readonly property var runs:
                                packet.runs || ({})
                            readonly property var runSummary:
                                runs.summary || ({})
                            readonly property var rehearsal:
                                packet.rehearsal || ({})
                            readonly property var postOp:
                                packet.postOp || ({})

                            GohuText {
                                width: parent.width
                                text:
                                    root.selectedEvent
                                    ? "SURGICAL REPORT // "
                                      + String(
                                          detailColumn.event.eventType
                                          || "EVENT"
                                      )
                                    : "SURGICAL REPORT // SELECT AN EVENT"
                                font.pixelSize: 13
                                color: Colors.magenta
                                elide: Text.ElideRight
                            }

                            Rectangle {
                                width: parent.width
                                height: 1
                                color: Colors.magenta
                                opacity: 0.72
                            }

                            EvidenceRow {
                                width: parent.width
                                label: "STATE"
                                value: String(detailColumn.event.state || "")
                                valueColor:
                                    detailColumn.event.state === "BLOCKED"
                                    ? Colors.red
                                    : detailColumn.event.state === "IN_MAIN"
                                    ? Colors.green
                                    : Colors.orange
                            }

                            EvidenceRow {
                                width: parent.width
                                label: "ROOM"
                                value: String(detailColumn.event.team || "")
                            }

                            EvidenceRow {
                                width: parent.width
                                label: "REPOSITORY"
                                value: root.eventRepository(detailColumn.event)
                            }

                            EvidenceRow {
                                width: parent.width
                                label: "BRANCH"
                                value: root.eventBranch(detailColumn.event)
                            }

                            EvidenceRow {
                                width: parent.width
                                label: "HEAD"
                                value: root.shortSha(
                                    root.eventHead(detailColumn.event)
                                )
                            }

                            EvidenceRow {
                                width: parent.width
                                label: "BASE HEAD"
                                value: root.shortSha(
                                    root.eventBaseHead(detailColumn.event)
                                )
                            }

                            EvidenceRow {
                                width: parent.width
                                label: "RECORDED"
                                value: String(
                                    detailColumn.event.recordedAt || ""
                                )
                            }

                            Rectangle {
                                width: parent.width
                                height: 1
                                color: Colors.cyan
                                opacity: 0.42
                            }

                            EvidenceRow {
                                width: parent.width
                                label: "FILES"
                                value:
                                    detailColumn.diff.files !== undefined
                                    ? String(detailColumn.diff.files)
                                      + " // +"
                                      + String(
                                          detailColumn.diff.additions || 0
                                      )
                                      + " / -"
                                      + String(
                                          detailColumn.diff.deletions || 0
                                      )
                                    : ""
                            }

                            EvidenceRow {
                                width: parent.width
                                label: "CHECKS"
                                value:
                                    String(
                                        detailColumn.checks.status
                                        || (
                                            detailColumn.checks.passed === true
                                            ? "PASS"
                                            : ""
                                        )
                                    )
                                valueColor:
                                    detailColumn.checks.passed === true
                                    || String(
                                        detailColumn.checks.status || ""
                                    ).toUpperCase() === "PASS"
                                    ? Colors.green
                                    : Colors.cyan
                            }

                            EvidenceRow {
                                width: parent.width
                                label: "RUNS"
                                value:
                                    detailColumn.runSummary.total !== undefined
                                    ? String(
                                        detailColumn.runSummary.success || 0
                                      )
                                      + " SUCCESS / "
                                      + String(
                                          detailColumn.runSummary.total || 0
                                      )
                                      + " TOTAL"
                                    : ""
                            }

                            EvidenceRow {
                                width: parent.width
                                label: "REHEARSAL"
                                value: String(
                                    detailColumn.rehearsal.status || ""
                                )
                                valueColor:
                                    String(
                                        detailColumn.rehearsal.status || ""
                                    ) === "CONFLICTS"
                                    ? Colors.red
                                    : String(
                                        detailColumn.rehearsal.status || ""
                                    ) === "CLEAN_MERGE"
                                    ? Colors.green
                                    : Colors.cyan
                            }

                            EvidenceRow {
                                width: parent.width
                                label: "POST-OP"
                                value: String(
                                    detailColumn.postOp.status || ""
                                )
                                valueColor:
                                    String(
                                        detailColumn.postOp.status || ""
                                    ) === "POST_OP_CLEAN"
                                    ? Colors.green
                                    : Colors.cyan
                            }

                            Rectangle {
                                width: parent.width
                                height: 1
                                color: Colors.orange
                                opacity: 0.52
                            }

                            GohuText {
                                width: parent.width
                                text: "REASON"
                                font.pixelSize: 10
                                color: Colors.magenta
                            }

                            GohuText {
                                width: parent.width
                                text:
                                    root.eventReason(detailColumn.event)
                                    || "NO RECORDED REASON"
                                font.pixelSize: 11
                                color: Colors.white
                                wrapMode: Text.Wrap
                            }

                            GohuText {
                                width: parent.width
                                visible:
                                    String(
                                        detailColumn.checks.reason || ""
                                    ).length > 0
                                text:
                                    "CHECK // "
                                    + String(
                                        detailColumn.checks.reason || ""
                                    )
                                font.pixelSize: 10
                                color: Colors.cyan
                                wrapMode: Text.Wrap
                            }
                        }
                    }
                }
            }
        }
    }
}
