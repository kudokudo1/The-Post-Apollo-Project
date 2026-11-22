import QtQuick

// Ordinary window-chassis size-step arrows. Presentation/input only:
// consumers keep ownership of their actual size levels, window geometry,
// unsaved edits and keyboard focus. A request must not resize by itself.
//
// Shared optical alignment and input inherit ActionButton. The visual states
// intentionally mirror CloseButton's three-plane, persistent identity recipe:
// hover keeps the directional color on icon/border/glows; press fills with it
// while the icon and border turn black. Actual resizing stays consumer-owned.
ActionButton {
    id: resizeButton

    // Supported direction values: "left", "up", "down", "right".
    // Left/down decrease; up/right increase.
    property string direction: "down"
    readonly property bool directionValid:
        direction === "left" || direction === "up"
        || direction === "down" || direction === "right"
    readonly property bool increasing:
        direction === "up" || direction === "right"
    readonly property int sizeDelta: increasing ? 1 : -1

    // Canonical orange for decreasing; purple is not in Colors yet, so keep
    // the existing approved purple swatch local and overridable.
    property color decreaseAccentColor: Colors.orange
    property color increaseAccentColor: "#A46AFF"

    implicitWidth: 30
    implicitHeight: 30
    width: implicitWidth
    height: width  // 1:1, including a 28px compact-width override

    label: direction === "left" ? "⮜"
           : direction === "up" ? "⮝"
           : direction === "right" ? "⮞"
           : "⮟"
    labelPixelSize: 17

    // ActionButton centers the line layout, but an arrow's actual ink can sit
    // above/below or to one side of that box depending on font fallback.
    // Center the measured glyph bounds for ALL four arrows, at any button
    // width; the base label and its sampled glow still move together.
    TextMetrics {
        id: arrowInk
        font: resizeButton.labelItem.font
        text: resizeButton.label
    }
    readonly property rect glyphInkBounds: arrowInk.tightBoundingRect
    readonly property real glyphAdvanceWidth: arrowInk.advanceWidth
    labelCenterOffsetX:
        glyphAdvanceWidth / 2
        - glyphInkBounds.x - glyphInkBounds.width / 2
    labelCenterOffsetY:
        resizeButton.labelItem.height / 2
        - resizeButton.labelItem.baselineOffset
        - glyphInkBounds.y - glyphInkBounds.height / 2

    accentColor: increasing ? increaseAccentColor : decreaseAccentColor

    // Match the shared CloseButton behavior, with the arrow's own orange or
    // purple identity persisting on the text, perimeter, and all glow planes.
    // Hover uses a yellow surface. Press uses the semantic color as the fill
    // with a black arrow and black border. Selection mirrors hover.
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

    // Source-aligned glyph glow keeps sampling the actual centered arrow,
    // including while the icon is black over the colored pressed fill.
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

    interactive: available && directionValid
    Accessible.name: increasing ? "Increase window size" : "Decrease window size"

    // The three existing ActionButton shadow implementations remain the only
    // effect sources. No copy of the arrow, extra MouseArea, or resize engine.
    signal resizeRequested(int delta)
    onLeftClicked: {
        if (directionValid)
            resizeButton.resizeRequested(sizeDelta);
    }
}
