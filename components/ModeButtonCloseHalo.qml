import QtQuick

// MODE BUTTON close perimeter: rear layer, separate from the front wash.
// Attach directly to the button Rectangle, not inside a wrapper Item.
HaloGlow {
    id: halo
    property bool selected: false
    property bool hovered: false
    property bool keyboardSelected: false
    property bool pressed: false

    readonly property bool energized:
        selected || hovered || keyboardSelected || pressed

    spread: VisualLanguage.modeCloseSpread
    baseOpacity: energized ? VisualLanguage.modeCloseActiveOpacity : 0.0
    color: VisualLanguage.modeHaloColor
    z: -1
}
