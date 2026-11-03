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

    Loader {
        id: earthLoader
        anchors.fill: parent
        active: earthPane.visible && earthPane.kind === "map"
        sourceComponent: earthMapComponent
    }

    Component {
        id: earthMapComponent

        StationDiscovery {
            stationOpen: earthPane.visible
            domain: "map"
            earthMapOnly: true
            earthMapRoute: earthPane.subjectRoute
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
}
