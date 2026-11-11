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

    // W9 // The five bottom WEATHER modes remain unchanged. Inside the
    // combined WEATHER mode, a pinned four-button rail swaps original
    // instruments without a tall scroll column or duplicate source owner.
    // Historical INDEX routes still render the original unmodified SKY.
    Component {
        id: skyPanel
        Item {
            id: skyHost
            objectName: "weather-w9-fixed-terminal-host"
            readonly property bool combined:
                weatherPane.subjectRoute === "weather/conditions/current"
            property string focus: "now"
            onCombinedChanged: {
                if (combined) focus = "now";
            }
            readonly property var runtimeRows: originalSky.runtimeRows
            readonly property alias renderer: originalSky
            readonly property alias viewport: instrumentViewport
            readonly property alias pageRail: instrumentRail

            Row {
                id: instrumentRail
                objectName: "weather-w9-fixed-page-rail"
                visible: skyHost.combined
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                height: visible ? 26 : 0
                spacing: 4
                Repeater {
                    model: [
                        {label:"NOW + AIR",focus:"now"},
                        {label:"HOURLY",focus:"hourly"},
                        {label:"DAILY",focus:"daily"},
                        {label:"TWILIGHT",focus:"twilight"}
                    ]
                    delegate: ActionButton {
                        required property var modelData
                        width: Math.max(1,(instrumentRail.width-12)/4)
                        height: 24
                        label: modelData.label
                        labelPixelSize: 10
                        accentColor: Colors.cyan
                        selected: skyHost.focus === modelData.focus
                        onClicked: skyHost.focus = modelData.focus
                    }
                }
            }

            Item {
                id: instrumentViewport
                objectName: "weather-w9-fixed-instrument-viewport"
                anchors.top: instrumentRail.bottom
                anchors.topMargin: skyHost.combined ? 3 : 0
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                clip: true

                // Uniformly scale the EXISTING graphics, preserving text,
                // icons, hourly selection, forecast artwork and meters.
                // No internal scroll or synthetic replacement visuals.
                StationSky {
                    id: originalSky
                    objectName: "weather-w9-original-sky"
                    subjectRoute: weatherPane.subjectRoute
                    weatherFocus: skyHost.combined ? skyHost.focus : ""
                    weatherService: weatherPane.weatherService
                    runtimeNowMs: weatherPane.runtimeNowMs
                    width: skyHost.combined
                           ? (skyHost.focus === "now" ? 860
                              : skyHost.focus === "hourly" ? 790
                              : skyHost.focus === "daily" ? 750 : 800)
                           : instrumentViewport.width
                    height: skyHost.combined ? 800 : instrumentViewport.height
                    transformOrigin: Item.TopLeft
                    scale: skyHost.combined
                           ? Math.min(1,
                               instrumentViewport.width / Math.max(1,width),
                               instrumentViewport.height
                                   / Math.max(1,focusedContentHeight))
                           : 1
                    x: skyHost.combined
                       ? Math.max(0,(instrumentViewport.width-width*scale)/2)
                       : 0
                    y: skyHost.combined
                       ? Math.max(0,(instrumentViewport.height
                                     -focusedContentHeight*scale)/2)
                       : 0
                }
            }
        }
    }
}
