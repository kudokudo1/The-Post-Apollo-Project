import QtQuick
import Quickshell
import "../components"

// FinanceW dock identity only. No menu or finance backend is attached yet.
// The shared DockButton owns pointer, hover, pressed, and glow behavior.
DockButton {
    id: financeDock

    implicitHeight: 50
    implicitWidth: Math.max(110, Math.ceil(financeMark.implicitWidth) + 20)

    // The glyph is sub-Omnitrix green; every green glow uses Omnitrix.
    normalForegroundColor: Colors.green
    hoverForegroundColor: Colors.green
    pressedForegroundColor: Colors.green
    openForegroundColor: Colors.green

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
        text: "˗ˋˏ˖⛀⛁ ⛁⛀๋࣭⭑ˎˊ˗"
        textFormat: Text.PlainText
        font.pixelSize: 21
        color: financeDock.foregroundColor
    }

    // No onLeftClicked handler until FinanceW's menu is approved.
}
