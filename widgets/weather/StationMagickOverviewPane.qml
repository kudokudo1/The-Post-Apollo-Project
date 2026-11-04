import QtQuick
import "../../components"
import "StationCosmosVisualPolicy.js" as CosmosVisual
import "StationSkyTwilightPolicy.js" as TwilightPolicy

// M30-B // The overview is a compact astro hero plus lunar/solar instruments.
// The single source-only SKY owns the existing USNO Moon actor. The solar
// calculation stays inside SUN, and the root-owned JPL process only runs after
// the explicit hero CALCULATE click. No invented planetary positions or readings.
Rectangle {
    id: deck
    color: Colors.black
    clip: true

    property var weatherService: null
    property var celestialSource: null
    property real runtimeNowMs: 0
    signal routeRequested(string path)

    readonly property real gutter: 6
    readonly property var moonModel: CosmosVisual.moonDisplay(
        !!observationOwner.moonObservation
            && observationOwner.moonObservation.ready,
        observationOwner.moonObservation
            ? observationOwner.moonObservation.ephemeris : null,
        observationOwner.astronomySummary
    )
    // Reference selectors are visual education only. They do not modify
    // provider Moon readings, chronology, location or the source Moon phase.
    property string inspectedPhaseId: ""
    readonly property var inspectedPhase: CosmosVisual.phaseReference(
        inspectedPhaseId)
    readonly property real referenceIllumination: ({
        "new":0,"waxing-crescent":25,"first-quarter":50,
        "waxing-gibbous":75,"full":100,"waning-gibbous":75,
        "last-quarter":50,"waning-crescent":25
    })[inspectedPhaseId] === undefined ? -1 : ({
        "new":0,"waxing-crescent":25,"first-quarter":50,
        "waxing-gibbous":75,"full":100,"waning-gibbous":75,
        "last-quarter":50,"waning-crescent":25
    })[inspectedPhaseId]
    readonly property real displayedMoonIllumination:
        inspectedPhase.valid ? referenceIllumination
        : moonModel.illumination === null ? -1 : moonModel.illumination
    readonly property bool displayedMoonWaxing:
        inspectedPhase.valid
        ? inspectedPhaseId.indexOf("waning") !== 0
            && inspectedPhaseId !== "last-quarter"
        : moonModel.waxing
    readonly property string displayedPhaseLabel:
        inspectedPhase.valid ? "REF // " + inspectedPhase.label
        : moonModel.phaseLabel

    // Sun presets inspect existing calibrated solar samples, not the
    // live observation and not an altered provider response.
    property real lockedSolarMinute: -1
    property real hoveredSolarMinute: -1
    readonly property real selectedSolarMinute:
        lockedSolarMinute >= 0 ? lockedSolarMinute
        : hoveredSolarMinute >= 0 ? hoveredSolarMinute
        : observationOwner.providerLocalMinute
    readonly property var solarCursor: CosmosVisual.nearestSolar(
        solarModel.rows,selectedSolarMinute)

    readonly property var solarModel: CosmosVisual.solarArc(
        observationOwner.astronomySummary.date,
        weatherService ? weatherService.latitude : "",
        weatherService ? weatherService.longitude : "",
        observationOwner.moonCivilOffsetMinutes,
        function(minute, date, latitude, longitude, offset) {
            return TwilightPolicy.solarPosition(
                date, minute, latitude, longitude, offset);
        }
    )

    // Keep the already-established SKY provider/date/offset contract without
    // mounting its full scroll surface or adding a second USNO collector.
    StationSky {
        id: observationOwner
        sourceOnly: true
        width: 1
        height: 1
        opacity: 0
        visible: deck.visible
        subjectRoute: "cosmos/moon/ephemeris"
        weatherService: deck.weatherService
        runtimeNowMs: deck.runtimeNowMs
    }

    Rectangle {
        id: hero
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: Math.max(0,Math.round(deck.height * 0.59))
        color: Colors.dark
        border.width: 1
        border.color: Colors.magenta
        clip: true

        GohuText {
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.leftMargin: 9
            anchors.topMargin: 6
            width: Math.max(0,parent.width-194)
            text: "MAGICK // CELESTIAL CHART"
            font.pixelSize: 11
            color: Colors.magenta
            elide: Text.ElideRight
        }
        Row {
            anchors.top: parent.top
            anchors.right: parent.right
            anchors.topMargin: 4
            anchors.rightMargin: 6
            spacing: 5
            ActionButton {
                width: 91
                height: 22
                label: deck.celestialSource && deck.celestialSource.loading
                       ? "CALCULATING" : "CALCULATE"
                labelPixelSize: 9
                accentColor: Colors.magenta
                available: !!deck.celestialSource
                           && deck.celestialSource.active
                           && deck.celestialSource.configured
                           && !deck.celestialSource.loading
                // One root-owned JPL Process. Deliberately no autoplay.
                onClicked: deck.celestialSource.refresh()
            }
            ActionButton {
                width: 57
                height: 22
                label: "CHARTS"
                labelPixelSize: 9
                accentColor: Colors.cyan
                onClicked: deck.routeRequested("magick/astrology/charts")
            }
        }

        // Reuse the actual wheel, motion, aspects, relations, network
        // and heliocentric renderer. Compact mode removes only controls
        // that would overflow the overview: the full chart keeps them.
        StationMagickCelestialInstrument {
            id: overviewChart
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.bottom: heroFooter.top
            anchors.leftMargin: 8
            anchors.rightMargin: 8
            anchors.topMargin: 29
            anchors.bottomMargin: 3
            compactMode: true
            neonEnabled: true
            visualData: deck.celestialSource && deck.celestialSource.ready
                        ? deck.celestialSource.visualData : null
        }

        Row {
            id: heroFooter
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.leftMargin: 7
            anchors.rightMargin: 7
            anchors.bottomMargin: 4
            height: 22
            spacing: 4
            QuietText {
                width: Math.max(0,parent.width-198)
                anchors.verticalCenter: parent.verticalCenter
                font.pixelSize: 8
                color: Colors.yellow
                text: "SYMBOLIC INTERPRETATION // NOT CONNECTED"
                elide: Text.ElideRight
            }
            ActionButton {
                width: 45
                height: 21
                label: "◀ PAIR"
                labelPixelSize: 8
                accentColor: Colors.cyan
                available: !!deck.celestialSource && !deck.celestialSource.loading
                onClicked: deck.celestialSource.cyclePair(-1)
            }
            ActionButton {
                width: 45
                height: 21
                label: "PAIR ▶"
                labelPixelSize: 8
                accentColor: Colors.cyan
                available: !!deck.celestialSource && !deck.celestialSource.loading
                onClicked: deck.celestialSource.cyclePair(1)
            }
            ActionButton {
                width: 53
                height: 21
                label: deck.celestialSource
                       ? "SPAN " + deck.celestialSource.spanDays + "D"
                       : "SPAN --"
                labelPixelSize: 8
                accentColor: Colors.yellow
                available: !!deck.celestialSource && !deck.celestialSource.loading
                onClicked: deck.celestialSource.cycleSpan()
            }
            ActionButton {
                width: 43
                height: 21
                label: "LENS"
                labelPixelSize: 8
                accentColor: Colors.magenta
                onClicked: deck.routeRequested("magick/planetary/correspondences")
            }
        }
    }

    Row {
        id: instrumentRow
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: hero.bottom
        anchors.bottom: parent.bottom
        anchors.topMargin: deck.gutter
        spacing: deck.gutter

        Rectangle {
            id: lunarCard
            width: Math.max(0,(instrumentRow.width - deck.gutter)/2)
            height: instrumentRow.height
            color: Colors.dark
            border.width: 1
            border.color: Colors.cyan
            clip: true

            GohuText {
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.leftMargin: 7
                anchors.topMargin: 5
                text: "MOON // PHASE"
                font.pixelSize: 10
                color: Colors.cyan
            }
            ActionButton {
                anchors.top: parent.top
                anchors.right: moonOpen.left
                anchors.topMargin: 4
                anchors.rightMargin: 3
                width: 32
                height: 19
                label: "NOW"
                labelPixelSize: 8
                accentColor: Colors.magenta
                available: deck.inspectedPhaseId !== ""
                onClicked: deck.inspectedPhaseId = ""
            }
            ActionButton {
                id: moonOpen
                anchors.top: parent.top
                anchors.right: parent.right
                anchors.topMargin: 4
                anchors.rightMargin: 5
                width: 43
                height: 19
                label: "OPEN"
                labelPixelSize: 8
                accentColor: Colors.cyan
                onClicked: deck.routeRequested("magick/lunar-solar/moon")
            }

            Row {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.bottom: phasePresetRow.top
                anchors.leftMargin: 6
                anchors.rightMargin: 6
                anchors.topMargin: 24
                anchors.bottomMargin: 3
                spacing: 7

                Canvas {
                    id: moonCanvas
                    width: Math.min(parent.height,58)
                    height: width
                    anchors.verticalCenter: parent.verticalCenter
                    onWidthChanged: requestPaint()
                    onHeightChanged: requestPaint()
                    onPaint: {
                        const ctx=getContext("2d");
                        ctx.clearRect(0,0,width,height);
                        const radius=Math.max(1,Math.min(width,height)/2-3);
                        const cx=width/2,cy=height/2;
                        ctx.beginPath();
                        ctx.arc(cx,cy,radius,0,Math.PI*2);
                        ctx.fillStyle=String(Colors.black);
                        ctx.fill();
                        ctx.strokeStyle=String(Colors.cyan);
                        ctx.lineWidth=1;
                        ctx.stroke();
                        const illumination=deck.displayedMoonIllumination;
                        if(illumination < 0 || (!deck.inspectedPhase.valid
                                               && !deck.moonModel.directionKnown))
                            return;
                        ctx.fillStyle=String(Colors.yellow);
                        for(let y=-radius;y<radius;y+=1){
                            const row=CosmosVisual.illuminatedSpan(
                                illumination,deck.displayedMoonWaxing,y+0.5,radius);
                            if(row)ctx.fillRect(cx+row.left,cy+y,
                                Math.max(0,row.right-row.left),1);
                        }
                    }
                    Connections {
                        target: deck
                        function onMoonModelChanged(){ moonCanvas.requestPaint(); }
                        function onInspectedPhaseIdChanged(){ moonCanvas.requestPaint(); }
                    }
                }
                Column {
                    width: Math.max(0,parent.width-moonCanvas.width-7)
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 2
                    GohuText {
                        width: parent.width
                        text: deck.displayedMoonIllumination<0
                              ? "--" : Math.round(deck.displayedMoonIllumination)+"%"
                        font.pixelSize: 18
                        color: Colors.yellow
                    }
                    QuietText {
                        width: parent.width
                        text: deck.displayedPhaseLabel
                        font.pixelSize: 8
                        elide: Text.ElideRight
                    }
                    QuietText {
                        width: parent.width
                        text: deck.inspectedPhase.valid
                              ? "SCHEMATIC REFERENCE"
                              : deck.moonModel.source
                        font.pixelSize: 8
                        color: deck.inspectedPhase.valid
                               ? Colors.magenta : Colors.cyan
                        elide: Text.ElideRight
                    }
                }
            }
            Row {
                id: phasePresetRow
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.leftMargin: 6
                anchors.rightMargin: 6
                anchors.bottomMargin: 3
                height: 18
                spacing: 2
                Repeater {
                    model: CosmosVisual.PHASES
                    delegate: ActionButton {
                        required property var modelData
                        width: Math.max(1,(phasePresetRow.width
                                         - phasePresetRow.spacing*7)/8)
                        height: 18
                        label: modelData.short
                        labelPixelSize: 8
                        contentPadding: 0
                        selected: deck.inspectedPhaseId !== ""
                                  ? deck.inspectedPhaseId === modelData.id
                                  : deck.moonModel.phaseId === modelData.id
                        accentColor: selected ? Colors.magenta : Colors.cyan
                        // Clicking a selected reference returns to live.
                        onClicked: deck.inspectedPhaseId =
                            deck.inspectedPhaseId === modelData.id ? ""
                            : modelData.id
                    }
                }
            }
        }

        Rectangle {
            id: solarCard
            width: lunarCard.width
            height: instrumentRow.height
            color: Colors.dark
            border.width: 1
            border.color: Colors.orange
            clip: true

            GohuText {
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.leftMargin: 7
                anchors.topMargin: 5
                text: "SUN // DAYLIGHT"
                font.pixelSize: 10
                color: Colors.orange
            }
            ActionButton {
                anchors.top: parent.top
                anchors.right: parent.right
                anchors.topMargin: 4
                anchors.rightMargin: 5
                width: 43
                height: 19
                label: "OPEN"
                labelPixelSize: 8
                accentColor: Colors.orange
                onClicked: deck.routeRequested("magick/planetary/hours")
            }

            Row {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.bottom: solarPresetRow.top
                anchors.leftMargin: 7
                anchors.rightMargin: 7
                anchors.topMargin: 26
                anchors.bottomMargin: 3
                spacing: 6

                Canvas {
                    id: solarCanvas
                    width: Math.max(45,parent.width*0.47)
                    height: parent.height
                    onWidthChanged: requestPaint()
                    onHeightChanged: requestPaint()
                    onPaint: {
                        const ctx=getContext("2d");
                        ctx.clearRect(0,0,width,height);
                        const w=Math.max(1,width-2),h=Math.max(1,height-2);
                        ctx.strokeStyle=String(Colors.cyan);
                        ctx.globalAlpha=0.35;
                        ctx.beginPath();
                        ctx.moveTo(0,h/2);
                        ctx.lineTo(w,h/2);
                        ctx.stroke();
                        ctx.globalAlpha=1;
                        if(!deck.solarModel.ready)return;
                        ctx.strokeStyle=String(Colors.orange);
                        ctx.lineWidth=1.6;
                        ctx.beginPath();
                        const rows=deck.solarModel.rows;
                        for(let i=0;i<rows.length;i++){
                            const x=CosmosVisual.positionX(rows[i].minute,w);
                            const y=CosmosVisual.positionY(rows[i].altitude,h);
                            if(i===0)ctx.moveTo(x,y);
                            else ctx.lineTo(x,y);
                        }
                        ctx.stroke();
                        if(deck.selectedSolarMinute>=0
                           && deck.selectedSolarMinute<1440){
                            const x=CosmosVisual.positionX(
                                deck.selectedSolarMinute,w);
                            ctx.strokeStyle=String(Colors.magenta);
                            ctx.globalAlpha=0.85;
                            ctx.lineWidth=1;
                            ctx.beginPath();
                            ctx.moveTo(x,0);
                            ctx.lineTo(x,h);
                            ctx.stroke();
                        }
                    }
                    Connections {
                        target: deck
                        function onSolarModelChanged(){solarCanvas.requestPaint();}
                        function onSelectedSolarMinuteChanged(){
                            solarCanvas.requestPaint();
                        }
                    }
                    MouseArea {
                        anchors.fill: parent
                        enabled: deck.solarModel.ready
                        hoverEnabled: true
                        preventStealing: true
                        cursorShape: Qt.CrossCursor
                        onPositionChanged: function(mouse) {
                            if(deck.lockedSolarMinute<0)
                                deck.hoveredSolarMinute=Math.max(0,Math.min(1439,
                                    Math.floor(mouse.x/Math.max(1,width)*1439)));
                        }
                        onExited: deck.hoveredSolarMinute=-1
                        onClicked: function(mouse) {
                            deck.lockedSolarMinute=Math.max(0,Math.min(1439,
                                Math.floor(mouse.x/Math.max(1,width)*1439)));
                        }
                    }
                }

                Column {
                    width: Math.max(0,parent.width-solarCanvas.width-6)
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 2
                    GohuText {
                        width: parent.width
                        text: "RISE " + observationOwner.astronomySummary.sunrise
                        font.pixelSize: 8
                        color: Colors.white
                        elide: Text.ElideRight
                    }
                    GohuText {
                        width: parent.width
                        text: "SET  " + observationOwner.astronomySummary.sunset
                        font.pixelSize: 8
                        color: Colors.white
                        elide: Text.ElideRight
                    }
                    QuietText {
                        width: parent.width
                        text: deck.solarCursor
                              ? "MODEL "+CosmosVisual.clockLabel(
                                    deck.solarCursor.minute)+" "
                                +deck.solarCursor.altitude.toFixed(1)+"°"
                              : "SOLAR MODEL // WAITING"
                        color: deck.solarCursor ? Colors.yellow : Colors.orange
                        font.pixelSize: 8
                        elide: Text.ElideRight
                    }
                }
            }
            Row {
                id: solarPresetRow
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.leftMargin: 6
                anchors.rightMargin: 6
                anchors.bottomMargin: 3
                height: 18
                spacing: 2
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
                        height: 18
                        label: modelData.label
                        labelPixelSize: 9
                        contentPadding: 0
                        selected: modelData.minute < 0
                                  ? deck.lockedSolarMinute < 0
                                  : deck.lockedSolarMinute === modelData.minute
                        available: deck.solarModel.ready
                                   && (modelData.minute >= 0
                                       || observationOwner.providerLocalMinute >= 0)
                        accentColor: selected ? Colors.magenta : Colors.cyan
                        onClicked: {
                            deck.lockedSolarMinute=modelData.minute;
                            deck.hoveredSolarMinute=-1;
                        }
                    }
                }
            }
        }
    }
}
