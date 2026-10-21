import QtQuick
import Quickshell
import "../components"

// ApolloHubW's center dock inherits Calendar's three-part ornament;
// clicking it opens the Hub once the shell mounts the paired window.
DockButton {
    id: dock

    property bool menuOpen: false
    signal toggleRequested()

    implicitWidth: 113
    implicitHeight: 50
    radius: 7
    open: menuOpen

    // Keep all three glyphs white/orange regardless of button state; preserve
    // independent magenta neon for the dock chassis and entire artwork.
    normalForegroundColor: Colors.white
    hoverForegroundColor: Colors.white
    pressedForegroundColor: Colors.white
    openForegroundColor: Colors.white

    normalDockGlowColor: Colors.magenta
    hoverDockGlowColor: Colors.magenta
    pressedDockGlowColor: Colors.magenta
    openGlowColor: Colors.magenta

    normalContentGlowColor: Colors.magenta
    hoverContentGlowColor: Colors.magenta
    pressedContentGlowColor: Colors.magenta
    contentGlowSource: hubMark

    // Keep the Unicode ornaments and emoji in ONE run to retain the original
    // Calendar text shaping and avoid doubled, separately sampled glow planes.
    NotoText {
        id: hubMark
        anchors.centerIn: parent
        textFormat: Text.StyledText
        text: " ⌯⌲ <font color='" + Colors.orange + "'>🗓</font> ⋆˙⟡ "
        font.pixelSize: 20
        color: Colors.white
    }

    onLeftClicked: toggleRequested()
}
