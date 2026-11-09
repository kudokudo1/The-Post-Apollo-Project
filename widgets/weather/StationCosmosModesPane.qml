import QtQuick
import "../../components"
import "StationCosmosModePolicy.js" as Modes
import "StationCosmosPlanetEventPolicy.js" as ClockPolicy

// Fixed subject rail + one focused instrument. No whole-page scrolling.
// The IAU shower catalogue alone scrolls inside a bounded middle panel.
Rectangle {
    id: cosmosModePane
    color: Colors.black
    clip: true
    property string subjectRoute: ""
    // C39 // Two instruments share one PLANETS stage, while the dedicated
    // SKY NOW strip always uses the existing live USNO celestial sample.
    property string planetSubmode: "day"
    property string planetSelection: "ALL"
    property bool skyDetailsExpanded: false
    property int skyDetailsIndex: 0
    property var weatherService: null
    property var spaceService: null
    property var liveHistoryStore: null
    property real runtimeNowMs: 0
    signal routeRequested(string path)
    readonly property string family: Modes.family(subjectRoute)
    readonly property string kind: Modes.kind(subjectRoute)
    readonly property var modes: Modes.modesFor(subjectRoute) || []
    readonly property int modeCount: modeRepeater.count
    readonly property int visibleClockLaneCount:
        instrumentLoader.item && instrumentLoader.item.renderedRowCount !== undefined
        ? instrumentLoader.item.renderedRowCount : 0
    // Read-only native acceptance diagnostics; do not create a separate source.
    readonly property var instrumentItem: instrumentLoader.item
    readonly property bool instrumentMounted: instrumentLoader.item !== null
    readonly property int instrumentLoadState: instrumentLoader.status
    readonly property var skyFeed: skyLoader.item
    readonly property var spaceFeed: spaceSourceLoader.item
    readonly property var astronomy: skyFeed ? skyFeed.astronomySummary : null
    readonly property var twilight: skyFeed ? skyFeed.twilightSummary : null
    readonly property var celnav: skyFeed ? skyFeed.celestialObservation : null
    readonly property var planetSource: skyFeed ? skyFeed.planetObservation : null
    readonly property var meteorSource: skyFeed ? skyFeed.meteorObservation : null
    readonly property var eclipseSource: skyFeed ? skyFeed.eclipseObservation : null
    readonly property var issSource: skyFeed ? skyFeed.issObservation : null
    readonly property string civilDate:
        skyFeed && typeof skyFeed.focusedCivilDate === "string"
        ? skyFeed.focusedCivilDate : ""
    readonly property var planetRows: ClockPolicy.clockRows(
        planetSource && planetSource.ready ? planetSource.rows : [],
        civilDate)
    // The clock is still an instrument when USNO is offline. Always show
    // its five lanes, with truthful empty markers instead of blank space.
    readonly property var displayedPlanetRows:
        planetRows && planetRows.length === 5 ? planetRows : [
            {name:"MERCURY",events:[]}, {name:"VENUS",events:[]},
            {name:"MARS",events:[]}, {name:"JUPITER",events:[]},
            {name:"SATURN",events:[]}
        ]
    readonly property bool sourceConfigured: {
        if (kind === "solar-path" || kind === "sun-position")
            return !!skyFeed && /^\d{4}-\d{2}-\d{2}$/.test(civilDate)
                && skyFeed.moonCivilOffsetMinutes !== null
                && skyFeed.moonCivilOffsetMinutes !== undefined
                && !!weatherService && weatherService.latitude !== ""
                && weatherService.longitude !== "";
        if (kind === "light")
            return !!twilight && twilight.available;
        if (kind === "planet-clock" || kind === "planets")
            return !!planetSource && planetSource.configured;
        if (kind === "planets" || kind === "stars")
            return !!celnav && celnav.configured;
        if (kind === "meteors")
            return !!meteorSource && meteorSource.configured;
        if (kind === "iss")
            return !!issSource && issSource.configured;
        if (kind === "eclipses")
            return !!eclipseSource;
        return true;
    }
    readonly property var selectedProvider:
        kind === "planet-clock" || kind === "planets"
            ? planetSource
        : kind === "planets" || kind === "stars" ? celnav
        : kind === "meteors" ? meteorSource
        : kind === "eclipses" ? eclipseSource
        : kind === "iss" ? issSource : null
    readonly property string sourceStatus: {
        if (!Modes.usesSky(subjectRoute)) return "";
        if (!skyFeed) return "ASTRONOMY SOURCE HOST NOT LOADED";
        if (kind === "solar-path" || kind === "sun-position")
            return sourceConfigured
                ? (astronomy && astronomy.available
                   ? "SOLAR MODEL READY // WEATHER FORECAST ANCHOR"
                   : "SOLAR MODEL READY // OPEN-METEO LOCAL CALENDAR")
                : "SOLAR MODEL NEEDS LOCAL DATE, LOCATION AND UTC OFFSET";
        if (kind === "light")
            return sourceConfigured ? "TWILIGHT MODEL READY"
                : "TWILIGHT NEEDS WEATHER SUNRISE CALIBRATION";
        if (!selectedProvider)
            return "PROVIDER NOT MOUNTED";
        if (!sourceConfigured)
            return kind === "planet-clock"
                ? "USNO NEEDS VALID DATE, COORDINATES AND UTC OFFSET"
                : "LOCATION COORDINATES UNAVAILABLE";
        if (!selectedProvider.active)
            return "SOURCE INACTIVE // ROUTE ACTIVATION FAILED";
        if (selectedProvider.loading) return "SOURCE RECEIVING";
        if (selectedProvider.failed)
            return selectedProvider.errorText || "SOURCE REQUEST FAILED";
        if (selectedProvider.ready) return "SOURCE RECEIVED";
        return "SOURCE IDLE // USE RETRY";
    }

    // Normalize source records for the four-card, non-scrolling layouts.
    // This is presentation only, not a fetcher or a new astronomy model.
    readonly property var cards: {
        var rows = [], i, item;
        if (kind === "planets" && celnav && celnav.ready) {
            for (i=0;i<Math.min(4,celnav.snapshot.planets.length);i++) {
                item=celnav.snapshot.planets[i];
                rows.push({name:item.name,
                    info:"ALT "+Number(item.altitude).toFixed(1)+"°",
                    detail:"AZ "+Number(item.azimuth).toFixed(1)+"° "+item.direction});
            }
        } else if (kind === "stars" && celnav && celnav.ready
                   && celnav.snapshot.constellations) {
            for (i=0;i<Math.min(4,celnav.snapshot.constellations.length);i++) {
                item=celnav.snapshot.constellations[i];
                rows.push({name:item.name,info:item.count+" NAV STARS",
                    detail:"ANCHOR "+item.anchorStar});
            }
        } else if (kind === "iss" && issSource && issSource.ready) {
            for (i=0;i<Math.min(4,issSource.passes.length);i++) {
                item=issSource.passes[i];
                rows.push({name:"ISS PASS "+(i+1),
                    info:Number(item.culminate.degrees).toFixed(0)+"° PEAK",
                    detail:"RISE "+String(item.rise.timeUtc)
                        +" // PEAK "+String(item.culminate.timeUtc)});
            }
        } else if (kind === "eclipses" && eclipseSource && eclipseSource.ready) {
            for (const row of [
                {name:"NEXT SOLAR",data:eclipseSource.nextSolar},
                {name:"NEXT LUNAR",data:eclipseSource.nextLunar}
            ]) rows.push({name:row.name,
                info:row.data ? row.data.event : "NO EVENT IN WINDOW",
                detail:row.data ? String(row.data.date) : "DATE --"});
        } else if (kind === "meteors" && meteorSource && meteorSource.ready) {
            // The established IAU feed has two separate lists. Render the
            // active list first, then upcoming; don't hide active showers.
            var seenShower = {};
            var activeList = meteorSource.activeShowers || [];
            var upcomingList = meteorSource.upcomingShowers || [];
            for (i=0;i<activeList.length;i++) {
                item=activeList[i];
                if (!item || !item.name || seenShower[item.name]) continue;
                seenShower[item.name] = true;
                rows.push({name:item.name,info:"ACTIVE NOW",
                    detail:"PEAK "+String(item.peakUtc || "--")});
            }
            for (i=0;i<upcomingList.length;i++) {
                item=upcomingList[i];
                if (!item || !item.name || seenShower[item.name]) continue;
                seenShower[item.name] = true;
                rows.push({name:item.name,info:"UPCOMING",
                    detail:"PEAK "+String(item.peakUtc || "--")});
            }
        }
        return rows;
    }

    Loader {
        id: skyLoader
        active: cosmosModePane.visible && Modes.usesSky(cosmosModePane.subjectRoute)
        width: 1
        height: 1
        opacity: 0
        z: -1
        sourceComponent: Component {
            StationSky {
                sourceOnly: true
                // C39 // Celestial-fix now gates both original USNO sources,
                // without switching routes or mounting another StationSky.
                subjectRoute: Modes.dataRoute(cosmosModePane.subjectRoute || "")
                // Service pointers bound by the parent AFTER item creation.
            }
        }
    }

    // One hidden owner for the selected NOAA source. Rendering it is
    // disabled, including the original SUVI Image network consumer.
    Loader {
        id: spaceSourceLoader
        active: cosmosModePane.visible && (cosmosModePane.kind === "solar-section"
            || cosmosModePane.kind === "sun-observation"
            || cosmosModePane.kind === "sun-live" || cosmosModePane.kind === "sun-activity")
        width: 1
        height: 1
        opacity: 0
        z: -1
        sourceComponent: Component {
            StationSpace {
                sourceOnly: true
                subjectRoute: Modes.dataRoute(cosmosModePane.subjectRoute)
                // Service pointers bound by the parent AFTER item creation.
            }
        }
    }

    // Loader-created components can resolve QObject-valued var bindings
    // before the outer pane has its service pointers. Parent-level Bindings
    // keep these live even when the Loader re-creates its source item.
    Binding {
        target: skyLoader.item
        property: "weatherService"
        value: cosmosModePane.weatherService
        when: skyLoader.item !== null
    }
    Binding {
        target: skyLoader.item
        property: "spaceService"
        value: cosmosModePane.spaceService
        when: skyLoader.item !== null
    }
    Binding {
        target: skyLoader.item
        property: "runtimeNowMs"
        value: cosmosModePane.runtimeNowMs
        when: skyLoader.item !== null
    }
    Binding {
        target: spaceSourceLoader.item
        property: "weatherService"
        value: cosmosModePane.weatherService
        when: spaceSourceLoader.item !== null
    }
    Binding {
        target: spaceSourceLoader.item
        property: "spaceService"
        value: cosmosModePane.spaceService
        when: spaceSourceLoader.item !== null
    }
    Binding {
        target: spaceSourceLoader.item
        property: "liveHistoryStore"
        value: cosmosModePane.liveHistoryStore
        when: spaceSourceLoader.item !== null
    }
    Binding {
        target: spaceSourceLoader.item
        property: "runtimeNowMs"
        value: cosmosModePane.runtimeNowMs
        when: spaceSourceLoader.item !== null
    }

    GohuText {
        id: titleText
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 6
        height: 18
        text: "COSMOS // "+cosmosModePane.family.toUpperCase()
        color: Colors.magenta
        font.pixelSize: 12
        elide: Text.ElideRight
    }
    Row {
        id: modeRail
        anchors.top: titleText.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: 6
        anchors.rightMargin: 6
        anchors.topMargin: 4
        height: 27
        spacing: 4
        Repeater {
            id: modeRepeater
            model: cosmosModePane.modes || []
            delegate: ActionButton {
                required property var modelData
                width: Math.max(1,(modeRail.width
                    -(cosmosModePane.modeCount-1)*modeRail.spacing)
                    /Math.max(1,cosmosModePane.modeCount))
                height: 27
                label: modelData.label
                labelPixelSize: cosmosModePane.modeCount>5 ? 9 : 10
                contentPadding: 1
                selected: Modes.canonical(cosmosModePane.subjectRoute) === modelData.route
                accentColor: Colors.cyan
                onClicked: cosmosModePane.routeRequested(modelData.route)
            }
        }
    }
    Rectangle {
        id: dividerLine
        anchors.top: modeRail.bottom
        anchors.topMargin: 5
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: 6
        anchors.rightMargin: 6
        height: 2
        color: Colors.cyan
    }
    Item {
        id: stage
        anchors.top: dividerLine.bottom
        anchors.bottom: footer.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 6
        clip: true
        Loader {
            id: instrumentLoader
            anchors.fill: parent
            active: cosmosModePane.visible
            sourceComponent: cosmosModePane.kind === "sun-observation"
                || cosmosModePane.kind === "sun-position"
                || cosmosModePane.kind === "sun-live" || cosmosModePane.kind === "sun-activity"
                    ? sunTerminalBoard
                : cosmosModePane.kind === "annual-solar" ? solarYear
                : cosmosModePane.kind === "solar-path" ? sunPath
                : cosmosModePane.kind === "light" ? sunLight
                : cosmosModePane.kind === "planet-clock" ? planetClock
                : cosmosModePane.kind === "planets" ? planetsComposite
                : cosmosModePane.kind === "solar-section" ? solarDetails
                : cosmosModePane.kind === "meteors" ? meteorList
                : cosmosModePane.kind === "eclipses" ? eclipseBoardComponent
                : cosmosModePane.kind === "stars" ? starsBoardComponent
                : subjectCards
        }
        // An unavailable solar forecast must not leave a blank graph without
        // saying which upstream payload is missing.
        QuietText {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.verticalCenter: parent.verticalCenter
            width: Math.max(1,stage.width-32)
            visible: (cosmosModePane.kind === "solar-path"
                || cosmosModePane.kind === "sun-position" || cosmosModePane.kind === "light")
                && !cosmosModePane.sourceConfigured
            text: cosmosModePane.sourceStatus || "SOURCE WAITING"
            color: Colors.orange
            font.pixelSize: 10
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
        }
    }
    Row {
        id: footer
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 6
        height: 20
        spacing: 5
        QuietText {
            width: Math.max(0,footer.width
                - 111 - (retrySource.visible ? 83 : 0))
            text: cosmosModePane.kind === "sun-observation"
                ? "SOLAR OBSERVATION // SUVI + ARC + LIGHT + GOES"
                : cosmosModePane.kind === "sun-position" ? "LOCAL SUN // SOLAR ARC + TWILIGHT"
                : cosmosModePane.kind === "sun-live" ? "NOAA // SUVI + XRS + FLARES"
                : cosmosModePane.kind === "sun-activity" ? "NOAA // XRS + FLARES + CYCLE"
                : cosmosModePane.kind === "annual-solar" ? "JPL // CALCULATE YEAR ON DEMAND"
                : cosmosModePane.kind === "meteors" ? "IAU MDC // SCROLL MIDDLE ONLY"
                : cosmosModePane.kind === "eclipses" ? "NASA GSFC // GLOBAL DATES ONLY"
                : cosmosModePane.kind === "stars" ? "USNO // NAVIGATION SAMPLE NOT FULL SKY"
                : cosmosModePane.kind === "planets" ? "USNO // DATED EVENTS + CURRENT SKY FIX"
                : cosmosModePane.kind === "solar-section" ? "NOAA // ONE INSTRUMENT"
                : "SOURCE-BACKED // FOCUSED VIEW"
            color: Colors.cyan
            font.pixelSize: 8
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        ActionButton {
            id: retrySource
            visible: cosmosModePane.selectedProvider !== null
                && cosmosModePane.sourceConfigured
                && !cosmosModePane.selectedProvider.loading
            width: visible ? 78 : 0
            height: 19
            contentPadding: 1
            label: "RETRY SOURCE"
            labelPixelSize: 8
            accentColor: Colors.orange
            onClicked: {
                if (cosmosModePane.selectedProvider
                    && cosmosModePane.selectedProvider.active
                    && cosmosModePane.selectedProvider.refresh)
                    cosmosModePane.selectedProvider.refresh();
            }
        }
        ActionButton {
            width: 105
            height: 19
            contentPadding: 1
            label: "FULL REFERENCE"
            labelPixelSize: 8
            accentColor: Colors.yellow
            onClicked: cosmosModePane.routeRequested(Modes.fullRoute(cosmosModePane.subjectRoute))
        }
    }

    Component {
        id: sunTerminalBoard
        StationCosmosSunTerminalPane {
            terminalMode: cosmosModePane.kind === "sun-observation" ? "observation"
                : cosmosModePane.kind === "sun-position" ? "position"
                : cosmosModePane.kind === "sun-activity" ? "activity" : "live"
            weatherService: cosmosModePane.weatherService
            spaceService: cosmosModePane.spaceService
            skyFeed: cosmosModePane.skyFeed
            sourceSpace: cosmosModePane.spaceFeed
        }
    }

    Component {
        id: solarDetails
        StationCosmosSunInstrumentPane {
            modeRoute: Modes.dataRoute(cosmosModePane.subjectRoute)
            sourceSpace: cosmosModePane.spaceFeed
            spaceService: cosmosModePane.spaceService
        }
    }
    Component {
        id: solarYear
        StationCosmosAnnualWheelPane {
            subject: "sun"
            weatherService: cosmosModePane.weatherService
            runtimeNowMs: cosmosModePane.runtimeNowMs
        }
    }

    Component {
        id: sunPath
        Column {
            anchors.fill: parent
            spacing: 6
            StationCosmosVisualInstruments {
                objectName: "cosmos-c5-sun-path"
                width: parent.width
                height: parent.height >= 270 ? 204 : parent.height
                compactMode: true
                showMoon: false
                showSun: true
                astronomySummary: cosmosModePane.astronomy
                twilightSummary: cosmosModePane.twilight
                currentSolarPosition: cosmosModePane.skyFeed
                    ? cosmosModePane.skyFeed.currentSolarPosition : null
                providerLocalMinute: cosmosModePane.skyFeed
                    ? cosmosModePane.skyFeed.focusedLocalMinute : -1
                solarDate: cosmosModePane.civilDate || ""
                solarCivilOffsetMinutes: cosmosModePane.skyFeed
                    ? cosmosModePane.skyFeed.moonCivilOffsetMinutes : null
                solarOffsetSource: cosmosModePane.skyFeed
                    ? cosmosModePane.skyFeed.moonCivilOffsetSource : "UNKNOWN"
                latitude: cosmosModePane.weatherService ? cosmosModePane.weatherService.latitude : ""
                longitude: cosmosModePane.weatherService ? cosmosModePane.weatherService.longitude : ""
            }
            Row {
                visible: parent.height >= 270
                height: visible ? 40 : 0
                width: parent.width
                spacing: 5
                Repeater {
                    model: [
                        {name:"SUNRISE",value:cosmosModePane.astronomy ? cosmosModePane.astronomy.sunrise : "--"},
                        {name:"SUNSET",value:cosmosModePane.astronomy ? cosmosModePane.astronomy.sunset : "--"},
                        {name:"DAYLIGHT",value:cosmosModePane.astronomy ? cosmosModePane.astronomy.daylightLabel : "--"}
                    ]
                    delegate: Rectangle {
                        required property var modelData
                        width: Math.max(1,(stage.width-10)/3)
                        height: 40
                        color: Colors.dark
                        border.width: 1
                        border.color: Colors.cyan
                        Column {
                            anchors.fill: parent
                            anchors.margins: 5
                            spacing: 3
                            SecondaryText {text:modelData.name;font.pixelSize:9}
                            GohuText {text:modelData.value;color:Colors.white;font.pixelSize:11}
                        }
                    }
                }
            }
        }
    }
    Component {
        id: sunLight
        Grid {
            anchors.fill: parent
            columns: 2
            spacing: 7
            Repeater {
                model: [
                    {name:"ASTRONOMICAL DAWN",value:cosmosModePane.twilight ? cosmosModePane.twilight.astronomicalDawn : "--"},
                    {name:"CIVIL DAWN",value:cosmosModePane.twilight ? cosmosModePane.twilight.civilDawn : "--"},
                    {name:"SOLAR NOON",value:cosmosModePane.twilight ? cosmosModePane.twilight.solarNoon : "--"},
                    {name:"CIVIL DUSK",value:cosmosModePane.twilight ? cosmosModePane.twilight.civilDusk : "--"},
                    {name:"BLUE AM",value:cosmosModePane.twilight ? cosmosModePane.twilight.blueMorningStart+" → "+cosmosModePane.twilight.blueMorningEnd : "--"},
                    {name:"GOLDEN AM",value:cosmosModePane.twilight ? cosmosModePane.twilight.goldenMorningStart+" → "+cosmosModePane.twilight.goldenMorningEnd : "--"},
                    {name:"GOLDEN PM",value:cosmosModePane.twilight ? cosmosModePane.twilight.goldenEveningStart+" → "+cosmosModePane.twilight.goldenEveningEnd : "--"},
                    {name:"BLUE PM",value:cosmosModePane.twilight ? cosmosModePane.twilight.blueEveningStart+" → "+cosmosModePane.twilight.blueEveningEnd : "--"}
                ]
                delegate: Rectangle {
                    required property var modelData
                    width: Math.max(1,(stage.width-7)/2)
                    height: Math.max(35,(stage.height-21)/4)
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.orange
                    Column {
                        anchors.fill: parent
                        anchors.margins: 6
                        spacing: 6
                        SecondaryText {text:modelData.name;font.pixelSize:9}
                        GohuText {
                            width: parent.width
                            text:modelData.value
                            color: Colors.white
                            font.pixelSize:11
                            elide:Text.ElideRight
                        }
                    }
                }
            }
        }
    }
    Component {
        id: planetsComposite
        Item {
            id: planetsLanding
            objectName: "cosmos-c38-planets-composite"
            anchors.fill: parent
            clip: true
            Row {
                id: planetsViews
                objectName: "cosmos-c39-planets-inner-modes"
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                height: 23
                spacing: 4
                ActionButton {
                    width: Math.max(1,(planetsViews.width-4)/2)
                    height: 22
                    label: "DAY EVENTS"
                    labelPixelSize: 9
                    contentPadding: 0
                    selected: cosmosModePane.planetSubmode === "day"
                    accentColor: Colors.magenta
                    onClicked: cosmosModePane.planetSubmode = "day"
                }
                ActionButton {
                    width: Math.max(1,(planetsViews.width-4)/2)
                    height: 22
                    label: "DAY RING"
                    labelPixelSize: 9
                    contentPadding: 0
                    selected: cosmosModePane.planetSubmode === "ring"
                    accentColor: Colors.yellow
                    onClicked: cosmosModePane.planetSubmode = "ring"
                }
            }
            Loader {
                id: planetsViewLoader
                objectName: "cosmos-c39-planets-active-instrument"
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: planetsViews.bottom
                anchors.topMargin: 3
                anchors.bottom: skyNowStrip.top
                anchors.bottomMargin: 3
                active: planetsLanding.visible && !cosmosModePane.skyDetailsExpanded
                sourceComponent: cosmosModePane.planetSubmode === "ring"
                    ? planetsRingComponent : planetsTimelineComponent
            }
            StationCosmosPlanetsSkyStrip {
                id: skyNowStrip
                objectName: "cosmos-c39-fixed-sky-now"
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: 38
                visible: !cosmosModePane.skyDetailsExpanded
                celestialSource: cosmosModePane.celnav
                selectedPlanet: cosmosModePane.planetSelection
                onPlanetPicked: function(name) {
                    cosmosModePane.planetSelection = name;
                }
                onDetailsRequested: function(index) {
                    cosmosModePane.skyDetailsIndex = index;
                    cosmosModePane.skyDetailsExpanded = true;
                }
            }
            Rectangle {
                id: detailOverlay
                objectName: "cosmos-c39-sky-detail-overlay"
                anchors.fill: parent
                visible: cosmosModePane.skyDetailsExpanded
                z: 5
                color: Colors.black
                clip: true
                Row {
                    id: overlayHeader
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right
                    height: 23
                    spacing: 4
                    GohuText {
                        width: Math.max(1,overlayHeader.width-105)
                        text: "SKY NOW // FULL SOURCE RECORD"
                        font.pixelSize: 10
                        color: Colors.magenta
                        elide: Text.ElideRight
                    }
                    ActionButton {
                        objectName: "cosmos-c39-close-sky-details"
                        width: 101
                        height: 22
                        label: "BACK TO PLANETS"
                        labelPixelSize: 8
                        contentPadding: 0
                        accentColor: Colors.cyan
                        onClicked: cosmosModePane.skyDetailsExpanded = false
                    }
                }
                Loader {
                    objectName: "cosmos-c39-source-record-details"
                    anchors.top: overlayHeader.bottom
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    anchors.topMargin: 3
                    active: detailOverlay.visible
                    sourceComponent: planetsSkyComponent
                }
            }
        }
    }
    Component {
        id: planetsSkyComponent
        StationCosmosDetailPane {
            kind: "planets"
            celestialSource: cosmosModePane.celnav
            sourceStatus: !cosmosModePane.celnav ? "USNO SOURCE UNAVAILABLE"
                : cosmosModePane.celnav.loading ? "SOURCE RECEIVING"
                : cosmosModePane.celnav.ready ? "SOURCE RECEIVED"
                : cosmosModePane.celnav.errorText || "USNO SOURCE WAITING"
            selectedIndex: cosmosModePane.skyDetailsIndex
        }
    }
    Component {
        id: planetsTimelineComponent
        StationCosmosPlanetsDayPane {
            compactInPlanets: true
            controlledSelection: true
            selectedPlanet: cosmosModePane.planetSelection
            onPlanetPicked: function(name) {
                cosmosModePane.planetSelection = name;
            }
            datedRows: cosmosModePane.planetRows
            civilDate: cosmosModePane.civilDate
            sourceReady: !!cosmosModePane.planetSource
                && cosmosModePane.planetSource.ready
            sourceStatus: cosmosModePane.sourceStatus
        }
    }
    Component {
        id: planetsRingComponent
        StationCosmosPlanetClockFace {
            objectName: "cosmos-c39-embedded-day-ring"
            compactInPlanets: true
            controlledSelection: true
            selectedPlanet: cosmosModePane.planetSelection
            onPlanetPicked: function(name) {
                cosmosModePane.planetSelection = name;
            }
            datedRows: cosmosModePane.planetRows
            civilDate: cosmosModePane.civilDate
            localCivilMinute: cosmosModePane.skyFeed
                ? cosmosModePane.skyFeed.focusedLocalMinute : -1
            sourceReady: !!cosmosModePane.planetSource
                && cosmosModePane.planetSource.ready
            sourceStatus: cosmosModePane.sourceStatus
        }
    }
    Component {
        id: planetClock
        // C28 // The circular 24h dial is the focused CLOCK screen, not
        // five linear timelines. It shares USNO source and V3d ring math.
        StationCosmosPlanetClockFace {
            datedRows: cosmosModePane.planetRows
            civilDate: cosmosModePane.civilDate
            localCivilMinute: cosmosModePane.skyFeed
                ? cosmosModePane.skyFeed.focusedLocalMinute : -1
            sourceReady: !!cosmosModePane.planetSource
                && cosmosModePane.planetSource.ready
            sourceStatus: cosmosModePane.sourceStatus
        }
    }
    Component {
        id: eclipseBoardComponent
        StationCosmosEclipseBoard {
            eclipseSource: cosmosModePane.eclipseSource
            sourceStatus: cosmosModePane.sourceStatus
        }
    }
    Component {
        id: starsBoardComponent
        StationCosmosStarsBoard {
            celestialSource: cosmosModePane.celnav
            sourceStatus: cosmosModePane.sourceStatus
        }
    }
    Component {
        id: subjectCards
        StationCosmosDetailPane {
            kind: cosmosModePane.kind
            celestialSource: cosmosModePane.celnav
            issSource: cosmosModePane.issSource
            eclipseSource: cosmosModePane.eclipseSource
            sourceStatus: cosmosModePane.sourceStatus
        }
    }
    Component {
        id: meteorList
        // C25 // Only the shower catalog scrolls. The NEXT PEAKS instrument
        // and source status are fixed above it within the existing stage.
        Item {
            id: meteorBoard
            anchors.fill: parent
            clip: true
            objectName: "cosmos-c25-meteor-board"
            property string selectedShowerName: ""
            property bool imageExpanded: false
            readonly property int featuredCount: width >= 650 ? 5 : 3
            readonly property var upcomingShowers:
                cosmosModePane.meteorSource && cosmosModePane.meteorSource.ready
                ? (cosmosModePane.meteorSource.upcomingShowers || []) : []

            function jumpToShower(name) {
                if (!name) return;
                selectedShowerName = name;
                const rows = cosmosModePane.cards || [];
                for (let i=0;i<rows.length;i++) {
                    if (rows[i] && rows[i].name === name) {
                        // All rows remain in the same bounded inner catalog.
                        const target = i * (47 + meteorCards.spacing);
                        meteorScroll.contentY = Math.max(0,Math.min(
                            Math.max(0,meteorScroll.contentHeight-meteorScroll.height),
                            target));
                        break;
                    }
                }
            }

            Column {
                id: pinnedMeteorHeader
                objectName: "cosmos-c25-meteor-sticky-header"
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                spacing: 4

                GohuText {
                    width: parent.width
                    height: 17
                    text: "METEOR SHOWERS // NEXT PEAKS"
                    font.pixelSize: 11
                    color: Colors.magenta
                    elide: Text.ElideRight
                }
                Row {
                    width: parent.width
                    height: 13
                    spacing: 6
                    QuietText {
                        width: Math.max(1,(parent.width-6)*0.52)
                        text: "IAU MDC // " + cosmosModePane.sourceStatus
                        color: cosmosModePane.sourceStatus === "SOURCE RECEIVED"
                            ? Colors.cyan : Colors.orange
                        font.pixelSize: 8
                        elide: Text.ElideRight
                    }
                    QuietText {
                        width: Math.max(1,(parent.width-6)*0.48)
                        text: cosmosModePane.meteorSource && cosmosModePane.meteorSource.ready
                            ? "ACTIVE " + cosmosModePane.meteorSource.activeCount
                              + " // λ☉ " +
                              (cosmosModePane.meteorSource.solarLongitude >= 0
                               ? cosmosModePane.meteorSource.solarLongitude.toFixed(1)+"°"
                               : "--")
                            : "PEAK DATES // APPROXIMATE UTC"
                        color: Colors.cyan
                        font.pixelSize: 8
                        elide: Text.ElideRight
                        horizontalAlignment: Text.AlignRight
                    }
                }

                // Three readable cards at current compact size, five at
                // user-selected wider sizes. Missing data stays explicitly
                // missing; source ownership remains with IauMeteorShowerService.
                Row {
                    id: meteorUpcomingRow
                    objectName: "cosmos-c25-meteor-next-peaks-row"
                    width: parent.width
                    height: 75
                    spacing: 5
                    Repeater {
                        model: meteorBoard.featuredCount
                        delegate: Rectangle {
                            id: peakCard
                            objectName: "cosmos-c25-meteor-peak-card"
                            required property int index
                            readonly property var shower:
                                index < meteorBoard.upcomingShowers.length
                                ? meteorBoard.upcomingShowers[index] : null
                            readonly property string showerName:
                                shower && shower.name ? String(shower.name) : ""
                            width: Math.max(1,(meteorUpcomingRow.width
                                -(meteorBoard.featuredCount-1)*meteorUpcomingRow.spacing)
                                /meteorBoard.featuredCount)
                            height: meteorUpcomingRow.height
                            color: Colors.dark
                            border.width: 1
                            border.color: showerName !== ""
                                && meteorBoard.selectedShowerName === showerName
                                ? Colors.yellow
                                : shower && shower.active ? Colors.magenta : Colors.cyan

                            Column {
                                anchors.fill: parent
                                anchors.margins: 5
                                spacing: 2
                                SecondaryText {
                                    width: parent.width
                                    height: 10
                                    text: "NEXT " + (peakCard.index+1)
                                    font.pixelSize: 8
                                    color: Colors.orange
                                }
                                GohuText {
                                    width: parent.width
                                    height: 12
                                    text: peakCard.showerName !== ""
                                        ? peakCard.showerName : "AWAITING SOURCE"
                                    font.pixelSize: 9
                                    color: Colors.white
                                    elide: Text.ElideRight
                                }
                                QuietText {
                                    width: parent.width
                                    height: 11
                                    text: peakCard.shower && peakCard.shower.peakUtc
                                        ? "PEAK " + String(peakCard.shower.peakUtc).slice(0,10)
                                        : "PEAK --"
                                    font.pixelSize: 8
                                    color: Colors.orange
                                    elide: Text.ElideRight
                                }
                                QuietText {
                                    width: parent.width
                                    height: 10
                                    text: peakCard.shower
                                        && peakCard.shower.daysToPeak !== null
                                        && peakCard.shower.daysToPeak !== undefined
                                        ? "IN " + Number(peakCard.shower.daysToPeak).toFixed(1)+" D"
                                        : "DAYS --"
                                    font.pixelSize: 8
                                    color: Colors.cyan
                                    elide: Text.ElideRight
                                }
                                QuietText {
                                    width: parent.width
                                    height: 10
                                    text: peakCard.shower
                                        && peakCard.shower.ra !== null
                                        && peakCard.shower.ra !== undefined
                                        && peakCard.shower.dec !== null
                                        && peakCard.shower.dec !== undefined
                                        ? "RA " + Number(peakCard.shower.ra).toFixed(0)
                                          + "° / DEC " + Number(peakCard.shower.dec).toFixed(0)+"°"
                                        : "RADIANT --"
                                    font.pixelSize: 8
                                    color: Colors.cyan
                                    elide: Text.ElideRight
                                }
                            }
                            MouseArea {
                                anchors.fill: parent
                                enabled: peakCard.showerName !== ""
                                cursorShape: Qt.PointingHandCursor
                                onClicked: meteorBoard.jumpToShower(peakCard.showerName)
                            }
                        }
                    }
                }
                QuietText {
                    width: parent.width
                    height: visible ? 12 : 0
                    visible: !cosmosModePane.cards || cosmosModePane.cards.length === 0
                    text: cosmosModePane.sourceStatus === "SOURCE RECEIVED"
                        ? "NO ACTIVE OR UPCOMING SHOWER IN THE SOURCE WINDOW"
                        : (cosmosModePane.sourceStatus || "SOURCE WAITING")
                    color: Colors.orange
                    font.pixelSize: 8
                    elide: Text.ElideRight
                }
            }

            // A real contained scroll viewport with its own physical border
            // and scrollbar. Neither the cards nor page header move.
            Rectangle {
                id: meteorCatalogFrame
                objectName: "cosmos-c25-meteor-catalog-frame"
                anchors.top: pinnedMeteorHeader.bottom
                anchors.topMargin: 5
                anchors.bottom: meteorCaveat.top
                anchors.bottomMargin: 4
                anchors.left: parent.left
                anchors.right: parent.right
                color: Colors.black
                border.width: 1
                border.color: Colors.cyan
                clip: true
                // C29 // The image is a fixed peer of the bounded catalogue:
                // neither the NASA archival photograph nor the peak meter
                // scrolls with the shower cards.
                StationCosmosMeteorVisual {
                    id: meteorVisual
                    objectName: "cosmos-c29-meteor-image-panel"
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    anchors.left: parent.left
                    width: parent.width >= 320
                        ? Math.min(220,parent.width*0.44) : 0
                    visible: width > 0
                    sourceReady: !!cosmosModePane.meteorSource
                        && cosmosModePane.meteorSource.ready
                    upcomingShowers: meteorBoard.upcomingShowers
                    selectedShowerName: meteorBoard.selectedShowerName
                    onExpandRequested: meteorBoard.imageExpanded = true
                }
                GohuText {
                    id: meteorCatalogTitle
                    anchors.top: parent.top
                    anchors.topMargin: 4
                    anchors.left: meteorVisual.right
                    anchors.leftMargin: 6
                    anchors.right: parent.right
                    anchors.rightMargin: 7
                    height: 13
                    text: "SHOWER CATALOG // ACTIVE + UPCOMING"
                    color: Colors.magenta
                    font.pixelSize: 9
                    elide: Text.ElideRight
                }
                Flickable {
                    id: meteorScroll
                    objectName: "cosmos-c25-meteor-catalog-scroll"
                    anchors.top: meteorCatalogTitle.bottom
                    anchors.topMargin: 3
                    anchors.left: meteorVisual.right
                    anchors.leftMargin: 5
                    anchors.right: parent.right
                    anchors.rightMargin: 12
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: 5
                    clip: true
                    contentWidth: width
                    contentHeight: meteorCards.implicitHeight
                    boundsBehavior: Flickable.StopAtBounds
                    Column {
                        id: meteorCards
                        width: meteorScroll.width
                        spacing: 5
                        Repeater {
                            model: cosmosModePane.cards ? cosmosModePane.cards.length : 0
                            delegate: Rectangle {
                                objectName: "cosmos-c5-meteor-card"
                                required property int index
                                readonly property var cardData: cosmosModePane.cards[index]
                                width: meteorCards.width
                                height: 47
                                color: Colors.dark
                                border.width: 1
                                border.color: cardData
                                    && meteorBoard.selectedShowerName === cardData.name
                                    ? Colors.yellow : Colors.magenta
                                Column {
                                    anchors.fill: parent
                                    anchors.margins: 6
                                    spacing: 4
                                    GohuText {
                                        width: parent.width
                                        text: cardData.name+" // "+cardData.info
                                        color: Colors.white
                                        font.pixelSize: 10
                                        elide: Text.ElideRight
                                    }
                                    QuietText {
                                        width: parent.width
                                        text: cardData.detail
                                        color: Colors.cyan
                                        font.pixelSize: 9
                                        elide: Text.ElideRight
                                    }
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: meteorBoard.selectedShowerName = parent.cardData.name
                                }
                            }
                        }
                    }
                }
                NeonScrollBar {
                    flickable: meteorScroll
                    geometryHost: meteorCatalogFrame
                    handleStyle: "star"
                    visible: scrollable
                }
            }

            // C33 // Photo focus uses the existing Meteors stage, not a
            // new window or global fullscreen. Catalogue scroll and chosen
            // peak remain mounted underneath and are restored by BACK.
            StationCosmosPhotoFocus {
                objectName: "cosmos-c33-meteor-photo-focus"
                anchors.fill: parent
                z: 10
                visible: meteorBoard.imageExpanded && meteorVisual.showArchive
                sourceUrl: meteorVisual.archiveFrame ? meteorVisual.archiveFrame.url : ""
                photoTitle: meteorVisual.archiveFrame
                    ? meteorVisual.archiveFrame.name : "NASA METEOR ARCHIVE"
                credit: meteorVisual.archiveFrame
                    ? meteorVisual.archiveFrame.credit : "NASA"
                canNext: true
                canPlay: true
                playing: meteorVisual.playing
                onCloseRequested: meteorBoard.imageExpanded = false
                onNextRequested: meteorVisual.nextArchive()
                onPlayRequested: meteorVisual.playing = !meteorVisual.playing
            }

            QuietText {
                id: meteorCaveat
                anchors.bottom: parent.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                height: 12
                text: "IAU MDC // CATALOG CONTEXT // NOT OBSERVED LOCAL RATE OR ZHR"
                color: Colors.orange
                font.pixelSize: 8
                elide: Text.ElideRight
            }
        }
    }
}
