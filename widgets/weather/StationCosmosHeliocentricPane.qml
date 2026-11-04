import QtQuick
import "../../components"
import "StationCosmosHeliocentricPolicy.js" as Helio
import "StationCosmosSolarOverviewPolicy.js" as Solar

// V4c // True Sun-centered, geometric JPL vector snapshot at one UTC.
// Neither the earlier apparent Earth-centric plot nor the longitudinal
// relationship graph is re-used as a substitute for these coordinates.
Item {
    id: spatial
    property var visualData: null
    property bool embedded: false
    property var graphModel: null
    property var verifiedNetwork: null
    property int focusIndex: -1
    property string selectedBody: ""
    property bool neonEnabled: true
    property bool tiltView: false
    property real spatialScale: 1.0
    property string atlasRange: "all"
    property string hoveredBody: ""
    // The requested V4d atlas is authoritative. If it is missing or
    // invalid, refuse to fake a multi-body view using the 2-body positions.
    // Legacy V4c results (without an atlas request) remain readable.
    readonly property bool atlasRequested: visualData && visualData.query
        && Array.isArray(visualData.query.solar_overview_bodies)
        && visualData.query.solar_overview_bodies.length>0
    readonly property var scene: atlasRequested
        ? Solar.scene(visualData,graphModel,verifiedNetwork,focusIndex)
        : Helio.verifiedScene(visualData,graphModel,verifiedNetwork,focusIndex)
    readonly property real radialDomainAu: scene.ready
        ? atlasRange==="inner" ? Math.min(scene.maxAu,4) : scene.maxAu
        : 0
    readonly property var focusPoint: Helio.byBody(scene,selectedBody)
    signal bodyPicked(string body)
    signal sampleScrubbed(int originIndex,real offsetPixels)

    onSceneChanged: spatialCanvas.requestPaint()
    onTiltViewChanged: spatialCanvas.requestPaint()
    onSpatialScaleChanged: spatialCanvas.requestPaint()
    onAtlasRangeChanged: spatialCanvas.requestPaint()
    onSelectedBodyChanged: spatialCanvas.requestPaint()
    onHoveredBodyChanged: spatialCanvas.requestPaint()

    function paint(ctx) {
        const w=spatialCanvas.width,h=spatialCanvas.height;
        ctx.clearRect(0,0,w,h);
        const g=Helio.layout(w,h,spatial.spatialScale);
        if(!g.ready)return;
        ctx.save();
        ctx.textAlign="center";
        ctx.textBaseline="middle";
        ctx.lineCap="round";
        ctx.font="9px monospace";

        const flatten=spatial.tiltView?Math.SQRT1_2:1;
        for(let ring=1;ring<=4;ring++){
            const r=g.r*ring/4;
            ctx.save();
            ctx.translate(g.cx,g.cy);
            ctx.scale(1,flatten);
            ctx.beginPath();
            ctx.arc(0,0,r,0,2*Math.PI);
            ctx.strokeStyle=String(ring===4?Colors.cyan:Colors.blue);
            ctx.globalAlpha=ring===4?0.65:0.26;
            ctx.lineWidth=ring===4?1.4:1;
            ctx.stroke();
            ctx.restore();
        }
        for(let degree=0;degree<360;degree+=45){
            const a=degree*Math.PI/180;
            ctx.beginPath();
            ctx.moveTo(g.cx+Math.sin(a)*g.r*0.93,
                       g.cy-Math.cos(a)*g.r*0.93*flatten);
            ctx.lineTo(g.cx+Math.sin(a)*g.r*1.02,
                       g.cy-Math.cos(a)*g.r*1.02*flatten);
            ctx.strokeStyle=String(Colors.yellow);
            ctx.globalAlpha=0.7;
            ctx.lineWidth=1;
            ctx.stroke();
        }
        ctx.globalAlpha=1;
        ctx.fillStyle=String(Colors.yellow);
        ctx.fillText("0°",g.cx,g.cy-g.r*flatten-15);
        ctx.fillText("90°",g.cx+g.r+14,g.cy);
        ctx.fillText("180°",g.cx,g.cy+g.r*flatten+14);
        ctx.fillText("270°",g.cx-g.r-17,g.cy);

        ctx.beginPath();
        ctx.arc(g.cx,g.cy,5,0,Math.PI*2);
        ctx.fillStyle=String(Colors.orange);
        ctx.shadowColor=String(Colors.orange);
        ctx.shadowBlur=spatial.neonEnabled?8:0;
        ctx.fill();
        ctx.shadowBlur=0;
        ctx.font="bold 9px monospace";
        ctx.fillStyle=String(Colors.yellow);
        ctx.fillText("SUN",g.cx,g.cy+15);

        if(!spatial.scene.ready) {
            ctx.fillStyle=String(Colors.orange);
            ctx.font="9px monospace";
            ctx.fillText("NO VERIFIED SUN-CENTERED JPL XYZ",g.cx,g.cy-20);
            ctx.restore();
            return;
        }

        for(let i=0;i<spatial.scene.points.length;i++){
            const point=spatial.scene.points[i];
            if(point.origin)continue; // sun already drawn at 0 AU
            const p=Helio.position(spatial.scene,point,w,h,
                                    spatial.spatialScale,spatial.tiltView,
                                    spatial.radialDomainAu);
            if(!p)continue;
            const focused=point.body===spatial.selectedBody
                || point.body===spatial.hoveredBody;
            ctx.globalAlpha=focused?0.91:0.5;
            ctx.strokeStyle=String(point.color);
            ctx.lineWidth=focused?2.5:1.3;
            ctx.beginPath();
            ctx.moveTo(g.cx,g.cy);
            ctx.lineTo(p.x,p.y);
            ctx.stroke();

            ctx.globalAlpha=1;
            ctx.fillStyle=String(point.color);
            ctx.shadowColor=String(point.color);
            ctx.shadowBlur=spatial.neonEnabled?(focused?11:4):0;
            ctx.beginPath();
            ctx.arc(p.x,p.y,focused?7:5,0,Math.PI*2);
            ctx.fill();
            ctx.shadowBlur=0;
            if(focused){
                ctx.strokeStyle=String(Colors.yellow);
                ctx.lineWidth=1.2;
                ctx.beginPath();
                ctx.arc(p.x,p.y,10,0,2*Math.PI);
                ctx.stroke();
            }
            ctx.fillStyle=String(point.color);
            ctx.font="9px monospace";
            ctx.textAlign=p.x>=g.cx?"left":"right";
            ctx.fillText(point.label||point.body.toUpperCase(),
                p.x+(p.x>=g.cx?9:-9),
                Math.max(10,Math.min(h-10,p.y)));
        }
        ctx.restore();
    }

    Canvas {
        id: spatialCanvas
        anchors.fill: parent
        anchors.margins: 7
        antialiasing: true
        renderTarget: Canvas.Image
        onPaint: spatial.paint(getContext("2d"))
    }

    MouseArea {
        anchors.fill: spatialCanvas
        enabled: spatial.scene.ready
        hoverEnabled: true
        preventStealing: true
        acceptedButtons: Qt.LeftButton
        cursorShape: Qt.CrossCursor
        property real pressX: 0
        property int originalIndex: -1
        property bool didDrag: false
        onPressed: function(mouse) {
            pressX=mouse.x;
            originalIndex=spatial.focusIndex;
            didDrag=false;
        }
        onPositionChanged: function(mouse) {
            if(pressed) {
                const dx=mouse.x-pressX;
                if(Math.abs(dx)>5)didDrag=true;
                if(didDrag && originalIndex>=0)
                    spatial.sampleScrubbed(originalIndex,dx);
                return;
            }
            spatial.hoveredBody=Helio.hit(spatial.scene,
                mouse.x,mouse.y,width,height,spatial.spatialScale,
                spatial.tiltView,13,spatial.radialDomainAu);
        }
        onClicked: function(mouse) {
            if(didDrag)return;
            const body=Helio.hit(spatial.scene,
                mouse.x,mouse.y,width,height,spatial.spatialScale,
                spatial.tiltView,14,spatial.radialDomainAu);
            if(body!=="")spatial.bodyPicked(body);
        }
        onCanceled: didDrag=false
        onExited: {if(!pressed)spatial.hoveredBody="";}
        onWheel: function(wheel) {
            if(wheel.angleDelta.y!==0){
                spatial.spatialScale=Math.max(0.4,Math.min(5,
                    spatial.spatialScale*(wheel.angleDelta.y>0?1.25:0.8)));
                wheel.accepted=true;
            }
        }
    }

    Column {
        visible: !spatial.embedded
        anchors.top: parent.top
        anchors.topMargin: 5
        anchors.right: parent.right
        anchors.rightMargin: 5
        width: Math.max(122,parent.width*0.29)
        spacing: 5
        GohuText {
            width: parent.width
            font.pixelSize: 11
            color: Colors.magenta
            text: "JPL // HELIOSPATIAL"
            elide: Text.ElideRight
        }
        Row {
            id: projectionControls
            width: parent.width
            height: 23
            spacing: 3
            ActionButton {
                width: Math.max(1,(projectionControls.width-projectionControls.spacing)/2)
                height: 22
                contentPadding: 0
                labelPixelSize: 9
                label: "TOP"
                accentColor: Colors.cyan
                selected: !spatial.tiltView
                onClicked: spatial.tiltView=false
            }
            ActionButton {
                width: Math.max(1,(projectionControls.width-projectionControls.spacing)/2)
                height: 22
                contentPadding: 0
                labelPixelSize: 9
                label: "TILT"
                accentColor: Colors.magenta
                selected: spatial.tiltView
                onClicked: spatial.tiltView=true
            }
        }
        Row {
            id: rangeControls
            width: parent.width
            height: 23
            spacing: 3
            ActionButton {
                width: Math.max(1,(rangeControls.width-rangeControls.spacing)/2)
                height: 22
                label: "ALL AU"
                labelPixelSize: 9
                contentPadding: 0
                accentColor: Colors.cyan
                selected: spatial.atlasRange==="all"
                onClicked: spatial.atlasRange="all"
            }
            ActionButton {
                width: Math.max(1,(rangeControls.width-rangeControls.spacing)/2)
                height: 22
                label: "INNER 4 AU"
                labelPixelSize: 9
                contentPadding: 0
                accentColor: Colors.magenta
                selected: spatial.atlasRange==="inner"
                onClicked: spatial.atlasRange="inner"
            }
        }
        QuietText {
            width: parent.width
            color: spatial.scene.ready?Colors.cyan:Colors.orange
            font.pixelSize: 9
            wrapMode: Text.WordWrap
            text: spatial.scene.ready
                  ? spatial.scene.count+" JPL BODIES // "
                    +spatial.scene.utc+" // "
                    +spatial.scene.source+" / "+spatial.scene.hash
                  : spatial.scene.reason
        }
        QuietText {
            width: parent.width
            color: Colors.yellow
            font.pixelSize: 9
            wrapMode: Text.WordWrap
            text: "ORIGIN: SUN // GEOMETRIC"
                  +" // ECLIPTIC OF DATE"
        }
        QuietText {
            width: parent.width
            color: Colors.magenta
            font.pixelSize: 10
            wrapMode: Text.WordWrap
            text: Helio.detail(spatial.focusPoint)
        }
        Repeater {
            model: spatial.scene.ready?spatial.scene.points:[]
            delegate: ActionButton {
                required property var modelData
                width: parent.width
                height: 22
                contentPadding: 1
                labelPixelSize: 9
                accentColor: Colors.cyan
                label: modelData.body.toUpperCase()
                       +" "+modelData.distance_au.toFixed(3)+" AU"
                selected: spatial.selectedBody===modelData.body
                onClicked: spatial.bodyPicked(modelData.body)
            }
        }
        QuietText {
            width: parent.width
            color: Colors.orange
            font.pixelSize: 9
            wrapMode: Text.WordWrap
            text: "SCALE // "+(spatial.scene.ready
                  ? spatial.radialDomainAu.toFixed(3)+" AU GRID RING"
                  : "UNAVAILABLE")
        }
    }

    QuietText {
        anchors.left: parent.left
        anchors.leftMargin: 4
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 4
        width: Math.max(0,parent.width*0.67)
        font.pixelSize: 9
        color: Colors.orange
        elide: Text.ElideRight
        text: spatial.atlasRange==="inner"
              ? "INNER 4 AU WINDOW // OUTER BODIES MAY BE OFFSCREEN"
              : "ONE UTC SNAPSHOT // NO ORBITS // DRAG TIME / WHEEL SCALE"
    }
}
