import QtQuick
import Quickshell
import "../components"
import QtQuick.Effects
import Qt5Compat.GraphicalEffects

Item {
    id: appmenuRoot

    implicitWidth: appmenuButton.implicitWidth
    implicitHeight: appmenuButton.implicitHeight

    property var appControlWindow

    Rectangle {
        id: appmenuButton

        implicitWidth: 65
        implicitHeight: 50

        color: Colors.black

        Item {
            id: appmenuIconContainer

            anchors.fill: parent

            GohuText {
                id: appmenuIcon

                anchors.centerIn: parent

                text: "-⋆♱⋆-"

                font.pixelSize: 19
                font.weight: 700

                color: Colors.white
            }

            DropShadow {
                id: appmenuIconGlow

                anchors.fill: appmenuIcon
                source: appmenuIcon

                verticalOffset: 0

                radius: 14
                samples: 15

                z: 2

                opacity: appmenuMouse.pressed ? 1.0 : appmenuMouse.containsMouse ? 0.8 : 0.6

                color: appmenuMouse.pressed ? Colors.magenta : appmenuMouse.containsMouse ? Colors.orange : Colors.cyan

                transparentBorder: true
            }
        }
    }

    MouseArea {
        id: appmenuMouse

        anchors.fill: appmenuButton

        hoverEnabled: true

        acceptedButtons: Qt.LeftButton | Qt.RightButton

        onClicked: function (mouse) {
            if (mouse.button === Qt.LeftButton) {
                console.log("applauncherbutton", "left clicked");
                if (appControlWindow) {
                    appControlWindow.menuOpen = !appControlWindow.menuOpen;
                }
            }

            if (mouse.button === Qt.RightButton) {
                console.log("applauncherbutton", "right clicked");
            }
        }
    }

    RectangularShadow {
        id: appmenuDockSoftGlow

        anchors.fill: appmenuButton

        spread: 3
        z: -1

        opacity: appmenuMouse.pressed ? 0.6 : appmenuMouse.containsMouse ? 0.5 : 0.4

        color: appmenuMouse.pressed ? Colors.magenta : appmenuMouse.containsMouse ? Colors.orange : Colors.cyan
    }

    RectangularShadow {
        id: appmenuDockWideGlow

        anchors.fill: appmenuButton

        spread: 10
        z: 1

        opacity: appmenuMouse.pressed ? 0.12 : appmenuMouse.containsMouse ? 0.09 : 0.07

        color: appmenuMouse.pressed ? Colors.magenta : appmenuMouse.containsMouse ? Colors.orange : Colors.cyan
    }
}
