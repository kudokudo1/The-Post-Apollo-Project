import QtQuick
import Quickshell
import "../components"
import QtQuick.Effects
import Qt5Compat.GraphicalEffects

Rectangle {
    id: dock

    implicitHeight: 50
    implicitWidth: Math.max(72, hospitalMark.implicitWidth + 18)

    color: Colors.black

    // Keep these exposed so the mark can be tuned without rebuilding the button.
    property int beatPixelSize: 11
    property int centerPixelSize: 28
    property int markSpacing: 0

    signal leftClicked()
    signal rightClicked()

    Item {
        id: textglowContainer

        anchors.fill: parent

        Row {
            id: hospitalMark

            anchors.centerIn: parent
            spacing: dock.markSpacing

            Text {
                id: leftBeat

                text: "ﮩ٨ـﮩﮩ"
                font.pixelSize: dock.beatPixelSize

                color: mouse.pressed
                       ? Colors.orange
                       : mouse.containsMouse
                       ? Colors.orange
                       : Colors.white
            }

            NotoText {
                id: hospitalCenter

                text: "⚚"
                font.pixelSize: dock.centerPixelSize

                anchors.verticalCenter: leftBeat.verticalCenter

                color: mouse.pressed
                       ? Colors.orange
                       : mouse.containsMouse
                       ? Colors.orange
                       : Colors.white
            }

            Text {
                id: rightBeat

                text: "ﮩ٨ـﮩ"
                font.pixelSize: dock.beatPixelSize

                anchors.verticalCenter: leftBeat.verticalCenter

                color: mouse.pressed
                       ? Colors.orange
                       : mouse.containsMouse
                       ? Colors.orange
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

            opacity: mouse.pressed
                     ? 1.0
                     : mouse.containsMouse
                     ? 0.8
                     : 0.6

            color: Colors.orange

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
                dock.leftClicked();
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

        opacity: mouse.pressed
                 ? 0.6
                 : mouse.containsMouse
                 ? 0.5
                 : 0.4

        color: Colors.orange
    }

    RectangularShadow {
        id: dockWideGlow

        anchors.fill: parent

        spread: 10
        z: 1

        opacity: mouse.pressed
                 ? 0.12
                 : mouse.containsMouse
                 ? 0.09
                 : 0.07

        color: Colors.orange
    }
}
