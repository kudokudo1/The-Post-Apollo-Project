import QtQuick
import Quickshell
import "../components"
import QtQuick.Effects
import Qt5Compat.GraphicalEffects

Rectangle {
    id: dock

    implicitWidth: Math.max(118, gitMark.implicitWidth + 18)
    implicitHeight: 50

    property bool menuOpen: false

    readonly property bool hovered: mouse.containsMouse
    readonly property bool pressed: mouse.pressed

    scale:
        pressed
        ? 0.99
        : hovered
        ? 1.025
        : menuOpen
        ? 1.01
        : 1.0

    color:
        pressed
        ? Colors.magenta
        : hovered || menuOpen
        ? Colors.yellow
        : Colors.black

    border.width: 1
    border.color:
        hovered || pressed || menuOpen
        ? Colors.orange
        : Colors.cyan

    Behavior on scale {
        NumberAnimation {
            duration: 90
            easing.type: Easing.OutQuad
        }
    }

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
                text: ""
                font.pixelSize: 30
                anchors.verticalCenter: parent.verticalCenter

                color: dock.pressed
                       ? Colors.black
                       : dock.menuOpen
                       ? Colors.magenta
                       : dock.hovered
                       ? Colors.orange
                       : Colors.cyan
            }

            GohuText {
                text: "≽(•⩊•マ≼"
                font.pixelSize: 16
                anchors.verticalCenter: parent.verticalCenter

                color: dock.pressed
                       ? Colors.black
                       : dock.menuOpen
                       ? Colors.magenta
                       : dock.hovered
                       ? Colors.orange
                       : Colors.cyan
            }
        }

        DropShadow {
            anchors.fill: gitMark
            source: gitMark
            horizontalOffset: 0
            verticalOffset: 0
            radius: 14
            samples: 15
            color:
                dock.menuOpen
                ? Colors.magenta
                : dock.hovered
                ? Colors.orange
                : Colors.cyan
            opacity:
                dock.pressed
                ? 0.0
                : dock.hovered
                ? 0.82
                : dock.menuOpen
                ? 0.72
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
        spread:
            dock.hovered
            ? 6
            : dock.menuOpen
            ? 4
            : 2
        z: -1
        color: Colors.orange
        opacity:
            dock.pressed
            ? 0.62
            : dock.hovered
            ? 0.56
            : dock.menuOpen
            ? 0.46
            : 0.10
    }

    RectangularShadow {
        anchors.fill: parent
        spread:
            dock.hovered
            ? 16
            : dock.menuOpen
            ? 11
            : 7
        z: -2
        color: Colors.orange
        opacity:
            dock.pressed
            ? 0.16
            : dock.hovered
            ? 0.14
            : dock.menuOpen
            ? 0.11
            : 0.035
    }
}
