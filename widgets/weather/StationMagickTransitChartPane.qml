import QtQuick
import "../../components"
import "StationMagickNatalWheelPolicy.js" as Chart
import "StationMagickTransitComparisonPolicy.js" as Transit
import "StationMagickWheelViewportPolicy.js" as Viewport
import "StationMagickDateLocationPolicy.js" as Defaults

// M8c // Dual-epoch chart, from TWO complete M8b/JPL results at one explicit
// observer location. No hidden time now, forecast, guess, or persisted record.
Rectangle {
    id: transits
    color: Colors.black
    clip: true
    property var natalData: null
    property var transitData: null
    property string expectedUtc: ""
    property string selectedContactUtc: ""
    property string selectedEventKind: "aspect"
    property string inspectionTarget: ""
    property string inspectionNatal: ""
    onInspectionTargetChanged: {
        if(Transit.TARGETS.indexOf(inspectionTarget)>=0)
            selectedTarget=inspectionTarget;
    }
    property string statusText: ""
    property bool loading: false
    property string dateText: ""
    property string timeText: ""
    property real orbDegrees: 3
    property string selectedTarget: "sun"
    property real zoom: 1.35
    property real panX: 0
    property real panY: 0
    signal calculateRequested(string epochUtc)
    readonly property var natalChart: Chart.validate(natalData)
    readonly property var transitChart: Chart.validate(transitData)
    readonly property var comparison: Transit.build(
        natalChart,transitChart,natalData,transitData,expectedUtc,orbDegrees)
    readonly property real fitRadius: Viewport.fitRadius(wheel.width,wheel.height)
    readonly property var selectedDelta: comparison.ready
        ? comparison.deltas.find(function(d){return d.id===selectedTarget;}) : null
    readonly property var relatedAspects: comparison.ready
        ? comparison.aspects.filter(function(a){return a.transit_id===selectedTarget;}) : []
    function fit(){zoom=1;panX=0;panY=0;}
    function zoomAt(factor,x,y){
        const v=Viewport.zoomAt(zoom,panX,panY,factor,
            x,y,wheel.width,wheel.height,fitRadius);
        if(!v)return;
        zoom=v.zoom;panX=v.panX;panY=v.panY;
    }
    function pan(dx,dy){
        const p=Viewport.boundedPan(panX+dx,panY+dy,fitRadius,zoom);
        panX=p.x;panY=p.y;
    }
    function clearEntry(){dateText="";timeEntry.text="";timeText="";}
    function setCurrentInstant(){
        const current=Defaults.utcClock();
        if(!current)return;
        dateText=current.date;
        timeEntry.text=current.time;
    }
    onVisibleChanged: {
        if(visible){
            if(!dateText)dateText=Defaults.utcDay();
        }else clearEntry();
    }
    onNatalDataChanged: {
        clearEntry();
        if(visible)dateText=Defaults.utcDay();
        selectedTarget=Transit.TARGETS.indexOf(inspectionTarget)>=0
            ?inspectionTarget:"sun";
        wheel.requestPaint();
    }
    onComparisonChanged:wheel.requestPaint()
    onSelectedTargetChanged:wheel.requestPaint()
    onZoomChanged:wheel.requestPaint()
    onPanXChanged:wheel.requestPaint()
    onPanYChanged:wheel.requestPaint()
    onWidthChanged:wheel.requestPaint()
    onHeightChanged:wheel.requestPaint()

    Row {
        id: sourceRow
        anchors.top:parent.top
        anchors.left:parent.left
        anchors.right:parent.right
        height:25
        spacing:3
        QuietText {
            width:Math.max(20,sourceRow.width-40-40-43-3*sourceRow.spacing)
            height:24
            verticalAlignment:Text.AlignVCenter
            font.pixelSize:9
            elide:Text.ElideRight
            color:transits.comparison.ready?Colors.cyan:Colors.orange
            text:transits.comparison.ready
                ?"JPL NATAL ↔ TRANSIT / "+transits.comparison.transit_epoch_utc
                :transits.natalChart.ready ? "NATAL READY // SELECT TRANSIT UTC"
                : "CALCULATE A NATAL CHART FIRST"
        }
        ActionButton {
            width:40;height:24;label:"−";labelPixelSize:12
            available:transits.zoom>1
            accentColor:Colors.cyan
            onClicked:transits.zoomAt(1/1.25,wheel.width/2,wheel.height/2)
        }
        ActionButton {
            width:40;height:24;label:"+";labelPixelSize:12
            available:transits.zoom<8
            accentColor:Colors.cyan
            onClicked:transits.zoomAt(1.25,wheel.width/2,wheel.height/2)
        }
        ActionButton {
            width:43;height:24;label:"FIT";labelPixelSize:9
            accentColor:Colors.orange
            onClicked:transits.fit()
        }
    }
    // M8d // Exactly the same month/day/year arrow controls as TASKS.
    Row {
        id: dateRow
        anchors.top:sourceRow.bottom
        anchors.left:parent.left
        anchors.right:parent.right
        anchors.topMargin:2
        height:26
        StationMagickUtcDateField {
            id:dateEntry
            width:parent.width
            height:26
            dateValue:transits.dateText
            canEdit:!transits.loading
            onDateEdited:function(date){transits.dateText=date;}
        }
    }
    Row {
        id: timeRow
        anchors.top:dateRow.bottom
        anchors.left:parent.left
        anchors.right:parent.right
        anchors.topMargin:2
        height:25
        spacing:3
        QuietText {
            width:52;height:24
            text:"UTC TIME"
            font.pixelSize:9
            color:Colors.cyan
            verticalAlignment:Text.AlignVCenter
        }
        Rectangle {
            width:Math.max(45,timeRow.width-52-54-74-66-4*timeRow.spacing)
            height:24
            color:Colors.dark;border.width:1;border.color:Colors.blue
            TextInput {
                id:timeEntry
                anchors.fill:parent;anchors.margins:3
                color:Colors.white;font.pixelSize:10;font.family:"monospace"
                maximumLength:5;selectByMouse:true
                inputMethodHints:Qt.ImhTime
                text:transits.timeText
                onTextChanged:transits.timeText=text
            }
        }
        ActionButton {
            width:54;height:24
            label:"NOW UTC";labelPixelSize:8
            accentColor:Colors.yellow
            available:!transits.loading
            onClicked:transits.setCurrentInstant()
        }
        ActionButton {
            width:74;height:24
            label:transits.loading?"WAIT":"TRANSIT UTC"
            labelPixelSize:8
            accentColor:Colors.magenta
            available:transits.natalChart.ready&&!transits.loading
            onClicked: {
                const instant=transits.dateText+"T"+transits.timeText+":00Z";
                if(Transit.utc(instant))transits.calculateRequested(instant);
            }
        }
        ActionButton {
            width:66;height:24;label:"ORB "+transits.orbDegrees+"°"
            labelPixelSize:8;accentColor:Colors.yellow
            onClicked:transits.orbDegrees=transits.orbDegrees===6
                ? 1:transits.orbDegrees+1
        }
    }
    QuietText {
        id:hint
        anchors.top:timeRow.bottom
        anchors.left:parent.left
        anchors.right:parent.right
        height:16
        color:Colors.cyan
        font.pixelSize:9
        elide:Text.ElideRight
        text:transits.loading?"JPL CALCULATION RUNNING":
            "UTC DATE: TASKS STEPPERS / TIME HH:MM // "+
            (transits.statusText||"NO TRANSIT LOADED")
    }
    Canvas {
        id:wheel
        anchors.top:hint.bottom
        anchors.left:parent.left
        anchors.right:parent.right
        anchors.bottom:detail.top
        anchors.bottomMargin:2
        onWidthChanged:requestPaint()
        onHeightChanged:requestPaint()
        onPaint: {
            const ctx=getContext("2d");
            ctx.clearRect(0,0,width,height);
            ctx.save();
            ctx.translate(width/2+transits.panX,height/2+transits.panY);
            ctx.scale(transits.zoom,transits.zoom);
            const r=transits.fitRadius,natal=transits.natalChart;
            const ready=transits.comparison.ready;
            const asc=natal.ready?natal.ascendant_deg:0;
            ctx.textAlign="center";ctx.textBaseline="middle";
            for(let i=0;i<12;i++){
                const a=Chart.canonicalAngle(i*30,asc);
                const b=Chart.canonicalAngle((i+1)*30,asc);
                ctx.beginPath();
                ctx.strokeStyle=String(Colors.blue);
                ctx.lineWidth=1;
                ctx.arc(0,0,r*.98,Math.min(a,b),Math.max(a,b));
                ctx.stroke();
                const p=Chart.point(i*30+15,asc,r*.86);
                ctx.fillStyle=String(Colors.cyan);
                ctx.font="9px monospace";
                ctx.fillText(Chart.SIGNS[i].slice(0,3),p.x,p.y);
            }
            [0.29,0.46,0.61,0.73].forEach(function(f) {
                ctx.beginPath();ctx.strokeStyle=String(Colors.blue);
                ctx.lineWidth=1;ctx.arc(0,0,r*f,0,2*Math.PI);ctx.stroke();
            });
            if(natal.ready){
                natal.cusps.forEach(function(deg,i){
                    const p=Chart.point(deg,asc,r*.76);
                    ctx.beginPath();ctx.strokeStyle=String(i===0?Colors.magenta:Colors.blue);
                    ctx.lineWidth=i===0?2:1;
                    ctx.moveTo(0,0);ctx.lineTo(p.x,p.y);ctx.stroke();
                });
                // For readability, only the selected transit body's aspects
                // connect to natal bodies; no 100-line obscuring spiderweb.
                if(ready){
                    transits.relatedAspects.forEach(function(a) {
                        const t=transits.comparison.transit.find(
                            function(p){return p.id===a.transit_id;});
                        const n=transits.comparison.natal.find(
                            function(p){return p.id===a.natal_id;});
                        if(!t||!n)return;
                        const p=Chart.point(t.longitude_deg,asc,r*.62),
                              q=Chart.point(n.longitude_deg,asc,r*.40);
                        ctx.beginPath();
                        ctx.strokeStyle=String(a.name==="square"?Colors.orange:
                           a.name==="trine"?Colors.cyan:Colors.magenta);
                        ctx.globalAlpha=.68;ctx.lineWidth=1;
                        ctx.moveTo(p.x,p.y);ctx.lineTo(q.x,q.y);ctx.stroke();
                        ctx.globalAlpha=1;
                    });
                }
                natal.planets.forEach(function(n) {
                    const p=Chart.point(n.longitude_deg,asc,r*.40);
                    ctx.beginPath();ctx.fillStyle=String(Colors.black);
                    ctx.strokeStyle=String(Colors.yellow);ctx.lineWidth=1.4;
                    ctx.arc(p.x,p.y,7,0,2*Math.PI);ctx.fill();ctx.stroke();
                    ctx.font="bold 7px monospace";ctx.fillStyle=String(Colors.white);
                    ctx.fillText(n.id.slice(0,2).toUpperCase(),p.x,p.y);
                });
                if(ready)transits.comparison.transit.forEach(function(t){
                    const p=Chart.point(t.longitude_deg,asc,r*.62);
                    const selected=t.id===transits.selectedTarget;
                    ctx.beginPath();ctx.fillStyle=String(Colors.black);
                    ctx.strokeStyle=String(selected?Colors.magenta:Colors.cyan);
                    ctx.lineWidth=selected?2.5:1.4;
                    ctx.arc(p.x,p.y,8,0,Math.PI*2);ctx.fill();ctx.stroke();
                    ctx.font="bold 7px monospace";ctx.fillStyle=String(Colors.white);
                    ctx.fillText(t.id.slice(0,2).toUpperCase(),p.x,p.y);
                });
            } else {
                ctx.font="10px monospace";ctx.fillStyle=String(Colors.orange);
                ctx.fillText("NATAL SOURCE REQUIRED",0,0);
            }
            ctx.font="9px monospace";ctx.fillStyle=String(Colors.yellow);
            ctx.fillText(ready?"DUAL EPOCH":"NATAL ONLY",0,-8);
            ctx.fillStyle=String(Colors.cyan);
            ctx.fillText(ready?"CYAN = TRANSIT":"ENTER TRANSIT TIME",0,9);
            ctx.restore();
        }
        MouseArea {
            id:touch
            anchors.fill:parent
            hoverEnabled:true
            cursorShape:pressed?Qt.ClosedHandCursor:Qt.OpenHandCursor
            property real startX:0
            property real startY:0
            property real lastX:0
            property real lastY:0
            property bool moved:false
            onPressed:function(mouse){
                startX=lastX=mouse.x;startY=lastY=mouse.y;moved=false;
            }
            onPositionChanged:function(mouse){
                if(!pressed)return;
                if(Math.hypot(mouse.x-startX,mouse.y-startY)>5)moved=true;
                if(moved)transits.pan(mouse.x-lastX,mouse.y-lastY);
                lastX=mouse.x;lastY=mouse.y;
            }
            onWheel:function(wheelEvent){
                if(!wheelEvent.angleDelta.y)return;
                transits.zoomAt(wheelEvent.angleDelta.y>0?1.2:1/1.2,
                                wheelEvent.x,wheelEvent.y);
                wheelEvent.accepted=true;
            }
            onDoubleClicked:transits.fit()
            onClicked:function(mouse){
                if(moved||!transits.comparison.ready)return;
                const p=Viewport.inversePoint(mouse.x,mouse.y,width,height,
                     transits.panX,transits.panY,transits.zoom);
                if(!p)return;
                let nearest="",delta=15;
                transits.comparison.transit.forEach(function(t){
                    const pt=Chart.point(t.longitude_deg,transits.natalChart.ascendant_deg,
                                         transits.fitRadius*.62);
                    const d=Math.hypot(pt.x-p.x,pt.y-p.y);
                    if(d<delta){nearest=t.id;delta=d;}
                });
                if(nearest)transits.selectedTarget=nearest;
            }
        }
    }
    Column {
        id:detail
        anchors.bottom:parent.bottom
        anchors.left:parent.left
        anchors.right:parent.right
        height:implicitHeight
        spacing:2
        QuietText {
            width:parent.width;height:19;font.pixelSize:9
            color:Colors.yellow;elide:Text.ElideRight
            text:transits.selectedDelta
              ? transits.selectedTarget.toUpperCase()+" // NATAL "+
                 transits.selectedDelta.natal_deg.toFixed(2)+"° / TRANSIT "+
                 transits.selectedDelta.transit_deg.toFixed(2)+"°"
              : "NATAL YELLOW / TRANSIT CYAN / SELECT CYAN PLANET"
        }
        QuietText {
            width:parent.width;height:18;font.pixelSize:9
            color:Colors.magenta;elide:Text.ElideRight
            text:transits.selectedDelta
              ? "SIGNED SHIFT "+transits.selectedDelta.signed_delta_deg.toFixed(2)+
                "° // CROSS-ASPECTS "+transits.relatedAspects.length
              : "SEPARATE UTC EPOCHS / SAME EXPLICIT OBSERVER AND JPL KERNEL"
        }
        QuietText {
            width:parent.width
            visible:transits.inspectionNatal!=="" &&
                Transit.TARGETS.indexOf(transits.inspectionNatal)>=0
            height:visible?18:0
            color:Colors.yellow
            font.pixelSize:9
            elide:Text.ElideRight
            text:"NATAL REFERENCE "+transits.inspectionNatal.toUpperCase()+
                " × TRANSIT "+transits.selectedTarget.toUpperCase()+
                " / VERIFIED MATRIX PAIR"
        }
        QuietText {
            width:parent.width
            visible:transits.selectedContactUtc!==""
            height:visible?18:0
            font.pixelSize:9
            color:Colors.magenta
            elide:Text.ElideRight
            text:(transits.selectedEventKind==="station"
                    ?"ESTIMATED STATION ":"EXACT CROSSING ")+
                transits.selectedContactUtc+
                " // CHART NEAREST UTC MINUTE"
        }
        QuietText {
            width:parent.width;height:16;font.pixelSize:8
            color:Colors.orange;elide:Text.ElideRight
            text:"ANGULAR TOLERANCES ONLY / NOT EXACT CONTACT TIMES OR FORECASTS"
        }
    }
}
