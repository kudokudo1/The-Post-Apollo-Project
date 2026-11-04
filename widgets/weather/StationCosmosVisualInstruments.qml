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
    height: compactMode ? 204 : 304

    // M30-D // Existing full COSMOS V2 visual remains unchanged by default.
    // MAGICK lunar/solar explicitly chooses the fixed-viewport presentation.
    property bool compactMode: false
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
    property string solarDate: ""
    property var solarCivilOffsetMinutes: null
    property string solarOffsetSource: "UNKNOWN"
    property string inspectedPhaseId: ""
    readonly property var referencePhase:
        VisualPolicy.phaseReference(inspectedPhaseId)
    readonly property bool previewReference:
        compactMode && referencePhase.valid
    readonly property var phaseReferenceIllumination: ({
        "new":0,"waxing-crescent":25,"first-quarter":50,
        "waxing-gibbous":75,"full":100,"waning-gibbous":75,
        "last-quarter":50,"waning-crescent":25
    })[inspectedPhaseId]
    readonly property bool referenceWaxing:
        inspectedPhaseId.indexOf("waning")!==0
        && inspectedPhaseId!=="last-quarter"
    readonly property var visibleIllumination: previewReference
        ? phaseReferenceIllumination : moonData.illumination

    property real hoveredMinute: -1
    property real lockedMinute: -1
    readonly property real selectedMinute: lockedMinute>=0
                                          ? lockedMinute:hoveredMinute

    readonly property var moonData: VisualPolicy.moonDisplay(
        moonReady,moonEphemeris,astronomySummary)
    readonly property var solarData: VisualPolicy.solarArc(
        solarDate,latitude,longitude,solarCivilOffsetMinutes,
        function(minute,date,lat,lon,offset) {
            return TwilightPolicy.solarPosition(date,minute,lat,lon,offset);
        })
    readonly property var cursorSolar: VisualPolicy.nearestSolar(
        solarData.rows,selectedMinute)

    onMoonDataChanged: moonCanvas.requestPaint()
    onInspectedPhaseIdChanged: moonCanvas.requestPaint()
    onSolarDataChanged: solarCanvas.requestPaint()
    onSelectedMinuteChanged: solarCanvas.requestPaint()
    onWidthChanged: {
        moonCanvas.requestPaint();
        solarCanvas.requestPaint();
    }

    Row {
        id: visualRow
        anchors.fill: parent
        anchors.margins: visual.compactMode ? 5 : 10
        spacing: visual.compactMode ? 5 : 12

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
                anchors.margins: visual.compactMode ? 5 : 9
                spacing: visual.compactMode ? 3 : 5

                GohuText {
                    width: parent.width
                    text: "MOON // PHASE ILLUMINATION"
                    font.pixelSize: visual.compactMode ? 10 : 12
                    color: Colors.magenta
                    elide: Text.ElideRight
                }

                Row {
                    height: visual.compactMode ? 75 : 124
                    width: parent.width
                    spacing: visual.compactMode ? 7 : 12

                    Canvas {
                        id: moonCanvas
                        width: visual.compactMode ? 73 : 120
                        height: width
                        onPaint: {
                            const ctx=getContext("2d");
                            ctx.clearRect(0,0,width,height);
                            const radius=Math.max(1,Math.min(width,height)/2-8),
                                  cx=width/2, cy=height/2;
                            ctx.beginPath();
                            ctx.arc(cx,cy,radius,0,2*Math.PI);
                            ctx.fillStyle=String(Colors.black);
                            ctx.fill();
                            ctx.strokeStyle=String(Colors.cyan);
                            ctx.lineWidth=1.3;
                            ctx.stroke();
                            const info=visual.moonData;
                            if((!info.ready || info.illumination===null
                               || !info.directionKnown)
                               && !visual.previewReference)return;
                            ctx.fillStyle=String(Colors.yellow);
                            // Horizontal circular slices integrate to the
                            // provider's illuminated fraction without
                            // inventing a positional ephemeris.
                            for(let iy=-radius;iy<radius;iy+=1) {
                                const row=VisualPolicy.illuminatedSpan(
                                    visual.visibleIllumination,
                                    visual.previewReference
                                    ? visual.referenceWaxing : info.waxing,
                                    iy+0.5,radius);
                                if(!row)continue;
                                ctx.fillRect(cx+row.left,cy+iy,
                                             Math.max(0,row.right-row.left),1);
                            }
                        }
                    }

                    MouseArea {
                        anchors.fill: moonCanvas
                        enabled: visual.moonData.phaseId !== ""
                        preventStealing: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            visual.inspectedPhaseId =
                                visual.inspectedPhaseId === visual.moonData.phaseId
                                ? "" : visual.moonData.phaseId;
                        }
                    }

                    Column {
                        width: Math.max(0,parent.width-moonCanvas.width-12)
                        height: parent.height
                        spacing: visual.compactMode ? 3 : 9
                        GohuText {
                            width: parent.width
                            text: visual.previewReference
                                  ? "REF // " + visual.referencePhase.label
                                  : visual.moonData.phaseLabel
                            font.pixelSize: visual.compactMode ? 10 : 12
                            color: Colors.white
                            wrapMode: visual.compactMode ? Text.NoWrap : Text.WordWrap
                            elide: Text.ElideRight
                        }
                        GohuText {
                            width: parent.width
                            text: visual.visibleIllumination===null
                                  || visual.visibleIllumination===undefined
                                ? "--" : Math.round(visual.visibleIllumination)+"%"
                            font.pixelSize: visual.compactMode ? 21 : 27
                            color: Colors.yellow
                        }
                        QuietText {
                            width: parent.width
                            text: visual.previewReference
                                  ? "SCHEMATIC REFERENCE"
                                  : visual.moonData.source
                                  +" // DATE "
                                  +(visual.moonData.sourceDate||"--")
                            font.pixelSize: visual.compactMode ? 8 : 9
                            color: visual.previewReference ? Colors.magenta : Colors.cyan
                            wrapMode: visual.compactMode ? Text.NoWrap : Text.WordWrap
                            elide: Text.ElideRight
                        }
                    }
                }

                Row {
                    id: phaseButtonRow
                    width: parent.width
                    height: visual.compactMode ? 23 : 33
                    spacing: 2

                    Repeater {
                        model: VisualPolicy.PHASES
                        delegate: ActionButton {
                            required property var modelData
                            width: Math.max(1,
                                (phaseButtonRow.width-7*phaseButtonRow.spacing)/8)
                            height: visual.compactMode ? 22 : 31
                            label: modelData.short
                            labelPixelSize: visual.compactMode ? 9 : 10
                            contentPadding: 1
                            accentColor: visual.moonData.phaseId === modelData.id
                                         ? Colors.magenta : Colors.cyan
                            selected: visual.inspectedPhaseId !== ""
                                      ? visual.inspectedPhaseId === modelData.id
                                      : visual.moonData.phaseId === modelData.id
                            onClicked: visual.inspectedPhaseId = modelData.id
                        }
                    }
                }

                Row {
                    width: parent.width
                    height: visual.compactMode ? 33 : 51
                    spacing: visual.compactMode ? 4 : 5

                    QuietText {
                        width: Math.max(0,parent.width-(visual.compactMode?68:89))
                        height: parent.height
                        wrapMode: Text.WordWrap
                        font.pixelSize: visual.compactMode ? 8 : 9
                        color: visual.inspectedPhaseId !== ""
                               ? Colors.cyan : Colors.orange
                        text: visual.inspectedPhaseId !== ""
                              ? "REFERENCE // "
                                +VisualPolicy.phaseReference(
                                   visual.inspectedPhaseId).description
                              : (visual.moonData.phaseId !== ""
                                 ? "CURRENT PHASE HIGHLIGHTED"
                                   +" // PICK A PHASE OR CLICK MOON"
                                 : "CURRENT PHASE UNAVAILABLE"
                                   +" // PICK A REFERENCE BELOW")
                    }

                    ActionButton {
                        width: visual.compactMode ? 64 : 84
                        height: visual.compactMode ? 22 : 25
                        label: "CURRENT"
                        labelPixelSize: 9
                        accentColor: Colors.magenta
                        available: visual.inspectedPhaseId !== ""
                        onClicked: visual.inspectedPhaseId = ""
                    }
                }

                QuietText {
                    width: parent.width
                    visible: !visual.compactMode
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
                anchors.margins: visual.compactMode ? 5 : 9
                spacing: visual.compactMode ? 3 : 6

                GohuText {
                    text: "SUN // 24H ALTITUDE MODEL"
                    width: parent.width
                    font.pixelSize: visual.compactMode ? 10 : 12
                    color: Colors.orange
                }

                Rectangle {
                    width: parent.width
                    height: visual.compactMode ? 75 : 119
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
                        preventStealing: true
                        acceptedButtons: Qt.LeftButton
                        cursorShape: visual.solarData.ready
                                     ? Qt.CrossCursor : Qt.ArrowCursor
                        onPositionChanged: function(mouse) {
                            if(!visual.solarData.ready
                               ||visual.lockedMinute>=0)return;
                            visual.hoveredMinute=Math.max(0,Math.min(1439,
                                 Math.floor(mouse.x/Math.max(1,width)*1439)));
                        }
                        onExited: visual.hoveredMinute=-1
                        onPressed: function(mouse) {
                            if(!visual.solarData.ready)return;
                            if(visual.lockedMinute<0)
                                visual.hoveredMinute=Math.max(0,Math.min(1439,
                                    Math.floor(mouse.x/Math.max(1,width)*1439)));
                        }
                        onClicked: function(mouse) {
                            if(!visual.solarData.ready)return;
                            visual.lockedMinute=Math.max(0,Math.min(1439,
                                 Math.floor(mouse.x/Math.max(1,width)*1439)));
                        }
                    }

                    GohuText {
                        anchors.centerIn: parent
                        visible: !visual.solarData.ready
                        text: VisualPolicy.solarUnavailableReason(
                            visual.solarDate,visual.latitude,visual.longitude,
                            visual.solarCivilOffsetMinutes)
                        font.pixelSize: 10
                        color: Colors.orange
                    }
                }

                Row {
                    width: parent.width
                    height: visual.compactMode ? 12 : 15
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
                    id: solarPresetRow
                    width: parent.width
                    height: visual.compactMode ? 23 : 27
                    spacing: 4

                    Repeater {
                        model: [
                            {id:"midnight",label:"00",minute:0},
                            {id:"morning",label:"06",minute:360},
                            {id:"noon",label:"12",minute:720},
                            {id:"evening",label:"18",minute:1080},
                            {id:"now",label:"NOW",minute:-1}
                        ]
                        delegate: ActionButton {
                            required property var modelData
                            width: Math.max(1,(solarPresetRow.width
                                             -solarPresetRow.spacing*4)/5)
                            height: visual.compactMode ? 22 : 26
                            contentPadding: visual.compactMode ? 1 : 2
                            label: modelData.label
                            labelPixelSize: visual.compactMode ? 9 : 10
                            accentColor: modelData.id === "now"
                                         ? Colors.magenta : Colors.cyan
                            available: visual.solarData.ready
                                       &&(modelData.id !== "now"
                                          ||visual.providerLocalMinute >= 0)
                            selected: visual.lockedMinute >= 0
                                      && (modelData.id === "now"
                                          ? visual.lockedMinute ===
                                             Math.floor(visual.providerLocalMinute)
                                          : visual.lockedMinute === modelData.minute)
                            onClicked: {
                                visual.lockedMinute = modelData.id === "now"
                                    ? Math.floor(visual.providerLocalMinute)
                                    : modelData.minute;
                            }
                        }
                    }
                }

                Row {
                    width: parent.width
                    height: visual.compactMode ? 22 : 25
                    spacing: visual.compactMode ? 4 : 8
                    GohuText {
                        width: Math.max(0,parent.width-
                            (visual.compactMode ? 72 : 104))
                        text: visual.cursorSolar
                              ? "MODEL "+VisualPolicy.clockLabel(
                                    visual.cursorSolar.minute)
                                +"  "+visual.cursorSolar.altitude.toFixed(1)+"°"
                              : visual.currentSolarPosition
                                && visual.currentSolarPosition.available
                                ? "NOW "
                                  +visual.currentSolarPosition.altitudeDegrees.toFixed(1)+"°"
                                : "ALTITUDE --"
                        font.pixelSize: visual.compactMode ? 10 : 12
                        color: Colors.yellow
                    }
                    ActionButton {
                        width: visual.compactMode ? 68 : 95
                        height: visual.compactMode ? 21 : 24
                        label: "UNLOCK"
                        labelPixelSize: visual.compactMode ? 9 : 10
                        accentColor: Colors.cyan
                        available: visual.lockedMinute>=0
                        onClicked: visual.lockedMinute=-1
                    }
                }

                QuietText {
                    visible: !visual.compactMode
                    width: parent.width
                    font.pixelSize: 8
                    color: Colors.orange
                    wrapMode: Text.WordWrap
                    text: "SOLAR CENTER / EXISTING CALIBRATED MODEL"
                          +" // DATE "+(visual.solarData.ready
                                       ?visual.solarData.date:"--")
                          +" // OFFSET "+visual.solarOffsetSource+" "
                          +(visual.solarCivilOffsetMinutes!==null
                            &&visual.solarCivilOffsetMinutes!==undefined
                            ?visual.solarCivilOffsetMinutes+"M":"--")
                          +" // NOT MEASURED SKY PHOTO"
                }
            }
        }
    }
}
