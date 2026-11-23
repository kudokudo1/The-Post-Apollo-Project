import QtQuick
import QtQuick.Shapes
import Qt5Compat.GraphicalEffects as Effects
import "../components"

// Forest-only gradient label. GohuText remains the source of text shaping,
// alignment and elision. The radial ink is masked by the actual text alpha,
// then sampled by the existing TextHashGlow from outside this component.
Item {
    id: root

    property string text: ""
    // Measure the entire displayed text by default, including // CHAT.
    // The gradient is always proportional to the visible label, not row width.
    property string gradientText: text
    property color baseColor: "#DCF3FA"
    property color accentColor: "#EE76B2"
    property bool accentTopRight: false
    property int pixelSize: 12
    property bool bold: true

    // Use the actual GohuFont width of gradientText, including suffixes
    // when provided. Clamp to the visible label span on narrow screens.
    readonly property real visibleGlyphWidth:
        Math.max(1, Math.min(width, gradientMeasure.implicitWidth))
    // A slightly stronger accent than the previous 0.42, kept
    // proportional so CHERRY, MAPLE and CEDAR are not overwhelmed.
    readonly property real accentRadius:
        Math.max(19, visibleGlyphWidth * 0.58)

    GohuText {
        id: gradientMeasure
        text: root.gradientText
        textFormat: Text.PlainText
        font.pixelSize: root.pixelSize
        font.bold: root.bold
        visible: false
    }

    GohuText {
        id: inkMask
        anchors.fill: parent
        text: root.text
        textFormat: Text.PlainText
        font.pixelSize: root.pixelSize
        font.bold: root.bold
        color: "white"
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
        visible: false
    }

    Shape {
        id: radialInk
        anchors.fill: parent
        visible: false

        ShapePath {
            strokeWidth: -1
            fillGradient: RadialGradient {
                centerX: root.accentTopRight ? root.visibleGlyphWidth : 0
                // The old y=0 put the accent above the actual glyphs,
                // especially hiding MAPLE's red top-right tint.
                centerY: root.height * 0.36
                centerRadius: root.accentRadius
                focalX: centerX
                focalY: centerY
                GradientStop { position: 0.0; color: root.accentColor }
                GradientStop { position: 0.2; color: root.accentColor }
                GradientStop { position: 1.0; color: root.baseColor }
            }

            startX: 0; startY: 0
            PathLine { x: root.width; y: 0 }
            PathLine { x: root.width; y: root.height }
            PathLine { x: 0; y: root.height }
            PathLine { x: 0; y: 0 }
        }
    }

    // The radial upper-left accent now applies consistently to every Tree:
    // Maple uses red at the upper-left and orange as its base to the right.
    Effects.OpacityMask {
        id: coloredText
        anchors.fill: parent
        source: radialInk
        maskSource: inkMask
        cached: false
    }
}
