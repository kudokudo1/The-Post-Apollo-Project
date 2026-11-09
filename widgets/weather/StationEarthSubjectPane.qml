import QtQuick
import "StationEarthSubjectPanelPolicy.js" as EarthPanelPolicy

// EARTH is one persistent StationDiscovery map instance across its routes.
// Selected event, geographic viewport and the existing dossier/archival UI
// stay in that instance when changing from MAP to INVESTIGATIONS.
// No second source collector or archive writer is created.
Rectangle {
    id: earthPane
    color: Colors.black

    property string subjectRoute: ""
    // MEDIA-sourced article location context, not an EARTH source collector.
    property var newsMentionOverlay: null
    signal newsMapClearRequested()
    signal routeRequested(string path)
    property var nwsAlertSource: null
    property var liveHistoryStore: null
    property var seismicSource: null
    property var lightningSource: null
    property var riverSource: null
    property var weatherService: null
    property var persistentCacheStore: null
    property var eventArchiveStore: null
    property var dossierArchiveStore: null
    property real runtimeNowMs: Date.now()

    readonly property string kind:
        EarthPanelPolicy.kindForRoute(subjectRoute)
    readonly property var runtimeRows:
        earthPane.kind === "ground" && earthGroundLoader.item
            && Array.isArray(earthGroundLoader.item.runtimeRows)
        ? earthGroundLoader.item.runtimeRows
        : earthLoader.item && Array.isArray(earthLoader.item.runtimeRows)
        ? earthLoader.item.runtimeRows : []

    // One map is kept mounted across EARTH tab switches to preserve
    // pan/zoom, manual source status and the selected event.
    Loader {
        id: earthLoader
        objectName: "earth-e2-one-persistent-map-owner"
        anchors.fill: parent
        active: earthPane.visible && earthPane.kind !== ""
        sourceComponent: earthMapComponent
    }

    Loader {
        id: earthGroundLoader
        objectName: "earth-e2-water-ground-router"
        anchors.fill: parent
        active: earthPane.visible && earthPane.kind === "ground"
        sourceComponent: earthPane.subjectRoute.indexOf("earth/water/") === 0
            ? earthWaterComponent : earthGroundComponent
    }

    StationEarthServicesPane {
        id: diagnostics
        objectName: "earth-e2-final-diagnostics"
        anchors.fill: parent
        visible: earthPane.kind === "services"
        runtimeRows: earthLoader.item ? earthLoader.item.runtimeRows : []
        sourceRows: earthLoader.item ? earthLoader.item.plannedSources : []
    }

    Component {
        id: earthMapComponent

        StationDiscovery {
            visible: earthPane.kind === "map"
                || earthPane.kind === "services"
            stationOpen: earthPane.visible
                && (earthPane.kind === "map"
                    || earthPane.kind === "services")
            domain: "map"
            // Only the exact full MAP route drops EARTH's layer filters.
            // All other EARTH routes keep their original source-scoped view.
            earthMapOnly: !EarthPanelPolicy.isFullMap(earthPane.subjectRoute)
            earthMapRoute: earthPane.kind === "services"
                ? "earth/maps/events" : earthPane.subjectRoute
            earthPinnedMap: EarthPanelPolicy.isPinnedMap(earthPane.subjectRoute)
            earthServicesOnly: earthPane.kind === "services"
            newsMentionOverlay: earthPane.newsMentionOverlay
            onNewsMapClearRequested: earthPane.newsMapClearRequested()

            seismicSource: earthPane.seismicSource
            lightningSource: earthPane.lightningSource
            riverSource: earthPane.riverSource
            weatherService: earthPane.weatherService
            persistentCacheStore: earthPane.persistentCacheStore
            eventArchiveStore: earthPane.eventArchiveStore
            dossierArchiveStore: earthPane.dossierArchiveStore
            runtimeNowMs: earthPane.runtimeNowMs
        }
    }

    Component {
        id: earthWaterComponent
        StationEarthWaterPane {
            subjectRoute: earthPane.subjectRoute
            weatherService: earthPane.weatherService
            nwsAlertSource: earthPane.nwsAlertSource
            seismicSource: earthPane.seismicSource
            lightningSource: earthPane.lightningSource
            riverSource: earthPane.riverSource
            persistentCacheStore: earthPane.persistentCacheStore
            liveHistoryStore: earthPane.liveHistoryStore
            runtimeNowMs: earthPane.runtimeNowMs
            onRouteRequested: function(path) { earthPane.routeRequested(path); }
        }
    }

    Component {
        id: earthGroundComponent
        StationGround {
            subjectRoute: earthPane.subjectRoute
            weatherService: earthPane.weatherService
            nwsAlertSource: earthPane.nwsAlertSource
            seismicSource: earthPane.seismicSource
            lightningSource: earthPane.lightningSource
            riverSource: earthPane.riverSource
            persistentCacheStore: earthPane.persistentCacheStore
            liveHistoryStore: earthPane.liveHistoryStore
            runtimeNowMs: earthPane.runtimeNowMs
            onRouteRequested: function(path) { earthPane.routeRequested(path); }
        }
    }
}
