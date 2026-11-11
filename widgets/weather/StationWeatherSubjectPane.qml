import QtQuick
import "../../components"
import "StationWeatherSubjectPanelPolicy.js" as WeatherPanelPolicy

// One live, route-filtered WEATHER page at a time. Reuses CLASSIC StationGround
// and StationSky components with the existing shared sources; no new collectors.
Rectangle {
    id: weatherPane
    color: Colors.black
    property string subjectRoute: ""
    signal routeRequested(string path)
    property var weatherService: null
    property var nwsAlertSource: null
    property var historyService: null
    property var seismicSource: null
    property var lightningSource: null
    property var riverSource: null
    property var persistentCacheStore: null
    property var liveHistoryStore: null
    property var homeFavoritesStore: null
    property real runtimeNowMs: Date.now()

    readonly property string kind:
        WeatherPanelPolicy.kindForRoute(subjectRoute)
    readonly property alias activePanelLoader: panelLoader
    readonly property var runtimeRows:
        kind === "map" && panelLoader.item
        && Array.isArray(panelLoader.item.runtimeRows)
        ? panelLoader.item.runtimeRows : []

    Loader {
        id: panelLoader
        anchors.fill: parent
        active: weatherPane.visible && weatherPane.kind !== ""
        sourceComponent: weatherPane.kind === "ground"
                         ? groundPanel : weatherPane.kind === "home"
                         ? homePanel : weatherPane.kind === "map"
                         ? mapPanel : weatherPane.kind === "services"
                         ? servicesPanel : skyPanel
    }

    Component {
        id: homePanel
        StationHome {
            subjectRoute: weatherPane.subjectRoute
            weatherService: weatherPane.weatherService
            // No cross-domain solar/Kp data is presented as WEATHER.
            spaceService: null
            nwsAlertSource: weatherPane.nwsAlertSource
            historyService: weatherPane.historyService
            liveHistoryStore: weatherPane.liveHistoryStore
            homeFavoritesStore: weatherPane.homeFavoritesStore
            runtimeNowMs: weatherPane.runtimeNowMs
        }
    }

    Component {
        id: mapPanel
        StationDiscovery {
            domain: "map"
            weatherMapOnly: true
            weatherMapRoute: weatherPane.subjectRoute
            stationOpen: weatherPane.visible
            seismicSource: weatherPane.seismicSource
            lightningSource: weatherPane.lightningSource
            riverSource: weatherPane.riverSource
            weatherService: weatherPane.weatherService
            persistentCacheStore: weatherPane.persistentCacheStore
            runtimeNowMs: weatherPane.runtimeNowMs
        }
    }

    Component {
        id: groundPanel
        StationGround {
            subjectRoute: weatherPane.subjectRoute
            onRouteRequested: function(path) { weatherPane.routeRequested(path); }
            weatherService: weatherPane.weatherService
            nwsAlertSource: weatherPane.nwsAlertSource
            seismicSource: weatherPane.seismicSource
            lightningSource: weatherPane.lightningSource
            riverSource: weatherPane.riverSource
            persistentCacheStore: weatherPane.persistentCacheStore
            liveHistoryStore: weatherPane.liveHistoryStore
            runtimeNowMs: weatherPane.runtimeNowMs
        }
    }

    // W4: reuse the current SKY and GROUND runtime arrays. No new collectors.
    Component {
        id: servicesPanel
        Item {
            // Reuse the existing single SKY/GROUND component definitions.
            // These only exist while SERVICES is selected; no new collector.
            Loader {
                id: weatherServicesSky
                active: true
                visible: false
                sourceComponent: skyPanel
            }
            Loader {
                id: weatherServicesGround
                active: true
                visible: false
                sourceComponent: groundPanel
            }
            StationWeatherServicesPane {
                anchors.fill: parent
                skyRows: weatherServicesSky.item
                    ? weatherServicesSky.item.runtimeRows : []
                groundRows: weatherServicesGround.item
                    ? weatherServicesGround.item.runtimeRows : []
            }
        }
    }

    // W10 // Same one SKY renderer and source lifetime, with two compact
    // internal screens. WEATHER combines original data/artwork across three
    // fixed bands; TWILIGHT reuses SKY's complete calculations plus the
    // existing COSMOS 24h solar altitude instrument. No new collectors.
    Component {
        id: skyPanel
        Item {
            id: skyHost
            objectName: "weather-w10-terminal-host"
            readonly property bool combined:
                weatherPane.subjectRoute === "weather/conditions/current"
            property string activeInstrument: "weather"
            onCombinedChanged: {
                if (combined) activeInstrument = "weather";
            }
            readonly property var runtimeRows: originalSky.runtimeRows
            readonly property alias renderer: originalSky
            readonly property alias viewport: instrumentViewport
            readonly property alias pageRail: instrumentRail
            readonly property alias combinedPanel: combinedDisplay
            readonly property alias solarVisual: solarChart

            Row {
                id: instrumentRail
                objectName: "weather-w10-two-page-rail"
                visible: skyHost.combined
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                height: visible ? 26 : 0
                spacing: 4
                Repeater {
                    model: [
                        {label:"WEATHER // CURRENT + FORECAST",focus:"weather"},
                        {label:"TWILIGHT // SOLAR",focus:"twilight"}
                    ]
                    delegate: ActionButton {
                        required property var modelData
                        width: Math.max(1,(instrumentRail.width-4)/2)
                        height: 24
                        label: modelData.label
                        labelPixelSize: 10
                        accentColor: Colors.cyan
                        selected: skyHost.activeInstrument === modelData.focus
                        onClicked: skyHost.activeInstrument = modelData.focus
                    }
                }
            }

            Item {
                id: instrumentViewport
                objectName: "weather-w10-fixed-instrument-viewport"
                anchors.top: instrumentRail.bottom
                anchors.topMargin: skyHost.combined ? 3 : 0
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                clip: true

                // Original SKY is still the sole calculation/forecast renderer
                // and remains loaded for source state and hour inspection.
                // Its old full visual remains untouched for INDEX deep links.
                StationSky {
                    id: originalSky
                    objectName: "weather-w10-original-sky"
                    subjectRoute: weatherPane.subjectRoute
                    weatherFocus: skyHost.combined
                        ? (skyHost.activeInstrument === "twilight"
                           ? "twilight" : "dashboard") : ""
                    weatherService: weatherPane.weatherService
                    runtimeNowMs: weatherPane.runtimeNowMs
                    visible: !skyHost.combined
                        || skyHost.activeInstrument === "twilight"
                    width: skyHost.combined ? 800 : instrumentViewport.width
                    height: skyHost.combined ? 800 : instrumentViewport.height
                    transformOrigin: Item.TopLeft
                    scale: skyHost.combined
                        ? Math.min(1,
                            instrumentViewport.width/Math.max(1,width),
                            twilightTextArea.height
                                / Math.max(1,focusedContentHeight))
                        : 1
                    x: skyHost.combined
                        ? Math.max(0,(instrumentViewport.width-width*scale)/2)
                        : 0
                    // TWILIGHT stays at the TOP, never vertically centered.
                    y: 0
                }

                StationWeatherCombinedPane {
                    id: combinedDisplay
                    objectName: "weather-w10-combined-display"
                    anchors.fill: parent
                    visible: skyHost.combined
                        && skyHost.activeInstrument === "weather"
                    sky: originalSky
                }

                Item {
                    id: twilightTextArea
                    objectName: "weather-w10-twilight-text-area"
                    visible: skyHost.combined
                        && skyHost.activeInstrument === "twilight"
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right
                    height: visible ? Math.max(90,
                          instrumentViewport.height*0.50) : 0
                }

                Item {
                    id: solarGraphArea
                    objectName: "weather-w10-solar-graph-area"
                    visible: skyHost.combined
                        && skyHost.activeInstrument === "twilight"
                    anchors.top: twilightTextArea.bottom
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    clip: true

                    // Existing interactive solar-altitude curve. It samples
                    // the calibrated TwilightPolicy model, not a new feed.
                    StationCosmosVisualInstruments {
                        id: solarChart
                        objectName: "weather-w10-existing-solar-graph"
                        width: 680
                        height: 204
                        compactMode: true
                        showMoon: false
                        showSun: true
                        moonReady: false
                        moonEphemeris: null
                        astronomySummary: originalSky.astronomySummary
                        twilightSummary: originalSky.twilightSummary
                        currentSolarPosition: originalSky.currentSolarPosition
                        providerLocalMinute: originalSky.providerLocalMinute
                        solarDate: originalSky.astronomySummary.date
                        solarCivilOffsetMinutes: originalSky.moonCivilOffsetMinutes
                        solarOffsetSource: originalSky.moonCivilOffsetSource
                        latitude: weatherPane.weatherService
                            ? weatherPane.weatherService.latitude : ""
                        longitude: weatherPane.weatherService
                            ? weatherPane.weatherService.longitude : ""
                        transformOrigin: Item.TopLeft
                        scale: Math.min(1,
                            solarGraphArea.width/Math.max(1,width),
                            solarGraphArea.height/Math.max(1,height))
                        x: Math.max(0,(solarGraphArea.width-width*scale)/2)
                        y: 0
                    }
                }
            }
        }
    }
}
