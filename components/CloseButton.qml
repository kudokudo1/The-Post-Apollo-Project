import QtQuick

// Universal ordinary window-close ×. This is presentation and input only:
// each owning widget handles its own close/cleanup on closeRequested.
//
// Design: Finance 17:16 frame and three glow planes; CPU++-style independent
// glyph illumination using ActionButton's source-aligned SafeDropShadow;
// Weather/Apollo Hub persistent RED glyph/border identity during hover.
// This component is deliberately NOT semantically destructive.
ActionButton {
    id: closeButton

    // Finance baseline. Scaling width preserves the exact 17:16 shape.
    implicitWidth: 34
    implicitHeight: 32
    width: implicitWidth
    height: width * 16 / 17

    // Finance placement guidelines belong to the parent, not the hit target.
    // Siblings supply the 7px gap and the menu supplies its 10px/12px insets.
    readonly property int recommendedLeftGap: 7
    readonly property int recommendedRightInset: 10
    readonly property int recommendedVerticalClearance: 12

    label: "×" // U+00D7, never a letter X
    labelPixelSize: Math.round(width * 22 / 34)
    contentPadding: 4
    acceptedButtons: Qt.LeftButton
    Accessible.name: "Close"

    destructive: false
    accentColor: Colors.red

    // Surface and foreground remain separate from the permanent red glow.
    idleFillColor: Colors.black
    hoverFillColor: Colors.yellow
    pressedFillColor: Colors.red
    selectedFillColor: Colors.yellow
    keyboardSelectedFillColor: Colors.yellow

    idleForegroundColor: Colors.red
    hoverForegroundColor: Colors.red
    pressedForegroundColor: Colors.black
    selectedForegroundColor: Colors.red
    keyboardSelectedForegroundColor: Colors.red

    idleBorderColor: Colors.red
    hoverBorderColor: Colors.red
    pressedBorderColor: Colors.black
    selectedBorderColor: Colors.red
    keyboardSelectedBorderColor: Colors.red
    idleBorderWidth: 1
    hoverBorderWidth: 1
    pressedBorderWidth: 1
    selectedBorderWidth: 1

    radius: 0
    clip: false

    // Independent, EXACTLY source-aligned glyph illumination. ActionButton
    // owns one guarded SafeDropShadow sampling its actual rendered label;
    // do not draw a second × or attach an unguarded DropShadow to this item.
    trackLabelGlowLocally: true
    contentGlowEnabled: true
    idleContentGlowColor: Colors.red
    hoverContentGlowColor: Colors.red
    pressedContentGlowColor: Colors.red
    selectedContentGlowColor: Colors.red
    keyboardSelectedContentGlowColor: Colors.red
    contentGlowRadius: 7
    contentGlowSamples: 7
    contentGlowIdleOpacity: 0.34
    contentGlowHoverOpacity: 0.72
    contentGlowPressedOpacity: 1.0
    contentGlowSelectedOpacity: 0.72
    contentGlowKeyboardSelectedOpacity: 0.72

    // Finance soft perimeter halo. Red identity persists on hover/press.
    softGlowEnabled: true
    softGlowSpread: 3
    softGlowMargin: 0
    idleSoftGlowColor: Colors.red
    hoverSoftGlowColor: Colors.red
    pressedSoftGlowColor: Colors.red
    selectedSoftGlowColor: Colors.red
    keyboardSelectedSoftGlowColor: Colors.red
    softGlowIdleOpacity: 0.48
    softGlowHoverOpacity: 0.70
    softGlowPressedOpacity: 1.0
    softGlowSelectedOpacity: 0.70
    softGlowKeyboardSelectedOpacity: 0.70

    // Finance wide perimeter halo, always on while the button is visible.
    wideGlowEnabled: true
    wideGlowSpread: 10
    idleWideGlowColor: Colors.red
    hoverWideGlowColor: Colors.red
    pressedWideGlowColor: Colors.red
    selectedWideGlowColor: Colors.red
    keyboardSelectedWideGlowColor: Colors.red
    wideGlowIdleOpacity: 0.22
    wideGlowHoverOpacity: 0.32
    wideGlowPressedOpacity: 1.0
    wideGlowSelectedOpacity: 0.32
    wideGlowKeyboardSelectedOpacity: 0.32

    // A close request is not authority to destroy records or kill processes.
    signal closeRequested()
    onLeftClicked: closeButton.closeRequested()
}
