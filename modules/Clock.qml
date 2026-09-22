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

    Rectangle {
        id: clockButton

        implicitHeight: 50
        implicitWidth: 151
        color: Colors.black

        //Process {
        //id: switchclockMode
        //command: [""]

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

                    color: clockArea.is24Hour ? Colors.orange : Colors.cyan
                    font.pixelSize: 20
                }

                DropShadow {
                    id: clockIconGlow

                    anchors.fill: clockIcon
                    source: clockIcon

                    horizontalOffset: 0
                    verticalOffset: 0

                    radius: 14
                    samples: 15

                    z: 2

                    opacity: clockMouse.pressed ? 1.0 : clockMouse.containsMouse ? 0.8 : 0.6

                    color: clockArea.is24Hour ? Colors.orange : Colors.cyan

                    transparentBorder: true
                }
            }

            Item {
                id: clockTextContainer

                implicitWidth: clockText.implicitWidth
                height: 20

                Text {
                    id: clockText

                    text: clockArea.is24Hour ? Qt.formatDateTime(clock.date, "HH:mm AP") : Qt.formatDateTime(clock.date, "hh:mm AP")

                    color: clockArea.is24Hour ? Colors.orange : Colors.cyan
                    font.pixelSize: 20

                    //Timer {
                    //interval: 1000
                    //running: true
                    //repeat: true

                    //onTriggered: {
                    //clock.text = Qt.formatDateTime(new Date(), clock.timeFormat);
                    //}

                    //}
                }

                DropShadow {
                    id: clockTextGlow

                    anchors.fill: clockText
                    source: clockText

                    horizontalOffset: 0
                    verticalOffset: 0

                    radius: 14
                    samples: 15

                    z: 2

                    opacity: clockMouse.pressed ? 1.0 : clockMouse.containsMouse ? 0.8 : 0.6

                    color: clockArea.is24Hour ? Colors.orange : Colors.cyan

                    transparentBorder: true
                }
            }
        }
    }

    MouseArea {
        id: clockMouse

        anchors.fill: clockButton
        hoverEnabled: true

        acceptedButtons: Qt.LeftButton | Qt.RightButton

        onClicked: {
            if (mouse.button === Qt.RightButton) {
                clockArea.is24Hour = !clockArea.is24Hour;
            }

            console.log("clockButton clicked");
        }
    }

    RectangularShadow {
        id: clockDockSoftGlow

        anchors.fill: clockButton

        spread: 3
        z: -1

        opacity: clockMouse.pressed ? 0.6 : clockMouse.containsMouse ? 0.5 : 0.4

        color: clockArea.is24Hour ? Colors.orange : Colors.cyan
    }

    RectangularShadow {
        id: clockDockWideGlow

        anchors.fill: clockButton

        spread: 10
        z: 1

        opacity: clockMouse.pressed ? 0.12 : clockMouse.containsMouse ? 0.09 : 0.07

        color: clockArea.is24Hour ? Colors.orange : Colors.cyan
    }
}
