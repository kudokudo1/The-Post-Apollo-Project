import QtQuick
import Quickshell
import "../components"
import QtQuick.Effects
import Qt5Compat.GraphicalEffects

Rectangle {
    id: calendarDock

    implicitHeight: 50
    implicitWidth: 113
    radius: 7
    color: Colors.black

    Item {
        id: calendarTextGlowContainer

        anchors.fill: parent

        NotoText {
            id: calendarText

            anchors.centerIn: parent

            text: " ⌯⌲ 🗓 ⋆˙⟡ "

            font.pixelSize: 20

            color: calendarMouse.pressed ? Colors.cyan : calendarMouse.containsMouse ? Colors.cyan : Colors.white
        }

        DropShadow {
            id: calendarTextGlow

            anchors.fill: calendarText
            source: calendarText

            horizontalOffset: 0
            verticalOffset: 0

            radius: 14
            samples: 15

            z: 2

            opacity: calendarMouse.pressed ? 1.0 : calendarMouse.containsMouse ? 0.8 : 0.6

            color: calendarMouse.pressed ? Colors.cyan : calendarMouse.containsMouse ? Colors.cyan : Colors.cyan

            transparentBorder: true
        }
    }

    MouseArea {
        id: calendarMouse

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
        id: calendarDockSoftGlow

        anchors.fill: parent

        spread: 3
        z: -1

        opacity: calendarMouse.pressed ? 0.6 : calendarMouse.containsMouse ? 0.5 : 0.4

        color: calendarMouse.pressed ? Colors.cyan : calendarMouse.containsMouse ? Colors.cyan : Colors.cyan
    }

    RectangularShadow {
        id: calendarDockWideGlow

        anchors.fill: parent

        spread: 10
        z: 1

        opacity: calendarMouse.pressed ? 0.12 : calendarMouse.containsMouse ? 0.09 : 0.07

        color: calendarMouse.pressed ? Colors.cyan : calendarMouse.containsMouse ? Colors.cyan : Colors.cyan
    }
}
