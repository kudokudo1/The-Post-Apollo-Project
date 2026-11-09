import QtQuick
import "../components"

// ANGEL-local outline-first action. Standard ActionButton paints a new color
// on hover/press, which turns an otherwise neutral entire rail into filled
// controls while pointer events move across them. Keep the idle surface when
// unselected; selected states may retain their intentional color wash.
ActionButton {
    idleFillColor: Colors.black
    hoverFillColor: selected ? selectedFillColor : idleFillColor
    pressedFillColor: selected ? selectedFillColor : idleFillColor

    hoverForegroundColor: selected ? selectedForegroundColor : idleForegroundColor
    pressedForegroundColor: selected ? selectedForegroundColor : idleForegroundColor
    hoverBorderColor: selected ? selectedBorderColor : idleBorderColor
    pressedBorderColor: selected ? selectedBorderColor : idleBorderColor

    hoverContentGlowColor: selected ? selectedContentGlowColor : idleContentGlowColor
    pressedContentGlowColor: selected ? selectedContentGlowColor : idleContentGlowColor
    hoverSoftGlowColor: selected ? selectedSoftGlowColor : idleSoftGlowColor
    pressedSoftGlowColor: selected ? selectedSoftGlowColor : idleSoftGlowColor
}
