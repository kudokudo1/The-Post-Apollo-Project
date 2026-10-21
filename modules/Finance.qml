import QtQuick
import Quickshell
import "../components"

// FinanceW dock identity only. No menu or finance backend is attached yet.
// The shared DockButton owns pointer, hover, pressed, and glow behavior.
DockButton {
    id: financeDock

    implicitHeight: 50
    implicitWidth: Math.max(80, Math.ceil(financeMark.implicitWidth) + 24)

    // White decorations, green coin pair; both dock and artwork glow Omnitrix.
    normalForegroundColor: Colors.white
    hoverForegroundColor: Colors.white
    pressedForegroundColor: Colors.white
    openForegroundColor: Colors.white

    normalContentGlowColor: Colors.omnitrix
    hoverContentGlowColor: Colors.omnitrix
    pressedContentGlowColor: Colors.omnitrix
    normalDockGlowColor: Colors.omnitrix
    hoverDockGlowColor: Colors.omnitrix
    pressedDockGlowColor: Colors.omnitrix
    openGlowColor: Colors.omnitrix

    contentGlowSource: financeMark

    NotoText {
        id: financeMark
        anchors.centerIn: parent
        text: "˗ˋˏ˖<font color='" + Colors.green + "'>⛁⛀</font>๋࣭⭑ˎˊ˗"
        textFormat: Text.StyledText
        font.pixelSize: 21
        color: financeDock.foregroundColor
    }

    // No onLeftClicked handler until FinanceW's menu is approved.
}
