import QtQuick
import "PrismArtwork.js" as Artwork

// Contextual visual-language dictionary trigger. The owner supplies the popup
// and its actual selected/open state; the artwork never opens a surface itself.
ActionButton {
    id: root
    objectName: "prismButton"
    implicitWidth: 44
    implicitHeight: 44
    label: ""
    showLabel: false
    accentColor: Colors.white
    acceptedButtons: Qt.LeftButton
    keyboardActivationSignal: "leftClicked"
    Accessible.role: Accessible.Button
    Accessible.name: "Prism"
    Accessible.description: "Explain the visual language of this context"
    Accessible.onPressAction: {
        if (root.interactive && root.available) {
            root.clicked(null)
            root.leftClicked(null)
            root.triggered(null)
        }
    }

    // Specialized identity is deliberately independent of action state.
    idleFillColor: Colors.black
    hoverFillColor: Colors.black
    pressedFillColor: Colors.black
    selectedFillColor: Colors.black
    keyboardSelectedFillColor: Colors.black
    idleBorderColor: Colors.white
    hoverBorderColor: Colors.white
    pressedBorderColor: Colors.white
    selectedBorderColor: Colors.white
    keyboardSelectedBorderColor: Colors.white
    // ONE native outline, fixed at one physical logical pixel in every state.
    // ActionButton paints its border below the children. Do not draw a second
    // white Rectangle over the spectrum.
    idleBorderWidth: 1
    hoverBorderWidth: 1
    pressedBorderWidth: 1
    selectedBorderWidth: 1
    keyboardSelectedBorderWidth: 1
    contentGlowEnabled: false
    contentGlowSource: null
    softGlowEnabled: false
    wideGlowEnabled: false
    perimeterGlowEnabled: false

    property real spectralGlowStrength: 1.0
    readonly property real glowPadding: Math.ceil(Math.min(width,height)*0.09)
    readonly property int rasterLimit: 256
    // Dock-like rising intensity without rerasterizing the expensive artwork
    // on hover/press/open. The second Canvas is a static, bloom-only texture.
    readonly property real glowEmphasisOpacity:
        !available ? 0.12 : effectiveSelected ? 0.78
        : pressed ? 0.64 : hovered ? 0.48 : 0.12

    function rgb(c) { return [c.r,c.g,c.b] }
    readonly property var prismPalette: [
        rgb(Colors.white),rgb(Colors.orange),rgb(Colors.yellow),
        rgb(Colors.green),rgb(Colors.cyan),rgb(Colors.blue),
        rgb(Colors.purple),rgb(Colors.magenta),rgb(Colors.black)
    ]

    // Analytic soft falloff is painted directly in one bounded raster. No
    // detached effect source, no shader sampling the parent, no periodic work.
    // Render at up to 2x logical size, then fit to the allocated face + halo.
    Canvas {
        id: raster
        objectName: "prismArtwork"
        readonly property real logicalWidth: Math.max(0,root.width+2*root.glowPadding)
        readonly property real logicalHeight: Math.max(0,root.height+2*root.glowPadding)
        readonly property real sampleScale: Math.min(2,root.rasterLimit/Math.max(1,logicalWidth,logicalHeight))
        anchors.centerIn: parent
        width: Math.max(1,Math.min(root.rasterLimit,Math.ceil(logicalWidth*sampleScale)))
        height: Math.max(1,Math.min(root.rasterLimit,Math.ceil(logicalHeight*sampleScale)))
        transform: Scale {
            origin.x: raster.width/2
            origin.y: raster.height/2
            xScale: raster.logicalWidth/raster.width
            yScale: raster.logicalHeight/raster.height
        }
        renderTarget: Canvas.Image
        renderStrategy: Canvas.Immediate
        contextType: "2d"
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onLogicalWidthChanged: requestPaint()
        onLogicalHeightChanged: requestPaint()
        onAvailableChanged: if (available) requestPaint()
        onVisibleChanged: if (visible) requestPaint()
        Component.onCompleted: requestPaint()
        Connections {
            target: root
            function onSpectralGlowStrengthChanged() { raster.requestPaint() }
            function onPrismPaletteChanged() { raster.requestPaint() }
        }
        property real lastPaintDurationMs: -1
        onPaint: {
            const started=Date.now()
            const c=getContext("2d")
            if (!c) return
            if (root.width<=0 || root.height<=0) {
                c.clearRect(0,0,width,height)
                return
            }
            Artwork.paint(c,width,height,root.width,root.height,root.glowPadding,
                          1,root.prismPalette,root.spectralGlowStrength)
            lastPaintDurationMs=Date.now()-started
        }
    }

    // Glow-only reuse of the exact spectral beam recipe, not an unrelated
    // white dock shadow. The native 1px border is underneath both canvases.
    // Keep this cached: state changes affect opacity, NEVER requestPaint().
    Canvas {
        id: glowRaster
        objectName: "prismGlowArtwork"
        readonly property real logicalWidth: raster.logicalWidth
        readonly property real logicalHeight: raster.logicalHeight
        readonly property real sampleScale: raster.sampleScale
        anchors.centerIn: parent
        width: raster.width
        height: raster.height
        transform: Scale {
            origin.x: glowRaster.width/2
            origin.y: glowRaster.height/2
            xScale: glowRaster.logicalWidth/glowRaster.width
            yScale: glowRaster.logicalHeight/glowRaster.height
        }
        renderTarget: Canvas.Image
        renderStrategy: Canvas.Immediate
        contextType: "2d"
        opacity: root.glowEmphasisOpacity
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onLogicalWidthChanged: requestPaint()
        onLogicalHeightChanged: requestPaint()
        onAvailableChanged: if (available) requestPaint()
        onVisibleChanged: if (visible) requestPaint()
        Component.onCompleted: requestPaint()
        Connections {
            target: root
            function onSpectralGlowStrengthChanged() { glowRaster.requestPaint() }
            function onPrismPaletteChanged() { glowRaster.requestPaint() }
        }
        property real lastPaintDurationMs: -1
        onPaint: {
            const started=Date.now()
            const c=getContext("2d")
            if (!c) return
            if (root.width<=0 || root.height<=0) {
                c.clearRect(0,0,width,height)
                return
            }
            Artwork.paint(c,width,height,root.width,root.height,root.glowPadding,
                          1,root.prismPalette,root.spectralGlowStrength,true)
            lastPaintDurationMs=Date.now()-started
        }
    }
}
