import QtQuick

// MAIN MODE close halo: behind button; fixed spread, progressive strength.
HaloGlow {
    id: halo
    property bool selected: false
    property bool hovered: false
    property bool keyboardSelected: false
    property bool pressed: false

    readonly property bool energized:
        selected || hovered || keyboardSelected || pressed

    spread: VisualLanguage.modeCloseSpread
    baseOpacity: VisualLanguage.modeCloseActiveOpacity
    glowStrength:
        pressed ? VisualLanguage.modeHaloPressedStrength
        : selected ? VisualLanguage.modeHaloSelectedStrength
        : hovered || keyboardSelected ? VisualLanguage.modeHaloHoverStrength
        : 0.0
    color: VisualLanguage.modeHaloColor
    z: -1
}
