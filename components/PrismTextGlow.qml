import QtQuick
import "PrismArtwork.js" as Artwork

// Behind a real text item, never a colored replacement for its foreground.
// Use the original Prism spectral stops and a bounded glyph-shaped halo.
Item {
    id: halo
    required property Text labelItem
    property real strength: 1.0
    readonly property int padding: 5
    readonly property var palette: [
        Colors.orange, Colors.yellow, Colors.green, Colors.cyan,
        Colors.blue, Colors.purple, Colors.magenta
    ]
    anchors.fill: labelItem

    TextMetrics {
        id: metrics
        font: halo.labelItem.font
        text: halo.labelItem.text
        elide: halo.labelItem.elide
        elideWidth: Math.max(0, halo.labelItem.width)
        onElidedTextChanged: raster.requestPaint()
        onFontChanged: raster.requestPaint()
    }
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
            target: halo.labelItem
            function onBaselineOffsetChanged() { raster.requestPaint() }
            function onHorizontalAlignmentChanged() { raster.requestPaint() }
            function onTextChanged() { raster.requestPaint() }
        }
        Connections {
            target: halo
            function onStrengthChanged() { raster.requestPaint() }
            function onPaletteChanged() { raster.requestPaint() }
        }
        onPaint: {
            const c=getContext("2d")
            if (!c) return
            c.clearRect(0,0,width,height)
            const label=halo.labelItem, p=halo.padding
            const text=metrics.elidedText
            if (!text || halo.width<=0 || halo.height<=0 || halo.strength<=0) return
            c.font=(label.font.bold ? "bold " : "") + label.font.pixelSize
                   + 'px "' + label.font.family + '"'
            c.textAlign="left"
            c.textBaseline="alphabetic"
            const inkWidth=c.measureText(text).width
            if (inkWidth<=0) return
            let x=p
            if (label.horizontalAlignment===Text.AlignHCenter)
                x+=(halo.width-inkWidth)/2
            else if (label.horizontalAlignment===Text.AlignRight)
                x+=halo.width-inkWidth
            const y=p+label.baselineOffset
            const gradient=c.createLinearGradient(x,0,x+inkWidth,0)
            const recipe=Artwork.prismGeometry()
            for (let i=0;i<recipe.spectrumStops.length;i++)
                gradient.addColorStop(recipe.spectrumStops[i],halo.palette[recipe.spectrumIndices[i]])
            c.strokeStyle=gradient
            c.lineJoin="round"
            const widths=[8,6,4,2,1]
            const alphas=[0.035,0.06,0.12,0.22,0.36]
            for(let i=0;i<widths.length;i++) {
                c.globalAlpha=Math.min(1,alphas[i]*halo.strength)
                c.lineWidth=widths[i]
                c.strokeText(text,x,y)
            }
            c.globalAlpha=1
        }
    }
}
