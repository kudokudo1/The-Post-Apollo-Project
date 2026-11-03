import QtQuick
import "../../components"
import "StationWorkspaceNavigationPolicy.js" as Workspace
import "StationHomeDeckPolicy.js" as HomeDeck

// W1r // Left family rail and bottom submodes, NOT a new source framework.
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

    // W2a preferences are owned by the persistent SubjectNavigator. The
    // surface is only the control and timer, never a storage or source owner.
    property bool deckEnabled: false
    property bool deckHeld: false
    property string deckMode: "mixed"
    property var deckFavorites: []
    property bool deckIndexOpen: false

    readonly property string activeFamily: Workspace.familyFor(currentPath)
    readonly property string homeSection: Workspace.homeSectionFor(currentPath)
    readonly property var activeTabs: Workspace.tabsFor(currentPath)
    signal routeRequested(string path)
    signal legacyPageRequested(string pageId)
    signal newsMapRequested(var payload)
    signal deckEnabledRequested(bool enabled)
    signal deckHeldRequested(bool held)
    signal deckModeRequested(string mode)
    signal deckFavoritesRequested(var paths)

    function advanceDeck() {
        const next = HomeDeck.nextRoute(
            currentPath, deckFavorites, deckMode, Math.random()
        );
        if (next !== "")
            routeRequested(next);
    }

    onCurrentPathChanged: {
        // Manual tab changes get a full reading interval before another swap.
        if (deckTimer.running)
            deckTimer.restart();
    }

    Item {
        id: workspaceContent
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: bottomRail.top

        // Intentionally not a Loader. This one HOME survives navigation
        // to COSMOS/EARTH and retains its 60s watch/ranking timer, trend
        // hysteresis and local previous-observation snapshots.
        StationHome {
            id: originalHome
            anchors.fill: parent
            anchors.bottomMargin: homeDeckBar.visible ? homeDeckBar.height : 0
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
            anchors.bottomMargin: homeDeckBar.visible ? homeDeckBar.height : 0
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

        // W2a HOME deck controls use the original ActionButton language and
        // reuse the existing HOME section routes. No extra panel instance.
        Rectangle {
            id: homeDeckBar
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            visible: surface.activeFamily === "home"
            height: visible ? 40 : 0
            color: Colors.black

            Rectangle {
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                height: 1
                color: Colors.cyan
            }

            Row {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.leftMargin: 10
                anchors.rightMargin: 10
                spacing: 6

                ActionButton {
                    width: Math.max(1,(parent.width - 24)/5)
                    height: 29
                    label: surface.deckEnabled ? "ROTATE // ON" : "ROTATE // OFF"
                    labelPixelSize: 10
                    selected: surface.deckEnabled
                    onClicked: surface.deckEnabledRequested(!surface.deckEnabled)
                }
                ActionButton {
                    width: Math.max(1,(parent.width - 24)/5)
                    height: 29
                    label: "MODE // " + surface.deckMode.toUpperCase()
                    labelPixelSize: 10
                    onClicked: surface.deckModeRequested(
                        HomeDeck.nextMode(surface.deckMode)
                    )
                }
                ActionButton {
                    width: Math.max(1,(parent.width - 24)/5)
                    height: 29
                    label: surface.deckHeld ? "RESUME" : "HOLD"
                    labelPixelSize: 10
                    selected: surface.deckHeld
                    onClicked: surface.deckHeldRequested(!surface.deckHeld)
                }
                ActionButton {
                    width: Math.max(1,(parent.width - 24)/5)
                    height: 29
                    label: HomeDeck.favorite(surface.deckFavorites,surface.currentPath)
                           ? "★ FAVORITE" : "☆ FAVORITE"
                    labelPixelSize: 10
                    selected: HomeDeck.favorite(surface.deckFavorites,surface.currentPath)
                    available: HomeDeck.isRotatable(surface.currentPath)
                    onClicked: surface.deckFavoritesRequested(
                        HomeDeck.toggleFavorite(
                            surface.deckFavorites, surface.currentPath
                        )
                    )
                }
                ActionButton {
                    width: Math.max(1,(parent.width - 24)/5)
                    height: 29
                    label: "NEXT"
                    labelPixelSize: 10
                    available: HomeDeck.candidates(
                        surface.currentPath,surface.deckFavorites,surface.deckMode
                    ).length > 0
                    onClicked: surface.advanceDeck()
                }
            }
        }
    }

    Timer {
        id: deckTimer
        interval: 30000
        repeat: true
        running: HomeDeck.mayRotate(
            surface.activeFamily, surface.visible, surface.deckEnabled,
            surface.deckHeld, surface.deckIndexOpen
        ) && HomeDeck.candidates(
            surface.currentPath, surface.deckFavorites, surface.deckMode
        ).length > 0
        onTriggered: surface.advanceDeck()
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
