import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.components
import qs.services.notifications
import QtQuick.Effects
import Qt5Compat.GraphicalEffects

Rectangle {
    id: dock

    signal toggleRequested

    property bool menuOpen: false

    implicitHeight: 50
    implicitWidth: 130

    color: dock.menuOpen ? Colors.yellow : Colors.black

    // ===== CONTENT ==============================================

    Item {
        id: textglowContainer

        anchors.fill: parent

        GohuText {
            id: text

            anchors.centerIn: parent

            text: "-⋆🗒⋆-"

            font.pixelSize: 25

            color: dock.menuOpen ? Colors.orange : mouse.pressed ? Colors.white : Colors.cyan
        }

        DropShadow {
            id: textGlow

            anchors.fill: text

            source: text

            horizontalOffset: 0
            verticalOffset: 0

            radius: 14
            samples: 15

            z: 2

            opacity: dock.menuOpen ? 1.0 : mouse.pressed ? 1.0 : mouse.containsMouse ? 0.8 : 0.6

            color: dock.menuOpen ? Colors.orange : Colors.cyan

            transparentBorder: true
        }
    }

    // ===== INPUT ================================================

    MouseArea {
        id: mouse

        anchors.fill: parent

        hoverEnabled: true

        acceptedButtons: Qt.LeftButton | Qt.RightButton

        onClicked: function (mouse) {
            if (mouse.button === Qt.LeftButton) {
                dock.toggleRequested();
            }

            if (mouse.button === Qt.RightButton) {
                // Reserved
            }
        }
    }

    // ===== EFFECTS ==============================================

    RectangularShadow {
        id: dockSoftGlow

        anchors.fill: parent

        spread: 3

        z: -1

        opacity: dock.menuOpen ? 0.75 : mouse.pressed ? 0.6 : mouse.containsMouse ? 0.5 : 0.4

        color: dock.menuOpen ? Colors.orange : Colors.cyan
    }

    RectangularShadow {
        id: dockWideGlow

        anchors.fill: parent

        spread: 10

        z: 1

        opacity: dock.menuOpen ? 0.16 : mouse.pressed ? 0.12 : mouse.containsMouse ? 0.09 : 0.07

        color: dock.menuOpen ? Colors.orange : Colors.cyan
    }
}
