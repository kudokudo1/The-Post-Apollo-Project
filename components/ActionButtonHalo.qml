import QtQuick

// Ordinary ACTION perimeter, not a mode-selection or chassis glow.
// This follows shared ActionButton's default rear halo; specialized
// action buttons may use a second/wider halo independently.
HaloGlow {
    id: halo
    property bool hovered: false
    property bool pressed: false
    property bool selected: false
    property bool keyboardSelected: false
    property bool destructive: false
    property color accentColor: Colors.cyan

    spread: VisualLanguage.actionHaloSpread
    z: -1
    color:
        pressed ? (destructive ? Colors.red : Colors.magenta)
        : keyboardSelected ? Colors.orange
        : selected ? Colors.magenta
        : hovered ? Colors.orange
        : accentColor

    baseOpacity:
        pressed ? VisualLanguage.actionPressedOpacity
        : keyboardSelected ? VisualLanguage.actionSelectedOpacity
        : selected ? VisualLanguage.actionSelectedOpacity
        : hovered ? VisualLanguage.actionHoverOpacity
        : VisualLanguage.actionIdleOpacity
}
