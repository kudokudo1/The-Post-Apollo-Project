import QtQuick
import "../../components"

// Social Organizations ONLY: semantic colors without geometry or behavioral
// changes to shared ActionButton. Roles are designed for instant scanning.
// Open and selected controls keep the original shared ActionButton state colors.
// Magenta is reserved here for Add and active press; danger press stays red.
ActionButton {
    id: semanticButton
    property string role: "navigate"
    readonly property color roleColor:
        role === "danger" ? Colors.red
        : role === "refresh" ? Colors.green
        : role === "manage" ? Colors.yellow
        : role === "add" ? Colors.magenta
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

    // Preserve base selected/keyboard-selected fill, glow and border rules.

    softGlowIdleOpacity: role === "neutral" ? 0.10 : 0.22
    softGlowHoverOpacity: 0.55
    unavailableOpacity: 0.38
}
