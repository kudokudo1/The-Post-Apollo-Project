import QtQuick
import "../../components"
import "StationMagickTraditionalDialPolicy.js" as Dial
import "StationMagickWheelViewportPolicy.js" as Viewport

// M8a // This instrument visualizes measured SOURCE civil-minute boundaries.
// Ruler names are Chaldean tradition; DST elapsed durations remain unverified.
// Same forecast / same M6d plan, no second source actor or saved data.
Rectangle {
    id: clock
    color: Colors.black
    clip: true
    property var plan: null
    property int selectedHour: 0
    property string targetDate: ""
    property var sourceDates: []
    signal hourRequested(int index)
    signal dayRequested(int delta)
    signal lanesRequested()
    readonly property var model: Dial.build(plan)
    readonly property var current: model.ready?model.sectors[
        Math.max(0,Math.min(23,selectedHour))]:null
    property real zoom: 1.2
    property real panX: 0
    property real panY: 0
    readonly property real fitRadius: Viewport.fitRadius(dialCanvas.width,dialCanvas.height)
    function fit(){zoom=1;panX=0;panY=0;}
    function zoomBy(mult,x,y){
        const next=Viewport.zoomAt(zoom,panX,panY,mult,
            x,y,dialCanvas.width,dialCanvas.height,fitRadius);
        if(!next)return;
        zoom=next.zoom;panX=next.panX;panY=next.panY;
    }
    function move(dx,dy){
        const next=Viewport.boundedPan(panX+dx,panY+dy,fitRadius,zoom);
        panX=next.x;panY=next.y;
    }
    onModelChanged: dialCanvas.requestPaint()
    onSelectedHourChanged: dialCanvas.requestPaint()
    onZoomChanged: dialCanvas.requestPaint()
    onPanXChanged: dialCanvas.requestPaint()
    onPanYChanged: dialCanvas.requestPaint()
    onWidthChanged: dialCanvas.requestPaint()
    onHeightChanged: dialCanvas.requestPaint()

    Row {
        id: tools
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 25
        spacing: 3
        ActionButton {
            width: 48;height:24;label:"◀ DAY";labelPixelSize:8
            accentColor:Colors.cyan
            available:clock.sourceDates.indexOf(clock.targetDate)>0
            onClicked:clock.dayRequested(-1)
        }
        QuietText {
            width:Math.max(20,tools.width-48-48-52-34-34-38-5*tools.spacing)
            height:24
            color:Colors.yellow;font.pixelSize:10
            horizontalAlignment:Text.AlignHCenter
            verticalAlignment:Text.AlignVCenter
            elide:Text.ElideRight
            text:clock.targetDate||"SOURCE DATE"
        }
        ActionButton {
            width:48;height:24;label:"DAY ▶";labelPixelSize:8
            accentColor:Colors.cyan
            available:clock.sourceDates.indexOf(clock.targetDate)>=0 &&
                 clock.sourceDates.indexOf(clock.targetDate)<clock.sourceDates.length-1
            onClicked:clock.dayRequested(1)
        }
        ActionButton {
            width:34;height:24;label:"−";labelPixelSize:11
            accentColor:Colors.cyan;available:clock.zoom>1
            onClicked:clock.zoomBy(1/1.25,dialCanvas.width/2,dialCanvas.height/2)
        }
        ActionButton {
            width:34;height:24;label:"+";labelPixelSize:11
            accentColor:Colors.cyan;available:clock.zoom<8
            onClicked:clock.zoomBy(1.25,dialCanvas.width/2,dialCanvas.height/2)
        }
        ActionButton {
            width:38;height:24;label:"FIT";labelPixelSize:8
            accentColor:Colors.orange
            onClicked:clock.fit()
        }
        ActionButton {
            width:52;height:24;label:"LANES";labelPixelSize:8
            accentColor:Colors.magenta
            onClicked:clock.lanesRequested()
        }
    }
    QuietText {
        id: source
        anchors.top: tools.bottom
        anchors.left:parent.left
        anchors.right:parent.right
        height:17
        font.pixelSize:9
        color:clock.model.ready?Colors.cyan:Colors.orange
        text:clock.model.ready
            ?"24 SOURCE DIVISIONS // CHALDEAN CIVIL CLOCK // "+
                Math.round(clock.zoom*100)+"%"
            :clock.model.reason
        elide:Text.ElideRight
    }
    Canvas {
        id:dialCanvas
        anchors.top:source.bottom
        anchors.left:parent.left
        anchors.right:parent.right
        anchors.bottom: detail.top
        anchors.bottomMargin:2
        onWidthChanged:requestPaint()
        onHeightChanged:requestPaint()
        onPaint: {
            const ctx=getContext("2d");
            ctx.clearRect(0,0,width,height);
            ctx.save();
            ctx.translate(width/2+clock.panX,height/2+clock.panY);
            ctx.scale(clock.zoom,clock.zoom);
            const r=clock.fitRadius;
            ctx.textAlign="center";ctx.textBaseline="middle";
            const sectors=clock.model.sectors;
            for(let i=0;i<sectors.length;i++){
                const v=sectors[i],selected=i===clock.selectedHour;
                const ink=v.ruler==="sun"?Colors.yellow:v.ruler==="venus"?Colors.magenta:
                    v.ruler==="mars"?Colors.orange:v.ruler==="jupiter"?Colors.blue:
                    v.ruler==="saturn"?Colors.white:Colors.cyan;
                const inner=r*.48,outer=r*.94;
                ctx.beginPath();
                ctx.arc(0,0,outer,v.startAngle,v.endAngle);
                ctx.arc(0,0,inner,v.endAngle,v.startAngle,true);
                ctx.closePath();
                ctx.fillStyle=String(v.phase==="day"?Colors.dark:Colors.black);
                ctx.fill();
                ctx.strokeStyle=String(selected?Colors.magenta:ink);
                ctx.lineWidth=selected?3:1.2;
                ctx.globalAlpha=selected?1:0.76;
                ctx.stroke();ctx.globalAlpha=1;
                const middle=(v.startAngle+v.endAngle)/2;
                const tx=r*.74*Math.cos(middle),ty=r*.74*Math.sin(middle);
                ctx.fillStyle=String(ink);
                ctx.font=selected?"bold 10px monospace":"9px monospace";
                ctx.fillText(String(i+1),tx,ty);
            }
            ctx.strokeStyle=String(Colors.yellow);
            ctx.lineWidth=2;
            ctx.beginPath();ctx.arc(0,0,r*.43,0,2*Math.PI);ctx.stroke();
            ctx.font="bold 12px monospace";
            ctx.fillStyle=String(Colors.magenta);
            ctx.fillText("24 HOURS",0,-16);
            ctx.fillStyle=String(Colors.yellow);
            ctx.font="10px monospace";
            ctx.fillText(clock.current?clock.current.ruler.toUpperCase():"AWAITING",0,2);
            ctx.font="9px monospace";
            ctx.fillStyle=String(Colors.cyan);
            ctx.fillText(clock.current?clock.current.phase.toUpperCase():"SOURCE",0,18);
            ctx.restore();
        }
        MouseArea {
            id:touch
            anchors.fill:parent
            hoverEnabled:true
            cursorShape:pressed?Qt.ClosedHandCursor:Qt.OpenHandCursor
            property real pressX:0
            property real pressY:0
            property real lastX:0
            property real lastY:0
            property bool moved:false
            onPressed:function(mouse){
                pressX=lastX=mouse.x;pressY=lastY=mouse.y;moved=false;
            }
            onPositionChanged:function(mouse){
                if(!touch.pressed)return;
                if(Math.hypot(mouse.x-pressX,mouse.y-pressY)>5)moved=true;
                if(moved)clock.move(mouse.x-lastX,mouse.y-lastY);
                lastX=mouse.x;lastY=mouse.y;
            }
            onWheel:function(wheel) {
                if(wheel.angleDelta.y===0)return;
                clock.zoomBy(wheel.angleDelta.y>0?1.2:1/1.2,wheel.x,wheel.y);
                wheel.accepted=true;
            }
            onDoubleClicked:clock.fit()
            onClicked:function(mouse) {
                if(moved||!clock.model.ready)return;
                const p=Viewport.inversePoint(mouse.x,mouse.y,width,height,
                                              clock.panX,clock.panY,clock.zoom);
                if(!p)return;
                const geometry={cx:0,cy:0,inner:clock.fitRadius*.48,
                                outer:clock.fitRadius*.94};
                const i=Dial.select(clock.model,geometry,p.x,p.y);
                if(i>=0)clock.hourRequested(i);
            }
        }
    }
    Column {
        id:detail
        anchors.left:parent.left
        anchors.right:parent.right
        anchors.bottom:parent.bottom
        spacing:2
        height:implicitHeight
        QuietText {
            width:parent.width;height:20
            color:Colors.yellow;font.pixelSize:10
            elide:Text.ElideRight
            text:clock.current?clock.current.ruler.toUpperCase()+
                " / "+clock.current.phase.toUpperCase()+" H"+
                clock.current.ordinal+" / "+clock.current.startLabel+
                " TO "+clock.current.endLabel:"SELECT SOURCE HOUR"
        }
        QuietText {
            width:parent.width;height:17
            color:Colors.orange;font.pixelSize:9
            text:"CIVIL CLOCK ONLY / DST ELAPSED TIME UNVERIFIED"
            elide:Text.ElideRight
        }
        QuietText {
            width:parent.width;height:15
            color:Colors.cyan;font.pixelSize:8
            text:"HISTORICAL RULERS / NO ASTRONOMICAL CAUSATION CLAIM"
            elide:Text.ElideRight
        }
    }
}
