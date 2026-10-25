import QtQuick
import Quickshell
import Quickshell.Wayland
import QtQuick.Effects
import Qt5Compat.GraphicalEffects
import "../../components"

PanelWindow {
    id: weatherStation

    property var weatherService: null
    property var spaceService: null

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

    readonly property string currentContext: currentViewName

    // Header source indicator follows the selected Main Mode's provider.
    // HOME is an aggregate surface now, so its badge represents both the
    // weather/air-quality stack and the independent NOAA space-weather stack.
    property int sourceStatusClock: 0

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

    readonly property int weatherAgeMinutes: {
        sourceStatusClock;

        if (!weatherService || !weatherService.ready)
            return -1;

        const stamp = weatherService.lastUpdated;
        if (!stamp || typeof stamp.getTime !== "function")
            return -1;

        const millis = stamp.getTime();
        if (!isFinite(millis) || millis <= 0)
            return -1;

        return Math.max(
            0,
            Math.floor((Date.now() - millis) / 60000)
        );
    }

    readonly property int spaceAgeMinutes: {
        sourceStatusClock;

        if (!spaceService)
            return -1;

        const stamp = spaceService.lastUpdated;
        if (!stamp || typeof stamp.getTime !== "function")
            return -1;

        const millis = stamp.getTime();
        if (!isFinite(millis) || millis <= 0)
            return -1;

        return Math.max(
            0,
            Math.floor((Date.now() - millis) / 60000)
        );
    }

    function compactAge(ageMinutes) {
        if (ageMinutes < 0)
            return "--";
        if (ageMinutes === 0)
            return "<1m";
        return ageMinutes + "m";
    }

    readonly property string footerSourceStatus:
        "WEATHER " + compactAge(weatherAgeMinutes)
        + " // SPACE " + compactAge(spaceAgeMinutes)

    readonly property bool weatherStale:
        weatherService
        && weatherService.ready
        && (
            String(weatherService.errorText || "").length > 0
            || weatherAgeMinutes >= 20
        )

    readonly property bool homeWeatherUsable:
        weatherService && weatherService.ready && !weatherStale
    readonly property bool homeSpaceUsable:
        spaceService && spaceService.ready
    readonly property bool homeSourceLoading:
        (weatherService && weatherService.loading)
        || (spaceService && spaceService.loading)
    readonly property bool homeSourceError:
        (weatherService
         && String(weatherService.errorText || "").length > 0)
        || (spaceService
            && String(spaceService.errorText || "").length > 0)

    readonly property string sourceStatusText: {
        if (usesHomeSources) {
            if (homeWeatherUsable && homeSpaceUsable)
                return "HOME LIVE";
            if (homeWeatherUsable || homeSpaceUsable)
                return "PARTIAL";
            if (homeSourceLoading)
                return "READING";
            if (homeSourceError)
                return "OFFLINE";
            return "CONNECTING";
        }

        if (usesWeatherSource) {
            if (!weatherService)
                return "OFFLINE";
            if (weatherService.loading)
                return "READING";
            if (!weatherService.ready)
                return String(weatherService.errorText || "").length > 0
                       ? "OFFLINE" : "CONNECTING";
            if (weatherStale)
                return "STALE";
            return "WEATHER LIVE";
        }

        if (usesSpaceSource) {
            if (!spaceService)
                return "OFFLINE";
            if (spaceService.loading)
                return "READING";
            if (spaceService.ready)
                return "SPACE LIVE";
            if (String(spaceService.errorText || "").length > 0)
                return "OFFLINE";
            return "PARTIAL";
        }
        if (usesNewsSource)
            return newsSourceItem ? newsSourceItem.feedBadge : "CONNECTING // NEWS";

        return "NO FEED";
    }

    readonly property string sourceStatusDisplay: {
        if (usesHomeSources) {
            if (homeWeatherUsable && homeSpaceUsable)
                return "HOME LIVE // 2 FEEDS";
            if (homeWeatherUsable)
                return "PARTIAL // WEATHER";
            if (homeSpaceUsable)
                return "PARTIAL // SPACE";
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

        if (usesSpaceSource || usesNewsSource)
            return sourceStatusText;

        return "NO FEED // NOT WIRED";
    }

    readonly property color sourceStatusColor: {
        if (usesHomeSources) {
            if (homeWeatherUsable && homeSpaceUsable)
                return Colors.magenta;
            if (homeWeatherUsable || homeSpaceUsable)
                return Colors.yellow;
            if (homeSourceLoading)
                return Colors.orange;
            if (homeSourceError)
                return Colors.red;
            return Colors.orange;
        }

        if (usesWeatherSource) {
            if (!weatherService)
                return Colors.red;
            if (weatherService.loading)
                return Colors.orange;
            if (!weatherService.ready)
                return String(weatherService.errorText || "").length > 0
                       ? Colors.red : Colors.orange;
            if (weatherStale)
                return Colors.yellow;
            return Colors.magenta;
        }

        if (usesSpaceSource) {
            if (!spaceService)
                return Colors.red;
            if (spaceService.loading)
                return Colors.orange;
            if (spaceService.ready)
                return Colors.magenta;
            if (String(spaceService.errorText || "").length > 0)
                return Colors.red;
            return Colors.yellow;
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
        const current = Math.max(0, mainModes.findIndex(function(mode) {
            return mode.id === currentView;
        }));
        const step = Number(direction) < 0 ? -1 : 1;
        const next = (current + step + mainModes.length) % mainModes.length;
        currentView = mainModes[next].id;
        navigationIndex = next;
    }

    function moveNavigationCursor(direction) {
        const step = Number(direction) < 0 ? -1 : 1;
        navigationIndex =
            (navigationIndex + step + mainModes.length) % mainModes.length;
    }

    function activateNavigationCursor() {
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

    function open() {
        weatherStation.keyboardOwnershipRequested();
        menuOpen = true;
        Qt.callLater(weatherStation.restoreWeatherKeyboardFocus);
    }

    function launchContextTerminal() {
        if (!menuOpen || terminalView.terminalState !== "IDLE")
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
        // One compositor-backed session at a time. Each new mode has a
        // different app ID; never direct Sway to close the wrong actor.
        closeContextTerminal();
    }

    function close() {
        closeContextTerminal();
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
                    label: weatherStation.currentView === "terminal"
                           ? "STAR MAP" : weatherStation.currentViewName
                    labelPixelSize: 11
                    contentPadding: 4
                    available: weatherStation.menuOpen
                               && terminalView.terminalState === "IDLE"
                    accentColor: Colors.cyan
                    onLeftClicked: weatherStation.launchContextTerminal()
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
                visible: weatherStation.currentView !== "terminal"
                         && !weatherStation.contextTerminalRequested

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
            }
        }

        Component {
            id: groundViewComponent

            StationGround {
                weatherService: weatherStation.weatherService
            }
        }

        Component {
            id: skyViewComponent

            StationSky {
                weatherService: weatherStation.weatherService
            }
        }

        Component {
            id: spaceViewComponent

            StationSpace {
                spaceService: weatherStation.spaceService
            }
        }

        Component {
            id: mapViewComponent

            StationDiscovery {
                stationOpen: weatherStation.menuOpen
                domain: "map"
            }
        }

        Component {
            id: newsViewComponent

            StationNewsHub {
                stationOpen: weatherStation.menuOpen
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

                text: weatherStation.currentViewName

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
