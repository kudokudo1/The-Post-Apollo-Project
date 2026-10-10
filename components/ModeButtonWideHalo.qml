import QtQuick

// MODE BUTTON wide wash: intentionally IN FRONT of the button face.
// Keep as a direct child of the button Rectangle. A nested composite
// cannot reliably reproduce this layer relative to the face.
HaloGlow {
    id: halo
    property bool selected: false
    property bool hovered: false
    property bool keyboardSelected: false
    property bool pressed: false

    readonly property bool energized:
        selected || hovered || keyboardSelected || pressed

    spread: VisualLanguage.modeWideSpread
    baseOpacity: energized ? VisualLanguage.modeWideActiveOpacity : 0.0
    color: VisualLanguage.modeHaloColor
    z: 1
}
