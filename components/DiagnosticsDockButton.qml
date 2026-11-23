import QtQuick

// Shared Weather + Finance diagnostics toggle. The owning widget alone
// decides when the service inspector opens/closes; the button is presentation
// and input only, with the same three glow intensities as × and resize arrows.
ActionButton {
    id: diagnosticButton
    property bool diagnosticsOpen: false
    signal toggleRequested()

    // Keep the established header footprint. Styled artwork preserves the
    // white decorative stars independently of the medical glyph's state hue.
    width: 59
    height: 32
    label: "<font color='" + Colors.white + "'>˖</font>"
           + "<font color='" + diagnosticButton.foregroundColor + "'>⚕๋࣭</font>"
           + "<font color='" + Colors.white + "'>⭑</font>"
    labelItem.textFormat: Text.StyledText
    labelPixelSize: 21
    labelFontSizeMode: Text.Fit
    labelMinimumPixelSize: 13
    contentPadding: 2
    labelElide: Text.ElideNone

    selected: diagnosticsOpen
    accentColor: Colors.yellow
    acceptedButtons: Qt.LeftButton

    // Match the canonical CloseButton / ResizeButton color and glow grammar.
    // Only the diagnostics icon keeps its yellow/magenta semantic identity.
    idleFillColor: Colors.black
    hoverFillColor: Colors.yellow
    pressedFillColor: accentColor
    selectedFillColor: Colors.yellow
    keyboardSelectedFillColor: Colors.yellow

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

    trackLabelGlowLocally: true
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
