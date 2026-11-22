import QtQuick
import Quickshell
import "../components"

// FOREST V0 // AI / automation identity uses Sub-Omnitrix green throughout
// the closed dock. The canonical yellow fill and magenta open-state survive.
DockButton {
    id: dock
    property bool menuOpen: false
    signal toggleRequested()

    implicitWidth: 72
    implicitHeight: 50
    open: menuOpen

    normalForegroundColor: Colors.green
    hoverForegroundColor: Colors.green
    pressedForegroundColor: Colors.green
    openForegroundColor: Colors.magenta

    normalDockGlowColor: Colors.green
    hoverDockGlowColor: Colors.green
    pressedDockGlowColor: Colors.green
    openGlowColor: Colors.magenta

    normalContentGlowColor: Colors.green
    hoverContentGlowColor: Colors.green
    pressedContentGlowColor: Colors.green
    contentGlowSource: forestMark
    trackArtworkGlowLocally: true

    // One Gohu shaping run: the stars stay adjacent to the campsite,
    // rather than being independently offset by fallback-font geometry.
    // Emoji glyph fallback is owned by Qt, but the requested text item,
    // ornament metrics and glow source all use GohuText.
    GohuText {
        id: forestMark
        anchors.centerIn: parent
        anchors.verticalCenterOffset: -2
        textFormat: Text.PlainText
        text: "࣪݁🏕๋⭑"
        font.pixelSize: 25
        font.letterSpacing: -1
        color: dock.foregroundColor
    }

    onLeftClicked: toggleRequested()
}
