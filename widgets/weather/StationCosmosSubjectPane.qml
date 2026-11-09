import QtQuick
import "StationCosmosSubjectPanelPolicy.js" as CosmosPanelPolicy
import "StationCosmosModePolicy.js" as Modes

// Reuses existing SKY and SPACE QML instruments. No copied collectors,
// cache writers or provider ownership. CLASSIC routes keep their own loaders.
Rectangle {
    id: cosmosPane
    color: Colors.black

    property string subjectRoute: ""
    property var weatherService: null
    property var spaceService: null
    property var liveHistoryStore: null
    property real runtimeNowMs: Date.now()
    signal routeRequested(string path)

    readonly property string kind:
        CosmosPanelPolicy.kindForRoute(subjectRoute)

    Loader {
        id: cosmosLoader
        anchors.fill: parent
        active: cosmosPane.visible && cosmosPane.kind !== ""
        sourceComponent: Modes.family(cosmosPane.subjectRoute) !== ""
                         ? focusModesComponent
                         : cosmosPane.kind === "overview"
                         ? overviewComponent
                         : cosmosPane.subjectRoute === "cosmos/moon/ephemeris"
                         ? moonCompactComponent
                         : cosmosPane.subjectRoute === "cosmos/moon/year"
                         ? moonYearComponent
                         : cosmosPane.subjectRoute === "cosmos/moon/forecast"
                         ? moonForecastComponent
                         : cosmosPane.kind === "sky" ? skyComponent
                         : cosmosPane.subjectRoute === "cosmos/space-weather/overview"
                           ? spaceHubComponent
                         : cosmosPane.subjectRoute === "cosmos/space-weather/geomagnetic"
                           ? geomagneticComponent
                         : cosmosPane.subjectRoute === "cosmos/space-weather/solar-wind"
                           ? solarWindComponent
                         : cosmosPane.subjectRoute === "cosmos/space-weather/history"
                           ? spaceTimelineComponent
                         : spaceComponent
    }

    // SPACE bottom tab now opens a compact directory; the full report
    // stays available through the original INDEX route.
    Component {
        id: spaceHubComponent
        StationCosmosSpaceWeatherHubPane {
            spaceService: cosmosPane.spaceService
            weatherService: cosmosPane.weatherService
            liveHistoryStore: cosmosPane.liveHistoryStore
            runtimeNowMs: cosmosPane.runtimeNowMs
            onRouteRequested: function(path) {
                cosmosPane.routeRequested(path)
            }
        }
    }

    Component {
        id: geomagneticComponent
        StationCosmosGeomagneticPane {
            spaceService: cosmosPane.spaceService
            weatherService: cosmosPane.weatherService
            liveHistoryStore: cosmosPane.liveHistoryStore
            runtimeNowMs: cosmosPane.runtimeNowMs
            onRouteRequested: function(path) {
                cosmosPane.routeRequested(path)
            }
        }
    }

    // C5 // One fixed mode strip owns all SUN/ASTRONOMY/EVENTS switching.
    // SOURCE-only SKY and route-selected NOAA readers are inside that pane.
    Component {
        id: focusModesComponent
        StationCosmosModesPane {
            subjectRoute: cosmosPane.subjectRoute
            weatherService: cosmosPane.weatherService
            spaceService: cosmosPane.spaceService
            liveHistoryStore: cosmosPane.liveHistoryStore
            runtimeNowMs: cosmosPane.runtimeNowMs
            onRouteRequested: function(path) {
                cosmosPane.routeRequested(path)
            }
        }
    }

    // C8 // The MOON landing uses the existing compact MAGICK-derived
    // instrument and the original source-only SKY collectors. No scroll.
    // The INDEX/full SKY and explicit moon-position routes remain untouched.
    Component {
        id: moonCompactComponent
        StationCosmosMoonCompactPane {
            weatherService: cosmosPane.weatherService
            spaceService: cosmosPane.spaceService
            runtimeNowMs: cosmosPane.runtimeNowMs
            onRouteRequested: function(path) {
                cosmosPane.routeRequested(path)
            }
        }
    }

    Component {
        id: moonYearComponent
        StationCosmosAnnualWheelPane {
            subject: "moon"
            weatherService: cosmosPane.weatherService
            runtimeNowMs: cosmosPane.runtimeNowMs
            onRouteRequested: function(path) {
                cosmosPane.routeRequested(path)
            }
        }
    }

    // C17 // Forecast is a second view of MAGICK's existing annual
    // calendar host, but it never activates the JPL annual calculation.
    Component {
        id: moonForecastComponent
        StationCosmosAnnualWheelPane {
            subject: "moon"
            moonView: "forecast"
            weatherService: cosmosPane.weatherService
            runtimeNowMs: cosmosPane.runtimeNowMs
            onRouteRequested: function(path) {
                cosmosPane.routeRequested(path)
            }
        }
    }

    Component {
        id: skyComponent
        StationSky {
            subjectRoute: cosmosPane.subjectRoute
            weatherService: cosmosPane.weatherService
            spaceService: cosmosPane.spaceService
            runtimeNowMs: cosmosPane.runtimeNowMs
            onRouteRequested: function(path) {
                cosmosPane.routeRequested(path)
            }
        }
    }

    Component {
        id: spaceComponent
        StationSpace {
            subjectRoute: cosmosPane.subjectRoute
            spaceService: cosmosPane.spaceService
            weatherService: cosmosPane.weatherService
            liveHistoryStore: cosmosPane.liveHistoryStore
            runtimeNowMs: cosmosPane.runtimeNowMs
        }
    }

    Component {
        id: spaceTimelineComponent
        StationSpaceWeatherTimelinePane {
            subjectRoute: cosmosPane.subjectRoute
            spaceService: cosmosPane.spaceService
            weatherService: cosmosPane.weatherService
            liveHistoryStore: cosmosPane.liveHistoryStore
            runtimeNowMs: cosmosPane.runtimeNowMs
        }
    }

    // C3 // Focused solar-wind route, independent of the long SPACE report.
    Component {
        id: solarWindComponent
        StationCosmosSolarWindPane {
            spaceService: cosmosPane.spaceService
            liveHistoryStore: cosmosPane.liveHistoryStore
            runtimeNowMs: cosmosPane.runtimeNowMs
            onRouteRequested: function(path) {
                cosmosPane.routeRequested(path)
            }
        }
    }

    // C2 // Overview is a single non-scrolling, card-based observation bay.
    // Existing full SKY and SPACE routes above remain unchanged.
    Component {
        id: overviewComponent
        StationCosmosOverviewPane {
            weatherService: cosmosPane.weatherService
            spaceService: cosmosPane.spaceService
            runtimeNowMs: cosmosPane.runtimeNowMs
            onRouteRequested: function(path) {
                cosmosPane.routeRequested(path)
            }
        }
    }
}
