import QtQuick
import Quickshell
import "../components"
import QtQuick.Effects
import Qt5Compat.GraphicalEffects

Item {
    id: clockArea

    width: clockButton.width + 20
    height: clockButton.height + 46

    property bool is24Hour: false

    DockButton {
        id: clockButton

        implicitHeight: 50
        implicitWidth: 151

        contentGlowEnabled: false

        normalDockGlowColor:
            clockArea.is24Hour ? Colors.orange : Colors.cyan
        hoverDockGlowColor: normalDockGlowColor
        pressedDockGlowColor: normalDockGlowColor

        softGlowIdleOpacity: 0.40
        softGlowHoverOpacity: 0.50
        softGlowPressedOpacity: 0.60

        wideGlowIdleOpacity: 0.07
        wideGlowHoverOpacity: 0.09
        wideGlowPressedOpacity: 0.12

        SystemClock {
            id: clock
            precision: SystemClock.Seconds
        }

        Row {
            id: clockRow
            anchors.centerIn: parent
            anchors.verticalCenter: parent.verticalCenter
            spacing: 9

            Item {
                id: clockIconContainer

                implicitWidth: clockIcon.implicitWidth
                height: 20

                Text {
                    id: clockIcon
                    anchors.centerIn: parent

                    text: " ๋࣭🕰 ⭑"
                    color:
                        clockArea.is24Hour
                        ? Colors.orange
                        : Colors.cyan
                    font.pixelSize: 20
                }

                DropShadow {
                    anchors.fill: clockIcon
                    source: clockIcon

                    horizontalOffset: 0
                    verticalOffset: 0
                    radius: 14
                    samples: 15
                    z: 2

                    opacity:
                        clockButton.pressed
                        ? 1.0
                        : clockButton.hovered
                        ? 0.8
                        : 0.6

                    color:
                        clockArea.is24Hour
                        ? Colors.orange
                        : Colors.cyan

                    transparentBorder: true
                }
            }

            Item {
                id: clockTextContainer

                implicitWidth: clockText.implicitWidth
                height: 20

                Text {
                    id: clockText

                    text:
                        clockArea.is24Hour
                        ? Qt.formatDateTime(clock.date, "HH:mm AP")
                        : Qt.formatDateTime(clock.date, "hh:mm AP")

                    color:
                        clockArea.is24Hour
                        ? Colors.orange
                        : Colors.cyan
                    font.pixelSize: 20
                }

                DropShadow {
                    anchors.fill: clockText
                    source: clockText

                    horizontalOffset: 0
                    verticalOffset: 0
                    radius: 14
                    samples: 15
                    z: 2

                    opacity:
                        clockButton.pressed
                        ? 1.0
                        : clockButton.hovered
                        ? 0.8
                        : 0.6

                    color:
                        clockArea.is24Hour
                        ? Colors.orange
                        : Colors.cyan

                    transparentBorder: true
                }
            }
        }

        onRightClicked: {
            clockArea.is24Hour = !clockArea.is24Hour;
        }

        onClicked: {
            console.log("clockButton clicked");
        }
    }
}
