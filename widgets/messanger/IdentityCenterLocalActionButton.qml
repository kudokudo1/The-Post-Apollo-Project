import QtQuick
import "../../components"

// Social Organizations ONLY: semantic colors without geometry or behavioral
// changes to shared ActionButton. Roles are designed for instant scanning.
// Selected and pressed are magenta intent, except red destructive presses.
ActionButton {
    id: semanticButton
    property string role: "navigate"
    readonly property color roleColor:
        role === "danger" ? Colors.red
        : role === "refresh" ? Colors.green
        : role === "manage" ? Colors.yellow
        : role === "primary" ? Colors.orange
        : role === "focus" ? Colors.magenta
        : role === "neutral" ? Colors.white
        : Colors.blue

    destructive: role === "danger"
    accentColor: roleColor
    idleForegroundColor: roleColor
    idleBorderColor: roleColor
    hoverFillColor: Qt.rgba(roleColor.r, roleColor.g, roleColor.b, 0.16)
    hoverForegroundColor: Colors.white
    hoverBorderColor: roleColor

    pressedFillColor: destructive ? Colors.red : Colors.magenta
    pressedBorderColor: destructive ? Colors.red : Colors.magenta
    pressedForegroundColor: Colors.black

    selectedFillColor: Qt.rgba(Colors.magenta.r, Colors.magenta.g,
                               Colors.magenta.b, 0.23)
    selectedBorderColor: Colors.magenta
    selectedForegroundColor: Colors.white
    selectedContentGlowColor: Colors.magenta
    selectedSoftGlowColor: Colors.magenta

    keyboardSelectedFillColor: selectedFillColor
    keyboardSelectedForegroundColor: selectedForegroundColor
    keyboardSelectedBorderColor: Colors.magenta

    softGlowIdleOpacity: role === "neutral" ? 0.10 : 0.22
    softGlowHoverOpacity: 0.55
    softGlowSelectedOpacity: 0.64
    wideGlowEnabled: effectiveSelected
    wideGlowSelectedOpacity: 0.10
    unavailableOpacity: 0.38
}
