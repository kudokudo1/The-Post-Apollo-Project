import QtQuick
import Quickshell
import "../components"
import QtQuick.Effects
import Qt5Compat.GraphicalEffects

Rectangle {
    id: bluetoothDock

    implicitHeight: 50
    implicitWidth: 85

    color: Colors.black

    Item {
        id: bluetoothTextContainer

        anchors.fill: parent

        Text {
            id: bluetoothText

            anchors.centerIn: parent

            text: "(˓✟˒)"

            font.pixelSize: 20
            color: bluetoothDockMouse.pressed ? Colors.cyan : bluetoothDockMouse.containsMouse ? Colors.cyan : Colors.white
        }

        DropShadow {
            id: bluetoothTextGlow

            anchors.fill: bluetoothText
            source: bluetoothText

            horizontalOffset: 0
            verticalOffset: 0

            radius: 14
            samples: 15

            z: 2

            opacity: bluetoothDockMouse.pressed ? 1.0 : bluetoothDockMouse.containsMouse ? 0.8 : 0.6

            color: bluetoothDockMouse.pressed ? Colors.cyan : bluetoothDockMouse.containsMouse ? Colors.cyan : Colors.cyan

            transparentBorder: true
        }
    }

    MouseArea {
        id: bluetoothDockMouse

        anchors.fill: parent
        hoverEnabled: true

        acceptedButtons: Qt.LeftButton | Qt.RightButton

        onClicked: function (mouse) {
            if (mouse.button === Qt.LeftButton) {
                // Left-click function
            }

            if (mouse.button === Qt.RightButton) {
                // Right-click function
            }
        }
    }

    RectangularShadow {
        id: bluetoothDockSoftGlow

        anchors.fill: parent

        spread: 3
        z: -1

        opacity: bluetoothDockMouse.pressed ? 0.6 : bluetoothDockMouse.containsMouse ? 0.5 : 0.4

        color: bluetoothDockMouse.pressed ? Colors.cyan : bluetoothDockMouse.containsMouse ? Colors.cyan : Colors.cyan
    }

    RectangularShadow {
        id: bluetoothDockWideGlow

        anchors.fill: parent

        spread: 10
        z: 1

        opacity: bluetoothDockMouse.pressed ? 0.12 : bluetoothDockMouse.containsMouse ? 0.09 : 0.07

        color: bluetoothDockMouse.pressed ? Colors.cyan : bluetoothDockMouse.containsMouse ? Colors.cyan : Colors.cyan
    }
}
