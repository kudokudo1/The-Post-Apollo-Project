import QtQuick
import Quickshell
import "../components"
import QtQuick.Effects
import Qt5Compat.GraphicalEffects

Rectangle {
    id: dock

    implicitWidth: Math.max(118, gitMark.implicitWidth + 18)
    implicitHeight: 50

    color: Colors.black

    property bool menuOpen: false

    signal toggleRequested()
    signal rightClicked()

    Item {
        id: markContainer
        anchors.fill: parent

        Row {
            id: gitMark

            anchors.centerIn: parent
            spacing: 5

            GohuText {
                id: gitDataMark

                text: ""
                font.pixelSize: 38
                anchors.verticalCenter: parent.verticalCenter
                color: Colors.white
                opacity: 1.0

                transform: Scale {
                    origin.x: gitDataMark.width / 2
                    origin.y: gitDataMark.height / 2
                    xScale: 0.54
                    yScale: 1.26
                }
            }

            GohuText {
                text: "≽(•⩊•マ≼"
                font.pixelSize: 16
                anchors.verticalCenter: parent.verticalCenter
                color: Colors.yellow
            }
        }

        DropShadow {
            anchors.fill: gitMark
            source: gitMark
            horizontalOffset: 0
            verticalOffset: 0
            radius: dock.menuOpen || mouse.containsMouse || mouse.pressed ? 18 : 14
            samples: dock.menuOpen || mouse.containsMouse || mouse.pressed ? 21 : 15
            color: Colors.orange
            opacity: dock.menuOpen
                     ? 1.0
                     : mouse.pressed
                     ? 1.0
                     : mouse.containsMouse
                     ? 0.96
                     : 0.76
            transparentBorder: true
        }
    }

    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.RightButton

        onClicked: function(mouse) {
            if (mouse.button === Qt.LeftButton)
                dock.toggleRequested();

            if (mouse.button === Qt.RightButton)
                dock.rightClicked();
        }
    }

    RectangularShadow {
        anchors.fill: parent
        spread: 3
        z: -1
        color: Colors.yellow
        opacity: dock.menuOpen
                 ? 0.86
                 : mouse.pressed
                 ? 0.60
                 : mouse.containsMouse
                 ? 0.48
                 : 0.32
    }

    RectangularShadow {
        anchors.fill: parent
        spread: 10
        z: 1
        color: Colors.yellow
        opacity: dock.menuOpen
                 ? 0.22
                 : mouse.pressed
                 ? 0.12
                 : mouse.containsMouse
                 ? 0.09
                 : 0.06
    }
}
