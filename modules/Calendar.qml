import QtQuick
import Quickshell
import "../components"

DockButton {
    id: calendarDock

    implicitHeight: 50
    implicitWidth: 113
    radius: 7

    normalForegroundColor: Colors.white
    hoverForegroundColor: Colors.white
    pressedForegroundColor: Colors.white

    normalContentGlowColor: Colors.cyan
    hoverContentGlowColor: Colors.orange
    pressedContentGlowColor: Colors.magenta

    normalDockGlowColor: Colors.cyan
    hoverDockGlowColor: Colors.orange
    pressedDockGlowColor: Colors.magenta

    contentGlowSource: calendarText

    // Keep the full icon grammar, with independent structural-white ornaments.
    Row {
        id: calendarText
        anchors.centerIn: parent
        spacing: 0

        NotoText {
            text: " ⌯⌲ "
            font.pixelSize: 20
            color: Colors.white
        }
        NotoText {
            text: "🗓"
            font.pixelSize: 20
            color: calendarDock.foregroundColor
        }
        NotoText {
            text: " ⋆˙⟡ "
            font.pixelSize: 20
            color: Colors.white
        }
    }
}
