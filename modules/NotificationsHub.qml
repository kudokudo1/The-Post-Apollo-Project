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

    normalForegroundColor: Colors.cyan
    hoverForegroundColor: Colors.cyan
    pressedForegroundColor: Colors.white

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
