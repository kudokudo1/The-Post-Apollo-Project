import QtQuick

// Shared Weather + Finance diagnostics toggle. The owning widget alone
// decides when the service inspector opens/closes; the button is presentation
// and input only, with the same three glow intensities as × and resize arrows.
ActionButton {
    id: diagnosticButton
    property bool diagnosticsOpen: false
    signal toggleRequested()

    // Tight optical cluster: the glyphs are separately positioned, so font
    // advance whitespace cannot push the small left star away from the staff.
    // Decorators are explicit WHITE Text items, including the two ornaments
    // previously encoded as colored combining marks inside "⚕๋࣭".
    width: 38
    height: 32
    label: ""
    Item {
        id: diagnosticsArtwork
        anchors.centerIn: parent
        width: 30
        height: 26

        Text {
            id: diagnosticsMedicalSymbol
            anchors.centerIn: parent
            text: "⚕"
            textFormat: Text.PlainText
            color: diagnosticButton.foregroundColor
            font.pixelSize: 21
        }

        Text {
            id: diagnosticsLeftStar
            text: "˖"
            textFormat: Text.PlainText
            color: diagnosticButton.diagnosticsOpen ? Colors.magenta : Colors.white
            font.pixelSize: 14
            anchors.right: diagnosticsMedicalSymbol.left
            // Pull the actual ink toward the staff despite fallback bearings.
            anchors.rightMargin: -6
            anchors.verticalCenter: diagnosticsMedicalSymbol.verticalCenter
        }

        Text {
            id: diagnosticsUpperStar
            text: "✦"
            textFormat: Text.PlainText
            color: diagnosticButton.diagnosticsOpen ? Colors.magenta : Colors.white
            font.pixelSize: 8
            anchors.left: diagnosticsMedicalSymbol.right
            anchors.leftMargin: -6
            anchors.top: diagnosticsMedicalSymbol.top
        }

        Text {
            id: diagnosticsRightStar
            text: "⭑"
            textFormat: Text.PlainText
            color: diagnosticButton.diagnosticsOpen ? Colors.magenta : Colors.white
            font.pixelSize: 10
            anchors.left: diagnosticsMedicalSymbol.right
            anchors.leftMargin: -4
            anchors.bottom: diagnosticsMedicalSymbol.bottom
            anchors.bottomMargin: -1
        }
    }

    // Reuse the existing ActionButton glow on the medical symbol alone.
    // No duplicate glyph and no orange/yellow tint added to white stars.
    contentGlowSource: diagnosticsMedicalSymbol
    trackLabelGlowLocally: true

    selected: diagnosticsOpen
    // Selection is an actual OPEN/activated button: yellow fill with
    // magenta ink, stars, border and every sampled/outer glow plane.
    // Closed idle/hover/pressed keep the TimeW RESYNC order unchanged.
    // Match TimeW's actual RESYNC / ReloadButton color order:
    // YELLOW semantic icon/border/glows; ORANGE hover/selected surface.
    property color semanticColor: Colors.yellow
    property color hoverSurfaceColor: Colors.orange
    accentColor: semanticColor
    acceptedButtons: Qt.LeftButton

    // Reuse the existing three-plane glow strengths. The icon's COLOR
    // order follows ReloadButton, not the downward ResizeButton.
    idleFillColor: Colors.black
    hoverFillColor: hoverSurfaceColor
    pressedFillColor: accentColor
    selectedFillColor: Colors.yellow
    keyboardSelectedFillColor: hoverSurfaceColor

    idleForegroundColor: accentColor
    hoverForegroundColor: accentColor
    pressedForegroundColor: Colors.black
    selectedForegroundColor: Colors.magenta
    keyboardSelectedForegroundColor: accentColor

    idleBorderColor: accentColor
    hoverBorderColor: accentColor
    pressedBorderColor: Colors.black
    selectedBorderColor: Colors.magenta
    keyboardSelectedBorderColor: accentColor
    idleBorderWidth: 1
    hoverBorderWidth: 1
    pressedBorderWidth: 1
    selectedBorderWidth: 1
    keyboardSelectedBorderWidth: 1

    contentGlowEnabled: true
    idleContentGlowColor: accentColor
    hoverContentGlowColor: accentColor
    pressedContentGlowColor: accentColor
    selectedContentGlowColor: Colors.magenta
    keyboardSelectedContentGlowColor: accentColor
    contentGlowRadius: 7
    contentGlowSamples: 7
    contentGlowIdleOpacity: 0.34
    contentGlowHoverOpacity: 0.72
    contentGlowPressedOpacity: 1.0
    contentGlowSelectedOpacity: 0.72
    contentGlowKeyboardSelectedOpacity: 0.72

    softGlowEnabled: true
    softGlowSpread: 3
    softGlowMargin: 0
    idleSoftGlowColor: accentColor
    hoverSoftGlowColor: accentColor
    pressedSoftGlowColor: accentColor
    selectedSoftGlowColor: Colors.magenta
    keyboardSelectedSoftGlowColor: accentColor
    softGlowIdleOpacity: 0.48
    softGlowHoverOpacity: 0.70
    softGlowPressedOpacity: 1.0
    softGlowSelectedOpacity: 0.70
    softGlowKeyboardSelectedOpacity: 0.70

    wideGlowEnabled: true
    wideGlowSpread: 10
    idleWideGlowColor: accentColor
    hoverWideGlowColor: accentColor
    pressedWideGlowColor: accentColor
    selectedWideGlowColor: Colors.magenta
    keyboardSelectedWideGlowColor: accentColor
    wideGlowIdleOpacity: 0.22
    wideGlowHoverOpacity: 0.32
    wideGlowPressedOpacity: 1.0
    wideGlowSelectedOpacity: 0.32
    wideGlowKeyboardSelectedOpacity: 0.32

    radius: 0
    clip: false
    Accessible.name: diagnosticsOpen ? "Close diagnostics" : "Open diagnostics"
    keyboardActivationSignal: "leftClicked"
    onLeftClicked: diagnosticButton.toggleRequested()
}
