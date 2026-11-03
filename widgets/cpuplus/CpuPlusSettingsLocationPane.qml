import QtQuick
import "../../components"

// SETTINGS / LOCATION M0 is a presentation and navigation slice.
// No location inference, persistence, profile changes or provider calls here.
Item {
    id: locationPane

    Flickable {
        id: locationScroll
        anchors.fill: parent
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        contentWidth: width
        contentHeight: Math.max(height, contents.y + contents.implicitHeight + 12)

        Column {
            id: contents
            x: 4
            y: 8
            width: Math.max(0, locationScroll.width - 12)
            spacing: 13

            GohuText {
                text: "PLACES // LOCATION CONTEXT"
                font.pixelSize: 12
                color: Colors.cyan
            }

            QuietText {
                width: parent.width
                wrapMode: Text.WordWrap
                text: "FIRST SUBMODE // CONFIGURATION SHELL"
                font.pixelSize: 9
            }

            Repeater {
                model: [
                    {
                        "title": "⌂  HOME LOCATION",
                        "state": "NOT CONNECTED",
                        "description": "PERSISTENT DEFAULT // WILL USE A SHARED LOCATION REGISTRY",
                        "accent": Colors.orange
                    },
                    {
                        "title": "⌖  EXPLORE LOCATION",
                        "state": "NOT ACTIVE",
                        "description": "TEMPORARY PLACE // DURATION // RETURN HOME // SUBJECT OVERRIDES",
                        "accent": Colors.cyan
                    },
                    {
                        "title": "↳  SHARED CONTEXT",
                        "state": "NOT WIRED",
                        "description": "WEATHER // SKY // GROUND // MAP. EMERGENCY ALERT POINTS STAY INDEPENDENT.",
                        "accent": Colors.magenta
                    }
                ]

                delegate: Rectangle {
                    required property var modelData
                    width: contents.width
                    height: 119
                    color: Colors.black
                    border.width: 1
                    border.color: modelData.accent

                    Column {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 8

                        GohuText {
                            width: parent.width
                            text: modelData.title
                            color: modelData.accent
                            font.pixelSize: 12
                        }
                        GohuText {
                            width: parent.width
                            text: modelData.state
                            color: Colors.white
                            font.pixelSize: 11
                        }
                        QuietText {
                            width: parent.width
                            wrapMode: Text.WordWrap
                            text: modelData.description
                            font.pixelSize: 9
                        }
                    }
                }
            }

            SecondaryText {
                width: parent.width
                wrapMode: Text.WordWrap
                text: "NO LOCATION IS READ, SAVED OR CHANGED BY THIS MENU YET."
                font.pixelSize: 9
            }
        }
    }

    NeonScrollBar {
        flickable: locationScroll
        x: parent.width - width
        y: 0
        height: parent.height
        visible: scrollable
    }
}
