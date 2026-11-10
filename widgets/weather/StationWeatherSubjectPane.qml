import QtQuick
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
            Flickable {
                anchors.fill: parent
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                contentWidth: width
                contentHeight: Math.max(height, servicesContent.y + servicesContent.implicitHeight + 10)
                Column {
                    id: servicesContent
                    x: 12
                    y: 10
                    width: Math.max(0, parent.width - 24)
                    spacing: 14
                    StationRuntimeRack {
                        objectName: "weather-w4-sky-rack"
                        title: "WEATHER SERVICES // SKY + ATMOSPHERE"
                        rows: weatherServicesSky.item ? weatherServicesSky.item.runtimeRows : []
                    }
                    StationRuntimeRack {
                        objectName: "weather-w4-ground-rack"
                        title: "WEATHER SERVICES // GROUND + HAZARDS"
                        rows: weatherServicesGround.item ? weatherServicesGround.item.runtimeRows : []
                    }
                }
            }
        }
    }

    Component {
        id: skyPanel
        StationSky {
            subjectRoute: weatherPane.subjectRoute
            weatherService: weatherPane.weatherService
            runtimeNowMs: weatherPane.runtimeNowMs
        }
    }
}
