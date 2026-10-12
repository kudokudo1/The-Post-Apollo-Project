import QtQuick
import Quickshell
import "../components"

DockButton {
    id: bluetoothDock

    implicitHeight: 50
    implicitWidth: 85

    normalForegroundColor: Colors.white
    hoverForegroundColor: Colors.white
    pressedForegroundColor: Colors.white

    normalContentGlowColor: Colors.cyan
    hoverContentGlowColor: Colors.orange
    pressedContentGlowColor: Colors.magenta

    normalDockGlowColor: Colors.cyan
    hoverDockGlowColor: Colors.orange
    pressedDockGlowColor: Colors.magenta

    contentGlowSource: bluetoothText

    // Styled text preserves the exact original centered line geometry.
    Text {
        id: bluetoothText
        anchors.centerIn: parent
        // The glyph's optical center sits below its font box center.
        // Lift only this original text item; DockButton's sampled glow follows.
        anchors.verticalCenterOffset: -2
        textFormat: Text.StyledText
        text: "(<font color='" + bluetoothDock.foregroundColor + "'>˓✟˒</font>)"
        font.pixelSize: 20
        // The parentheses inherit normal/hover/pressed/open foreground state.
        color: bluetoothDock.foregroundColor
    }
}
