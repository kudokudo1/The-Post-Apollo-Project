import QtQuick
import "../../components"
import "StationCosmosVisualPolicy.js" as VisualPolicy
import "StationSkyTwilightPolicy.js" as TwilightPolicy

// V2 // Two astronomy instruments using StationSky's already active inputs.
// No separate USNO service, timer, location request, storage or ephemeris.
// Lunar orientation is schematic, not the observer's optical tilt.
// The 24h solar path samples the existing calibrated calculation.
Rectangle {
    id: visual
    color: Colors.black
    border.width: 1
    border.color: Colors.cyan
    height: 258

    property bool showMoon: true
    property bool showSun: true
    property bool moonReady: false
    property var moonEphemeris: null
    property var astronomySummary: null
    property var twilightSummary: null
    property var currentSolarPosition: null
    property real providerLocalMinute: -1
    property var latitude: ""
    property var longitude: ""

    property real hoveredMinute: -1
    property real lockedMinute: -1
    readonly property real selectedMinute: lockedMinute>=0
                                          ? lockedMinute:hoveredMinute

    readonly property var moonData: VisualPolicy.moonDisplay(
        moonReady,moonEphemeris,astronomySummary)
    readonly property var solarData: VisualPolicy.solarArc(
        twilightSummary && twilightSummary.available
            ? twilightSummary.date : "",
        latitude,longitude,
        twilightSummary && twilightSummary.available
            ? twilightSummary.calibrationOffsetMinutes:null,
        function(minute,date,lat,lon,offset) {
            return TwilightPolicy.solarPosition(date,minute,lat,lon,offset);
        })
    readonly property var cursorSolar: VisualPolicy.nearestSolar(
        solarData.rows,selectedMinute)

    onMoonDataChanged: moonCanvas.requestPaint()
    onSolarDataChanged: solarCanvas.requestPaint()
    onSelectedMinuteChanged: solarCanvas.requestPaint()
    onWidthChanged: {
        moonCanvas.requestPaint();
        solarCanvas.requestPaint();
    }

    Row {
        id: visualRow
        anchors.fill: parent
        anchors.margins: 10
        spacing: 12

        Rectangle {
            id: moonBay
            visible: visual.showMoon
            width: visual.showSun ? Math.max(0,(visualRow.width-12)/2)
                                  : visualRow.width
            height: parent.height
            color: Colors.dark
            border.width: 1
            border.color: Colors.magenta

            Column {
                anchors.fill: parent
                anchors.margins: 9
                spacing: 5

                GohuText {
                    width: parent.width
                    text: "MOON // PHASE ILLUMINATION"
                    font.pixelSize: 12
                    color: Colors.magenta
                    elide: Text.ElideRight
                }

                Row {
                    height: 124
                    width: parent.width
                    spacing: 12

                    Canvas {
                        id: moonCanvas
                        width: 120
                        height: 120
                        onPaint: {
                            const ctx=getContext("2d");
                            ctx.clearRect(0,0,width,height);
                            const radius=52, cx=width/2, cy=height/2;
                            ctx.beginPath();
                            ctx.arc(cx,cy,radius,0,2*Math.PI);
                            ctx.fillStyle=String(Colors.black);
                            ctx.fill();
                            ctx.strokeStyle=String(Colors.cyan);
                            ctx.lineWidth=1.3;
                            ctx.stroke();
                            const info=visual.moonData;
                            if(!info.ready || info.illumination===null)return;
                            ctx.fillStyle=String(Colors.yellow);
                            // Horizontal circular slices integrate to the
                            // provider's illuminated fraction without
                            // inventing a positional ephemeris.
                            for(let iy=-radius;iy<radius;iy+=1) {
                                const row=VisualPolicy.illuminatedSpan(
                                    info.illumination,info.waxing,iy+0.5,radius);
                                if(!row)continue;
                                ctx.fillRect(cx+row.left,cy+iy,
                                             Math.max(0,row.right-row.left),1);
                            }
                        }
                    }

                    Column {
                        width: Math.max(0,parent.width-132)
                        height: parent.height
                        spacing: 9
                        GohuText {
                            width: parent.width
                            text: visual.moonData.phaseLabel
                            font.pixelSize: 12
                            color: Colors.white
                            wrapMode: Text.WordWrap
                        }
                        GohuText {
                            width: parent.width
                            text: visual.moonData.illumination===null
                                ? "--" : Math.round(visual.moonData.illumination)+"%"
                            font.pixelSize: 27
                            color: Colors.yellow
                        }
                        QuietText {
                            width: parent.width
                            text: visual.moonData.source
                            font.pixelSize: 9
                            color: Colors.cyan
                            wrapMode: Text.WordWrap
                        }
                    }
                }

                Row {
                    width: parent.width
                    height: 33
                    spacing: 2

                    Repeater {
                        model: VisualPolicy.PHASES
                        delegate: Rectangle {
                            required property var modelData
                            width: Math.max(1,(moonBay.width-20-14)/8)
                            height: 31
                            color: visual.moonData.phaseId===modelData.id
                                   ? Colors.magenta:Colors.black
                            border.width: 1
                            border.color: Colors.cyan
                            GohuText {
                                anchors.centerIn: parent
                                text: String(modelData.label).split(" ").map(
                                    function(s){return s.slice(0,1);}
                                ).join("")
                                font.pixelSize: 10
                                color: visual.moonData.phaseId===modelData.id
                                       ? Colors.black:Colors.cyan
                            }
                        }
                    }
                }

                QuietText {
                    width: parent.width
                    font.pixelSize: 8
                    color: Colors.orange
                    wrapMode: Text.WordWrap
                    text: "EIGHT PHASE MARKERS // CURRENT STAGE ONLY"
                          +" // LIT SIDE SCHEMATIC, NOT LOCAL OPTICAL ORIENTATION"
                }
            }
        }

        Rectangle {
            id: solarBay
            visible: visual.showSun
            width: visual.showMoon ? Math.max(0,(visualRow.width-12)/2)
                                   : visualRow.width
            height: parent.height
            color: Colors.dark
            border.width: 1
            border.color: Colors.orange

            Column {
                anchors.fill: parent
                anchors.margins: 9
                spacing: 6

                GohuText {
                    text: "SUN // 24H ALTITUDE MODEL"
                    width: parent.width
                    font.pixelSize: 12
                    color: Colors.orange
                }

                Rectangle {
                    width: parent.width
                    height: 119
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.blue

                    Canvas {
                        id: solarCanvas
                        anchors.fill: parent
                        anchors.margins: 8

                        onPaint: {
                            const ctx=getContext("2d");
                            ctx.clearRect(0,0,width,height);
                            // 0° horizon is the middle reference line.
                            const horizon=VisualPolicy.positionY(0,height);
                            ctx.strokeStyle=String(Colors.cyan);
                            ctx.globalAlpha=0.60;
                            ctx.beginPath();
                            ctx.moveTo(0,horizon);
                            ctx.lineTo(width,horizon);
                            ctx.stroke();
                            ctx.globalAlpha=1;
                            if(!visual.solarData.ready)return;
                            const rows=visual.solarData.rows;
                            ctx.lineWidth=2;
                            for(let i=1;i<rows.length;i++){
                                const a=rows[i-1],b=rows[i];
                                const x1=VisualPolicy.positionX(a.minute,width);
                                const x2=VisualPolicy.positionX(b.minute,width);
                                const y1=VisualPolicy.positionY(a.altitude,height);
                                const y2=VisualPolicy.positionY(b.altitude,height);
                                ctx.strokeStyle=String(
                                    a.altitude>=0&&b.altitude>=0
                                        ? Colors.yellow : Colors.blue);
                                ctx.beginPath();
                                ctx.moveTo(x1,y1);
                                ctx.lineTo(x2,y2);
                                ctx.stroke();
                            }
                            const minute=visual.selectedMinute>=0
                                ? visual.selectedMinute:visual.providerLocalMinute;
                            if(minute>=0&&minute<1440){
                                const x=VisualPolicy.positionX(minute,width);
                                ctx.strokeStyle=String(Colors.magenta);
                                ctx.globalAlpha=0.78;
                                ctx.beginPath();
                                ctx.moveTo(x,0);ctx.lineTo(x,height);ctx.stroke();
                                ctx.globalAlpha=1;
                            }
                        }
                    }

                    MouseArea {
                        anchors.fill: solarCanvas
                        hoverEnabled: true
                        acceptedButtons: Qt.LeftButton
                        cursorShape: Qt.CrossCursor
                        onPositionChanged: function(mouse) {
                            if(visual.lockedMinute>=0)return;
                            visual.hoveredMinute=Math.max(0,Math.min(1439,
                                 Math.floor(mouse.x/Math.max(1,width)*1439)));
                        }
                        onExited: visual.hoveredMinute=-1
                        onClicked: function(mouse) {
                            if(!visual.solarData.ready)return;
                            visual.lockedMinute=Math.max(0,Math.min(1439,
                                 Math.floor(mouse.x/Math.max(1,width)*1439)));
                        }
                    }

                    GohuText {
                        anchors.centerIn: parent
                        visible: !visual.solarData.ready
                        text: "SOLAR MODEL UNAVAILABLE"
                        font.pixelSize: 10
                        color: Colors.orange
                    }
                }

                Row {
                    width: parent.width
                    height: 15
                    GohuText {
                        width: parent.width/5
                        text: "00"
                        font.pixelSize: 9
                        color: Colors.cyan
                    }
                    GohuText {
                        width: parent.width*3/5
                        text: "06     12       18"
                        font.pixelSize: 9
                        horizontalAlignment: Text.AlignHCenter
                        color: Colors.cyan
                    }
                    GohuText {
                        width: parent.width/5
                        text: "24"
                        font.pixelSize: 9
                        horizontalAlignment: Text.AlignRight
                        color: Colors.cyan
                    }
                }

                Row {
                    width: parent.width
                    height: 25
                    spacing: 8
                    GohuText {
                        width: Math.max(0,parent.width-104)
                        text: visual.cursorSolar
                              ? VisualPolicy.clockLabel(visual.cursorSolar.minute)
                                +"  "+visual.cursorSolar.altitude.toFixed(1)+"°"
                              : visual.currentSolarPosition
                                && visual.currentSolarPosition.available
                                ? "NOW "
                                  +visual.currentSolarPosition.altitudeDegrees.toFixed(1)+"°"
                                : "ALTITUDE --"
                        font.pixelSize: 12
                        color: Colors.yellow
                    }
                    ActionButton {
                        width: 95
                        height: 24
                        label: "UNLOCK"
                        labelPixelSize: 10
                        accentColor: Colors.cyan
                        available: visual.lockedMinute>=0
                        onClicked: visual.lockedMinute=-1
                    }
                }

                QuietText {
                    width: parent.width
                    font.pixelSize: 8
                    color: Colors.orange
                    wrapMode: Text.WordWrap
                    text: "SOLAR CENTER / EXISTING CALIBRATED MODEL"
                          +" // LOCAL CIVIL CLOCK, NOT MEASURED SKY PHOTO"
                }
            }
        }
    }
}
