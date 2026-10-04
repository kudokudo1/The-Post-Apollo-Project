import QtQuick
import Quickshell
import "../components"
import QtQuick.Effects
import Qt5Compat.GraphicalEffects

Rectangle {
    id: dock

    implicitHeight: 50
    implicitWidth: Math.max(72, hospitalMark.implicitWidth + 18)

    color: dock.menuOpen ? Colors.yellow : Colors.black

    // Keep these exposed so the mark can be tuned without rebuilding the button.
    property int beatPixelSize: 11
    property int centerPixelSize: 28
    property int markSpacing: 0

    property bool menuOpen: false

    signal toggleRequested()
    signal rightClicked()

    Item {
        id: textglowContainer

        anchors.fill: parent

        Row {
            id: hospitalMark

            anchors.centerIn: parent
            spacing: dock.markSpacing

            // Shared vertical box keeps the visible mark centered.
            height: 34

            Text {
                id: leftBeat

                height: hospitalMark.height

                text: "ﮩ٨ـﮩﮩ"
                font.pixelSize: dock.beatPixelSize
                verticalAlignment: Text.AlignVCenter

                color: dock.menuOpen
                       ? Colors.magenta
                       : mouse.pressed
                       ? Colors.magenta
                       : mouse.containsMouse
                       ? Colors.magenta
                       : Colors.white
            }

            NotoText {
                id: hospitalCenter

                height: hospitalMark.height

                text: "⚚"
                font.pixelSize: dock.centerPixelSize
                verticalAlignment: Text.AlignVCenter

                color: dock.menuOpen
                       ? Colors.magenta
                       : mouse.pressed
                       ? Colors.magenta
                       : mouse.containsMouse
                       ? Colors.magenta
                       : Colors.white
            }

            Text {
                id: rightBeat

                height: hospitalMark.height

                text: "ﮩ٨ـﮩ"
                font.pixelSize: dock.beatPixelSize
                verticalAlignment: Text.AlignVCenter

                color: dock.menuOpen
                       ? Colors.magenta
                       : mouse.pressed
                       ? Colors.magenta
                       : mouse.containsMouse
                       ? Colors.magenta
                       : Colors.white
            }
        }

        DropShadow {
            id: textGlow

            anchors.fill: hospitalMark
            source: hospitalMark

            horizontalOffset: 0
            verticalOffset: 0

            radius: 14
            samples: 15

            z: 2

            opacity: dock.menuOpen
                     ? 1.0
                     : mouse.pressed
                     ? 1.0
                     : mouse.containsMouse
                     ? 0.8
                     : 0.6

            color: Colors.magenta

            transparentBorder: true
        }
    }

    MouseArea {
        id: mouse

        anchors.fill: parent

        hoverEnabled: true

        acceptedButtons: Qt.LeftButton | Qt.RightButton

        onClicked: function(mouse) {
            if (mouse.button === Qt.LeftButton) {
                dock.toggleRequested();
            }

            if (mouse.button === Qt.RightButton) {
                dock.rightClicked();
            }
        }
    }

    RectangularShadow {
        id: dockSoftGlow

        anchors.fill: parent

        spread: 3
        z: -1

        opacity: dock.menuOpen
                 ? 0.75
                 : mouse.pressed
                 ? 0.6
                 : mouse.containsMouse
                 ? 0.5
                 : 0.4

        color: Colors.magenta
    }

    RectangularShadow {
        id: dockWideGlow

        anchors.fill: parent

        spread: 10
        z: 1

        opacity: dock.menuOpen
                 ? 0.16
                 : mouse.pressed
                 ? 0.12
                 : mouse.containsMouse
                 ? 0.09
                 : 0.07

        color: Colors.magenta
    }
}
