import QtQuick
import "../../components"
import "StationCosmosPlanetDayWheelPolicy.js" as Day
import "StationCosmosPlanetEventPolicy.js" as PlanetPolicy

// V3d // Real dated USNO events arranged around a 24-hour civil clock.
// Angle = local time of that discrete event. Ring radius = planet identity.
// This does NOT draw actual planetary orbits, positions, azimuth or aspects.
Rectangle {
    id: dayWheel
    height: 414
    color: Colors.black
    border.width: 1
    border.color: Colors.cyan
    clip: true

    property var datedRows: []
    property string civilDate: ""
    property bool sourceReady: false
    property string sourceError: ""
    property string selectedPlanet: "ALL"
    property string selectedKind: "ALL"
    property var hoveredEvent: null
    property var lockedEvent: null
    signal planetPicked(string planet)
    signal kindPicked(string kind)
    signal returnToTimeline()
    signal showHorizon()

    readonly property var events: sourceReady
        ? Day.datedEvents(
              PlanetPolicy.orderedEvents(
                  datedRows,selectedPlanet,selectedKind),civilDate)
        : []
    readonly property var focusEvent: lockedEvent || hoveredEvent

    onEventsChanged: {
        hoveredEvent=null;
        lockedEvent=null;
        wheelCanvas.requestPaint();
    }
    onFocusEventChanged: wheelCanvas.requestPaint()
    onWidthChanged: wheelCanvas.requestPaint()
    onHeightChanged: wheelCanvas.requestPaint()

    function kindInk(kind) {
        if(kind==="rise")return String(Colors.cyan);
        if(kind==="transit")return String(Colors.magenta);
        return String(Colors.orange);
    }

    function paintWheel(ctx) {
        const width=wheelCanvas.width,height=wheelCanvas.height;
        ctx.clearRect(0,0,width,height);
        const g=Day.geometry(width,height);
        if(!g.ready)return;
        ctx.save();
        ctx.textAlign="center";
        ctx.textBaseline="middle";
        ctx.font="10px monospace";

        // Five visually distinct categorical lanes, inner Mercury to outer
        // Saturn. Radius never means distance, altitude or orbital size.
        for(let i=0;i<Day.PLANETS.length;i++) {
            const planet=Day.PLANETS[i];
            const radius=Day.ringRadius(planet,width,height);
            const focused=dayWheel.selectedPlanet===planet
                || dayWheel.focusEvent
                   && dayWheel.focusEvent.planet===planet;
            ctx.beginPath();
            ctx.arc(g.x,g.y,radius,0,2*Math.PI);
            ctx.strokeStyle=String(focused?Colors.magenta:Colors.cyan);
            ctx.lineWidth=focused?1.6:1;
            ctx.globalAlpha=focused?0.9:0.32;
            ctx.shadowColor=String(Colors.magenta);
            ctx.shadowBlur=focused?6:0;
            ctx.stroke();
            ctx.shadowBlur=0;
        }

        // Local 00 / 06 / 12 / 18 are time-of-day directions, NOT
        // compass headings. 00 at top, increasing clockwise.
        for(let hour=0;hour<24;hour+=3) {
            const angle=hour*Math.PI/12;
            const major=hour%6===0;
            ctx.beginPath();
            ctx.moveTo(g.x+Math.sin(angle)*g.radius,
                       g.y-Math.cos(angle)*g.radius);
            ctx.lineTo(g.x+Math.sin(angle)*(g.radius+6),
                       g.y-Math.cos(angle)*(g.radius+6));
            ctx.globalAlpha=major?0.9:0.48;
            ctx.strokeStyle=String(major?Colors.yellow:Colors.blue);
            ctx.lineWidth=major?2:1;
            ctx.stroke();
            if(major) {
                ctx.fillStyle=String(Colors.yellow);
                ctx.globalAlpha=1;
                ctx.font="9px monospace";
                ctx.fillText(Day.timeLabel(hour*60).slice(0,2),
                    g.x+Math.sin(angle)*(g.radius+14),
                    g.y-Math.cos(angle)*(g.radius+14));
            }
        }

        ctx.globalAlpha=0.6;
        ctx.fillStyle=String(Colors.magenta);
        ctx.beginPath();
        ctx.arc(g.x,g.y,3,0,2*Math.PI);
        ctx.fill();
        ctx.fillStyle=String(Colors.cyan);
        ctx.globalAlpha=0.9;
        ctx.font="bold 9px monospace";
        ctx.fillText("24H",g.x,g.y+16);

        for(let i=0;i<dayWheel.events.length;i++) {
            const event=dayWheel.events[i];
            const point=Day.point(event,width,height);
            if(!point)continue;
            const selected=dayWheel.focusEvent
                && dayWheel.focusEvent.id===event.id;
            const color=dayWheel.kindInk(event.kind);
            if(selected) {
                ctx.strokeStyle=String(Colors.yellow);
                ctx.lineWidth=1.4;
                ctx.globalAlpha=0.72;
                ctx.beginPath();
                ctx.moveTo(g.x,g.y);
                ctx.lineTo(point.x,point.y);
                ctx.stroke();
            }
            ctx.globalAlpha=1;
            ctx.fillStyle=color;
            ctx.shadowColor=color;
            ctx.shadowBlur=selected?12:4;
            ctx.beginPath();
            ctx.arc(point.x,point.y,selected?7:5,0,2*Math.PI);
            ctx.fill();
            ctx.shadowBlur=0;
            ctx.fillStyle=String(Colors.black);
            ctx.font="bold 9px monospace";
            ctx.fillText(event.kind==="rise"?"R":
                         event.kind==="transit"?"T":"S",
                         point.x,point.y+0.5);
            if(selected) {
                ctx.beginPath();
                ctx.arc(point.x,point.y,10,0,2*Math.PI);
                ctx.strokeStyle=String(Colors.yellow);
                ctx.lineWidth=1.2;
                ctx.stroke();
            }
        }
        if(dayWheel.events.length===0) {
            ctx.fillStyle=String(Colors.orange);
            ctx.font="9px monospace";
            ctx.globalAlpha=1;
            ctx.fillText("NO DATED EVENTS",g.x,g.y-4);
        }
        ctx.restore();
    }

    Column {
        anchors.fill: parent
        anchors.margins: 8
        spacing: 4

        Row {
            width: parent.width
            height: 23
            spacing: 5
            GohuText {
                width: Math.max(0,parent.width-177)
                height: 22
                font.pixelSize: 12
                text: "✦ PLANET EVENT WHEEL // LOCAL 24H"
                color: Colors.magenta
                elide: Text.ElideRight
            }
            ActionButton {
                width: 80
                height: 22
                contentPadding: 0
                labelPixelSize: 9
                label: "TIMELINE"
                accentColor: Colors.cyan
                onClicked: dayWheel.returnToTimeline()
            }
            ActionButton {
                width: 87
                height: 22
                contentPadding: 0
                labelPixelSize: 9
                label: "HORIZON"
                accentColor: Colors.magenta
                onClicked: dayWheel.showHorizon()
            }
        }

        QuietText {
            width: parent.width
            height: 15
            color: Colors.cyan
            font.pixelSize: 9
            elide: Text.ElideRight
            text: (dayWheel.sourceReady?"USNO MRST // ":"SOURCE UNAVAILABLE // ")
                + (dayWheel.civilDate||"NO DATE")
                + " // " + dayWheel.events.length
                + " DATED EVENTS // ANGLE IS TIME, RADIUS IS PLANET"
        }

        Row {
            id: planetFilters
            width: parent.width
            height: 26
            spacing: 4
            ActionButton {
                width: Math.max(1,(planetFilters.width-5*planetFilters.spacing)/6)
                height: 25
                contentPadding: 0
                labelPixelSize: 9
                label: "ALL"
                selected: dayWheel.selectedPlanet==="ALL"
                accentColor: Colors.magenta
                onClicked: dayWheel.planetPicked("ALL")
            }
            Repeater {
                model: PlanetPolicy.PLANETS
                delegate: ActionButton {
                    required property var modelData
                    width: Math.max(1,(planetFilters.width-5*planetFilters.spacing)/6)
                    height: 25
                    contentPadding: 0
                    labelPixelSize: 9
                    label: PlanetPolicy.planetLabel(modelData)
                    selected: dayWheel.selectedPlanet===modelData
                    accentColor: Colors.cyan
                    onClicked: dayWheel.planetPicked(modelData)
                }
            }
        }

        Row {
            id: kindFilters
            width: parent.width
            height: 25
            spacing: 5
            Repeater {
                model: [
                    {id:"ALL",label:"ALL EVENTS"},
                    {id:"rise",label:"R // RISE"},
                    {id:"transit",label:"T // TRANSIT"},
                    {id:"set",label:"S // SET"}
                ]
                delegate: ActionButton {
                    required property var modelData
                    width: Math.max(1,(kindFilters.width-3*kindFilters.spacing)/4)
                    height: 24
                    contentPadding: 0
                    labelPixelSize: 9
                    label: modelData.label
                    selected: dayWheel.selectedKind===modelData.id
                    accentColor: modelData.id==="rise"?Colors.cyan
                          : modelData.id==="transit"?Colors.magenta
                          : modelData.id==="set"?Colors.orange:Colors.yellow
                    onClicked: dayWheel.kindPicked(modelData.id)
                }
            }
        }

        Row {
            id: ringRow
            width: parent.width
            height: 205
            spacing: 8
            Item {
                id: wheelBay
                width: Math.min(230,Math.max(205,ringRow.width*0.48))
                height: ringRow.height

                Canvas {
                    id: wheelCanvas
                    anchors.fill: parent
                    antialiasing: true
                    renderTarget: Canvas.Image
                    onPaint: dayWheel.paintWheel(getContext("2d"))
                }
                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    acceptedButtons: Qt.LeftButton
                    preventStealing: true
                    cursorShape: Qt.CrossCursor
                    onPositionChanged: function(mouse) {
                        dayWheel.hoveredEvent=Day.pick(
                            dayWheel.events,mouse.x,mouse.y,width,height,8);
                    }
                    onExited: dayWheel.hoveredEvent=null
                    onClicked: function(mouse) {
                        const chosen=Day.pick(
                            dayWheel.events,mouse.x,mouse.y,width,height,8);
                        if(chosen) {
                            dayWheel.lockedEvent=chosen;
                        } else {
                            const planet=Day.pickRing(
                                mouse.x,mouse.y,width,height,5);
                            if(planet!=="")dayWheel.planetPicked(
                                dayWheel.selectedPlanet===planet?"ALL":planet);
                        }
                    }
                }
            }
            Column {
                width: Math.max(0,ringRow.width-wheelBay.width-ringRow.spacing)
                height: parent.height
                spacing: 8
                GohuText {
                    width: parent.width
                    text: "EVENT INSPECTOR"
                    color: Colors.magenta
                    font.pixelSize: 12
                    elide: Text.ElideRight
                }
                GohuText {
                    width: parent.width
                    text: dayWheel.focusEvent
                        ? dayWheel.focusEvent.planet
                        : "SELECT AN EVENT"
                    font.pixelSize: 13
                    color: Colors.yellow
                    elide: Text.ElideRight
                }
                QuietText {
                    width: parent.width
                    font.pixelSize: 10
                    color: Colors.cyan
                    wrapMode: Text.WordWrap
                    text: dayWheel.focusEvent
                        ? PlanetPolicy.eventDetail(dayWheel.focusEvent)
                        : "CLICK R / T / S ON A PLANET RING."
                }
                QuietText {
                    width: parent.width
                    font.pixelSize: 10
                    color: Colors.yellow
                    elide: Text.ElideRight
                    text: "EVENT " + Day.ordinal(dayWheel.events,dayWheel.focusEvent)
                }
                QuietText {
                    width: parent.width
                    font.pixelSize: 9
                    color: Colors.orange
                    wrapMode: Text.WordWrap
                    text: "CLICK A RING TO FILTER // MER / VEN / MAR / JUP / SAT"
                }
                QuietText {
                    width: parent.width
                    font.pixelSize: 9
                    color: Colors.orange
                    wrapMode: Text.WordWrap
                    text: "00 TOP · 06 RIGHT · 12 BOTTOM · 18 LEFT"
                }
                QuietText {
                    width: parent.width
                    font.pixelSize: 9
                    color: Colors.cyan
                    wrapMode: Text.WordWrap
                    text: "R // RISE · T // TRANSIT · S // SET"
                }
            }
        }

        Row {
            id: controls
            width: parent.width
            height: 29
            spacing: 5
            ActionButton {
                width: Math.max(1,(controls.width-2*controls.spacing)/3)
                height: 28
                label: "◀ PREV EVENT"
                labelPixelSize: 10
                contentPadding: 1
                accentColor: Colors.cyan
                available: dayWheel.events.length>0
                onClicked: dayWheel.lockedEvent=PlanetPolicy.stepEvent(
                    dayWheel.events,dayWheel.focusEvent,-1)
            }
            ActionButton {
                width: Math.max(1,(controls.width-2*controls.spacing)/3)
                height: 28
                label: "NEXT EVENT ▶"
                labelPixelSize: 10
                contentPadding: 1
                accentColor: Colors.magenta
                available: dayWheel.events.length>0
                onClicked: dayWheel.lockedEvent=PlanetPolicy.stepEvent(
                    dayWheel.events,dayWheel.focusEvent,1)
            }
            ActionButton {
                width: Math.max(1,(controls.width-2*controls.spacing)/3)
                height: 28
                label: "UNLOCK"
                labelPixelSize: 10
                contentPadding: 1
                accentColor: Colors.orange
                available: dayWheel.lockedEvent!==null
                onClicked: dayWheel.lockedEvent=null
            }
        }

        QuietText {
            width: parent.width
            height: 19
            font.pixelSize: 9
            color: Colors.orange
            elide: Text.ElideRight
            text: dayWheel.sourceError!=="" ? dayWheel.sourceError
                : "LOCAL EVENT TIMES // NO PLANET TRACKS, SKY POSITIONS OR ASPECTS"
        }
    }
}
