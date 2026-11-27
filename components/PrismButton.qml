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
    hoverBorderWidth: 2
    pressedBorderWidth: 2
    selectedBorderWidth: 2
    keyboardSelectedBorderWidth: 2
    contentGlowEnabled: false
    contentGlowSource: null
    softGlowEnabled: false
    wideGlowEnabled: false
    perimeterGlowEnabled: false

    property real spectralGlowStrength: 1.0
    readonly property real glowPadding: Math.ceil(Math.min(width,height)*0.09)
    readonly property int rasterLimit: 256

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
        onPaint: {
            console.info("PRISM_PAINT_ENTER",width,height,available)
            const c=getContext("2d")
            if (!c) { console.error("PRISM_PAINT_NO_CONTEXT"); return }
            if (root.width<=0 || root.height<=0) {
                c.clearRect(0,0,width,height)
                return
            }
            try {
                Artwork.paint(c,width,height,root.width,root.height,root.glowPadding,
                              1,root.prismPalette,root.spectralGlowStrength)
                const before=c.getImageData(Math.floor(width/2),Math.floor(height/2),1,1).data
                console.info("PRISM_PAINT_PUT_IMAGE",before[0],before[1],before[2],before[3])
                c.fillStyle="#ffffff"
                c.fillRect(Math.floor(width/2),Math.floor(height/2),2,2)
                const px=c.getImageData(Math.floor(width/2),Math.floor(height/2),1,1).data
                console.info("PRISM_PAINT_FILL_RECT",px[0],px[1],px[2],px[3])
            } catch (error) {
                console.error("PRISM_PAINT_ERROR",String(error))
            }
        }
    }

    // Native state emphasis is composited above the artwork. Changing hover,
    // press or selection does not regenerate the expensive raster.
    Rectangle {
        anchors.fill: parent
        color: "transparent"
        border.color: root.activeBorderColor
        border.width: root.activeBorderWidth
        radius: 0
    }
}
