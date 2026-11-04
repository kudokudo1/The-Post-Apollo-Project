import QtQuick
import "../../components"
import "StationCosmosPlanetHorizonPolicy.js" as Horizon
import "StationCosmosPlanetEventPolicy.js" as PlanetPolicy

// V3a // Source-true USNO horizon azimuth instrument.
// Compass dots depict only RISE / SET event bearings from TRUE NORTH.
// Transit altitude is a separate numerical reading. No current planet
// position, continuous sky track or JPL/ecliptic inference is drawn.
Rectangle {
    id: horizonPane
    height: 414
    color: Colors.black
    border.width: 1
    border.color: Colors.cyan
    clip: true

    property var datedRows: []
    property string civilDate: ""
    property string selectedPlanet: "ALL"
    property bool sourceReady: false
    property string sourceError: ""
    property var hoveredMarker: null
    property var lockedMarker: null

    signal planetPicked(string name)
    signal returnToTimeline()

    readonly property var markers: sourceReady
        ? Horizon.markers(datedRows, selectedPlanet) : []
    readonly property var transits: sourceReady
        ? Horizon.transits(datedRows) : Horizon.transits([])
    readonly property var focusedMarker: lockedMarker || hoveredMarker

    onMarkersChanged: {
        hoveredMarker = null;
        lockedMarker = null;
        compassCanvas.requestPaint();
    }
    onFocusedMarkerChanged: compassCanvas.requestPaint()
    onSelectedPlanetChanged: {
        hoveredMarker = null;
        lockedMarker = null;
    }
    onWidthChanged: compassCanvas.requestPaint()
    onHeightChanged: compassCanvas.requestPaint()

    function ink(kind) {
        return kind === "rise" ? String(Colors.cyan) : String(Colors.orange);
    }

    function paintCompass(ctx) {
        const w=compassCanvas.width, h=compassCanvas.height;
        ctx.clearRect(0,0,w,h);
        const g=Horizon.geometry(w,h);
        if(!g.ready || g.radius<=0) return;
        ctx.save();
        ctx.lineWidth=1;
        for(let ring=1;ring<=3;ring++) {
            ctx.beginPath();
            ctx.arc(g.x,g.y,g.radius*ring/3,0,Math.PI*2);
            ctx.strokeStyle=String(Colors.cyan);
            ctx.globalAlpha=ring===3?0.60:0.21;
            ctx.stroke();
        }
        for(let angle=0;angle<360;angle+=30) {
            const rad=angle*Math.PI/180;
            ctx.beginPath();
            ctx.moveTo(g.x+Math.sin(rad)*g.radius*0.08,
                       g.y-Math.cos(rad)*g.radius*0.08);
            ctx.lineTo(g.x+Math.sin(rad)*g.radius,
                       g.y-Math.cos(rad)*g.radius);
            ctx.strokeStyle=String(Colors.blue);
            ctx.globalAlpha=angle%90===0?0.5:0.22;
            ctx.stroke();
        }
        ctx.textAlign="center";
        ctx.textBaseline="middle";
        ctx.font="bold 10px monospace";
        for(const label of [
                {text:"N",a:0},{text:"E",a:90},
                {text:"S",a:180},{text:"W",a:270}]) {
            const rad=label.a*Math.PI/180;
            ctx.fillStyle=String(Colors.yellow);
            ctx.globalAlpha=1;
            ctx.fillText(label.text,
                g.x+Math.sin(rad)*(g.radius+13),
                g.y-Math.cos(rad)*(g.radius+13));
        }
        ctx.globalAlpha=0.65;
        ctx.fillStyle=String(Colors.magenta);
        ctx.beginPath();
        ctx.arc(g.x,g.y,3,0,Math.PI*2);ctx.fill();

        for(let i=0;i<horizonPane.markers.length;i++) {
            const marker=horizonPane.markers[i];
            const pt=Horizon.point(marker.azimuth,w,h);
            if(!pt)continue;
            const picked=horizonPane.focusedMarker
                      && horizonPane.focusedMarker.id===marker.id;
            const color=horizonPane.ink(marker.kind);
            ctx.strokeStyle=color;
            ctx.globalAlpha=picked?0.95:0.43;
            ctx.lineWidth=picked?2.3:1.2;
            ctx.beginPath();
            ctx.moveTo(g.x,g.y);
            ctx.lineTo(pt.x,pt.y);
            ctx.stroke();

            ctx.shadowColor=color;
            ctx.shadowBlur=picked?12:4;
            ctx.fillStyle=color;
            ctx.globalAlpha=1;
            ctx.beginPath();
            ctx.arc(pt.x,pt.y,picked?7:5,0,Math.PI*2);
            ctx.fill();
            ctx.shadowBlur=0;
            ctx.fillStyle=String(Colors.black);
            ctx.font="bold 8px monospace";
            ctx.fillText(marker.kind==="rise"?"R":"S",pt.x,pt.y+0.5);
            if(picked) {
                ctx.strokeStyle=String(Colors.magenta);
                ctx.lineWidth=1.5;
                ctx.beginPath();
                ctx.arc(pt.x,pt.y,11,0,Math.PI*2);
                ctx.stroke();
            }
        }
        ctx.restore();
    }

    Column {
        anchors.fill: parent
        anchors.margins: 9
        spacing: 4

        Row {
            width: parent.width
            height: 23
            spacing: 5
            GohuText {
                width: Math.max(0,parent.width-178)
                height: 22
                text: "✦ HORIZON // TRUE NORTH"
                color: Colors.magenta
                font.pixelSize: 12
                elide: Text.ElideRight
            }
            ActionButton {
                width: 80
                height: 22
                label: "TIMELINE"
                labelPixelSize: 9
                contentPadding: 0
                accentColor: Colors.cyan
                onClicked: horizonPane.returnToTimeline()
            }
            GohuText {
                width: 88
                height: 22
                horizontalAlignment: Text.AlignRight
                text: horizonPane.sourceReady ? "USNO / DATED" : "UNAVAILABLE"
                color: horizonPane.sourceReady ? Colors.cyan : Colors.orange
                font.pixelSize: 9
            }
        }

        QuietText {
            width: parent.width
            height: 14
            text: "RISE / SET AZIMUTH // " + (horizonPane.civilDate || "DATE --")
                  + " // " + horizonPane.markers.length + " VALID BEARINGS"
            color: Colors.cyan
            font.pixelSize: 9
            elide: Text.ElideRight
        }

        Row {
            id: planetSelect
            width: parent.width
            height: 27
            spacing: 4
            ActionButton {
                width: Math.max(1,(planetSelect.width-5*planetSelect.spacing)/6)
                height: 25
                contentPadding: 1
                label: "ALL"
                labelPixelSize: 9
                selected: horizonPane.selectedPlanet==="ALL"
                accentColor: Colors.magenta
                onClicked: horizonPane.planetPicked("ALL")
            }
            Repeater {
                model: PlanetPolicy.PLANETS
                delegate: ActionButton {
                    required property var modelData
                    width: Math.max(1,(planetSelect.width-5*planetSelect.spacing)/6)
                    height: 25
                    contentPadding: 1
                    label: PlanetPolicy.planetLabel(modelData)
                    labelPixelSize: 9
                    selected: horizonPane.selectedPlanet===modelData
                    accentColor: Colors.cyan
                    onClicked: horizonPane.planetPicked(modelData)
                }
            }
        }

        Row {
            id: compassRow
            width: parent.width
            height: 212
            spacing: 8

            Item {
                id: compassBay
                width: Math.min(232,Math.max(156,compassRow.width*0.59))
                height: compassRow.height

                Canvas {
                    id: compassCanvas
                    anchors.fill: parent
                    antialiasing: true
                    renderTarget: Canvas.Image
                    onPaint: {
                        const ctx=getContext("2d");
                        horizonPane.paintCompass(ctx);
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    acceptedButtons: Qt.LeftButton
                    preventStealing: true
                    cursorShape: Qt.CrossCursor
                    onPositionChanged: function(mouse) {
                        horizonPane.hoveredMarker=Horizon.pick(
                            horizonPane.markers,mouse.x,mouse.y,
                            width,height,13);
                    }
                    onExited: horizonPane.hoveredMarker=null
                    onClicked: function(mouse) {
                        horizonPane.lockedMarker=Horizon.pick(
                            horizonPane.markers,mouse.x,mouse.y,
                            width,height,13);
                    }
                }
            }

            Column {
                width: Math.max(0,compassRow.width-compassBay.width-compassRow.spacing)
                height: compassRow.height
                spacing: 7
                GohuText {
                    width: parent.width
                    text: "EVENT INSPECTOR"
                    font.pixelSize: 11
                    color: Colors.magenta
                    elide: Text.ElideRight
                }
                GohuText {
                    width: parent.width
                    text: horizonPane.focusedMarker
                          ? horizonPane.focusedMarker.planet
                          : "NO EVENT SELECTED"
                    font.pixelSize: 12
                    color: Colors.yellow
                    elide: Text.ElideRight
                }
                QuietText {
                    width: parent.width
                    font.pixelSize: 10
                    color: Colors.cyan
                    wrapMode: Text.WordWrap
                    text: Horizon.markerLabel(horizonPane.focusedMarker)
                }
                Row {
                    spacing: 5
                    Rectangle {width:8;height:8;color:Colors.cyan}
                    QuietText {text:"RISE AZ";font.pixelSize:9}
                }
                Row {
                    spacing: 5
                    Rectangle {width:8;height:8;color:Colors.orange}
                    QuietText {text:"SET AZ";font.pixelSize:9}
                }
                QuietText {
                    width: parent.width
                    font.pixelSize: 9
                    color: Colors.orange
                    wrapMode: Text.WordWrap
                    text: "BEARINGS ARE EVENT DIRECTIONS, NOT LIVE SKY POSITIONS"
                }
                ActionButton {
                    width: 90
                    height: 24
                    contentPadding: 1
                    label: "UNLOCK"
                    labelPixelSize: 10
                    available: horizonPane.lockedMarker!==null
                    accentColor: Colors.magenta
                    onClicked: horizonPane.lockedMarker=null
                }
            }
        }

        GohuText {
            width: parent.width
            height: 15
            font.pixelSize: 10
            color: Colors.magenta
            text: "TRANSIT // MAXIMUM ALTITUDE (NOT AZIMUTH)"
            elide: Text.ElideRight
        }

        Row {
            id: transitBarRow
            width: parent.width
            height: 55
            spacing: 4
            Repeater {
                model: horizonPane.transits
                delegate: Rectangle {
                    id: transitCard
                    required property var modelData
                    width: Math.max(1,(transitBarRow.width-4*transitBarRow.spacing)/5)
                    height: transitBarRow.height
                    color: Colors.dark
                    border.width: 1
                    border.color: horizonPane.selectedPlanet===modelData.planet
                                  ? Colors.magenta : Colors.blue
                    Column {
                        anchors.fill: parent
                        anchors.margins: 3
                        spacing: 3
                        GohuText {
                            width: parent.width
                            font.pixelSize: 9
                            color: Colors.cyan
                            text: transitCard.modelData.planet
                            elide: Text.ElideRight
                        }
                        Rectangle {
                            width: parent.width
                            height: 5
                            color: Colors.black
                            Rectangle {
                                width: transitCard.modelData.altitude===null ? 0
                                    : parent.width*transitCard.modelData.altitude/90
                                height: parent.height
                                color: Colors.magenta
                            }
                        }
                        QuietText {
                            width: parent.width
                            font.pixelSize: 9
                            color: Colors.yellow
                            elide: Text.ElideRight
                            text: Horizon.altitudeLabel(transitCard.modelData)
                        }
                    }
                }
            }
        }

        QuietText {
            width: parent.width
            height: 20
            color: Colors.orange
            font.pixelSize: 9
            wrapMode: Text.WordWrap
            text: horizonPane.sourceError !== ""
                  ? horizonPane.sourceError
                  : "USNO MRST // TRUE-NORTH AZIMUTH & TRANSIT ALTITUDE."
                    + " NO PLANET TRACK OR ECLIPTIC ALIGNMENT IMPLIED."
        }
    }
}
