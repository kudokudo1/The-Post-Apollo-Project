import QtQuick
import Quickshell
import "../components"

// Company Network dock identity. No data loading or company access occurs here.
// The owning CompanyNetworkW window controls the open/closed state.
DockButton {
    id: companyDock

    property bool menuOpen: false
    signal toggleRequested()

    implicitHeight: 50
    implicitWidth: Math.max(86, Math.ceil(companyMark.implicitWidth) + 22)
    open: menuOpen

    // Yellow identity, independently blue sampled artwork and dock halos.
    normalForegroundColor: Colors.yellow
    hoverForegroundColor: Colors.yellow
    pressedForegroundColor: Colors.yellow
    openForegroundColor: Colors.blue

    normalContentGlowColor: Colors.blue
    hoverContentGlowColor: Colors.blue
    pressedContentGlowColor: Colors.blue
    normalDockGlowColor: Colors.blue
    hoverDockGlowColor: Colors.blue
    pressedDockGlowColor: Colors.blue
    openGlowColor: Colors.blue

    // Maintain the canonical selected yellow fill, using blue artwork for
    // legibility rather than yellow-on-yellow while the widget is open.
    openFillColor: Colors.yellow
    contentGlowSource: companyMark

    NotoText {
        id: companyMark
        anchors.centerIn: parent
        textFormat: Text.PlainText
        text: ". ݁₊⊹🏙๋࣭⭑"
        font.pixelSize: 22
        color: companyDock.foregroundColor
    }

    onLeftClicked: toggleRequested()
}
