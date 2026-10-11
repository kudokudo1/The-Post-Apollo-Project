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

    NotoText {
        id: calendarText
        anchors.centerIn: parent

        text: " ⌯⌲ 🗓 ⋆˙⟡ "
        font.pixelSize: 20
        color: calendarDock.foregroundColor
    }
}
