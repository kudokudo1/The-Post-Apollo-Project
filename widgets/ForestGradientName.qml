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
    property color baseColor: "#DCF3FA"
    property color accentColor: "#EE76B2"
    property bool accentTopRight: false
    property int pixelSize: 12
    property bool bold: true

    // Text.implicitWidth is measured from the actual GohuFont text, not
    // the available button width. For long names the source Text elides,
    // so constrain the gradient anchor to the visible glyph span.
    readonly property real visibleGlyphWidth:
        Math.max(1, Math.min(width, inkMask.implicitWidth))
    readonly property real accentRadius:
        Math.max(16, visibleGlyphWidth * 0.42)

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
                centerY: 0
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

    Effects.OpacityMask {
        id: coloredText
        anchors.fill: parent
        source: radialInk
        maskSource: inkMask
        cached: false
    }
}
