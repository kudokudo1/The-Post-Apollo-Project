import QtQuick
import "StationWeatherSubjectPanelPolicy.js" as WeatherPanelPolicy

// One live, route-filtered WEATHER page at a time. Reuses CLASSIC StationGround
// and StationSky components with the existing shared sources; no new collectors.
Rectangle {
    id: weatherPane
    color: Colors.black
    property string subjectRoute: ""
    property var weatherService: null
    property var nwsAlertSource: null
    property var seismicSource: null
    property var lightningSource: null
    property var riverSource: null
    property var persistentCacheStore: null
    property var liveHistoryStore: null
    property real runtimeNowMs: Date.now()

    readonly property string kind:
        WeatherPanelPolicy.kindForRoute(subjectRoute)

    Loader {
        id: panelLoader
        anchors.fill: parent
        active: weatherPane.visible && weatherPane.kind !== ""
        sourceComponent: weatherPane.kind === "ground"
                         ? groundPanel : skyPanel
    }

    Component {
        id: groundPanel
        StationGround {
            subjectRoute: weatherPane.subjectRoute
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
