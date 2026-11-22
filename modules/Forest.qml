import QtQuick
import Quickshell
import "../components"

// FOREST V0: dock-only entry point; no model initialized on shell startup.
DockButton {
    id: dock
    property bool menuOpen: false
    signal toggleRequested()

    implicitWidth: 72
    implicitHeight: 50
    open: menuOpen

    normalForegroundColor: Colors.white
    hoverForegroundColor: Colors.orange
    pressedForegroundColor: Colors.magenta
    openForegroundColor: Colors.magenta
    normalDockGlowColor: Colors.cyan
    hoverDockGlowColor: Colors.orange
    pressedDockGlowColor: Colors.magenta
    openGlowColor: Colors.magenta
    normalContentGlowColor: Colors.cyan
    hoverContentGlowColor: Colors.orange
    pressedContentGlowColor: Colors.magenta
    contentGlowSource: treeMark

    NotoText {
        id: treeMark
        anchors.centerIn: parent
        text: "🌲"
        font.pixelSize: 27
        color: dock.foregroundColor
    }

    onLeftClicked: toggleRequested()
}
