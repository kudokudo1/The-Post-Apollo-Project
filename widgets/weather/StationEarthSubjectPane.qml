import QtQuick
import "../../components"
import "StationSubjectHeaderGeometry.js" as HeaderGeometry
import "StationEarthSubjectPanelPolicy.js" as EarthPanelPolicy

// EARTH is one persistent StationDiscovery map instance across its routes.
// Selected event, geographic viewport and the existing dossier/archival UI
// stay in that instance when changing from MAP to INVESTIGATIONS.
// No second source collector or archive writer is created.
Rectangle {
    id: earthPane
    color: Colors.black

    property string subjectRoute: ""
    // E4 // Local GROUND submode; the outer EARTH bottom-route stays stable.
    property string groundViewMode: "environment"
    readonly property bool overviewMode: subjectRoute === "earth/overview"
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
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: earthPane.overviewMode ? Math.floor(earthPane.height/2)
                                       : earthPane.height
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

    // E6 // The lower half of OVERVIEW is a read-only carousel. Its cards
    // only observe existing source QObjects; the persistent map stays above.
    StationEarthOverviewPane {
        id: overviewSummary
        objectName: "earth-e6-overview-lower-half"
        visible: earthPane.overviewMode
        anchors.top: earthLoader.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        weatherService: earthPane.weatherService
        riverSource: earthPane.riverSource
        nwsAlertSource: earthPane.nwsAlertSource
        seismicSource: earthPane.seismicSource
        onOpenTopicRequested: function(topicId) {
            if (topicId === "water") {
                earthPane.routeRequested("earth/water/rivers");
            } else if (topicId === "pollen" || topicId === "environment") {
                earthPane.groundViewMode = topicId === "pollen"
                    ? "air-pollen" : "environment";
                earthPane.routeRequested("earth/ground/full");
            }
        }
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
                || earthPane.overviewMode
            earthOverviewMode: earthPane.overviewMode
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

        // E4 // Two fixed pages over ONE original StationGround renderer.
        Rectangle {
            id: groundShell
            objectName: "earth-e4-ground-shell"
            color: Colors.black
            clip: true

            GohuText {
                id: groundTitle
                objectName: "earth-e4-ground-title"
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.margins: HeaderGeometry.inset
                height: HeaderGeometry.titleHeight
                text: "EARTH // GROUND"
                font.pixelSize: 12
                color: Colors.magenta
                verticalAlignment: Text.AlignVCenter
            }

            Row {
                id: groundModes
                objectName: "earth-e4-ground-tabs"
                anchors.top: groundTitle.bottom
                anchors.topMargin: HeaderGeometry.titleToTabs
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.leftMargin: HeaderGeometry.inset
                anchors.rightMargin: HeaderGeometry.inset
                height: HeaderGeometry.tabHeight
                spacing: HeaderGeometry.tabSpacing

                Repeater {
                    model: [
                        {key:"environment",label:"ENVIRONMENT"},
                        {key:"air-pollen",label:"AIR // POLLEN"}
                    ]
                    delegate: ActionButton {
                        required property var modelData
                        width: HeaderGeometry.buttonWidth(groundModes.width,2)
                        height: HeaderGeometry.tabHeight
                        label: modelData.label
                        labelPixelSize: 10
                        contentPadding: 1
                        selected: earthPane.groundViewMode === modelData.key
                        accentColor: Colors.cyan
                        onClicked: earthPane.groundViewMode = modelData.key
                    }
                }
            }

            Rectangle {
                id: groundRule
                objectName: "earth-e4-ground-divider"
                anchors.top: groundModes.bottom
                anchors.topMargin: HeaderGeometry.tabsToRule
                anchors.left: groundModes.left
                anchors.right: groundModes.right
                height: HeaderGeometry.ruleHeight
                color: Colors.cyan
            }

            StationGround {
                objectName: "earth-e4-one-ground-renderer"
                anchors.top: groundRule.bottom
                anchors.topMargin: HeaderGeometry.ruleToContent
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                subjectRoute: earthPane.groundViewMode === "air-pollen"
                    ? "earth/ground/air-pollen" : "earth/ground/environment"
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
}
