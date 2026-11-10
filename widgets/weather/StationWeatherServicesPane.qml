import QtQuick
import "../../components"
import "../../services/weather/WeatherRuntimePolicy.js" as RuntimePolicy
import "StationSubjectHeaderGeometry.js" as HeaderGeometry

// W5 // WEATHER's first canonical SERVICES visual pass.
// Read-only view over the original StationSky and StationGround runtime arrays.
// The sources/collectors and their activation policy stay with their owners.
Rectangle {
    id: services
    objectName: "weather-w5-services-pane"
    color: Colors.black
    clip: true

    property var skyRows: []
    property var groundRows: []
    property string selectedServiceId: ""

    readonly property var runtimeRows: {
        const rows = [];
        const ids = {};
        const inputs = [skyRows, groundRows];
        for (let group = 0; group < inputs.length; group++) {
            const source = Array.isArray(inputs[group]) ? inputs[group] : [];
            for (let i = 0; i < source.length; i++) {
                const row = source[i];
                if (!row) continue;
                const id = String(row.id || "");
                if (id !== "" && Object.prototype.hasOwnProperty.call(ids,id))
                    continue;
                if (id !== "") ids[id] = true;
                rows.push(row);
            }
        }
        return rows;
    }
    readonly property var summary: RuntimePolicy.summarizeRows(runtimeRows)
    readonly property var selectedRow: {
        for (let i = 0; i < runtimeRows.length; i++)
            if (runtimeRows[i].id === selectedServiceId) return runtimeRows[i];
        return runtimeRows.length ? runtimeRows[0] : null;
    }
    readonly property var metricRows: [
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
        objectName: "weather-w5-fixed-header"
        x: HeaderGeometry.inset
        y: HeaderGeometry.inset
        width: Math.max(0,services.width - 2*HeaderGeometry.inset)
        spacing: 0

        Row {
            width: parent.width
            height: HeaderGeometry.titleHeight
            spacing: 4
            GohuText {
                width: Math.max(1,parent.width-129)
                height: parent.height
                verticalAlignment: Text.AlignVCenter
                text: "WEATHER // SERVICES"
                color: Colors.magenta
                font.pixelSize: 12
                elide: Text.ElideRight
            }
            QuietText {
                width: 125
                height: parent.height
                verticalAlignment: Text.AlignVCenter
                horizontalAlignment: Text.AlignRight
                text: "READY // " + services.summary.ready
                      + "/" + services.summary.total
                color: Colors.cyan
                font.pixelSize: 9
                elide: Text.ElideRight
            }
        }

        Item { width: parent.width; height: HeaderGeometry.titleToTabs }

        Row {
            id: statusStrips
            objectName: "weather-w5-status-strips"
            width: parent.width
            height: HeaderGeometry.tabHeight
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
                    text: "LIVE FEED // WEATHER"
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
                    text: "SOURCE DIRECTORY // " + services.summary.total
                    color: Colors.magenta
                    font.pixelSize: 9
                    horizontalAlignment: Text.AlignHCenter
                    elide: Text.ElideRight
                }
            }
        }

        Item {
            width: parent.width
            height: HeaderGeometry.tabsToRule + HeaderGeometry.ruleHeight
            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: HeaderGeometry.ruleHeight
                color: Colors.cyan
            }
        }

        Item { width: parent.width; height: HeaderGeometry.ruleToContent }

        Grid {
            id: metrics
            objectName: "weather-w5-summary-cards"
            width: parent.width
            height: 65
            columns: 3
            columnSpacing: 3
            rowSpacing: 3
            Repeater {
                model: services.metricRows
                delegate: Rectangle {
                    id: summaryCard
                    required property var modelData
                    width: Math.max(1,(metrics.width-2*metrics.columnSpacing)/3)
                    height: 31
                    color: Colors.dark
                    border.width: 1
                    border.color: modelData.color
                    Column {
                        anchors.fill: parent
                        anchors.margins: 3
                        spacing: 1
                        QuietText {
                            width: parent.width
                            height: 9
                            font.pixelSize: 8
                            color: summaryCard.modelData.color
                            text: summaryCard.modelData.label
                            elide: Text.ElideRight
                        }
                        GohuText {
                            width: parent.width
                            height: 13
                            font.pixelSize: 12
                            color: Colors.white
                            text: summaryCard.modelData.value
                            elide: Text.ElideRight
                        }
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

    Flickable {
        id: detailScroll
        objectName: "weather-w5-detail-scroll"
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
            objectName: "weather-w5-runtime-rows"
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
                        onTapped: services.selectedServiceId = entry.modelData.id
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
        objectName: "weather-w5-selected-report"
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
                text: "REPORT // " + (services.selectedRow
                      ? services.selectedRow.label : "NO SERVICE")
                color: Colors.magenta
                font.pixelSize: 8
                elide: Text.ElideRight
            }
            GohuText {
                width: parent.width
                height: 11
                text: services.selectedRow
                      ? RuntimePolicy.rowStateLabel(services.selectedRow)
                        + " // " + RuntimePolicy.rowAgeLabel(services.selectedRow)
                      : "NO CURRENT SERVICE RECORD"
                color: services.selectedRow
                       ? services.rowColor(services.selectedRow) : Colors.orange
                font.pixelSize: 9
                elide: Text.ElideRight
            }
            QuietText {
                width: parent.width
                height: 10
                text: services.selectedRow
                      ? "CADENCE " + RuntimePolicy.cadenceLabel(services.selectedRow)
                        + " // " + RuntimePolicy.retentionLabel(services.selectedRow)
                        + (services.selectedRow.detail
                           ? " // " + services.selectedRow.detail : "")
                      : "READ ONLY // EXISTING WEATHER PROVIDERS"
                color: Colors.cyan
                font.pixelSize: 8
                elide: Text.ElideRight
            }
        }
    }
}
