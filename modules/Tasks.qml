import QtQuick
import Quickshell
import "../components"

// TASKS dock artwork pilot. The task window does not exist yet.
// Keep this visual launcher non-interactive until it has a real target.
DockButton {
    id: tasksDock

    implicitHeight: 50
    implicitWidth: Math.max(72, Math.ceil(tasksMark.implicitWidth) + 20)
    interactive: false

    // Independent yellow task identity and white ornaments. Cyan is the
    // surrounding content glow and dock halo, not the glyph foreground.
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
        textFormat: Text.StyledText
        color: Colors.yellow

        // Keep the original combining-mark composition intact.
        // U+FE0E requests a monochrome/text notepad so it can be yellow.
        text: "<font color='" + Colors.white + "'>݁˖</font>"
              + "<font color='" + Colors.yellow + "'>✎๋࣭🗒︎๋࣭</font>"
              + "<font color='" + Colors.white + "'>⊹</font>"
    }
}
