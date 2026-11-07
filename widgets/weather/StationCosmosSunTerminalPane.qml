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

    property string terminalMode: "live" // live | position | activity
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
    property int flareDetailPage: 0
    property int cycleDetailPage: 0
    property int activityFocus: 0 // X-RAY | FLARES | CYCLE
    property bool xraySourcePage: false

    readonly property var selectedFlare: SolarDetails.flareAt(flares,selectedFlareIndex)
    readonly property var flareFields: SolarDetails.flarePage(selectedFlare,flareDetailPage)
    readonly property var cycleFields: SolarDetails.cyclePage(
        cycle && cycle.ready ? cycle.summary : null,cycleDetailPage,
        spaceService ? spaceService.solarFluxText : "")
    readonly property var xrayFields: SolarDetails.xrayPage(
        xray && xray.ready ? xray : null,xraySourcePage ? 1 : 0)

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
    function updateSource() {
        if (activityFocus===0 && xray && !xray.loading) xray.refresh();
        if (activityFocus===1 && flares && !flares.loading) flares.refresh();
        if (activityFocus===2 && cycle && !cycle.loading) cycle.refresh(true);
    }

    Loader {
        id: activeTerminal
        objectName: "cosmos-c12-active-board"
        anchors.fill: parent
        sourceComponent: sunTerminal.terminalMode==="position" ? positionBoard
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

    // ACTIVITY // summary stays in view. The instrument beneath is chosen
    // within this same panel, not another bottom-route menu.
    Component {
        id: activityBoard
        Item {
            objectName: "cosmos-c12-activity-board"
            anchors.fill: parent
            Row {
                id: activityMetrics
                objectName: "cosmos-c12-activity-metrics"
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                height: 61
                spacing: 5
                Repeater {
                    model: [
                        {label:"X-RAY // CLASS",value:sunTerminal.xray && sunTerminal.xray.ready
                            ? sunTerminal.show(sunTerminal.xray.classEquivalent.label) : "--",
                         note:"GOES XRS",color:Colors.cyan,weight:0.30},
                        {label:"FLARE // PEAK",value:sunTerminal.flares && sunTerminal.flares.latest
                            ? sunTerminal.show(sunTerminal.flares.latest.classLabel) : "--",
                         note:sunTerminal.flares && sunTerminal.flares.ready
                            ? sunTerminal.flares.count24h+" / 24H" : "WAITING",
                         color:Colors.magenta,weight:0.32},
                        {label:"CYCLE // SSN",value:sunTerminal.cycle && sunTerminal.cycle.ready
                            ? sunTerminal.reading(sunTerminal.cycle.summary.predictedSsn,1) : "--",
                         note:"PREDICTED",color:Colors.yellow,weight:0.19},
                        {label:"F10.7 // SFU",value:sunTerminal.cycle && sunTerminal.cycle.ready
                            ? sunTerminal.reading(sunTerminal.cycle.summary.predictedFlux,1) : "--",
                         note:"PREDICTED",color:Colors.orange,weight:0.19}
                    ]
                    delegate: Rectangle {
                        required property var modelData
                        width: Math.max(1,(activityMetrics.width-15)*modelData.weight)
                        height: activityMetrics.height
                        color: Colors.dark
                        border.width: 1
                        border.color: modelData.color
                        Column {
                            anchors.fill: parent
                            anchors.margins: 4
                            spacing: 3
                            QuietText {
                                width: parent.width
                                text: modelData.label
                                color: modelData.color
                                font.pixelSize: 8
                                elide: Text.ElideRight
                            }
                            GohuText {
                                width: parent.width
                                text: modelData.value
                                color: Colors.white
                                font.pixelSize: 17
                                elide: Text.ElideRight
                            }
                            QuietText {
                                width: parent.width
                                text: modelData.note
                                color: Colors.cyan
                                font.pixelSize: 8
                                elide: Text.ElideRight
                            }
                        }
                    }
                }
            }
            Row {
                id: activityTabs
                objectName: "cosmos-c12-activity-inner-modes"
                anchors.top: activityMetrics.bottom
                anchors.topMargin: 5
                anchors.left: parent.left
                anchors.right: parent.right
                height: 24
                spacing: 4
                Repeater {
                    model: [
                        {title:"X-RAY / HISTORY",idx:0},
                        {title:"FLARE / LOG",idx:1},
                        {title:"CYCLE / MODEL",idx:2}
                    ]
                    delegate: ActionButton {
                        required property var modelData
                        width: Math.max(1,(activityTabs.width-78)/3)
                        height: activityTabs.height
                        label: modelData.title
                        labelPixelSize: 9
                        contentPadding: 1
                        selected: sunTerminal.activityFocus===modelData.idx
                        accentColor: Colors.magenta
                        onClicked: sunTerminal.activityFocus=modelData.idx
                    }
                }
                ActionButton {
                    width: 70
                    height: activityTabs.height
                    label: "REFRESH"
                    labelPixelSize: 8
                    contentPadding: 1
                    accentColor: Colors.cyan
                    onClicked: sunTerminal.updateSource()
                }
            }

            Loader {
                id: activityInstrument
                objectName: "cosmos-c12-activity-instrument"
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: activityTabs.bottom
                anchors.topMargin: 5
                anchors.bottom: activityNote.top
                anchors.bottomMargin: 3
                sourceComponent: sunTerminal.activityFocus===0 ? xrayDetail
                    : sunTerminal.activityFocus===1 ? flareDetail : cycleDetail
            }

            QuietText {
                id: activityNote
                anchors.bottom: parent.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                height: 12
                font.pixelSize: 8
                color: Colors.orange
                elide: Text.ElideRight
                text: sunTerminal.activityFocus===2
                    ? "NOAA SOLAR CYCLE // MONTHLY PREDICTION, NOT LIVE FLUX"
                    : sunTerminal.activityFocus===1
                    ? "GOES X-RAY FLARES // OBSERVED EVENT PEAKS, NOT ALERTS"
                    : sunTerminal.xray && sunTerminal.xray.ready
                    ? "GOES XRS SAMPLE "+sunTerminal.show(sunTerminal.xray.sampleUtc)
                        +" // "+(sunTerminal.xray.sampleFresh ? "CURRENT" : "STALE")
                    : "GOES XRS // WAITING OR UNAVAILABLE"
            }

            Component {
                id: xrayDetail
                Item {
                    objectName: "cosmos-c12-xray-detail"
                    anchors.fill: parent
                    ActionButton {
                        id: xraySwitch
                        anchors.top: parent.top
                        anchors.right: parent.right
                        width: 77
                        height: 20
                        label: sunTerminal.xraySourcePage ? "TREND" : "SOURCE"
                        labelPixelSize: 9
                        contentPadding: 1
                        selected: sunTerminal.xraySourcePage
                        accentColor: Colors.cyan
                        onClicked: sunTerminal.xraySourcePage = !sunTerminal.xraySourcePage
                    }
                    Row {
                        id: xrayData
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: xraySwitch.bottom
                        anchors.topMargin: 3
                        anchors.bottom: parent.bottom
                        spacing: 6
                        Item {
                            width: Math.max(1,(xrayData.width-6)*0.58)
                            height: xrayData.height
                            Row {
                                objectName: "cosmos-c12-xray-trend"
                                visible: !sunTerminal.xraySourcePage
                                anchors.fill: parent
                                spacing: 2
                                Repeater {
                                    model: sunTerminal.xray && sunTerminal.xray.ready
                                        ? sunTerminal.xray.trend : []
                                    delegate: Item {
                                        required property var modelData
                                        width: Math.max(1,(parent.width-22)/12)
                                        height: parent.height
                                        Rectangle {
                                            anchors.left: parent.left
                                            anchors.right: parent.right
                                            anchors.bottom: parent.bottom
                                            height: Math.max(3,(parent.height-4)*modelData.level)
                                            color: modelData.classLetter==="X"
                                                ? Colors.magenta : modelData.classLetter==="M"
                                                ? Colors.orange : modelData.classLetter==="C"
                                                ? Colors.yellow : Colors.cyan
                                        }
                                    }
                                }
                            }
                            Column {
                                visible: sunTerminal.xraySourcePage
                                anchors.fill: parent
                                spacing: 4
                                QuietText {
                                    text: "GOES // LONG + SHORT X-RAY BANDS"
                                    color: Colors.magenta
                                    font.pixelSize: 8
                                }
                                GohuText {
                                    text: sunTerminal.xray && sunTerminal.xray.ready
                                        ? sunTerminal.reading(sunTerminal.xray.fluxLong,9)+" W/M²"
                                        : "-- W/M²"
                                    font.pixelSize: 12
                                    color: Colors.yellow
                                }
                                QuietText {
                                    text: sunTerminal.xray && sunTerminal.xray.ready
                                        ? sunTerminal.reading(sunTerminal.xray.fluxShort,9)+" W/M²"
                                        : "-- W/M²"
                                    font.pixelSize: 9
                                }
                            }
                        }
                        Grid {
                            id: xrayFacts
                            objectName: "cosmos-c12-xray-facts"
                            width: Math.max(1,xrayData.width-6
                                -Math.round((xrayData.width-6)*0.58))
                            height: xrayData.height
                            columns: 2
                            spacing: 3
                            Repeater {
                                model: sunTerminal.xrayFields
                                delegate: Rectangle {
                                    required property var modelData
                                    width: Math.max(1,(xrayFacts.width-3)/2)
                                    height: Math.max(1,(xrayFacts.height-3)/2)
                                    color: Colors.dark
                                    border.width: 1
                                    border.color: Colors.blue
                                    Column {
                                        anchors.fill: parent
                                        anchors.margins: 3
                                        spacing: 2
                                        QuietText {
                                            width: parent.width
                                            text: modelData.label
                                            color: Colors.cyan
                                            font.pixelSize: 8
                                            elide: Text.ElideRight
                                        }
                                        GohuText {
                                            width: parent.width
                                            text: modelData.value
                                            color: Colors.white
                                            font.pixelSize: 9
                                            elide: Text.ElideRight
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
            Component {
                id: flareDetail
                Item {
                    objectName: "cosmos-c12-flare-detail"
                    anchors.fill: parent
                    Row {
                        id: flareBar
                        anchors.top: parent.top
                        anchors.left: parent.left
                        anchors.right: parent.right
                        height: 21
                        spacing: 4
                        ActionButton {
                            width: 48
                            height: 21
                            label: "PREV"
                            labelPixelSize: 9
                            available: sunTerminal.flareCount>1
                            onClicked: sunTerminal.selectedFlareIndex =
                                (sunTerminal.selectedFlareIndex-1
                                +sunTerminal.flareCount)%sunTerminal.flareCount
                        }
                        ActionButton {
                            width: 48
                            height: 21
                            label: "NEXT"
                            labelPixelSize: 9
                            available: sunTerminal.flareCount>1
                            onClicked: sunTerminal.selectedFlareIndex =
                                (sunTerminal.selectedFlareIndex+1)
                                %sunTerminal.flareCount
                        }
                        QuietText {
                            width: Math.max(1,flareBar.width-195)
                            height: 21
                            text: sunTerminal.flareCount
                                ? "EVENT "+(sunTerminal.selectedFlareIndex+1)
                                    +"/"+sunTerminal.flareCount
                                : "NO EVENTS"
                            color: Colors.cyan
                            font.pixelSize: 9
                            verticalAlignment: Text.AlignVCenter
                        }
                        ActionButton {
                            width: 84
                            height: 21
                            label: sunTerminal.flareDetailPage===0 ? "TIMES" : "DETAIL"
                            labelPixelSize: 9
                            selected: true
                            accentColor: Colors.magenta
                            available: sunTerminal.flareCount>0
                            onClicked: sunTerminal.flareDetailPage =
                                sunTerminal.flareDetailPage===0 ? 1 : 0
                        }
                    }
                    Row {
                        id: flareFacts
                        objectName: "cosmos-c12-flare-facts"
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: flareBar.bottom
                        anchors.topMargin: 4
                        anchors.bottom: parent.bottom
                        spacing: 4
                        Repeater {
                            model: sunTerminal.flareFields
                            delegate: Rectangle {
                                required property var modelData
                                width: Math.max(1,(flareFacts.width-12)/4)
                                height: flareFacts.height
                                color: Colors.dark
                                border.width: 1
                                border.color: Colors.magenta
                                Column {
                                    anchors.fill: parent
                                    anchors.margins: 4
                                    spacing: 5
                                    QuietText {
                                        width: parent.width
                                        text: modelData.label
                                        color: Colors.cyan
                                        font.pixelSize: 8
                                        elide: Text.ElideRight
                                    }
                                    GohuText {
                                        width: parent.width
                                        text: modelData.value
                                        color: Colors.yellow
                                        font.pixelSize: 11
                                        elide: Text.ElideRight
                                    }
                                }
                            }
                        }
                    }
                }
            }
            Component {
                id: cycleDetail
                Item {
                    objectName: "cosmos-c12-cycle-detail"
                    anchors.fill: parent
                    Row {
                        id: cycleModes
                        anchors.top: parent.top
                        anchors.left: parent.left
                        anchors.right: parent.right
                        height: 21
                        spacing: 4
                        Repeater {
                            model: [
                                {label:"MODEL",idx:0},
                                {label:"RANGES",idx:1},
                                {label:"OUTLOOK",idx:2}
                            ]
                            delegate: ActionButton {
                                required property var modelData
                                width: Math.max(1,(cycleModes.width-8)/3)
                                height: 21
                                label: modelData.label
                                labelPixelSize: 9
                                contentPadding: 1
                                selected: sunTerminal.cycleDetailPage===modelData.idx
                                accentColor: Colors.orange
                                onClicked: sunTerminal.cycleDetailPage=modelData.idx
                            }
                        }
                    }
                    Row {
                        id: cycleFacts
                        objectName: "cosmos-c12-cycle-facts"
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: cycleModes.bottom
                        anchors.topMargin: 4
                        anchors.bottom: parent.bottom
                        spacing: 4
                        Repeater {
                            model: sunTerminal.cycleFields
                            delegate: Rectangle {
                                required property var modelData
                                width: Math.max(1,(cycleFacts.width-12)/4)
                                height: cycleFacts.height
                                color: Colors.dark
                                border.width: 1
                                border.color: Colors.yellow
                                Column {
                                    anchors.fill: parent
                                    anchors.margins: 4
                                    spacing: 5
                                    QuietText {
                                        width: parent.width
                                        text: modelData.label
                                        color: Colors.orange
                                        font.pixelSize: 8
                                        elide: Text.ElideRight
                                    }
                                    GohuText {
                                        width: parent.width
                                        text: modelData.value
                                        color: Colors.white
                                        font.pixelSize: 11
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
