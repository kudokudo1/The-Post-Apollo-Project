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
        spacing: 5

        NotoText {
            text: "📷︎"
            textFormat: Text.PlainText
            font.pixelSize: 25
            color: cameraDock.menuOpen ? Colors.magenta : Colors.white
        }
        GohuText {
            height: 31
            verticalAlignment: Text.AlignVCenter
            text: "CAM"
            font.pixelSize: 13
            color: cameraDock.menuOpen ? Colors.magenta : Colors.cyan
        }
    }

    onLeftClicked: toggleRequested()
}
