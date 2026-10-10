pragma Singleton
import QtQuick

// Canonical appearance recipes. Colors describe identity; effect components
// decide which recipe belongs to which surface. These are defaults, not a
// universal semantic hierarchy.
QtObject {
    readonly property color modeHaloColor: Colors.orange
    readonly property real modeCloseSpread: 3
    readonly property real modeCloseActiveOpacity: 0.50
    readonly property real modeWideSpread: 10
    readonly property real modeWideActiveOpacity: 0.09

    // Git's restrained chassis is the preferred WINDOW default.
    readonly property real chassisCloseSpread: 6
    readonly property real chassisCloseOpacity: 0.21
    readonly property real chassisWideSpread: 12
    readonly property real chassisWideOpacity: 0.05

    readonly property real actionHaloSpread: 3
    readonly property real actionIdleOpacity: 0.22
    readonly property real actionHoverOpacity: 0.56
    readonly property real actionSelectedOpacity: 0.56
    readonly property real actionPressedOpacity: 0.60

    // The intentionally undersampled, hash-like TEXT effect. This is not
    // the smooth chassis/button effect or a CRT shader.
    readonly property real textHashRadius: 10
    readonly property int textHashSamples: 9
    readonly property real textHashOpacity: 0.84

    // Fading importance is NOT the same as disabling an action.
    readonly property real quietTextOpacity: 0.42
    readonly property real secondaryTextOpacity: 0.68
}
