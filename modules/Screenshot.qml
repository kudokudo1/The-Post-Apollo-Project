import QtQuick
import Quickshell
import "../components"

// CAMERA // The original screenshot dock slot was empty. The new dock owns
// only the Camera window's open/close action, never user picture files.
DockButton {
    id: cameraDock
    property bool menuOpen: false
    signal toggleRequested()

    implicitWidth: 96
    implicitHeight: 50
    open: menuOpen
    normalForegroundColor: Colors.white
    hoverForegroundColor: Colors.cyan
    openForegroundColor: Colors.magenta
    normalContentGlowColor: Colors.cyan
    hoverContentGlowColor: Colors.cyan
    openGlowColor: Colors.magenta
    openFillColor: Colors.black

    contentGlowSource: cameraMark

    Row {
        id: cameraMark
        anchors.centerIn: parent
        height: 42
        spacing: 5

        // Actual Qt vector geometry: no emoji, bitmap, opaque camera body or
        // opaque lens center. The orbit and stars retain independent strokes.
        CameraGlyph {
            width: 58
            height: cameraMark.height
            bodyColor: cameraDock.foregroundColor
            lensColor: cameraDock.menuOpen ? Colors.white
                       : cameraDock.hovered ? Colors.cyan : Colors.white
            ornamentColor: cameraDock.menuOpen ? Colors.magenta : Colors.cyan
        }

        GohuText {
            height: cameraMark.height
            verticalAlignment: Text.AlignVCenter
            text: "CAM"
            font.pixelSize: 13
            color: cameraDock.menuOpen ? Colors.magenta : Colors.cyan
        }
    }

    onLeftClicked: toggleRequested()
}
