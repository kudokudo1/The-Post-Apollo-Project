import QtQuick
import "../components"

// ANGEL // ONE BACKGROUND COLOR.
// The shared ActionButton normally uses state-dependent fills. Angel does not:
// idle, hover, press, keyboard focus, selection and favorite all paint black.
// State remains visible in text, border and glow, never in the background.
// This is intentionally scoped to Angel rather than shared ActionButton.
ActionButton {
    id: angelButton

    readonly property color fixedFillColor: Colors.black
    idleFillColor: fixedFillColor
    hoverFillColor: fixedFillColor
    pressedFillColor: fixedFillColor
    selectedFillColor: fixedFillColor
    keyboardSelectedFillColor: fixedFillColor

    // Final painted surface is independent of fillColor's state machine.
    // Scrolling/reusing ListView delegates cannot restore a colored wash.
    color: fixedFillColor

    hoverForegroundColor: selected ? selectedForegroundColor : idleForegroundColor
    pressedForegroundColor: selected ? selectedForegroundColor : idleForegroundColor
    hoverBorderColor: selected ? selectedBorderColor : idleBorderColor
    pressedBorderColor: selected ? selectedBorderColor : idleBorderColor

    hoverContentGlowColor: selected ? selectedContentGlowColor : idleContentGlowColor
    pressedContentGlowColor: selected ? selectedContentGlowColor : idleContentGlowColor
    hoverSoftGlowColor: selected ? selectedSoftGlowColor : idleSoftGlowColor
    pressedSoftGlowColor: selected ? selectedSoftGlowColor : idleSoftGlowColor
}
