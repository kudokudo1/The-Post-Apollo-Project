import QtQuick
import "../components"

// ANGEL // STABLE COLOR WASH BY IDENTITY.
// Angel observation rows keep their permanent category-color washes.
// Small controls (favorite, note +, filters) may opt out of the wash.
// Open/selected navigation uses yellow with magenta ink/glow instead.
// A fully opaque blend prevents translucent compositing changes while scrolling.
// The shared ActionButton's broad rectangular shadows remain disabled.
ActionButton {
    id: angelButton

    readonly property color baseFillColor: Colors.black
    readonly property color activeFillColor: Colors.yellow
    readonly property real washStrength: 0.24
    readonly property color steadyWashColor: Qt.rgba(
        baseFillColor.r * (1.0 - washStrength) + accentColor.r * washStrength,
        baseFillColor.g * (1.0 - washStrength) + accentColor.g * washStrength,
        baseFillColor.b * (1.0 - washStrength) + accentColor.b * washStrength,
        1.0
    )
    // Selected means OPEN only when this control explicitly opts in.
    // Stars and ERR markers use selected for their status, not navigation.
    property bool highlightWhenSelected: false
    property bool washByDefault: true
    readonly property color defaultFillColor:
        washByDefault ? steadyWashColor : baseFillColor

    idleFillColor: defaultFillColor
    hoverFillColor: defaultFillColor
    pressedFillColor: defaultFillColor
    selectedFillColor: highlightWhenSelected ? activeFillColor : defaultFillColor
    keyboardSelectedFillColor: defaultFillColor

    // Static default for idle/hover/press/focus, never a transient wash.
    // Yellow remains a deliberate OPEN/SELECT state only.
    color: highlightWhenSelected && selected ? activeFillColor : defaultFillColor

    selectedForegroundColor: Colors.magenta
    selectedBorderColor: Colors.magenta
    selectedContentGlowColor: Colors.magenta

    // RectangularShadow is a filled shadow shape, not an outline-only
    // stroke. On the history ListView its full-rectangle accent tint can
    // become visible during scrolling/compositing despite a black Rectangle.
    // Keep the text/glow identity but remove these broad-area shadow layers.
    softGlowEnabled: false
    wideGlowEnabled: false
    contentGlowEnabled: true

    hoverForegroundColor: selected ? selectedForegroundColor : idleForegroundColor
    pressedForegroundColor: selected ? selectedForegroundColor : idleForegroundColor
    hoverBorderColor: selected ? selectedBorderColor : idleBorderColor
    pressedBorderColor: selected ? selectedBorderColor : idleBorderColor

    hoverContentGlowColor: selected ? selectedContentGlowColor : idleContentGlowColor
    pressedContentGlowColor: selected ? selectedContentGlowColor : idleContentGlowColor
    hoverSoftGlowColor: selected ? selectedSoftGlowColor : idleSoftGlowColor
    pressedSoftGlowColor: selected ? selectedSoftGlowColor : idleSoftGlowColor
}
