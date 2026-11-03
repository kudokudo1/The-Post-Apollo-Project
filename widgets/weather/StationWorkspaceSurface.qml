import QtQuick
import "../../components"
import "StationWorkspaceNavigationPolicy.js" as Workspace

// W1 // full-width subject workspaces, NOT a new source framework.
// HOME is one persistent original StationHome instance across all tabs.
// Existing subject panes remain the only data-panel implementations.
Rectangle {
    id: surface
    color: Colors.black
    property string currentPath: "home/overview"
    property var weatherService: null
    property var spaceService: null
    property var nwsAlertSource: null
    property var historyService: null
    property var seismicSource: null
    property var lightningSource: null
    property var riverSource: null
    property var persistentCacheStore: null
    property var liveHistoryStore: null
    property var eventArchiveStore: null
    property var dossierArchiveStore: null
    property real runtimeNowMs: 0

    readonly property string activeFamily: Workspace.familyFor(currentPath)
    readonly property string homeSection: Workspace.homeSectionFor(currentPath)
    readonly property var activeTabs: Workspace.tabsFor(currentPath)
    signal routeRequested(string path)
    signal legacyPageRequested(string pageId)
    signal newsMapRequested(var payload)
    signal indexRequested()

    Rectangle {
        id: topRail
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 52
        color: Colors.black

        Row {
            anchors.fill: parent
            anchors.margins: 6
            spacing: 5

            Repeater {
                model: Workspace.FAMILIES
                delegate: ModeButton {
                    required property var modelData
                    width: Math.max(71,(surface.width - 215 - 12
                                     - (Workspace.FAMILIES.length - 1) * 5)
                                    / Workspace.FAMILIES.length)
                    height: 38
                    bordered: false
                    textOnly: true
                    labelFontSize: 11
                    labelText: modelData.label
                    selected: surface.activeFamily === modelData.id
                    onTriggered: surface.routeRequested(modelData.landing)
                }
            }

            ActionButton {
                width: 83
                height: 38
                label: "MORE"
                labelPixelSize: 11
                accentColor: Colors.cyan
                onClicked: surface.indexRequested()
            }
            ActionButton {
                width: 91
                height: 38
                label: "CLASSIC"
                labelPixelSize: 11
                accentColor: Colors.orange
                onClicked: surface.legacyPageRequested("home")
            }
        }

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: 2
            color: Colors.cyan
        }
    }

    Item {
        id: workspaceContent
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: topRail.bottom
        anchors.bottom: bottomRail.top

        // Intentionally not a Loader. This one HOME survives navigation
        // to COSMOS/EARTH and retains its 60s watch/ranking timer, trend
        // hysteresis and local previous-observation snapshots.
        StationHome {
            id: originalHome
            anchors.fill: parent
            visible: surface.activeFamily === "home"
                     && surface.homeSection !== "magick"
            subjectRoute: ""
            workspaceSection: surface.homeSection === "overview"
                              ? "" : surface.homeSection
            weatherService: surface.weatherService
            spaceService: surface.spaceService
            nwsAlertSource: surface.nwsAlertSource
            historyService: surface.historyService
            liveHistoryStore: surface.liveHistoryStore
            runtimeNowMs: surface.runtimeNowMs
        }

        // MAGICK belongs to HOME's discovery controls but remains
        // clearly separated from unsupported spiritual calculations.
        StationMagickSubjectPane {
            anchors.fill: parent
            visible: surface.activeFamily === "home"
                     && surface.homeSection === "magick"
            subjectRoute: "magick/overview"
            weatherService: surface.weatherService
            runtimeNowMs: surface.runtimeNowMs
        }

        StationWeatherSubjectPane {
            anchors.fill: parent
            visible: surface.activeFamily === "weather"
            subjectRoute: surface.currentPath
            weatherService: surface.weatherService
            nwsAlertSource: surface.nwsAlertSource
            historyService: surface.historyService
            seismicSource: surface.seismicSource
            lightningSource: surface.lightningSource
            riverSource: surface.riverSource
            persistentCacheStore: surface.persistentCacheStore
            liveHistoryStore: surface.liveHistoryStore
            runtimeNowMs: surface.runtimeNowMs
        }

        StationCosmosSubjectPane {
            anchors.fill: parent
            visible: surface.activeFamily === "cosmos"
            subjectRoute: surface.currentPath
            weatherService: surface.weatherService
            spaceService: surface.spaceService
            liveHistoryStore: surface.liveHistoryStore
            runtimeNowMs: surface.runtimeNowMs
        }

        StationEarthSubjectPane {
            anchors.fill: parent
            visible: surface.activeFamily === "earth"
            subjectRoute: surface.currentPath
            seismicSource: surface.seismicSource
            lightningSource: surface.lightningSource
            riverSource: surface.riverSource
            weatherService: surface.weatherService
            persistentCacheStore: surface.persistentCacheStore
            eventArchiveStore: surface.eventArchiveStore
            dossierArchiveStore: surface.dossierArchiveStore
            runtimeNowMs: surface.runtimeNowMs
        }

        StationMediaSubjectPane {
            anchors.fill: parent
            visible: surface.activeFamily === "media"
            subjectRoute: surface.currentPath
            runtimeNowMs: surface.runtimeNowMs
            onNewsMapRequested: function(payload) {
                surface.newsMapRequested(payload);
            }
        }

        StationMagickSubjectPane {
            anchors.fill: parent
            visible: surface.activeFamily === "magick"
            subjectRoute: surface.currentPath
            weatherService: surface.weatherService
            runtimeNowMs: surface.runtimeNowMs
        }

        StationToolsSubjectPane {
            anchors.fill: parent
            visible: surface.activeFamily === "tools"
            subjectRoute: surface.currentPath
            weatherService: surface.weatherService
            spaceService: surface.spaceService
            persistentCacheStore: surface.persistentCacheStore
            liveHistoryStore: surface.liveHistoryStore
            eventArchiveStore: surface.eventArchiveStore
            dossierArchiveStore: surface.dossierArchiveStore
            runtimeNowMs: surface.runtimeNowMs
            onLegacyPageRequested: function(pageId) {
                surface.legacyPageRequested(pageId);
            }
        }
    }

    Rectangle {
        id: bottomRail
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 51
        color: Colors.black

        Rectangle {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 2
            color: Colors.cyan
        }

        Row {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.leftMargin: 10
            anchors.rightMargin: 10
            spacing: 5

            Repeater {
                model: surface.activeTabs
                delegate: ModeButton {
                    required property var modelData
                    width: Math.max(1,
                       (bottomRail.width - 20
                        - 5 * Math.max(0,surface.activeTabs.length - 1))
                       / Math.max(1,surface.activeTabs.length))
                    height: 36
                    bordered: false
                    textOnly: true
                    labelFontSize: 10
                    labelText: modelData.label
                    selected: Workspace.selectedGroup(surface.currentPath)
                              === modelData.key
                    onTriggered: surface.routeRequested(modelData.path)
                }
            }
        }
    }
}
