import QtQuick
import "../../components"
import "StationMagickPlanetaryHoursPolicy.js" as Hours

// M6d // Explicitly traditional, read-only 24-hour civil-clock reference.
// There is no personal reading, ritual recommendation or additional service.
Rectangle {
    id: hours
    color: Colors.black
    clip: true
    property var weatherService: null
    signal routeRequested(string path)
    property int selectedHour: -1
    readonly property var plan: Hours.build(
        hours.weatherService && hours.weatherService.forecastReady
            ? hours.weatherService.dailyForecast : [],
        hours.weatherService
            ? String(hours.weatherService.localObservationDateTime || "") : "")
    readonly property int observationHour: Hours.observedIndex(
        plan,hours.weatherService
             ? String(hours.weatherService.localObservationDateTime || "") : "")
    readonly property int focusIndex: plan.ready
        ? (selectedHour >= 0 && selectedHour < 24 ? selectedHour
           : observationHour >= 0 ? observationHour : 0)
        : -1
    readonly property var activeHour: focusIndex >= 0
        ? plan.hours[focusIndex] : null
    onPlanChanged: {
        hours.selectedHour=-1;
        dial.requestPaint();
    }
    onFocusIndexChanged: dial.requestPaint()
    onWidthChanged: dial.requestPaint()
    onHeightChanged: dial.requestPaint()

    function moveHour(delta) {
        if(!hours.plan.ready)return;
        hours.selectedHour=(hours.focusIndex+delta+24)%24;
    }
    function rulerInk(name) {
        if(name==="sun")return Colors.yellow;
        if(name==="moon")return Colors.cyan;
        if(name==="mars")return Colors.orange;
        if(name==="venus")return Colors.magenta;
        if(name==="mercury")return Colors.cyan;
        if(name==="jupiter")return Colors.blue;
        return Colors.white; // Saturn, no destructive red coloring
    }

    Column {
        anchors.fill: parent
        anchors.margins: 8
        spacing: 5

        Row {
            width: parent.width
            height: 24
            spacing: 7
            GohuText {
                width: Math.max(0,parent.width-145)
                height: parent.height
                verticalAlignment: Text.AlignVCenter
                font.pixelSize: 13
                color: Colors.magenta
                text: "PLANETARY HOURS // CHALDEAN"
                elide: Text.ElideRight
            }
            ActionButton {
                width: 138
                height: 23
                label: "OPEN SOLAR SOURCE"
                labelPixelSize: 9
                accentColor: Colors.yellow
                onClicked: hours.routeRequested("cosmos/sun/twilight")
            }
        }

        QuietText {
            width: parent.width
            height: 20
            font.pixelSize: 9
            color: hours.plan.ready ? Colors.cyan : Colors.orange
            elide: Text.ElideRight
            text: hours.plan.ready
                ? hours.plan.date+" // "+hours.plan.source
                : hours.plan.reason
        }

        Canvas {
            id: dial
            width: parent.width
            height: Math.max(135,Math.min(370,
                hours.height-175))
            onPaint: {
                const ctx=getContext("2d");
                ctx.clearRect(0,0,width,height);
                if(!hours.plan.ready)return;
                const g=Hours.wheelGeometry(width,height);
                if(!g)return;
                const twoPi=Math.PI*2;
                ctx.save();
                ctx.textAlign="center";
                ctx.textBaseline="middle";
                for(let i=0;i<24;i++){
                    const item=hours.plan.hours[i];
                    const begin=-Math.PI/2+twoPi*i/24+0.016;
                    const end=-Math.PI/2+twoPi*(i+1)/24-0.016;
                    const active=i===hours.focusIndex;
                    const ink=hours.rulerInk(item.ruler);
                    ctx.beginPath();
                    ctx.arc(g.cx,g.cy,g.radius,begin,end);
                    ctx.strokeStyle=String(ink);
                    ctx.globalAlpha=active?1:(item.phase==="day"?0.8:0.45);
                    ctx.lineWidth=active?22:15;
                    ctx.stroke();
                    if(active){
                        ctx.beginPath();
                        ctx.arc(g.cx,g.cy,g.radius+16,begin,end);
                        ctx.strokeStyle=String(Colors.magenta);
                        ctx.globalAlpha=0.95;
                        ctx.lineWidth=2;
                        ctx.stroke();
                    }
                    if(i%3===0){
                        const angle=-Math.PI/2+twoPi*(i+0.5)/24;
                        const rad=g.radius+25;
                        ctx.globalAlpha=0.9;
                        ctx.fillStyle=String(Colors.white);
                        ctx.font="9px monospace";
                        ctx.fillText(String(i+1),
                            g.cx+rad*Math.cos(angle),
                            g.cy+rad*Math.sin(angle));
                    }
                }
                ctx.globalAlpha=0.7;
                ctx.strokeStyle=String(Colors.blue);
                ctx.lineWidth=1;
                ctx.beginPath();
                ctx.arc(g.cx,g.cy,g.radius-28,0,twoPi);
                ctx.stroke();
                ctx.globalAlpha=1;
                ctx.fillStyle=String(Colors.yellow);
                ctx.font="bold 12px monospace";
                ctx.fillText(hours.activeHour.ruler.toUpperCase(),
                    g.cx,g.cy-14,Math.max(20,g.radius));
                ctx.font="9px monospace";
                ctx.fillStyle=String(Colors.cyan);
                ctx.fillText((hours.focusIndex+1)+"/24 // "+
                    hours.activeHour.phase.toUpperCase(),
                    g.cx,g.cy+4,Math.max(20,g.radius*1.5));
                ctx.fillStyle=String(Colors.white);
                ctx.fillText(hours.activeHour.startLabel,
                    g.cx,g.cy+19,Math.max(20,g.radius*1.7));
                ctx.restore();
            }
            MouseArea {
                anchors.fill: parent
                hoverEnabled: true
                acceptedButtons: Qt.LeftButton
                cursorShape: Qt.PointingHandCursor
                onClicked: function(mouse) {
                    const g=Hours.wheelGeometry(dial.width,dial.height);
                    const index=Hours.pick(hours.plan,g,mouse.x,mouse.y);
                    if(index>=0)hours.selectedHour=index;
                }
                onWheel: function(wheel) {
                    if(!hours.plan.ready)return;
                    hours.moveHour(wheel.angleDelta.y>0?1:-1);
                    wheel.accepted=true;
                }
            }
        }

        Row {
            width: parent.width
            height: 25
            spacing: 5
            ActionButton {
                width: 78
                height: 24
                label: "◀ HOUR"
                accentColor: Colors.cyan
                labelPixelSize: 9
                available: hours.plan.ready
                onClicked: hours.moveHour(-1)
            }
            QuietText {
                width: Math.max(15,parent.width-78-78-12)
                height: parent.height
                verticalAlignment: Text.AlignVCenter
                horizontalAlignment: Text.AlignHCenter
                elide: Text.ElideRight
                color: Colors.yellow
                font.pixelSize: 10
                text: hours.activeHour ?
                    hours.activeHour.ruler.toUpperCase()+" // "+
                    hours.activeHour.startLabel+" – "+
                    hours.activeHour.endLabel : "NO VERIFIED SOLAR HOURS"
            }
            ActionButton {
                width: 78
                height: 24
                label: "HOUR ▶"
                accentColor: Colors.cyan
                labelPixelSize: 9
                available: hours.plan.ready
                onClicked: hours.moveHour(1)
            }
        }

        QuietText {
            width: parent.width
            height: 18
            color: Colors.white
            font.pixelSize: 9
            elide: Text.ElideRight
            text: hours.plan.ready
                ? "RISE "+hours.plan.sunrise+" | SET "+
                  hours.plan.sunset+" | NEXT RISE "+hours.plan.nextSunrise
                : "SOURCE REQUIRES TODAY AND TOMORROW SOLAR EVENTS"
        }
        QuietText {
            width: parent.width
            height: 18
            color: Colors.orange
            font.pixelSize: 9
            elide: Text.ElideRight
            text: "TRADITIONAL RULERS // CULTURAL CONVENTION, NOT ASTRONOMICAL CAUSATION"
        }
        QuietText {
            width: parent.width
            height: 17
            color: Colors.yellow
            font.pixelSize: 9
            elide: Text.ElideRight
            text: "PROVIDER-LOCAL CLOCK // DST TRANSITION DURATION UNVERIFIED"
        }
    }
}
