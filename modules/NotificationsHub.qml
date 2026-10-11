import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.components
import qs.services.notifications

DockButton {
    id: dock

    signal toggleRequested

    property bool menuOpen: false

    implicitHeight: 50
    implicitWidth: 130

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

    contentGlowSource: text

    GohuText {
        id: text
        anchors.centerIn: parent

        text: "-⋆🗒⋆-"
        font.pixelSize: 25
        color: dock.foregroundColor
    }

    onLeftClicked: {
        dock.toggleRequested();
    }
}
