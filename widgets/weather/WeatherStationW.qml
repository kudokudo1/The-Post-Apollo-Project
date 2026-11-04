import QtQuick
import Quickshell
import Quickshell.Wayland
import QtQuick.Effects
import Qt5Compat.GraphicalEffects
import "../../components"
import "../../services/weather" as WeatherServices
import "StationOfficialAlertPolicy.js" as OfficialAlertPolicy
import "StationWeatherSubjectPanelPolicy.js" as SubjectPanelPolicy
import "StationSubjectSourceBadgePolicy.js" as SubjectSourceBadge
import "StationSubjectDefaultPolicy.js" as SubjectDefaultPolicy
import "StationProviderDiagnosticsPolicy.js" as ProviderDiagnostics
import "StationMagickSubjectPanelPolicy.js" as MagickPanelPolicy
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

    // M30-B // One owner for M4 celestial graphs, also available on MAGICK
    // overview for its explicit CALCULATE control. No automatic execution.
    // No polling, automatic download, local write, or extra provider.
    WeatherServices.CelestialVisualService {
        id: celestialVisualService
        active: weatherStation.menuOpen
                && weatherStation.subjectNavigationOpen
                && !weatherStation.contextTerminalRequested
                && (MagickPanelPolicy.visualForRoute(subjectNavigator.currentPath)
                    || subjectNavigator.currentPath === "magick/overview")
        route: subjectNavigator.currentPath
        anchorNowMs: weatherStation.runtimeNowMs
    }

    // W2b single Weather-owned bookmark writer; never touches AppControl.
    // The FileView reads at startup but only explicit pin clicks write.
    WeatherServices.WeatherHomeFavoritesStore {
        id: homeFavoritesStore
    }

    WeatherServices.WeatherHistoryService {
        id: weatherHistoryService
        active: weatherStation.menuOpen && weatherStation.subjectNavigationOpen
                && (subjectNavigator.liveHomeKind !== ""
                    || SubjectPanelPolicy.needsSource(
                        subjectNavigator.currentPath, "history"))
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
        active: weatherStation.menuOpen && weatherStation.subjectNavigationOpen
                && (EarthPanelPolicy.needsSource(
                               subjectNavigator.currentPath, "seismic")
                            || SubjectPanelPolicy.needsSource(
                               subjectNavigator.currentPath, "seismic"))

    }

    WeatherServices.NowcoastLightningService {
        id: lightningService
        active: weatherStation.menuOpen && weatherStation.subjectNavigationOpen
                && (SubjectPanelPolicy.needsSource(
                               subjectNavigator.currentPath, "lightning")
                            || EarthPanelPolicy.needsSource(
                               subjectNavigator.currentPath, "lightning"))
        latitude: weatherStation.weatherService
                  ? weatherStation.weatherService.latitude : ""
        longitude: weatherStation.weatherService
                   ? weatherStation.weatherService.longitude : ""
    }

    WeatherServices.NwpsRiverService {
        id: riverService
        cacheStore: weatherStation.persistentCacheStore
        active: weatherStation.menuOpen && weatherStation.subjectNavigationOpen
                && (SubjectPanelPolicy.needsSource(
                               subjectNavigator.currentPath, "river")
                            || EarthPanelPolicy.needsSource(
                               subjectNavigator.currentPath, "river"))
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
    // SUBJECTS is the only presentation; the collapsed host unloads it.
    property bool providerDiagnosticsOpen: false
    onMenuOpenChanged: {
        if (!menuOpen)
            providerDiagnosticsOpen = false;
    }
    property bool relationshipFocusModeActive: false
    property bool relationshipFocused: false

    // Collapsed 0x0 PanelWindow must NEVER keep SUBJECTS workspace loaded.
    // The M28-N pilot selects SUBJECTS only on explicit open(), not at init.
    property bool subjectNavigationOpen: false
    property bool contextTerminalRequested: false
    // M28-C: subject-native TOOLS launches reuse the ONE root StationTerminal.
    // This is a fixed mode, never a user-supplied shell command.
    property string subjectTerminalMode: "terminal"

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
        menuOpen && contextTerminalRequested
        && terminalView.sessionMode === subjectTerminalMode
        && terminalView.terminalState === "VISIBLE"
        && terminalHoleValid

    readonly property bool standardKeysAvailable:
        menuOpen && keyboardActive
        && (!relationshipFocusModeActive || relationshipFocused)

    readonly property string currentContext:
        subjectNavigator.liveHomeKind !== "" ? "HOME"
        : subjectNavigator.liveWeatherKind !== "" ? "WEATHER"
        : subjectNavigator.liveCosmosKind !== "" ? "COSMOS"
        : subjectNavigator.liveEarthKind !== "" ? "EARTH"
        : subjectNavigator.liveMediaKind !== "" ? "MEDIA"
        : subjectNavigator.liveMagickKind !== "" ? "MAGICK"
        : subjectNavigator.liveToolsKind !== "" ? "TOOLS"
        : "SUBJECT INDEX"

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

    // Read-only view over one shared WeatherService. No diagnostics poller.
    readonly property var weatherDiagnostics:
        ProviderDiagnostics.snapshot({
            ready: weatherService ? weatherService.ready : false,
            loading: weatherService ? weatherService.loading : false,
            activeProvider: weatherService
                            ? weatherService.activeWeatherProvider : "NONE",
            cachedProvider: weatherService
                            ? weatherService.cachedWeatherProvider : "",
            usingCache: weatherService
                        ? weatherService.usingPersistentCurrentCache : false,
            lastUpdated: weatherService ? weatherService.lastUpdated : null,
            selectedPlace: weatherService ? weatherService.selectedPlace : null,
            primaryStatus: weatherService
                           ? weatherService.primaryWeatherStatus : "IDLE",
            fallbackStatus: weatherService
                            ? weatherService.fallbackWeatherStatus : "IDLE",
            fallbackError: weatherService
                           ? weatherService.fallbackWeatherError : "",
            primaryLastSuccessAt: weatherService
                                  ? weatherService.primaryLastSuccessAt : null,
            fallbackLastSuccessAt: weatherService
                                   ? weatherService.fallbackLastSuccessAt : null,
            aqiReady: weatherService ? weatherService.aqiReady : false,
            aqiLoading: weatherService ? weatherService.aqiLoading : false,
            aqiUsingCache: weatherService
                           ? weatherService.usingPersistentAqiCache : false,
            aqiLastUpdated: weatherService
                            ? weatherService.aqiLastUpdated : null,
            aqiError: weatherService
                      ? weatherService.aqiErrorText : "",
            error: weatherService ? weatherService.errorText : ""
        }, runtimeNowMs)

    // The one active SUBJECTS map owns the runtime rows.
    readonly property var currentPageRuntimeRows:
        subjectNavigator.liveMapRuntimeRows
    readonly property var currentPageRuntimeSummary:
        RuntimePolicy.summarizeRows(currentPageRuntimeRows)
    readonly property var subjectSourceBadge:
        SubjectSourceBadge.badgeFor(
            subjectNavigator.currentPath,subjectNavigator.indexOpen,
            weatherRuntimeState,spaceRuntimeState,currentPageRuntimeSummary)

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
        if (!subjectNavigator.indexOpen
                && subjectNavigator.liveWeatherKind !== "")
            return weatherDiagnostics.header;
        return subjectSourceBadge.text;
    }
    readonly property string sourceStatusDisplay: sourceStatusText
    readonly property color sourceStatusColor: {
        if (officialAlertSummary.available)
            return officialAlertColor(officialAlertSummary.colorToken);
        if (!subjectNavigator.indexOpen
                && subjectNavigator.liveWeatherKind !== "") {
            if (weatherDiagnostics.currentState === "CACHE"
                    || weatherDiagnostics.currentState === "FALLBACK")
                return Colors.yellow;
            if (weatherDiagnostics.currentState === "OFFLINE")
                return Colors.red;
            if (weatherDiagnostics.currentState === "READING")
                return Colors.orange;
            return Colors.cyan;
        }
        switch (subjectSourceBadge.tone) {
        case "red": return Colors.red;
        case "yellow": return Colors.yellow;
        case "orange": return Colors.orange;
        case "blue": return Colors.blue;
        case "green": return Colors.green;
        case "magenta": return Colors.magenta;
        default: return Colors.cyan;
        }
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
                weatherStation.handleEscape();
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

    function handleEscape() {
        // Diagnostics closes first; INDEX returns to its workspace;
        // Escape from the workspace closes the station.
        if (providerDiagnosticsOpen) {
            providerDiagnosticsOpen = false;
            return;
        }
        const action = SubjectDefaultPolicy.escapeAction(subjectNavigator.indexOpen);
        if (action === "workspace")
            subjectNavigator.returnToWorkspace();
        else
            close();
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


    // Keyboard navigation only targets the native SUBJECTS/INDEX rail.
    function cycleMainMode(direction) {
        subjectNavigator.cycleSubjects(direction);
    }
    function moveNavigationCursor(direction) {
        subjectNavigator.moveCursor(direction);
    }
    function activateNavigationCursor() {
        subjectNavigator.activateCursor();
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

    // Notifications retain historical view tokens but now open native routes.
    function openNotificationView(view) {
        const targets = {
            "home":"home/overview",
            "ground":"weather/ground/full",
            "sky":"weather/conditions/current",
            "space":"cosmos/space-weather/full",
            "map":"earth/maps/full",
            "news":"media/news/full",
            "radio":"media/radio/full",
            "terminal":"tools/terminal/star-map"
        };
        const target = targets[String(view || "")];
        if (!target)
            return false;
        if (!menuOpen)
            open();
        if (!menuOpen || contextTerminalRequested)
            return false;
        return subjectNavigator.chooseRoute(target);
    }

    function open() {
        // A live compositor-backed Kitty actor must not be masked by opening.
        if (terminalView.terminalState !== "IDLE")
            return;
        weatherStation.keyboardOwnershipRequested();
        if (subjectNavigator.indexOpen)
            subjectNavigator.returnToWorkspace();
        subjectNavigationOpen = true;
        menuOpen = true;
        Qt.callLater(weatherStation.restoreWeatherKeyboardFocus);
    }

    function launchSubjectTerminal(mode) {
        // TOOLS owns this routed launch; reuse the single root Kitty actor.
        if (!menuOpen || !subjectNavigationOpen || subjectNavigator.indexOpen
                || contextTerminalRequested
                || terminalView.terminalState !== "IDLE")
            return false;
        const route = subjectNavigator.currentPath;
        const consoleModes = ["home","ground","sky","space","map",
                              "news","radio"];
        const allowed = route === "tools/terminal/star-map"
            ? mode === "terminal"
            : route === "tools/terminal/consoles"
              && consoleModes.indexOf(mode) >= 0;
        if (!allowed || !terminalView.outputName)
            return false;
        subjectTerminalMode = mode;
        contextTerminalRequested = true;
        // The root Terminal is now visible; launch only after geometry
        // binding and terminalMode have adopted the requested identity.
        Qt.callLater(function() {
            if (menuOpen && subjectNavigationOpen && contextTerminalRequested
                    && subjectNavigator.currentPath === route
                    && terminalView.terminalMode === mode) {
                if (!terminalView.openTerminal())
                    contextTerminalRequested = false;
            } else if (terminalView.terminalState === "IDLE") {
                // The route/host changed before the deferred launch.
                // Never strand SUBJECTS behind a blank terminal overlay.
                contextTerminalRequested = false;
            }
        });
        return true;
    }

    // Header SHORTCUT to the existing SUBJECTS STAR MAP route. Navigation
    // must happen first because launchSubjectTerminal guards the owning TOOLS
    // route; neither a second Kitty actor nor a Classic mode may be created.
    function launchHeaderTerminal() {
        if (!menuOpen || !subjectNavigationOpen || contextTerminalRequested
                || terminalView.terminalState !== "IDLE"
                || !terminalView.outputName)
            return false;
        if (!subjectNavigator.chooseRoute("tools/terminal/star-map"))
            return false;
        return launchSubjectTerminal("terminal");
    }

    function closeContextTerminal() {
        terminalView.closeTerminal();
        contextTerminalRequested = false;
    }

    function close() {
        closeContextTerminal();
        // Unload SUBJECTS in the collapsed 0x0 layer-shell host.
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
                    label: "INDEX"
                    labelPixelSize: 11
                    contentPadding: 4
                    available: weatherStation.menuOpen
                               && terminalView.terminalState === "IDLE"
                               && !weatherStation.contextTerminalRequested
                    accentColor: Colors.cyan
                    onLeftClicked: {
                        if (subjectNavigator.indexOpen)
                            subjectNavigator.returnToWorkspace();
                        else
                            subjectNavigator.openIndex();
                    }
                }

                // The former inactive CLOSE slot is the persistent
                // terminal control: launch STAR MAP while idle and CLOSE
                // the same verified Kitty actor while active. Its right edge
                // stays in the original header position next to the divider.
                ActionButton {
                    id: contextTerminalClose
                    readonly property bool terminalSessionActive:
                        weatherStation.contextTerminalRequested
                        || terminalView.terminalState !== "IDLE"
                    width: 88
                    height: 32
                    label: terminalSessionActive ? "CLOSE" : "TERMINAL"
                    labelPixelSize: 11
                    contentPadding: 4
                    accentColor: terminalSessionActive ? Colors.red : Colors.cyan
                    destructive: terminalSessionActive
                    idleForegroundColor: terminalSessionActive ? Colors.red : Colors.cyan
                    idleBorderColor: terminalSessionActive ? Colors.red : Colors.cyan
                    hoverForegroundColor: terminalSessionActive ? Colors.red : Colors.orange
                    hoverBorderColor: terminalSessionActive ? Colors.red : Colors.orange
                    idleContentGlowColor: terminalSessionActive ? Colors.red : Colors.cyan
                    hoverContentGlowColor: terminalSessionActive ? Colors.red : Colors.orange
                    idleSoftGlowColor: terminalSessionActive ? Colors.red : Colors.cyan
                    hoverSoftGlowColor: terminalSessionActive ? Colors.red : Colors.orange
                    available: weatherStation.menuOpen
                               && (terminalSessionActive
                                   || (weatherStation.subjectNavigationOpen
                                       && terminalView.outputName))
                    onLeftClicked: {
                        if (terminalSessionActive)
                            weatherStation.closeContextTerminal();
                        else
                            weatherStation.launchHeaderTerminal();
                    }
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

                // Inspect the live provider owners without adding another
                // source or hijacking the existing header status indicator.
                ActionButton {
                    id: providerDiagnosticsButton
                    width: 59
                    height: 32
                    label: weatherStation.providerDiagnosticsOpen
                           ? "BACK" : "DIAG"
                    labelPixelSize: 11
                    contentPadding: 4
                    accentColor: Colors.yellow
                    available: weatherStation.menuOpen
                               && !weatherStation.contextTerminalRequested
                    onLeftClicked:
                        weatherStation.providerDiagnosticsOpen =
                            !weatherStation.providerDiagnosticsOpen
                }

                // Live source badge, matching the Git/Finance header grammar.
                // It remains an indicator, not an input control.
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

            // Seven-family workspace and deep INDEX share this rail.
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

            // Native family rail reuses original 160px geometry.
            // INDEX retains the separate detailed rail.
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

            color: weatherStation.contextTerminalRequested
                   ? "transparent" : Colors.black

            clip: true

            StationSubjectNavigator {
                id: subjectNavigator
                celestialSource: celestialVisualService
                anchors.fill: parent
                visible: weatherStation.subjectNavigationOpen
                         && weatherStation.menuOpen
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
                onTerminalLaunchRequested: function(mode) {
                    weatherStation.launchSubjectTerminal(mode);
                }
            }

            StationTerminal {
                id: terminalView

                anchors.fill: parent
                visible: weatherStation.contextTerminalRequested
                stationOpen: weatherStation.menuOpen
                terminalMode: weatherStation.subjectTerminalMode
                targetScreen: weatherStation.screen
                stationWidth: stationBackground.width
                stationHeight: stationBackground.height
                stationRightMargin: 20
                stationBottomMargin: 90
                stationHeaderHeight: header.height
                stationRailWidth: modeRail.width
            }

            StationWeatherProviderDiagnostics {
                id: providerDiagnosticsPane
                z: 50
                visible: weatherStation.providerDiagnosticsOpen
                         && !terminalView.visible
                enabled: visible
                width: Math.min(478, parent.width - 24)
                height: Math.min(460, parent.height - 24)
                anchors.top: parent.top
                anchors.right: parent.right
                anchors.topMargin: 12
                anchors.rightMargin: 12
                snapshot: weatherStation.weatherDiagnostics
                onCloseRequested: weatherStation.providerDiagnosticsOpen = false
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

                text: "SUBJECTS"

                font.family: "GohuFont 11 Nerd Font Mono"

                font.pixelSize: 16

                color: Colors.cyan
            }
        }
    }

    Shortcut {
        sequence: "Escape"

        enabled: weatherStation.menuOpen
        onActivated: weatherStation.handleEscape()
    }

    Shortcut {
        sequence: "Meta+Shift+Q"

        enabled: weatherStation.menuOpen

        onActivated: {
            weatherStation.close();
        }
    }
}
