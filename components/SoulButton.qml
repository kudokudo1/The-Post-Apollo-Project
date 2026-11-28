import QtQuick

// Joy / Soul: contextual creator information. The owner retains popup state
// and click handlers. Use the ordinary ActionButton input and glow lifecycle.
ActionButton {
    id: root
    width: 24
    height: 22
    label: "i"
    showLabel: false
    contentPadding: 2
    accentColor: Colors.yellow
    idleForegroundColor: Colors.white
    hoverForegroundColor: Colors.orange
    selectedForegroundColor: Colors.magenta
    idleContentGlowColor: Colors.magenta
    hoverContentGlowColor: Colors.magenta
    pressedContentGlowColor: Colors.magenta
    selectedContentGlowColor: Colors.magenta
    keyboardSelectedContentGlowColor: Colors.magenta
    idleSoftGlowColor: Colors.magenta
    hoverSoftGlowColor: Colors.magenta
    pressedSoftGlowColor: Colors.magenta
    selectedSoftGlowColor: Colors.magenta
    keyboardSelectedSoftGlowColor: Colors.magenta
    contentGlowIdleOpacity: 0.85
    contentGlowSource: soulArtwork
    // Keep the normal ActionButton wash-safe perimeter and state fills.
    // Artwork has fixed semantic colors, including in selected state.
    acceptedButtons: Qt.LeftButton
    keyboardActivationSignal: "leftClicked"
    Accessible.name: "Information"

    Image {
        id: soulArtwork
        anchors.centerIn: parent
        width: Math.max(0, parent.width - root.contentPadding)
        height: Math.max(0, parent.height - root.contentPadding)
        source: Qt.resolvedUrl("../assets/prism/soul-joy.svg")
        fillMode: Image.PreserveAspectFit
        smooth: true
        mipmap: true
        sourceSize.width: Math.max(1, Math.min(256, Math.ceil(width * 2)))
        sourceSize.height: Math.max(1, Math.min(256, Math.ceil(height * 2)))
    }
}
