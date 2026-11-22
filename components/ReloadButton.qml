import QtQuick

// Reusable reload/refresh glyph control. Its owner decides what "reload"
// actually does: this component never changes time, restarts a service, or
// triggers a host operation by itself.
//
// Share the CloseButton's source-aligned three-layer glow grammar but keep
// the action's SEMANTIC hue in the glyph, border, and every glow state.
// For TimeW, yellow stays the reload identity while the hover/selected
// surface becomes orange, intentionally distinct from the Close ×.
ActionButton {
    id: reloadButton

    property color semanticColor: Colors.yellow
    property color hoverSurfaceColor: Colors.orange

    // Preserve the existing TimeW header footprint and reload glyph.
    implicitWidth: 35
    implicitHeight: 32
    width: implicitWidth
    height: implicitHeight

    label: "⟳"
    labelPixelSize: 22
    contentPadding: 3
    acceptedButtons: Qt.LeftButton
    Accessible.name: "Reload"

    destructive: false
    accentColor: semanticColor

    idleFillColor: Colors.black
    hoverFillColor: hoverSurfaceColor
    pressedFillColor: accentColor
    selectedFillColor: hoverSurfaceColor
    keyboardSelectedFillColor: hoverSurfaceColor

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

    radius: 0
    clip: false

    // Use ActionButton's original rendered glyph as the shadow source.
    // No second glyph, unguarded shadow, or independent pointer handler.
    trackLabelGlowLocally: true
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

    signal reloadRequested()
    onLeftClicked: reloadButton.reloadRequested()
}
