import QtQuick
import Quickshell
import "../components"
import QtQuick.Effects
import Qt5Compat.GraphicalEffects

Rectangle {
    id: dock

    implicitWidth: Math.max(92, gitMark.implicitWidth + 18)
    implicitHeight: 50

    color: dock.menuOpen ? Colors.yellow : Colors.black

    property bool menuOpen: false

    signal toggleRequested()
    signal rightClicked()

    Item {
        id: markContainer
        anchors.fill: parent

        Text {
            id: gitMark

            anchors.centerIn: parent

            text: "≽(•⩊•マ≼"
            font.pixelSize: 16

            color: dock.menuOpen
                   ? Colors.orange
                   : mouse.pressed
                   ? Colors.magenta
                   : mouse.containsMouse
                   ? Colors.orange
                   : Colors.white
        }

        DropShadow {
            anchors.fill: gitMark
            source: gitMark
            horizontalOffset: 0
            verticalOffset: 0
            radius: 14
            samples: 15
            color: dock.menuOpen ? Colors.orange : Colors.orange
            opacity: mouse.pressed
                     ? 1.0
                     : mouse.containsMouse
                     ? 0.82
                     : 0.58
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
        color: Colors.orange
        opacity: mouse.pressed
                 ? 0.60
                 : mouse.containsMouse
                 ? 0.48
                 : 0.32
    }

    RectangularShadow {
        anchors.fill: parent
        spread: 10
        z: 1
        color: Colors.orange
        opacity: mouse.pressed
                 ? 0.12
                 : mouse.containsMouse
                 ? 0.09
                 : 0.06
    }
}
