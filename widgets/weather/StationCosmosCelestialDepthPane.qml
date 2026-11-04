import QtQuick
import "../../components"
import "StationCosmosCelestialDepthPolicy.js" as Depth
import "StationMagickCelestialVisualPolicy.js" as Celestial

// V4b // Earth-centered APPARENT JPL distance/direction at exact M4 UTC.
// No heliocentric orbit, physical instantaneous solar system or fake trail.
Item {
    id: depthPane
    property var graphModel: null
    property var verifiedScene: null
    property int focusIndex: -1
    property string selectedBody: ""
    property bool neonEnabled: true
    property string hoverBody: ""
    readonly property var depthScene: Depth.depth(
        graphModel,focusIndex,verifiedScene)
    readonly property var focusPoint: Depth.byBody(
        depthScene,selectedBody)
    readonly property string focusDetail: Depth.detail(focusPoint)

    signal bodyPicked(string body)
    signal sampleScrubbed(int originIndex, real offsetPixels)
    signal zoomRequested(int direction)

    onDepthSceneChanged: depthCanvas.requestPaint()
    onSelectedBodyChanged: depthCanvas.requestPaint()
    onHoverBodyChanged: depthCanvas.requestPaint()
    onWidthChanged: depthCanvas.requestPaint()
    onHeightChanged: depthCanvas.requestPaint()

    function paint(ctx) {
        const width=depthCanvas.width,height=depthCanvas.height;
        ctx.clearRect(0,0,width,height);
        const g=Depth.layout(width,height);
        if(!g.ready)return;
        ctx.save();
        ctx.textAlign="center";
        ctx.textBaseline="middle";
        ctx.font="9px monospace";
        for(let ring=1;ring<=4;ring++){
            const radius=g.r*ring/4;
            ctx.beginPath();
            ctx.arc(g.cx,g.cy,radius,0,2*Math.PI);
            ctx.strokeStyle=String(ring===4?Colors.cyan:Colors.blue);
            ctx.globalAlpha=ring===4?0.65:0.28;
            ctx.lineWidth=ring===4?1.4:1;
            ctx.stroke();
        }
        for(let degree=0;degree<360;degree+=45){
            const a=degree*Math.PI/180;
            ctx.beginPath();
            ctx.moveTo(g.cx+Math.sin(a)*(g.r-3),
                       g.cy-Math.cos(a)*(g.r-3));
            ctx.lineTo(g.cx+Math.sin(a)*(g.r+3),
                       g.cy-Math.cos(a)*(g.r+3));
            ctx.globalAlpha=0.8;
            ctx.strokeStyle=String(Colors.yellow);
            ctx.stroke();
        }
        ctx.globalAlpha=1;
        ctx.fillStyle=String(Colors.yellow);
        for(const ref of [{v:0,t:"0°"},{v:90,t:"90°"},
                          {v:180,t:"180°"},{v:270,t:"270°"}]){
            const a=ref.v*Math.PI/180;
            ctx.fillText(ref.t,g.cx+Math.sin(a)*(g.r+14),
                         g.cy-Math.cos(a)*(g.r+14));
        }
        ctx.fillStyle=String(Colors.magenta);
        ctx.beginPath();
        ctx.arc(g.cx,g.cy,4,0,2*Math.PI);
        ctx.fill();
        ctx.fillStyle=String(Colors.yellow);
        ctx.fillText("EARTH",g.cx,g.cy+15);

        if(!depthPane.depthScene.ready){
            ctx.fillStyle=String(Colors.orange);
            ctx.fillText("NO M4 APPARENT DISTANCE",g.cx,g.cy-14);
            ctx.restore();
            return;
        }

        for(let i=0;i<depthPane.depthScene.points.length;i++){
            const point=depthPane.depthScene.points[i];
            const projected=Depth.projected(
                depthPane.depthScene,point,width,height);
            if(!projected)continue;
            const focused=depthPane.selectedBody===point.body
                || depthPane.hoverBody===point.body;
            ctx.beginPath();
            ctx.moveTo(g.cx,g.cy);
            ctx.lineTo(projected.x,projected.y);
            ctx.strokeStyle=String(point.color);
            ctx.lineWidth=focused?2.6:1.3;
            ctx.globalAlpha=focused?0.95:0.48;
            ctx.shadowColor=String(point.color);
            ctx.shadowBlur=depthPane.neonEnabled&&focused?8:0;
            ctx.stroke();
            ctx.shadowBlur=0;
            ctx.fillStyle=String(point.color);
            ctx.globalAlpha=1;
            ctx.beginPath();
            ctx.arc(projected.x,projected.y,focused?8:5,0,2*Math.PI);
            ctx.shadowColor=String(point.color);
            ctx.shadowBlur=depthPane.neonEnabled?(focused?12:4):0;
            ctx.fill();
            ctx.shadowBlur=0;
            if(focused){
                ctx.strokeStyle=String(Colors.yellow);
                ctx.lineWidth=1.3;
                ctx.beginPath();
                ctx.arc(projected.x,projected.y,11,0,2*Math.PI);
                ctx.stroke();
            }
            ctx.textAlign=projected.x>=g.cx?"left":"right";
            ctx.font="9px monospace";
            ctx.fillStyle=String(point.color);
            ctx.fillText(Celestial.shortBodyName(point.body),
                projected.x+(projected.x>=g.cx?9:-9),
                Math.max(8,Math.min(height-8,projected.y)));
        }
        ctx.restore();
    }

    Canvas {
        id: depthCanvas
        anchors.fill: parent
        antialiasing: true
        renderTarget: Canvas.Image
        onPaint: depthPane.paint(getContext("2d"))
    }

    MouseArea {
        anchors.fill: parent
        enabled: depthPane.depthScene.ready
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton
        preventStealing: true
        cursorShape: Qt.CrossCursor
        property real pressX: 0
        property int originIndex: -1
        property bool didDrag: false
        onPressed: function(mouse) {
            pressX=mouse.x;
            originIndex=depthPane.focusIndex;
            didDrag=false;
        }
        onPositionChanged: function(mouse) {
            if(pressed){
                const dx=mouse.x-pressX;
                if(Math.abs(dx)>5)didDrag=true;
                if(didDrag && originIndex>=0)
                    depthPane.sampleScrubbed(originIndex,dx);
                return;
            }
            depthPane.hoverBody=Depth.hit(depthPane.depthScene,
                mouse.x,mouse.y,width,height,13);
        }
        onClicked: function(mouse) {
            if(didDrag)return;
            const body=Depth.hit(depthPane.depthScene,
                mouse.x,mouse.y,width,height,15);
            if(body!=="")depthPane.bodyPicked(body);
        }
        onCanceled: didDrag=false
        onExited: {if(!pressed)depthPane.hoverBody="";}
        onWheel: function(wheel) {
            if(wheel.angleDelta.y!==0){
                depthPane.zoomRequested(wheel.angleDelta.y>0?1:-1);
                wheel.accepted=true;
            }
        }
    }

    QuietText {
        anchors.left: parent.left
        anchors.leftMargin: 5
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 5
        width: Math.max(0,parent.width*0.68)
        font.pixelSize: 9
        color: Colors.orange
        elide: Text.ElideRight
        text: depthPane.depthScene.ready
              ? "LINEAR AU // OUTER "+depthPane.depthScene.maxDistanceAu.toFixed(4)
                +" AU // APPARENT GEOCENTRIC"
              : "NO PHYSICAL ORBITS // AWAITING VALIDATED SOURCE"
    }
}
