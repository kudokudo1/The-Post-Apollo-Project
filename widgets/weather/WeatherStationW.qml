import QtQuick
import Quickshell
import Quickshell.Wayland
import QtQuick.Effects
import Qt5Compat.GraphicalEffects
import "../../components"
import "../../services/weather" as WeatherServices
import "StationOfficialAlertPolicy.js" as OfficialAlertPolicy
import "StationWeatherSubjectPanelPolicy.js" as SubjectPanelPolicy
import "StationEarthSubjectPanelPolicy.js" as EarthPanelPolicy
import "../../services/weather/WeatherRuntimePolicy.js" as RuntimePolicy

PanelWindow {
    id: weatherStation

    property var weatherService: null
    property var spaceService: null
    property var nwsAlertSource: null
    property var persistentCacheStore: null
    property var liveHistoryStore: null
    property var eventArchiveStore: null
    property var dossierArchiveStore: null

    // W2b single Weather-owned bookmark writer; never touches AppControl.
    // The FileView reads at startup but only explicit pin clicks write.
    WeatherServices.WeatherHomeFavoritesStore {
        id: homeFavoritesStore
    }

    WeatherServices.WeatherHistoryService {
        id: weatherHistoryService
        active: weatherStation.menuOpen
                && ((!weatherStation.subjectNavigationOpen
                     && weatherStation.currentView === "home")
                    || (weatherStation.subjectNavigationOpen
                        && (subjectNavigator.liveHomeKind !== ""
                            || SubjectPanelPolicy.needsSource(
                               subjectNavigator.currentPath, "history"))))
        latitude: weatherStation.weatherService
                  ? weatherStation.weatherService.latitude : ""
        longitude: weatherStation.weatherService
                   ? weatherStation.weatherService.longitude : ""
        anchorDateTime: weatherStation.weatherService
                        ? weatherStation.weatherService.localObservationDateTime
                        : ""
    }

    WeatherServices.SeismicService {
        id: seismicService
        cacheStore: weatherStation.persistentCacheStore
        active: weatherStation.menuOpen
                && ((!weatherStation.subjectNavigationOpen
                     && (weatherStation.currentView === "ground"
                         || weatherStation.currentView === "map"))
                    || (weatherStation.subjectNavigationOpen
                        && EarthPanelPolicy.needsSource(
                               subjectNavigator.currentPath, "seismic")))
    }

    WeatherServices.NowcoastLightningService {
        id: lightningService
        active: weatherStation.menuOpen
                && ((!weatherStation.subjectNavigationOpen
                     && (weatherStation.currentView === "ground"
                         || weatherStation.currentView === "map"))
                    || (weatherStation.subjectNavigationOpen
                        && SubjectPanelPolicy.needsSource(
                               subjectNavigator.currentPath, "lightning")))
        latitude: weatherStation.weatherService
                  ? weatherStation.weatherService.latitude : ""
        longitude: weatherStation.weatherService
                   ? weatherStation.weatherService.longitude : ""
    }

    WeatherServices.NwpsRiverService {
        id: riverService
        cacheStore: weatherStation.persistentCacheStore
        active: weatherStation.menuOpen
                && ((!weatherStation.subjectNavigationOpen
                     && (weatherStation.currentView === "ground"
                         || weatherStation.currentView === "map"))
                    || (weatherStation.subjectNavigationOpen
                        && SubjectPanelPolicy.needsSource(
                               subjectNavigator.currentPath, "river")))
        latitude: weatherStation.weatherService
                  ? weatherStation.weatherService.latitude : ""
        longitude: weatherStation.weatherService
                   ? weatherStation.weatherService.longitude : ""
    }

    // Shared keyboard-ownership contract. Weather stays usable with the
    // existing shell even before shell-level ownership wiring lands because
    // keyboardActive defaults true and OnDemand never traps desktop typing.
    property bool keyboardActive: true
    property bool keyboardLock: false
    signal keyboardOwnershipRequested()

    property bool menuOpen: false
    property bool relationshipFocusModeActive: false
    property bool relationshipFocused: false

    property string currentView: "home"
    // M1 opt-in browser: the existing eight-mode UI remains canonical.
    property bool subjectNavigationOpen: false
    property var newsMapOverlay: null
    property bool contextTerminalRequested: false

    // The SAME geometry drives the layer-shell input mask and the actual
    // transparent visual opening. Sway owns Kitty's global positioning.
    readonly property real terminalHoleX: modeRail.width + terminalView.visibleBayX
    readonly property real terminalHoleY: header.height + terminalView.visibleBayY
    readonly property real terminalHoleWidth: terminalView.visibleBayWidth
    readonly property real terminalHoleHeight: terminalView.visibleBayHeight
    readonly property bool terminalHoleValid:
        terminalHoleX >= 0 && terminalHoleY >= 0
        && terminalHoleWidth > 0 && terminalHoleHeight > 0
        && terminalHoleX + terminalHoleWidth <= stationBackground.width
        && terminalHoleY + terminalHoleHeight <= stationBackground.height
    readonly property bool terminalHoleActive:
        menuOpen && (currentView === "terminal" || contextTerminalRequested)
        && terminalView.sessionMode === currentView
        && terminalView.terminalState === "VISIBLE"
        && terminalHoleValid

    // A keyboard cursor previews rail controls; Enter activates it.
    property int navigationIndex: 0
    readonly property bool standardKeysAvailable:
        menuOpen
        && keyboardActive
        && (!relationshipFocusModeActive || relationshipFocused)

    // HOME, GROUND, SKY and SPACE are peers now. MAP/NEWS/RADIO/TERMINAL
    // remain peers in the same Main Mode family; page-local Sub Modes can be
    // added later without pretending a domain is a filter under HOME.
    readonly property var mainModes: [
        { "id": "home", "name": "HOME", "symbol": "⌂" },
        { "id": "ground", "name": "GROUND", "symbol": "⌁" },
        { "id": "sky", "name": "SKY", "symbol": "☁" },
        { "id": "space", "name": "SPACE", "symbol": "✦" },
        { "id": "map", "name": "MAP", "symbol": "⌖" },
        { "id": "news", "name": "NEWS", "symbol": "▤" },
        { "id": "radio", "name": "RADIO", "symbol": "◉" },
        { "id": "terminal", "name": "TERMINAL", "symbol": ">_" }
    ]

    readonly property string currentViewName: {
        for (let i = 0; i < mainModes.length; i++) {
            if (mainModes[i].id === currentView)
                return mainModes[i].name;
        }
        return "UNKNOWN";
    }

    readonly property string currentContext:
        subjectNavigationOpen
        ? (subjectNavigator.liveHomeKind !== ""
           ? "HOME" : subjectNavigator.liveWeatherKind !== ""
           ? "WEATHER" : subjectNavigator.liveCosmosKind !== ""
             ? "COSMOS" : subjectNavigator.liveEarthKind !== ""
               ? "EARTH" : subjectNavigator.liveMediaKind !== ""
               ? "MEDIA" : subjectNavigator.liveMagickKind !== ""
                 ? "MAGICK" : subjectNavigator.liveToolsKind !== ""
                   ? "TOOLS" : "SUBJECT INDEX") : currentViewName

    readonly property var officialAlertSummary:
        OfficialAlertPolicy.summary(
            nwsAlertSource && Array.isArray(nwsAlertSource.alertList)
            ? nwsAlertSource.alertList : []
        )
    readonly property bool officialAlertUsingPersistentCache:
        nwsAlertSource && nwsAlertSource.usingPersistentCache === true

    function officialAlertColor(token) {
        switch (String(token || "")) {
        case "red": return Colors.red;
        case "orange": return Colors.orange;
        case "yellow": return Colors.yellow;
        case "cyan": return Colors.cyan;
        default: return Colors.white;
        }
    }

    // Header source indicator follows the selected Main Mode's provider.
    // HOME is an aggregate surface now, so its badge represents both the
    // weather/air-quality stack and the independent NOAA space-weather stack.
    property int sourceStatusClock: 0
    readonly property real runtimeNowMs: {
        sourceStatusClock;
        return Date.now();
    }

    readonly property bool usesHomeSources:
        currentView === "home"

    readonly property bool usesWeatherSource:
        currentView === "ground"
        || currentView === "sky"

    readonly property bool usesSpaceSource:
        currentView === "space"

    readonly property bool usesNewsSource: currentView === "news"
    // The NEWS provider belongs to the loaded StationDiscovery instance.
    // Read its exposed status rather than invent a parallel NEWS poller.
    readonly property var newsSourceItem:
        usesNewsSource && weatherContentLoader.item
        ? weatherContentLoader.item : null

    readonly property var currentPageRuntimeRows:
        weatherContentLoader.item
        && Array.isArray(weatherContentLoader.item.runtimeRows)
        ? weatherContentLoader.item.runtimeRows : []
    readonly property var currentPageRuntimeSummary:
        RuntimePolicy.summarizeRows(currentPageRuntimeRows)
    readonly property bool usesMapRuntime:
        currentView === "map"

    // NEWS player viewport in the 1000x700 Station chassis's local logical
    // coordinate system. The Station window's *global* coordinates remain
    // compositor-owned. This read-only QML geometry is not browser authority.
    readonly property rect newsViewerViewportRect: {
        const hub = newsSourceItem;
        if (!menuOpen || contextTerminalRequested || !hub || !hub.viewerOpen)
            return Qt.rect(0, 0, 0, 0);
        const bay = hub.playerViewportRect;
        if (!bay || bay.width <= 0 || bay.height <= 0)
            return Qt.rect(0, 0, 0, 0);
        const origin = hub.mapToItem(stationBackground, bay.x, bay.y);
        return Qt.rect(origin.x, origin.y, bay.width, bay.height);
    }
    readonly property bool newsViewerGeometryValid:
        menuOpen && currentView === "news" && !contextTerminalRequested
        && newsViewerViewportRect.x >= 0 && newsViewerViewportRect.y >= 0
        && newsViewerViewportRect.width > 0 && newsViewerViewportRect.height > 0
        && newsViewerViewportRect.x + newsViewerViewportRect.width <= stationBackground.width
        && newsViewerViewportRect.y + newsViewerViewportRect.height <= stationBackground.height

    readonly property var weatherRuntimeSpec:
        RuntimePolicy.sourceSpec("weather-current")
    readonly property var spaceRuntimeSpec:
        RuntimePolicy.sourceSpec("space-core")

    readonly property var weatherRuntimeState: {
        sourceStatusClock;
        return RuntimePolicy.runtimeState(
            weatherRuntimeSpec,
            {
                "active": true,
                "ready": !!weatherService && weatherService.ready,
                "loading": !!weatherService && weatherService.loading,
                "errorText": weatherService
                             ? weatherService.errorText : "",
                "receivedAt": weatherService
                              ? weatherService.lastUpdated : null,
                "usingCache": weatherService
                              ? weatherService.usingPersistentCurrentCache
                              : false
            },
            Date.now()
        );
    }

    readonly property var spaceRuntimeState: {
        sourceStatusClock;
        return RuntimePolicy.runtimeState(
            spaceRuntimeSpec,
            {
                "active": true,
                "ready": !!spaceService && spaceService.ready,
                "loading": !!spaceService && spaceService.loading,
                "errorText": spaceService
                             ? spaceService.errorText : "",
                "receivedAt": spaceService
                              ? spaceService.lastUpdated : null,
                "usingCache": spaceService
                              ? spaceService.usingPersistentCache : false
            },
            Date.now()
        );
    }

    readonly property int weatherAgeMinutes:
        weatherRuntimeState.receivedAgeMs < 0
        ? -1
        : Math.floor(weatherRuntimeState.receivedAgeMs / 60000)

    readonly property int weatherObservationAgeMinutes:
        weatherRuntimeState.observationAgeMs < 0
        ? -1
        : Math.floor(weatherRuntimeState.observationAgeMs / 60000)

    readonly property int spaceAgeMinutes:
        spaceRuntimeState.receivedAgeMs < 0
        ? -1
        : Math.floor(spaceRuntimeState.receivedAgeMs / 60000)

    function compactAge(ageMinutes) {
        return RuntimePolicy.compactAgeMinutes(ageMinutes);
    }

    readonly property string footerSourceStatus:
        "WEATHER " + compactAge(weatherAgeMinutes)
        + " // SPACE " + compactAge(spaceAgeMinutes)

    readonly property bool weatherStale:
        weatherService
        && weatherService.ready
        && (
            String(weatherService.errorText || "").length > 0
            || weatherRuntimeState.freshness === "AGING"
            || weatherRuntimeState.freshness === "STALE"
            || weatherRuntimeState.freshness === "EXPIRED"
        )

    function runtimeExpired(state) {
        if (!state)
            return true;
        const value = String(state.availability || "");
        return value === "OFFLINE"
            || value === "EXPIRED"
            || value === "CACHE_EXPIRED";
    }

    function runtimeCached(state) {
        return state
            && String(state.availability || "").indexOf("CACHE_") === 0;
    }

    function runtimeHeaderText(state, liveLabel) {
        if (!state)
            return "OFFLINE";
        switch (String(state.availability || "")) {
        case "LIVE": return liveLabel;
        case "LIVE_AGING": return "AGING";
        case "LIVE_STALE": return "STALE";
        case "EXPIRED": return "EXPIRED";
        case "CACHE_FRESH": return "CACHE FRESH";
        case "CACHE_AGING": return "CACHE AGING";
        case "CACHE_STALE": return "CACHE STALE";
        case "CACHE_EXPIRED": return "CACHE EXPIRED";
        case "READING": return "READING";
        case "OFFLINE": return "OFFLINE";
        case "WAITING": return "CONNECTING";
        case "INACTIVE": return "INACTIVE";
        default: return liveLabel;
        }
    }

    function runtimeHeaderColor(state, liveColor) {
        switch (RuntimePolicy.statusToken(state)) {
        case "red": return Colors.red;
        case "yellow": return Colors.yellow;
        case "orange": return Colors.orange;
        case "blue": return Colors.blue;
        case "green": return Colors.green;
        case "cyan": return Colors.cyan;
        case "magenta": return Colors.magenta;
        default: return liveColor;
        }
    }

    readonly property bool homeWeatherUsable:
        weatherService && weatherService.ready
        && !runtimeExpired(weatherRuntimeState)
    readonly property bool homeSpaceUsable:
        spaceService && spaceService.ready
        && !runtimeExpired(spaceRuntimeState)
    readonly property bool homeSourceLoading:
        (weatherService && weatherService.loading)
        || (spaceService && spaceService.loading)
    readonly property bool homeSourceError:
        (weatherService
         && String(weatherService.errorText || "").length > 0)
        || (spaceService
            && String(spaceService.errorText || "").length > 0)

    readonly property string sourceStatusText: {
        if (officialAlertSummary.available)
            return officialAlertSummary.headerText
                   + (officialAlertUsingPersistentCache ? " // CACHE" : "");

        if (subjectNavigationOpen)
            return subjectNavigator.liveHomeKind !== ""
                   ? "HOME DYNAMIC" : subjectNavigator.liveWeatherKind !== ""
                   ? "WEATHER PANEL" : subjectNavigator.liveCosmosKind !== ""
                     ? "COSMOS PANEL" : subjectNavigator.liveEarthKind !== ""
                       ? "EARTH PANEL" : subjectNavigator.liveMediaKind !== ""
                         ? "MEDIA PANEL" : subjectNavigator.liveMagickKind !== ""
                           ? "MAGICK REFERENCE" : subjectNavigator.liveToolsKind !== ""
                             ? "TOOLS READ-ONLY" : "NAV PREVIEW";

        if (usesHomeSources) {
            if (homeWeatherUsable && homeSpaceUsable) {
                if (runtimeCached(weatherRuntimeState)
                        && runtimeCached(spaceRuntimeState))
                    return "HOME CACHE";
                if (runtimeCached(weatherRuntimeState)
                        || runtimeCached(spaceRuntimeState))
                    return "HOME MIXED";
                return "HOME LIVE";
            }
            if (homeWeatherUsable || homeSpaceUsable)
                return runtimeCached(weatherRuntimeState)
                       || runtimeCached(spaceRuntimeState)
                       ? "PARTIAL CACHE" : "PARTIAL";
            if (homeSourceLoading)
                return "READING";
            if (homeSourceError)
                return "OFFLINE";
            return "CONNECTING";
        }

        if (usesWeatherSource)
            return runtimeHeaderText(weatherRuntimeState, "WEATHER LIVE");

        if (usesSpaceSource)
            return runtimeHeaderText(spaceRuntimeState, "SPACE LIVE");

        if (usesMapRuntime) {
            if (currentPageRuntimeSummary.expired > 0
                    && currentPageRuntimeSummary.expired
                       >= currentPageRuntimeSummary.ready)
                return "MAP EXPIRED";
            if ((currentPageRuntimeSummary.problem > 0
                    || currentPageRuntimeSummary.offline > 0)
                    && currentPageRuntimeSummary.ready === 0)
                return "OFFLINE";
            if (currentPageRuntimeSummary.loading > 0
                    && currentPageRuntimeSummary.ready === 0)
                return "READING";
            if (currentPageRuntimeSummary.cached > 0)
                return "MAP CACHE";
            if (currentPageRuntimeSummary.stale > 0)
                return "STALE";
            if (currentPageRuntimeSummary.ready > 0)
                return "MAP LIVE";
            return "CONNECTING";
        }

        if (usesNewsSource)
            return newsSourceItem ? newsSourceItem.feedBadge : "CONNECTING // NEWS";

        return "NO FEED";
    }

    readonly property string sourceStatusDisplay: {
        if (officialAlertSummary.available)
            return officialAlertSummary.headerText
                   + (officialAlertUsingPersistentCache ? " // CACHE" : "");

        if (subjectNavigationOpen) {
            if (subjectNavigator.liveHomeKind !== "")
                return "HOME // AUTO RELEVANCE + HISTORY";
            if (subjectNavigator.liveWeatherKind !== "")
                return "WEATHER // PANEL";
            if (subjectNavigator.liveCosmosKind !== "")
                return "COSMOS // PANEL";
            if (subjectNavigator.liveEarthKind !== "")
                return "EARTH // PANEL";
            if (subjectNavigator.liveMediaKind !== "")
                return "MEDIA // PANEL";
            if (subjectNavigator.liveMagickKind !== "")
                return "MAGICK // ASTRONOMY REFERENCE";
            if (subjectNavigator.liveToolsKind !== "")
                return "TOOLS // SOURCE AND STORAGE STATUS";
            return "INDEX // PREVIEW";
        }

        if (usesHomeSources) {
            if (homeWeatherUsable && homeSpaceUsable)
                return sourceStatusText + " // 2 FEEDS";
            if (homeWeatherUsable)
                return sourceStatusText + " // WEATHER";
            if (homeSpaceUsable)
                return sourceStatusText + " // SPACE";
            if (homeSourceLoading)
                return "READING // SOURCES";
            if (homeSourceError)
                return "OFFLINE // SOURCES";
            return "CONNECTING // SOURCES";
        }

        if (usesWeatherSource) {
            if (!weatherService)
                return "OFFLINE // NO SERVICE";
            if (weatherService.loading)
                return "READING // UPDATING";
            if (!weatherService.ready)
                return String(weatherService.errorText || "").length > 0
                       ? "OFFLINE // NO LINK" : "CONNECTING // WAITING";

            if (weatherAgeMinutes < 0)
                return sourceStatusText;

            const ageText = weatherAgeMinutes === 0
                            ? "<1m"
                            : weatherAgeMinutes + "m";
            return sourceStatusText + " // " + ageText;
        }

        if (usesMapRuntime) {
            if (currentPageRuntimeSummary.ready > 0)
                return sourceStatusText + " // "
                       + currentPageRuntimeSummary.ready + " READY";
            if (currentPageRuntimeSummary.loading > 0)
                return sourceStatusText + " // "
                       + currentPageRuntimeSummary.loading + " READING";
            return sourceStatusText + " // SOURCES";
        }

        if (usesSpaceSource || usesNewsSource)
            return sourceStatusText;

        return "NO FEED // NOT WIRED";
    }

    readonly property color sourceStatusColor: {
        if (officialAlertSummary.available)
            return officialAlertColor(officialAlertSummary.colorToken);

        if (subjectNavigationOpen)
            return Colors.cyan;

        if (usesHomeSources) {
            if (homeWeatherUsable && homeSpaceUsable) {
                if (runtimeCached(weatherRuntimeState)
                        || runtimeCached(spaceRuntimeState))
                    return Colors.blue;
                return Colors.magenta;
            }
            if (homeWeatherUsable || homeSpaceUsable)
                return Colors.yellow;
            if (homeSourceLoading)
                return Colors.orange;
            if (homeSourceError)
                return Colors.red;
            return Colors.orange;
        }

        if (usesWeatherSource)
            return runtimeHeaderColor(weatherRuntimeState, Colors.magenta);

        if (usesSpaceSource)
            return runtimeHeaderColor(spaceRuntimeState, Colors.magenta);

        if (usesMapRuntime) {
            if (currentPageRuntimeSummary.expired > 0
                    && currentPageRuntimeSummary.expired
                       >= currentPageRuntimeSummary.ready)
                return Colors.red;
            if ((currentPageRuntimeSummary.problem > 0
                    || currentPageRuntimeSummary.offline > 0)
                    && currentPageRuntimeSummary.ready === 0)
                return Colors.red;
            if (currentPageRuntimeSummary.cached > 0)
                return Colors.blue;
            if (currentPageRuntimeSummary.stale > 0
                    || currentPageRuntimeSummary.problem > 0)
                return Colors.yellow;
            if (currentPageRuntimeSummary.loading > 0
                    && currentPageRuntimeSummary.ready === 0)
                return Colors.orange;
            if (currentPageRuntimeSummary.ready > 0)
                return Colors.magenta;
            return Colors.orange;
        }

        if (usesNewsSource)
            return newsSourceItem ? newsSourceItem.feedBadgeColor : Colors.orange;

        return Colors.orange;
    }

    Timer {
        interval: 30000
        repeat: true
        running: weatherStation.menuOpen
        onTriggered: weatherStation.sourceStatusClock++
    }

    implicitWidth: menuOpen ? 1000 : 0

    implicitHeight: menuOpen ? 700 : 0

    visible: true
    color: "transparent"

    exclusiveZone: 0
    // Static before layer-shell connection. Stage Director recognizes this
    // exact host candidate; a namespace alone never authenticates ownership.
    WlrLayershell.namespace: "post-apollo-weather-station"
    WlrLayershell.layer: WlrLayer.Overlay

    // Ordinary Weather use is OnDemand so an open widget never monopolizes
    // keyboard input from normal apps. Preserve Weather's existing Koinoikos
    // selected-menu behavior until the concurrent shell ownership seam is
    // available for the same bounded keyboard-lock wiring as Git/Finance.
    WlrLayershell.keyboardFocus:
        !weatherStation.menuOpen || !weatherStation.keyboardActive
        ? WlrKeyboardFocus.None
        : weatherStation.relationshipFocusModeActive
        ? (weatherStation.relationshipFocused
           ? WlrKeyboardFocus.Exclusive : WlrKeyboardFocus.None)
        : weatherStation.keyboardLock
        ? WlrKeyboardFocus.Exclusive
        : WlrKeyboardFocus.OnDemand
    focusable:
        weatherStation.menuOpen
        && weatherStation.keyboardActive
        && (!weatherStation.relationshipFocusModeActive
            || weatherStation.relationshipFocused)
    surfaceFormat.opaque: false

    anchors {
        top: true
        bottom: false
        right: true
        left: false
    }

    // Match the 9px visible top line of FinanceW, TasksW and TimeW.
    // No weather station resizing or internal position changes.
    margins {
        top: 9
        bottom: 0
        right: 20
        left: 0
    }

    // Mouse can still pass through the Star Map
    // display area while Kitty is visible.
    mask: Region {
        width: weatherStation.menuOpen ? 1000 : 0

        height: weatherStation.menuOpen ? 700 : 0

        Region {
            x: weatherStation.terminalHoleX

            y: weatherStation.terminalHoleY

            width: weatherStation.terminalHoleActive
                   ? weatherStation.terminalHoleWidth : 0

            height: weatherStation.terminalHoleActive
                    ? weatherStation.terminalHoleHeight : 0

            intersection: Intersection.Subtract
        }
    }

    // Stable keyboard home. Qt can consume Tab as focus-chain navigation
    // before a WindowShortcut, so the anchor handles the shared navigation
    // keys locally while the guarded Shortcut entries remain as fallback.
    Item {
        id: weatherKeyboardAnchor

        anchors.fill: parent
        enabled: weatherStation.standardKeysAvailable
        focus: weatherStation.standardKeysAvailable
        z: -1000

        Keys.priority: Keys.BeforeItem

        Keys.onShortcutOverride: function(event) {
            if (!weatherStation.standardKeysAvailable)
                return;

            if (event.key === Qt.Key_Tab
                    || event.key === Qt.Key_Backtab
                    || event.key === Qt.Key_Escape) {
                event.accepted = true;
            }
        }

        Keys.onPressed: function(event) {
            if (!weatherStation.standardKeysAvailable)
                return;

            if (event.key === Qt.Key_Escape) {
                if (weatherStation.subjectNavigationOpen)
                    weatherStation.subjectNavigationOpen = false;
                else
                    weatherStation.close();
            } else if (event.key === Qt.Key_Tab
                       || event.key === Qt.Key_Backtab) {
                const reverse =
                    event.key === Qt.Key_Backtab
                    || (event.modifiers & Qt.ShiftModifier) !== 0;
                weatherStation.cycleMainMode(reverse ? -1 : 1);
            } else if (event.key === Qt.Key_Up) {
                weatherStation.moveNavigationCursor(-1);
            } else if (event.key === Qt.Key_Down) {
                weatherStation.moveNavigationCursor(1);
            } else if (event.key === Qt.Key_Return
                       || event.key === Qt.Key_Enter) {
                weatherStation.activateNavigationCursor();
            } else {
                return;
            }

            event.accepted = true;
        }
    }

    function restoreWeatherKeyboardFocus() {
        if (weatherStation.standardKeysAvailable)
            weatherKeyboardAnchor.forceActiveFocus();
    }

    onKeyboardActiveChanged: {
        if (weatherStation.menuOpen && weatherStation.keyboardActive)
            Qt.callLater(weatherStation.restoreWeatherKeyboardFocus);
    }

    onRelationshipFocusedChanged: {
        if (weatherStation.menuOpen
                && (!weatherStation.relationshipFocusModeActive
                    || weatherStation.relationshipFocused)) {
            Qt.callLater(weatherStation.restoreWeatherKeyboardFocus);
        }
    }


    // Every visible rail page is a Main Mode. Tab/Shift+Tab cycles them
    // in rail order; Up/Down previews the same list and Enter activates it.
    function cycleMainMode(direction) {
        if (subjectNavigationOpen) {
            subjectNavigator.cycleSubjects(direction);
            return;
        }
        const current = Math.max(0, mainModes.findIndex(function(mode) {
            return mode.id === currentView;
        }));
        const step = Number(direction) < 0 ? -1 : 1;
        const next = (current + step + mainModes.length) % mainModes.length;
        currentView = mainModes[next].id;
        navigationIndex = next;
    }

    function moveNavigationCursor(direction) {
        if (subjectNavigationOpen) {
            subjectNavigator.moveCursor(direction);
            return;
        }
        const step = Number(direction) < 0 ? -1 : 1;
        navigationIndex =
            (navigationIndex + step + mainModes.length) % mainModes.length;
    }

    function activateNavigationCursor() {
        if (subjectNavigationOpen) {
            subjectNavigator.activateCursor();
            return;
        }
        if (navigationIndex < 0 || navigationIndex >= mainModes.length)
            return;
        currentView = mainModes[navigationIndex].id;
    }

    Shortcut {
        sequence: "Tab"
        context: Qt.WindowShortcut
        enabled: weatherStation.standardKeysAvailable
        onActivated: weatherStation.cycleMainMode(1)
    }
    Shortcut {
        sequence: "Shift+Tab"
        context: Qt.WindowShortcut
        enabled: weatherStation.standardKeysAvailable
        onActivated: weatherStation.cycleMainMode(-1)
    }
    Shortcut {
        sequence: "Up"
        context: Qt.WindowShortcut
        enabled: weatherStation.standardKeysAvailable
        onActivated: weatherStation.moveNavigationCursor(-1)
    }
    Shortcut {
        sequence: "Down"
        context: Qt.WindowShortcut
        enabled: weatherStation.standardKeysAvailable
        onActivated: weatherStation.moveNavigationCursor(1)
    }
    Shortcut {
        sequence: "Return"
        context: Qt.WindowShortcut
        enabled: weatherStation.standardKeysAvailable
        onActivated: weatherStation.activateNavigationCursor()
    }
    Shortcut {
        sequence: "Enter"
        context: Qt.WindowShortcut
        enabled: weatherStation.standardKeysAvailable
        onActivated: weatherStation.activateNavigationCursor()
    }

    function openSubjectNavigation() {
        // The M1 browser is intentionally passive; never obscure a live
        // terminal actor or reinterpret its exact legacy session identity.
        if (!menuOpen || contextTerminalRequested
                || terminalView.terminalState !== "IDLE")
            return;
        if (currentView === "terminal") {
            currentView = "home";
            navigationIndex = 0;
        }
        subjectNavigationOpen = true;
    }

    function openLegacyFromSubject(pageId) {
        const index = mainModes.findIndex(function(mode) {
            return mode.id === pageId;
        });
        if (index < 0)
            return;
        subjectNavigationOpen = false;
        navigationIndex = index;
        currentView = pageId;
    }

    function open() {
        weatherStation.keyboardOwnershipRequested();
        menuOpen = true;
        Qt.callLater(weatherStation.restoreWeatherKeyboardFocus);
    }

    function launchContextTerminal() {
        if (!menuOpen || subjectNavigationOpen
                || terminalView.terminalState !== "IDLE")
            return;
        contextTerminalRequested = true;
        // Wait for the host to become visible before requesting Kitty.
        Qt.callLater(function() {
            if (menuOpen && contextTerminalRequested
                    && terminalView.terminalMode === currentView) {
                if (!terminalView.openTerminal())
                    contextTerminalRequested = false;
            }
        });
    }

    function closeContextTerminal() {
        terminalView.closeTerminal();
        contextTerminalRequested = false;
    }

    onCurrentViewChanged: {
        subjectNavigationOpen = false;
        // One compositor-backed session at a time. Each new mode has a
        // different app ID; never direct Sway to close the wrong actor.
        closeContextTerminal();
    }

    function close() {
        closeContextTerminal();
        subjectNavigationOpen = false;
        menuOpen = false;
    }

    function toggle() {
        if (menuOpen)
            close();
        else
            open();
    }

    WindowPanelFrame {
        id: stationBackground

        width: 1000
        height: 700

        anchors.right: parent.right
        anchors.bottom: parent.bottom

        visible: weatherStation.menuOpen

        // Full chassis fill would obscure Kitty through the overlay layer.
        // When the terminal is positioned, four strips paint everywhere
        // EXCEPT the terminal viewport. No cutout while launch is pending.
        fillVisible: !weatherStation.terminalHoleActive
        fillColor: Colors.black
        fillOpacity: 0.96
        borderVisible: true
        borderColor: Colors.cyan
        borderWidth: 1
        radius: 0

        glowVisible: weatherStation.menuOpen
        glowColor: Colors.cyan
        closeGlowSpread: 4
        closeGlowOpacity: relationshipFocusModeActive
                          ? (relationshipFocused ? 0.58 : 0.09) : 0.30
        wideGlowSpread: 14
        wideGlowOpacity: relationshipFocusModeActive
                         ? (relationshipFocused ? 0.20 : 0.02) : 0.10

        StationChassisCutout {
            id: terminalChassisCutout
            anchors.fill: parent
            visible: weatherStation.terminalHoleActive
            holeX: weatherStation.terminalHoleX
            holeY: weatherStation.terminalHoleY
            holeWidth: weatherStation.terminalHoleWidth
            holeHeight: weatherStation.terminalHoleHeight
            panelColor: Colors.black
            panelOpacity: 0.96
        }

        // ─────────────────────────────────────────
        // HEADER
        // ─────────────────────────────────────────

        Rectangle {
            id: header

            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right

            height: 62

            color: Colors.black

            Text {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter

                anchors.leftMargin: 22

                text: "WEATHER STATION // " + weatherStation.currentContext

                font.family: "GohuFont 11 Nerd Font Mono"

                font.pixelSize: 20

                color: Colors.magenta
            }

            Row {
                id: headerActions

                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.rightMargin: 14

                spacing: 8

                // One context-sensitive launch control replaces the
                // Observatory placeholder. STAR MAP is the existing real
                // TUI; other pages initially get an honest plain console.
                ActionButton {
                    id: contextTerminalLaunch
                    width: 106
                    height: 32
                    label: weatherStation.subjectNavigationOpen
                           ? "INDEX" : weatherStation.currentView === "terminal"
                           ? "STAR MAP" : weatherStation.currentViewName
                    labelPixelSize: 11
                    contentPadding: 4
                    available: weatherStation.menuOpen
                               && terminalView.terminalState === "IDLE"
                               && !weatherStation.contextTerminalRequested
                    accentColor: Colors.cyan
                    onLeftClicked: {
                        if (weatherStation.subjectNavigationOpen) {
                            if (subjectNavigator.indexOpen)
                                subjectNavigator.returnToWorkspace();
                            else
                                subjectNavigator.openIndex();
                        } else {
                            weatherStation.launchContextTerminal();
                        }
                    }
                }

                ActionButton {
                    id: contextTerminalClose
                    width: 57
                    height: 32
                    label: "CLOSE"
                    labelPixelSize: 11
                    contentPadding: 4
                    accentColor: Colors.red
                    destructive: true
                    idleForegroundColor: Colors.red
                    idleBorderColor: Colors.red
                    hoverForegroundColor: Colors.red
                    hoverBorderColor: Colors.red
                    idleContentGlowColor: Colors.red
                    hoverContentGlowColor: Colors.red
                    idleSoftGlowColor: Colors.red
                    hoverSoftGlowColor: Colors.red
                    available: weatherStation.menuOpen
                               && (weatherStation.contextTerminalRequested
                                   || terminalView.terminalState !== "IDLE")
                    onLeftClicked: weatherStation.closeContextTerminal()
                }

                // Separate the terminal session controls from the live
                // source indicator without stealing the whole header row.
                Rectangle {
                    id: terminalHeaderDivider
                    width: 2
                    height: 25
                    anchors.verticalCenter: parent.verticalCenter
                    color: Colors.cyan
                    opacity: 0.85
                }

                // Live source badge, matching the Git/Finance header grammar.
                // It is an indicator, not an input control.
                Rectangle {
                    id: sourceStatusIndicator

                    width: 150
                    height: 32
                    anchors.verticalCenter: parent.verticalCenter

                    color: Colors.dark
                    border.width: 1
                    border.color: weatherStation.sourceStatusColor

                    RectangularShadow {
                        anchors.fill: parent
                        z: -1
                        spread: 4
                        opacity: weatherStation.menuOpen ? 0.54 : 0
                        color: weatherStation.sourceStatusColor
                    }

                    GohuText {
                        anchors.centerIn: parent
                        text: weatherStation.sourceStatusDisplay
                        font.pixelSize: 11
                        color: weatherStation.sourceStatusColor
                        textFormat: Text.PlainText
                    }
                }

                // Standard Post-Apollo Close / Dismiss glyph: × (U+00D7).
                ActionButton {
                    id: closeButton

                    width: 34
                    height: 32

                    label: "×"
                    labelPixelSize: 22
                    contentPadding: 4
                    trackLabelGlowLocally: true

                    accentColor: Colors.red
                    destructive: true

                    idleForegroundColor: Colors.red
                    hoverForegroundColor: Colors.red
                    selectedForegroundColor: Colors.red
                    keyboardSelectedForegroundColor: Colors.red

                    hoverBorderColor: Colors.red
                    selectedBorderColor: Colors.red
                    keyboardSelectedBorderColor: Colors.red

                    idleContentGlowColor: Colors.red
                    hoverContentGlowColor: Colors.red
                    selectedContentGlowColor: Colors.red
                    keyboardSelectedContentGlowColor: Colors.red

                    softGlowEnabled: true
                    idleSoftGlowColor: Colors.red
                    hoverSoftGlowColor: Colors.red
                    pressedSoftGlowColor: Colors.red
                    softGlowIdleOpacity: 0.48
                    softGlowHoverOpacity: 0.70

                    wideGlowEnabled: true
                    idleWideGlowColor: Colors.red
                    hoverWideGlowColor: Colors.red
                    pressedWideGlowColor: Colors.red
                    wideGlowIdleOpacity: 0.22
                    wideGlowHoverOpacity: 0.32

                    onLeftClicked: weatherStation.close()
                }
            }

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom

                anchors.leftMargin: 15
                anchors.rightMargin: 15

                height: 2

                color: Colors.cyan
            }
        }

        // ─────────────────────────────────────────
        // NAVIGATION
        // ─────────────────────────────────────────

        Rectangle {
            id: modeRail

            anchors.top: header.bottom
            anchors.bottom: footer.top
            anchors.left: parent.left

            // The original 160px mode rail is shared by CLASSIC,
            // the seven-family workspace, and the deep INDEX view.
            // Terminal placement stays on this original geometry.
            width: 160

            color: Colors.black

            Rectangle {
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                anchors.right: parent.right

                width: 2

                color: Colors.cyan
            }

            Column {
                id: railColumn
                visible: !weatherStation.subjectNavigationOpen

                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.topMargin: 14

                spacing: 6

                Repeater {
                    model: weatherStation.mainModes

                    delegate: ModeButton {
                        id: mainModeButton

                        required property int index
                        required property var modelData

                        width: railColumn.width
                        height: 48

                        keyboardActive: weatherStation.standardKeysAvailable
                        keyboardSelected:
                            weatherStation.navigationIndex === index
                        onPointerMoved:
                            weatherStation.navigationIndex = index

                        selected:
                            weatherStation.currentView === modelData.id
                        bordered: false
                        horizontalContent: true
                        contentSpacing: 10
                        iconFontSize: 18
                        labelFontSize: 18
                        iconText: modelData.symbol
                        labelText: modelData.name

                        onTriggered: {
                            weatherStation.navigationIndex = index;
                            weatherStation.currentView = modelData.id;
                        }
                    }
                }
            }

            // Main family buttons share the CLASSIC left rail's visual
            // grammar. The existing deep subject rail remains for INDEX.
            StationWorkspaceFamilyRail {
                id: workspaceFamilyRailColumn
                visible: weatherStation.subjectNavigationOpen
                         && !subjectNavigator.indexOpen
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.topMargin: 14
                navigator: subjectNavigator
            }

            // The existing detailed subject INDEX still uses its rail.
            StationSubjectRail {
                id: subjectRailColumn
                visible: weatherStation.subjectNavigationOpen
                         && subjectNavigator.indexOpen
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.topMargin: 14
                navigator: subjectNavigator
            }

            // Explicit CLASSIC return. This is an index preview, not a
            // premature activation of migrated source panels.
            ActionButton {
                id: subjectBrowserToggle
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.leftMargin: 9
                anchors.rightMargin: 9
                anchors.bottomMargin: 12
                height: 36
                visible: true
                label: weatherStation.subjectNavigationOpen
                       ? "CLASSIC" : "SUBJECTS"
                labelPixelSize: 12
                selected: weatherStation.subjectNavigationOpen
                available: weatherStation.menuOpen
                           && terminalView.terminalState === "IDLE"
                           && !weatherStation.contextTerminalRequested
                onClicked: {
                    if (weatherStation.subjectNavigationOpen)
                        weatherStation.subjectNavigationOpen = false;
                    else
                        weatherStation.openSubjectNavigation();
                }
            }
        }

        // ─────────────────────────────────────────
        // MAIN VIEW
        // ─────────────────────────────────────────

        Rectangle {
            id: mainView

            anchors.top: header.bottom
            anchors.bottom: footer.top
            anchors.left: modeRail.right
            anchors.right: parent.right

            color: weatherStation.currentView === "terminal"
                   || weatherStation.contextTerminalRequested
                   ? "transparent" : Colors.black

            clip: true

            Loader {
                id: weatherContentLoader
                anchors.fill: parent
                // SUBJECTS owns its own real panels, not a hidden duplicate
                // CLASSIC NEWS/RADIO view with a second memory observer.
                active: !weatherStation.subjectNavigationOpen
                visible: weatherStation.currentView !== "terminal"
                         && !weatherStation.contextTerminalRequested
                         && !weatherStation.subjectNavigationOpen

                sourceComponent:
                    weatherStation.currentView === "home"
                    ? homeViewComponent
                    : weatherStation.currentView === "ground"
                    ? groundViewComponent
                    : weatherStation.currentView === "sky"
                    ? skyViewComponent
                    : weatherStation.currentView === "space"
                    ? spaceViewComponent
                    : weatherStation.currentView === "map"
                    ? mapViewComponent
                    : weatherStation.currentView === "news"
                    ? newsViewComponent
                    : weatherStation.currentView === "radio"
                    ? radioViewComponent
                    : placeholderViewComponent
            }

            StationSubjectNavigator {
                id: subjectNavigator
                anchors.fill: parent
                visible: weatherStation.subjectNavigationOpen
                         && !weatherStation.contextTerminalRequested
                enabled: visible
                weatherService: weatherStation.weatherService
                spaceService: weatherStation.spaceService
                nwsAlertSource: weatherStation.nwsAlertSource
                historyService: weatherHistoryService
                seismicSource: seismicService
                lightningSource: lightningService
                riverSource: riverService
                persistentCacheStore: weatherStation.persistentCacheStore
                liveHistoryStore: weatherStation.liveHistoryStore
                eventArchiveStore: weatherStation.eventArchiveStore
                dossierArchiveStore: weatherStation.dossierArchiveStore
                homeFavoritesStore: homeFavoritesStore
                runtimeNowMs: weatherStation.runtimeNowMs
                onLegacyPageRequested: function(pageId) {
                    weatherStation.openLegacyFromSubject(pageId);
                }
            }

            StationTerminal {
                id: terminalView

                anchors.fill: parent
                visible: weatherStation.currentView === "terminal"
                         || weatherStation.contextTerminalRequested
                stationOpen: weatherStation.menuOpen
                terminalMode: weatherStation.currentView
                targetScreen: weatherStation.screen
                stationWidth: stationBackground.width
                stationHeight: stationBackground.height
                stationRightMargin: 20
                stationBottomMargin: 90
                stationHeaderHeight: header.height
                stationRailWidth: modeRail.width
            }
        }

        Component {
            id: homeViewComponent

            StationHome {
                weatherService: weatherStation.weatherService
                spaceService: weatherStation.spaceService
                nwsAlertSource: weatherStation.nwsAlertSource
                historyService: weatherHistoryService
                liveHistoryStore: weatherStation.liveHistoryStore
                runtimeNowMs: weatherStation.runtimeNowMs
            }
        }

        Component {
            id: groundViewComponent

            StationGround {
                weatherService: weatherStation.weatherService
                nwsAlertSource: weatherStation.nwsAlertSource
                seismicSource: seismicService
                lightningSource: lightningService
                riverSource: riverService
                persistentCacheStore: weatherStation.persistentCacheStore
                liveHistoryStore: weatherStation.liveHistoryStore
                runtimeNowMs: weatherStation.runtimeNowMs
            }
        }

        Component {
            id: skyViewComponent

            StationSky {
                weatherService: weatherStation.weatherService
                runtimeNowMs: weatherStation.runtimeNowMs
            }
        }

        Component {
            id: spaceViewComponent

            StationSpace {
                spaceService: weatherStation.spaceService
                weatherService: weatherStation.weatherService
                liveHistoryStore: weatherStation.liveHistoryStore
                runtimeNowMs: weatherStation.runtimeNowMs
            }
        }

        Component {
            id: mapViewComponent

            StationDiscovery {
                stationOpen: weatherStation.menuOpen
                domain: "map"
                seismicSource: seismicService
                lightningSource: lightningService
                riverSource: riverService
                weatherService: weatherStation.weatherService
                persistentCacheStore: weatherStation.persistentCacheStore
                eventArchiveStore: weatherStation.eventArchiveStore
                dossierArchiveStore: weatherStation.dossierArchiveStore
                newsMentionOverlay: weatherStation.newsMapOverlay
                runtimeNowMs: weatherStation.runtimeNowMs
                onNewsMapClearRequested: {
                    weatherStation.newsMapOverlay = null;
                }
            }
        }

        Component {
            id: newsViewComponent

            StationNewsHub {
                stationOpen: weatherStation.menuOpen
                runtimeNowMs: weatherStation.runtimeNowMs
                onNewsMapRequested: function(payload) {
                    if (!payload
                            || !Array.isArray(payload.locations)
                            || payload.locations.length === 0)
                        return;
                    weatherStation.newsMapOverlay =
                        JSON.parse(JSON.stringify(payload));
                    weatherStation.currentView = "map";
                    weatherStation.navigationIndex =
                        weatherStation.mainModes.findIndex(function(mode) {
                            return mode.id === "map";
                        });
                }
            }
        }

        Component {
            id: radioViewComponent

            StationRadio {
                stationOpen: weatherStation.menuOpen
            }
        }

        Component {
            id: placeholderViewComponent

            Rectangle {
                color: Colors.black

                Column {
                    anchors.centerIn: parent
                    spacing: 12

                    GohuText {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: weatherStation.currentViewName
                        font.pixelSize: 28
                        color: Colors.orange
                    }

                    SecondaryText {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "SOURCE NOT YET CONNECTED"
                        font.pixelSize: 16
                    }
                }
            }
        }

        // ─────────────────────────────────────────
        // FOOTER
        // ─────────────────────────────────────────

        Rectangle {
            id: footer

            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom

            height: 62

            color: Colors.black

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top

                anchors.leftMargin: 15
                anchors.rightMargin: 15

                height: 2

                color: Colors.cyan
            }

            Row {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter

                anchors.leftMargin: 20

                spacing: 8

                Text {
                    text: "◉"

                    font.family: "GohuFont 11 Nerd Font Mono"

                    font.pixelSize: 16

                    color: Colors.red
                }

                Text {
                    text: weatherStation.footerSourceStatus

                    font.family: "GohuFont 11 Nerd Font Mono"

                    font.pixelSize: 16

                    color: Colors.cyan
                }
            }

            Text {
                anchors.centerIn: parent

                text: "MEDIA BAY // IDLE"

                font.family: "GohuFont 11 Nerd Font Mono"

                font.pixelSize: 16

                color: Colors.white
            }

            Text {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter

                anchors.rightMargin: 20

                text: weatherStation.subjectNavigationOpen
                      ? "SUBJECTS" : weatherStation.currentViewName

                font.family: "GohuFont 11 Nerd Font Mono"

                font.pixelSize: 16

                color: Colors.cyan
            }
        }
    }

    Shortcut {
        sequence: "Escape"

        enabled: weatherStation.menuOpen

        onActivated: {
            if (weatherStation.subjectNavigationOpen)
                weatherStation.subjectNavigationOpen = false;
            else
                weatherStation.close();
        }
    }

    Shortcut {
        sequence: "Meta+Shift+Q"

        enabled: weatherStation.menuOpen

        onActivated: {
            weatherStation.close();
        }
    }
}
