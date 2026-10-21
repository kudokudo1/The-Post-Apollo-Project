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

    property string activeDomain: "sky"
    property string currentView: "home"
    // A keyboard cursor previews rail controls; Enter activates it.
    property int navigationIndex: 0
    readonly property bool standardKeysAvailable:
        menuOpen
        && keyboardActive
        && (!relationshipFocusModeActive || relationshipFocused)

    readonly property var domains: [
        {
            "id": "ground",
            "name": "GROUND",
            "symbol": "⌁"
        },
        {
            "id": "sky",
            "name": "SKY",
            "symbol": "☁"
        },
        {
            "id": "space",
            "name": "SPACE",
            "symbol": "✦"
        }
    ]

    readonly property var views: [
        {
            "id": "map",
            "name": "MAP",
            "symbol": "⌖"
        },
        {
            "id": "news",
            "name": "NEWS",
            "symbol": "▤"
        },
        {
            "id": "radio",
            "name": "RADIO",
            "symbol": "◉"
        },
        {
            "id": "terminal",
            "name": "TERMINAL",
            "symbol": ">_"
        }
    ]

    readonly property string activeDomainName: {
        for (let i = 0; i < domains.length; i++) {
            if (domains[i].id === activeDomain)
                return domains[i].name;
        }

        return "UNKNOWN";
    }

    readonly property string currentViewName: {
        if (currentView === "home")
            return "HOME";

        for (let i = 0; i < views.length; i++) {
            if (views[i].id === currentView)
                return views[i].name;
        }

        return "UNKNOWN";
    }

    readonly property string currentContext: {
        if (currentView === "home")
            return "HOME";

        return activeDomainName + " // " + currentViewName;
    }

    // Header source indicator. HOME currently reflects the actual weather
    // transport; later MAP/NEWS/RADIO pages can replace this branch with
    // their own provider state without changing the header geometry.
    property int sourceStatusClock: 0

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

    readonly property bool weatherStale:
        weatherService
        && weatherService.ready
        && (
            String(weatherService.errorText || "").length > 0
            || weatherAgeMinutes >= 20
        )

    readonly property string sourceStatusText: {
        if (currentView !== "home")
            return "NO FEED";

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

    readonly property string sourceStatusDisplay: {
        if (currentView !== "home")
            return "NO FEED // NOT WIRED";

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

    readonly property color sourceStatusColor: {
        if (currentView !== "home")
            return Colors.orange;

        if (!weatherService)
            return Colors.red;

        if (weatherService.loading)
            return Colors.orange;

        if (!weatherService.ready)
            return String(weatherService.errorText || "").length > 0
                   ? Colors.red : Colors.orange;

        if (weatherStale)
            return Colors.yellow;

        // Healthy source relationship is magenta by operator decision.
        return Colors.magenta;
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

    margins {
        top: 0
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
            x: modeRail.width + terminalView.bayX

            y: header.height + terminalView.bayY

            width: weatherStation.menuOpen && weatherStation.currentView === "terminal" && terminalView.terminalState === "VISIBLE" ? terminalView.bayWidth : 0

            height: weatherStation.menuOpen && weatherStation.currentView === "terminal" && terminalView.terminalState === "VISIBLE" ? terminalView.bayHeight : 0

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
            } else if ((event.modifiers & Qt.ShiftModifier) !== 0
                       && (event.key === Qt.Key_Left
                           || event.key === Qt.Key_Right)) {
                weatherStation.cycleTopSubMode(
                    event.key === Qt.Key_Left ? -1 : 1
                );
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


    // The Home + VIEW pages are the Main Mode family. DOMAIN is a top
    // Sub Mode family; arrow/Enter navigation follows the actual vertical rail.
    function cycleMainMode(direction) {
        const pages = ["home"].concat(views.map(function(v) { return v.id; }));
        const current = Math.max(0, pages.indexOf(currentView));
        const step = Number(direction) < 0 ? -1 : 1;
        const next = (current + step + pages.length) % pages.length;
        currentView = pages[next];
        navigationIndex = next === 0 ? 0 : domains.length + next;
    }

    function cycleTopSubMode(direction) {
        const current = Math.max(0, domains.findIndex(function(d) {
            return d.id === activeDomain;
        }));
        const step = Number(direction) < 0 ? -1 : 1;
        const index = (current + step + domains.length) % domains.length;
        activeDomain = domains[index].id;
        navigationIndex = 1 + index;
    }

    function moveNavigationCursor(direction) {
        const count = 1 + domains.length + views.length;
        const step = Number(direction) < 0 ? -1 : 1;
        navigationIndex = (navigationIndex + step + count) % count;
    }

    function activateNavigationCursor() {
        if (navigationIndex === 0) {
            currentView = "home";
        } else if (navigationIndex <= domains.length) {
            activeDomain = domains[navigationIndex - 1].id;
        } else {
            currentView = views[navigationIndex - domains.length - 1].id;
        }
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
        sequence: "Shift+Left"
        context: Qt.WindowShortcut
        enabled: weatherStation.standardKeysAvailable
        onActivated: weatherStation.cycleTopSubMode(-1)
    }
    Shortcut {
        sequence: "Shift+Right"
        context: Qt.WindowShortcut
        enabled: weatherStation.standardKeysAvailable
        onActivated: weatherStation.cycleTopSubMode(1)
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

    function close() {
        terminalView.closeTerminal();
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

        fillVisible: true
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

                text: "✦ WEATHER STATION ✦"

                font.family: "GohuFont 11 Nerd Font Mono"

                font.pixelSize: 20

                color: Colors.cyan
            }

            Text {
                anchors.centerIn: parent

                text: weatherStation.currentContext

                font.family: "GohuFont 11 Nerd Font Mono"

                font.pixelSize: 18

                color: Colors.orange
            }

            Row {
                id: headerActions

                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.rightMargin: 14

                spacing: 8

                // Observatory expansion is not wired yet. Present it as an
                // unavailable shared action instead of a fake clickable glyph.
                ActionButton {
                    id: observatoryButton

                    width: 34
                    height: 32

                    label: "□"
                    labelPixelSize: 18
                    contentPadding: 4

                    available: false
                    interactive: false
                    accentColor: Colors.cyan
                    unavailableOpacity: 0.42
                }

                // Live source badge, matching the Git/Finance header grammar.
                // It is an indicator, not an input control.
                Rectangle {
                    id: sourceStatusIndicator

                    width: 164
                    height: 34
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
                        font.pixelSize: 10
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

                ModeButton {
                    id: homeButton
                    keyboardActive: weatherStation.standardKeysAvailable
                    keyboardSelected: weatherStation.navigationIndex === 0
                    onPointerMoved: weatherStation.navigationIndex = 0

                    width: railColumn.width
                    height: 48
                    selected: weatherStation.currentView === "home"
                    bordered: false
                    horizontalContent: true
                    contentSpacing: 10
                    iconFontSize: 18
                    labelFontSize: 18
                    iconText: "⌂"
                    labelText: "HOME"
                    onTriggered: {
                        weatherStation.navigationIndex = 0;
                        weatherStation.currentView = "home";
                    }
                }

                Item {
                    width: 1
                    height: 7
                }

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter

                    text: "DOMAIN"

                    font.family: "GohuFont 11 Nerd Font Mono"

                    font.pixelSize: 12

                    color: Colors.white
                }

                Repeater {
                    model: weatherStation.domains

                    delegate: ModeButton {
                        id: domainButton
                        keyboardActive: weatherStation.standardKeysAvailable
                        keyboardSelected: weatherStation.navigationIndex === 1 + index
                        onPointerMoved: weatherStation.navigationIndex = 1 + index
                        required property int index
                                                required property var modelData

                        width: railColumn.width
                        height: 48
                        selected: weatherStation.activeDomain === modelData.id
                        bordered: false
                        horizontalContent: true
                        contentSpacing: 10
                        iconFontSize: 18
                        labelFontSize: 18
                        iconText: modelData.symbol
                        labelText: modelData.name
                        onTriggered: {
                            weatherStation.navigationIndex = 1 + index;
                            weatherStation.activeDomain = modelData.id;
                        }
                    }
                }

                Item {
                    width: railColumn.width
                    height: 17

                    Rectangle {
                        anchors.centerIn: parent

                        width: parent.width - 28
                        height: 2

                        color: Colors.cyan
                    }
                }

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter

                    text: "VIEW"

                    font.family: "GohuFont 11 Nerd Font Mono"

                    font.pixelSize: 12

                    color: Colors.white
                }

                Repeater {
                    model: weatherStation.views

                    delegate: ModeButton {
                        id: viewButton
                        keyboardActive: weatherStation.standardKeysAvailable
                        keyboardSelected: weatherStation.navigationIndex
                                          === 1 + weatherStation.domains.length + index
                        onPointerMoved: weatherStation.navigationIndex =
                            1 + weatherStation.domains.length + index
                        required property int index
                                                required property var modelData

                        width: railColumn.width
                        height: 48
                        selected: weatherStation.currentView === modelData.id
                        bordered: false
                        horizontalContent: true
                        contentSpacing: 10
                        iconFontSize: 18
                        labelFontSize: 18
                        iconText: modelData.symbol
                        labelText: modelData.name
                        onTriggered: {
                            weatherStation.navigationIndex =
                                1 + weatherStation.domains.length + index;
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

            color: weatherStation.currentView === "terminal" ? "transparent" : Colors.black

            clip: true

            Loader {
                anchors.fill: parent

                visible: weatherStation.currentView !== "terminal"

                sourceComponent: weatherStation.currentView === "home" ? homeViewComponent : placeholderViewComponent
            }

            StationTerminal {
                id: terminalView

                anchors.fill: parent

                visible: weatherStation.currentView === "terminal"

                stationOpen: weatherStation.menuOpen

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
                activeDomain: weatherStation.activeDomain

                weatherService: weatherStation.weatherService

                spaceService: weatherStation.spaceService

                onDomainRequested: function (domain) {
                    weatherStation.activeDomain = domain;
                }
            }
        }

        Component {
            id: placeholderViewComponent

            Rectangle {
                color: Colors.black

                Column {
                    anchors.centerIn: parent

                    spacing: 12

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter

                        text: weatherStation.activeDomainName

                        font.family: "GohuFont 11 Nerd Font Mono"

                        font.pixelSize: 20

                        color: Colors.cyan
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter

                        text: weatherStation.currentViewName

                        font.family: "GohuFont 11 Nerd Font Mono"

                        font.pixelSize: 28

                        color: Colors.orange
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter

                        text: {
                            if (weatherStation.currentView === "map")
                                return "map display offline...";

                            if (weatherStation.currentView === "news")
                                return "news receiver offline...";

                            if (weatherStation.currentView === "radio")
                                return "radio receiver offline...";

                            return "";
                        }

                        font.family: "GohuFont 11 Nerd Font Mono"

                        font.pixelSize: 16

                        color: Colors.white
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

            Text {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter

                anchors.leftMargin: 20

                text: weatherStation.weatherService && weatherStation.weatherService.ready ? "◉ WEATHER LINK ONLINE" : "◉ SYSTEM ONLINE"

                font.family: "GohuFont 11 Nerd Font Mono"

                font.pixelSize: 16

                color: Colors.cyan
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

                text: weatherStation.activeDomainName

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
