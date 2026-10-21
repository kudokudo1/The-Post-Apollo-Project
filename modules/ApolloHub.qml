import QtQuick
import Quickshell
import "../components"

// New center-bar control, staged separately from shell.qml until the operator
// has reviewed the first working Hub window.
DockButton {
    id: dock

    property bool menuOpen: false
    signal toggleRequested()

    implicitWidth: 120
    implicitHeight: 50
    open: menuOpen

    normalForegroundColor: Colors.white
    hoverForegroundColor: Colors.white
    pressedForegroundColor: Colors.white

    normalDockGlowColor: Colors.cyan
    hoverDockGlowColor: Colors.orange
    pressedDockGlowColor: Colors.magenta

    normalContentGlowColor: Colors.cyan
    hoverContentGlowColor: Colors.orange
    pressedContentGlowColor: Colors.magenta
    contentGlowSource: titleText

    GohuText {
        id: titleText
        anchors.centerIn: parent
        text: "✦ APOLLO ✦"
        font.pixelSize: 16
        font.weight: 700
        color: dock.foregroundColor
    }

    onLeftClicked: toggleRequested()
}
