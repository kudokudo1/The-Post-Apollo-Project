import QtQuick 6.5
import QtQuick.Window 6.5
import QtLocation 6.5
import QtPositioning 6.5
import MapLibre 3.0

// Isolated standalone proof, not loaded by shell.qml.
// Offline mode uses explicitly synthetic geometry, not real roads or hubs.
// Online mode only activates with the C++ --online argument.
Window {
    id: root
    visible: true
    width: 1000
    height: 700
    color: "#1B0623"
    title: "POST-APOLLO // COMPANY VECTOR RENDERER PROBE"
    property var flint: QtPositioning.coordinate(43.0125, -83.6875)

    Plugin {
        id: mapPlugin
        name: "maplibre"
        PluginParameter {
            name: "maplibre.map.styles"
            value: probeStyleUrl
        }
    }

    MapView {
        id: mapView
        anchors.fill: parent
        map.plugin: mapPlugin
        map.center: root.flint
        map.zoomLevel: 10
        MapLibre.style: Style {}
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: 54
        color: "#1B0623"
        border.color: "#55CFCA"
        border.width: 1
        z: 10
        Text {
            anchors.left: parent.left
            anchors.leftMargin: 16
            anchors.verticalCenter: parent.verticalCenter
            text: "🏙  COMPANY // VECTOR PROOF"
            color: "#F2BE4E"
            font.pixelSize: 20
            font.bold: true
        }
        Text {
            anchors.right: parent.right
            anchors.rightMargin: 16
            anchors.verticalCenter: parent.verticalCenter
            text: probeOnline ? "ONLINE VECTOR // PILOT" : "OFFLINE SYNTHETIC FIXTURE"
            color: "#C74EC7"
            font.pixelSize: 13
        }
    }

    Column {
        anchors.right: parent.right
        anchors.rightMargin: 14
        anchors.top: parent.top
        anchors.topMargin: 72
        spacing: 5
        z: 10
        Repeater {
            model: ["+", "−", "FLINT"]
            Rectangle {
                required property string modelData
                width: 76
                height: 36
                color: "#1B0623"
                border.color: "#5B5FD4"
                border.width: 2
                Text {
                    anchors.centerIn: parent
                    color: "#DCF3FA"
                    font.pixelSize: 15
                    text: parent.modelData
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        if (modelData === "+")
                            mapView.map.zoomLevel = Math.min(17, mapView.map.zoomLevel + 1);
                        else if (modelData === "−")
                            mapView.map.zoomLevel = Math.max(2, mapView.map.zoomLevel - 1);
                        else {
                            mapView.map.center = root.flint;
                            mapView.map.zoomLevel = 10;
                        }
                    }
                }
            }
        }
    }

    Rectangle {
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 42
        color: "#1B0623"
        border.color: "#55CFCA"
        border.width: 1
        z: 10
        Text {
            anchors.centerIn: parent
            color: "#DCF3FA"
            font.pixelSize: 12
            text: probeOnline
                ? "© OpenStreetMap contributors · © OpenMapTiles · OpenFreeMap | VIEWPORT DISCLOSED"
                : "SYNTHETIC VECTOR GEOMETRY · NOT REAL STREETS OR COMPANY COVERAGE"
        }
    }
}
