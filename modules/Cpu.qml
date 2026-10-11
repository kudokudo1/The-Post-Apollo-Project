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
    hoverForegroundColor: Colors.white
    pressedForegroundColor: Colors.white

    normalContentGlowColor: Colors.cyan
    hoverContentGlowColor: Colors.orange
    pressedContentGlowColor: Colors.magenta

    normalDockGlowColor: Colors.cyan
    hoverDockGlowColor: Colors.orange
    pressedDockGlowColor: Colors.magenta

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
