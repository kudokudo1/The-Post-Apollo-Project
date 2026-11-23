import QtQuick
import QtQuick.Shapes
import Qt5Compat.GraphicalEffects
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

    readonly property real accentRadius:
        Math.max(38, Math.min(96, width * 0.66))

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
                centerX: root.accentTopRight ? root.width : 0
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

    OpacityMask {
        id: coloredText
        anchors.fill: parent
        source: radialInk
        maskSource: inkMask
        cached: false
    }
}
