import QtQuick
import Quickshell
import "../components"

DockButton {
    id: calendarDock

    implicitHeight: 50
    implicitWidth: 113
    radius: 7

    normalForegroundColor: Colors.white
    hoverForegroundColor: Colors.cyan
    pressedForegroundColor: Colors.cyan

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

    contentGlowSource: calendarText

    NotoText {
        id: calendarText
        anchors.centerIn: parent

        text: " ⌯⌲ 🗓 ⋆˙⟡ "
        font.pixelSize: 20
        color: calendarDock.foregroundColor
    }
}
