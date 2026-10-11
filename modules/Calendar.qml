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

    // Do not split the Noto glyph sequence into independent QML items.
    NotoText {
        id: calendarText
        anchors.centerIn: parent
        textFormat: Text.StyledText
        text: " ⌯⌲ <font color='" + calendarDock.foregroundColor + "'>🗓</font> ⋆˙⟡ "
        font.pixelSize: 20
        // Ornaments stay with the whole mark on future open-state changes.
        color: calendarDock.foregroundColor
    }
}
