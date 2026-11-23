import QtQuick

// Shared Weather + Finance diagnostics toggle. The owning widget alone
// decides when the service inspector opens/closes; the button is presentation
// and input only, with the same three glow intensities as × and resize arrows.
ActionButton {
    id: diagnosticButton
    property bool diagnosticsOpen: false
    signal toggleRequested()

    // Keep the existing header footprint. Three separately painted glyphs
    // stop rich-text fallback and tinting from coloring either white star.
    // The slight overlap keeps the smaller left star close to the medical mark.
    width: 59
    height: 32
    label: ""
    Item {
        id: diagnosticsArtwork
        anchors.centerIn: parent
        width: diagnosticsSymbols.implicitWidth
        height: 27

        Row {
            id: diagnosticsSymbols
            anchors.centerIn: parent
            spacing: -2

            Text {
                id: diagnosticsLeftStar
                text: "˖"
                textFormat: Text.PlainText
                color: Colors.white
                font.pixelSize: 16
                height: diagnosticsArtwork.height
                verticalAlignment: Text.AlignVCenter
            }

            Text {
                id: diagnosticsMedicalSymbol
                text: "⚕๋࣭"
                textFormat: Text.PlainText
                color: diagnosticButton.foregroundColor
                font.pixelSize: 21
                height: diagnosticsArtwork.height
                verticalAlignment: Text.AlignVCenter
            }

            Text {
                id: diagnosticsRightStar
                text: "⭑"
                textFormat: Text.PlainText
                color: Colors.white
                font.pixelSize: 15
                height: diagnosticsArtwork.height
                verticalAlignment: Text.AlignVCenter
            }
        }
    }

    // Sample only the medical glyph. The separate white stars should not
    // inherit its orange/magenta shadow or change with hover/press.
    contentGlowSource: diagnosticsMedicalSymbol
    trackLabelGlowLocally: true

    selected: diagnosticsOpen
    // Same semantic identity as ResizeButton's downward arrow. Hover is
    // yellow fill with ORANGE glyph, border and all glow planes.
    accentColor: Colors.orange
    acceptedButtons: Qt.LeftButton

    // Match the canonical CloseButton / ResizeButton glow geometry and
    // downward arrow colors. The two decorative stars stay white.
    idleFillColor: Colors.black
    hoverFillColor: Colors.yellow
    pressedFillColor: accentColor
    selectedFillColor: Colors.yellow
    keyboardSelectedFillColor: Colors.yellow

    idleForegroundColor: accentColor
    hoverForegroundColor: accentColor
    pressedForegroundColor: Colors.black
    selectedForegroundColor: accentColor
    keyboardSelectedForegroundColor: accentColor

    idleBorderColor: accentColor
    hoverBorderColor: accentColor
    pressedBorderColor: Colors.black
    selectedBorderColor: accentColor
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
    selectedContentGlowColor: accentColor
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
    selectedSoftGlowColor: accentColor
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
    selectedWideGlowColor: accentColor
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
