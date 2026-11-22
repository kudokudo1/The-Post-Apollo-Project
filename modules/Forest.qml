import QtQuick
import Quickshell
import "../components"

// FOREST // AI/automation: Sub-Omnitrix green artwork and self-colored glow.
// Decorative stars stay white until the widget is open, then turn magenta.
// Shared DockButton owns the selected yellow fill, click, and outer halo.
DockButton {
    id: dock

    property bool menuOpen: false
    signal toggleRequested()
    readonly property int iconPadding: 10
    readonly property color starColor: dock.open ? Colors.magenta : Colors.white

    // Standard 50px rail height. The icon lives in the centered 30x30
    // content square, leaving the same 10px padding on all four sides.
    implicitWidth: 50
    implicitHeight: 50
    radius: 0
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
    // Sample only the campsite so the WHITE idle stars are not green-glowed.
    contentGlowSource: tentFace
    trackArtworkGlowLocally: true

    Item {
        id: forestArtwork
        width: dock.width - 2 * dock.iconPadding
        height: dock.height - 2 * dock.iconPadding
        anchors.centerIn: parent

        GohuText {
            id: tentFace
            anchors.centerIn: parent
            textFormat: Text.PlainText
            text: "🏕"
            font.pixelSize: 23
            color: dock.foregroundColor
        }

        // Star decoration is independent of the green tent foreground.
        // Keep both marks inside the same centered artwork footprint,
        // tucked above the tent instead of extending the dock width.
        GohuText {
            id: upperLeftStars
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.topMargin: -1
            textFormat: Text.PlainText
            text: "࣪݁✧"
            font.pixelSize: 11
            color: dock.starColor
        }

        GohuText {
            id: upperRightStars
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.topMargin: -1
            textFormat: Text.PlainText
            text: "๋⭑"
            font.pixelSize: 12
            color: dock.starColor
        }
    }

    onLeftClicked: toggleRequested()
}
