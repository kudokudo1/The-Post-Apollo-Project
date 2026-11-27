import QtQuick
import "PrismArtwork.js" as Artwork

// Spectral perimeter only. Reuse the Prism button's actual stops and
// orientation: orange bottom-left, cyan at both opposite corners,
// magenta top-right. Draw on the native Canvas vector path, not putImageData.
Item {
    id: halo
    property bool divider: false
    property real strength: 1.0
    property int padding: 12
    readonly property var palette: [
        Colors.orange, Colors.yellow, Colors.green, Colors.cyan,
        Colors.blue, Colors.purple, Colors.magenta
    ]
    Canvas {
        id: raster
        anchors.fill: parent
        anchors.margins: -halo.padding
        renderTarget: Canvas.Image
        renderStrategy: Canvas.Immediate
        contextType: "2d"
        onAvailableChanged: if (available) requestPaint()
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onVisibleChanged: if (visible) requestPaint()
        Component.onCompleted: requestPaint()
        Connections {
            target: halo
            function onStrengthChanged() { raster.requestPaint() }
            function onPaletteChanged() { raster.requestPaint() }
            function onDividerChanged() { raster.requestPaint() }
        }
        onPaint: {
            const c=getContext("2d")
            if (!c) return
            c.clearRect(0,0,width,height)
            const p=halo.padding, w=halo.width, h=halo.height
            if (w<=0 || h<=0 || halo.strength<=0) return
            // On rectangular surfaces preserve the same normalized diagonal
            // as the button; a plain corner-to-corner linear gradient would
            // shift the cyan corners on tall/skinny rectangles.
            const norm=1/(w*w)+1/(h*h)
            const g=halo.divider
                ? c.createLinearGradient(p,0,p+w,0)
                : c.createLinearGradient(p,p+h,p+2/w/norm,p+h-2/h/norm)
            const recipe=Artwork.prismGeometry()
            for (let i=0;i<recipe.spectrumStops.length;i++)
                g.addColorStop(recipe.spectrumStops[i],halo.palette[recipe.spectrumIndices[i]])
            c.strokeStyle=g
            // Smooth falloff using bounded vector strokes, with a thin
            // tinted core. No additional white outline, image or animation.
            const widths=[21,17,13,9,5,3,1]
            const alphas=[0.018,0.025,0.04,0.065,0.12,0.22,0.42]
            for(let i=0;i<widths.length;i++) {
                c.globalAlpha=Math.min(1,alphas[i]*halo.strength)
                c.lineWidth=widths[i]
                if (halo.divider) {
                    c.beginPath()
                    c.moveTo(p,p+h/2)
                    c.lineTo(p+w,p+h/2)
                    c.stroke()
                } else {
                    c.strokeRect(p+.5,p+.5,Math.max(0,w-1),Math.max(0,h-1))
                }
            }
            c.globalAlpha=1
        }
    }
}
