import QtQuick
import "../components"

// ANGEL // STABLE COLOR WASH BY IDENTITY.
// Every Angel button is always gently washed with its own accent color.
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

    idleFillColor: steadyWashColor
    hoverFillColor: steadyWashColor
    pressedFillColor: steadyWashColor
    selectedFillColor: highlightWhenSelected ? activeFillColor : steadyWashColor
    keyboardSelectedFillColor: steadyWashColor

    // One deterministic color per control identity. Mouse/scroll/focus
    // cannot turn a different or stale fill on. Selection alone overrides
    // the default wash with solid yellow for opt-in navigation controls.
    color: highlightWhenSelected && selected ? activeFillColor : steadyWashColor

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
