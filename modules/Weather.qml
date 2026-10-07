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

    contentGlowIdleOpacity: 0.60
    contentGlowHoverOpacity: 0.80
    contentGlowPressedOpacity: 1.0
    contentGlowHoverRadius: 14
    contentGlowPressedRadius: 14
    contentGlowHoverSamples: 15
    contentGlowPressedSamples: 15

    softGlowIdleOpacity: 0.40
    softGlowHoverOpacity: 0.50
    softGlowPressedOpacity: 0.60

    wideGlowIdleOpacity: 0.07
    wideGlowHoverOpacity: 0.09
    wideGlowPressedOpacity: 0.12

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
