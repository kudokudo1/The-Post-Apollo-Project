import QtQuick
import "../../components"
import "StationMagickNatalWheelPolicy.js" as Chart
import "StationMagickWheelViewportPolicy.js" as Viewport

// M8a // Source-gated natal chart wheel. Zodiac labels are a REFERENCE ring.
// Actual planets, ASC, MC, houses and aspects render ONLY from a complete
// source-bound chart. Existing selected-pair output is deliberately rejected.
Rectangle {
    id: natal
    color: Colors.black
    clip: true
    property var chartData: null
    readonly property var model: Chart.validate(chartData)
    property real zoom: 1.25
    property real panX: 0
    property real panY: 0
    property string selectedPlanet: ""
    readonly property real fitRadius: Viewport.fitRadius(wheel.width,wheel.height)
    function fit(){zoom=1;panX=0;panY=0;}
    function zoomAt(factor,x,y){
        const out=Viewport.zoomAt(zoom,panX,panY,factor,
             x,y,wheel.width,wheel.height,fitRadius);
        if(!out)return;
        zoom=out.zoom;panX=out.panX;panY=out.panY;
    }
    function drag(dx,dy) {
        const p=Viewport.boundedPan(panX+dx,panY+dy,fitRadius,zoom);
        panX=p.x;panY=p.y;
    }
    onModelChanged:{ selectedPlanet="";wheel.requestPaint(); }
    onSelectedPlanetChanged: wheel.requestPaint()
    onZoomChanged: wheel.requestPaint()
    onPanXChanged: wheel.requestPaint()
    onPanYChanged: wheel.requestPaint()

    Row {
        id: toolbar
        anchors.top:parent.top
        anchors.left:parent.left
        anchors.right:parent.right
        height:25
        spacing:3
        QuietText {
            width:Math.max(65,parent.width-38-38-42-3*toolbar.spacing)
            height:24;color:Colors.yellow;font.pixelSize:9
            verticalAlignment:Text.AlignVCenter
            text:natal.model.ready?"NATAL // SOURCE-VERIFIED":"NATAL // REFERENCE ONLY"
            elide:Text.ElideRight
        }
        ActionButton {
            width:38;height:24;label:"−";labelPixelSize:12
            available:natal.zoom>1;accentColor:Colors.cyan
            onClicked:natal.zoomAt(1/1.25,wheel.width/2,wheel.height/2)
        }
        ActionButton {
            width:38;height:24;label:"+";labelPixelSize:12
            available:natal.zoom<8;accentColor:Colors.cyan
            onClicked:natal.zoomAt(1.25,wheel.width/2,wheel.height/2)
        }
        ActionButton {
            width:42;height:24;label:"FIT";labelPixelSize:9
            accentColor:Colors.orange
            onClicked:natal.fit()
        }
    }
    Canvas {
        id:wheel
        anchors.top: toolbar.bottom
        anchors.left:parent.left
        anchors.right:parent.right
        anchors.bottom:readout.top
        anchors.bottomMargin:2
        onWidthChanged:requestPaint()
        onHeightChanged:requestPaint()
        onPaint:{
            const ctx=getContext("2d");
            ctx.clearRect(0,0,width,height);
            ctx.save();
            ctx.translate(width/2+natal.panX,height/2+natal.panY);
            ctx.scale(natal.zoom,natal.zoom);
            const r=natal.fitRadius,ready=natal.model.ready;
            const asc=ready?natal.model.ascendant_deg:0;
            ctx.textAlign="center";ctx.textBaseline="middle";
            // This outer ring is only the fixed 12-sign zodiac reference.
            for(let i=0;i<12;i++){
                const a=Chart.canonicalAngle(i*30,asc),b=Chart.canonicalAngle((i+1)*30,asc);
                const start=Math.min(a,b),end=Math.max(a,b);
                ctx.fillStyle=String(Colors.dark);
                ctx.strokeStyle=String(Colors.blue);
                ctx.lineWidth=1.2;ctx.globalAlpha=.8;
                ctx.beginPath();
                ctx.arc(0,0,r*.97,start,end);
                ctx.arc(0,0,r*.75,end,start,true);
                ctx.closePath();
                ctx.fill();ctx.stroke();
                const label=Chart.point(i*30+15,asc,r*.86);
                ctx.fillStyle=String(i%3===0?Colors.yellow:Colors.cyan);
                ctx.font="9px monospace";ctx.globalAlpha=1;
                ctx.fillText(Chart.SIGNS[i].slice(0,3),label.x,label.y);
            }
            ctx.beginPath();ctx.arc(0,0,r*.53,0,2*Math.PI);
            ctx.strokeStyle=String(ready?Colors.magenta:Colors.blue);
            ctx.lineWidth=1.5;ctx.stroke();
            if(ready){
                for(let j=0;j<12;j++){
                    const a=Chart.canonicalAngle(natal.model.cusps[j],asc);
                    ctx.strokeStyle=String(j===0?Colors.magenta:Colors.cyan);
                    ctx.globalAlpha=j===0?1:.6;
                    ctx.lineWidth=j===0?2:1;
                    ctx.beginPath();ctx.moveTo(0,0);
                    ctx.lineTo(Math.cos(a)*r*.74,Math.sin(a)*r*.74);
                    ctx.stroke();ctx.globalAlpha=1;
                    const p=Chart.point(natal.model.cusps[j]+8,asc,r*.64);
                    ctx.font="8px monospace";ctx.fillStyle=String(Colors.yellow);
                    ctx.fillText(String(j+1),p.x,p.y);
                }
                natal.model.aspects.forEach(function(a) {
                    const p=natal.model.planets.find(function(x){return x.id===a.a;});
                    const q=natal.model.planets.find(function(x){return x.id===a.b;});
                    if(!p||!q)return;
                    const l=Chart.point(p.longitude_deg,asc,r*.38),
                          k=Chart.point(q.longitude_deg,asc,r*.38);
                    ctx.globalAlpha=.64;
                    ctx.strokeStyle=String(a.name==="trine"?Colors.cyan:
                        a.name==="square"?Colors.orange:Colors.magenta);
                    ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(l.x,l.y);
                    ctx.lineTo(k.x,k.y);ctx.stroke();ctx.globalAlpha=1;
                });
                natal.model.planets.forEach(function(p) {
                    const position=Chart.point(p.longitude_deg,asc,r*.48);
                    const selected=p.id===natal.selectedPlanet;
                    ctx.fillStyle=String(Colors.black);
                    ctx.strokeStyle=String(selected?Colors.magenta:Colors.yellow);
                    ctx.lineWidth=selected?2.5:1;
                    ctx.beginPath();ctx.arc(position.x,position.y,9,0,Math.PI*2);
                    ctx.fill();ctx.stroke();
                    ctx.font="bold 7px monospace";ctx.fillStyle=String(Colors.white);
                    ctx.fillText(p.id.slice(0,2).toUpperCase(),position.x,position.y);
                });
                const ascPoint=Chart.point(natal.model.ascendant_deg,asc,r*.68);
                ctx.fillStyle=String(Colors.magenta);ctx.font="bold 9px monospace";
                ctx.fillText("ASC",ascPoint.x,ascPoint.y);
                const mcPoint=Chart.point(natal.model.mc_deg,asc,r*.70);
                ctx.fillStyle=String(Colors.yellow);
                ctx.fillText("MC",mcPoint.x,mcPoint.y);
            } else {
                ctx.fillStyle=String(Colors.orange);
                ctx.font="10px monospace";
                ctx.fillText("NO VERIFIED",0,-10);
                ctx.fillText("FULL CHART",0,7);
                ctx.font="8px monospace";ctx.fillStyle=String(Colors.cyan);
                ctx.fillText("REFERENCE SIGNS ONLY",0,23);
            }
            ctx.restore();
        }
        MouseArea {
            id:touch
            anchors.fill:parent
            hoverEnabled:true
            cursorShape:pressed?Qt.ClosedHandCursor:Qt.OpenHandCursor
            property real sx:0
            property real sy:0
            property real lastX:0
            property real lastY:0
            property bool dragged:false
            onPressed:function(mouse){ sx=lastX=mouse.x;sy=lastY=mouse.y;dragged=false; }
            onPositionChanged:function(mouse){
                if(!pressed)return;
                if(Math.hypot(mouse.x-sx,mouse.y-sy)>5)dragged=true;
                if(dragged)natal.drag(mouse.x-lastX,mouse.y-lastY);
                lastX=mouse.x;lastY=mouse.y;
            }
            onWheel:function(wheel){
                if(wheel.angleDelta.y===0)return;
                natal.zoomAt(wheel.angleDelta.y>0?1.2:1/1.2,wheel.x,wheel.y);
                wheel.accepted=true;
            }
            onDoubleClicked:natal.fit()
            onClicked:function(mouse){
                if(dragged||!natal.model.ready)return;
                const p=Viewport.inversePoint(mouse.x,mouse.y,width,height,
                    natal.panX,natal.panY,natal.zoom);
                if(!p)return;
                let nearest=null,d=16;
                natal.model.planets.forEach(function(body){
                    const at=Chart.point(body.longitude_deg,
                        natal.model.ascendant_deg,natal.fitRadius*.48);
                    const v=Math.hypot(p.x-at.x,p.y-at.y);
                    if(v<d){d=v;nearest=body;}
                });
                if(nearest)natal.selectedPlanet=nearest.id;
            }
        }
    }
    Column {
        id:readout
        anchors.bottom:parent.bottom
        anchors.left:parent.left
        anchors.right:parent.right
        spacing:2
        height:implicitHeight
        QuietText {
            width:parent.width;height:20
            font.pixelSize:10
            color:natal.model.ready?Colors.cyan:Colors.orange
            elide:Text.ElideRight
            text:natal.model.ready
                ? natal.model.epoch_utc+" / ASC "+
                    natal.model.ascendant_deg.toFixed(2)+"° / MC "+
                    natal.model.mc_deg.toFixed(2)+"°"
                :"FULL NATAL CALCULATION NOT CONNECTED"
        }
        QuietText {
            width:parent.width;height:17
            font.pixelSize:9
            color:Colors.yellow;elide:Text.ElideRight
            text:natal.model.ready
                ? (natal.selectedPlanet
                   ? natal.selectedPlanet.toUpperCase()+" / "+
                     natal.model.planets.find(function(p){
                         return p.id===natal.selectedPlanet;}).longitude_deg.toFixed(2)+"°"
                   : natal.model.house_system.toUpperCase()+" / "+
                     natal.model.zodiac.toUpperCase())
                :"JPL PAIR IS NOT A BIRTH CHART / NO PLANETS OR HOUSES INVENTED"
        }
    }
}
