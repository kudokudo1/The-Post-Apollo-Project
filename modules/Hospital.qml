import QtQuick
import Quickshell
import "../components"
import QtQuick.Effects
import Qt5Compat.GraphicalEffects

Rectangle {
    id: dock

    implicitHeight: 50
    implicitWidth: Math.max(72, hospitalMark.implicitWidth + 18)

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
        ? Colors.magenta
        : Colors.cyan

    Behavior on scale {
        NumberAnimation {
            duration: 90
            easing.type: Easing.OutQuad
        }
    }

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

            // Give every glyph the same vertical box. This centers the
            // visible mark instead of centering three different font metrics.
            height: 34

            Text {
                id: leftBeat

                height: hospitalMark.height

                text: "ﮩ٨ـﮩﮩ"
                font.pixelSize: dock.beatPixelSize
                verticalAlignment: Text.AlignVCenter

                color: dock.pressed
                       ? Colors.black
                       : dock.menuOpen
                       ? Colors.magenta
                       : dock.hovered
                       ? Colors.orange
                       : Colors.cyan
            }

            NotoText {
                id: hospitalCenter

                height: hospitalMark.height

                text: "⚚"
                font.pixelSize: dock.centerPixelSize
                verticalAlignment: Text.AlignVCenter

                color: dock.pressed
                       ? Colors.black
                       : dock.menuOpen
                       ? Colors.magenta
                       : dock.hovered
                       ? Colors.orange
                       : Colors.cyan
            }

            Text {
                id: rightBeat

                height: hospitalMark.height

                text: "ﮩ٨ـﮩ"
                font.pixelSize: dock.beatPixelSize
                verticalAlignment: Text.AlignVCenter

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
            id: textGlow

            anchors.fill: hospitalMark
            source: hospitalMark

            horizontalOffset: 0
            verticalOffset: 0

            radius: 14
            samples: 15

            z: 2

            opacity:
                dock.pressed
                ? 0.0
                : dock.hovered
                ? 0.82
                : dock.menuOpen
                ? 0.72
                : 0.58

            color:
                dock.menuOpen
                ? Colors.magenta
                : dock.hovered
                ? Colors.orange
                : Colors.cyan

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

        spread:
            dock.hovered
            ? 6
            : dock.menuOpen
            ? 4
            : 2
        z: -1

        opacity:
            dock.pressed
            ? 0.62
            : dock.hovered
            ? 0.56
            : dock.menuOpen
            ? 0.46
            : 0.10

        color: Colors.magenta
    }

    RectangularShadow {
        id: dockWideGlow

        anchors.fill: parent

        spread:
            dock.hovered
            ? 16
            : dock.menuOpen
            ? 11
            : 7
        z: -2

        opacity:
            dock.pressed
            ? 0.16
            : dock.hovered
            ? 0.14
            : dock.menuOpen
            ? 0.11
            : 0.035

        color: Colors.magenta
    }
}
