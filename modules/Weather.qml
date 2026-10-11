import QtQuick
import Quickshell
import "../components"

DockButton {
    id: weatherDock

    property var weatherStationWindow: null
    readonly property bool menuOpen:
        weatherStationWindow && weatherStationWindow.menuOpen

    implicitHeight: 50
    implicitWidth: 90

    signal weatherClicked

    open: menuOpen

    normalForegroundColor: Colors.orange
    hoverForegroundColor: Colors.orange
    pressedForegroundColor: Colors.orange

    normalContentGlowColor: Colors.orange
    hoverContentGlowColor: Colors.orange
    pressedContentGlowColor: Colors.orange

    normalDockGlowColor: Colors.orange
    hoverDockGlowColor: Colors.orange
    pressedDockGlowColor: Colors.orange

    contentGlowSource: weatherText

    Text {
        id: weatherText
        anchors.centerIn: parent

        text: "🌡"
        font.pixelSize: 20
        color: weatherDock.foregroundColor
    }

    onLeftClicked: {
        if (weatherStationWindow)
            weatherStationWindow.toggle();
    }
}
