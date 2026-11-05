import QtQuick
import "../../components"
import "StationCosmosModePolicy.js" as Modes
import "StationCosmosPlanetEventPolicy.js" as ClockPolicy

// Fixed subject rail + one focused instrument. No whole-page scrolling.
// The IAU shower catalogue alone scrolls inside a bounded middle panel.
Rectangle {
    id: focus
    color: Colors.black
    clip: true
    property string subjectRoute: ""
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
        if (kind === "solar-path")
            return !!skyFeed && /^\d{4}-\d{2}-\d{2}$/.test(civilDate)
                && skyFeed.moonCivilOffsetMinutes !== null
                && skyFeed.moonCivilOffsetMinutes !== undefined
                && !!weatherService && weatherService.latitude !== ""
                && weatherService.longitude !== "";
        if (kind === "light")
            return !!twilight && twilight.available;
        if (kind === "planet-clock")
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
        kind === "planet-clock" ? planetSource
        : kind === "planets" || kind === "stars" ? celnav
        : kind === "meteors" ? meteorSource
        : kind === "eclipses" ? eclipseSource
        : kind === "iss" ? issSource : null
    readonly property string sourceStatus: {
        if (!Modes.usesSky(subjectRoute)) return "";
        if (!skyFeed) return "ASTRONOMY SOURCE HOST NOT LOADED";
        if (kind === "solar-path")
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
        if (selectedProvider.loading) return "SOURCE RECEIVING";
        if (selectedProvider.failed)
            return selectedProvider.errorText || "SOURCE REQUEST FAILED";
        if (selectedProvider.ready) return "SOURCE RECEIVED";
        return "SOURCE WAITING";
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
                    detail:"RISE "+String(item.rise.time)
                        +" // PEAK "+String(item.culminate.time)});
            }
        } else if (kind === "eclipses" && eclipseSource && eclipseSource.ready) {
            for (const row of [
                {name:"NEXT SOLAR",data:eclipseSource.nextSolar},
                {name:"NEXT LUNAR",data:eclipseSource.nextLunar}
            ]) rows.push({name:row.name,
                info:row.data ? row.data.event : "NO EVENT IN WINDOW",
                detail:row.data ? String(row.data.date) : "DATE --"});
        } else if (kind === "meteors" && meteorSource && meteorSource.ready) {
            for (i=0;i<meteorSource.upcomingShowers.length;i++) {
                item=meteorSource.upcomingShowers[i];
                rows.push({name:item.name,
                    info:item.active ? "ACTIVE NOW" : "UPCOMING",
                    detail:"PEAK "+String(item.peakUtc)});
            }
        }
        return rows;
    }

    Loader {
        id: skyLoader
        active: focus.visible && Modes.usesSky(focus.subjectRoute)
        width: 1
        height: 1
        opacity: 0
        z: -1
        sourceComponent: Component {
            StationSky {
                sourceOnly: true
                subjectRoute: Modes.dataRoute(focus.subjectRoute || "")
                weatherService: focus.weatherService
                spaceService: focus.spaceService
                runtimeNowMs: focus.runtimeNowMs || 0
            }
        }
    }

    // One hidden owner for the selected NOAA source. Rendering it is
    // disabled, including the original SUVI Image network consumer.
    Loader {
        id: spaceSourceLoader
        active: focus.visible && focus.kind === "solar-section"
        width: 1
        height: 1
        opacity: 0
        z: -1
        sourceComponent: Component {
            StationSpace {
                sourceOnly: true
                subjectRoute: Modes.dataRoute(focus.subjectRoute)
                spaceService: focus.spaceService
                weatherService: focus.weatherService
                liveHistoryStore: focus.liveHistoryStore
                runtimeNowMs: focus.runtimeNowMs
            }
        }
    }

    GohuText {
        id: titleText
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 6
        height: 18
        text: "COSMOS // "+focus.family.toUpperCase()
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
            model: focus.modes || []
            delegate: ActionButton {
                required property var modelData
                width: Math.max(1,(modeRail.width
                    -(focus.modeCount-1)*modeRail.spacing)
                    /Math.max(1,focus.modeCount))
                height: 27
                label: modelData.label
                labelPixelSize: focus.modeCount>5 ? 9 : 10
                contentPadding: 1
                selected: Modes.canonical(focus.subjectRoute) === modelData.route
                accentColor: Colors.cyan
                onClicked: focus.routeRequested(modelData.route)
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
            active: focus.visible
            sourceComponent: focus.kind === "solar-path" ? sunPath
                : focus.kind === "light" ? sunLight
                : focus.kind === "planet-clock" ? planetClock
                : focus.kind === "solar-section" ? solarDetails
                : focus.kind === "meteors" ? meteorList
                : subjectCards
        }
        // An unavailable solar forecast must not leave a blank graph without
        // saying which upstream payload is missing.
        QuietText {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.verticalCenter: parent.verticalCenter
            width: Math.max(1,stage.width-32)
            visible: (focus.kind === "solar-path" || focus.kind === "light")
                && !focus.sourceConfigured
            text: focus.sourceStatus
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
            width: Math.max(0,footer.width-111)
            text: focus.kind === "meteors" ? "IAU MDC // SCROLL MIDDLE ONLY"
                : focus.kind === "solar-section" ? "NOAA // ONE INSTRUMENT"
                : "SOURCE-BACKED // FOCUSED VIEW"
            color: Colors.cyan
            font.pixelSize: 8
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        ActionButton {
            width: 105
            height: 19
            contentPadding: 1
            label: "FULL REFERENCE"
            labelPixelSize: 8
            accentColor: Colors.yellow
            onClicked: focus.routeRequested(Modes.fullRoute(focus.subjectRoute))
        }
    }

    Component {
        id: solarDetails
        StationCosmosSunInstrumentPane {
            modeRoute: Modes.dataRoute(focus.subjectRoute)
            sourceSpace: focus.spaceFeed
            spaceService: focus.spaceService
        }
    }
    Component {
        id: sunPath
        Column {
            anchors.fill: parent
            spacing: 6
            StationCosmosVisualInstruments {
                width: parent.width
                height: parent.height >= 270 ? 204 : parent.height
                compactMode: true
                showMoon: false
                showSun: true
                astronomySummary: focus.astronomy
                twilightSummary: focus.twilight
                currentSolarPosition: focus.skyFeed
                    ? focus.skyFeed.currentSolarPosition : null
                providerLocalMinute: focus.skyFeed
                    ? focus.skyFeed.providerLocalMinute : -1
                solarDate: focus.civilDate || ""
                solarCivilOffsetMinutes: focus.skyFeed
                    ? focus.skyFeed.moonCivilOffsetMinutes : null
                solarOffsetSource: focus.skyFeed
                    ? focus.skyFeed.moonCivilOffsetSource : "UNKNOWN"
                latitude: focus.weatherService ? focus.weatherService.latitude : ""
                longitude: focus.weatherService ? focus.weatherService.longitude : ""
            }
            Row {
                visible: parent.height >= 270
                height: visible ? 40 : 0
                width: parent.width
                spacing: 5
                Repeater {
                    model: [
                        {name:"SUNRISE",value:focus.astronomy ? focus.astronomy.sunrise : "--"},
                        {name:"SUNSET",value:focus.astronomy ? focus.astronomy.sunset : "--"},
                        {name:"DAYLIGHT",value:focus.astronomy ? focus.astronomy.daylightLabel : "--"}
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
                    {name:"ASTRONOMICAL DAWN",value:focus.twilight ? focus.twilight.astronomicalDawn : "--"},
                    {name:"CIVIL DAWN",value:focus.twilight ? focus.twilight.civilDawn : "--"},
                    {name:"SOLAR NOON",value:focus.twilight ? focus.twilight.solarNoon : "--"},
                    {name:"CIVIL DUSK",value:focus.twilight ? focus.twilight.civilDusk : "--"},
                    {name:"BLUE AM",value:focus.twilight ? focus.twilight.blueMorningStart+" → "+focus.twilight.blueMorningEnd : "--"},
                    {name:"GOLDEN AM",value:focus.twilight ? focus.twilight.goldenMorningStart+" → "+focus.twilight.goldenMorningEnd : "--"},
                    {name:"GOLDEN PM",value:focus.twilight ? focus.twilight.goldenEveningStart+" → "+focus.twilight.goldenEveningEnd : "--"},
                    {name:"BLUE PM",value:focus.twilight ? focus.twilight.blueEveningStart+" → "+focus.twilight.blueEveningEnd : "--"}
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
        id: planetClock
        Column {
            readonly property int renderedRowCount: clockRepeater.count
            anchors.fill: parent
            spacing: 5
            GohuText {
                width: parent.width
                height: 19
                text: "PLANET CLOCK // USNO RISE / TRANSIT / SET"
                color: Colors.magenta
                font.pixelSize:11
            }
            Repeater {
                id: clockRepeater
                model: focus.displayedPlanetRows || []
                delegate: Rectangle {
                    required property var modelData
                    width: parent.width
                    height: Math.max(26,(stage.height-53)/5)
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.cyan
                    Row {
                        anchors.fill: parent
                        anchors.margins: 5
                        spacing: 7
                        GohuText {
                            width: 65
                            text: modelData.name
                            color: Colors.orange
                            font.pixelSize: 10
                            elide: Text.ElideRight
                        }
                        Rectangle {
                            id: clockLane
                            width: Math.max(1,parent.width-77)
                            height: 15
                            color: Colors.black
                            border.width: 1
                            border.color: Colors.magenta
                            Repeater {
                                model: modelData.events
                                delegate: Rectangle {
                                    required property var modelData
                                    x: 2+modelData.minute/1440*Math.max(0,clockLane.width-10)
                                    y: 2
                                    width: 6
                                    height: 9
                                    color: modelData.kind==="rise" ? Colors.cyan
                                        : modelData.kind==="transit" ? Colors.yellow
                                        : Colors.magenta
                                }
                            }
                        }
                    }
                }
            }
            QuietText {
                width: parent.width
                text: focus.sourceStatus
                    + (focus.civilDate !== "" ? " // "+focus.civilDate : "")
                visible: focus.sourceStatus !== "SOURCE RECEIVED"
                color: Colors.orange
                font.pixelSize: 9
                elide: Text.ElideRight
            }
            QuietText {
                width:parent.width
                text:"CYAN RISE // YELLOW TRANSIT // MAGENTA SET // 24-HOUR CIVIL DAY"
                color:Colors.cyan
                font.pixelSize:9
                elide:Text.ElideRight
            }
        }
    }
    Component {
        id: subjectCards
        Column {
            anchors.fill: parent
            spacing: 8
            GohuText {
                text: focus.kind==="planets" ? "PLANETS // CURRENT USNO SKY"
                    : focus.kind==="stars" ? "CONSTELLATION ANCHORS // USNO"
                    : focus.kind==="eclipses" ? "ECLIPSES // NASA GSFC"
                    : "ISS // PREDICTED PASSES"
                color: Colors.magenta
                font.pixelSize:11
            }
            QuietText {
                width: parent.width
                visible: !focus.cards || focus.cards.length === 0
                text: focus.sourceStatus
                color: Colors.orange
                font.pixelSize: 10
                wrapMode: Text.WordWrap
            }
            Grid {
                id: cardGrid
                width: parent.width
                columns: 2
                spacing: 7
                Repeater {
                    model: focus.cards ? focus.cards.slice(0,4) : []
                    delegate: Rectangle {
                        required property var modelData
                        width: Math.max(1,(cardGrid.width-7)/2)
                        height: Math.max(65,(stage.height-53)/2)
                        color: Colors.dark
                        border.width: 1
                        border.color: Colors.cyan
                        Column {
                            anchors.fill: parent
                            anchors.margins: 8
                            spacing: 6
                            GohuText {
                                width: parent.width
                                text: modelData.name
                                color: Colors.orange
                                font.pixelSize: 12
                                elide: Text.ElideRight
                            }
                            QuietText {
                                width: parent.width
                                text: modelData.info
                                font.pixelSize: 10
                                elide: Text.ElideRight
                            }
                            QuietText {
                                width: parent.width
                                text: modelData.detail
                                font.pixelSize: 9
                                wrapMode: Text.WordWrap
                            }
                        }
                    }
                }
            }
            QuietText {
                width:parent.width
                text:(!focus.cards || focus.cards.length===0) ? "SOURCE WAITING / NO DATA IN WINDOW"
                    : focus.kind==="eclipses"
                    ? "GLOBAL EVENT DATE // LOCAL VISIBILITY NOT CALCULATED"
                    : "OBSERVATIONS / PREDICTIONS ARE SOURCE-SCOPED"
                color:Colors.cyan
                font.pixelSize:9
                elide:Text.ElideRight
            }
        }
    }
    Component {
        id: meteorList
        Column {
            anchors.fill: parent
            spacing: 7
            GohuText {
                height:20
                text:"METEOR SHOWERS // IAU MDC"
                color:Colors.magenta
                font.pixelSize:12
            }
            QuietText {
                width: parent.width
                visible: focus.cards.length === 0
                text: focus.sourceStatus === "SOURCE RECEIVED"
                    ? "NO ACTIVE OR UPCOMING SHOWER IN THE SOURCE WINDOW"
                    : focus.sourceStatus
                color: Colors.orange
                font.pixelSize: 10
                wrapMode: Text.WordWrap
            }
            Flickable {
                id: meteorScroll
                width: parent.width
                height: Math.max(0,parent.height-48)
                clip: true
                contentWidth: width
                contentHeight: meteorCards.implicitHeight
                boundsBehavior: Flickable.StopAtBounds
                Column {
                    id: meteorCards
                    width: meteorScroll.width
                    spacing: 5
                    Repeater {
                        model: focus.cards || []
                        delegate: Rectangle {
                            required property var modelData
                            width: meteorCards.width
                            height: 47
                            color: Colors.dark
                            border.width: 1
                            border.color: Colors.magenta
                            Column {
                                anchors.fill:parent
                                anchors.margins:6
                                spacing:4
                                GohuText {
                                    width:parent.width
                                    text:modelData.name+" // "+modelData.info
                                    color:Colors.white
                                    font.pixelSize:10
                                    elide:Text.ElideRight
                                }
                                QuietText {
                                    text:modelData.detail
                                    color:Colors.cyan
                                    font.pixelSize:9
                                }
                            }
                        }
                    }
                }
            }
            QuietText {
                text:"CATALOG CONTEXT // NOT OBSERVED LOCAL RATE OR ZHR"
                color:Colors.orange
                font.pixelSize:9
            }
        }
    }
}
