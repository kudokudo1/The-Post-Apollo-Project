import QtQuick
import Quickshell
import "../components"
import QtQuick.Effects
import Qt5Compat.GraphicalEffects

Rectangle {
    id: weatherDock
    property var weatherStationWindow: null

    implicitHeight: 50
    implicitWidth: 90

    color: Colors.black

    signal weatherClicked

    Item {
        id: weatherTextGlowContainer

        anchors.fill: parent

        Text {
            id: weatherText

            anchors.centerIn: parent

            // Placeholder for now.
            // Later this can become:
            // "☀ 72°"
            // "☁ 68°"
            // "🌧 61°"
            text: "🌡"

            font.pixelSize: 20

            color: Colors.orange
        }

        DropShadow {
            id: weatherTextGlow

            anchors.fill: weatherText
            source: weatherText

            horizontalOffset: 0
            verticalOffset: 0

            radius: 14
            samples: 15

            z: 2

            opacity: weatherMouse.pressed ? 1.0 : weatherMouse.containsMouse ? 0.8 : 0.6

            color: Colors.orange

            transparentBorder: true
        }
    }

    MouseArea {
        id: weatherMouse

        anchors.fill: parent

        hoverEnabled: true

        acceptedButtons: Qt.LeftButton | Qt.RightButton

        onClicked: function (mouse) {
            if (mouse.button === Qt.LeftButton) {
                if (weatherDock.weatherStationWindow)
                    weatherDock.weatherStationWindow.toggle();
            }

            if (mouse.button === Qt.RightButton) {
                // Leave unused for now.
                // We can give this Observatory / alternate behavior later.
            }
        }
    }

    RectangularShadow {
        id: weatherDockSoftGlow

        anchors.fill: parent

        spread: 3
        z: -1

        opacity: weatherMouse.pressed ? 0.6 : weatherMouse.containsMouse ? 0.5 : 0.4

        color: Colors.orange
    }

    RectangularShadow {
        id: weatherDockWideGlow

        anchors.fill: parent

        spread: 10
        z: 1

        opacity: weatherMouse.pressed ? 0.12 : weatherMouse.containsMouse ? 0.09 : 0.07

        color: Colors.orange
    }
}
