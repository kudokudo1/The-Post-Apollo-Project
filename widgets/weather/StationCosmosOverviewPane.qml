import QtQuick
import "../../components"
import "../../services/weather/WeatherRuntimePolicy.js" as RuntimePolicy
import "StationSubjectHeaderGeometry.js" as HeaderGeometry

// COSMOS C2 // A fixed observation console, not two long reports
// squeezed into halves. All readouts reuse the existing root services.
// Full astronomy, solar-weather and source diagnostics remain in INDEX.
Rectangle {
    id: overview
    color: Colors.black
    clip: true

    property var weatherService: null
    property var spaceService: null
    property real runtimeNowMs: 0
    signal routeRequested(string path)

    // Exactly one source-only SKY, using existing USNO/solar models.
    // The full StationSpace is intentionally NOT mounted here:
    // its long page would reactivate unrelated deep-only collectors.
    StationSky {
        id: sourceSky
        width: 1
        height: 1
        sourceOnly: true
        opacity: 0
        subjectRoute: "cosmos/overview"
        weatherService: overview.weatherService
        runtimeNowMs: overview.runtimeNowMs
    }

    function metric(ready,value,digits,unit) {
        if (!ready || value===null || value===undefined
                || !isFinite(Number(value))) return "--";
        return Number(value).toFixed(digits) + unit;
    }

    // Live availability is not synonymous with a fresh reading. Reuse
    // the same timestamp/cache vocabulary as the existing SPACE rack.
    function availability(sourceId,ready,loading,error,received,observed,cache) {
        return RuntimePolicy.displayRow(sourceId,{
            active:true, ready:!!ready, loading:!!loading,
            errorText:error||"", receivedAt:received,
            observedAt:observed, usingCache:!!cache
        },runtimeNowMs).availability.replace(/_/g," ");
    }

    readonly property var liveMetrics: [
        {label:"KP / GEOMAG",value:metric(spaceService && spaceService.kpReady,
            spaceService ? spaceService.kp : null,1,""),
            state:availability("space-kp",
                spaceService && spaceService.kpReady,
                spaceService && spaceService.kpLoading,
                spaceService ? spaceService.kpErrorText : "",
                spaceService ? spaceService.kpLastUpdated : null,
                spaceService ? spaceService.kpTime : null,
                spaceService && spaceService.usingPersistentKpCache),
            path:"cosmos/space-weather/geomagnetic",color:Colors.cyan},
        {label:"SOLAR WIND",value:metric(spaceService && spaceService.solarWindReady,
            spaceService ? spaceService.solarWindSpeed : null,0," KM/S"),
            state:availability("space-wind",
                spaceService && spaceService.solarWindReady,
                spaceService && spaceService.solarWindLoading,
                spaceService ? spaceService.solarWindErrorText : "",
                spaceService ? spaceService.solarWindLastUpdated : null,
                spaceService ? spaceService.solarWindTime : null,
                spaceService && spaceService.usingPersistentSolarWindCache),
            path:"cosmos/space-weather/solar-wind",color:Colors.yellow},
        {label:"IMF BZ",value:metric(spaceService && spaceService.magneticFieldReady,
            spaceService ? spaceService.magneticFieldBz : null,1," NT"),
            state:availability("space-imf",
                spaceService && spaceService.magneticFieldReady,
                spaceService && spaceService.magneticFieldLoading,
                spaceService ? spaceService.magneticFieldErrorText : "",
                spaceService ? spaceService.magneticFieldLastUpdated : null,
                spaceService ? spaceService.magneticFieldTime : null,
                spaceService && spaceService.usingPersistentMagneticFieldCache),
            path:"cosmos/space-weather/solar-wind",color:Colors.magenta},
        {label:"F10.7 FLUX",value:metric(spaceService && spaceService.solarFluxReady,
            spaceService ? spaceService.solarFlux : null,0," SFU"),
            state:availability("space-flux",
                spaceService && spaceService.solarFluxReady,
                spaceService && spaceService.solarFluxLoading,
                spaceService ? spaceService.solarFluxErrorText : "",
                spaceService ? spaceService.solarFluxLastUpdated : null,
                spaceService ? spaceService.solarFluxTime : null,
                spaceService && spaceService.usingPersistentSolarFluxCache),
            path:"cosmos/sun/activity",color:Colors.orange}
    ]

    Column {
        id: dashboard
        anchors.fill: parent
        anchors.margins: HeaderGeometry.inset
        // Fixed C44 stages; inner instrument content retains its own spacing.
        spacing: 0

        GohuText {
            id: consoleHeader
            objectName: "cosmos-c44-overview-title"
            width: parent.width
            height: HeaderGeometry.titleHeight
            verticalAlignment: Text.AlignVCenter
            text: "COSMOS // OVERVIEW"
            font.pixelSize: 12
            color: Colors.magenta
            elide: Text.ElideRight
        }
        Item {
            id: headerSpacer
            width: parent.width
            height: HeaderGeometry.titleToTabs
        }
        Row {
            id: overviewModeRail
            objectName: "cosmos-c44-overview-mode-rail"
            width: parent.width
            height: HeaderGeometry.tabHeight
            spacing: HeaderGeometry.tabSpacing
            Repeater {
                model: [
                    {label:"SUN",path:"cosmos/sun/position"},
                    {label:"MOON",path:"cosmos/moon/ephemeris"},
                    {label:"SPACE",path:"cosmos/space-weather/overview"}
                ]
                delegate: ActionButton {
                    required property var modelData
                    objectName: "cosmos-c44-overview-button"
                    width: HeaderGeometry.buttonWidth(overviewModeRail.width,3)
                    height: HeaderGeometry.tabHeight
                    contentPadding: 1
                    label: modelData.label
                    labelPixelSize: 10
                    accentColor: Colors.cyan
                    onClicked: overview.routeRequested(modelData.path)
                }
            }
        }
        Item {
            id: dividerSlot
            objectName: "cosmos-c44-overview-divider-slot"
            width: parent.width
            height: HeaderGeometry.tabsToRule + HeaderGeometry.ruleHeight
            Rectangle {
                objectName: "cosmos-c44-overview-divider"
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: HeaderGeometry.ruleHeight
                color: Colors.cyan
            }
        }

        Item {
            id: headerContentGap
            width: parent.width
            height: HeaderGeometry.ruleToContent
        }
        Column {
            id: overviewContent
            width: parent.width
            height: Math.max(0,dashboard.height - consoleHeader.height
                - headerSpacer.height - overviewModeRail.height
                - dividerSlot.height - headerContentGap.height)
            spacing: HeaderGeometry.ruleToContent
        Rectangle {
            id: skyInstrumentFrame
            objectName: "cosmos-c44-overview-stage"
            width: parent.width
            // Leave a fixed lower rack; do not make the outer dashboard scroll.
            height: Math.max(0,overviewContent.height
                    -spaceHeader.height-spaceMetricRow.height
                    -2*overviewContent.spacing)
            color: Colors.black
            border.width: 1
            border.color: Colors.magenta
            clip: true
            StationCosmosVisualInstruments {
                id: scientificVisuals
                anchors.fill: parent
                anchors.margins: 1
                compactMode: true
                showMoon: true
                showSun: true
                moonReady: !!sourceSky.moonObservation
                    && sourceSky.moonObservation.ready
                moonEphemeris: sourceSky.moonObservation
                    ? sourceSky.moonObservation.ephemeris : null
                astronomySummary: sourceSky.astronomySummary
                twilightSummary: sourceSky.twilightSummary
                currentSolarPosition: sourceSky.currentSolarPosition
                providerLocalMinute: sourceSky.providerLocalMinute
                latitude: overview.weatherService
                    ? overview.weatherService.latitude : ""
                longitude: overview.weatherService
                    ? overview.weatherService.longitude : ""
                solarDate: sourceSky.astronomySummary.date
                solarCivilOffsetMinutes: sourceSky.moonCivilOffsetMinutes
                solarOffsetSource: sourceSky.moonCivilOffsetSource
            }
        }

        Row {
            id: spaceHeader
            width: parent.width
            height: 15
            spacing: 4
            GohuText {
                width: Math.max(0,parent.width-120)
                height: parent.height
                verticalAlignment: Text.AlignVCenter
                font.pixelSize: 10
                text: "SPACE WEATHER // LATEST"
                color: Colors.magenta
                elide: Text.ElideRight
            }
            ActionButton {
                width: 116
                height: 15
                label: "SPACE // ALL"
                labelPixelSize: 8
                contentPadding: 0
                accentColor: Colors.orange
                onClicked: overview.routeRequested("cosmos/space-weather/full")
            }
        }

        Row {
            id: spaceMetricRow
            width: parent.width
            height: 48
            spacing: 4
            Repeater {
                model: overview.liveMetrics
                delegate: Rectangle {
                    required property var modelData
                    width: Math.max(1,(spaceMetricRow.width
                        -3*spaceMetricRow.spacing)/4)
                    height: spaceMetricRow.height
                    color: Colors.dark
                    border.width: 1
                    border.color: modelData.color
                    clip: true
                    Column {
                        anchors.fill: parent
                        anchors.margins: 3
                        spacing: 2
                        QuietText {
                            width: parent.width
                            font.pixelSize: 8
                            color: modelData.color
                            text: modelData.label
                            elide: Text.ElideRight
                        }
                        GohuText {
                            width: parent.width
                            font.pixelSize: 13
                            color: Colors.white
                            text: modelData.value
                            elide: Text.ElideRight
                        }
                        QuietText {
                            width: parent.width
                            font.pixelSize: 8
                            color: Colors.yellow
                            text: modelData.state
                            elide: Text.ElideRight
                        }
                    }
                    // The entire tile is the action, not a tiny extra
                    // button consuming the space needed for readable data.
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: overview.routeRequested(modelData.path)
                    }
                }
            }
        }
        }
    }
}
