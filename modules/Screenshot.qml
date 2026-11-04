import QtQuick
import Quickshell
import "../components"

// CAMERA // The original screenshot dock slot was empty. The new dock owns
// only the Camera window's open/close action, never user picture files.
DockButton {
    id: cameraDock
    property bool menuOpen: false
    signal toggleRequested()

    implicitWidth: 84
    implicitHeight: 50
    open: menuOpen

    // One ink color drives every vector stroke: camera outline, lens,
    // compass ticks, orbital arcs, and stars. No separate white lens remains
    // when the dock opens. Hover/press do not change the closed white icon.
    readonly property color glyphInk: menuOpen ? Colors.magenta : Colors.white
    normalForegroundColor: Colors.white
    hoverForegroundColor: Colors.white
    pressedForegroundColor: Colors.white
    openForegroundColor: Colors.magenta
    normalContentGlowColor: Colors.white
    hoverContentGlowColor: Colors.white
    pressedContentGlowColor: Colors.white
    openGlowColor: Colors.magenta
    openFillColor: Colors.black

    contentGlowSource: cameraMark

    // Native hollow Qt Shapes artwork only. The text label is deliberately
    // removed; the original DockButton owns the same click/hover/open states.
    CameraGlyph {
        id: cameraMark
        anchors.centerIn: parent
        width: 64
        height: 48
        bodyColor: cameraDock.glyphInk
        lensColor: cameraDock.glyphInk
        ornamentColor: cameraDock.glyphInk
    }

    onLeftClicked: toggleRequested()
}
