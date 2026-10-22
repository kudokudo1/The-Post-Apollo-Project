import QtQuick
import Quickshell
import "../components"

// TASKS dock launcher. Task storage and sync remain future work.
DockButton {
    id: tasksDock

    implicitHeight: 50
    implicitWidth: Math.max(72, Math.ceil(tasksMark.implicitWidth) + 20)
    property bool menuOpen: false
    signal toggleRequested()
    open: menuOpen

    // White artwork when closed, magenta when the menu opens.
    // Artwork color remains separate from the existing glow behavior.
    normalContentGlowColor: Colors.cyan
    hoverContentGlowColor: Colors.cyan
    pressedContentGlowColor: Colors.cyan
    normalDockGlowColor: Colors.cyan
    hoverDockGlowColor: Colors.cyan
    pressedDockGlowColor: Colors.cyan
    contentGlowSource: tasksMark

    NotoText {
        id: tasksMark
        anchors.centerIn: parent
        font.pixelSize: 22
        // A single text run prevents style-span boundaries from splitting
        // the combining marks. U+FE0E requests a tintable text notepad.
        textFormat: Text.PlainText
        color: tasksDock.menuOpen ? Colors.magenta : Colors.white
        text: "݁˖✎๋࣭🗒︎๋࣭⊹"
    }

    onLeftClicked: toggleRequested()
}
