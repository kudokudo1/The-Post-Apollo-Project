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
                         ? mapPanel : skyPanel
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

    Component {
        id: skyPanel
        StationSky {
            subjectRoute: weatherPane.subjectRoute
            weatherService: weatherPane.weatherService
            runtimeNowMs: weatherPane.runtimeNowMs
        }
    }
}
