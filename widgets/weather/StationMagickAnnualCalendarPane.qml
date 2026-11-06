import QtQuick
import "../../components"
import "../../services/weather" as WeatherServices
import "StationMagickAnnualAtlasPolicy.js" as Atlas

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
    onSelectedMonthChanged: wheel.requestPaint()
    onSelectedIndexChanged: wheel.requestPaint()
    onSelectedSolarChanged: wheel.requestPaint()
    onScopeModeChanged: wheel.requestPaint()
    onViewChanged: {
        annualPane.selectedIndex=-1;
        annualPane.selectedSolar="";
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

    Column {
        id: controls
        visible: annualPane.view!=="forecast"
        anchors.top: topModes.bottom
        anchors.topMargin: 4
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: 3

        Row {
            width: parent.width
            height: 26
            spacing: 3
            ActionButton {
                width: 39; height: 24
                label: "◀ YR"
                labelPixelSize: 8
                accentColor: Colors.cyan
                available: annualPane.selectedYear>1901
                onClicked: annualPane.selectedYear--
            }
            QuietText {
                width: 40; height: 24
                verticalAlignment: Text.AlignVCenter
                horizontalAlignment: Text.AlignHCenter
                font.pixelSize: 11
                color: Colors.yellow
                text: String(annualPane.selectedYear)
            }
            ActionButton {
                width: 39; height: 24
                label: "YR ▶"
                labelPixelSize: 8
                accentColor: Colors.cyan
                available: annualPane.selectedYear<2099
                onClicked: annualPane.selectedYear++
            }
            ActionButton {
                width: 53; height: 24
                label: "YEAR"
                labelPixelSize: 8
                selected: annualPane.scopeMode==="year"
                accentColor: selected?Colors.magenta:Colors.cyan
                onClicked: annualPane.scopeMode="year"
            }
            ActionButton {
                width: 58; height: 24
                label: "MONTH"
                labelPixelSize: 8
                available: annualPane.view==="moon"
                selected: annualPane.scopeMode==="month"
                accentColor: selected?Colors.magenta:Colors.cyan
                onClicked: annualPane.scopeMode="month"
            }
            ActionButton {
                width: Math.max(25,parent.width-39-40-39-53-58-5*spacing)
                height: 24
                label: annualSource.loading?"LOADING":"CALCULATE YEAR"
                labelPixelSize: 8
                accentColor: Colors.orange
                available: annualSource.configured && !annualSource.loading
                onClicked: annualSource.calculate()
            }
        }
        Row {
            width: parent.width
            height: 24
            spacing: 4
            QuietText {
                width: 75; height: 23
                text: "IANA ZONE"
                color: Colors.cyan
                verticalAlignment: Text.AlignVCenter
                font.pixelSize: 9
            }
            Rectangle {
                width: Math.max(80,parent.width-75-58-2*4)
                height: 23
                border.width: 1
                border.color: Colors.blue
                color: Colors.dark
                TextInput {
                    id: zoneInput
                    anchors.fill: parent
                    anchors.margins: 3
                    text: annualPane.zoneId
                    color: Colors.white
                    font.family: "monospace"
                    font.pixelSize: 10
                    selectByMouse: true
                    maximumLength: 64
                    onEditingFinished: {
                        annualPane.zoneId=text.trim();
                        focus=false;
                    }
                }
            }
            ActionButton {
                width: 58; height: 23
                label: "SET ZONE"
                labelPixelSize: 8
                accentColor: Colors.yellow
                onClicked: {annualPane.zoneId=zoneInput.text.trim();zoneInput.focus=false;}
            }
        }
        QuietText {
            width: parent.width
            height: 17
            font.pixelSize: 9
            color: annualSource.ready?Colors.cyan:Colors.orange
            text: annualSource.statusText+" // "+annualPane.zoneId
            elide: Text.ElideRight
        }
    }

    // Main datum wheel, intentionally no whole-page Flickable.
    Canvas {
        id: wheel
        visible: annualPane.view!=="forecast"
        anchors.top: controls.bottom
        anchors.topMargin: 2
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: detailRack.top
        anchors.bottomMargin: 2
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onPaint: {
            const ctx=getContext("2d");
            ctx.clearRect(0,0,width,height);
            const cx=width/2,cy=height/2,r=Math.max(5,Math.min(
                width-6,height-4)*0.48);
            const data=annualPane.model,valid=data.ready;
            const isMoon=annualPane.view==="moon";
            const monthMode=isMoon&&annualPane.scopeMode==="month";
            ctx.save();
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
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: function(mouse) {
                const model=annualPane.model;
                if(!model.ready)return;
                const cx=wheel.width/2,cy=wheel.height/2;
                const r=Math.max(5,Math.min(wheel.width-6,wheel.height-4)*0.48);
                const dist=Math.hypot(mouse.x-cx,mouse.y-cy);
                if(dist>r||dist<r*0.24)return;
                if(annualPane.view==="moon"&&annualPane.scopeMode==="month"){
                    const rows=annualPane.moonMonth;
                    const i=Atlas.indexAtAngle(mouse.x,mouse.y,cx,cy,rows.length);
                    if(i>=0)annualPane.selectedIndex=rows[i].day_index;
                } else {
                    const i=Atlas.indexAtAngle(mouse.x,mouse.y,cx,cy,
                                               model.days.length);
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
        visible: annualPane.view!=="forecast"
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
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
