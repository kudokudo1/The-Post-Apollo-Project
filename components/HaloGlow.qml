import QtQuick
import QtQuick.Effects

// Geometry-only rectangular glow. Attach as a direct child of the surface.
// Children can place it behind (negative z) or in front (positive z).
RectangularShadow {
    id: halo
    anchors.fill: parent

    property bool glowEnabled: true
    property real glowStrength: 1.0
    property real baseOpacity: 0.0

    z: -1
    spread: 3
    color: Colors.orange
    opacity: glowEnabled ? baseOpacity * glowStrength : 0.0
}
