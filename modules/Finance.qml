import QtQuick
import Quickshell
import "../components"

// FinanceW dock identity. The menu is a blank portrait chassis; no backend.
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
    // Open button: canonical yellow surface with a magenta halo.
    openFillColor: Colors.yellow
    openGlowColor: Colors.magenta

    contentGlowSource: financeMark

    NotoText {
        id: financeMark
        anchors.centerIn: parent
        text: "˗ˋˏ˖<font color='" + Colors.green + "'>⛁⛀</font>๋࣭⭑ˎˊ˗"
        textFormat: Text.StyledText
        font.pixelSize: 21
        color: financeDock.foregroundColor
    }

    // The window owns its open state; DockButton supplies the default click
    // and selected-state behavior without a second MouseArea.
    property bool menuOpen: false
    signal toggleRequested()
    open: menuOpen

    onLeftClicked: toggleRequested()
}
