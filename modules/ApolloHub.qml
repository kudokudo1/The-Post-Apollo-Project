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

    // Preserve white ornaments, magenta Calendar glyph, and magenta artwork.
    // Only the idle rear/wide dock halo is orange; active states remain magenta.
    normalForegroundColor: Colors.white
    hoverForegroundColor: Colors.white
    pressedForegroundColor: Colors.white
    openForegroundColor: Colors.white

    normalDockGlowColor: Colors.orange
    hoverDockGlowColor: Colors.magenta
    pressedDockGlowColor: Colors.magenta
    openGlowColor: Colors.magenta

    normalContentGlowColor: Colors.magenta
    hoverContentGlowColor: Colors.magenta
    pressedContentGlowColor: Colors.magenta
    contentGlowSource: hubMark
    trackArtworkGlowLocally: true

    // Keep the Unicode ornaments and emoji in ONE run to retain the original
    // Calendar text shaping and avoid doubled, separately sampled glow planes.
    NotoText {
        id: hubMark
        anchors.centerIn: parent
        textFormat: Text.StyledText
        text: " ⌯⌲ <font color='" + Colors.magenta + "'>🗓</font> ⋆˙⟡ "
        font.pixelSize: 20
        color: Colors.white
    }

    onLeftClicked: toggleRequested()
}
