import QtQuick
import "../../../components" as Apollo

// Deterministic disposable visual fixture for eight lunar phases at
// real SKY and dock scales. Never reads weather/location/network data.
Rectangle {
    id: matrix
    width: 800
    height: 330
    color: "#1B0623"

    readonly property var phases: [
        "new", "waxing-crescent", "first-quarter", "waxing-gibbous",
        "full", "waning-gibbous", "last-quarter", "waning-crescent"
    ]

    Grid {
        anchors.fill: parent
        columns: 8
        columnSpacing: 0
        rowSpacing: 0

        Repeater {
            model: 24
            delegate: Item {
                required property int index
                readonly property int rowIndex: Math.floor(index / 8)
                readonly property string phase: matrix.phases[index % 8]
                width: 100
                height: 110

                Apollo.WeatherCelestialGlyph {
                    id: moon
                    x: (parent.width - width) / 2
                    y: 8
                    width: parent.rowIndex === 2 ? 40 : 80
                    height: width
                    solar: "night"
                    mode: parent.rowIndex === 0 ? "moon" : "night-weather"
                    weatherKind: parent.rowIndex === 1 ? "cloud" : "clear"
                    moonPhase: parent.phase
                    ink: "#ED981A"
                }

                Text {
                    anchors.top: moon.bottom
                    anchors.topMargin: 3
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: parent.phase
                    font.pixelSize: 8
                    color: "#DCF3FA"
                }
            }
        }
    }
}
