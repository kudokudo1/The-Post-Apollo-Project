import QtQuick
import QtQuick.Effects
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
    // Visual-only neon styling; no extra ephemeris calls or animations.
    property bool neonEnabled: true

    readonly property var eventsInView: Celestial.visibleEvents(graphModel,viewWindow)
    readonly property var chosenEvent: Celestial.eventAt(graphModel,viewWindow,eventOrdinal)
    readonly property var timelineThumbFraction:
        Celestial.timelineHandleFraction(graphModel,viewWindow,focusIndex)

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
        eventTimelineCanvas.requestPaint();
    }
    onGraphModelChanged: graphCanvas.requestPaint()
    onFocusIndexChanged: {
        graphCanvas.requestPaint();
        eventTimelineCanvas.requestPaint();
    }
    onModeChanged: graphCanvas.requestPaint()
    onViewWindowChanged: {
        instrument.eventOrdinal=-1;
        graphCanvas.requestPaint();
        eventTimelineCanvas.requestPaint();
    }
    onEventOrdinalChanged: {
        graphCanvas.requestPaint();
        eventTimelineCanvas.requestPaint();
    }
    onSelectedBodyChanged: graphCanvas.requestPaint()
    onWidthChanged: graphCanvas.requestPaint()
    onHeightChanged: graphCanvas.requestPaint()

    function neonStroke(ctx,color,width,blur) {
        ctx.save();
        ctx.strokeStyle=String(color);
        ctx.lineWidth=width;
        ctx.shadowColor=String(color);
        ctx.shadowBlur=instrument.neonEnabled ? blur : 0;
        ctx.shadowOffsetX=0;
        ctx.shadowOffsetY=0;
        ctx.stroke();
        ctx.restore();
    }
    function neonText(ctx,text,x,y,color,blur) {
        ctx.save();
        ctx.fillStyle=String(color);
        ctx.shadowColor=String(color);
        ctx.shadowBlur=instrument.neonEnabled ? blur : 0;
        ctx.shadowOffsetX=0;
        ctx.shadowOffsetY=0;
        ctx.fillText(text,x,y);
        ctx.restore();
    }
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
            instrument.neonStroke(ctx,
                ring===0?Colors.cyan:Colors.blue,ring===0?1.5:1,7);
        }
        ctx.font="10px monospace";
        for(let sign=0;sign<12;sign++){
            const theta=sign*Math.PI/6-Math.PI/2;
            const color=Celestial.zodiacColor(sign);
            ctx.globalAlpha=0.38;
            ctx.beginPath();
            ctx.moveTo(cx,cy);
            ctx.lineTo(cx+radius*Math.cos(theta),
                       cy+radius*Math.sin(theta));
            instrument.neonStroke(ctx,color,0.8,5);
            // Actual Unicode zodiac glyphs, not AR/TA/GE abbreviations.
            // Qt's font fallback resolves the symbols if Noto is absent.
            ctx.font="18px 'Noto Sans Symbols 2'";
            ctx.textAlign="center";
            ctx.textBaseline="middle";
            ctx.globalAlpha=1;
            const glyph=Celestial.zodiacGlyph(sign);
            instrument.neonText(ctx,glyph,
                cx+(radius+17)*Math.cos(theta),
                cy+(radius+17)*Math.sin(theta),color,10);
            ctx.font="10px monospace";
        }
        ctx.textAlign="start";
        ctx.textBaseline="alphabetic";
        ctx.globalAlpha=1;
        ctx.font="10px monospace";
        instrument.neonText(ctx,"ECLIPTIC",cx-28,cy-7,Colors.magenta,7);
        instrument.neonText(ctx,"0° / ♈",cx-21,cy+11,Colors.cyan,6);
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
            instrument.neonStroke(ctx,Colors.magenta,1.5,9);
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
            ctx.shadowColor=point.color;
            ctx.shadowBlur=instrument.neonEnabled?11:0;
            ctx.fill();
            ctx.shadowBlur=0;
            ctx.strokeStyle=String(Colors.black);
            ctx.lineWidth=1;ctx.stroke();
            // Marker remains on its true ecliptic angle; text is offset
            // independently so neighboring planet names remain legible.
        }
        const labels=Celestial.wheelLabels(instrument.graphModel,
                         instrument.focusIndex,graphCanvas.width,graphCanvas.height);
        for(let l=0;l<labels.length;l++){
            const point=labels[l];
            ctx.beginPath();
            ctx.moveTo(point.pointX,point.pointY);
            ctx.lineTo(point.x,point.y-3);
            ctx.strokeStyle=point.color;
            ctx.globalAlpha=0.5;
            instrument.neonStroke(ctx,point.color,1,5);
            ctx.globalAlpha=1;
            ctx.font="10px monospace";
            instrument.neonText(ctx,point.label,point.x,point.y,
                                point.color,6);
        }
        ctx.restore();
    }
    function paintRelations(ctx) {
        const m=instrument.graphModel;
        const value=Celestial.relationAt(m,instrument.focusIndex);
        const width=graphCanvas.width,height=graphCanvas.height;
        ctx.save();
        ctx.font="10px monospace";
        ctx.textBaseline="alphabetic";
        ctx.fillStyle=String(Colors.magenta);
        ctx.fillText("RELATIONSHIP // ECLIPTIC LONGITUDE GAP",4,11);
        if(!value){
            ctx.fillStyle=String(Colors.orange);
            ctx.fillText("NO SOURCE PAIR IN THIS M4 DATA",8,height/2);
            ctx.restore();
            return;
        }
        // This arc is a 0-180° separation gauge, NOT an orbital map.
        // All reference ticks are traditional aspect angles.
        for(let i=0;i<=60;i++){
            const p=Celestial.relationArcPoint(i*3,width,height);
            if(i===0)ctx.beginPath();
            if(i===0)ctx.moveTo(p.x,p.y);
            else ctx.lineTo(p.x,p.y);
        }
        ctx.globalAlpha=0.9;
        instrument.neonStroke(ctx,Colors.blue,2,8);
        for(let i=0;i<=60;i++){
            const deg=i*value.separation_deg/60;
            const p=Celestial.relationArcPoint(deg,width,height);
            if(i===0)ctx.beginPath();
            if(i===0)ctx.moveTo(p.x,p.y);
            else ctx.lineTo(p.x,p.y);
        }
        ctx.globalAlpha=0.95;
        instrument.neonStroke(ctx,Colors.magenta,3,13);
        ctx.font="9px monospace";
        for(let guide of Celestial.ASPECT_GUIDES){
            const p=Celestial.relationArcPoint(guide.angle,width,height);
            const dx=(p.x-p.cx)/p.radius,dy=(p.y-p.cy)/p.radius;
            ctx.beginPath();
            ctx.moveTo(p.x-dx*5,p.y-dy*5);
            ctx.lineTo(p.x+dx*5,p.y+dy*5);
            ctx.globalAlpha=0.9;
            instrument.neonStroke(ctx,Colors.yellow,1,5);
            ctx.fillStyle=String(Colors.white);
            const px=Celestial.clamp(p.x-10,2,width-32);
            const py=Celestial.clamp(p.y+dy*13,22,height-21);
            ctx.fillText(guide.angle+"°",px,py);
        }
        const marker=Celestial.relationArcPoint(value.separation_deg,width,height);
        ctx.beginPath();ctx.arc(marker.x,marker.y,5,0,2*Math.PI);
        ctx.fillStyle=String(Colors.magenta);ctx.globalAlpha=1;
        ctx.shadowColor=String(Colors.magenta);
        ctx.shadowBlur=instrument.neonEnabled?12:0;
        ctx.fill();ctx.shadowBlur=0;
        ctx.strokeStyle=String(Colors.white);ctx.lineWidth=1;ctx.stroke();
        const centerX=width/2,centerY=Math.max(70,height*0.79);
        ctx.fillStyle=String(Colors.white);
        ctx.font="15px monospace";
        ctx.fillText(value.separation_deg.toFixed(2)+"°",
                     centerX-24,centerY-39);
        ctx.font="9px monospace";
        ctx.fillStyle=String(Colors.cyan);
        const aspectText=value.aspects.length
            ? value.aspects.join(" / ").toUpperCase()
            : "NO ASPECT IN ORB";
        ctx.fillText(aspectText.slice(0,27),
                     Celestial.clamp(centerX-aspectText.length*2.5,4,width-85),
                     centerY-21);
        // These dots label the two measured bodies, not their orbital locations.
        const first=Celestial.relationArcPoint(0,width,height);
        const second=Celestial.relationArcPoint(180,width,height);
        ctx.globalAlpha=1;
        for(let node of [
            {x:first.x,color:value.firstColor,label:value.first},
            {x:second.x,color:value.secondColor,label:value.second}
        ]){
            ctx.beginPath();ctx.arc(node.x,centerY,4,0,2*Math.PI);
            ctx.fillStyle=node.color;
            ctx.shadowColor=node.color;
            ctx.shadowBlur=instrument.neonEnabled?8:0;
            ctx.fill();ctx.shadowBlur=0;
            ctx.font="10px monospace";
            ctx.fillText(node.label.slice(0,12),
                Celestial.clamp(node.x-node.label.length*3,2,width-80),
                Celestial.clamp(centerY+18,13,height-6));
        }
        ctx.restore();
    }
    function paintChart(ctx) {
        const width=graphCanvas.width,height=graphCanvas.height;
        const view=instrument.viewWindow;
        const range=Celestial.rangeFor(instrument.graphModel,view,
                                       instrument.mode);
        const layout=Celestial.chartLayout(width,height);
        const series=instrument.mode==="aspects"
            ? instrument.graphModel.relationships
            : instrument.graphModel.series;
        const legend=Celestial.legendRows(instrument.graphModel,instrument.mode);
        ctx.save();
        ctx.font="10px monospace";
        ctx.lineWidth=1;
        ctx.globalAlpha=0.9;
        ctx.fillStyle=String(Colors.white);
        ctx.fillText(instrument.mode==="aspects"
                     ? "ECLIPTIC SEPARATION (°)" : "UNWRAPPED LONGITUDE (°)",
                     2,10);
        // Legend colors are the same as the rendered series colors.
        let legendX=layout.left;
        for(let l=0;l<legend.length;l++) {
            const label=legend[l];
            const labelWidth=Math.min(125,label.text.length*6+18);
            if(legendX+labelWidth>width-3)break;
            ctx.globalAlpha=1;
            ctx.fillStyle=label.color;
            ctx.fillRect(legendX,16,9,3);
            ctx.font="9px monospace";
            ctx.fillText(label.text,legendX+13,23);
            legendX+=labelWidth+5;
        }
        ctx.font="10px monospace";
        // Reserve a left gutter for ° ticks, plus bottom UTC date labels.
        for(let tick=0;tick<=4;tick++){
            const y=layout.top+tick*layout.height/4;
            ctx.globalAlpha=0.24;
            ctx.strokeStyle=String(Colors.cyan);
            ctx.beginPath();
            ctx.moveTo(layout.left,y);ctx.lineTo(layout.right,y);
            ctx.stroke();
            ctx.globalAlpha=0.82;
            ctx.fillStyle=String(Colors.white);
            ctx.fillText((range.max-(range.max-range.min)*tick/4)
                         .toFixed(1)+"°",2,y+3);
        }
        const timeTicks=[view.from,Math.round((view.from+view.to)/2),view.to];
        for(let ti=0;ti<timeTicks.length;ti++){
            const idx=timeTicks[ti];
            if(ti>0 && idx===timeTicks[ti-1])continue;
            const t=instrument.graphModel.times[idx];
            const x=Celestial.plotX(idx,view,layout);
            const text=Celestial.axisText(t).slice(5,16);
            ctx.globalAlpha=0.3;
            ctx.strokeStyle=String(Colors.cyan);
            ctx.beginPath();
            ctx.moveTo(x,layout.top);ctx.lineTo(x,layout.bottom);
            ctx.stroke();
            ctx.globalAlpha=0.85;
            ctx.fillStyle=String(Colors.white);
            const offset=ti===0?0:ti===2?text.length*6:text.length*3;
            ctx.fillText(text,x-offset,height-5);
        }
        for(let rowIndex=0;rowIndex<series.length;rowIndex++){
            const row=series[rowIndex];
            const points=instrument.mode==="aspects"?row.samples:row.rows;
            const isFocused=instrument.mode==="aspects" ||
                instrument.focusBody===row.body;
            ctx.strokeStyle=instrument.chartInk(rowIndex);
            ctx.globalAlpha=isFocused?1:0.65;
            ctx.lineWidth=isFocused?2.2:1.5;
            ctx.beginPath();
            for(let index=view.from;index<=view.to;index++){
                const value=instrument.mode==="aspects"
                    ? points[index].longitude_separation_deg
                    : points[index].unwrapped_longitude_deg;
                const x=Celestial.plotX(index,view,layout);
                const y=Celestial.plotY(value,range,layout);
                if(index===view.from)ctx.moveTo(x,y);
                else ctx.lineTo(x,y);
            }
            instrument.neonStroke(ctx,instrument.chartInk(rowIndex),
                                  isFocused?2.2:1.5,7);
        }
        const start=instrument.graphModel.times[view.from];
        const end=instrument.graphModel.times[view.to];
        if(instrument.graphModel.events.length>0){
            for(let e=0;e<instrument.graphModel.events.length;e++){
                const event=instrument.graphModel.events[e];
                const t=Date.parse(event.time_utc);
                if(t<start||t>end)continue;
                const x=layout.left+(t-start)/Math.max(1,end-start)*layout.width;
                const selected=instrument.chosenEvent &&
                    event.time_utc===instrument.chosenEvent.time_utc &&
                    event.name===instrument.chosenEvent.name;
                ctx.strokeStyle=selected?String(Colors.magenta):String(Colors.yellow);
                ctx.globalAlpha=selected?1:0.38;
                ctx.lineWidth=selected?2:1;
                ctx.beginPath();ctx.moveTo(x,layout.top);
                ctx.lineTo(x,layout.bottom);
                instrument.neonStroke(ctx,selected?Colors.magenta:Colors.yellow,
                                      selected?2:1,selected?9:5);
            }
        }
        const focusTime=instrument.graphModel.times[instrument.focusIndex];
        if(focusTime>=start && focusTime<=end){
            const focusX=layout.left+(focusTime-start)
                          /Math.max(1,end-start)*layout.width;
            ctx.strokeStyle=String(Colors.magenta);
            ctx.globalAlpha=0.95;
            ctx.lineWidth=1;
            ctx.beginPath();ctx.moveTo(focusX,layout.top);
            ctx.lineTo(focusX,layout.bottom);
            instrument.neonStroke(ctx,Colors.magenta,1,7);
            for(let rowIndex=0;rowIndex<series.length;rowIndex++){
                const row=series[rowIndex];
                const sample=instrument.mode==="aspects"
                    ? row.samples[instrument.focusIndex]
                    : row.rows[instrument.focusIndex];
                const value=instrument.mode==="aspects"
                    ? sample.longitude_separation_deg
                    : sample.unwrapped_longitude_deg;
                const y=Celestial.plotY(value,range,layout);
                ctx.beginPath();ctx.arc(focusX,y,3.5,0,2*Math.PI);
                ctx.fillStyle=instrument.chartInk(rowIndex);
                ctx.globalAlpha=1;
                ctx.shadowColor=instrument.chartInk(rowIndex);
                ctx.shadowBlur=instrument.neonEnabled?8:0;
                ctx.fill();ctx.shadowBlur=0;
            }
        }
        ctx.restore();
    }

    Column {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 5

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
                    {id:"wheel",label:"ZODIAC"},
                    {id:"motion",label:"MOTION"},
                    {id:"aspects",label:"ASPECTS"},
                    {id:"relations",label:"RELATIONS"}
                ]
                delegate: ActionButton {
                    required property var modelData
                    width: Math.max(1,(modeRow.width-15)/4)
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
            height: Math.max(150,instrument.height-254)
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
                    else if(instrument.mode==="relations")instrument.paintRelations(ctx);
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
                function sampleFraction(x) {
                    return instrument.mode==="wheel" || instrument.mode==="relations"
                        ? x/Math.max(1,width)
                        : Celestial.plotFraction(x,width,height);
                }

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
                            instrument.mode!=="relations" && instrument.zoom>1) {
                            instrument.panPosition=Celestial.clamp(
                                instrument.panPosition
                                -(mouse.x-previousX)
                                /Math.max(1,Celestial.chartLayout(width,height).width),
                                0,1);
                        } else if (panning && (instrument.mode==="wheel" ||
                                                 instrument.mode==="relations")) {
                            instrument.eventOrdinal=-1;
                            instrument.lockedIndex=Celestial.indexAtFraction(
                                instrument.graphModel,instrument.viewWindow,
                                sampleFraction(mouse.x));
                        }
                        previousX=mouse.x;
                    } else if (instrument.lockedIndex<0) {
                        instrument.hoveredIndex=Celestial.indexAtFraction(
                            instrument.graphModel,instrument.viewWindow,
                            sampleFraction(mouse.x));
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
                    } else if(instrument.mode==="relations"){
                        const pair=Celestial.relationAt(instrument.graphModel,
                                                        instrument.focusIndex);
                        if(!pair)return;
                        instrument.selectedBody=pair.bodies[mouse.x<width/2?0:1];
                        instrument.eventOrdinal=-1;
                        instrument.lockedIndex=instrument.focusIndex;
                    } else {
                        instrument.eventOrdinal=-1;
                        instrument.lockedIndex=Celestial.indexAtFraction(
                            instrument.graphModel,instrument.viewWindow,
                            sampleFraction(mouse.x));
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
                text: instrument.mode==="wheel" || instrument.mode==="relations"
                    ? "DRAG // TIME   |   CLICK // BODY   |   SCROLL // ZOOM TIME"
                    : "DRAG // PAN TIME   |   CLICK // LOCK   |   SCROLL // ZOOM"
                visible: instrument.graphModel.ready
            }
        }

        // M5g // Clickable timeline is derived exclusively from M4 events.
        // A click outside an event selects the nearest existing M4 sample.
        Rectangle {
            id: eventTimeline
            width: parent.width
            height: 30
            color: Colors.dark
            border.width: 1
            border.color: Colors.blue
            clip: false
            Canvas {
                id: eventTimelineCanvas
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 12
                onPaint: {
                    const ctx=getContext("2d");
                    ctx.clearRect(0,0,width,height);
                    if(!instrument.graphModel.ready)return;
                    const markers=Celestial.timelineMarkers(
                        instrument.graphModel,instrument.viewWindow);
                    ctx.strokeStyle=String(Colors.cyan);
                    ctx.globalAlpha=0.75;
                    ctx.lineWidth=2;
                    ctx.shadowColor=String(Colors.cyan);
                    ctx.shadowBlur=instrument.neonEnabled?9:0;
                    ctx.beginPath();
                    ctx.moveTo(0,height/2);ctx.lineTo(width,height/2);
                    ctx.stroke();
                    ctx.shadowBlur=0;
                    const kindColors={
                        "crossing":String(Colors.yellow),
                        "station":String(Colors.magenta),
                        "candidate":String(Colors.orange)
                    };
                    for(let marker of markers){
                        const px=marker.fraction*width;
                        const selected=marker.ordinal===instrument.eventOrdinal;
                        ctx.strokeStyle=kindColors[marker.kind];
                        ctx.globalAlpha=selected?1:0.8;
                        ctx.lineWidth=selected?3:2;
                        ctx.shadowColor=kindColors[marker.kind];
                        ctx.shadowBlur=instrument.neonEnabled?8:0;
                        ctx.beginPath();
                        ctx.moveTo(px,selected?1:5);
                        ctx.lineTo(px,height-5);
                        ctx.stroke();
                        ctx.shadowBlur=0;
                    }
                    const t=instrument.graphModel.times[instrument.focusIndex];
                    const v=instrument.viewWindow;
                    const start=instrument.graphModel.times[v.from];
                    const end=instrument.graphModel.times[v.to];
                    if(t>=start && t<=end){
                        const px=(t-start)/Math.max(1,end-start)*width;
                        ctx.globalAlpha=1;
                        ctx.fillStyle=String(Colors.white);
                        ctx.shadowColor=String(Colors.white);
                        ctx.shadowBlur=instrument.neonEnabled?7:0;
                        ctx.beginPath();ctx.arc(px,height/2,2.5,0,Math.PI*2);
                        ctx.fill();ctx.shadowBlur=0;
                    }
                }
            }
            // M5h // Slider-style grab handle. It follows a real M4
            // sample timestamp and never invents intermediate ephemeris data.
            Rectangle {
                id: timelineThumb
                z: 2
                visible: instrument.graphModel.ready
                         && instrument.timelineThumbFraction !== null
                width: 17
                height: 20
                radius: 3
                x: eventTimelineCanvas.x
                   + (instrument.timelineThumbFraction === null ? 0
                      : instrument.timelineThumbFraction*eventTimelineCanvas.width)
                   - width/2
                anchors.verticalCenter: parent.verticalCenter
                color: timelineInput.pressed ? Colors.yellow : Colors.white
                border.width: 1
                border.color: Colors.magenta

                RectangularShadow {
                    anchors.fill: parent
                    z: -1
                    spread: 5
                    opacity: instrument.neonEnabled ? 0.75 : 0.0
                    color: timelineInput.pressed ? Colors.orange : Colors.magenta
                }
                Row {
                    anchors.centerIn: parent
                    spacing: 3
                    Repeater {
                        model: 2
                        Rectangle {
                            width: 2
                            height: 9
                            radius: 1
                            color: Colors.magenta
                        }
                    }
                }
                Behavior on x {
                    enabled: !timelineInput.pressed
                    NumberAnimation { duration: 80; easing.type: Easing.OutQuad }
                }
            }
            MouseArea {
                id: timelineInput
                z: 3
                anchors.fill: eventTimelineCanvas
                enabled: instrument.graphModel.ready
                hoverEnabled: true
                preventStealing: true
                cursorShape: Qt.SizeHorCursor
                acceptedButtons: Qt.LeftButton

                property real pressX: 0
                property real grabOffset: 0
                property bool didDrag: false

                function scrubTo(x) {
                    const index=Celestial.timelineSampleIndex(
                        instrument.graphModel,instrument.viewWindow,x,width);
                    if(index < 0)return;
                    instrument.eventOrdinal=-1;
                    instrument.lockedIndex=index;
                }
                onPressed: function(mouse) {
                    pressX=mouse.x;
                    didDrag=false;
                    const centerX=Celestial.timelineHandleX(
                        instrument.graphModel,instrument.viewWindow,
                        instrument.focusIndex,width);
                    grabOffset=centerX!==null && Math.abs(mouse.x-centerX)<=13
                        ? mouse.x-centerX : 0;
                }
                onPositionChanged: function(mouse) {
                    if(!pressed)return;
                    if(Math.abs(mouse.x-pressX)>3)didDrag=true;
                    if(didDrag)scrubTo(mouse.x-grabOffset);
                }
                onReleased: function(mouse) {
                    if(!didDrag){
                        // Preserve the existing clickable M4 event markers.
                        const chosen=Celestial.timelinePick(instrument.graphModel,
                            instrument.viewWindow,mouse.x,width,10);
                        if(chosen){
                            instrument.eventOrdinal=chosen.ordinal;
                            instrument.lockedIndex=chosen.sampleIndex;
                        }else{
                            scrubTo(mouse.x);
                        }
                    }
                    didDrag=false;
                    grabOffset=0;
                }
                onCanceled: {
                    didDrag=false;
                    grabOffset=0;
                }
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
                ? "CALCULATED EVENT TIME // PLANET POSITIONS USE NEAREST SAMPLE"
                : "GEOCENTRIC / TROPICAL REFERENCE // SAMPLED EVENTS NOT EXHAUSTIVE"
        }
    }
}
