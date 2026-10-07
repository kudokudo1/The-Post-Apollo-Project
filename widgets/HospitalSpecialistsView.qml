import QtQuick
import Quickshell
import qs.components

Item {
    id: root

    required property var registryService

    property string filterMode: "ALL"
    property int selectedIndex: -1

    readonly property var displayedSpecialists: {
        const source =
            root.registryService
            && Array.isArray(root.registryService.specialists)
            ? root.registryService.specialists
            : [];

        if (root.filterMode === "READY")
            return source.filter(function(row) {
                return String((row || {}).presence || "") === "READY";
            });

        if (root.filterMode === "OFFLINE")
            return source.filter(function(row) {
                return String((row || {}).presence || "") === "OFFLINE";
            });

        return source;
    }

    readonly property var selectedSpecialist: {
        if (selectedIndex < 0
                || selectedIndex >= displayedSpecialists.length)
            return null;

        return displayedSpecialists[selectedIndex] || null;
    }

    function presenceColor(value) {
        const state = String(value || "").toUpperCase();

        if (state === "READY")
            return Colors.green;
        if (state === "OFFLINE")
            return Colors.red;

        return Colors.orange;
    }

    function selectSpecialist(index) {
        const requested = Number(index);

        if (requested < 0 || requested >= displayedSpecialists.length)
            return false;

        selectedIndex = requested;
        return true;
    }

    function selectSpecialistById(value) {
        const wanted = String(value || "").trim();

        if (!wanted)
            return false;

        filterMode = "ALL";

        const rows =
            root.registryService
            && Array.isArray(root.registryService.specialists)
            ? root.registryService.specialists
            : [];

        for (let i = 0; i < rows.length; ++i) {
            if (String((rows[i] || {}).id || "") !== wanted)
                continue;

            selectedIndex = i;
            return true;
        }

        return false;
    }

    onDisplayedSpecialistsChanged: {
        if (displayedSpecialists.length === 0)
            selectedIndex = -1;
        else if (selectedIndex < 0
                || selectedIndex >= displayedSpecialists.length)
            selectedIndex = 0;
    }

    component StaffButton: Rectangle {
        id: button

        property string label: ""
        property bool enabledAction: true
        property bool selectedAction: false

        signal triggered()

        height: 34
        color:
            !enabledAction
            ? Colors.black
            : selectedAction
            ? Colors.yellow
            : mouse.pressed
            ? Colors.orange
            : Colors.black
        border.width:
            selectedAction || mouse.containsMouse
            ? 2 : 1
        border.color:
            !enabledAction
            ? Colors.cyan
            : selectedAction
            ? Colors.orange
            : mouse.containsMouse
            ? Colors.orange
            : Colors.cyan

        GohuText {
            anchors.centerIn: parent
            text: button.label
            font.pixelSize: 11
            color:
                button.selectedAction
                ? Colors.magenta
                : mouse.pressed
                ? Colors.black
                : Colors.cyan
            opacity: button.enabledAction ? 1.0 : 0.34
        }

        MouseArea {
            id: mouse

            anchors.fill: parent
            enabled: button.enabledAction
            hoverEnabled: true
            cursorShape:
                enabled
                ? Qt.PointingHandCursor
                : Qt.ArrowCursor

            onClicked: button.triggered()
        }
    }

    component MetricBox: Rectangle {
        property string label: ""
        property string value: "0"
        property color accent: Colors.cyan

        height: 58
        color: Colors.black
        border.width: 1
        border.color: accent

        Column {
            anchors.centerIn: parent
            spacing: 3

            GohuText {
                anchors.horizontalCenter: parent.horizontalCenter
                text: parent.parent.value
                font.pixelSize: 16
                color: parent.parent.accent
            }

            GohuText {
                anchors.horizontalCenter: parent.horizontalCenter
                text: parent.parent.label
                font.pixelSize: 9
                color: Colors.white
                opacity: 0.78
            }
        }
    }

    component DetailRow: Row {
        property string label: ""
        property string value: ""
        property color valueColor: Colors.cyan

        height: 26
        spacing: 10

        GohuText {
            width: 92
            anchors.verticalCenter: parent.verticalCenter
            text: parent.label
            font.pixelSize: 10
            color: Colors.magenta
        }

        GohuText {
            width: parent.width - 102
            anchors.verticalCenter: parent.verticalCenter
            text: parent.value || "—"
            font.pixelSize: 11
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
            acceptedButtons: Qt.AllButtons
            hoverEnabled: true

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
                    width: parent.width - 344
                    anchors.verticalCenter: parent.verticalCenter
                    text: "STAFF // SPECIALIST REGISTRY"
                    font.pixelSize: 13
                    color: Colors.magenta
                    elide: Text.ElideRight
                }

                StaffButton {
                    width: 58
                    label: "ALL"
                    selectedAction: root.filterMode === "ALL"
                    onTriggered: root.filterMode = "ALL"
                }

                StaffButton {
                    width: 68
                    label: "READY"
                    selectedAction: root.filterMode === "READY"
                    onTriggered: root.filterMode = "READY"
                }

                StaffButton {
                    width: 78
                    label: "OFFLINE"
                    selectedAction: root.filterMode === "OFFLINE"
                    onTriggered: root.filterMode = "OFFLINE"
                }

                StaffButton {
                    width: 108
                    label:
                        root.registryService.probing
                        ? "CHECKING"
                        : "REFRESH"
                    enabledAction: !root.registryService.probing
                    onTriggered:
                        root.registryService.refreshPresence()
                }
            }

            Row {
                width: parent.width
                height: 58
                spacing: 6

                MetricBox {
                    width: (parent.width - 18) / 4
                    label: "STAFF"
                    value:
                        String(root.registryService.specialistCount)
                    accent: Colors.cyan
                }

                MetricBox {
                    width: (parent.width - 18) / 4
                    label: "READY"
                    value:
                        String(root.registryService.readyCount)
                    accent:
                        root.registryService.readyCount > 0
                        ? Colors.green
                        : Colors.cyan
                }

                MetricBox {
                    width: (parent.width - 18) / 4
                    label: "OFFLINE"
                    value:
                        String(root.registryService.offlineCount)
                    accent:
                        root.registryService.offlineCount > 0
                        ? Colors.red
                        : Colors.green
                }

                MetricBox {
                    width: (parent.width - 18) / 4
                    label: "CALLABLE"
                    value:
                        String(root.registryService.callableCount)
                    accent:
                        root.registryService.callableCount > 0
                        ? Colors.orange
                        : Colors.cyan
                }
            }

            Rectangle {
                width: parent.width
                height: 34
                color: Colors.black
                border.width: 1
                border.color:
                    root.registryService.lastError
                    ? Colors.red
                    : Colors.cyan

                GohuText {
                    anchors {
                        fill: parent
                        margins: 7
                    }

                    text:
                        root.registryService.lastError
                        ? root.registryService.lastError
                        : root.registryService.probing
                        ? "PRESENCE // CHECKING SPECIALIST ENDPOINTS"
                        : root.registryService.lastRefreshedAt
                        ? "PRESENCE // LAST CHECK "
                          + root.registryService.lastRefreshedAt
                        : "PRESENCE // NOT CHECKED"
                    font.pixelSize: 10
                    color:
                        root.registryService.lastError
                        ? Colors.red
                        : root.registryService.probing
                        ? Colors.orange
                        : Colors.cyan
                    elide: Text.ElideRight
                }
            }

            Row {
                width: parent.width
                height: parent.height - 160
                spacing: 10

                Rectangle {
                    width: (parent.width - 10) * 0.58
                    height: parent.height
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.orange

                    Flickable {
                        id: staffList

                        anchors {
                            fill: parent
                            margins: 6
                        }

                        clip: true
                        contentWidth: width
                        contentHeight: staffColumn.height
                        boundsBehavior: Flickable.StopAtBounds

                        Column {
                            id: staffColumn

                            width: staffList.width
                            spacing: 6

                            Repeater {
                                model: root.displayedSpecialists

                                Rectangle {
                                    id: specialistCard

                                    required property int index
                                    required property var modelData

                                    readonly property bool selected:
                                        root.selectedIndex === index
                                    readonly property color stateColor:
                                        root.presenceColor(
                                            modelData.presence
                                        )

                                    width: staffColumn.width
                                    height: 92
                                    color:
                                        selected
                                        ? Colors.yellow
                                        : Colors.dark
                                    border.width:
                                        selected
                                        || staffMouse.containsMouse
                                        ? 2 : 1
                                    border.color:
                                        selected
                                        ? Colors.orange
                                        : stateColor

                                    Column {
                                        anchors {
                                            fill: parent
                                            margins: 8
                                        }
                                        spacing: 5

                                        Row {
                                            width: parent.width

                                            GohuText {
                                                width: parent.width * 0.58
                                                text:
                                                    String(
                                                        specialistCard
                                                            .modelData.name
                                                        || "SPECIALIST"
                                                    )
                                                font.pixelSize: 12
                                                color:
                                                    specialistCard.selected
                                                    ? Colors.magenta
                                                    : Colors.cyan
                                                elide: Text.ElideRight
                                            }

                                            GohuText {
                                                width: parent.width * 0.42
                                                text:
                                                    String(
                                                        specialistCard
                                                            .modelData.presence
                                                        || "UNKNOWN"
                                                    )
                                                font.pixelSize: 11
                                                color:
                                                    specialistCard.stateColor
                                                horizontalAlignment:
                                                    Text.AlignRight
                                                elide: Text.ElideRight
                                            }
                                        }

                                        GohuText {
                                            width: parent.width
                                            text:
                                                String(
                                                    specialistCard
                                                        .modelData.role
                                                    || "SPECIALIST"
                                                )
                                            font.pixelSize: 11
                                            color: Colors.white
                                            elide: Text.ElideRight
                                        }

                                        GohuText {
                                            width: parent.width
                                            text:
                                                String(
                                                    specialistCard
                                                        .modelData.provider
                                                    || "UNSPECIFIED"
                                                )
                                                + " // "
                                                + String(
                                                    specialistCard
                                                        .modelData.transport
                                                    || "UNKNOWN"
                                                )
                                                + " // "
                                                + String(
                                                    specialistCard
                                                        .modelData.assignment
                                                    || "UNASSIGNED"
                                                )
                                            font.pixelSize: 10
                                            color: Colors.orange
                                            elide: Text.ElideRight
                                        }
                                    }

                                    MouseArea {
                                        id: staffMouse

                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor

                                        onClicked:
                                            root.selectSpecialist(index)
                                    }
                                }
                            }

                            GohuText {
                                width: parent.width
                                visible:
                                    root.displayedSpecialists.length === 0
                                text:
                                    root.filterMode === "ALL"
                                    ? "NO SPECIALISTS REGISTERED"
                                    : "NO SPECIALISTS MATCH THIS PRESENCE FILTER"
                                font.pixelSize: 11
                                color: Colors.cyan
                                opacity: 0.68
                                horizontalAlignment: Text.AlignHCenter
                            }
                        }
                    }
                }

                Rectangle {
                    width: (parent.width - 10) * 0.42
                    height: parent.height
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.cyan

                    Flickable {
                        id: detailFlick

                        anchors {
                            fill: parent
                            margins: 10
                        }

                        clip: true
                        contentWidth: width
                        contentHeight: detailColumn.height
                        boundsBehavior: Flickable.StopAtBounds

                        Column {
                            id: detailColumn

                            width: detailFlick.width
                            spacing: 8

                            readonly property var specialist:
                                root.selectedSpecialist || ({})

                            GohuText {
                                width: parent.width
                                text:
                                    root.selectedSpecialist
                                    ? "SPECIALIST // "
                                      + String(
                                          detailColumn.specialist.name
                                          || "UNKNOWN"
                                      )
                                    : "SPECIALIST // SELECT STAFF"
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

                            DetailRow {
                                width: parent.width
                                label: "PRESENCE"
                                value:
                                    String(
                                        detailColumn
                                            .specialist.presence
                                        || "UNKNOWN"
                                    )
                                valueColor:
                                    root.presenceColor(
                                        detailColumn
                                            .specialist.presence
                                    )
                            }

                            DetailRow {
                                width: parent.width
                                label: "ROLE"
                                value:
                                    String(
                                        detailColumn.specialist.role
                                        || ""
                                    )
                            }

                            DetailRow {
                                width: parent.width
                                label: "PROVIDER"
                                value:
                                    String(
                                        detailColumn
                                            .specialist.provider
                                        || ""
                                    )
                            }

                            DetailRow {
                                width: parent.width
                                label: "TYPE"
                                value:
                                    String(
                                        detailColumn.specialist.kind
                                        || ""
                                    )
                                    + " // "
                                    + String(
                                        detailColumn
                                            .specialist.transport
                                        || ""
                                    )
                            }

                            DetailRow {
                                width: parent.width
                                label: "ASSIGNMENT"
                                value:
                                    String(
                                        detailColumn
                                            .specialist.assignment
                                        || "UNASSIGNED"
                                    )
                                valueColor: Colors.orange
                            }

                            DetailRow {
                                width: parent.width
                                label: "COMMAND"
                                value:
                                    String(
                                        detailColumn
                                            .specialist.command
                                        || "NONE"
                                    )
                                valueColor: Colors.blue
                            }

                            DetailRow {
                                width: parent.width
                                label: "ENDPOINT"
                                value:
                                    String(
                                        detailColumn
                                            .specialist.endpoint
                                        || "NOT RESOLVED"
                                    )
                            }

                            DetailRow {
                                width: parent.width
                                label: "CALLABLE"
                                value:
                                    detailColumn.specialist.callable
                                    ? (
                                        detailColumn.specialist
                                            .presence === "READY"
                                        ? "READY FOR PHONE"
                                        : "CONFIGURED // OFFLINE"
                                      )
                                    : "NO"
                                valueColor:
                                    detailColumn.specialist.callable
                                    && detailColumn.specialist
                                        .presence === "READY"
                                    ? Colors.green
                                    : Colors.orange
                            }

                            DetailRow {
                                width: parent.width
                                label: "LAST SEEN"
                                value:
                                    String(
                                        detailColumn
                                            .specialist.lastSeen
                                        || "NOT CHECKED"
                                    )
                            }

                            Rectangle {
                                width: parent.width
                                height: 1
                                color: Colors.cyan
                                opacity: 0.42
                            }

                            GohuText {
                                width: parent.width
                                text: "CAPABILITIES"
                                font.pixelSize: 11
                                color: Colors.magenta
                            }

                            GohuText {
                                width: parent.width
                                text:
                                    Array.isArray(
                                        detailColumn
                                            .specialist.capabilities
                                    )
                                    && detailColumn
                                        .specialist.capabilities.length > 0
                                    ? detailColumn
                                        .specialist.capabilities.join(
                                            " // "
                                        )
                                    : "NONE RECORDED"
                                font.pixelSize: 11
                                color: Colors.white
                                wrapMode: Text.Wrap
                            }

                            Rectangle {
                                width: parent.width
                                height: 34
                                color: Colors.black
                                border.width: 1
                                border.color:
                                    detailColumn.specialist.callable
                                    ? Colors.orange
                                    : Colors.cyan
                                opacity:
                                    root.selectedSpecialist
                                    ? 1.0 : 0.40

                                GohuText {
                                    anchors.centerIn: parent
                                    text:
                                        !root.selectedSpecialist
                                        ? "SELECT SPECIALIST"
                                        : detailColumn
                                            .specialist.callable
                                        ? "PHONE CONTRACT // READY"
                                        : "PHONE CONTRACT // DISABLED"
                                    font.pixelSize: 11
                                    color:
                                        detailColumn
                                            .specialist.callable
                                        ? Colors.orange
                                        : Colors.cyan
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
