import QtQuick
import "../components"

// ANGEL-local outline-first action. Standard ActionButton paints a new color
// on hover/press, which turns an otherwise neutral entire rail into filled
// controls while pointer events move across them. Keep the idle surface when
// unselected; selected states may retain their intentional color wash.
ActionButton {
    id: angelButton

    idleFillColor: Colors.black
    hoverFillColor: selected ? selectedFillColor : idleFillColor
    pressedFillColor: selected ? selectedFillColor : idleFillColor
    // The shared ActionButton has a separate keyboard-selection branch that
    // previously fell back to selectedFillColor even when selected was false.
    keyboardSelectedFillColor: selected ? selectedFillColor : idleFillColor

    // Paint from semantic selection only. Hover, press and keyboard focus
    // cannot wash unrelated entries, even if a state remains set during
    // ListView delegate reuse or pointer transitions. A favorite observation
    // can still provide its magenta-tinted idleFillColor.
    color: angelButton.withOpacity(
        angelButton.selected
            ? angelButton.selectedFillColor : angelButton.idleFillColor,
        angelButton.available ? 1.0 : angelButton.unavailableFillOpacity
    )

    hoverForegroundColor: selected ? selectedForegroundColor : idleForegroundColor
    pressedForegroundColor: selected ? selectedForegroundColor : idleForegroundColor
    hoverBorderColor: selected ? selectedBorderColor : idleBorderColor
    pressedBorderColor: selected ? selectedBorderColor : idleBorderColor

    hoverContentGlowColor: selected ? selectedContentGlowColor : idleContentGlowColor
    pressedContentGlowColor: selected ? selectedContentGlowColor : idleContentGlowColor
    hoverSoftGlowColor: selected ? selectedSoftGlowColor : idleSoftGlowColor
    pressedSoftGlowColor: selected ? selectedSoftGlowColor : idleSoftGlowColor
}
