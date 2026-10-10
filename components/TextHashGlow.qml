import QtQuick

// Intentionally sampled TEXT / ICON glow. Unlike chassis halos this effect
// samples an actual source and must disconnect it during Quickshell teardown.
// Set foregroundColor to the text/icon's actual foreground in the consumer.
SafeDropShadow {
    id: hashGlow

    property color foregroundColor: Colors.white

    // The normal palette pairings are defaults. MAGENTA IS NON-NEGOTIABLE:
    // magenta foreground always gets magenta text/icon glow, even when
    // another preferred color was requested for the rest of the control.
    property color preferredGlowColor:
        foregroundColor === Colors.white ? Colors.cyan
        : foregroundColor === Colors.yellow ? Colors.orange
        : foregroundColor === Colors.green ? Colors.omnitrix
        : foregroundColor

    readonly property color resolvedGlowColor:
        foregroundColor === Colors.magenta
        ? Colors.magenta : preferredGlowColor

    readonly property point sourceOrigin:
        sourceAttached && parent !== null
        ? safeSource.mapToItem(parent, 0, 0)
        : Qt.point(0, 0)

    x: sourceOrigin.x
    y: sourceOrigin.y
    width: sourceAttached ? safeSource.width : 0
    height: sourceAttached ? safeSource.height : 0

    horizontalOffset: 0
    verticalOffset: 0
    radius: VisualLanguage.textHashRadius
    samples: VisualLanguage.textHashSamples
    opacity: VisualLanguage.textHashOpacity
    color: resolvedGlowColor
    transparentBorder: true
    z: 2
}
