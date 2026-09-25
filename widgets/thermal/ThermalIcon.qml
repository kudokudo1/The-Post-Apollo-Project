import QtQuick
import Qt5Compat.GraphicalEffects
import "../../components"

Item {
    id: thermalIconRoot
    property color iconColor: Colors.orange
    property real iconScale: 1.0
    property real glowOpacity: 0.46
    property bool pressed: false

    opacity: 1.0
    implicitWidth: 59 * iconScale
    implicitHeight: 24 * iconScale
    width: implicitWidth
    height: implicitHeight

    Item {
        id: thermalIconScaledContent
        width: 59
        height: 24
        anchors.centerIn: parent
        scale: thermalIconRoot.iconScale
        transformOrigin: Item.Center
        opacity: 1.0

        // A third small star occupies the open upper-left pocket so
        // the left/right decoration feels balanced at every scale.
        GohuText {
            id: thermalIconTopLeftStar
            x: 15
            y: -3
            text: "⋆"
            font.pixelSize: 7
            opacity: 1.0
            color: thermalIconRoot.pressed ? Colors.black : thermalIconRoot.iconColor
        }

        DropShadow {
            anchors.fill: thermalIconTopLeftStar
            source: thermalIconTopLeftStar
            visible: !thermalIconRoot.pressed
            horizontalOffset: 0
            verticalOffset: 0
            radius: 4
            samples: 5
            opacity: thermalIconRoot.glowOpacity
            color: thermalIconRoot.iconColor
            transparentBorder: true
        }

        Row {
            id: thermalIconOuterRow
            anchors.centerIn: parent
            spacing: 1

            Row {
                id: thermalIconLeftCoreRow
                anchors.verticalCenter: parent.verticalCenter
                spacing: -9

                Item {
                    width: thermalIconLeft.implicitWidth
                    height: 24

                    GohuText {
                        id: thermalIconLeft
                        anchors.verticalCenter: parent.verticalCenter
                        text: "₊˚⊹"
                        font.pixelSize: 13
                        font.letterSpacing: -1.6
                        opacity: 1.0
                        color: thermalIconRoot.pressed ? Colors.black : thermalIconRoot.iconColor
                    }

                    DropShadow {
                        anchors.fill: thermalIconLeft
                        source: thermalIconLeft
                        visible: !thermalIconRoot.pressed
                        horizontalOffset: 0
                        verticalOffset: 0
                        radius: 5
                        samples: 5
                        opacity: thermalIconRoot.glowOpacity
                        color: thermalIconRoot.iconColor
                        transparentBorder: true
                    }
                }

                Item {
                    width: thermalIconCore.implicitWidth
                    height: 24

                    Text {
                        id: thermalIconCore
                        anchors.verticalCenter: parent.verticalCenter
                        text: "🌡"
                        font.family: "Noto Sans Symbols2"
                        font.pixelSize: 20
                        font.weight: Font.Bold
                        opacity: 1.0
                        color: thermalIconRoot.pressed ? Colors.black : thermalIconRoot.iconColor
                    }

                    DropShadow {
                        anchors.fill: thermalIconCore
                        source: thermalIconCore
                        visible: !thermalIconRoot.pressed
                        horizontalOffset: 0
                        verticalOffset: 0
                        radius: 5
                        samples: 5
                        opacity: thermalIconRoot.glowOpacity * 0.76
                        color: thermalIconRoot.iconColor
                        transparentBorder: true
                    }
                }
            }

            Item {
                width: thermalIconRight.implicitWidth
                height: 24

                GohuText {
                    id: thermalIconRight
                    anchors.verticalCenter: parent.verticalCenter
                    text: "๋࣭⭑"
                    font.pixelSize: 13
                    opacity: 1.0
                    color: thermalIconRoot.pressed ? Colors.black : thermalIconRoot.iconColor
                }

                DropShadow {
                    anchors.fill: thermalIconRight
                    source: thermalIconRight
                    visible: !thermalIconRoot.pressed
                    horizontalOffset: 0
                    verticalOffset: 0
                    radius: 5
                    samples: 5
                    opacity: thermalIconRoot.glowOpacity
                    color: thermalIconRoot.iconColor
                    transparentBorder: true
                }
            }
        }
    }
}
