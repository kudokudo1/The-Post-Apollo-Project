import QtQuick
import "../../components"
import "StationSubjectNavigationPolicy.js" as SubjectRoutes
import "StationSubjectNavigationPreviewPolicy.js" as PreviewRoutes
import "StationWeatherSubjectPanelPolicy.js" as WeatherPanelPolicy
import "StationCosmosSubjectPanelPolicy.js" as CosmosPanelPolicy
import "StationEarthSubjectPanelPolicy.js" as EarthPanelPolicy
import "StationMediaSubjectPanelPolicy.js" as MediaPanelPolicy
import "StationMagickSubjectPanelPolicy.js" as MagickPanelPolicy
import "StationToolsSubjectPanelPolicy.js" as ToolsPanelPolicy
import "StationWorkspaceNavigationPolicy.js" as Workspace
import "StationMapProjectionPolicy.js" as MapProjection

// W1 workspace shell, retaining the original M1 route index as MORE.
// HOME is the original running StationHome. No extra providers or writers.
Rectangle {
    id: browser
    color: Colors.black

    property string currentPath: "home/overview"
    property string lastWorkspacePath: "home/overview"
    property bool indexOpen: false
    property var lastSubjectPaths: ({})
    property int navigationCursor: 0

    // W2a: HOME deck choices survive tab/subject switches and closing the
    // SUBJECTS layer for this StationNavigator lifetime. No disk writes.
    property bool homeDeckEnabled: false
    property bool homeDeckHeld: false
    property string homeDeckMode: "mixed"
    property var homeDeckFavorites: []
    property var homeFavoritesStore: null

    function syncHomeDeckFavorites() {
        if (!homeFavoritesStore ||
                (homeFavoritesStore.storageState !== "ready"
                && homeFavoritesStore.storageState !== "empty")) {
            return;
        }
        const paths = homeFavoritesStore.panelRoutes.slice();
        browser.homeDeckFavorites = paths;
    }

    onHomeFavoritesStoreChanged: syncHomeDeckFavorites()

    Connections {
        target: browser.homeFavoritesStore
        function onFavoritesLoaded() { browser.syncHomeDeckFavorites(); }
        function onFavoritesSaved(revision) { browser.syncHomeDeckFavorites(); }
    }

    // Existing Weather Station sources supplied from the single owning root.
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
    property real runtimeNowMs: Date.now()
    readonly property string liveHomeKind:
        Workspace.isHomeRoute(currentPath) ? "home" : ""
    readonly property string liveWeatherKind:
        WeatherPanelPolicy.kindForRoute(currentPath)
    readonly property string liveCosmosKind:
        CosmosPanelPolicy.kindForRoute(currentPath)
    readonly property string liveEarthKind:
        EarthPanelPolicy.kindForRoute(currentPath)
    readonly property string liveMediaKind:
        MediaPanelPolicy.kindForRoute(currentPath)
    readonly property string liveMagickKind:
        MagickPanelPolicy.kindForRoute(currentPath)
    readonly property string liveToolsKind:
        ToolsPanelPolicy.kindForRoute(currentPath)

    readonly property var currentRoute: SubjectRoutes.findRoute(currentPath)
    readonly property var childrenRoutes: SubjectRoutes.childrenOf(currentPath)
    readonly property var pathCrumbs: SubjectRoutes.breadcrumbs(currentPath)
    readonly property var classicSources:
        PreviewRoutes.sourcePagesForPath(currentPath, SubjectRoutes.PANELS)

    // MEDIA owns article extraction. EARTH owns map plotting and inspection.
    // This is transient view context, never a source event or archive write.
    property var newsMentionOverlay: null
    signal legacyPageRequested(string pageId)

    function showNewsMentionsOnEarth(payload) {
        if (!payload || !Array.isArray(payload.locations))
            return false;
        const locations = MapProjection.plottable(payload.locations);
        if (locations.length === 0)
            return false;
        // Copy only data from the existing MEDIA handoff. Never mutate
        // the originating article object or infer disaster locations.
        const incoming = JSON.parse(JSON.stringify(payload));
        incoming.locations = JSON.parse(JSON.stringify(locations));
        if (!chooseRoute("earth/maps/overview"))
            return false;
        newsMentionOverlay = incoming;
        return true;
    }

    function clearNewsMentions() {
        newsMentionOverlay = null;
    }

    // All top-level family choices open a landing page directly.
    // MORE retains access to the full 135-route original index.
    function chooseRoute(path) {
        const home = Workspace.isHomeRoute(path);
        const candidate = home ? {path:path,subject:"home"}
                               : SubjectRoutes.findRoute(path);
        if (!candidate)
            return false;
        // MORE is a real nested explorer. Group selection must descend
        // inside that index, not open an unrenderable parent route.
        if (indexOpen && !home && candidate.group) {
            currentPath = candidate.path;
            navigationCursor = 0;
            if (routeScroll) routeScroll.contentY = 0;
            return true;
        }
        currentPath = candidate.path;
        const updated = Object.assign({}, lastSubjectPaths);
        updated[candidate.subject] = candidate.path;
        lastSubjectPaths = updated;
        navigationCursor = 0;
        indexOpen = false;
        if (routeScroll)
            routeScroll.contentY = 0;
        return true;
    }

    function selectSubject(subjectId) {
        if (indexOpen) {
            const subject = SubjectRoutes.findRoute(subjectId);
            if (!subject || subject.depth !== 0)
                return false;
            currentPath = subjectId;
            navigationCursor = 0;
            routeScroll.contentY = 0;
            return true;
        }
        return chooseRoute(Workspace.landingFor(subjectId));
    }

    function openIndex() {
        lastWorkspacePath = Workspace.isHomeRoute(currentPath)
            || SubjectRoutes.findRoute(currentPath)
            ? currentPath : Workspace.landingFor("home");
        const family = Workspace.familyFor(lastWorkspacePath);
        currentPath = family === "home" ? "weather" : family;
        indexOpen = true;
        navigationCursor = 0;
        if (routeScroll)
            routeScroll.contentY = 0;
    }

    function returnToWorkspace() {
        const route = Workspace.isHomeRoute(lastWorkspacePath)
            || SubjectRoutes.findRoute(lastWorkspacePath)
            ? lastWorkspacePath : Workspace.landingFor("home");
        return chooseRoute(route);
    }

    function cycleSubjects(direction) {
        const step = Number(direction) < 0 ? -1 : 1;
        if (indexOpen) {
            const names = SubjectRoutes.SUBJECTS;
            const current = Workspace.familyFor(currentPath);
            const idx = names.findIndex(function(x){return x.id === current;});
            return selectSubject(names[(Math.max(0,idx)+step+names.length)%names.length].id);
        }
        const tabs = Workspace.FAMILIES;
        const now = Workspace.familyFor(currentPath);
        const idx = tabs.findIndex(function(x){return x.id === now;});
        return chooseRoute(tabs[(Math.max(0,idx)+step+tabs.length)%tabs.length].landing);
    }

    function moveCursor(direction) {
        const count = indexOpen ? childrenRoutes.length
                                : Workspace.tabsFor(currentPath).length;
        if (count === 0) return;
        const step = Number(direction) < 0 ? -1 : 1;
        navigationCursor = (navigationCursor + step + count) % count;
    }

    function activateCursor() {
        if (indexOpen) {
            if (childrenRoutes.length > 0)
                chooseRoute(childrenRoutes[navigationCursor].path);
            return;
        }
        const tabs = Workspace.tabsFor(currentPath);
        if (tabs.length > 0)
            chooseRoute(tabs[Math.min(navigationCursor,tabs.length-1)].path);
    }

    function goUp() {
        if (indexOpen) {
            if (pathCrumbs.length > 1) {
                currentPath = pathCrumbs[pathCrumbs.length-2].path;
                navigationCursor = 0;
                if (routeScroll) routeScroll.contentY = 0;
            }
            return;
        }
        chooseRoute(Workspace.landingFor(Workspace.familyFor(currentPath)));
    }

    // Load only when SUBJECTS is visible. CLASSIC therefore never runs
    // a second hidden HOME watcher or set of source-panel instances.
    Loader {
        id: workspaceLoader
        anchors.fill: parent
        active: browser.visible
        visible: browser.visible && !browser.indexOpen
        sourceComponent: Component {
            StationWorkspaceSurface {
                currentPath: browser.currentPath
                newsMentionOverlay: browser.newsMentionOverlay
                deckEnabled: browser.homeDeckEnabled
                deckHeld: browser.homeDeckHeld
                deckMode: browser.homeDeckMode
                deckFavorites: browser.homeDeckFavorites
                homeFavoritesStore: browser.homeFavoritesStore
                deckIndexOpen: browser.indexOpen
                onDeckEnabledRequested: function(enabled) {
                    browser.homeDeckEnabled = enabled;
                }
                onDeckHeldRequested: function(held) {
                    browser.homeDeckHeld = held;
                }
                onDeckModeRequested: function(mode) {
                    browser.homeDeckMode = mode;
                }
                onDeckFavoritesRequested: function(paths) {
                    // Store is the only durable owner; UI syncs after save.
                    if (browser.homeFavoritesStore)
                        browser.homeFavoritesStore.replacePanelFavorites(paths);
                }
                weatherService: browser.weatherService
                spaceService: browser.spaceService
                nwsAlertSource: browser.nwsAlertSource
                historyService: browser.historyService
                seismicSource: browser.seismicSource
                lightningSource: browser.lightningSource
                riverSource: browser.riverSource
                persistentCacheStore: browser.persistentCacheStore
                liveHistoryStore: browser.liveHistoryStore
                eventArchiveStore: browser.eventArchiveStore
                dossierArchiveStore: browser.dossierArchiveStore
                runtimeNowMs: browser.runtimeNowMs
                onRouteRequested: function(path) {
                    browser.chooseRoute(path);
                }
                onLegacyPageRequested: function(pageId) {
                    browser.legacyPageRequested(pageId);
                }
                onNewsMapRequested: function(payload) {
                    browser.showNewsMentionsOnEarth(payload);
                }
                onNewsMapClearRequested: browser.clearNewsMentions()
            }
        }
    }

    Item {
        id: legacyIndexLayer
        anchors.fill: parent
        visible: browser.visible && browser.indexOpen
        enabled: visible

    Item {
        id: navigationHeading
        ActionButton {
            anchors.top: parent.top
            anchors.right: parent.right
            width: 110
            height: 28
            label: "WORKSPACE"
            labelPixelSize: 10
            accentColor: Colors.cyan
            onClicked: browser.returnToWorkspace()
        }

        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 16
        height: 39

        GohuText {
            id: headingText
            anchors.top: parent.top
            anchors.left: parent.left
            text: browser.liveWeatherKind !== ""
                  ? "WEATHER // SUBJECT VIEW"
                  : browser.liveCosmosKind !== ""
                    ? "COSMOS // SUBJECT VIEW"
                    : browser.liveEarthKind !== ""
                      ? "EARTH // SUBJECT VIEW"
                    : browser.liveMediaKind !== ""
                      ? "MEDIA // SUBJECT VIEW"
                    : browser.liveMagickKind !== ""
                      ? "MAGICK // INTERPRETIVE REFERENCE"
                    : browser.liveToolsKind !== ""
                      ? "TOOLS // OPERATIONAL INSPECTION"
                    : "SUBJECTS // NAVIGATION PREVIEW"
            color: Colors.magenta
            font.pixelSize: 17
        }

    }

    Row {
        id: breadcrumbRow
        anchors.top: navigationHeading.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: 16
        anchors.rightMargin: 16
        spacing: 6
        height: 32

        ActionButton {
            width: 56
            height: 30
            label: "UP"
            labelPixelSize: 11
            available: browser.pathCrumbs.length > 1
            onClicked: browser.goUp()
        }

        Repeater {
            model: browser.pathCrumbs
            delegate: ModeButton {
                required property var modelData
                width: Math.min(145, Math.max(74, modelData.label.length * 9))
                height: 30
                textOnly: true
                labelFontSize: 10
                selected: modelData.path === browser.currentPath
                onTriggered: browser.chooseRoute(modelData.path)
            }
        }
    }

    Rectangle {
        anchors.top: breadcrumbRow.bottom
        anchors.topMargin: 4
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: 16
        anchors.rightMargin: 16
        height: 2
        color: Colors.cyan
    }

    Flickable {
        id: routeScroll
        anchors.top: breadcrumbRow.bottom
        anchors.topMargin: 14
        anchors.bottom: previewNote.top
        anchors.bottomMargin: 6
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: 18
        anchors.rightMargin: 18
        clip: true
        visible: browser.liveWeatherKind === ""
                 && browser.liveCosmosKind === ""
                 && browser.liveEarthKind === ""
                 && browser.liveMediaKind === ""
                 && browser.liveMagickKind === ""
                 && browser.liveToolsKind === ""
        boundsBehavior: Flickable.StopAtBounds
        contentWidth: width
        contentHeight: Math.max(height, contentColumn.implicitHeight + 12)

        Column {
            id: contentColumn
            width: routeScroll.width
            spacing: 9

            GohuText {
                text: browser.currentRoute
                      ? browser.currentRoute.label : "UNKNOWN ROUTE"
                font.pixelSize: 22
                color: Colors.orange
            }

            QuietText {
                width: parent.width
                wrapMode: Text.WordWrap
                font.pixelSize: 11
                text: browser.childrenRoutes.length > 0
                      ? "SUBMODES // SELECT A SUBJECT AREA TO OPEN ITS DEEPER BUCKETS"
                      : "ROUTE RESERVED // ITS CONTENT HAS NOT BEEN MOVED FROM THE CLASSIC PAGES"
            }

            Repeater {
                model: browser.childrenRoutes
                delegate: ModeButton {
                    required property int index
                    required property var modelData
                    width: contentColumn.width
                    height: 39
                    horizontalContent: true
                    bordered: false
                    iconText: modelData.group ? "▸" : "·"
                    labelText: modelData.label
                    labelFontSize: 13
                    iconFontSize: 14
                    keyboardActive: browser.visible
                    keyboardSelected: index === browser.navigationCursor
                    onPointerMoved: browser.navigationCursor = index
                    onTriggered: browser.chooseRoute(modelData.path)
                }
            }

            Rectangle {
                width: parent.width
                height: 1
                color: Colors.cyan
            }

            GohuText {
                text: "CURRENT SOURCE PAGES // CLASSIC"
                font.pixelSize: 13
                color: Colors.cyan
            }

            QuietText {
                width: parent.width
                wrapMode: Text.WordWrap
                text: "OPEN A CLASSIC PAGE TO USE ITS EXISTING CONTROLS. THE NEW ROUTE TREE DOES NOT YET RELOCATE OR FILTER THAT PAGE."
                font.pixelSize: 10
            }

            Repeater {
                model: browser.classicSources
                delegate: ActionButton {
                    required property var modelData
                    width: contentColumn.width
                    height: 32
                    label: "OPEN " + modelData.label
                           + " // " + modelData.panels + " MAPPED"
                    labelPixelSize: 11
                    onClicked: browser.legacyPageRequested(modelData.id)
                }
            }

            QuietText {
                width: parent.width
                visible: browser.classicSources.length === 0
                wrapMode: Text.WordWrap
                text: browser.currentRoute
                      && browser.currentRoute.subject === "magick"
                      ? "MAGICK IS A PLANNED INTERPRETIVE SUBJECT. NO ASTROLOGY OR MAGICK CONTENT IS BEING CLAIMED AS OPERATIONAL."
                      : "NO CLASSIC PAGE IS DIRECTLY MAPPED TO THIS ROUTE YET."
            }
        }
    }

    // Selectors for deeper reserved river subroutes remain available even
    // while the parent river instrument is displayed.
    Flickable {
        id: liveChildren
        visible: (browser.liveWeatherKind !== ""
                  || browser.liveCosmosKind !== ""
                  || browser.liveEarthKind !== ""
                  || browser.liveMediaKind !== ""
                  || browser.liveMagickKind !== ""
                  || browser.liveToolsKind !== "")
                 && browser.childrenRoutes.length > 0
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: breadcrumbRow.bottom
        anchors.topMargin: 6
        anchors.leftMargin: 18
        anchors.rightMargin: 18
        height: visible ? 34 : 0
        contentHeight: height
        contentWidth: Math.max(width, liveChildRow.implicitWidth)
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Row {
            id: liveChildRow
            spacing: 7
            Repeater {
                model: browser.childrenRoutes
                delegate: ModeButton {
                    required property var modelData
                    height: 31
                    width: Math.max(100, modelData.label.length * 9 + 14)
                    labelFontSize: 11
                    textOnly: true
                    onTriggered: browser.chooseRoute(modelData.path)
                }
            }
        }
    }

    StationWeatherSubjectPane {
        id: weatherLivePane
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: liveChildren.visible
                     ? liveChildren.bottom : breadcrumbRow.bottom
        anchors.topMargin: liveChildren.visible ? 6 : 14
        anchors.bottom: previewNote.top
        anchors.bottomMargin: 6
        visible: browser.visible && browser.liveWeatherKind !== ""
        subjectRoute: browser.currentPath
        weatherService: browser.weatherService
        nwsAlertSource: browser.nwsAlertSource
        historyService: browser.historyService
        seismicSource: browser.seismicSource
        lightningSource: browser.lightningSource
        riverSource: browser.riverSource
        persistentCacheStore: browser.persistentCacheStore
        liveHistoryStore: browser.liveHistoryStore
        runtimeNowMs: browser.runtimeNowMs
    }

    StationCosmosSubjectPane {
        id: cosmosLivePane
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: liveChildren.visible
                     ? liveChildren.bottom : breadcrumbRow.bottom
        anchors.topMargin: liveChildren.visible ? 6 : 14
        anchors.bottom: previewNote.top
        anchors.bottomMargin: 6
        visible: browser.visible && browser.liveCosmosKind !== ""
        subjectRoute: browser.currentPath
        weatherService: browser.weatherService
        spaceService: browser.spaceService
        liveHistoryStore: browser.liveHistoryStore
        runtimeNowMs: browser.runtimeNowMs
    }

    StationEarthSubjectPane {
        id: earthLivePane
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: liveChildren.visible
                     ? liveChildren.bottom : breadcrumbRow.bottom
        anchors.topMargin: liveChildren.visible ? 6 : 14
        anchors.bottom: previewNote.top
        anchors.bottomMargin: 6
        visible: browser.visible && browser.liveEarthKind !== ""
        subjectRoute: browser.currentPath
        newsMentionOverlay: browser.newsMentionOverlay
        onNewsMapClearRequested: browser.clearNewsMentions()
        seismicSource: browser.seismicSource
        lightningSource: browser.lightningSource
        riverSource: browser.riverSource
        weatherService: browser.weatherService
        persistentCacheStore: browser.persistentCacheStore
        eventArchiveStore: browser.eventArchiveStore
        dossierArchiveStore: browser.dossierArchiveStore
        runtimeNowMs: browser.runtimeNowMs
    }

    StationMediaSubjectPane {
        id: mediaLivePane
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: liveChildren.visible
                     ? liveChildren.bottom : breadcrumbRow.bottom
        anchors.topMargin: liveChildren.visible ? 6 : 14
        anchors.bottom: previewNote.top
        anchors.bottomMargin: 6
        visible: browser.visible && browser.liveMediaKind !== ""
        subjectRoute: browser.currentPath
        runtimeNowMs: browser.runtimeNowMs
        onNewsMapRequested: function(payload) {
            browser.showNewsMentionsOnEarth(payload);
        }
    }

    StationMagickSubjectPane {
        id: magickReferencePane
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: liveChildren.visible
                     ? liveChildren.bottom : breadcrumbRow.bottom
        anchors.topMargin: liveChildren.visible ? 6 : 14
        anchors.bottom: previewNote.top
        anchors.bottomMargin: 6
        visible: browser.visible && browser.liveMagickKind !== ""
        subjectRoute: browser.currentPath
        weatherService: browser.weatherService
        runtimeNowMs: browser.runtimeNowMs
    }

    StationToolsSubjectPane {
        id: toolsLivePane
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: liveChildren.visible
                     ? liveChildren.bottom : breadcrumbRow.bottom
        anchors.topMargin: liveChildren.visible ? 6 : 14
        anchors.bottom: previewNote.top
        anchors.bottomMargin: 6
        visible: browser.visible && browser.liveToolsKind !== ""
        subjectRoute: browser.currentPath
        weatherService: browser.weatherService
        spaceService: browser.spaceService
        persistentCacheStore: browser.persistentCacheStore
        liveHistoryStore: browser.liveHistoryStore
        eventArchiveStore: browser.eventArchiveStore
        dossierArchiveStore: browser.dossierArchiveStore
        runtimeNowMs: browser.runtimeNowMs
        onLegacyPageRequested: function(pageId) {
            browser.legacyPageRequested(pageId);
        }
    }

    // Post-Apollo shared star indicator; no new scroll behavior is invented.
    NeonScrollBar {
        flickable: routeScroll
        geometryMode: "viewport"
        handleStyle: "star"
        visible: browser.visible && browser.liveWeatherKind === ""
                 && browser.liveCosmosKind === ""
                 && browser.liveEarthKind === ""
                 && browser.liveMediaKind === ""
                 && browser.liveMagickKind === ""
                 && browser.liveToolsKind === ""
                 && routeScroll.contentHeight > routeScroll.height + 1
    }

    QuietText {
        id: previewNote
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.leftMargin: 16
        anchors.rightMargin: 16
        anchors.bottomMargin: 10
        height: 23
        font.pixelSize: 10
        color: Colors.yellow
        text: browser.liveWeatherKind !== ""
              ? "WEATHER // EXISTING SOURCE PANELS // SAME COLLECTORS"
              : browser.liveCosmosKind !== ""
                ? "COSMOS // EXISTING SKY + SPACE PANELS // SAME COLLECTORS"
                : browser.liveEarthKind !== ""
                  ? "EARTH // SHARED MAP + EVENT DOSSIERS // ORIGINAL STORES"
                : browser.liveMediaKind !== ""
                  ? "MEDIA // GDELT + PUBLISHER CATALOG + HI-FI RADIO // ORIGINAL SOURCES"
                : browser.liveMagickKind !== ""
                  ? "MAGICK // ASTRONOMICAL REFERENCE ONLY // NO CALCULATED READINGS"
                : browser.liveToolsKind !== ""
                  ? "TOOLS // LIVE SOURCE READBACK // SHARED STORES // SAFE KITTY HANDOFF"
                : "SPEC-ONLY SUBJECTS // CLASSIC PAGES REMAIN CANONICAL UNTIL PANEL MIGRATION"
    }
    }
}
