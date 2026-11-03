import QtQuick
import "../../components"
import "StationMagickCelestialVisualPolicy.js" as Celestial

// M5 // Standalone, source-fed celestial instrument. No self-owned provider,
// ephemeris download, timer, location lookup, journal, or page navigation.
// The Station owner can mount this *after* an M4 JSON transport is approved.
Rectangle {
    id: instrument
    width: 640
    height: 470
    color: Colors.black
    border.width: 1
    border.color: Colors.magenta
    clip: true

    // M4 production JSON; a missing or unverified payload stays unavailable.
    property var visualData: null
    property string mode: "wheel"
    property string selectedBody: ""
    property int lockedIndex: -1
    property int hoveredIndex: -1
    property real zoom: 1.0
    property real panPosition: 0.5
    property int eventOrdinal: -1

    readonly property var eventsInView: Celestial.visibleEvents(graphModel,viewWindow)
    readonly property var chosenEvent: Celestial.eventAt(graphModel,viewWindow,eventOrdinal)

    function stepToEvent(direction) {
        const chosen=Celestial.stepEvent(graphModel,viewWindow,eventOrdinal,direction);
        if(!chosen)return false;
        instrument.eventOrdinal=chosen.ordinal;
        instrument.lockedIndex=chosen.sampleIndex;
        return true;
    }

    readonly property var graphModel: Celestial.model(visualData)
    readonly property var viewWindow: Celestial.windowFor(
        graphModel,zoom,panPosition)
    readonly property int focusIndex: Celestial.selectedIndex(
        graphModel,lockedIndex,hoveredIndex)
    readonly property var wheelPoints: Celestial.wheelPositions(
        graphModel,focusIndex)
    readonly property string focusBody: selectedBody !== "" &&
        graphModel.bodies.indexOf(selectedBody)>=0
        ? selectedBody : (graphModel.ready ? graphModel.bodies[0] : "")

    onVisualDataChanged: {
        instrument.lockedIndex=-1;
        instrument.hoveredIndex=-1;
        instrument.selectedBody="";
        instrument.zoom=1.0;
        instrument.panPosition=0.5;
        instrument.eventOrdinal=-1;
    }
    onGraphModelChanged: graphCanvas.requestPaint()
    onFocusIndexChanged: graphCanvas.requestPaint()
    onModeChanged: graphCanvas.requestPaint()
    onViewWindowChanged: {
        instrument.eventOrdinal=-1;
        graphCanvas.requestPaint();
    }
    onEventOrdinalChanged: graphCanvas.requestPaint()
    onSelectedBodyChanged: graphCanvas.requestPaint()
    onWidthChanged: graphCanvas.requestPaint()
    onHeightChanged: graphCanvas.requestPaint()

    function chartInk(i) {
        return [String(Colors.orange),String(Colors.cyan),
                String(Colors.magenta),String(Colors.yellow)][i%4];
    }
    function paintWheel(ctx) {
        const cx=graphCanvas.width/2,cy=graphCanvas.height/2;
        const radius=Math.max(30,Math.min(graphCanvas.width,
                                          graphCanvas.height)*0.36);
        ctx.save();
        ctx.strokeStyle=String(Colors.blue);
        ctx.globalAlpha=0.85;
        for (let ring=0;ring<3;ring++){
            ctx.beginPath();
            ctx.arc(cx,cy,radius*(1-ring*0.18),0,2*Math.PI);
            ctx.stroke();
        }
        ctx.font="10px monospace";
        for(let sign=0;sign<12;sign++){
            const theta=sign*Math.PI/6-Math.PI/2;
            ctx.strokeStyle=String(Colors.cyan);
            ctx.globalAlpha=0.35;
            ctx.beginPath();
            ctx.moveTo(cx,cy);
            ctx.lineTo(cx+radius*Math.cos(theta),
                       cy+radius*Math.sin(theta));
            ctx.stroke();
            ctx.fillStyle=String(Colors.white);
            ctx.globalAlpha=0.9;
            const label=Celestial.SIGNS[sign];
            ctx.fillText(label,cx+(radius+13)*Math.cos(theta)-6,
                              cy+(radius+13)*Math.sin(theta)+4);
        }
        ctx.globalAlpha=1;
        ctx.fillStyle=String(Colors.magenta);
        ctx.fillText("ECLIPTIC",cx-28,cy-7);
        ctx.fillStyle=String(Colors.cyan);
        ctx.fillText("0° / AR",cx-21,cy+11);
        const positions=instrument.wheelPoints;
        const byBody={};
        for(let p=0;p<positions.length;p++)
            byBody[positions[p].body]=positions[p];
        for(let j=0;j<instrument.graphModel.relationships.length;j++){
            const pair=instrument.graphModel.relationships[j];
            if(!pair.samples[instrument.focusIndex].aspects.length)continue;
            const left=byBody[pair.bodies[0]],right=byBody[pair.bodies[1]];
            if(!left||!right)continue;
            const ra=left.longitude_deg*Math.PI/180;
            const rb=right.longitude_deg*Math.PI/180;
            ctx.beginPath();
            ctx.moveTo(cx+radius*Math.sin(ra),cy-radius*Math.cos(ra));
            ctx.lineTo(cx+radius*Math.sin(rb),cy-radius*Math.cos(rb));
            ctx.strokeStyle=String(Colors.magenta);
            ctx.globalAlpha=0.72;
            ctx.lineWidth=1.5;ctx.stroke();
        }
        ctx.globalAlpha=1;
        for(let k=0;k<positions.length;k++){
            const point=positions[k];
            const angle=point.longitude_deg*Math.PI/180;
            const x=cx+radius*Math.sin(angle),y=cy-radius*Math.cos(angle);
            ctx.beginPath();
            ctx.arc(x,y,point.body===instrument.focusBody?6.5:4.5,
                    0,2*Math.PI);
            ctx.fillStyle=point.color;
            ctx.fill();
            ctx.strokeStyle=String(Colors.black);
            ctx.lineWidth=1;ctx.stroke();
            ctx.fillStyle=point.color;
            ctx.font="10px monospace";
            ctx.fillText(point.body.toUpperCase().slice(0,9),x+8,y+3);
        }
        ctx.restore();
    }
    function paintChart(ctx) {
        const width=graphCanvas.width,height=graphCanvas.height;
        const view=instrument.viewWindow;
        const range=Celestial.rangeFor(instrument.graphModel,view,
                                        instrument.mode);
        ctx.save();
        ctx.font="10px monospace";
        ctx.lineWidth=1;
        for(let i=0;i<=4;i++){
            const y=i*height/4;
            ctx.globalAlpha=0.3;
            ctx.strokeStyle=String(Colors.cyan);
            ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(width,y);ctx.stroke();
            ctx.globalAlpha=0.8;
            ctx.fillStyle=String(Colors.white);
            ctx.fillText((range.max-(range.max-range.min)*i/4)
                         .toFixed(1)+"°",2,Math.max(10,y-3));
        }
        ctx.globalAlpha=1;
        const series=instrument.mode==="aspects"
            ? instrument.graphModel.relationships
            : instrument.graphModel.series;
        for(let rowIndex=0;rowIndex<series.length;rowIndex++){
            const row=series[rowIndex];
            const points=instrument.mode==="aspects"?row.samples:row.rows;
            ctx.strokeStyle=instrument.chartInk(rowIndex);
            ctx.lineWidth=2;
            ctx.beginPath();
            for(let index=view.from;index<=view.to;index++){
                const value=instrument.mode==="aspects"
                    ? points[index].longitude_separation_deg
                    : points[index].unwrapped_longitude_deg;
                const x=Celestial.chartX(index,view,width);
                const y=Celestial.chartY(value,range,height);
                if(index===view.from)ctx.moveTo(x,y);
                else ctx.lineTo(x,y);
            }
            ctx.stroke();
        }
        const start=instrument.graphModel.times[view.from];
        const end=instrument.graphModel.times[view.to];
        if (instrument.graphModel.events.length>0){
            ctx.strokeStyle=String(Colors.yellow);
            ctx.globalAlpha=0.38;
            ctx.lineWidth=1;
            for(let e=0;e<instrument.graphModel.events.length;e++){
                const t=Date.parse(instrument.graphModel.events[e].time_utc);
                if(t<start||t>end)continue;
                const x=(t-start)/Math.max(1,end-start)*width;
                const event=instrument.graphModel.events[e];
                const selected=instrument.chosenEvent &&
                    event.time_utc===instrument.chosenEvent.time_utc &&
                    event.name===instrument.chosenEvent.name;
                ctx.strokeStyle=selected?String(Colors.magenta):String(Colors.yellow);
                ctx.globalAlpha=selected?1:0.38;
                ctx.lineWidth=selected?2:1;
                ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,height);
                ctx.stroke();
            }
        }
        const focusTime=instrument.graphModel.times[instrument.focusIndex];
        if(focusTime>=start && focusTime<=end){
            ctx.globalAlpha=0.95;
            ctx.strokeStyle=String(Colors.magenta);
            ctx.lineWidth=1;
            const focusX=(focusTime-start)/Math.max(1,end-start)*width;
            ctx.beginPath();ctx.moveTo(focusX,0);
            ctx.lineTo(focusX,height);ctx.stroke();
        }
        ctx.restore();
    }

    Column {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 7

        Row {
            width: parent.width
            height: 27
            spacing: 8
            GohuText {
                width: Math.max(0,parent.width-225)
                height: parent.height
                verticalAlignment: Text.AlignVCenter
                font.pixelSize: 13
                color: Colors.magenta
                text: "MAGICK // CELESTIAL INSTRUMENT"
                elide: Text.ElideRight
            }
            QuietText {
                width: 217
                height: parent.height
                verticalAlignment: Text.AlignVCenter
                horizontalAlignment: Text.AlignRight
                font.pixelSize: 9
                color: instrument.graphModel.ready
                       ? Colors.cyan:Colors.orange
                elide: Text.ElideRight
                text: instrument.graphModel.ready
                    ? instrument.graphModel.source+" // "
                      +instrument.graphModel.hash
                    : "NO CALCULATION SOURCE"
            }
        }

        Row {
            id: modeRow
            width: parent.width
            height: 27
            spacing: 5
            Repeater {
                model: [
                    {id:"wheel",label:"ZODIAC WHEEL"},
                    {id:"motion",label:"MOTION CURVE"},
                    {id:"aspects",label:"ASPECT GRAPH"}
                ]
                delegate: ActionButton {
                    required property var modelData
                    width: Math.max(1,(modeRow.width-10)/3)
                    height: 27
                    contentPadding: 3
                    label: modelData.label
                    labelPixelSize: 10
                    selected: instrument.mode === modelData.id
                    accentColor: selected ? Colors.magenta : Colors.cyan
                    onClicked: instrument.mode = modelData.id
                }
            }
        }

        Rectangle {
            id: chartFrame
            width: parent.width
            height: Math.max(155,instrument.height-225)
            color: Colors.dark
            border.width: 1
            border.color: Colors.cyan
            clip: true

            Canvas {
                id: graphCanvas
                anchors.fill: parent
                anchors.margins: 17
                onPaint: {
                    const ctx=getContext("2d");
                    ctx.clearRect(0,0,width,height);
                    if(!instrument.graphModel.ready)return;
                    if(instrument.mode==="wheel")instrument.paintWheel(ctx);
                    else instrument.paintChart(ctx);
                }
            }

            MouseArea {
                id: pointer
                anchors.fill: graphCanvas
                enabled: instrument.graphModel.ready
                hoverEnabled: true
                preventStealing: true
                acceptedButtons: Qt.LeftButton
                cursorShape: Qt.CrossCursor
                property real previousX: 0
                property real gestureOriginX: 0
                property bool panning: false

                onPressed: function(mouse) {
                    previousX=mouse.x;
                    gestureOriginX=mouse.x;
                    panning=false;
                }
                onPositionChanged: function(mouse) {
                    if (!instrument.graphModel.ready)return;
                    if (pressed) {
                        if (Math.abs(mouse.x-gestureOriginX)>5)panning=true;
                        if (panning && instrument.mode!=="wheel" &&
                            instrument.zoom>1) {
                            instrument.panPosition=Celestial.clamp(
                                instrument.panPosition
                                -(mouse.x-previousX)/Math.max(1,width),
                                0,1);
                        } else if (panning && instrument.mode==="wheel") {
                            instrument.eventOrdinal=-1;
                            instrument.lockedIndex=Celestial.indexAtFraction(
                                instrument.graphModel,instrument.viewWindow,
                                mouse.x/Math.max(1,width));
                        }
                        previousX=mouse.x;
                    } else if (instrument.lockedIndex<0) {
                        instrument.hoveredIndex=Celestial.indexAtFraction(
                            instrument.graphModel,instrument.viewWindow,
                            mouse.x/Math.max(1,width));
                    }
                }
                onClicked: function(mouse) {
                    if(panning || !instrument.graphModel.ready)return;
                    if(instrument.mode==="wheel"){
                        const radius=Math.max(30,Math.min(graphCanvas.width,
                                            graphCanvas.height)*0.36);
                        const nx=0.5+(mouse.x-graphCanvas.width/2)*0.36/radius;
                        const ny=0.5+(mouse.y-graphCanvas.height/2)*0.36/radius;
                        const body=Celestial.nearestWheelBody(
                            instrument.graphModel,instrument.focusIndex,nx,ny);
                        if(body===null)return;
                        instrument.selectedBody=body;
                        instrument.eventOrdinal=-1;
                        instrument.lockedIndex=instrument.focusIndex;
                    }else {
                        instrument.eventOrdinal=-1;
                        instrument.lockedIndex=Celestial.indexAtFraction(
                            instrument.graphModel,instrument.viewWindow,
                            mouse.x/Math.max(1,width));
                    }
                }
                onExited: {
                    if(instrument.lockedIndex<0)instrument.hoveredIndex=-1;
                }
                onWheel: function(wheel) {
                    if(!instrument.graphModel.ready)return;
                    instrument.zoom=Celestial.clamp(
                        instrument.zoom*(wheel.angleDelta.y>0?1.4:1/1.4),
                        1,8);
                    wheel.accepted=true;
                }
            }

            GohuText {
                anchors.centerIn: parent
                width: Math.max(0,parent.width-32)
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
                font.pixelSize: 12
                color: Colors.orange
                visible: !instrument.graphModel.ready
                text: instrument.graphModel.reason
            }

            QuietText {
                anchors.left: parent.left
                anchors.bottom: parent.bottom
                anchors.margins: 4
                font.pixelSize: 9
                color: Colors.cyan
                text: instrument.mode==="wheel"
                    ? "DRAG // TIME   |   CLICK // BODY   |   SCROLL // ZOOM TIME"
                    : "DRAG // PAN TIME   |   CLICK // LOCK   |   SCROLL // ZOOM"
                visible: instrument.graphModel.ready
            }
        }

        // Event times are backend-calculated; the wheel/curve is deliberately
        // locked to the nearest *sample*, not an invented interpolated point.
        Row {
            width: parent.width
            height: 24
            spacing: 5
            ActionButton {
                width: 79
                height: 24
                label: "◀ EVENT"
                labelPixelSize: 9
                contentPadding: 2
                accentColor: Colors.yellow
                available: instrument.graphModel.ready && instrument.eventsInView.length>0
                onClicked: instrument.stepToEvent(-1)
            }
            QuietText {
                width: Math.max(0,parent.width-158-10)
                height: 24
                font.pixelSize: 9
                verticalAlignment: Text.AlignVCenter
                horizontalAlignment: Text.AlignHCenter
                elide: Text.ElideRight
                color: Colors.white
                text: Celestial.eventLabel(instrument.graphModel,
                                          instrument.viewWindow,instrument.eventOrdinal)
            }
            ActionButton {
                width: 79
                height: 24
                label: "EVENT ▶"
                labelPixelSize: 9
                contentPadding: 2
                accentColor: Colors.yellow
                available: instrument.graphModel.ready && instrument.eventsInView.length>0
                onClicked: instrument.stepToEvent(1)
            }
        }

        Row {
            width: parent.width
            height: 30
            spacing: 5
            Repeater {
                model: [
                    {id:"back",label:"◀ TIME"},
                    {id:"next",label:"TIME ▶"},
                    {id:"unlock",label:"UNLOCK"},
                    {id:"reset",label:"RESET"}
                ]
                delegate: ActionButton {
                    required property var modelData
                    width: Math.max(1,(parent.width-15)/4)
                    height: 29
                    label: modelData.label
                    labelPixelSize: 10
                    contentPadding: 3
                    accentColor: modelData.id==="reset"
                                 ? Colors.orange:Colors.cyan
                    available: instrument.graphModel.ready
                    onClicked: {
                        if(modelData.id==="back") {
                            instrument.eventOrdinal=-1;
                            instrument.lockedIndex=Celestial.clamp(
                                instrument.focusIndex-1,0,
                                instrument.graphModel.sampleCount-1);
                        } else if(modelData.id==="next") {
                            instrument.eventOrdinal=-1;
                            instrument.lockedIndex=Celestial.clamp(
                                instrument.focusIndex+1,0,
                                instrument.graphModel.sampleCount-1);
                        } else if(modelData.id==="unlock") {
                            instrument.eventOrdinal=-1;
                            instrument.lockedIndex=-1;
                        }
                        else if(modelData.id==="reset"){
                            instrument.lockedIndex=-1;
                            instrument.hoveredIndex=-1;
                            instrument.zoom=1;
                            instrument.panPosition=0.5;
                            instrument.selectedBody="";
                            instrument.eventOrdinal=-1;
                        }
                    }
                }
            }
        }

        GohuText {
            width: parent.width
            height: 14
            font.pixelSize: 10
            color: Colors.white
            elide: Text.ElideRight
            text: instrument.graphModel.ready
                ? Celestial.axisText(
                    instrument.graphModel.times[instrument.focusIndex])
                    +" // "+Celestial.bodyDetails(instrument.graphModel,
                        instrument.focusIndex,instrument.focusBody)
                : "NO SOURCE-VERIFIED OBSERVATION OR CALCULATION"
        }
        QuietText {
            width: parent.width
            height: 14
            font.pixelSize: 10
            color: Colors.cyan
            elide: Text.ElideRight
            text: Celestial.pairDetails(instrument.graphModel,
                                        instrument.focusIndex)
        }
        QuietText {
            width: parent.width
            height: 14
            font.pixelSize: 9
            color: Colors.yellow
            elide: Text.ElideRight
            text: instrument.chosenEvent
                ? "EVENT TIME (EXACT SEARCH) // SAMPLE INSPECTOR IS NEAREST POINT"
                : "GEOCENTRIC / TROPICAL REFERENCE // SAMPLED EVENTS NOT EXHAUSTIVE"
        }
    }
}
