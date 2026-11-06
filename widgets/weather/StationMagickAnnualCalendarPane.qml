import QtQuick
import "../../components"
import "../../services/weather" as WeatherServices
import "StationMagickAnnualAtlasPolicy.js" as Atlas
import "StationMagickWheelViewportPolicy.js" as Viewport

// M7b // Interactive radial representations of explicit JPL year data.
// The year wheel compresses daily illumination into 365/366 tick marks;
// MONTH mode shows an individual Moon disc on every actual calendar day.
// The 24 solar terms occupy real dated positions, not 24 equal time slots.
Rectangle {
    id: annualPane
    color: Colors.black
    clip: true
    property var weatherService: null
    property real runtimeNowMs: 0
    property string view: "moon"
    property string scopeMode: "year"
    property int selectedYear: runtimeNowMs>0
        ? new Date(runtimeNowMs).getUTCFullYear():2026
    property string zoneId: "UTC" // Explicit basis until global IANA zone wiring.
    property int selectedMonth: 1
    property int selectedIndex: -1
    property string selectedSolar: ""
    // M7c // A true inspectable viewport. FIT is 1.0; the opening 1.6x
    // magnification makes the dense annual dial visible in the compact shell.
    property real wheelZoom: Viewport.DEFAULT_ZOOM
    property real panX: 0
    property real panY: 0
    property bool focusMode: false
    property bool zoneEditorOpen: false
    readonly property real fitRadius: Viewport.fitRadius(wheel.width,wheel.height)
    readonly property real minZoom: Viewport.MIN_ZOOM
    readonly property real maxZoom: Viewport.MAX_ZOOM

    function clampPan(){
        const p=Viewport.boundedPan(panX,panY,fitRadius,wheelZoom);
        panX=p.x;panY=p.y;
    }
    function panBy(dx,dy){
        if(!isFinite(dx)||!isFinite(dy))return;
        panX+=dx;panY+=dy;clampPan();
    }
    function zoomAt(factor,x,y){
        const next=Viewport.zoomAt(wheelZoom,panX,panY,factor,
                                   x,y,wheel.width,wheel.height,fitRadius);
        if(!next)return;
        wheelZoom=next.zoom;panX=next.panX;panY=next.panY;
    }
    function fitWheel(){wheelZoom=1;panX=0;panY=0;}
    function resetView(){wheelZoom=Viewport.DEFAULT_ZOOM;panX=0;panY=0;}
    readonly property var model: annualSource.atlas
    readonly property var focusedDay:
        Atlas.selectedDay(model,selectedIndex)
    readonly property var moonMonth: Atlas.monthRows(model,selectedMonth)
    readonly property var currentTerm:
        model.ready ? model.solar_terms.filter(function(x){
            return x.id===selectedSolar;
        })[0] || model.solar_terms[0] : null

    WeatherServices.CelestialAnnualCalendarService {
        id: annualSource
        active: annualPane.visible && annualPane.view!=="forecast"
        year: annualPane.selectedYear
        timezoneId: annualPane.zoneId
    }

    onModelChanged: wheel.requestPaint()
    onWheelZoomChanged: wheel.requestPaint()
    onPanXChanged: wheel.requestPaint()
    onPanYChanged: wheel.requestPaint()
    onFitRadiusChanged: clampPan()
    onSelectedMonthChanged: wheel.requestPaint()
    onSelectedIndexChanged: wheel.requestPaint()
    onSelectedSolarChanged: wheel.requestPaint()
    onScopeModeChanged: { panX=0;panY=0;wheel.requestPaint(); }
    onViewChanged: {
        annualPane.selectedIndex=-1;
        annualPane.selectedSolar="";
        annualPane.focusMode=false;
        annualPane.resetView();
        wheel.requestPaint();
    }

    Row {
        id: topModes
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: 26
        spacing: 4
        Repeater {
            model: [
                {id:"moon",label:"LUNAR YEAR"},
                {id:"solar",label:"SOLAR YEAR"},
                {id:"forecast",label:"FORECAST"}
            ]
            delegate: ActionButton {
                required property var modelData
                width: Math.max(20,(topModes.width-8)/3)
                height: 25
                label: modelData.label
                labelPixelSize: 9
                contentPadding: 1
                selected: annualPane.view===modelData.id
                accentColor: selected?Colors.magenta:Colors.cyan
                onClicked: annualPane.view=modelData.id
            }
        }
    }

    StationMagickForecastCalendarPane {
        anchors.top: topModes.bottom
        anchors.topMargin: 3
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        visible: annualPane.view==="forecast"
        weatherService: annualPane.weatherService
    }

    // Keep the actual Canvas full height. These compact controls float
    // above it and can be hidden in FOCUS, avoiding the old 100-pixel dial.
    Rectangle {
        id: controlBackground
        visible: controls.visible
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: topModes.bottom
        height: controls.height+statusLine.height+4
                +(zoneRow.visible?zoneRow.height+2:0)
        color: Colors.black
        opacity: 0.93
        z: 2
    }
    Row {
        id: controls
        visible: annualPane.view!=="forecast" && !annualPane.focusMode
        z: 3
        anchors.top: topModes.bottom
        anchors.topMargin: 3
        anchors.left: parent.left
        anchors.right: parent.right
        height: 24
        spacing: 3
        ActionButton {
            width: 31;height: 23;label: "◀ YR";labelPixelSize: 8
            accentColor: Colors.cyan
            available: annualPane.selectedYear>1901
            onClicked: annualPane.selectedYear--
        }
        QuietText {
            width: 38;height:23
            verticalAlignment: Text.AlignVCenter
            horizontalAlignment: Text.AlignHCenter
            font.pixelSize: 11;color: Colors.yellow
            text: String(annualPane.selectedYear)
        }
        ActionButton {
            width:31;height:23;label:"YR ▶";labelPixelSize:8
            accentColor:Colors.cyan
            available:annualPane.selectedYear<2099
            onClicked: annualPane.selectedYear++
        }
        ActionButton {
            width: 53;height:23
            label: annualPane.scopeMode==="year"?"MONTH":"YEAR"
            labelPixelSize: 8
            available: annualPane.view==="moon"
            accentColor:Colors.magenta
            onClicked: annualPane.scopeMode=
                annualPane.scopeMode==="year"?"month":"year"
        }
        ActionButton {
            width:Math.max(55,parent.width-31-38-31-53-43-5*spacing)
            height:23
            label: annualSource.loading?"LOADING":"CALCULATE YEAR"
            labelPixelSize:8
            accentColor:Colors.orange
            available: annualSource.configured&&!annualSource.loading
            onClicked: annualSource.calculate()
        }
        ActionButton {
            width:43;height:23;label:"ZONE"
            labelPixelSize:8
            accentColor: annualPane.zoneEditorOpen?Colors.magenta:Colors.cyan
            selected: annualPane.zoneEditorOpen
            onClicked: annualPane.zoneEditorOpen=!annualPane.zoneEditorOpen
        }
    }
    Row {
        id: zoneRow
        visible: controls.visible&&annualPane.zoneEditorOpen
        z: 3
        anchors.top: controls.bottom
        anchors.topMargin: 2
        anchors.left: parent.left
        anchors.right: parent.right
        height: visible?24:0
        spacing:4
        QuietText {
            width: 65;height:23
            text:"IANA ZONE"
            color:Colors.cyan
            verticalAlignment:Text.AlignVCenter
            font.pixelSize:9
        }
        Rectangle {
            width:Math.max(90,parent.width-65-58-8)
            height:23
            color:Colors.dark
            border.width:1;border.color:Colors.blue
            TextInput {
                id:zoneInput
                anchors.fill:parent
                anchors.margins:3
                text:annualPane.zoneId
                color:Colors.white
                font.family:"monospace"
                font.pixelSize:10
                selectByMouse:true
                maximumLength:64
                onEditingFinished: {
                    annualPane.zoneId=text.trim();
                    focus=false;
                }
            }
        }
        ActionButton {
            width:58;height:23
            label:"SET ZONE";labelPixelSize:8
            accentColor:Colors.yellow
            onClicked: {
                annualPane.zoneId=zoneInput.text.trim();
                zoneInput.focus=false;
                annualPane.zoneEditorOpen=false;
            }
        }
    }
    QuietText {
        id: statusLine
        visible: controls.visible
        z: 3
        anchors.top: zoneRow.visible?zoneRow.bottom:controls.bottom
        anchors.topMargin:2
        anchors.left:parent.left
        anchors.right:parent.right
        height:visible?14:0
        font.pixelSize:9
        color:annualSource.ready?Colors.cyan:Colors.orange
        elide:Text.ElideRight
        text:annualSource.statusText+" // "+annualPane.zoneId
    }

    // These remain visible in focus mode so zoom never becomes a trap.
    Rectangle {
        id: zoomBackground
        visible: zoomToolbar.visible
        anchors.centerIn: zoomToolbar
        width: zoomToolbar.width+6
        height: zoomToolbar.height+3
        color: Colors.black
        opacity:0.92
        z:3
    }
    Row {
        id: zoomToolbar
        visible:annualPane.view!=="forecast"
        z:4
        height:25
        spacing:3
        anchors.horizontalCenter:parent.horizontalCenter
        anchors.bottom: detailRack.visible?detailRack.top:parent.bottom
        anchors.bottomMargin: detailRack.visible?2:5
        ActionButton {
            width:35;height:24;label:"−"
            labelPixelSize:13
            accentColor:Colors.cyan
            available:annualPane.wheelZoom>annualPane.minZoom
            onClicked: annualPane.zoomAt(1/1.25,wheel.width/2,wheel.height/2)
        }
        QuietText {
            width:50;height:24
            text:Math.round(annualPane.wheelZoom*100)+"%"
            color:Colors.yellow;font.pixelSize:11
            verticalAlignment:Text.AlignVCenter
            horizontalAlignment:Text.AlignHCenter
        }
        ActionButton {
            width:35;height:24;label:"+"
            labelPixelSize:13
            accentColor:Colors.cyan
            available:annualPane.wheelZoom<annualPane.maxZoom
            onClicked: annualPane.zoomAt(1.25,wheel.width/2,wheel.height/2)
        }
        ActionButton {
            width:44;height:24;label:"FIT"
            labelPixelSize:9
            accentColor:Colors.orange
            onClicked:annualPane.fitWheel()
        }
        ActionButton {
            width:48;height:24;label:"RESET"
            labelPixelSize:9
            accentColor:Colors.orange
            onClicked:annualPane.resetView()
        }
        ActionButton {
            width:52;height:24
            label:annualPane.focusMode?"BACK":"FOCUS"
            labelPixelSize:9
            accentColor:annualPane.focusMode?Colors.magenta:Colors.cyan
            selected: annualPane.focusMode
            onClicked: annualPane.focusMode=!annualPane.focusMode
        }
    }

    // Main datum wheel, intentionally no whole-page Flickable.
    Canvas {
        id: wheel
        visible: annualPane.view!=="forecast"
        anchors.top: topModes.bottom
        anchors.topMargin: 1
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 0
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onPaint: {
            const ctx=getContext("2d");
            ctx.clearRect(0,0,width,height);
            const cx=0,cy=0,r=annualPane.fitRadius;
            const data=annualPane.model,valid=data.ready;
            const isMoon=annualPane.view==="moon";
            const monthMode=isMoon&&annualPane.scopeMode==="month";
            ctx.save();
            ctx.translate(width/2+annualPane.panX,height/2+annualPane.panY);
            ctx.scale(annualPane.wheelZoom,annualPane.wheelZoom);
            ctx.lineWidth=1;
            ctx.textAlign="center";
            ctx.textBaseline="middle";
            // The concentric rings are geometry, not invented ephemerides.
            [0.28,0.55,0.73,0.94].forEach(function(f,i){
                ctx.beginPath();
                ctx.strokeStyle=String(i===3?Colors.magenta:Colors.blue);
                ctx.globalAlpha=i===3?0.9:0.6;
                ctx.arc(cx,cy,r*f,0,2*Math.PI);
                ctx.stroke();
            });
            ctx.globalAlpha=1;
            if(!valid) {
                ctx.fillStyle=String(Colors.orange);
                ctx.font="10px monospace";
                ctx.fillText("LOAD LOCAL JPL YEAR",cx,cy);
                ctx.restore();return;
            }
            const days=data.days,total=days.length;
            function polar(angle,rad){
                return {x:cx+rad*Math.cos(angle),y:cy+rad*Math.sin(angle)};
            }
            function disc(x,y,radius,illum,angle,selected){
                const k=Math.min(1,Math.max(0,illum/100));
                ctx.fillStyle=String(Colors.dark);
                ctx.beginPath();ctx.arc(x,y,radius,0,Math.PI*2);ctx.fill();
                ctx.fillStyle=String(selected?Colors.magenta:Colors.yellow);
                for(let yy=-radius;yy<=radius;yy+=1) {
                    const edge=Math.sqrt(Math.max(0,radius*radius-yy*yy));
                    const waxing=angle<180;
                    const from=waxing?(1-2*k)*edge:-edge;
                    const to=waxing?edge:(2*k-1)*edge;
                    if(to>from)ctx.fillRect(x+from,y+yy,to-from,1.35);
                }
                ctx.strokeStyle=String(selected?Colors.magenta:Colors.cyan);
                ctx.lineWidth=selected?2:0.7;
                ctx.beginPath();ctx.arc(x,y,radius,0,Math.PI*2);ctx.stroke();
            }
            if(monthMode) {
                const rows=annualPane.moonMonth;
                const count=rows.length;
                for(let i=0;i<count;i++){
                    const angle=Atlas.angleFor(i,count);
                    const p=polar(angle,r*0.70);
                    const d=rows[i];
                    disc(p.x,p.y,Math.min(8,Math.max(3,r*0.047)),
                         d.illumination,d.phase_angle_deg,
                         d.day_index===annualPane.selectedIndex);
                    const txt=polar(angle,r*0.87);
                    ctx.font="8px monospace";ctx.fillStyle=String(Colors.white);
                    ctx.fillText(d.date.slice(8),txt.x,txt.y);
                }
            } else {
                // Year ring uses one real lunar measurement per local day.
                // Individual discs would overlap at ~4px/day; MONTH shows them.
                if(isMoon){
                    for(let i=0;i<total;i++){
                        const day=days[i],a=Atlas.angleFor(i,total);
                        const inner=polar(a,r*0.59),outer=polar(a,r*0.68);
                        ctx.strokeStyle=String(
                            i===annualPane.selectedIndex?Colors.magenta:
                            day.illumination>=50?Colors.yellow:Colors.blue);
                        ctx.globalAlpha=0.30+0.70*day.illumination/100;
                        ctx.lineWidth=i===annualPane.selectedIndex?2:1;
                        ctx.beginPath();ctx.moveTo(inner.x,inner.y);
                        ctx.lineTo(outer.x,outer.y);ctx.stroke();
                    }
                    ctx.globalAlpha=1;
                    for(let i=0;i<data.lunar_events.length;i++){
                        const event=data.lunar_events[i];
                        const index=Atlas.dayIndex(data,event.date);
                        if(index<0)continue;
                        const d=days[index],p=polar(Atlas.angleFor(index,total),r*0.76);
                        disc(p.x,p.y,Math.max(2,Math.min(5,r*.025)),
                             d.illumination,d.phase_angle_deg,
                             index===annualPane.selectedIndex);
                    }
                } else {
                    data.solar_terms.forEach(function(term,i){
                        const index=Atlas.dayIndex(data,term.date);
                        const a=Atlas.angleFor(index,total),p=polar(a,r*0.71);
                        const chosen=annualPane.currentTerm &&
                            annualPane.currentTerm.id===term.id;
                        ctx.fillStyle=String(chosen?Colors.magenta:
                                            term.major?Colors.yellow:Colors.cyan);
                        ctx.beginPath();ctx.arc(p.x,p.y,
                            term.major?5:3,0,Math.PI*2);ctx.fill();
                        const n=polar(a,r*0.83);
                        ctx.font="8px monospace";
                        ctx.fillText(String(i+1),n.x,n.y);
                    });
                }
                for(let m=1;m<=12;m++){
                    const start=Atlas.monthIndex(data,m),
                          next=m===12?total:Atlas.monthIndex(data,m+1);
                    const a=Atlas.angleFor((start+next)/2,total),p=polar(a,r*0.91);
                    ctx.fillStyle=String(Colors.white);
                    ctx.font="9px monospace";
                    ctx.fillText(Atlas.MONTHS[m-1],p.x,p.y);
                    const b=Atlas.angleFor(start,total),from=polar(b,r*0.85),
                          to=polar(b,r*0.97);
                    ctx.strokeStyle=String(Colors.magenta);ctx.lineWidth=1;
                    ctx.beginPath();ctx.moveTo(from.x,from.y);
                    ctx.lineTo(to.x,to.y);ctx.stroke();
                }
            }
            ctx.fillStyle=String(isMoon?Colors.cyan:Colors.yellow);
            ctx.font="bold 15px monospace";
            ctx.fillText(isMoon?"MOON":"SUN",cx,cy-12);
            ctx.font="9px monospace";
            ctx.fillText(monthMode?Atlas.MONTHS[annualPane.selectedMonth-1]:
                         String(annualPane.selectedYear),cx,cy+4);
            ctx.fillStyle=String(Colors.white);
            ctx.font="8px monospace";
            ctx.fillText(monthMode?"DAILY PHASE":isMoon?"DAILY TICKS":"24 TERMS",
                         cx,cy+19);
            ctx.restore();
        }
        MouseArea {
            id: wheelMouse
            anchors.fill: parent
            acceptedButtons: Qt.LeftButton
            hoverEnabled: true
            cursorShape: wheelMouse.pressed?Qt.ClosedHandCursor:Qt.OpenHandCursor
            property real pressX: 0
            property real pressY: 0
            property real lastX: 0
            property real lastY: 0
            property bool dragged: false
            onPressed: function(mouse) {
                pressX=lastX=mouse.x;
                pressY=lastY=mouse.y;
                dragged=false;
            }
            onPositionChanged: function(mouse) {
                if(!wheelMouse.pressed)return;
                if(Math.hypot(mouse.x-pressX,mouse.y-pressY)>5)
                    dragged=true;
                if(dragged)annualPane.panBy(mouse.x-lastX,mouse.y-lastY);
                lastX=mouse.x;lastY=mouse.y;
            }
            onWheel: function(wheelEvent) {
                if(wheelEvent.angleDelta.y!==0) {
                    annualPane.zoomAt(wheelEvent.angleDelta.y>0?1.2:1/1.2,
                                      wheelEvent.x,wheelEvent.y);
                    wheelEvent.accepted=true;
                }
            }
            onDoubleClicked: annualPane.fitWheel()
            onClicked: function(mouse) {
                if(dragged)return;
                const model=annualPane.model;
                if(!model.ready)return;
                // Inverse of painter translate + scale for correct wheel hits
                // after zoom/pan. The angle always maps to true dated entries.
                const pos=Viewport.inversePoint(mouse.x,mouse.y,
                    wheel.width,wheel.height,annualPane.panX,
                    annualPane.panY,annualPane.wheelZoom);
                if(!pos)return;
                const dx=pos.x,dy=pos.y;
                const r=annualPane.fitRadius;
                const dist=Math.hypot(dx,dy);
                if(dist>r||dist<r*0.24)return;
                if(annualPane.view==="moon"&&annualPane.scopeMode==="month"){
                    const rows=annualPane.moonMonth;
                    const i=Atlas.indexAtAngle(dx,dy,0,0,rows.length);
                    if(i>=0)annualPane.selectedIndex=rows[i].day_index;
                } else {
                    const i=Atlas.indexAtAngle(dx,dy,0,0,model.days.length);
                    if(i<0)return;
                    if(annualPane.view==="moon"){
                        annualPane.selectedIndex=i;
                        if(dist>r*0.82){
                            annualPane.selectedMonth=model.days[i].month;
                            annualPane.scopeMode="month";
                        }
                    } else {
                        let nearest=null,difference=9999;
                        model.solar_terms.forEach(function(t){
                            const day=Atlas.dayIndex(model,t.date);
                            const delta=Math.min(Math.abs(day-i),
                                                 model.days.length-Math.abs(day-i));
                            if(delta<difference){difference=delta;nearest=t;}
                        });
                        if(nearest)annualPane.selectedSolar=nearest.id;
                    }
                }
            }
        }
    }

    Column {
        id: detailRack
        visible: annualPane.view!=="forecast" && !annualPane.focusMode
        z: 3
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: visible?implicitHeight:0
        spacing: 2
        Row {
            visible: annualPane.view==="moon"&&annualPane.scopeMode==="month"
            width: parent.width
            height: visible?23:0
            spacing: 3
            ActionButton {
                width: 45;height: 22;label: "◀ MON";labelPixelSize: 8
                accentColor: Colors.cyan
                onClicked: annualPane.selectedMonth=
                    annualPane.selectedMonth===1?12:annualPane.selectedMonth-1
            }
            QuietText {
                width: Math.max(15,parent.width-93);height:22
                text: Atlas.MONTHS[annualPane.selectedMonth-1]+" / "+
                      annualPane.selectedYear
                font.pixelSize: 10
                color: Colors.yellow
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
            ActionButton {
                width: 45;height:22;label:"MON ▶";labelPixelSize:8
                accentColor: Colors.cyan
                onClicked: annualPane.selectedMonth=
                    annualPane.selectedMonth===12?1:annualPane.selectedMonth+1
            }
        }
        QuietText {
            width: parent.width; height: 20;font.pixelSize: 9
            color: Colors.yellow;elide: Text.ElideRight
            text: annualPane.view==="solar"
                ? (annualPane.currentTerm
                   ? annualPane.currentTerm.id.toUpperCase().replace(/-/g," ")+
                     " / "+annualPane.currentTerm.date
                   : "SELECT A SOLAR TERM")
                : (annualPane.focusedDay
                   ? annualPane.focusedDay.date+" / "+
                     annualPane.focusedDay.phase_id.toUpperCase().replace(/-/g," ")+
                     " / "+annualPane.focusedDay.illumination+"% LIT"
                   : "SELECT A DAY OR OPEN A MONTH")
        }
        QuietText {
            width: parent.width; height: 19;font.pixelSize: 9
            color: Colors.cyan;elide: Text.ElideRight
            text: annualPane.view==="solar"
                ? (annualPane.currentTerm
                   ? annualPane.currentTerm.longitude_deg+"° ECLIPTIC / "+
                     annualPane.currentTerm.time_utc
                   : "15° SOLAR-LONGITUDE DIVISIONS")
                : (annualPane.focusedDay
                   ? Atlas.eventsOnDay(annualPane.model,
                                      annualPane.focusedDay.date)
                       .map(function(x){return x.id.toUpperCase()+" "+x.time_utc;})
                       .join(" / ")||"NO EXACT EVENT THIS DAY"
                   : "PRINCIPAL PHASES MARKED ON YEAR RING")
        }
        QuietText {
            width: parent.width;height: 16;font.pixelSize: 8
            color: Colors.orange;elide: Text.ElideRight
            text: "JPL / LOCAL NOON DAILY PHASES / UTC EVENT INSTANTS"
        }
    }
}
