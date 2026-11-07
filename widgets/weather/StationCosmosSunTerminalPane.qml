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

    // OBSERVATION // keep live image and solar arc as large, simultaneous
    // instruments. The related telemetry, position and twilight readings
    // occupy three fixed lower lanes; this panel never scrolls.
    Component {
        id: observationBoard
        Item {
            id: observation
            objectName: "cosmos-c14-observation-board"
            anchors.fill: parent
            readonly property bool roomy: width >= 620 && height >= 330
            readonly property int captionSize: roomy ? 10 : 8
            readonly property int readingSize: roomy ? 14 : 9
            readonly property int liveRowHeight: roomy ? 40 : 23
            readonly property int skyRowHeight: roomy ? 44 : 25
            readonly property int lightRowHeight: roomy ? 78 : 50
            readonly property var liveReadings: [
                {name:"X-RAY // GOES",value:sunTerminal.xray && sunTerminal.xray.ready
                    ? sunTerminal.show(sunTerminal.xray.classEquivalent.label) : "--",
                 border:Colors.yellow},
                {name:"FLARES // 24H",value:sunTerminal.flares && sunTerminal.flares.ready
                    ? sunTerminal.flares.count24h+" EVENTS" : "--",
                 border:Colors.magenta},
                {name:"SUVI CHANNEL",value:sunTerminal.sourceSpace
                    ? sunTerminal.sourceSpace.solarImageInfo.shortLabel : "--",
                 border:Colors.cyan},
                {name:"XRS STATUS",value:sunTerminal.xray && sunTerminal.xray.ready
                    ? (sunTerminal.xray.sampleFresh ? "CURRENT" : "STALE") : "WAITING",
                 border:Colors.blue}
            ]

            Row {
                id: observationHeroes
                objectName: "cosmos-c14-observation-heroes"
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                height: Math.max(1,observation.height-observation.liveRowHeight
                    -observation.skyRowHeight-observation.lightRowHeight-13)
                spacing: 5

                StationCosmosSunInstrumentPane {
                    objectName: "cosmos-c14-suvi-hero"
                    width: Math.max(1,Math.round((observationHeroes.width-5)*0.52))
                    height: observationHeroes.height
                    modeRoute: "cosmos/sun/suvi"
                    sourceSpace: sunTerminal.sourceSpace
                    spaceService: sunTerminal.spaceService
                }
                StationCosmosVisualInstruments {
                    objectName: "cosmos-c14-sun-path-hero"
                    width: Math.max(1,observationHeroes.width-5
                        -Math.round((observationHeroes.width-5)*0.52))
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
                id: observationLive
                objectName: "cosmos-c14-live-telemetry"
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: observationHeroes.bottom
                anchors.topMargin: 3
                height: observation.liveRowHeight
                spacing: 3
                Repeater {
                    model: observation.liveReadings
                    delegate: Rectangle {
                        required property var modelData
                        width: Math.max(1,(observationLive.width-9)/4)
                        height: observationLive.height
                        color: Colors.dark
                        border.width: 1
                        border.color: modelData.border
                        Column {
                            anchors.fill: parent
                            anchors.margins: 2
                            spacing: 1
                            QuietText {
                                width: parent.width
                                text: modelData.name
                                color: modelData.border
                                font.pixelSize: observation.captionSize
                                elide: Text.ElideRight
                            }
                            GohuText {
                                width: parent.width
                                text: modelData.value
                                color: Colors.white
                                font.pixelSize: observation.readingSize
                                elide: Text.ElideRight
                            }
                        }
                    }
                }
            }

            Row {
                id: observationSky
                objectName: "cosmos-c14-position-live-strip"
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: observationLive.bottom
                anchors.topMargin: 3
                height: observation.skyRowHeight
                spacing: 3
                Repeater {
                    model: sunTerminal.positionStrip
                    delegate: Rectangle {
                        required property var modelData
                        width: Math.max(1,(observationSky.width-12)/5)
                        height: observationSky.height
                        color: Colors.dark
                        border.width: 1
                        border.color: Colors.blue
                        Column {
                            anchors.fill: parent
                            anchors.margins: 2
                            spacing: 1
                            QuietText {
                                width: parent.width
                                text: modelData.name
                                color: Colors.cyan
                                font.pixelSize: observation.captionSize
                                elide: Text.ElideRight
                            }
                            GohuText {
                                width: parent.width
                                text: modelData.value
                                color: Colors.yellow
                                font.pixelSize: observation.readingSize
                                elide: Text.ElideRight
                            }
                        }
                    }
                }
            }
            Grid {
                id: observationLight
                objectName: "cosmos-c14-twilight-ledger"
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: observationSky.bottom
                anchors.topMargin: 3
                anchors.bottom: parent.bottom
                columns: 4
                spacing: 3
                Repeater {
                    model: sunTerminal.positionRows
                    delegate: Rectangle {
                        required property var modelData
                        width: Math.max(1,(observationLight.width-9)/4)
                        height: Math.max(1,(observationLight.height-3)/2)
                        color: Colors.dark
                        border.width: 1
                        border.color: Colors.orange
                        Column {
                            anchors.fill: parent
                            anchors.margins: 2
                            spacing: 1
                            QuietText {
                                width: parent.width
                                text: modelData.name
                                color: Colors.cyan
                                font.pixelSize: observation.captionSize
                                elide: Text.ElideRight
                            }
                            GohuText {
                                width: parent.width
                                text: modelData.value
                                color: Colors.white
                                font.pixelSize: observation.readingSize
                                elide: Text.ElideRight
                            }
                        }
                    }
                }
            }
        }
    }

    // ACTIVITY // X-RAY, FLARES and SOLAR CYCLE share one fixed viewport.
    // The large history graph and two compact fact ledgers are simultaneous;
    // only PREV/NEXT changes which observed flare occupies the event card.
    Component {
        id: activityBoard
        Item {
            id: allActivity
            objectName: "cosmos-c13-activity-board"
            anchors.fill: parent
            readonly property bool roomy: width >= 620 && height >= 330
            readonly property int smallText: roomy ? 10 : 8
            readonly property int valueText: roomy ? 12 : 9

            Row {
                id: activityMetrics
                objectName: "cosmos-c12-activity-metrics"
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                height: allActivity.roomy ? 66 : 52
                spacing: 4
                Repeater {
                    model: [
                        {label:"X-RAY // CLASS",value:sunTerminal.xray && sunTerminal.xray.ready
                            ? sunTerminal.show(sunTerminal.xray.classEquivalent.label) : "--",
                         note:"GOES XRS",color:Colors.cyan,weight:0.30},
                        {label:"FLARE // PEAK",value:sunTerminal.flares && sunTerminal.flares.latest
                            ? sunTerminal.show(sunTerminal.flares.latest.classLabel) : "--",
                         note:sunTerminal.flares && sunTerminal.flares.ready
                            ? sunTerminal.flares.count24h+" / 24H" : "WAITING",
                         color:Colors.magenta,weight:0.30},
                        {label:"CYCLE // SSN",value:sunTerminal.cycle && sunTerminal.cycle.ready
                            ? sunTerminal.reading(sunTerminal.cycle.summary.predictedSsn,1) : "--",
                         note:"PREDICTED",color:Colors.yellow,weight:0.20},
                        {label:"F10.7 // SFU",value:sunTerminal.cycle && sunTerminal.cycle.ready
                            ? sunTerminal.reading(sunTerminal.cycle.summary.predictedFlux,1) : "--",
                         note:"PREDICTED",color:Colors.orange,weight:0.20}
                    ]
                    delegate: Rectangle {
                        required property var modelData
                        width: Math.max(1,(activityMetrics.width-12)*modelData.weight)
                        height: activityMetrics.height
                        color: Colors.dark
                        border.width: 1
                        border.color: modelData.color
                        Column {
                            anchors.fill: parent
                            anchors.margins: 4
                            spacing: 2
                            QuietText {
                                width: parent.width
                                text: modelData.label
                                color: modelData.color
                                font.pixelSize: allActivity.smallText
                                elide: Text.ElideRight
                            }
                            GohuText {
                                width: parent.width
                                text: modelData.value
                                color: Colors.white
                                font.pixelSize: allActivity.roomy ? 21 : 17
                                elide: Text.ElideRight
                            }
                            QuietText {
                                width: parent.width
                                text: modelData.note
                                color: Colors.cyan
                                font.pixelSize: allActivity.smallText
                                elide: Text.ElideRight
                            }
                        }
                    }
                }
            }

            Row {
                id: activityInstruments
                objectName: "cosmos-c13-simultaneous-instruments"
                anchors.top: activityMetrics.bottom
                anchors.topMargin: 5
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: activityNote.top
                anchors.bottomMargin: 4
                spacing: 5

                Rectangle {
                    id: xrayBay
                    objectName: "cosmos-c13-xray-bay"
                    width: Math.max(1, Math.round((activityInstruments.width-5)*0.57))
                    height: activityInstruments.height
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.cyan
                    clip: true

                    Row {
                        id: xrayTitle
                        anchors.top: parent.top
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.margins: 3
                        height: allActivity.roomy ? 25 : 19
                        spacing: 3
                        QuietText {
                            width: Math.max(1,xrayTitle.width-65)
                            height: parent.height
                            text: "X-RAY // HISTORY + SOURCE"
                            color: Colors.cyan
                            font.pixelSize: allActivity.smallText
                            verticalAlignment: Text.AlignVCenter
                            elide: Text.ElideRight
                        }
                        ActionButton {
                            width: 60
                            height: parent.height
                            label: "REFRESH"
                            labelPixelSize: 8
                            contentPadding: 1
                            accentColor: Colors.cyan
                            onClicked: sunTerminal.updateSource()
                        }
                    }

                    Rectangle {
                        id: xrayGraph
                        objectName: "cosmos-c13-xray-graph"
                        anchors.top: xrayTitle.bottom
                        anchors.topMargin: 3
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.leftMargin: 3
                        anchors.rightMargin: 3
                        height: Math.max(40,Math.round((xrayBay.height-xrayTitle.height-8)*0.42))
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
                                    width: Math.max(1,(xrayTrend.width
                                        -Math.max(0,xrayTrend.children.length-1)*2)/12)
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
                    Grid {
                        id: xrayFacts
                        objectName: "cosmos-c12-xray-facts"
                        anchors.top: xrayGraph.bottom
                        anchors.topMargin: 3
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        anchors.margins: 3
                        columns: 2
                        spacing: 2
                        Repeater {
                            model: sunTerminal.xrayFields
                            delegate: Rectangle {
                                required property var modelData
                                width: Math.max(1,(xrayFacts.width-2)/2)
                                height: Math.max(1,(xrayFacts.height-6)/4)
                                color: Colors.black
                                border.width: 1
                                border.color: Colors.blue
                                Column {
                                    anchors.fill: parent
                                    anchors.margins: 2
                                    spacing: 1
                                    QuietText {
                                        width: parent.width
                                        text: modelData.label
                                        color: Colors.cyan
                                        font.pixelSize: allActivity.smallText
                                        elide: Text.ElideRight
                                    }
                                    GohuText {
                                        width: parent.width
                                        text: modelData.value
                                        color: Colors.white
                                        font.pixelSize: allActivity.valueText
                                        elide: Text.ElideRight
                                    }
                                }
                            }
                        }
                    }
                }

                Column {
                    id: activitySide
                    width: Math.max(1,activityInstruments.width-xrayBay.width-5)
                    height: activityInstruments.height
                    spacing: 4

                    Rectangle {
                        id: flareBay
                        objectName: "cosmos-c13-flare-bay"
                        width: parent.width
                        height: Math.max(1,Math.round((activitySide.height-4)*0.46))
                        color: Colors.dark
                        border.width: 1
                        border.color: Colors.magenta
                        clip: true
                        Row {
                            id: flareTitle
                            anchors.top: parent.top
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.margins: 3
                            height: allActivity.roomy ? 25 : 19
                            spacing: 3
                            QuietText {
                                width: Math.max(1,flareTitle.width-50)
                                height: parent.height
                                text: sunTerminal.flareCount
                                    ? "FLARE "+(sunTerminal.selectedFlareIndex+1)
                                        +"/"+sunTerminal.flareCount : "FLARES // NONE"
                                color: Colors.magenta
                                font.pixelSize: allActivity.smallText
                                verticalAlignment: Text.AlignVCenter
                                elide: Text.ElideRight
                            }
                            ActionButton {
                                width: 21
                                height: parent.height
                                label: "‹"
                                labelPixelSize: 14
                                contentPadding: 1
                                available: sunTerminal.flareCount>1
                                accentColor: Colors.magenta
                                onClicked: sunTerminal.selectedFlareIndex =
                                    (sunTerminal.selectedFlareIndex-1+sunTerminal.flareCount)
                                        %sunTerminal.flareCount
                            }
                            ActionButton {
                                width: 21
                                height: parent.height
                                label: "›"
                                labelPixelSize: 14
                                contentPadding: 1
                                available: sunTerminal.flareCount>1
                                accentColor: Colors.magenta
                                onClicked: sunTerminal.selectedFlareIndex =
                                    (sunTerminal.selectedFlareIndex+1)%sunTerminal.flareCount
                            }
                        }
                        Grid {
                            id: flareFacts
                            objectName: "cosmos-c12-flare-facts"
                            anchors.top: flareTitle.bottom
                            anchors.topMargin: 2
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.bottom: parent.bottom
                            anchors.margins: 3
                            columns: 4
                            spacing: 2
                            Repeater {
                                model: sunTerminal.flareFields
                                delegate: Rectangle {
                                    required property var modelData
                                    width: Math.max(1,(flareFacts.width-6)/4)
                                    height: Math.max(1,(flareFacts.height-2)/2)
                                    color: Colors.black
                                    border.width: 1
                                    border.color: Colors.magenta
                                    Column {
                                        anchors.fill: parent
                                        anchors.margins: 2
                                        spacing: 1
                                        QuietText {
                                            width: parent.width
                                            text: modelData.label
                                            color: Colors.cyan
                                            font.pixelSize: allActivity.roomy ? 9 : 7
                                            elide: Text.ElideRight
                                        }
                                        GohuText {
                                            width: parent.width
                                            text: modelData.value
                                            color: Colors.yellow
                                            font.pixelSize: allActivity.valueText
                                            elide: Text.ElideRight
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Rectangle {
                        id: cycleBay
                        objectName: "cosmos-c13-cycle-bay"
                        width: parent.width
                        height: Math.max(1,activitySide.height-flareBay.height-4)
                        color: Colors.dark
                        border.width: 1
                        border.color: Colors.yellow
                        clip: true
                        QuietText {
                            id: cycleTitle
                            anchors.top: parent.top
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.margins: 3
                            height: allActivity.roomy ? 25 : 19
                            text: "CYCLE // MONTHLY MODEL"
                            color: Colors.orange
                            font.pixelSize: allActivity.smallText
                            verticalAlignment: Text.AlignVCenter
                            elide: Text.ElideRight
                        }
                        Grid {
                            id: cycleFacts
                            objectName: "cosmos-c12-cycle-facts"
                            anchors.top: cycleTitle.bottom
                            anchors.topMargin: 2
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.bottom: parent.bottom
                            anchors.margins: 3
                            columns: 4
                            spacing: 2
                            Repeater {
                                model: sunTerminal.cycleFields
                                delegate: Rectangle {
                                    required property var modelData
                                    width: Math.max(1,(cycleFacts.width-6)/4)
                                    height: Math.max(1,(cycleFacts.height-4)/3)
                                    color: Colors.black
                                    border.width: 1
                                    border.color: Colors.yellow
                                    Column {
                                        anchors.fill: parent
                                        anchors.margins: 2
                                        spacing: 1
                                        QuietText {
                                            width: parent.width
                                            text: modelData.label
                                            color: Colors.orange
                                            font.pixelSize: allActivity.roomy ? 9 : 7
                                            elide: Text.ElideRight
                                        }
                                        GohuText {
                                            width: parent.width
                                            text: modelData.value
                                            color: Colors.white
                                            font.pixelSize: allActivity.valueText
                                            elide: Text.ElideRight
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
            QuietText {
                id: activityNote
                anchors.bottom: parent.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                height: 13
                font.pixelSize: 8
                color: Colors.orange
                elide: Text.ElideRight
                text: "GOES XRS "+(sunTerminal.xray && sunTerminal.xray.ready
                    ? (sunTerminal.xray.sampleFresh ? "CURRENT" : "STALE")
                    : "UNAVAILABLE")+" // OBSERVED EVENT PEAKS, NOT ALERTS"
                    +" // NOAA SOLAR CYCLE // MONTHLY PREDICTION, NOT LIVE FLUX"
            }
        }
    }
}
