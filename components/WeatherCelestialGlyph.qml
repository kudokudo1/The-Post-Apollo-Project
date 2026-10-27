import QtQuick
import QtQuick.Shapes
import QtQuick.Effects
import "WeatherMoonGeometry.js" as MoonGeometry

// Flat solar and lunar geometry shared by the Weather dock and SKY.
// No emoji moons, independent fetches, special phase colors or animations.
Item {
    id: glyph

    // "sun", "moon", "sun-cloud", or the shared "night-weather" scene.
    property string mode: "moon"
    property string solar: "day"
    property string moonPhase: "unknown"
    property string weatherKind: "clear"  // clear/cloud/rain/snow/hail/storm/wind
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

    readonly property bool nightComposition: mode === "night-weather"
    readonly property bool moonVisible: mode === "moon" || mode === "moon-cloud"
                                        || nightComposition
    readonly property bool foregroundCloud: nightComposition
        && (weatherKind === "cloud" || weatherKind === "rain"
            || weatherKind === "snow" || weatherKind === "hail"
            || weatherKind === "storm")
    readonly property bool sunVisible: mode === "sun" || mode === "sun-cloud"
    readonly property bool horizon: solar === "dawn" || solar === "dusk"
    readonly property bool waxing: moonPhase.indexOf("waxing") === 0
                                   || moonPhase === "first-quarter"
    readonly property bool waning: moonPhase.indexOf("waning") === 0
                                   || moonPhase === "last-quarter"
    // The precise QML contour is defined by a single symmetric helper.
    // No orientation-specific PathArc implementation is required.

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

        // The moon is offset within the *same* 40x40 artboard for every
        // night-weather scene: fixed upper-left, constant lunar orientation.
        // Pure moon-phase detail (mode: moon) stays centered.
        Item {
            id: lunarBody
            x: glyph.nightComposition ? -4 : 0
            y: glyph.nightComposition ? -5 : 0
            width: 40
            height: 40

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
                PathSvg {
                    path: MoonGeometry.litPath(glyph.moonPhase)
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

        } // lunarBody

        // A FILLED foreground cloud physically occludes the lower moon.
        // No font baseline or emoji bearings can shift its position.
        Shape {
            anchors.fill: parent
            visible: glyph.foregroundCloud
            ShapePath {
                strokeWidth: 0
                fillColor: glyph.ink
                startX: 7
                startY: 31
                PathCubic { x: 7; y: 22; control1X: 3; control1Y: 29; control2X: 3; control2Y: 23 }
                PathCubic { x: 15; y: 19; control1X: 8; control1Y: 18; control2X: 11; control2Y: 17 }
                PathCubic { x: 27; y: 19; control1X: 16; control1Y: 9; control2X: 26; control2Y: 11 }
                PathCubic { x: 35; y: 23; control1X: 31; control1Y: 18; control2X: 34; control2Y: 19 }
                PathCubic { x: 34; y: 31; control1X: 39; control1Y: 26; control2X: 37; control2Y: 30 }
                PathLine { x: 7; y: 31 }
            }
        }
        // Weather details are layered IN FRONT of the cloud, never between
        // the moon and cloud; no independent badges or condition offsets.
        Repeater {
            model: 3
            delegate: Rectangle {
                visible: glyph.nightComposition && glyph.weatherKind === "rain"
                x: 13 + index * 8
                y: 33
                width: 2
                height: 5
                radius: 1
                rotation: 20
                color: glyph.ink
            }
        }
        Repeater {
            model: 3
            delegate: Text {
                visible: glyph.nightComposition && glyph.weatherKind === "snow"
                text: "❆"
                font.family: "GohuFont 11 Nerd Font Mono"
                font.pixelSize: 10
                x: 10 + index * 9
                y: 28
                color: glyph.ink
            }
        }
        Repeater {
            model: 3
            delegate: Rectangle {
                visible: glyph.nightComposition && glyph.weatherKind === "hail"
                x: 13 + index * 8
                y: 34
                width: 3
                height: 3
                rotation: 45
                color: glyph.ink
            }
        }
        Shape {
            anchors.fill: parent
            visible: glyph.nightComposition && glyph.weatherKind === "storm"
            ShapePath {
                strokeWidth: 0
                fillColor: glyph.ink
                startX: 23; startY: 27
                PathLine { x: 18; y: 34 }
                PathLine { x: 23; y: 34 }
                PathLine { x: 20; y: 40 }
                PathLine { x: 30; y: 31 }
                PathLine { x: 25; y: 31 }
                PathLine { x: 28; y: 27 }
                PathLine { x: 23; y: 27 }
            }
        }
        Text {
            visible: glyph.nightComposition && glyph.weatherKind === "wind"
            text: "༄"
            font.family: "GohuFont 11 Nerd Font Mono"
            font.pixelSize: 27
            x: 15
            y: 14
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
