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

    // Composite glyph kept in one measured 50x40 box. Separately anchored
    // ornamental marks stay above / close to the camp regardless of fallback
    // font advances. Do not add literal spaces between the glyphs.
    Item {
        id: forestMark
        width: 50
        height: 40
        anchors.centerIn: parent

        NotoText {
            id: campFace
            anchors.centerIn: parent
            text: "🏕"
            font.pixelSize: 29
            color: dock.foregroundColor
        }

        GohuText {
            id: leftStars
            anchors.right: campFace.left
            anchors.rightMargin: -7
            anchors.top: campFace.top
            anchors.topMargin: -6
            textFormat: Text.PlainText
            text: "࣪݁"
            font.pixelSize: 16
            color: dock.foregroundColor
        }

        GohuText {
            id: rightStars
            anchors.left: campFace.right
            anchors.leftMargin: -8
            anchors.top: campFace.top
            anchors.topMargin: -6
            textFormat: Text.PlainText
            text: "๋⭑"
            font.pixelSize: 16
            color: dock.foregroundColor
        }
    }

    onLeftClicked: toggleRequested()
}
