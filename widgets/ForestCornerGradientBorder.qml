import QtQuick
import QtQuick.Shapes

// Forest-only 1px border ink. The odd-even ring leaves the center untouched,
// so the normal DockButton yellow selected fill and independent rear halos
// stay intact. Accent lives at the operator-assigned upper corner.
Item {
    id: root

    property color baseColor: "#DCF3FA"
    property color accentColor: "#EE76B2"
    property bool accentTopRight: false
    property real lineWidth: 1

    readonly property real accentRadius:
        Math.max(42, Math.min(100, width * 0.43))

    Shape {
        anchors.fill: parent

        ShapePath {
            strokeWidth: -1
            fillRule: ShapePath.OddEvenFill
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

            PathMove { x: root.lineWidth; y: root.lineWidth }
            PathLine { x: root.lineWidth; y: root.height - root.lineWidth }
            PathLine { x: root.width - root.lineWidth; y: root.height - root.lineWidth }
            PathLine { x: root.width - root.lineWidth; y: root.lineWidth }
            PathLine { x: root.lineWidth; y: root.lineWidth }
        }
    }
}
