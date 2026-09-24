import QtQuick
import Quickshell
import "../components"
import QtQuick.Effects
import Qt5Compat.GraphicalEffects

Rectangle {
    id: cpuDock

    property var cpuPlusWindow

    implicitHeight: 50
    implicitWidth: 70

    color: Colors.black

    Item {
        id: cpuTextGlowContainer

        anchors.fill: parent

        GohuText {
            id: cpuText

            anchors.centerIn: parent

            text: "🖥"

            font.pixelSize: 20

            color: cpuMouse.pressed ? Colors.cyan : cpuMouse.containsMouse ? Colors.cyan : Colors.white
        }

        DropShadow {
            id: cpuTextGlow

            anchors.fill: cpuText
            source: cpuText

            horizontalOffset: 0
            verticalOffset: 0

            radius: 14
            samples: 15

            z: 2

            opacity: cpuMouse.pressed ? 1.0 : cpuMouse.containsMouse ? 0.8 : 0.6

            color: cpuMouse.pressed ? Colors.cyan : cpuMouse.containsMouse ? Colors.cyan : Colors.cyan

            transparentBorder: true
        }
    }

    MouseArea {
        id: cpuMouse

        anchors.fill: parent

        hoverEnabled: true

        acceptedButtons: Qt.LeftButton | Qt.RightButton

        onClicked: function (mouse) {
            if (mouse.button === Qt.LeftButton) {
                if (cpuDock.cpuPlusWindow)
                    cpuDock.cpuPlusWindow.toggle();
            }

            if (mouse.button === Qt.RightButton) {
                // Reserved for a future CPU++ quick action.
            }
        }
    }

    RectangularShadow {
        id: cpuDockSoftGlow

        anchors.fill: parent

        spread: 3
        z: -1

        opacity: cpuMouse.pressed ? 0.6 : cpuMouse.containsMouse ? 0.5 : 0.4

        color: cpuMouse.pressed ? Colors.cyan : cpuMouse.containsMouse ? Colors.cyan : Colors.cyan
    }

    RectangularShadow {
        id: cpuDockWideGlow

        anchors.fill: parent

        spread: 10
        z: 1

        opacity: cpuMouse.pressed ? 0.12 : cpuMouse.containsMouse ? 0.09 : 0.07

        color: cpuMouse.pressed ? Colors.cyan : cpuMouse.containsMouse ? Colors.cyan : Colors.cyan
    }
}
