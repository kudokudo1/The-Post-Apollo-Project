import QtQuick

// MAIN MODE wide wash: in FRONT of button; fixed spread, weaker base strength.
// Identical state multipliers preserve the close:wide glow ratio.
HaloGlow {
    id: halo
    property bool selected: false
    property bool hovered: false
    property bool keyboardSelected: false
    property bool pressed: false

    readonly property bool energized:
        selected || hovered || keyboardSelected || pressed

    spread: VisualLanguage.modeWideSpread
    baseOpacity: VisualLanguage.modeWideActiveOpacity
    glowStrength:
        pressed ? VisualLanguage.modeHaloPressedStrength
        : selected ? VisualLanguage.modeHaloSelectedStrength
        : hovered || keyboardSelected ? VisualLanguage.modeHaloHoverStrength
        : 0.0
    color: VisualLanguage.modeHaloColor
    z: 1
}
