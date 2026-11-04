import QtQuick
import "../../components"
import "StationCosmosBearingComparisonPolicy.js" as Compare
import "StationCosmosPlanetHorizonPolicy.js" as Horizon
import "StationCosmosPlanetEventPolicy.js" as PlanetPolicy

// V3c // Two dated USNO local-horizon event bearings, not orbital aspects.
// All angles are azimuths clockwise from TRUE NORTH for a single civil date.
Rectangle {
    id: comparisonPane
    height: 414
    color: Colors.black
    border.width: 1
    border.color: Colors.cyan
    clip: true

    property var datedRows: []
    property string civilDate: ""
    property bool sourceReady: false
    property string sourceError: ""
    property string planetA: "MERCURY"
    property string planetB: "VENUS"
    property string eventKind: "rise"
    property string activeSide: "A"
    signal backToHorizon()
    signal returnToTimeline()

    readonly property var bearings: sourceReady
        ? Horizon.markers(datedRows, "ALL") : []
    readonly property var measurement: Compare.compare(
        bearings, civilDate, planetA, planetB, eventKind)
    readonly property var activeEvent: measurement.ready
        ? (activeSide === "B" ? measurement.eventB : measurement.eventA)
        : null

    onMeasurementChanged: bearingCanvas.requestPaint()
    onActiveSideChanged: bearingCanvas.requestPaint()
    onWidthChanged: bearingCanvas.requestPaint()
    onHeightChanged: bearingCanvas.requestPaint()

    function paintDial(ctx) {
        const w=bearingCanvas.width,h=bearingCanvas.height;
        ctx.clearRect(0,0,w,h);
        if(w<=0 || h<=0) return;
        const cx=w/2,cy=h/2,r=Math.max(0,Math.min(w,h)/2-27);
        if(r<5) return;
        ctx.save();
        ctx.textAlign="center";
        ctx.textBaseline="middle";
        ctx.font="10px monospace";
        for(let ring=1;ring<=3;ring++) {
            ctx.beginPath();
            ctx.arc(cx,cy,r*ring/3,0,2*Math.PI);
            ctx.strokeStyle=String(Colors.cyan);
            ctx.lineWidth=ring===3?1.5:0.8;
            ctx.globalAlpha=ring===3?0.65:0.20;
            ctx.stroke();
        }
        for(let degrees=0;degrees<360;degrees+=30) {
            const a=(degrees-90)*Math.PI/180;
            ctx.beginPath();
            ctx.moveTo(cx+Math.cos(a)*(r-6),cy+Math.sin(a)*(r-6));
            ctx.lineTo(cx+Math.cos(a)*r,cy+Math.sin(a)*r);
            ctx.strokeStyle=String(Colors.blue);
            ctx.globalAlpha=degrees%90===0?0.82:0.39;
            ctx.lineWidth=degrees%90===0?2:1;
            ctx.stroke();
        }
        for(const label of [
            {text:"N",angle:0},{text:"E",angle:90},
            {text:"S",angle:180},{text:"W",angle:270}]) {
            const a=(label.angle-90)*Math.PI/180;
            ctx.fillStyle=String(Colors.yellow);
            ctx.globalAlpha=1;
            ctx.fillText(label.text,
                cx+Math.cos(a)*(r+13),cy+Math.sin(a)*(r+13));
        }
        ctx.fillStyle=String(Colors.magenta);
        ctx.beginPath();
        ctx.arc(cx,cy,3,0,2*Math.PI);
        ctx.fill();

        const result=comparisonPane.measurement;
        if(!result.ready) {
            ctx.fillStyle=String(Colors.orange);
            ctx.font="10px monospace";
            ctx.fillText("NO PAIRED DATA",cx,cy+22);
            ctx.restore();
            return;
        }

        // Shortest measured angular separation. Arc represents bearing
        // difference only; it is NOT a planet movement or ecliptic aspect.
        if(result.gap>0) {
            const start=Compare.theta(result.eventA.azimuth);
            const end=start+result.signed*Math.PI/180;
            ctx.beginPath();
            ctx.arc(cx,cy,r*0.57,start,end,result.signed<0);
            ctx.strokeStyle=String(Colors.magenta);
            ctx.globalAlpha=0.95;
            ctx.lineWidth=4;
            ctx.lineCap="round";
            ctx.shadowColor=String(Colors.magenta);
            ctx.shadowBlur=8;
            ctx.stroke();
            ctx.shadowBlur=0;
        }

        for(const member of [
                {event:result.eventA,side:"A",color:Colors.cyan},
                {event:result.eventB,side:"B",color:Colors.orange}]) {
            const pt=Compare.point(member.event.azimuth,cx,cy,r);
            if(!pt)continue;
            const focused=comparisonPane.activeSide===member.side;
            ctx.beginPath();
            ctx.moveTo(cx,cy);
            ctx.lineTo(pt.x,pt.y);
            ctx.globalAlpha=focused?0.94:0.52;
            ctx.strokeStyle=String(member.color);
            ctx.lineWidth=focused?2.5:1.4;
            ctx.stroke();

            ctx.beginPath();
            ctx.arc(pt.x,pt.y,focused?8:6,0,2*Math.PI);
            ctx.globalAlpha=1;
            ctx.fillStyle=String(member.color);
            ctx.shadowColor=String(member.color);
            ctx.shadowBlur=focused?11:5;
            ctx.fill();
            ctx.shadowBlur=0;
            ctx.fillStyle=String(Colors.black);
            ctx.font="bold 10px monospace";
            ctx.fillText(member.side,pt.x,pt.y+0.5);
            if(focused) {
                ctx.beginPath();
                ctx.arc(pt.x,pt.y,11,0,2*Math.PI);
                ctx.strokeStyle=String(Colors.yellow);
                ctx.lineWidth=1;
                ctx.stroke();
            }
        }
        ctx.font="bold 13px monospace";
        ctx.globalAlpha=1;
        ctx.fillStyle=String(Colors.magenta);
        ctx.fillText(result.gap+"°",cx,cy+20);
        ctx.restore();
    }

    Column {
        anchors.fill: parent
        anchors.margins: 9
        spacing: 4

        Row {
            width: parent.width
            height: 24
            spacing: 5
            GohuText {
                width: Math.max(0,parent.width-177)
                height: 23
                font.pixelSize: 12
                text: "✦ BEARING GAP // TRUE N"
                color: Colors.magenta
                elide: Text.ElideRight
            }
            ActionButton {
                width: 80
                height: 22
                label: "HORIZON"
                labelPixelSize: 9
                contentPadding: 0
                accentColor: Colors.cyan
                onClicked: comparisonPane.backToHorizon()
            }
            ActionButton {
                width: 87
                height: 22
                label: "TIMELINE"
                labelPixelSize: 9
                contentPadding: 0
                accentColor: Colors.orange
                onClicked: comparisonPane.returnToTimeline()
            }
        }

        QuietText {
            width: parent.width
            height: 16
            font.pixelSize: 9
            color: Colors.cyan
            elide: Text.ElideRight
            text: "USNO MRST // " + (comparisonPane.civilDate || "DATE --")
                  + " // " + (comparisonPane.sourceReady
                             ? "DATED EVENT BEARINGS" : "NO SOURCE")
        }

        Row {
            id: firstSelect
            width: parent.width
            height: 27
            spacing: 4
            GohuText {
                width: 18
                height: 25
                text: "A"
                color: Colors.cyan
                font.pixelSize: 14
            }
            Repeater {
                model: Compare.PLANETS
                delegate: ActionButton {
                    required property var modelData
                    width: Math.max(1,(firstSelect.width-18-5*firstSelect.spacing)/5)
                    height: 25
                    contentPadding: 1
                    labelPixelSize: 9
                    label: PlanetPolicy.planetLabel(modelData)
                    selected: comparisonPane.planetA===modelData
                    accentColor: Colors.cyan
                    onClicked: comparisonPane.planetA=modelData
                }
            }
        }

        Row {
            id: secondSelect
            width: parent.width
            height: 27
            spacing: 4
            GohuText {
                width: 18
                height: 25
                text: "B"
                color: Colors.orange
                font.pixelSize: 14
            }
            Repeater {
                model: Compare.PLANETS
                delegate: ActionButton {
                    required property var modelData
                    width: Math.max(1,(secondSelect.width-18-5*secondSelect.spacing)/5)
                    height: 25
                    contentPadding: 1
                    labelPixelSize: 9
                    label: PlanetPolicy.planetLabel(modelData)
                    selected: comparisonPane.planetB===modelData
                    accentColor: Colors.orange
                    onClicked: comparisonPane.planetB=modelData
                }
            }
        }

        Row {
            width: parent.width
            height: 27
            spacing: 6
            ActionButton {
                width: 110
                height: 25
                contentPadding: 1
                label: "R // RISE"
                labelPixelSize: 10
                accentColor: Colors.cyan
                selected: comparisonPane.eventKind==="rise"
                onClicked: comparisonPane.eventKind="rise"
            }
            ActionButton {
                width: 110
                height: 25
                contentPadding: 1
                label: "S // SET"
                labelPixelSize: 10
                accentColor: Colors.orange
                selected: comparisonPane.eventKind==="set"
                onClicked: comparisonPane.eventKind="set"
            }
            QuietText {
                width: Math.max(0,parent.width-232)
                font.pixelSize: 9
                color: Colors.yellow
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
                text: "SELECT TWO BODIES + ONE EVENT KIND"
            }
        }

        Row {
            width: parent.width
            height: 186
            spacing: 8
            Item {
                width: Math.min(214, Math.max(164,parent.width*0.52))
                height: parent.height
                Canvas {
                    id: bearingCanvas
                    anchors.fill: parent
                    antialiasing: true
                    renderTarget: Canvas.Image
                    onPaint: comparisonPane.paintDial(getContext("2d"))
                }
                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    acceptedButtons: Qt.LeftButton
                    cursorShape: Qt.CrossCursor
                    onClicked: function(mouse) {
                        const cx=width/2,cy=height/2;
                        const radius=Math.max(0,Math.min(width,height)/2-27);
                        const side=Compare.pickSide(
                            comparisonPane.measurement,mouse.x,mouse.y,
                            cx,cy,radius,13);
                        if(side!=="")comparisonPane.activeSide=side;
                    }
                }
            }
            Column {
                width: Math.max(0,parent.width-222)
                height: parent.height
                spacing: 8
                GohuText {
                    width: parent.width
                    color: Colors.magenta
                    font.pixelSize: 12
                    text: comparisonPane.measurement.ready
                        ? comparisonPane.measurement.gap+"° // "
                          +comparisonPane.measurement.direction
                        : "UNAVAILABLE"
                    elide: Text.ElideRight
                }
                QuietText {
                    width: parent.width
                    font.pixelSize: 10
                    color: Colors.cyan
                    wrapMode: Text.WordWrap
                    text: comparisonPane.measurement.ready
                        ? Compare.eventLabel(comparisonPane.measurement.eventA)
                        : comparisonPane.measurement.reason
                }
                QuietText {
                    width: parent.width
                    font.pixelSize: 10
                    color: Colors.orange
                    wrapMode: Text.WordWrap
                    text: comparisonPane.measurement.ready
                        ? Compare.eventLabel(comparisonPane.measurement.eventB)
                        : "ONLY MATCHED SOURCE EVENTS ARE COMPARED"
                }
                Row {
                    width: parent.width
                    height: 25
                    spacing: 5
                    ActionButton {
                        width: 57
                        height: 24
                        contentPadding: 0
                        labelPixelSize: 9
                        label: "FOCUS A"
                        accentColor: Colors.cyan
                        selected: comparisonPane.activeSide === "A"
                        available: comparisonPane.measurement.ready
                        onClicked: comparisonPane.activeSide = "A"
                    }
                    ActionButton {
                        width: 57
                        height: 24
                        contentPadding: 0
                        labelPixelSize: 9
                        label: "FOCUS B"
                        accentColor: Colors.orange
                        selected: comparisonPane.activeSide === "B"
                        available: comparisonPane.measurement.ready
                        onClicked: comparisonPane.activeSide = "B"
                    }
                }
                QuietText {
                    width: parent.width
                    color: Colors.cyan
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                    text: "CLICK A OR B MARKER TO INSPECT ITS ORIGINAL BEARING"
                }
            }
        }

        Rectangle {
            width: parent.width
            height: 37
            color: Colors.dark
            border.width: 1
            border.color: Colors.blue
            Column {
                anchors.fill: parent
                anchors.margins: 5
                spacing: 2
                GohuText {
                    width: parent.width
                    font.pixelSize: 10
                    color: Colors.yellow
                    elide: Text.ElideRight
                    text: comparisonPane.activeEvent
                          ? Compare.eventLabel(comparisonPane.activeEvent)
                          : "NO VALID PAIR FOR THIS DATE"
                }
                QuietText {
                    width: parent.width
                    font.pixelSize: 9
                    color: Colors.orange
                    elide: Text.ElideRight
                    text: "HORIZON BEARING GAP // NOT ECLIPTIC ASPECT OR ORBITAL ANGLE"
                }
            }
        }

        QuietText {
            width: parent.width
            font.pixelSize: 9
            color: Colors.orange
            wrapMode: Text.WordWrap
            text: comparisonPane.sourceError!=="" ? comparisonPane.sourceError
                  : "DATED USNO EVENTS // A/B TIMES MAY DIFFER."
                    + " ANGLE BETWEEN TRUE-NORTH DIRECTIONS, NOT PLANET POSITIONS."
        }
    }
}
