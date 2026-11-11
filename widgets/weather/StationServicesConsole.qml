import QtQuick
import "../../components"
import "../../services/weather/WeatherRuntimePolicy.js" as RuntimePolicy
import "StationSubjectHeaderGeometry.js" as HeaderGeometry

// Canonical SERVICES terminal presentation reused across HOME, EARTH, MEDIA.
// Source snapshots arrive as data props; no fetching, storage, or service ownership.
Rectangle {
    id: services
    objectName: "station-services-console"
    color: Colors.black
    clip: true

    property string familyLabel: "WEATHER"
    // MEDIA already owns a fixed C44 title and two contextual controls.
    property bool embeddedHeader: false
    property string statusScope: familyLabel
    property string headerStatus: ""
    property var runtimeRows: []
    // Directory entries are source inventories, NOT live runtime reports.
    property var directoryRows: []
    // For HOME these are the original six source-health cards, reduced in size.
    property var customCards: []
    property bool homeCards: false
    property string selectedServiceId: ""
    property string selectedDirectoryId: ""

    readonly property var summary: RuntimePolicy.summarizeRows(runtimeRows)
    readonly property var selectedDirectoryRow: {
        for (let i = 0; i < directoryRows.length; i++)
            if (String(directoryRows[i].id) === selectedDirectoryId)
                return directoryRows[i];
        return null;
    }
    readonly property var selectedRow: {
        if (selectedDirectoryId !== "") return null;
        for (let i = 0; i < runtimeRows.length; i++)
            if (runtimeRows[i].id === selectedServiceId) return runtimeRows[i];
        return runtimeRows.length ? runtimeRows[0] : null;
    }
    readonly property var metricRows: customCards.length > 0 ? customCards : [
        {label:"READY",value:String(summary.ready),color:Colors.cyan},
        {label:"READING",value:String(summary.loading),color:Colors.orange},
        {label:"CACHE",value:String(summary.cached),color:Colors.blue},
        {label:"STALE",value:String(summary.stale),color:Colors.yellow},
        {label:"OFFLINE",value:String(summary.offline),color:Colors.red},
        {label:"ERROR",value:String(summary.problem),color:Colors.red}
    ]

    function rowColor(row) {
        switch (RuntimePolicy.statusToken(row)) {
        case "red": return Colors.red;
        case "yellow": return Colors.yellow;
        case "orange": return Colors.orange;
        case "magenta": return Colors.magenta;
        case "blue": return Colors.blue;
        case "green": return Colors.green;
        case "cyan": return Colors.cyan;
        default: return Colors.white;
        }
    }

    Column {
        id: fixedTop
        objectName: "services-console-fixed-header"
        x: HeaderGeometry.inset
        y: services.embeddedHeader ? 0 : HeaderGeometry.inset
        width: Math.max(0,services.width - 2*HeaderGeometry.inset)
        spacing: 0

        Row {
            width: parent.width
            height: services.embeddedHeader ? 0 : HeaderGeometry.titleHeight
            visible: !services.embeddedHeader
            spacing: 4
            GohuText {
                width: Math.max(1,parent.width-129)
                height: parent.height
                verticalAlignment: Text.AlignVCenter
                text: services.familyLabel + " // SERVICES"
                color: Colors.magenta
                font.pixelSize: 12
                elide: Text.ElideRight
            }
            QuietText {
                width: 125
                height: parent.height
                verticalAlignment: Text.AlignVCenter
                horizontalAlignment: Text.AlignRight
                text: services.headerStatus !== ""
                      ? services.headerStatus : "READY // " + services.summary.ready
                      + "/" + services.summary.total
                color: Colors.cyan
                font.pixelSize: 9
                elide: Text.ElideRight
            }
        }

        Item { width: parent.width; height: services.embeddedHeader ? 0 : HeaderGeometry.titleToTabs }

        Row {
            id: statusStrips
            objectName: "services-console-status-strips"
            width: parent.width
            visible: !services.embeddedHeader
            height: services.embeddedHeader ? 0 : HeaderGeometry.tabHeight
            spacing: HeaderGeometry.tabSpacing
            Rectangle {
                width: HeaderGeometry.buttonWidth(statusStrips.width,2)
                height: parent.height
                color: Colors.dark
                border.width: 1
                border.color: Colors.cyan
                GohuText {
                    anchors.centerIn: parent
                    width: Math.max(1,parent.width-8)
                    text: "LIVE FEED // " + services.statusScope
                    color: Colors.cyan
                    font.pixelSize: 9
                    horizontalAlignment: Text.AlignHCenter
                    elide: Text.ElideRight
                }
            }
            Rectangle {
                width: HeaderGeometry.buttonWidth(statusStrips.width,2)
                height: parent.height
                color: Colors.dark
                border.width: 1
                border.color: Colors.magenta
                GohuText {
                    anchors.centerIn: parent
                    width: Math.max(1,parent.width-8)
                    text: "SOURCE DIRECTORY // "
                          + (services.summary.total + services.directoryRows.length)
                    color: Colors.magenta
                    font.pixelSize: 9
                    horizontalAlignment: Text.AlignHCenter
                    elide: Text.ElideRight
                }
            }
        }

        Item {
            width: parent.width
            height: services.embeddedHeader ? 0
                    : HeaderGeometry.tabsToRule + HeaderGeometry.ruleHeight
            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: HeaderGeometry.ruleHeight
                color: Colors.cyan
            }
        }

        Item { width: parent.width; height: services.embeddedHeader ? 0 : HeaderGeometry.ruleToContent }

        Grid {
            id: metrics
            objectName: "services-console-summary-cards"
            width: parent.width
            height: services.homeCards ? 91 : 65
            columns: 3
            columnSpacing: 3
            rowSpacing: 3
            Repeater {
                model: services.metricRows
                delegate: Item {
                    id: metricEntry
                    required property var modelData
                    width: Math.max(1,(metrics.width-2*metrics.columnSpacing)/3)
                    height: services.homeCards ? 44 : 31
                    Rectangle {
                        anchors.fill: parent
                        visible: !services.homeCards
                        color: Colors.dark
                        border.width: 1
                        border.color: metricEntry.modelData.color || Colors.cyan
                        Column {
                            anchors.fill: parent
                            anchors.margins: 3
                            spacing: 1
                            QuietText {
                                width: parent.width
                                height: 9
                                font.pixelSize: 8
                                color: metricEntry.modelData.color || Colors.cyan
                                text: metricEntry.modelData.label
                                elide: Text.ElideRight
                            }
                            GohuText {
                                width: parent.width
                                height: 13
                                font.pixelSize: 12
                                color: Colors.white
                                text: metricEntry.modelData.value
                                elide: Text.ElideRight
                            }
                        }
                    }
                    StationHomeMetricCard {
                        anchors.fill: parent
                        visible: services.homeCards
                        compact: true
                        title: metricEntry.modelData.label || ""
                        valueText: metricEntry.modelData.value || "--"
                        detailText: metricEntry.modelData.detail || ""
                        footerText: metricEntry.modelData.footer || ""
                        accentColor: metricEntry.modelData.color || Colors.cyan
                        valueColor: metricEntry.modelData.color || Colors.cyan
                    }
                }
            }
        }

        Item { width: parent.width; height: 3 }

        Row {
            width: parent.width
            height: 14
            spacing: 4
            QuietText {
                width: parent.width*0.47
                height: parent.height
                text: "SERVICES " + services.summary.total
                      + " // READY " + services.summary.ready
                      + " // DIRECTORY " + services.directoryRows.length
                color: Colors.orange
                font.pixelSize: 8
                elide: Text.ElideRight
            }
            QuietText {
                width: parent.width*0.52
                height: parent.height
                horizontalAlignment: Text.AlignRight
                text: "FRESHNESS // RX / OBS // CADENCE"
                color: Colors.cyan
                font.pixelSize: 8
                elide: Text.ElideRight
            }
        }
    }

    // Both sections remain in one dossier; MEDIA's legacy contextual tabs
    // jump to the appropriate section without hiding data or duplicating feeds.
    function focusDirectory() {
        if (directoryRows.length > 0)
            detailScroll.contentY = Math.min(
                Math.max(0,detailScroll.contentHeight-detailScroll.height),
                Math.max(0,directoryHeading.y));
    }
    function focusRuntime() { detailScroll.contentY = 0; }

    Flickable {
        id: detailScroll
        objectName: "services-console-detail-scroll"
        anchors.left: fixedTop.left
        anchors.right: fixedTop.right
        anchors.top: fixedTop.bottom
        anchors.topMargin: 2
        anchors.bottom: selectedReport.top
        anchors.bottomMargin: 3
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        contentWidth: width
        contentHeight: Math.max(height, serviceRows.implicitHeight+2)

        Column {
            id: serviceRows
            objectName: "services-console-runtime-rows"
            width: detailScroll.width
            spacing: 1

            Repeater {
                model: services.runtimeRows
                delegate: Rectangle {
                    id: entry
                    required property var modelData
                    width: serviceRows.width
                    height: 23
                    readonly property bool isSelected:
                        services.selectedRow
                        && services.selectedRow.id === modelData.id
                    color: isSelected ? Colors.dark : Colors.black
                    border.width: 1
                    border.color: isSelected ? Colors.magenta : Colors.blue

                    Row {
                        anchors.fill: parent
                        anchors.leftMargin: 4
                        anchors.rightMargin: 4
                        spacing: 3
                        GohuText {
                            width: Math.max(1,parent.width*0.33)
                            height: parent.height
                            verticalAlignment: Text.AlignVCenter
                            text: entry.modelData.label
                            color: Colors.white
                            font.pixelSize: 8
                            elide: Text.ElideRight
                        }
                        GohuText {
                            width: Math.max(1,parent.width*0.25)
                            height: parent.height
                            verticalAlignment: Text.AlignVCenter
                            text: RuntimePolicy.rowStateLabel(entry.modelData)
                            color: services.rowColor(entry.modelData)
                            font.pixelSize: 8
                            elide: Text.ElideRight
                        }
                        SecondaryText {
                            width: Math.max(1,parent.width*0.27)
                            height: parent.height
                            verticalAlignment: Text.AlignVCenter
                            text: RuntimePolicy.rowAgeLabel(entry.modelData)
                            font.pixelSize: 8
                            elide: Text.ElideRight
                        }
                        QuietText {
                            width: Math.max(1,parent.width*0.11)
                            height: parent.height
                            verticalAlignment: Text.AlignVCenter
                            horizontalAlignment: Text.AlignRight
                            text: RuntimePolicy.cadenceLabel(entry.modelData)
                            color: Colors.cyan
                            font.pixelSize: 8
                            elide: Text.ElideRight
                        }
                    }
                    TapHandler {
                        onTapped: {
                            services.selectedDirectoryId = "";
                            services.selectedServiceId = entry.modelData.id;
                        }
                    }
                    HoverHandler { cursorShape: Qt.PointingHandCursor }
                }
            }
            QuietText {
                id: directoryHeading
                objectName: "services-console-directory-heading"
                width: parent.width
                height: services.directoryRows.length > 0 ? 14 : 0
                visible: services.directoryRows.length > 0
                color: Colors.orange
                font.pixelSize: 8
                text: "SOURCE DIRECTORY // OWNERSHIP / ROUTES // NOT LIVE HEALTH PROBES"
                elide: Text.ElideRight
            }
            Repeater {
                model: services.directoryRows
                delegate: Rectangle {
                    id: directoryEntry
                    required property var modelData
                    width: serviceRows.width
                    height: 29
                    color: services.selectedDirectoryId === String(modelData.id)
                        ? Colors.dark : Colors.black
                    border.width: 1
                    border.color: services.selectedDirectoryId === String(modelData.id)
                        ? Colors.magenta : Colors.blue
                    Column {
                        anchors.fill: parent
                        anchors.margins: 3
                        spacing: 2
                        GohuText {
                            width: parent.width
                            height: 10
                            text: (directoryEntry.modelData.name || "--")
                                + " // " + (directoryEntry.modelData.state || "--")
                            font.pixelSize: 8
                            color: Colors.white
                            elide: Text.ElideRight
                        }
                        QuietText {
                            width: parent.width
                            height: 9
                            text: (directoryEntry.modelData.owner || "")
                                + " // " + (directoryEntry.modelData.detail || "")
                            font.pixelSize: 8
                            color: Colors.cyan
                            elide: Text.ElideRight
                        }
                    }
                    TapHandler {
                        onTapped: {
                            services.selectedDirectoryId = String(directoryEntry.modelData.id);
                            services.selectedServiceId = "";
                        }
                    }
                    HoverHandler { cursorShape: Qt.PointingHandCursor }
                }
            }
        }
    }

    NeonScrollBar {
        flickable: detailScroll
        handleStyle: "star"
        geometryHost: services
        visible: scrollable
    }

    Rectangle {
        id: selectedReport
        objectName: "services-console-selected-report"
        anchors.left: fixedTop.left
        anchors.right: fixedTop.right
        anchors.bottom: parent.bottom
        anchors.bottomMargin: HeaderGeometry.inset
        height: 42
        color: Colors.dark
        border.width: 1
        border.color: Colors.magenta
        Column {
            anchors.fill: parent
            anchors.margins: 4
            spacing: 2
            QuietText {
                width: parent.width
                height: 10
                text: "REPORT // " + (services.selectedDirectoryRow
                      ? services.selectedDirectoryRow.name
                      : services.selectedRow ? services.selectedRow.label : "NO SERVICE")
                color: Colors.magenta
                font.pixelSize: 8
                elide: Text.ElideRight
            }
            GohuText {
                width: parent.width
                height: 11
                text: services.selectedDirectoryRow
                      ? "SOURCE DIRECTORY // " + (services.selectedDirectoryRow.state || "UNVERIFIED")
                      : services.selectedRow
                      ? RuntimePolicy.rowStateLabel(services.selectedRow)
                        + " // " + RuntimePolicy.rowAgeLabel(services.selectedRow)
                      : "NO CURRENT SERVICE RECORD"
                color: services.selectedDirectoryRow ? Colors.orange
                       : services.selectedRow ? services.rowColor(services.selectedRow)
                       : Colors.orange
                font.pixelSize: 9
                elide: Text.ElideRight
            }
            QuietText {
                width: parent.width
                height: 10
                text: services.selectedDirectoryRow
                      ? "OWNER " + (services.selectedDirectoryRow.owner || "--")
                        + " // " + (services.selectedDirectoryRow.detail || "")
                      : services.selectedRow
                      ? "CADENCE " + RuntimePolicy.cadenceLabel(services.selectedRow)
                        + " // " + RuntimePolicy.retentionLabel(services.selectedRow)
                        + (services.selectedRow.detail
                           ? " // " + services.selectedRow.detail : "")
                      : "READ ONLY // EXISTING PROVIDER SNAPSHOTS"
                color: Colors.cyan
                font.pixelSize: 8
                elide: Text.ElideRight
            }
        }
    }
}
