import QtQuick
import "../components"

// ANGEL // EXPLICIT SELECTION COLOR ONLY.
// Idle/hover/press/focus remain black; only a navigation or history action
// explicitly opted into selection highlighting gets a yellow background.
// Favorite membership and ERR status are not navigation selections.
// Keep this local: the shared button's broad glows are unsafe for Angel rows.
ActionButton {
    id: angelButton

    readonly property color fixedFillColor: Colors.black
    readonly property color activeFillColor: Colors.yellow
    // Only OPEN/SELECT navigation explicitly enables the selection wash.
    property bool highlightWhenSelected: false

    idleFillColor: fixedFillColor
    hoverFillColor: fixedFillColor
    pressedFillColor: fixedFillColor
    selectedFillColor: activeFillColor
    keyboardSelectedFillColor: fixedFillColor

    // Never use the shared hover/press/keyboard fill-state dispatcher.
    // List scrolling cannot accidentally produce a colored background.
    color: highlightWhenSelected && selected ? activeFillColor : fixedFillColor

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
