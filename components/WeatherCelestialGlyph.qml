import QtQuick
import QtQuick.Shapes
import QtQuick.Effects

// Flat solar and lunar geometry shared by the Weather dock and SKY.
// No emoji moons, independent fetches, special phase colors or animations.
Item {
    id: glyph

    // "sun", "moon", "sun-cloud" or "moon-cloud".
    property string mode: "moon"
    property string solar: "day"
    property string moonPhase: "unknown"
    property color ink: "white"
    // Weather owns the illuminated portion; night owns only the atmospheric
    // glow. Keep the dark face distinct from both the semantic ink and dock
    // interaction glow. This is shared by dock, SKY and forecast sizes.
    property color shadowInk: Colors.dark
    property color nightHalo: Colors.magenta
    readonly property bool nightGlowEnabled:
        solar === "night" && moonVisible

    implicitWidth: 40
    implicitHeight: 40
    width: implicitWidth
    height: implicitHeight

    readonly property bool moonVisible: mode === "moon" || mode === "moon-cloud"
    readonly property bool sunVisible: mode === "sun" || mode === "sun-cloud"
    readonly property bool horizon: solar === "dawn" || solar === "dusk"
    readonly property bool waxing: moonPhase.indexOf("waxing") === 0
                                   || moonPhase === "first-quarter"
    readonly property bool waning: moonPhase.indexOf("waning") === 0
                                   || moonPhase === "last-quarter"
    readonly property real terminatorX:
        moonPhase.indexOf("crescent") !== -1 ? (waxing ? 31 : 9)
        : moonPhase.indexOf("gibbous") !== -1 ? (waxing ? 9 : 31)
        : 20

    Item {
        id: art
        width: 40
        height: 40
        anchors.centerIn: parent
        scale: Math.min(glyph.width, glyph.height) / 40

        // Full-day icon: one disk and eight simple rays.
        Rectangle {
            visible: glyph.sunVisible && !glyph.horizon
            x: 12; y: 12; width: 16; height: 16
            radius: 8
            color: glyph.ink
        }
        Repeater {
            model: 8
            delegate: Rectangle {
                visible: glyph.sunVisible && !glyph.horizon
                x: 19; y: 2
                width: 2; height: 6
                radius: 1
                color: glyph.ink
                transform: Rotation {
                    origin.x: 1
                    origin.y: 18
                    angle: index * 45
                }
            }
        }

        // At dawn/dusk the same sun sits on a straight horizon.
        Shape {
            anchors.fill: parent
            visible: glyph.sunVisible && glyph.horizon
            ShapePath {
                strokeWidth: 0
                fillColor: glyph.ink
                startX: 9; startY: 28
                PathArc {
                    x: 31; y: 28
                    radiusX: 11; radiusY: 11
                    direction: PathArc.Clockwise
                }
                PathLine { x: 9; y: 28 }
            }
        }
        Rectangle {
            visible: glyph.sunVisible && glyph.horizon
            x: 3; y: 28; width: 34; height: 2
            color: glyph.ink
        }
        Repeater {
            model: 5
            delegate: Rectangle {
                readonly property real angleDegrees: (index - 2) * 37
                readonly property real angleRadians: angleDegrees * Math.PI / 180
                visible: glyph.sunVisible && glyph.horizon
                width: 2; height: 5
                radius: 1
                x: 20 + Math.sin(angleRadians) * 17 - 1
                y: 28 - Math.cos(angleRadians) * 17 - 2
                rotation: angleDegrees
                color: glyph.ink
            }
        }

        // The dark lunar disk stays at the same center in all eight phases.
        // A separate low-intensity magenta halo defines the night silhouette
        // even when the disk nearly matches the panel background.
        RectangularShadow {
            x: 6
            y: 6
            width: 28
            height: 28
            radius: 14
            blur: 10
            spread: 2
            color: glyph.nightHalo
            opacity: glyph.nightGlowEnabled ? 0.42 : 0
            visible: glyph.nightGlowEnabled
        }

        // The 8 lunar phases always have exactly the same 28px perimeter.
        Rectangle {
            visible: glyph.moonVisible
            x: 6; y: 6; width: 28; height: 28
            radius: 14
            color: glyph.moonPhase === "full" ? glyph.ink : glyph.shadowInk
            // A lit outline would disguise the dark hemisphere and turn
            // every phase into a ring. Only unknown phase needs a marker.
            border.width: glyph.moonPhase === "unknown" ? 1.4 : 0
            border.color: glyph.ink
        }
        Shape {
            anchors.fill: parent
            visible: glyph.moonVisible && (glyph.waxing || glyph.waning)
            ShapePath {
                strokeWidth: 0
                fillColor: glyph.ink
                startX: 20
                startY: 6
                PathArc {
                    x: 20
                    y: 34
                    radiusX: 14
                    radiusY: 14
                    direction: glyph.waxing
                               ? PathArc.Clockwise : PathArc.Counterclockwise
                }
                PathCubic {
                    x: 20
                    y: 6
                    control1X: glyph.terminatorX
                    control1Y: 29
                    control2X: glyph.terminatorX
                    control2Y: 11
                }
            }
        }

        // Unknown lunar phase never masquerades as new moon or a crescent.
        // Keep a small outline and question mark rather than a blank icon.
        Text {
            anchors.centerIn: parent
            visible: glyph.moonVisible && glyph.moonPhase === "unknown"
            text: "?"
            font.pixelSize: 18
            color: glyph.ink
        }

        // Keep the existing flat cloud glyph, scaled over either celestial
        // body. Its color is inherited, not a new weather palette entry.
        Text {
            visible: glyph.mode === "sun-cloud" || glyph.mode === "moon-cloud"
            text: "☁︎"
            x: 12
            y: 18
            font.pixelSize: 24
            color: glyph.ink
        }
    }
}
