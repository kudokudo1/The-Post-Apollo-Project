import QtQuick
import "../../components"

Rectangle {
    id: card

    property var eventContext: null
    property real weatherFixDistanceKm: -1
    property var radarContext: null
    property var lightningContext: null
    property var companions: []
    property color accentColor: Colors.magenta

    readonly property int companionCount:
        Array.isArray(companions) ? companions.length : 0

    visible: eventContext !== null
    width: parent ? parent.width : 0
    height: visible ? 218 + Math.min(4, companionCount) * 42 : 0

    color: Colors.dark
    border.width: 1
    border.color: accentColor

    Column {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 5

        Row {
            width: parent.width
            spacing: 10

            GohuText {
                width: Math.max(0, parent.width - 180)
                text: "CROSS-DOMAIN EVENT CONTEXT"
                font.pixelSize: 12
                color: Colors.magenta
                elide: Text.ElideRight
            }

            GohuText {
                width: 170
                text: card.eventContext
                    ? card.eventContext.sourceLabel : ""
                horizontalAlignment: Text.AlignRight
                font.pixelSize: 10
                color: card.accentColor
                elide: Text.ElideRight
            }
        }

        GohuText {
            width: parent.width
            text: card.eventContext
                ? card.eventContext.title : ""
            font.pixelSize: 13
            color: Colors.white
            elide: Text.ElideRight
        }

        QuietText {
            width: parent.width
            text: card.eventContext
                ? card.eventContext.typeLabel
                    + " // " + card.eventContext.coordinates
                    + " // " + card.eventContext.timeLabel
                : ""
            font.pixelSize: 9
            elide: Text.ElideRight
        }

        QuietText {
            width: parent.width
            text: card.weatherFixDistanceKm >= 0
                ? "WEATHER FIX // "
                    + Math.round(card.weatherFixDistanceKm)
                    + " KM FROM EVENT // DISTANCE ONLY"
                : "WEATHER FIX // POINT DISTANCE UNAVAILABLE"
            font.pixelSize: 9
            color: Colors.cyan
            elide: Text.ElideRight
        }

        GohuText {
            width: parent.width
            text: card.radarContext
                ? "MRMS // " + card.radarContext.status
                    + (card.radarContext.available
                       ? " // " + card.radarContext.frameLabel
                         + " // " + card.radarContext.timeLabel
                         + (card.radarContext.usingCache ? " // CACHE" : "")
                       : "")
                : "MRMS // NO LOADED FRAME"
            font.pixelSize: 9
            color: card.radarContext
                   && card.radarContext.covered
                   ? Colors.green : Colors.orange
            elide: Text.ElideRight
        }

        QuietText {
            width: parent.width
            text: "RADAR CONTEXT = GEOMETRIC FRAME COVERAGE ONLY // IMAGE PIXELS ARE NOT INTERPRETED"
            font.pixelSize: 8
            color: Colors.orange
            elide: Text.ElideRight
        }

        GohuText {
            width: parent.width
            text: card.lightningContext
                ? "LIGHTNING // " + card.lightningContext.status
                    + (card.lightningContext.available
                       ? " // " + card.lightningContext.windowMinutes
                         + "M DENSITY // "
                         + card.lightningContext.timeLabel
                         + (card.lightningContext.usingCache
                            ? " // CACHE" : "")
                       : "")
                : "LIGHTNING // NO LOADED LIGHTNING FRAME"
            font.pixelSize: 9
            color: card.lightningContext
                   && card.lightningContext.covered
                   ? Colors.magenta : Colors.orange
            elide: Text.ElideRight
        }

        QuietText {
            width: parent.width
            text: "LIGHTNING CONTEXT = GEOMETRIC FRAME COVERAGE ONLY // DENSITY PIXELS ARE NOT INTERPRETED"
            font.pixelSize: 8
            color: Colors.orange
            elide: Text.ElideRight
        }

        GohuText {
            width: parent.width
            text: "NEARBY INDEPENDENT MAP RECORDS // "
                + card.companionCount
                + " WITHIN 250 KM"
            font.pixelSize: 9
            color: Colors.cyan
        }

        Repeater {
            model: Array.isArray(card.companions)
                ? card.companions.slice(0, 4) : []

            delegate: Rectangle {
                required property var modelData
                width: card.width - 20
                height: 37
                color: Colors.black
                border.width: 1
                border.color: Colors.blue

                Row {
                    anchors.fill: parent
                    anchors.margins: 6
                    spacing: 8

                    GohuText {
                        width: 88
                        text: modelData.sourceLabel
                        font.pixelSize: 9
                        color: Colors.magenta
                        elide: Text.ElideRight
                    }

                    GohuText {
                        width: 70
                        text: Math.round(modelData.distanceKm) + " KM"
                        font.pixelSize: 9
                        color: Colors.cyan
                    }

                    QuietText {
                        width: Math.max(0, parent.width - 174)
                        text: modelData.typeLabel
                            + " // " + modelData.title
                        font.pixelSize: 8
                        elide: Text.ElideRight
                    }
                }
            }
        }

        QuietText {
            width: parent.width
            text: "NEARBY ≠ SAME EVENT // SOURCE RECORDS REMAIN INDEPENDENT EVIDENCE"
            font.pixelSize: 8
            color: Colors.orange
            elide: Text.ElideRight
        }
    }
}
