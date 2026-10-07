import QtQuick
import Quickshell
import "../components"

DockButton {
    id: cpuDock

    property var cpuPlusWindow
    readonly property bool menuOpen:
        cpuPlusWindow && cpuPlusWindow.menuOpen

    // Session-wide hardware services are injected by shell.qml. CPU++ can
    // build its own view/controller state without duplicating polling or PWM
    // ownership.
    property var systemTelemetry: null
    property var fanControl: null

    implicitHeight: 50
    implicitWidth: 70

    open: menuOpen

    normalForegroundColor: Colors.white
    hoverForegroundColor: Colors.cyan
    pressedForegroundColor: Colors.cyan

    normalContentGlowColor: Colors.cyan
    hoverContentGlowColor: Colors.cyan
    pressedContentGlowColor: Colors.cyan

    normalDockGlowColor: Colors.cyan
    hoverDockGlowColor: Colors.cyan
    pressedDockGlowColor: Colors.cyan

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

    contentGlowSource: cpuText

    GohuText {
        id: cpuText
        anchors.centerIn: parent

        text: "🖥"
        font.pixelSize: 20
        color: cpuDock.foregroundColor
    }

    onLeftClicked: {
        if (cpuPlusWindow)
            cpuPlusWindow.toggle();
    }
}
