import QtQuick
import "../../components"
import "StationCosmosSolarDetailPolicy.js" as SolarDetails

// C12 // Terminal-first Sun composites. Presentation only: StationSky and
// StationSpace remain the sole owners of all observations and refresh actions.
// The old specialist instruments and complete INDEX reference remain intact.
Rectangle {
    id: sunTerminal
    objectName: "cosmos-c12-sun-terminal"
    color: Colors.black
    clip: true

    property string terminalMode: "live" // observation | live | position | activity
    property var weatherService: null
    property var spaceService: null
    property var skyFeed: null
    property var sourceSpace: null

    readonly property var astronomy: skyFeed ? skyFeed.astronomySummary : null
    readonly property var twilight: skyFeed ? skyFeed.twilightSummary : null
    readonly property var solarFix: skyFeed ? skyFeed.currentSolarPosition : null
    readonly property var xray: sourceSpace ? sourceSpace.xrayObservation : null
    readonly property var flares: sourceSpace ? sourceSpace.flareObservation : null
    readonly property var cycle: sourceSpace ? sourceSpace.cycleObservation : null
    readonly property int flareCount: SolarDetails.flareCount(flares)
    property int selectedFlareIndex: 0
    // One instrument board: keep all source facts visible at once, no
    // X-RAY/FLARE/CYCLE submenu or time/detail/model page switches.
    readonly property var selectedFlare: SolarDetails.flareAt(flares, selectedFlareIndex)
    readonly property var flareFields:
        SolarDetails.flarePage(selectedFlare, 0)
        .concat(SolarDetails.flarePage(selectedFlare, 1))
    readonly property var cycleFields:
        SolarDetails.cyclePage(cycle && cycle.ready ? cycle.summary : null, 0,
                              spaceService ? spaceService.solarFluxText : "")
        .concat(SolarDetails.cyclePage(
            cycle && cycle.ready ? cycle.summary : null, 1,
            spaceService ? spaceService.solarFluxText : ""))
        .concat(SolarDetails.cyclePage(
            cycle && cycle.ready ? cycle.summary : null, 2,
            spaceService ? spaceService.solarFluxText : ""))
    readonly property var xrayFields:
        SolarDetails.xrayPage(xray && xray.ready ? xray : null, 0)
        .concat(SolarDetails.xrayPage(xray && xray.ready ? xray : null, 1))

    readonly property var positionRows: [
        {name:"ASTRONOMICAL DAWN",value:show(twilight ? twilight.astronomicalDawn : null)},
        {name:"CIVIL DAWN",value:show(twilight ? twilight.civilDawn : null)},
        {name:"SOLAR NOON",value:show(twilight ? twilight.solarNoon : null)},
        {name:"CIVIL DUSK",value:show(twilight ? twilight.civilDusk : null)},
        {name:"BLUE // AM",value:interval(twilight ? twilight.blueMorningStart : null,
                                        twilight ? twilight.blueMorningEnd : null)},
        {name:"GOLDEN // AM",value:interval(twilight ? twilight.goldenMorningStart : null,
                                          twilight ? twilight.goldenMorningEnd : null)},
        {name:"GOLDEN // PM",value:interval(twilight ? twilight.goldenEveningStart : null,
                                          twilight ? twilight.goldenEveningEnd : null)},
        {name:"BLUE // PM",value:interval(twilight ? twilight.blueEveningStart : null,
                                        twilight ? twilight.blueEveningEnd : null)}
    ]
    readonly property var positionStrip: [
        {name:"SUNRISE",value:show(astronomy ? astronomy.sunrise : null)},
        {name:"SUNSET",value:show(astronomy ? astronomy.sunset : null)},
        {name:"DAYLIGHT",value:show(astronomy ? astronomy.daylightLabel : null)},
        {name:"ALTITUDE",value:solarFix && solarFix.available
            ? Number(solarFix.altitudeDegrees).toFixed(1)+"°" : "--"},
        {name:"AZIMUTH",value:solarFix && solarFix.available
            ? Number(solarFix.azimuthDegrees).toFixed(1)+"°" : "--"}
    ]

    onFlareCountChanged: {
        if (selectedFlareIndex >= flareCount)
            selectedFlareIndex = Math.max(0,flareCount-1);
    }

    function show(value) {
        return value === null || value === undefined || String(value)===""
            ? "--" : String(value);
    }
    function interval(a,b) {
        return show(a)==="--" || show(b)==="--"
            ? "--" : show(a)+" → "+show(b);
    }
    function reading(raw,digits) {
        return raw !== null && raw !== undefined && raw !== ""
             && isFinite(Number(raw)) ? Number(raw).toFixed(digits) : "--";
    }
    // A single explicit refresh button requests the same three existing
    // NOAA owners. No hidden tab dictates which source is refreshed.
    function updateSource() {
        if (xray && !xray.loading && xray.refresh) xray.refresh();
        if (flares && !flares.loading && flares.refresh) flares.refresh();
        if (cycle && !cycle.loading && cycle.refresh) cycle.refresh(true);
    }

    Loader {
        id: activeTerminal
        objectName: "cosmos-c12-active-board"
        anchors.fill: parent
        sourceComponent: sunTerminal.terminalMode==="observation" ? observationBoard
            : sunTerminal.terminalMode==="position" ? positionBoard
            : sunTerminal.terminalMode==="activity" ? activityBoard : liveBoard
    }

    // POSITION + LIGHT // one interactive graph, one fine-grained twilight
    // ledger, and a lower live sky strip. No nested source or scroll surface.
    Component {
        id: positionBoard
        Item {
            objectName: "cosmos-c12-position-board"
            anchors.fill: parent
            Row {
                id: positionBody
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                height: Math.max(1,parent.height-48)
                spacing: 6

                StationCosmosVisualInstruments {
                    id: solarArc
                    objectName: "cosmos-c12-sun-path-hero"
                    width: Math.max(1,Math.round((positionBody.width-6)*0.61))
                    height: positionBody.height
                    compactMode: true
                    showMoon: false
                    showSun: true
                    astronomySummary: sunTerminal.astronomy
                    twilightSummary: sunTerminal.twilight
                    currentSolarPosition: sunTerminal.solarFix
                    providerLocalMinute: sunTerminal.skyFeed
                        ? sunTerminal.skyFeed.focusedLocalMinute : -1
                    solarDate: sunTerminal.skyFeed
                        ? sunTerminal.skyFeed.focusedCivilDate : ""
                    solarCivilOffsetMinutes: sunTerminal.skyFeed
                        ? sunTerminal.skyFeed.moonCivilOffsetMinutes : null
                    solarOffsetSource: sunTerminal.skyFeed
                        ? sunTerminal.skyFeed.moonCivilOffsetSource : "UNKNOWN"
                    latitude: sunTerminal.weatherService
                        ? sunTerminal.weatherService.latitude : ""
                    longitude: sunTerminal.weatherService
                        ? sunTerminal.weatherService.longitude : ""
                }

                Rectangle {
                    id: twilightLedger
                    objectName: "cosmos-c12-light-ledger"
                    width: Math.max(1,positionBody.width-solarArc.width-positionBody.spacing)
                    height: positionBody.height
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.orange
                    Column {
                        anchors.fill: parent
                        anchors.margins: 4
                        spacing: 1
                        Repeater {
                            model: sunTerminal.positionRows
                            delegate: Item {
                                required property var modelData
                                width: twilightLedger.width-8
                                height: Math.max(1,(twilightLedger.height-9)/8-1)
                                Rectangle {
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    anchors.bottom: parent.bottom
                                    height: 1
                                    opacity: 0.45
                                    color: Colors.orange
                                }
                                QuietText {
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    anchors.top: parent.top
                                    height: 10
                                    text: modelData.name
                                    color: Colors.cyan
                                    font.pixelSize: 8
                                    elide: Text.ElideRight
                                }
                                GohuText {
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    anchors.bottom: parent.bottom
                                    anchors.bottomMargin: 2
                                    height: 11
                                    text: modelData.value
                                    color: Colors.white
                                    font.pixelSize: 10
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }
                }
            }
            Row {
                id: positionBottom
                objectName: "cosmos-c12-position-live-strip"
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: positionBody.bottom
                anchors.topMargin: 5
                anchors.bottom: parent.bottom
                spacing: 4
                Repeater {
                    model: sunTerminal.positionStrip
                    delegate: Rectangle {
                        required property var modelData
                        width: Math.max(1,(positionBottom.width-16)/5)
                        height: positionBottom.height
                        color: Colors.dark
                        border.width: 1
                        border.color: Colors.blue
                        Column {
                            anchors.fill: parent
                            anchors.margins: 3
                            spacing: 3
                            QuietText {
                                width: parent.width
                                text: modelData.name
                                color: Colors.cyan
                                font.pixelSize: 8
                                elide: Text.ElideRight
                            }
                            GohuText {
                                width: parent.width
                                text: modelData.value
                                color: Colors.yellow
                                font.pixelSize: 10
                                elide: Text.ElideRight
                            }
                        }
                    }
                }
            }
        }
    }

    // LIVE // the existing SUVI renderer occupies the hero bay, with GOES
    // X-ray and flare readings beside it and a narrow provenance/status rail.
    Component {
        id: liveBoard
        Item {
            objectName: "cosmos-c12-live-board"
            anchors.fill: parent
            Row {
                id: liveBody
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.right: parent.right
                anchors.bottom: liveFooter.top
                anchors.bottomMargin: 5
                spacing: 6

                StationCosmosSunInstrumentPane {
                    objectName: "cosmos-c12-suvi-hero"
                    width: Math.max(1,Math.round((liveBody.width-6)*0.64))
                    height: liveBody.height
                    modeRoute: "cosmos/sun/suvi"
                    sourceSpace: sunTerminal.sourceSpace
                    spaceService: sunTerminal.spaceService
                }

                Column {
                    id: liveTelemetry
                    objectName: "cosmos-c12-live-telemetry"
                    width: Math.max(1,liveBody.width-6
                        -Math.round((liveBody.width-6)*0.64))
                    height: liveBody.height
                    spacing: 4

                    Rectangle {
                        width: parent.width
                        height: Math.max(1,(liveTelemetry.height-12)*0.35)
                        color: Colors.dark
                        border.width: 1
                        border.color: Colors.yellow
                        Column {
                            anchors.fill: parent
                            anchors.margins: 5
                            spacing: 4
                            QuietText {text:"GOES // X-RAY CLASS";color:Colors.cyan;font.pixelSize:8}
                            GohuText {
                                text: sunTerminal.xray && sunTerminal.xray.ready
                                    ? sunTerminal.show(sunTerminal.xray.classEquivalent.label)
                                    : "--"
                                color: Colors.yellow
                                font.pixelSize: 21
                            }
                            QuietText {
                                width: parent.width
                                text: sunTerminal.xray && sunTerminal.xray.ready
                                    ? sunTerminal.reading(sunTerminal.xray.fluxLong,9)+" W/M²"
                                    : "X-RAY SAMPLE WAITING"
                                font.pixelSize: 8
                                color: Colors.cyan
                                elide: Text.ElideRight
                            }
                        }
                    }
                    Rectangle {
                        width: parent.width
                        height: Math.max(1,(liveTelemetry.height-12)*0.35)
                        color: Colors.dark
                        border.width: 1
                        border.color: Colors.magenta
                        Column {
                            anchors.fill: parent
                            anchors.margins: 5
                            spacing: 4
                            QuietText {text:"LATEST FLARE // GOES";color:Colors.cyan;font.pixelSize:8}
                            GohuText {
                                text: sunTerminal.flares && sunTerminal.flares.latest
                                    ? sunTerminal.show(sunTerminal.flares.latest.classLabel)
                                    : "--"
                                color: Colors.orange
                                font.pixelSize: 21
                            }
                            QuietText {
                                width: parent.width
                                text: sunTerminal.flares && sunTerminal.flares.ready
                                    ? sunTerminal.flares.count24h+" EVENTS / 24H"
                                    : "FLARE FEED WAITING"
                                font.pixelSize: 8
                                color: Colors.cyan
                                elide: Text.ElideRight
                            }
                        }
                    }
                    Item {
                        width: parent.width
                        height: Math.max(1,liveTelemetry.height-12
                            -Math.max(1,(liveTelemetry.height-12)*0.35)*2)
                        Column {
                            anchors.fill: parent
                            spacing: 3
                            QuietText {
                                width: parent.width
                                text: "SOURCE // NOAA SWPC"
                                color: Colors.orange
                                font.pixelSize: 8
                                elide: Text.ElideRight
                            }
                            QuietText {
                                width: parent.width
                                text: sunTerminal.sourceSpace
                                    ? sunTerminal.sourceSpace.solarImageInfo.shortLabel
                                    : "CHANNEL --"
                                color: Colors.white
                                font.pixelSize: 9
                                elide: Text.ElideRight
                            }
                            QuietText {
                                width: parent.width
                                text: "XRS "+(sunTerminal.xray
                                    ? (sunTerminal.xray.loading ? "RECEIVING"
                                        : sunTerminal.xray.ready ? "RECEIVED" : "WAITING")
                                    : "OFFLINE")
                                color: Colors.cyan
                                font.pixelSize: 8
                                elide: Text.ElideRight
                            }
                            QuietText {
                                width: parent.width
                                text: "FLARES "+(sunTerminal.flares
                                    ? (sunTerminal.flares.loading ? "RECEIVING"
                                        : sunTerminal.flares.ready ? "RECEIVED" : "WAITING")
                                    : "OFFLINE")
                                color: Colors.cyan
                                font.pixelSize: 8
                                elide: Text.ElideRight
                            }
                        }
                    }
                }
            }
            QuietText {
                id: liveFooter
                objectName: "cosmos-c12-live-source-line"
                anchors.bottom: parent.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                height: 13
                color: Colors.orange
                font.pixelSize: 8
                elide: Text.ElideRight
                text: "SUVI IMAGE // GOES XRS // 7-DAY FLARES"
                    +"   •   "+(sunTerminal.xray && sunTerminal.xray.ready
                        ? (sunTerminal.xray.sampleFresh ? "XRS CURRENT" : "XRS STALE")
                        : "XRS UNAVAILABLE")
            }
        }
    }

    // OBSERVATION // two large live instruments, then contextual telemetry
    // meters and actual sunrise/twilight timings. No fake motion or scrolling.
    Component {
        id: observationBoard
        Item {
            id: observation
            objectName: "cosmos-c14-observation-board"
            anchors.fill: parent
            readonly property bool roomy: width >= 620 && height >= 330
            readonly property int labelSize: roomy ? 10 : 8
            readonly property int textSize: roomy ? 13 : 10
            readonly property int bottomHeight: Math.max(1,Math.round(height*0.40))
            readonly property var space: sunTerminal.spaceService
            readonly property var highlights: [
                {name:"BLUE // AM",value:sunTerminal.interval(
                    sunTerminal.twilight ? sunTerminal.twilight.blueMorningStart : null,
                    sunTerminal.twilight ? sunTerminal.twilight.blueMorningEnd : null),
                 tint:Colors.cyan},
                {name:"GOLDEN // AM",value:sunTerminal.interval(
                    sunTerminal.twilight ? sunTerminal.twilight.goldenMorningStart : null,
                    sunTerminal.twilight ? sunTerminal.twilight.goldenMorningEnd : null),
                 tint:Colors.yellow},
                {name:"GOLDEN // PM",value:sunTerminal.interval(
                    sunTerminal.twilight ? sunTerminal.twilight.goldenEveningStart : null,
                    sunTerminal.twilight ? sunTerminal.twilight.goldenEveningEnd : null),
                 tint:Colors.yellow},
                {name:"BLUE // PM",value:sunTerminal.interval(
                    sunTerminal.twilight ? sunTerminal.twilight.blueEveningStart : null,
                    sunTerminal.twilight ? sunTerminal.twilight.blueEveningEnd : null),
                 tint:Colors.cyan}
            ]
            readonly property var contextMeters: [
                {name:"KP / 9",value:space && space.kpReady
                    ? sunTerminal.reading(space.kp,1) : "--",
                 frac:space && space.kpReady
                    ? Math.max(0,Math.min(1,Number(space.kp)/9)) : 0,
                 tint:Colors.cyan},
                {name:"WIND / 1000",value:space && space.solarWindReady
                    ? sunTerminal.reading(space.solarWindSpeed,0)+" KM/S" : "--",
                 frac:space && space.solarWindReady
                    ? Math.max(0,Math.min(1,Number(space.solarWindSpeed)/1000)) : 0,
                 tint:Colors.yellow},
                {name:"BZ / ±20NT",value:space && space.magneticFieldReady
                    ? sunTerminal.reading(space.magneticFieldBz,1)+" NT" : "--",
                 frac:space && space.magneticFieldReady
                    ? Math.max(0,Math.min(1,Math.abs(Number(space.magneticFieldBz))/20)) : 0,
                 tint:space && space.magneticFieldReady
                    && Number(space.magneticFieldBz)<0 ? Colors.magenta : Colors.orange}
            ]

            Row {
                id: observationHeroes
                objectName: "cosmos-c14-observation-heroes"
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                height: Math.max(1,observation.height-observation.bottomHeight-5)
                spacing: 5
                StationCosmosSunInstrumentPane {
                    objectName: "cosmos-c14-suvi-hero"
                    width: Math.max(1,Math.round((observationHeroes.width-5)*0.53))
                    height: observationHeroes.height
                    modeRoute: "cosmos/sun/suvi"
                    sourceSpace: sunTerminal.sourceSpace
                    spaceService: sunTerminal.spaceService
                }
                StationCosmosVisualInstruments {
                    objectName: "cosmos-c14-sun-path-hero"
                    width: Math.max(1,observationHeroes.width-5
                        -Math.round((observationHeroes.width-5)*0.53))
                    height: observationHeroes.height
                    compactMode: true
                    showMoon: false
                    showSun: true
                    astronomySummary: sunTerminal.astronomy
                    twilightSummary: sunTerminal.twilight
                    currentSolarPosition: sunTerminal.solarFix
                    providerLocalMinute: sunTerminal.skyFeed
                        ? sunTerminal.skyFeed.focusedLocalMinute : -1
                    solarDate: sunTerminal.skyFeed
                        ? sunTerminal.skyFeed.focusedCivilDate : ""
                    solarCivilOffsetMinutes: sunTerminal.skyFeed
                        ? sunTerminal.skyFeed.moonCivilOffsetMinutes : null
                    solarOffsetSource: sunTerminal.skyFeed
                        ? sunTerminal.skyFeed.moonCivilOffsetSource : "UNKNOWN"
                    latitude: sunTerminal.weatherService
                        ? sunTerminal.weatherService.latitude : ""
                    longitude: sunTerminal.weatherService
                        ? sunTerminal.weatherService.longitude : ""
                }
            }
            Row {
                id: observationDashboard
                objectName: "cosmos-c15-relationships-deck"
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: observationHeroes.bottom
                anchors.topMargin: 5
                anchors.bottom: parent.bottom
                spacing: 5
                Column {
                    id: observationLeft
                    width: Math.max(1,Math.round((observationDashboard.width-5)*0.53))
                    height: observationDashboard.height
                    spacing: 3
                    Rectangle {
                        id: observationLive
                        objectName: "cosmos-c14-live-telemetry"
                        width: parent.width
                        height: Math.max(1,Math.round((observationLeft.height-3)*0.46))
                        color: Colors.dark
                        border.width: 1
                        border.color: Colors.magenta
                        clip: true
                        QuietText {
                            id: goestitle
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: 3
                            height: observation.roomy ? 16 : 12
                            text: "GOES // ACTIVE X-RAY + OBSERVED FLARES"
                            font.pixelSize: observation.labelSize
                            color: Colors.cyan
                            elide: Text.ElideRight
                        }
                        Row {
                            id: goesReadout
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: goestitle.bottom
                            anchors.bottom: parent.bottom
                            anchors.margins: 3
                            spacing: 5
                            GohuText {
                                width: Math.max(1,goesReadout.width*0.31)
                                font.pixelSize: observation.roomy ? 25 : 18
                                text: sunTerminal.xray && sunTerminal.xray.ready
                                    ? sunTerminal.show(sunTerminal.xray.classEquivalent.label) : "--"
                                color: Colors.yellow
                                elide: Text.ElideRight
                            }
                            Column {
                                width: Math.max(1,goesReadout.width*0.69-5)
                                spacing: 1
                                GohuText {
                                    width: parent.width
                                    font.pixelSize: observation.textSize
                                    text: "FLARE "+(sunTerminal.flares && sunTerminal.flares.latest
                                        ? sunTerminal.show(sunTerminal.flares.latest.classLabel) : "--")
                                    color: Colors.orange
                                    elide: Text.ElideRight
                                }
                                QuietText {
                                    width: parent.width
                                    font.pixelSize: observation.labelSize
                                    color: Colors.cyan
                                    text: sunTerminal.flares && sunTerminal.flares.ready
                                        ? sunTerminal.flares.count24h+" EVENTS / 24H"
                                        : "FLARE SOURCE WAITING"
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }
                    Rectangle {
                        id: spaceContext
                        objectName: "cosmos-c15-space-context-meters"
                        width: parent.width
                        height: Math.max(1,observationLeft.height-observationLive.height-3)
                        color: Colors.dark
                        border.width: 1
                        border.color: Colors.cyan
                        clip: true
                        QuietText {
                            id: spaceContextTitle
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: 2
                            height: observation.roomy ? 17 : 11
                            color: Colors.orange
                            font.pixelSize: observation.labelSize
                            text: "SOLAR WIND // GEOMAGNETIC CONTEXT"
                            elide: Text.ElideRight
                        }
                        Row {
                            id: meterRack
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: spaceContextTitle.bottom
                            anchors.bottom: parent.bottom
                            anchors.margins: 2
                            spacing: 3
                            Repeater {
                                model: observation.contextMeters
                                delegate: Column {
                                    required property var modelData
                                    width: Math.max(1,(meterRack.width-6)/3)
                                    spacing: 2
                                    QuietText {
                                        width: parent.width
                                        text: modelData.name
                                        color: Colors.cyan
                                        font.pixelSize: observation.labelSize
                                        elide: Text.ElideRight
                                    }
                                    GohuText {
                                        width: parent.width
                                        text: modelData.value
                                        color: modelData.tint
                                        font.pixelSize: observation.textSize
                                        elide: Text.ElideRight
                                    }
                                    Item {
                                        width: parent.width
                                        height: observation.roomy ? 9 : 5
                                        Rectangle {
                                            anchors.fill: parent
                                            color: Colors.black
                                            border.width: 1
                                            border.color: Colors.blue
                                        }
                                        Rectangle {
                                            height: parent.height
                                            width: parent.width*modelData.frac
                                            color: modelData.tint
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                Column {
                    id: observationRight
                    width: Math.max(1,observationDashboard.width-observationLeft.width-5)
                    height: observationDashboard.height
                    spacing: 3
                    Rectangle {
                        id: observationSky
                        objectName: "cosmos-c14-position-live-strip"
                        width: parent.width
                        height: Math.max(1,Math.round((observationRight.height-3)*0.39))
                        color: Colors.dark
                        border.width: 1
                        border.color: Colors.blue
                        clip: true
                        QuietText {
                            id: dayTitle
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: 2
                            height: observation.roomy ? 17 : 12
                            font.pixelSize: observation.labelSize
                            color: Colors.cyan
                            text: "DAYLIGHT // SUNRISE → NOON → SUNSET"
                            elide: Text.ElideRight
                        }
                        Row {
                            id: skyTimeline
                            objectName: "cosmos-c15-daylight-timeline"
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: dayTitle.bottom
                            anchors.bottom: parent.bottom
                            anchors.margins: 2
                            spacing: 2
                            Repeater {
                                model: [
                                    {label:"RISE",value:sunTerminal.show(sunTerminal.astronomy
                                        ? sunTerminal.astronomy.sunrise : null)},
                                    {label:"NOON",value:sunTerminal.show(sunTerminal.twilight
                                        ? sunTerminal.twilight.solarNoon : null)},
                                    {label:"SET",value:sunTerminal.show(sunTerminal.astronomy
                                        ? sunTerminal.astronomy.sunset : null)}
                                ]
                                delegate: Column {
                                    required property var modelData
                                    width: Math.max(1,(skyTimeline.width-4)/3)
                                    spacing: 0
                                    QuietText {
                                        width: parent.width
                                        font.pixelSize: observation.labelSize
                                        color: Colors.orange
                                        text: modelData.label
                                        elide: Text.ElideRight
                                    }
                                    GohuText {
                                        width: parent.width
                                        font.pixelSize: observation.textSize
                                        color: Colors.white
                                        text: modelData.value
                                        elide: Text.ElideRight
                                    }
                                }
                            }
                        }
                    }
                    Rectangle {
                        id: observationLight
                        objectName: "cosmos-c14-twilight-ledger"
                        width: parent.width
                        height: Math.max(1,observationRight.height-observationSky.height-3)
                        color: Colors.dark
                        border.width: 1
                        border.color: Colors.orange
                        clip: true
                        QuietText {
                            id: twilightTitle
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: 2
                            height: observation.roomy ? 16 : 11
                            color: Colors.orange
                            font.pixelSize: observation.labelSize
                            text: "TWILIGHT // BLUE + GOLDEN HOURS"
                            elide: Text.ElideRight
                        }
                        Grid {
                            id: twilightGroups
                            objectName: "cosmos-c15-twilight-groups"
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: twilightTitle.bottom
                            anchors.bottom: parent.bottom
                            anchors.margins: 2
                            columns: 2
                            spacing: 1
                            Repeater {
                                model: observation.roomy ? sunTerminal.positionRows
                                    : observation.highlights
                                delegate: Item {
                                    required property var modelData
                                    width: Math.max(1,(twilightGroups.width-1)/2)
                                    height: Math.max(1,(twilightGroups.height
                                        -(observation.roomy ? 3 : 1))
                                        /(observation.roomy ? 4 : 2))
                                    Column {
                                        anchors.fill: parent
                                        spacing: 0
                                        QuietText {
                                            width: parent.width
                                            color: modelData.tint || Colors.cyan
                                            font.pixelSize: observation.labelSize
                                            text: modelData.name
                                            elide: Text.ElideRight
                                        }
                                        GohuText {
                                            width: parent.width
                                            color: Colors.white
                                            font.pixelSize: observation.roomy ? 11 : 8
                                            text: modelData.value
                                            elide: Text.ElideRight
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // ACTIVITY // Different physical quantities deserve different shapes.
    // X-ray time samples are a large graph; flare data is an event inspector;
    // monthly cycle predictions are bounded model ranges, not live bars.
    Component {
        id: activityBoard
        Item {
            id: allActivity
            objectName: "cosmos-c13-activity-board"
            anchors.fill: parent
            readonly property bool roomy: width >= 620 && height >= 330
            readonly property int tiny: roomy ? 10 : 8
            readonly property int valueFont: roomy ? 14 : 10
            readonly property var model: sunTerminal.cycle && sunTerminal.cycle.ready
                ? sunTerminal.cycle.summary : null
            readonly property real ssnLimit: model
                ? Math.max(1,Math.max(Number(model.highSsn)||0,
                                      Number(model.predictedSsn)||0)*1.1) : 1
            readonly property real fluxLimit: model
                ? Math.max(1,Math.max(Number(model.highFlux)||0,
                                      Number(model.predictedFlux)||0)*1.1) : 1
            readonly property real ssnLow: model && model.ssnRangeValid
                ? Math.max(0,Number(model.lowSsn)||0) : 0
            readonly property real ssnHigh: model && model.ssnRangeValid
                ? Math.max(0,Number(model.highSsn)||0) : 0
            readonly property real fluxLow: model && model.fluxRangeValid
                ? Math.max(0,Number(model.lowFlux)||0) : 0
            readonly property real fluxHigh: model && model.fluxRangeValid
                ? Math.max(0,Number(model.highFlux)||0) : 0

            Row {
                id: activityInstruments
                objectName: "cosmos-c13-simultaneous-instruments"
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.bottom: cycleBay.top
                anchors.bottomMargin: 5
                spacing: 5

                Rectangle {
                    id: xrayBay
                    objectName: "cosmos-c13-xray-bay"
                    width: Math.max(1,Math.round((activityInstruments.width-5)*0.60))
                    height: activityInstruments.height
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.cyan
                    clip: true
                    Row {
                        id: xrayHeader
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: 3
                        height: allActivity.roomy ? 25 : 19
                        spacing: 3
                        QuietText {
                            width: Math.max(1,xrayHeader.width-66)
                            height: parent.height
                            text: "GOES XRS // HISTORY"
                            color: Colors.cyan
                            font.pixelSize: allActivity.tiny
                            verticalAlignment: Text.AlignVCenter
                            elide: Text.ElideRight
                        }
                        ActionButton {
                            width: 62
                            height: parent.height
                            label: "REFRESH"
                            labelPixelSize: 8
                            contentPadding: 1
                            accentColor: Colors.cyan
                            onClicked: sunTerminal.updateSource()
                        }
                    }
                    Row {
                        id: xrayReadout
                        objectName: "cosmos-c12-activity-metrics"
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: xrayHeader.bottom
                        anchors.leftMargin: 4
                        anchors.rightMargin: 4
                        height: allActivity.roomy ? 54 : 39
                        spacing: 5
                        GohuText {
                            width: Math.max(1,xrayReadout.width*0.32)
                            height: parent.height
                            font.pixelSize: allActivity.roomy ? 29 : 23
                            color: Colors.yellow
                            verticalAlignment: Text.AlignVCenter
                            text: sunTerminal.xray && sunTerminal.xray.ready
                                ? sunTerminal.show(sunTerminal.xray.classEquivalent.label) : "--"
                            elide: Text.ElideRight
                        }
                        Column {
                            width: Math.max(1,xrayReadout.width*0.68-5)
                            height: parent.height
                            spacing: 1
                            QuietText {
                                width: parent.width
                                color: Colors.cyan
                                font.pixelSize: allActivity.tiny
                                text: "0.1–0.8 NM // LONG BAND"
                                elide: Text.ElideRight
                            }
                            GohuText {
                                width: parent.width
                                font.pixelSize: allActivity.valueFont
                                color: Colors.white
                                text: sunTerminal.xray && sunTerminal.xray.ready
                                    ? sunTerminal.reading(sunTerminal.xray.fluxLong,9)+" W/M²" : "--"
                                elide: Text.ElideRight
                            }
                            QuietText {
                                width: parent.width
                                color: Colors.magenta
                                font.pixelSize: allActivity.tiny
                                text: "SHORT "+(sunTerminal.xray && sunTerminal.xray.ready
                                    ? sunTerminal.reading(sunTerminal.xray.fluxShort,9) : "--")
                                elide: Text.ElideRight
                            }
                        }
                    }
                    Rectangle {
                        id: xrayGraph
                        objectName: "cosmos-c13-xray-graph"
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: xrayReadout.bottom
                        anchors.bottom: xrayFooter.top
                        anchors.margins: 3
                        color: Colors.black
                        border.width: 1
                        border.color: Colors.blue
                        clip: true
                        Row {
                            id: xrayTrend
                            objectName: "cosmos-c12-xray-trend"
                            anchors.fill: parent
                            anchors.margins: 3
                            spacing: 2
                            Repeater {
                                model: sunTerminal.xray && sunTerminal.xray.ready
                                    ? sunTerminal.xray.trend : []
                                delegate: Item {
                                    required property var modelData
                                    width: Math.max(1,(xrayTrend.width-22)/12)
                                    height: xrayTrend.height
                                    Rectangle {
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.bottom: parent.bottom
                                        height: Math.max(2,(parent.height-2)*Math.max(0,
                                            Math.min(1,Number(modelData.level)||0)))
                                        color: modelData.classLetter==="X" ? Colors.magenta
                                            : modelData.classLetter==="M" ? Colors.orange
                                            : modelData.classLetter==="C" ? Colors.yellow : Colors.cyan
                                    }
                                }
                            }
                        }
                    }
                    QuietText {
                        id: xrayFooter
                        objectName: "cosmos-c12-xray-facts"
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        anchors.margins: 4
                        height: allActivity.roomy ? 18 : 13
                        font.pixelSize: allActivity.tiny
                        color: Colors.cyan
                        elide: Text.ElideRight
                        text: (sunTerminal.xray && sunTerminal.xray.ready
                            ? sunTerminal.show(sunTerminal.xray.satellite)
                                +" // "+sunTerminal.show(sunTerminal.xray.sampleUtc)
                                +" // "+(sunTerminal.xray.sampleFresh?"CURRENT":"STALE")
                            : "NOAA XRS // WAITING")
                    }
                }

                Rectangle {
                    id: flareBay
                    objectName: "cosmos-c13-flare-bay"
                    width: Math.max(1,activityInstruments.width-xrayBay.width-5)
                    height: activityInstruments.height
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.magenta
                    clip: true
                    Row {
                        id: flareHeading
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: 3
                        height: allActivity.roomy ? 25 : 19
                        spacing: 3
                        QuietText {
                            width: Math.max(1,flareHeading.width-50)
                            height: parent.height
                            text: "FLARES // EVENTS"
                            color: Colors.magenta
                            font.pixelSize: allActivity.tiny
                            verticalAlignment: Text.AlignVCenter
                            elide: Text.ElideRight
                        }
                        ActionButton {
                            width: 21; height: parent.height
                            label: "‹"; labelPixelSize: 14; contentPadding: 1
                            available: sunTerminal.flareCount>1
                            accentColor: Colors.magenta
                            onClicked: sunTerminal.selectedFlareIndex =
                                (sunTerminal.selectedFlareIndex-1+sunTerminal.flareCount)
                                    %sunTerminal.flareCount
                        }
                        ActionButton {
                            width: 21; height: parent.height
                            label: "›"; labelPixelSize: 14; contentPadding: 1
                            available: sunTerminal.flareCount>1
                            accentColor: Colors.magenta
                            onClicked: sunTerminal.selectedFlareIndex =
                                (sunTerminal.selectedFlareIndex+1)%sunTerminal.flareCount
                        }
                    }
                    Column {
                        id: flareFacts
                        objectName: "cosmos-c12-flare-facts"
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: flareHeading.bottom
                        anchors.bottom: parent.bottom
                        anchors.margins: 4
                        spacing: allActivity.roomy ? 5 : 2
                        GohuText {
                            width: parent.width
                            font.pixelSize: allActivity.roomy ? 32 : 25
                            color: Colors.yellow
                            text: sunTerminal.selectedFlare
                                ? sunTerminal.show(sunTerminal.selectedFlare.classLabel) : "--"
                            elide: Text.ElideRight
                        }
                        QuietText {
                            width: parent.width
                            color: Colors.cyan
                            font.pixelSize: allActivity.tiny
                            text: sunTerminal.flareCount
                                ? "EVENT "+(sunTerminal.selectedFlareIndex+1)+"/"
                                    +sunTerminal.flareCount
                                    +" // "+sunTerminal.show(sunTerminal.selectedFlare.satellite)
                                : "NO OBSERVED EVENTS"
                            elide: Text.ElideRight
                        }
                        QuietText {
                            width: parent.width
                            color: Colors.white
                            font.pixelSize: allActivity.tiny
                            text: "BEGIN  "+sunTerminal.show(sunTerminal.selectedFlare
                                ? sunTerminal.selectedFlare.beginUtc : null)
                            elide: Text.ElideRight
                        }
                        QuietText {
                            width: parent.width
                            color: Colors.orange
                            font.pixelSize: allActivity.tiny
                            text: "PEAK   "+sunTerminal.show(sunTerminal.selectedFlare
                                ? sunTerminal.selectedFlare.peakUtc : null)
                            elide: Text.ElideRight
                        }
                        QuietText {
                            width: parent.width
                            color: Colors.white
                            font.pixelSize: allActivity.tiny
                            text: "END    "+sunTerminal.show(sunTerminal.selectedFlare
                                ? sunTerminal.selectedFlare.endUtc : null)
                            elide: Text.ElideRight
                        }
                        QuietText {
                            width: parent.width
                            color: Colors.cyan
                            font.pixelSize: allActivity.tiny
                            text: sunTerminal.selectedFlare
                                ? sunTerminal.reading(sunTerminal.selectedFlare.flux,9)
                                    +" W/M² // OBSERVED" : "GOES // WAITING"
                            elide: Text.ElideRight
                        }
                    }
                }
            }

            Rectangle {
                id: cycleBay
                objectName: "cosmos-c13-cycle-bay"
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: activityNote.top
                anchors.bottomMargin: 3
                height: Math.max(1,Math.round(allActivity.height*(allActivity.roomy ? 0.35 : 0.34)))
                color: Colors.dark
                border.width: 1
                border.color: Colors.yellow
                clip: true
                QuietText {
                    id: cycleHeader
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 3
                    height: allActivity.roomy ? 18 : 14
                    font.pixelSize: allActivity.tiny
                    text: "SOLAR CYCLE // MONTHLY MODEL + RANGES // NOT LIVE"
                    color: Colors.orange
                    elide: Text.ElideRight
                }
                Row {
                    id: cycleSummary
                    objectName: "cosmos-c12-cycle-facts"
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: cycleHeader.bottom
                    anchors.bottom: parent.bottom
                    anchors.margins: 3
                    spacing: 5
                    Column {
                        width: Math.max(1,cycleSummary.width*0.23)
                        spacing: 2
                        QuietText {
                            width: parent.width
                            font.pixelSize: allActivity.tiny
                            color: Colors.cyan
                            text: "PREDICTED SSN"
                            elide: Text.ElideRight
                        }
                        GohuText {
                            width: parent.width
                            font.pixelSize: allActivity.roomy ? 26 : 20
                            color: Colors.yellow
                            text: allActivity.model
                                ? sunTerminal.reading(allActivity.model.predictedSsn,1) : "--"
                            elide: Text.ElideRight
                        }
                        QuietText {
                            width: parent.width
                            font.pixelSize: allActivity.tiny
                            color: Colors.white
                            text: allActivity.model
                                ? sunTerminal.reading(allActivity.model.predictedFlux,1)+" SFU"
                                : "-- SFU"
                            elide: Text.ElideRight
                        }
                    }
                    Column {
                        id: cycleRanges
                        objectName: "cosmos-c15-cycle-range-chart"
                        width: Math.max(1,cycleSummary.width*0.52)
                        spacing: allActivity.roomy ? 8 : 3
                        QuietText {
                            width: parent.width
                            color: Colors.cyan
                            font.pixelSize: allActivity.tiny
                            text: "SUNSPOT RANGE  "+(allActivity.model && allActivity.model.ssnRangeValid
                                ? sunTerminal.reading(allActivity.ssnLow,1)+"–"
                                    +sunTerminal.reading(allActivity.ssnHigh,1) : "--")
                            elide: Text.ElideRight
                        }
                        Item {
                            id: ssnTrack
                            width: parent.width
                            height: allActivity.roomy ? 11 : 7
                            Rectangle { anchors.fill: parent; color: Colors.black; border.color: Colors.blue; border.width: 1 }
                            Rectangle {
                                visible: !!allActivity.model && allActivity.model.ssnRangeValid
                                x: Math.max(0,ssnTrack.width*allActivity.ssnLow/allActivity.ssnLimit)
                                width: Math.max(1,ssnTrack.width*
                                    (allActivity.ssnHigh-allActivity.ssnLow)/allActivity.ssnLimit)
                                height: parent.height
                                color: Colors.cyan
                            }
                            Rectangle {
                                visible: !!allActivity.model
                                x: Math.max(0,Math.min(ssnTrack.width-2,ssnTrack.width*
                                    Number(allActivity.model ? allActivity.model.predictedSsn : 0)
                                    /allActivity.ssnLimit))
                                width: 2
                                height: parent.height
                                color: Colors.yellow
                            }
                        }
                        QuietText {
                            width: parent.width
                            color: Colors.orange
                            font.pixelSize: allActivity.tiny
                            text: "F10.7 RANGE  "+(allActivity.model && allActivity.model.fluxRangeValid
                                ? sunTerminal.reading(allActivity.fluxLow,1)+"–"
                                    +sunTerminal.reading(allActivity.fluxHigh,1)+" SFU" : "--")
                            elide: Text.ElideRight
                        }
                        Item {
                            id: fluxTrack
                            width: parent.width
                            height: allActivity.roomy ? 11 : 7
                            Rectangle { anchors.fill: parent; color: Colors.black; border.color: Colors.blue; border.width: 1 }
                            Rectangle {
                                visible: !!allActivity.model && allActivity.model.fluxRangeValid
                                x: Math.max(0,fluxTrack.width*allActivity.fluxLow/allActivity.fluxLimit)
                                width: Math.max(1,fluxTrack.width*
                                    (allActivity.fluxHigh-allActivity.fluxLow)/allActivity.fluxLimit)
                                height: parent.height
                                color: Colors.orange
                            }
                            Rectangle {
                                visible: !!allActivity.model
                                x: Math.max(0,Math.min(fluxTrack.width-2,fluxTrack.width*
                                    Number(allActivity.model ? allActivity.model.predictedFlux : 0)
                                    /allActivity.fluxLimit))
                                width: 2
                                height: parent.height
                                color: Colors.yellow
                            }
                        }
                    }
                    Column {
                        width: Math.max(1,cycleSummary.width*0.25-10)
                        spacing: allActivity.roomy ? 6 : 3
                        QuietText {
                            width: parent.width
                            color: Colors.cyan
                            font.pixelSize: allActivity.tiny
                            text: "MODEL "+sunTerminal.show(allActivity.model
                                ? allActivity.model.modelMonth : null)
                            elide: Text.ElideRight
                        }
                        QuietText {
                            width: parent.width
                            color: Colors.white
                            font.pixelSize: allActivity.tiny
                            text: "NEXT "+sunTerminal.show(allActivity.model
                                ? allActivity.model.nextMonth : null)
                            elide: Text.ElideRight
                        }
                        QuietText {
                            width: parent.width
                            color: Colors.yellow
                            font.pixelSize: allActivity.tiny
                            text: "PEAK "+sunTerminal.show(allActivity.model
                                ? allActivity.model.peakMonth : null)
                            elide: Text.ElideRight
                        }
                        QuietText {
                            width: parent.width
                            color: Colors.orange
                            font.pixelSize: allActivity.tiny
                            text: "SSN "+sunTerminal.reading(allActivity.model
                                ? allActivity.model.peakPredictedSsn : null,1)
                            elide: Text.ElideRight
                        }
                    }
                }
            }
            QuietText {
                id: activityNote
                anchors.bottom: parent.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                height: 11
                font.pixelSize: 8
                color: Colors.orange
                elide: Text.ElideRight
                text: "GOES XRS "+(sunTerminal.xray && sunTerminal.xray.ready
                    ? (sunTerminal.xray.sampleFresh ? "CURRENT" : "STALE")
                    : "UNAVAILABLE")+" // OBSERVED FLARES // NOAA MONTHLY MODEL"
            }
        }
    }
}
