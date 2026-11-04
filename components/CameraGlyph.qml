import QtQuick
import QtQuick.Shapes

// CAMERA // Post-Apollo native line glyph, not emoji, PNG, SVG asset or Canvas
// bitmap. Exact SVG-style path geometry is drawn by Qt Quick Shapes.
// All eight paths have transparent fill. The lens center and camera body show
// whatever background is behind this component. No material/black rectangle.
Item {
    id: glyph

    implicitWidth: 58
    implicitHeight: 42

    // Monochrome white by default; the Camera dock overrides all three
    // stroke roles with one bound color (magenta whenever it is open).
    // All paths remain hollow: these colors affect stroke, never fill.
    property color bodyColor: "#FFFFFF"
    property color lensColor: bodyColor
    property color ornamentColor: bodyColor

    // Source geometry is 128 x 96. This transforms the real vector paths,
    // including their stroke widths, instead of scaling a pre-rendered image.
    Shape {
        id: art
        width: 128
        height: 96
        transformOrigin: Item.TopLeft
        transform: Scale {
            origin.x: 0
            origin.y: 0
            xScale: glyph.width / 128
            yScale: glyph.height / 96
        }

        // Orbit lines live outside the camera silhouette; no filled ribbon.
        ShapePath {
            strokeColor: glyph.ornamentColor
            strokeWidth: 1.75
            capStyle: ShapePath.RoundCap
            joinStyle: ShapePath.RoundJoin
            fillColor: "transparent"
            PathSvg {
                path: "M 14 72 C 7 83 25 93 48 92 C 82 92 110 74 122 49 C 130 33 125 22 115 15"
            }
        }
        ShapePath {
            strokeColor: glyph.ornamentColor
            strokeWidth: 1.35
            capStyle: ShapePath.RoundCap
            fillColor: "transparent"
            PathSvg {
                path: "M 14 72 C 7 67 10 58 16 54"
            }
        }

        // Geometric outline and raised viewfinder: no opaque camera body.
        ShapePath {
            strokeColor: glyph.bodyColor
            strokeWidth: 3.2
            capStyle: ShapePath.RoundCap
            joinStyle: ShapePath.RoundJoin
            fillColor: "transparent"
            PathSvg {
                path: "M 22 28 L 45 28 L 52 16 L 76 16 L 84 28 L 103 28 Q 112 28 112 36 L 112 72 Q 112 79 104 79 L 23 79 Q 15 79 15 72 L 15 36 Q 15 30 22 28 Z"
            }
        }
        ShapePath {
            strokeColor: glyph.bodyColor
            strokeWidth: 1.7
            capStyle: ShapePath.RoundCap
            joinStyle: ShapePath.RoundJoin
            fillColor: "transparent"
            PathSvg {
                path: "M 50 27 L 56 20 L 73 20 L 78 27 M 27 28 L 27 21 Q 27 19 30 19 L 38 19 Q 41 19 41 22 L 41 28 M 94 37 L 103 37 Q 105 37 105 39 L 105 44 L 94 44 Z M 20 37 L 31 37 M 96 53 L 107 53 M 21 73 L 38 73 M 91 73 L 107 73"
            }
        }

        // Three concentric outline rings; interior is fully transparent.
        ShapePath {
            strokeColor: glyph.lensColor
            strokeWidth: 3.0
            capStyle: ShapePath.RoundCap
            joinStyle: ShapePath.RoundJoin
            fillColor: "transparent"
            PathSvg {
                path: "M 90 53 A 26 26 0 1 0 38 53 A 26 26 0 1 0 90 53 Z M 83 53 A 19 19 0 1 0 45 53 A 19 19 0 1 0 83 53 Z M 77 53 A 13 13 0 1 0 51 53 A 13 13 0 1 0 77 53 Z"
            }
        }

        // Compass/reticle ticks around the lens, not a filled sight.
        ShapePath {
            strokeColor: glyph.ornamentColor
            strokeWidth: 2.1
            capStyle: ShapePath.RoundCap
            joinStyle: ShapePath.RoundJoin
            fillColor: "transparent"
            PathSvg {
                path: "M 64 24 L 64 36 M 64 70 L 64 82 M 35 53 L 46 53 M 82 53 L 93 53"
            }
        }

        // Small inner optical highlights as open line arcs, not white blobs.
        ShapePath {
            strokeColor: glyph.bodyColor
            strokeWidth: 1.3
            capStyle: ShapePath.RoundCap
            fillColor: "transparent"
            PathSvg {
                path: "M 55 61 Q 60 67 67 65 M 70 45 L 73 47"
            }
        }

        // Four-point star ornaments: outlines only. No solid white diamonds.
        ShapePath {
            strokeColor: glyph.ornamentColor
            strokeWidth: 1.8
            capStyle: ShapePath.RoundCap
            joinStyle: ShapePath.RoundJoin
            fillColor: "transparent"
            PathSvg {
                path: "M 101 4 Q 103 13 111 16 Q 103 19 101 27 Q 98 19 91 16 Q 98 13 101 4 Z M 28 46 Q 30 54 37 56 Q 30 58 28 66 Q 26 58 19 56 Q 26 54 28 46 Z M 40 77 Q 42 84 49 87 Q 42 90 40 95 Q 38 90 31 87 Q 38 84 40 77 Z M 102 63 Q 104 69 110 70 Q 104 72 102 78 Q 100 72 95 70 Q 100 69 102 63 Z"
            }
        }

        // Tiny cross stars complete the orbital decoration.
        ShapePath {
            strokeColor: glyph.ornamentColor
            strokeWidth: 1.6
            capStyle: ShapePath.RoundCap
            fillColor: "transparent"
            PathSvg {
                path: "M 42 6 L 42 13 M 38.5 9.5 L 45.5 9.5 M 119 81 L 119 87 M 116 84 L 122 84"
            }
        }
    }
}
