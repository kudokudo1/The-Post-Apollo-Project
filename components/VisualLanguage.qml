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

    // Fixed spreads; state strength increases while close:wide ratio persists.
    // Progressive multipliers are tuning baselines pending on-screen review.
    readonly property real modeHaloHoverStrength: 0.80
    readonly property real modeHaloSelectedStrength: 1.00
    readonly property real modeHaloPressedStrength: 1.20

    // MAIN MODE primary sampled-icon glow tuning is provisional.
    readonly property real modeIconIdleOpacity: 0.40
    readonly property real modeIconHoverOpacity: 0.80
    readonly property real modeIconSelectedOpacity: 1.00
    readonly property real modeIconIdleRadius: 10
    readonly property real modeIconHoverRadius: 14
    readonly property real modeIconSelectedRadius: 18
    readonly property int modeIconIdleSamples: 7
    readonly property int modeIconHoverSamples: 9
    readonly property int modeIconSelectedSamples: 17

    readonly property real modeLabelIdleOpacity: 0.34
    readonly property real modeLabelActiveOpacity: 0.48
    readonly property real modeLabelPressedOpacity: 0.42
    readonly property real modeLabelGlowIdleOpacity: 0.06
    readonly property real modeLabelGlowActiveOpacity: 0.10
    readonly property real modeLabelGlowRadius: 5
    readonly property int modeLabelGlowSamples: 7

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
