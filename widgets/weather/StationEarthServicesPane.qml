import QtQuick
import "../../components"
import "../../services/weather/WeatherRuntimePolicy.js" as RuntimePolicy
import "StationSubjectHeaderGeometry.js" as HeaderGeometry

// E2 // Report-only observer of the existing StationDiscovery source owner.
// No new discovery, radar, EONET, GDACS, archive or storage instance.
Rectangle {
    id: services
    objectName: "earth-e2-services-pane"
    color: Colors.black
    clip: true
    property var runtimeRows: []
    property var sourceRows: []
    property string viewMode: "runtime"
    property string selectedSourceId: ""
    readonly property var selectedSource: {
        for (var i=0;i<runtimeRows.length;i++)
            if (runtimeRows[i].id === selectedSourceId)
                return runtimeRows[i];
        return runtimeRows.length ? runtimeRows[0] : null;
    }
    readonly property int readyCount: runtimeRows.filter(function(row) {
        return row.ready === true;
    }).length

    GohuText {
        id: title
        objectName: "earth-e2-services-title"
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: HeaderGeometry.inset
        height: HeaderGeometry.titleHeight
        text: "EARTH // SERVICES"
        font.pixelSize: 12
        color: Colors.magenta
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
    Row {
        id: tabs
        objectName: "earth-e2-services-tabs"
        anchors.top: title.bottom
        anchors.topMargin: HeaderGeometry.titleToTabs
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: HeaderGeometry.inset
        anchors.rightMargin: HeaderGeometry.inset
        height: HeaderGeometry.tabHeight
        spacing: HeaderGeometry.tabSpacing
        Repeater {
            model: [{id:"runtime",label:"RUNTIME"},
                    {id:"sources",label:"SOURCE DIRECTORY"}]
            delegate: ActionButton {
                required property var modelData
                width: HeaderGeometry.buttonWidth(tabs.width,2)
                height: HeaderGeometry.tabHeight
                label: modelData.label
                labelPixelSize: 10
                contentPadding: 1
                selected: services.viewMode === modelData.id
                accentColor: Colors.cyan
                onClicked: services.viewMode = modelData.id
            }
        }
    }
    Rectangle {
        id: rule
        objectName: "earth-e2-services-divider"
        anchors.top: tabs.bottom
        anchors.topMargin: HeaderGeometry.tabsToRule
        anchors.left: tabs.left
        anchors.right: tabs.right
        height: HeaderGeometry.ruleHeight
        color: Colors.cyan
    }
    Column {
        id: report
        objectName: "earth-e2-services-body"
        anchors.top: rule.bottom
        anchors.topMargin: HeaderGeometry.ruleToContent
        anchors.left: tabs.left
        anchors.right: tabs.right
        anchors.bottom: parent.bottom
        anchors.bottomMargin: HeaderGeometry.inset
        spacing: 4

        Row {
            width: parent.width
            height: 17
            spacing: 4
            QuietText {
                width: Math.max(1,parent.width*0.64)
                text: services.viewMode === "runtime"
                    ? "LIVE SOURCES // " + services.runtimeRows.length
                    : "EXISTING SOURCE DIRECTORY // " + services.sourceRows.length
                font.pixelSize: 9
                color: Colors.cyan
                elide: Text.ElideRight
            }
            QuietText {
                width: Math.max(1,parent.width*0.35)
                horizontalAlignment: Text.AlignRight
                text: "READY " + services.readyCount + "/"
                    + services.runtimeRows.length
                font.pixelSize: 9
                color: Colors.magenta
            }
        }

        Flickable {
            id: rowScroll
            objectName: "earth-e2-service-row-scroll"
            width: parent.width
            height: Math.max(0,report.height-17-41-2*report.spacing)
            clip: true
            contentWidth: width
            contentHeight: Math.max(height, rows.y+rows.implicitHeight+4)
            boundsBehavior: Flickable.StopAtBounds

            Column {
                id: rows
                width: rowScroll.width
                y: 1
                spacing: 3
                Repeater {
                    model: services.viewMode === "runtime"
                        ? services.runtimeRows : []
                    delegate: Rectangle {
                        id: record
                        required property var modelData
                        width: rows.width
                        height: 26
                        color: services.selectedSource
                            && services.selectedSource.id === modelData.id
                            ? Colors.dark : Colors.black
                        border.width: 1
                        border.color: services.selectedSource
                            && services.selectedSource.id === modelData.id
                            ? Colors.magenta : Colors.cyan
                        Row {
                            anchors.fill: parent
                            anchors.margins: 3
                            spacing: 3
                            QuietText {
                                width: Math.max(1,parent.width*0.32)
                                text: record.modelData.label || record.modelData.id
                                font.pixelSize: 9
                                color: Colors.cyan
                                elide: Text.ElideRight
                            }
                            QuietText {
                                width: Math.max(1,parent.width*0.22)
                                text: RuntimePolicy.rowStateLabel(record.modelData)
                                font.pixelSize: 8
                                color: Colors.white
                                elide: Text.ElideRight
                            }
                            QuietText {
                                width: Math.max(1,parent.width*0.30)
                                text: RuntimePolicy.rowAgeLabel(record.modelData)
                                font.pixelSize: 8
                                color: Colors.yellow
                                elide: Text.ElideRight
                            }
                            QuietText {
                                width: Math.max(1,parent.width*0.14)
                                text: RuntimePolicy.cadenceLabel(record.modelData)
                                font.pixelSize: 8
                                color: Colors.cyan
                                elide: Text.ElideRight
                            }
                        }
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: services.selectedSourceId = record.modelData.id
                        }
                    }
                }
                Repeater {
                    model: services.viewMode === "sources"
                        ? services.sourceRows : []
                    delegate: Rectangle {
                        id: sourceEntry
                        required property var modelData
                        width: rows.width
                        height: 30
                        color: Colors.dark
                        border.color: Colors.cyan
                        border.width: 1
                        Row {
                            anchors.fill: parent
                            anchors.margins: 4
                            spacing: 5
                            QuietText {
                                width: Math.max(1,parent.width*0.61)
                                text: sourceEntry.modelData.name || "--"
                                font.pixelSize: 9
                                color: Colors.cyan
                                elide: Text.ElideRight
                            }
                            QuietText {
                                width: Math.max(1,parent.width*0.36)
                                text: sourceEntry.modelData.state || "--"
                                font.pixelSize: 9
                                color: Colors.yellow
                                elide: Text.ElideRight
                            }
                        }
                    }
                }
            }
        }

        Column {
            width: parent.width
            height: 41
            spacing: 2
            QuietText {
                width: parent.width
                text: services.viewMode === "runtime"
                    ? "SELECTED // " + (services.selectedSource
                        ? services.selectedSource.label : "--")
                      + " // " + (services.selectedSource
                        ? RuntimePolicy.rowAgeLabel(services.selectedSource)
                        : "RX --")
                    : "SOURCES SHARE THE EXISTING EARTH MAP OWNER"
                font.pixelSize: 9
                color: Colors.magenta
                elide: Text.ElideRight
            }
            QuietText {
                width: parent.width
                text: services.viewMode === "runtime"
                    ? "RX = LOCAL RECEIPT // OBS = PROVIDER SAMPLE"
                      + " // FINAL COLUMN = CADENCE"
                    : "NO DUPLICATE POLLING // MANUAL FIRE AND RADAR REQUESTS"
                font.pixelSize: 9
                color: Colors.cyan
                elide: Text.ElideRight
            }
        }
    }
}
