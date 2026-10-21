import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.components
import qs.services.notifications
import "../../services/notifications/NotificationFacets.js" as NotificationFacets
import QtQuick.Effects
import Qt5Compat.GraphicalEffects

PanelWindow {
    id: root

    property bool menuOpen: false
    // Read-only update offers and explicit local reviewer. No update
    // credentials, shell snippets, or arbitrary notification actions.
    property var updatesController: null
    // Koinoikos / shared keyboard-owner compatibility. The menu remains
    // mapped while closed; neither visibility nor visual selection is focus.
    property bool keyboardActive: false
    property bool keyboardLock: false
    property bool relationshipFocusModeActive: false
    property bool relationshipFocused: false
    signal keyboardOwnershipRequested()

    function restoreKeyboardNavigationAnchor() {
        if (!menuOpen || !keyboardActive || searchInput.activeFocus)
            return;
        notificationKeyboardAnchor.forceActiveFocus();
    }

    // A permanent-mapped PanelWindow can receive the owner claim before
    // the compositor has committed its newly opened input region. Retry that
    // *initial* acquisition once after a frame only when Qt still reports
    // that Notifications itself is NOT the active window. This invokes the
    // existing bounded owner pulse; it never installs persistent Exclusive.
    Timer {
        id: notificationOpenFocusRetry
        interval: 48
        repeat: false
        onTriggered: {
            if (!root.menuOpen || !root.keyboardActive
                    || notificationKeyboardAnchor.Window.active)
                return;
            root.keyboardOwnershipRequested();
            Qt.callLater(root.restoreKeyboardNavigationAnchor);
        }
    }

    onKeyboardActiveChanged: {
        if (keyboardActive && menuOpen) {
            Qt.callLater(root.restoreKeyboardNavigationAnchor);
            notificationOpenFocusRetry.restart();
        } else {
            notificationOpenFocusRetry.stop();
        }
    }

    onMenuOpenChanged: {
        if (menuOpen && keyboardActive) {
            Qt.callLater(root.restoreKeyboardNavigationAnchor);
            notificationOpenFocusRetry.restart();
        } else if (!menuOpen) {
            notificationOpenFocusRetry.stop();
            listKeyboardSelectionActive = false;
        }
    }

    // ===== QUICK CONFIG =========================================
    // Main panel geometry. These preserve the placement you already dialed in.
    property int panelWidth: 520

    property int panelTopMargin: 0
    property int panelBottomMargin: 5
    property int panelLeftMargin: 0
    property int panelRightMargin: 5

    property int frameInset: 8

    // Main purple glass.
    property real backgroundOpacity: 0.64

    // Card opacity compensation:
    //
    // Previous target:
    //     background 0.60 + card 0.76 = ~0.904 effective alpha
    //
    // With background at 0.64:
    //     x + 0.64 * (1 - x) = 0.904
    //     x ~= 0.7333
    //
    // This keeps the notification fill visually close to the previous pass.
    property real cardFillOpacity: 0.7333

    // Header / search / filters.
    property int headerHeight: 122

    property int searchHeight: 32
    property int filterStripHeight: 30
    property int filterButtonHeight: 30
    property int filterButtonSpacing: 5

    property int historyTopGap: 10
    property int historyBottomGap: 12

    // Bottom fixed control bay.
    property int controlBayHeight: 220
    property int controlBaySideMargin: 10
    property int controlBayBottomMargin: 10
    property real controlBayOpacity: 0.64

    // Notification cards.
    property int cardHeight: 116
    property int reportCardHeight: 352 // solar/weather records need readable multiline history
    property int cardSpacing: 2
    property int cardGlowGutter: 24
    property int cardContentMargin: 10

    // General text glow.
    property real textGlowOpacity: 0.60
    property int textGlowRadius: 14
    property int textGlowSamples: 15

    // Tighter white/cyan text glow.
    property int tightGlowRadius: 7
    property int tightGlowSamples: 9

    // Outer window glow is border-sourced rather than a full-rectangle shadow.
    // This keeps orange light around the perimeter without tinting the
    // translucent purple glass through the center of the Hub.
    property int frameCloseGlowRadius: 6
    property int frameCloseGlowSamples: 9
    property real frameCloseGlowOpacity: 0.58
    property int frameWideGlowRadius: 8
    property int frameWideGlowSamples: 11
    property real frameWideGlowOpacity: 0.16

    // History cards keep only a restrained local aura. Their combined
    // gutter/spacing is intentionally close to the old pre-glow density.
    property int cardGlowVerticalGutter: 5
    property int cardCloseGlowSpread: 2
    property real cardCloseGlowOpacity: 0.28
    property int cardWideGlowSpread: 5
    property real cardWideGlowOpacity: 0.06

    // Typography.
    property int hubTitleFontSize: 20
    property int storedCountFontSize: 14

    property int appNameFontSize: 14
    property int notificationTitleFontSize: 15
    property int notificationMessageFontSize: 13
    property int notificationMetaFontSize: 10

    // App icon.
    property int appIconSize: 36
    property int appIconInnerMargin: 3

    // Scroll bar:
    // cyan track is intentionally 2px thicker than magenta thumb.
    property int scrollBarAreaWidth: 16
    property int scrollTrackWidth: 7
    property int scrollThumbWidth: 5
    property int scrollThumbMinHeight: 34

    // Post-Apollo semantic green.
    // Use this everywhere this file means "green".
    property color omnitrixGreen: "#00F782"

    // ===== SEARCH / FILTER STATE ================================

    property string searchQuery: ""
    property string activeFilter: "all"
    // Eight Main Mode buttons in filterStrip, in visual order.
    // They are Main Modes, not "History" plus six Sub Modes.
    readonly property var mainModeOrder: [
        "all", "favorites", "apps", "social", "apollo", "system", "warning", "manager"
    ]
    property bool listKeyboardSelectionActive: false
    property string managerSelectionSection: "dnd"
    // Do not take mode keys from the search editor or destructive dialogs.
    readonly property bool standardKeysAvailable:
        menuOpen && keyboardActive && !searchInput.activeFocus
        && pendingClearAllKey === "" && pendingClearAllSource === ""

    // Tab cycles every real filter button in visual order; Shift+Tab
    // reverses. A mouse click changes activeFilter, so the next key
    // continues from the clicked button rather than switching to Manager.
    function cycleMainMode(direction) {
        const count = mainModeOrder.length;
        if (count === 0)
            return;
        const current = Math.max(0, mainModeOrder.indexOf(activeFilter));
        const step = Number(direction) < 0 ? -1 : 1;
        activeFilter = mainModeOrder[(current + step + count) % count];
    }

    function moveCurrentList(direction) {
        const list = activeFilter === "manager"
            ? (managerSelectionSection === "favorites" ? favoriteManagerList : dndManagerList)
            : historyList;
        if (list.count < 1)
            return;
        const step = Number(direction) < 0 ? -1 : 1;
        // Starting from a newly opened or switched page, the first arrow
        // selects an actual visible item rather than skipping index zero.
        const index = !listKeyboardSelectionActive || list.currentIndex < 0
            ? (step < 0 ? list.count - 1 : 0)
            : (list.currentIndex + step + list.count) % list.count;
        listKeyboardSelectionActive = true;
        list.currentIndex = index;
        list.positionViewAtIndex(index, ListView.Contain);
    }

    function activateCurrentHistoryItem() {
        // Manager allows explicit ALLOW clicks only; pressing Enter must
        // never implicitly remove a DND policy.
        if (!listKeyboardSelectionActive || activeFilter === "manager")
            return;
        const index = historyList.currentIndex;
        if (index < 0 || index >= filteredNotifications.count)
            return;
        const row = filteredNotifications.get(index);
        if (row)
            takeMeToApp(row.sourceId, row.source);
    }

    // Scope Escape to this window's active keyboard ownership.
    function handleEscape() {
        if (!menuOpen || !keyboardActive)
            return;
        if (pendingClearAllKey !== "") {
            cancelClearAll();
            return;
        }
        close();
    }

    Shortcut {
        sequence: "Escape"
        context: Qt.WindowShortcut
        enabled: root.menuOpen && root.keyboardActive
        onActivated: root.handleEscape()
    }
    Shortcut {
        sequence: "Left"
        context: Qt.WindowShortcut
        enabled: root.standardKeysAvailable && root.activeFilter === "manager"
        onActivated: {
            root.managerSelectionSection = "dnd";
            root.listKeyboardSelectionActive = false;
        }
    }
    Shortcut {
        sequence: "Right"
        context: Qt.WindowShortcut
        enabled: root.standardKeysAvailable && root.activeFilter === "manager"
        onActivated: {
            root.managerSelectionSection = "favorites";
            root.listKeyboardSelectionActive = false;
        }
    }
    Shortcut {
        sequence: "Tab"
        context: Qt.WindowShortcut
        enabled: root.standardKeysAvailable
        onActivated: root.cycleMainMode(1)
    }
    Shortcut {
        sequence: "Shift+Tab"
        context: Qt.WindowShortcut
        enabled: root.standardKeysAvailable
        onActivated: root.cycleMainMode(-1)
    }
    Shortcut {
        sequence: "Enter"
        context: Qt.WindowShortcut
        enabled: root.standardKeysAvailable && root.listKeyboardSelectionActive
                 && root.activeFilter !== "manager"
        onActivated: root.activateCurrentHistoryItem()
    }
    Shortcut {
        sequence: "Return"
        context: Qt.WindowShortcut
        enabled: root.standardKeysAvailable && root.listKeyboardSelectionActive
                 && root.activeFilter !== "manager"
        onActivated: root.activateCurrentHistoryItem()
    }
    Shortcut {
        sequence: "Up"
        context: Qt.WindowShortcut
        enabled: root.standardKeysAvailable
        onActivated: root.moveCurrentList(-1)
    }
    Shortcut {
        sequence: "Down"
        context: Qt.WindowShortcut
        enabled: root.standardKeysAvailable
        onActivated: root.moveCurrentList(1)
    }

    property string pendingClearAllKey: ""
    property string pendingClearAllSource: ""

    // Keep the heavy ListView on an actually filtered model.
    // Zero-height delegates force ListView to walk and construct large
    // stretches of hidden history just to fill the viewport.
    ListModel {
        id: filteredNotifications
    }

    ListModel {
        id: managerDndPolicies
    }

    Timer {
        id: filteredModelRefreshTimer

        interval: 0
        repeat: false

        onTriggered: {
            root.rebuildFilteredNotifications();
        }
    }

    Connections {
        target: NotificationsService

        function onNotificationsRevisionChanged() {
            root.scheduleFilteredModelRebuild();
        }

        function onPolicyRevisionChanged() {
            root.rebuildManagerDndPolicies();
        }
        function onFavoritesRevisionChanged() {
            root.scheduleFilteredModelRebuild();
        }
    }

    onActiveFilterChanged: {
        listKeyboardSelectionActive = false;
        if (activeFilter === "manager")
            managerSelectionSection = dndManagerList.count > 0 ? "dnd" : "favorites";
        root.scheduleFilteredModelRebuild();
    }

    onSearchQueryChanged: {
        listKeyboardSelectionActive = false;
        root.scheduleFilteredModelRebuild();
    }

    Component.onCompleted: {
        root.scheduleFilteredModelRebuild();
        root.rebuildManagerDndPolicies();
    }

    // ===== APP-WIDE CARD STATE ==================================
    // Favorite, DND and snooze are independent persistent service preferences.

    // ===== WINDOW ===============================================

    implicitWidth: root.panelWidth

    anchors {
        top: true
        bottom: true
        left: false
        right: true
    }

    margins {
        top: root.panelTopMargin
        bottom: root.panelBottomMargin
        left: root.panelLeftMargin
        right: root.panelRightMargin
    }

    exclusiveZone: 0

    WlrLayershell.layer: WlrLayer.Overlay
    // Same bounded acquisition pulse as the Git/Hospital owner pilot.
    // Never hold Exclusive merely because this history window stays mapped.
    WlrLayershell.keyboardFocus:
        !root.menuOpen || !root.keyboardActive
        ? WlrKeyboardFocus.None
        : root.keyboardLock
        ? WlrKeyboardFocus.Exclusive
        : WlrKeyboardFocus.OnDemand

    color: "transparent"

    surfaceFormat.opaque: false

    // IMPORTANT:
    // Keep the real PanelWindow mapped permanently.
    //
    // Repeated unmap/remap was what triggered the native Qt/Quickshell
    // second-open crash.
    visible: true

    // Closed = invisible + click-through.
    mask: Region {
        x: 0
        y: 0

        width: root.menuOpen ? root.width : 0
        height: root.menuOpen ? root.height : 0
    }

    // Keyboard anchor is separate from the SEARCH editor. The first Tab
    // after opening switches actual Main Modes, not input-widget focus.
    Item {
        id: notificationKeyboardAnchor
        anchors.fill: parent
        enabled: root.menuOpen
        focus: root.menuOpen && root.keyboardActive
        z: -1000

        // Qt may treat Tab as focus-chain navigation before a WindowShortcut
        // fires. Keep a *local* KeyPress path on the navigation anchor; it
        // only runs once the compositor really delivers keys to this window.
        Keys.priority: Keys.BeforeItem
        Keys.onShortcutOverride: function(event) {
            if (!root.standardKeysAvailable)
                return;
            if (event.key === Qt.Key_Tab || event.key === Qt.Key_Backtab
                    || event.key === Qt.Key_Escape)
                event.accepted = true;
        }
        Keys.onPressed: function(event) {
            if (event.key === Qt.Key_Escape && root.menuOpen && root.keyboardActive) {
                root.handleEscape();
                event.accepted = true;
                return;
            }
            if (!root.standardKeysAvailable)
                return;
            if (event.key !== Qt.Key_Tab && event.key !== Qt.Key_Backtab)
                return;
            const reverse = event.key === Qt.Key_Backtab
                || (event.modifiers & Qt.ShiftModifier) !== 0;
            root.cycleMainMode(reverse ? -1 : 1);
            event.accepted = true;
        }
    }

    // ===== LOCAL VISUAL TYPE: GLOW TEXT =========================

    component GlowText: Item {
        id: glowText

        property string text: ""

        property color textColor: Colors.cyan
        property color glowColor: textColor

        property int pixelSize: 14

        property real glowOpacity: root.textGlowOpacity
        property real glowRadius: root.textGlowRadius
        property int glowSamples: root.textGlowSamples

        property int elideMode: Text.ElideNone
        property int wrapMode: Text.NoWrap
        property int horizontalAlignment: Text.AlignLeft
        // Real wrapped Text height, independent of the old fixed card height.
        readonly property real fullTextHeight: glowLabel.contentHeight

        GohuText {
            id: glowLabel

            anchors.fill: parent

            text: glowText.text

            font.pixelSize: glowText.pixelSize

            color: glowText.textColor

            elide: glowText.elideMode
            wrapMode: glowText.wrapMode

            horizontalAlignment: glowText.horizontalAlignment
            verticalAlignment: glowText.wrapMode === Text.NoWrap
                               ? Text.AlignVCenter : Text.AlignTop
        }

        SafeDropShadow {
            anchors.fill: glowLabel

            safeSource: glowLabel
            horizontalOffset: 0
            verticalOffset: 0

            radius: glowText.glowRadius
            samples: glowText.glowSamples

            color: glowText.glowColor

            opacity: glowText.glowOpacity

            transparentBorder: true
        }
    }

    // ===== LOCAL VISUAL TYPE: MINI BUTTON =======================

    component MiniButton: Rectangle {
        id: miniButton

        property string label: ""

        property bool active: false
        property bool danger: false

        property color activeColor: Colors.orange

        property int labelPixelSize: 11

        signal triggered

        readonly property bool hovered: buttonMouse.containsMouse
        readonly property bool pressed: buttonMouse.pressed

        readonly property color normalStateColor: active ? activeColor : Colors.cyan

        readonly property color stateColor: {
            if (danger)
                return Colors.red;

            if (pressed)
                return Colors.magenta;

            if (hovered)
                return Colors.orange;

            return normalStateColor;
        }

        color: {
            if (danger && pressed)
                return Colors.red;

            if (danger)
                return Colors.dark;

            if (pressed)
                return Colors.magenta;

            if (hovered)
                return Colors.yellow;

            if (active)
                return Colors.yellow;

            return Colors.dark;
        }

        border.width: 1

        border.color: {
            if (danger && pressed)
                return Colors.black;

            if (danger && hovered)
                return Colors.red;

            if (active)
                return Colors.orange;

            return stateColor;
        }

        GohuText {
            id: miniButtonText

            anchors.centerIn: parent

            text: miniButton.label

            font.pixelSize: miniButton.labelPixelSize

            color: {
                if (miniButton.danger && miniButton.pressed)
                    return Colors.black;

                if (miniButton.danger && miniButton.hovered)
                    return Colors.red;

                if (miniButton.active)
                    return Colors.orange;

                if (miniButton.pressed)
                    return Colors.black;

                return miniButton.stateColor;
            }
        }

        SafeDropShadow {
            anchors.fill: miniButtonText

            safeSource: miniButtonText
            horizontalOffset: 0
            verticalOffset: 0

            radius: 10
            samples: 13

            color: miniButton.danger && (miniButton.hovered || miniButton.pressed) ? Colors.red : miniButton.stateColor

            opacity: miniButton.pressed ? 0.90 : miniButton.hovered ? 0.70 : 0.55

            transparentBorder: true
        }

        SafeDropShadow {
            anchors.fill: miniButton

            safeSource: miniButton
            horizontalOffset: 0
            verticalOffset: 0

            radius: 9
            samples: 13

            color: miniButton.danger && (miniButton.hovered || miniButton.pressed) ? Colors.red : miniButton.active ? Colors.orange : miniButton.stateColor

            opacity: miniButton.pressed ? 0.60 : miniButton.hovered ? 0.44 : miniButton.active ? 0.32 : 0.10

            z: -1

            transparentBorder: true
        }

        MouseArea {
            id: buttonMouse

            anchors.fill: parent

            hoverEnabled: true

            onClicked: {
                miniButton.triggered();
            }
        }
    }

    // ===== LOCAL VISUAL TYPE: FILTER BUTTON =====================

    component FilterButton: Rectangle {
        id: filterButton

        property string filterId: ""
        property string label: ""

        property color accentColor: Colors.cyan

        readonly property bool active: root.activeFilter === filterId

        readonly property bool hovered: filterMouse.containsMouse

        readonly property bool pressed: filterMouse.pressed

        height: root.filterButtonHeight

        color: active ? Colors.yellow : pressed ? Colors.magenta : Colors.dark

        border.width: 1

        border.color: active ? Colors.orange : pressed ? Colors.magenta : accentColor

        GohuText {
            id: filterLabel

            anchors.centerIn: parent

            text: filterButton.label

            font.pixelSize: 10

            color: filterButton.active ? Colors.orange : filterButton.pressed ? Colors.black : filterButton.accentColor
        }

        SafeDropShadow {
            anchors.fill: filterLabel

            safeSource: filterLabel
            horizontalOffset: 0
            verticalOffset: 0

            radius: filterButton.hovered || filterButton.active ? 12 : 8

            samples: 13

            color: filterButton.active ? Colors.orange : filterButton.pressed ? Colors.magenta : filterButton.accentColor

            opacity: filterButton.active ? 0.82 : filterButton.hovered ? 0.76 : 0.52

            transparentBorder: true
        }

        SafeDropShadow {
            anchors.fill: filterButton

            safeSource: filterButton
            horizontalOffset: 0
            verticalOffset: 0

            radius: 9
            samples: 13

            color: filterButton.active ? Colors.orange : filterButton.pressed ? Colors.magenta : filterButton.accentColor

            opacity: filterButton.active ? 0.52 : filterButton.hovered ? 0.40 : 0.14

            z: -1

            transparentBorder: true
        }

        MouseArea {
            id: filterMouse

            anchors.fill: parent

            hoverEnabled: true

            onClicked: {
                root.activeFilter = filterButton.filterId;
            }
        }
    }

    // ===== FUNCTIONS ============================================

    function open() {
        menuOpen = true;
        keyboardOwnershipRequested();
    }

    function close() {
        menuOpen = false;
    }

    function toggle() {
        menuOpen = !menuOpen;
        if (menuOpen)
            keyboardOwnershipRequested();
    }

    // ===== APP STATE HELPERS ====================================

    function appKeyFor(sourceId, source) {
        return NotificationsService.sourceKey(sourceId, source);
    }

    // ===== CLASSIFICATION =========================================
    //
    // Legacy sender group remains the presentation/color-tone choice.
    // Filters use independent origin/domain/severity facets below, so one
    // Apollo SYSTEM warning appears in Apollo, System and Warning without
    // duplicating or rewriting its history record.
    // A category like "important" or "reminder" is NOT an Apollo source.

    function isWarning(category, severity) {
        const c = String(category || "").trim().toLowerCase();
        const s = String(severity || "").trim().toLowerCase();
        return s === "warning" || s === "critical" || s === "emergency"
            || c === "warning" || c === "critical" || c === "emergency";
    }

    // Sender name and desktop entry are best-effort identities supplied by
    // the originating app. Do not look at private titles/message bodies to
    // guess classification. Browser-only notifications with no site metadata
    // correctly remain Apps.
    function isCommunicationSource(source, sourceId) {
        const sourceText = String(source || "").trim().toLowerCase();
        const sourceIdText = String(sourceId || "").trim().toLowerCase();
        const tokens = (sourceText + " " + sourceIdText).split(/[^a-z0-9]+/);
        const known = [
            "discord", "vesktop", "equibop", "session", "signal",
            "telegram", "telegramdesktop", "element", "matrix",
            "slack", "teams", "whatsapp", "thunderbird", "gmail",
            "outlook", "protonmail", "skype", "zoom", "mattermost",
            "mastodon", "bluesky", "youtube", "twitch", "reddit"
        ];

        if (sourceText === "proton mail" || sourceText === "proton-mail")
            return true;

        for (let i = 0; i < known.length; i++) {
            if (tokens.indexOf(known[i]) !== -1)
                return true;
        }

        return false;
    }

    function classificationFor(source, sourceId, category, severity) {
        const sourceText = String(source || "").trim().toLowerCase();
        const sourceIdText = String(sourceId || "").trim().toLowerCase();
        const categoryText = String(category || "").trim().toLowerCase();
        const categoryFamily = categoryText.split(".")[0];

        // External desktop notifications often have no category hint.
        // Named communication senders can still be recognized; other
        // browser/app events remain in Apps unless their hint says otherwise.
        let group = "apps";
        if (sourceText.indexOf("apollo") !== -1
                || sourceIdText.indexOf("apollo") !== -1
                || sourceText === "hospital" || sourceText === "git"
                || sourceText === "cpu++" || sourceText === "weather station"
                || sourceText === "appcontrol"
                || categoryText === "apollo" || categoryText === "internal") {
            group = "apollo";
        } else if (root.isCommunicationSource(source, sourceId)
                || categoryFamily === "email" || categoryFamily === "im"
                || categoryFamily === "call" || categoryFamily === "presence"
                || categoryText === "social" || categoryText === "friend"
                || categoryText === "friends" || categoryText === "message"
                || categoryText === "communication" || categoryText === "audio"
                || categoryText === "voice" || categoryText === "media"
                || categoryText === "fullscreen") {
            group = "social";
        } else if (categoryFamily === "device" || categoryFamily === "network"
                || categoryText === "system" || categoryText === "technical"
                || categoryText === "hardware" || categoryText === "resource"
                || categoryText === "telemetry") {
            group = "system";
        }

        // A critical message from Signal stays Social, but also appears in
        // the Warning view. Presentation color can reflect the urgency.
        const tone = root.isWarning(category, severity) ? "warning"
                   : group === "apollo" ? "apollo"
                   : group === "social" ? "social" : "system";
        return { group: group, tone: tone };
    }

    function baseColorForTone(tone) {
        if (tone === "warning")
            return Colors.red;

        if (tone === "apollo")
            return Colors.orange;

        if (tone === "social")
            return root.omnitrixGreen;

        return Colors.cyan;
    }

    // ===== SEARCH / FILTER ======================================

    // Latest receipt/update time, formatted in the local timezone.
    function eventTimestamp(createdAt, updatedAt) {
        const first = Number(createdAt || 0);
        const last = Number(updatedAt || 0);
        const time = last > first ? last : first;
        return time > 0 ? Qt.formatDateTime(new Date(time), "MM/dd/yy  h:mm AP") : "TIME UNKNOWN";
    }

    function scheduleFilteredModelRebuild() {
        filteredModelRefreshTimer.restart();
    }

    // Report identity comes from the stored event, not an inferred message
    // keyword. Existing solar records get the expanded layout after reload.
    function reportKindFor(entry) {
        const context = entry.context || {};
        const eventType = String(context.eventType || "");
        const sourceId = String(entry.sourceId || "").toLowerCase();
        if (eventType === "solar-daily-report" && sourceId === "weather-space")
            return "solar";
        if (eventType === "weather-daily-report" && sourceId === "weather-brief")
            return "weather";
        return "";
    }

    function reportNumber(value, digits, suffix) {
        if (value === null || value === undefined || value === "")
            return "UNAVAILABLE";
        const number = Number(value);
        if (!isFinite(number))
            return "UNAVAILABLE";
        return number.toFixed(digits) + String(suffix || "");
    }

    function reportObserved(raw) {
        const value = String(raw || "").trim();
        if (!value)
            return "TIME UNAVAILABLE";
        return value.replace("T", " ").replace(/Z$/, " UTC").slice(0, 24);
    }

    function reportDetailsFor(entry, kind) {
        const m = entry.metrics || {};
        const ctx = entry.context || {};
        if (kind === "solar") {
            const stamps = ctx.observationTimesUtc || {};
            return [
                "GEOMAGNETIC // Kp " + root.reportNumber(m.kp, 1, "")
                    + "  " + (Number(m.kp) >= 5 ? "STORM RANGE" : "OBSERVED"),
                "SOLAR WIND // " + root.reportNumber(m.solarWindKmS, 0, " km/s"),
                "MAGNETIC Bz // " + root.reportNumber(m.magneticBzNt, 1, " nT"),
                "MAGNETIC Bt // " + root.reportNumber(m.magneticBtNt, 1, " nT"),
                "RADIO FLUX F10.7 // " + root.reportNumber(m.solarFluxSfu, 0, " SFU"),
                "",
                "NOAA OBSERVATIONS // UTC",
                "Kp // " + root.reportObserved(stamps.kp),
                "WIND // " + root.reportObserved(stamps.solarWind),
                "FIELD // " + root.reportObserved(stamps.magneticField),
                "FLUX // " + root.reportObserved(stamps.solarFlux)
            ].join("\n");
        }
        if (kind === "weather") {
            const aqiAvailable = m.aqi !== null && m.aqi !== undefined
                                 && isFinite(Number(m.aqi));
            return [
                "CONDITIONS // " + String(m.condition || "UNKNOWN").toUpperCase(),
                "TEMPERATURE // " + root.reportNumber(m.temperatureF, 0, "°F"),
                "FEELS LIKE // " + root.reportNumber(m.feelsLikeF, 0, "°F"),
                "HUMIDITY // " + root.reportNumber(m.humidityPercent, 0, "%"),
                "WIND // " + (String(m.windDirection || "").toUpperCase())
                    + " " + root.reportNumber(m.windMph, 0, " mph"),
                "",
                "AIR QUALITY // " + (aqiAvailable
                    ? root.reportNumber(m.aqi, 0, "") + "  " + String(m.aqiLabel || "")
                    : "NOT AVAILABLE"),
                "PM2.5 // " + root.reportNumber(m.pm25, 1, " µg/m³"),
                "PM10 // " + root.reportNumber(m.pm10, 1, " µg/m³"),
                "",
                "WEATHER OBSERVED // " + root.reportObserved(ctx.observedAtUtc),
                "DATA // WTTR.IN / OPEN-METEO",
                "AQI // LAST AVAILABLE (SEPARATE)"
            ].join("\n");
        }
        return "";
    }

    function rebuildFilteredNotifications() {
        filteredNotifications.clear();

        if (root.activeFilter === "manager")
            return;

        // Sort presentation only; do not reorder or rewrite durable history.
        const rows = [];
        for (let i = 0; i < NotificationsService.notifications.count; i++) {
            const entry = NotificationsService.notifications.get(i);
            const classification = root.classificationFor(entry.source, entry.sourceId, entry.category, entry.severity);
            const facets = NotificationFacets.facetsFor(entry);
            const reportKind = root.reportKindFor(entry);
            if (!root.notificationMatches(entry.source, entry.sourceId, entry.title, entry.message, entry.category, entry.severity, classification.group, facets))
                continue;
            rows.push({
                ordinal: i,
                data: {
                    "notificationId": String(entry.id || ""),
                    "source": String(entry.source || ""),
                    "sourceId": String(entry.sourceId || ""),
                    "title": String(entry.title || ""),
                    "message": String(entry.message || ""),
                    "appIcon": String(entry.appIcon || ""),
                    "category": String(entry.category || "generic"),
                    "severity": String(entry.severity || "normal"),
                    "createdAt": Number(entry.createdAt || 0),
                    "updatedAt": Number(entry.updatedAt || 0),
                    "reportKind": reportKind,
                    "reportDetails": root.reportDetailsFor(entry, reportKind),
                    "updateKind": entry.sourceId === "apollo-update-monitor"
                                  ? String((entry.context || {}).updateKind || "") : "",
                    "updateToken": entry.sourceId === "apollo-update-monitor"
                                   ? String((entry.context || {}).updateToken || "") : ""
                }
            });
        }

        rows.sort(function(a, b) {
            const aTime = Math.max(a.data.updatedAt, a.data.createdAt);
            const bTime = Math.max(b.data.updatedAt, b.data.createdAt);
            return (bTime - aTime) || (b.ordinal - a.ordinal);
        });
        for (let j = 0; j < rows.length; j++)
            filteredNotifications.append(rows[j].data);
    }

    function rebuildManagerDndPolicies() {
        managerDndPolicies.clear();

        for (var i = 0; i < NotificationsService.sourcePolicies.count; i++) {
            var policy = NotificationsService.sourcePolicies.get(i);

            if (policy.dnd !== true)
                continue;

            managerDndPolicies.append({
                "appKey": String(policy.appKey || ""),
                "source": String(policy.source || ""),
                "sourceId": String(policy.sourceId || "")
            });
        }
    }

    function durationLabel(durationMs) {
        var milliseconds = Math.max(0, Number(durationMs || 0));
        var hour = 60 * 60 * 1000;
        var day = 24 * hour;

        if (milliseconds >= day && milliseconds % day === 0) {
            var days = Math.round(milliseconds / day);
            return days + (days === 1 ? " DAY" : " DAYS");
        }

        if (milliseconds >= hour && milliseconds % hour === 0) {
            var hours = Math.round(milliseconds / hour);
            return hours + (hours === 1 ? " HOUR" : " HOURS");
        }

        return Math.round(milliseconds / 60000) + " MIN";
    }

    function notificationMatches(source, sourceId, title, message, category, severity, filterGroup, facets) {
        // Warning is an overlapping severity view, not a source category.
        if (root.activeFilter === "warning") {
            if (!root.isWarning(category, severity))
                return false;
        } else if (root.activeFilter === "favorites") {
            if (!NotificationsService.isFavorite(root.appKeyFor(sourceId, source)))
                return false;
        } else if (root.activeFilter !== "all"
                   && !NotificationFacets.matches(root.activeFilter, facets, false)) {
            return false;
        }

        var query = String(root.searchQuery || "").trim().toLowerCase();

        if (query === "")
            return true;

        var haystack = [source, title, message, category, severity].join(" ").toLowerCase();

        return haystack.indexOf(query) !== -1;
    }

    // ===== ICON HELPER ==========================================

    function resolveAppIcon(appIcon, sourceId) {
        var icon = String(appIcon || "");

        if (icon === "")
            icon = String(sourceId || "");

        if (icon === "")
            return "";

        if (icon.indexOf("/") === 0 || icon.indexOf("file:") === 0 || icon.indexOf("image:") === 0 || icon.indexOf("data:") === 0)
            return icon;

        return Quickshell.iconPath(icon, true);
    }

    // ===== DISMISS ==============================================
    //
    // Dismiss is notification-specific.
    // Favorite / snooze / DND are app-wide.

    function dismissNotification(notificationId) {
        var eventId = String(notificationId || "");

        if (eventId === "")
            return;

        for (var historyIndex = NotificationsService.notifications.count - 1; historyIndex >= 0; historyIndex--) {
            var entry = NotificationsService.notifications.get(historyIndex);

            if (String(entry.id || "") === eventId) {
                NotificationsService.notifications.remove(historyIndex);
                break;
            }
        }

        for (var i = NotificationsService.activeNotifications.count - 1; i >= 0; i--) {
            var active = NotificationsService.activeNotifications.get(i);

            if (String(active.id || "") === eventId)
                NotificationsService.activeNotifications.remove(i);
        }

        NotificationsService.markNotificationsChanged();
        NotificationsService.scheduleHistorySave();
    }

    function requestClearAllForApp(appKey, source) {
        root.pendingClearAllKey = String(appKey || "");
        root.pendingClearAllSource = String(source || appKey || "");
    }

    function cancelClearAll() {
        root.pendingClearAllKey = "";
        root.pendingClearAllSource = "";
    }

    function confirmClearAll() {
        if (root.pendingClearAllKey === "")
            return;

        NotificationsService.clearNotificationsForSource(root.pendingClearAllKey);
        root.cancelClearAll();
    }

    // ===== APP NAVIGATION =======================================
    //
    // These actions are intentionally limited to:
    //   - focus an exact matching app_id / XWayland class
    //   - move that exact matching window to the current workspace
    //   - launch its desktop entry if no exact window match exists
    //
    // No kill/delete/privileged action lives here.

    function normalizedDesktopId(sourceId) {
        var id = String(sourceId || "").trim();

        if (id.endsWith(".desktop"))
            id = id.slice(0, -8);

        return id;
    }

    function takeMeToApp(sourceId, source) {
        var desktopId = root.normalizedDesktopId(sourceId);

        if (desktopId === "") {
            console.warn("Notification Hub: no desktop entry for TAKE ME TO:", source);
            return;
        }

        var script = 'id="$1"; ' + 'tree="$(swaymsg -t get_tree -r)"; ' + 'con="$(printf "%s" "$tree" | jq -r --arg id "$id" ' + '\'.. | objects ' + '| select(((.app_id? // "") | ascii_downcase) == ($id | ascii_downcase) ' + 'or (((.window_properties.class? // "") | ascii_downcase) == ($id | ascii_downcase))) ' + '| .id\' | head -n 1)"; ' + 'if [ -n "$con" ] && [ "$con" != "null" ]; then ' + '  swaymsg "[con_id=$con]" focus >/dev/null; ' + 'else ' + '  gtk-launch "$id" >/dev/null 2>&1 & ' + 'fi';

        Quickshell.execDetached(["bash", "-lc", script, "_", desktopId]);
    }

    function bringAppHere(sourceId, source) {
        var desktopId = root.normalizedDesktopId(sourceId);

        if (desktopId === "") {
            console.warn("Notification Hub: no desktop entry for BRING HERE:", source);
            return;
        }

        var script = 'id="$1"; ' + 'tree="$(swaymsg -t get_tree -r)"; ' + 'con="$(printf "%s" "$tree" | jq -r --arg id "$id" ' + '\'.. | objects ' + '| select(((.app_id? // "") | ascii_downcase) == ($id | ascii_downcase) ' + 'or (((.window_properties.class? // "") | ascii_downcase) == ($id | ascii_downcase))) ' + '| .id\' | head -n 1)"; ' + 'if [ -n "$con" ] && [ "$con" != "null" ]; then ' + '  ws="$(swaymsg -t get_workspaces -r ' + '| jq -r \'.[] | select(.focused == true) | .name\' | head -n 1)"; ' + '  if [ -n "$ws" ]; then ' + '    swaymsg "[con_id=$con]" move container to workspace "$ws" >/dev/null; ' + '    swaymsg "[con_id=$con]" focus >/dev/null; ' + '  fi; ' + 'else ' + '  gtk-launch "$id" >/dev/null 2>&1 & ' + 'fi';

        Quickshell.execDetached(["bash", "-lc", script, "_", desktopId]);
    }

    // ===== HUB CONTENT ==========================================
    //
    // This Item never gets destroyed when the menu closes.
    // It only becomes transparent.
    //
    // Heavy animations added later should bind their running/enabled
    // state to root.menuOpen so the persistent hidden window can sleep.

    Item {
        id: hubContent

        anchors.fill: parent

        opacity: root.menuOpen ? 1.0 : 0.0

        // ===== MAIN WINDOW PANEL ================================
        //
        // Notifications now uses the same reusable large-window chassis as the
        // other major menus. The close/wide spreads are intentionally bounded
        // by frameInset so the glow is fully rendered instead of being clipped
        // by the native PanelWindow edge.

        Rectangle {
            id: frameGlowSource

            anchors.fill: parent
            anchors.margins: root.frameInset

            color: "transparent"

            // This border is only the effect source. Making it thicker gives
            // the blur enough orange energy without changing the visible 2px
            // frame rendered by WindowPanelFrame below.
            border.width: 4
            border.color: Colors.orange
            z: -2
        }

        SafeDropShadow {
            anchors.fill: frameGlowSource
            safeSource: frameGlowSource
            horizontalOffset: 0
            verticalOffset: 0
            radius: root.frameCloseGlowRadius
            samples: root.frameCloseGlowSamples
            color: Colors.orange
            opacity: root.relationshipFocusModeActive
                     ? (root.relationshipFocused ? 0.70 : 0.10)
                     : root.frameCloseGlowOpacity
            z: -3
            transparentBorder: true
        }

        SafeDropShadow {
            anchors.fill: frameGlowSource
            safeSource: frameGlowSource
            horizontalOffset: 0
            verticalOffset: 0
            radius: root.frameWideGlowRadius
            samples: root.frameWideGlowSamples
            color: Colors.orange
            opacity: root.frameWideGlowOpacity
            z: -4
            transparentBorder: true
        }

        WindowPanelFrame {
            id: frame

            anchors.fill: parent
            anchors.margins: root.frameInset

            HoverHandler {
                enabled: root.menuOpen
                onHoveredChanged: {
                    if (hovered)
                        root.keyboardOwnershipRequested();
                }
            }

            fillColor: Colors.black
            fillOpacity: root.backgroundOpacity

            borderWidth: 2
            borderColor: Colors.orange

            // The Hub is translucent, so a full rectangular shadow would show
            // through the glass. Its glow comes from frameGlowSource instead.
            glowVisible: false

            // ===== HEADER =======================================

            Rectangle {
                id: header

                anchors {
                    top: parent.top
                    left: parent.left
                    right: parent.right
                }

                height: root.headerHeight

                color: "transparent"

                border.width: 1
                border.color: Colors.cyan

                // ===== TITLE ROW ================================

                GlowText {
                    anchors {
                        top: parent.top
                        left: parent.left
                    }

                    anchors.topMargin: 8
                    anchors.leftMargin: 18

                    width: 260
                    height: 30

                    text: "NOTIFICATION HUB"

                    pixelSize: root.hubTitleFontSize

                    textColor: Colors.magenta
                    glowColor: Colors.magenta
                }

                // Stored notification count:
                // > 0 = orange/orange
                // 0   = white/cyan
                GlowText {
                    id: storedCountNumber

                    anchors {
                        top: parent.top
                        right: storedLabel.left
                    }

                    anchors.topMargin: 8
                    anchors.rightMargin: 2

                    width: 36
                    height: 30

                    text: String(NotificationsService.notifications.count)

                    pixelSize: root.storedCountFontSize

                    horizontalAlignment: Text.AlignRight

                    textColor: NotificationsService.notifications.count === 0 ? Colors.white : Colors.orange

                    glowColor: NotificationsService.notifications.count === 0 ? Colors.cyan : Colors.orange

                    glowRadius: NotificationsService.notifications.count === 0 ? root.tightGlowRadius : root.textGlowRadius

                    glowSamples: NotificationsService.notifications.count === 0 ? root.tightGlowSamples : root.textGlowSamples
                }

                GlowText {
                    id: storedLabel

                    anchors {
                        top: parent.top
                        right: parent.right
                    }

                    anchors.topMargin: 8
                    anchors.rightMargin: 18

                    width: 56
                    height: 30

                    text: "STORED"

                    pixelSize: root.storedCountFontSize

                    textColor: Colors.cyan
                    glowColor: Colors.cyan
                }

                // ===== SEARCH ===================================

                Rectangle {
                    id: searchBox

                    anchors {
                        top: parent.top
                        left: parent.left
                        right: parent.right
                    }

                    anchors.topMargin: 45
                    anchors.leftMargin: 14
                    anchors.rightMargin: 14

                    height: root.searchHeight

                    color: Colors.dark

                    border.width: 1
                    border.color: searchInput.activeFocus ? Colors.orange : searchMouse.containsMouse ? Colors.cyan : Colors.cyan

                    SafeDropShadow {
                        anchors.fill: parent

                        safeSource: searchBox
                        horizontalOffset: 0
                        verticalOffset: 0

                        radius: searchInput.activeFocus ? 10 : 7

                        samples: 13

                        color: searchInput.activeFocus ? Colors.orange : Colors.cyan

                        opacity: searchInput.activeFocus ? 0.42 : searchMouse.containsMouse ? 0.30 : 0.14

                        z: -1

                        transparentBorder: true
                    }

                    GohuText {
                        anchors {
                            left: parent.left
                            verticalCenter: parent.verticalCenter
                        }

                        anchors.leftMargin: 10

                        text: "⌕"

                        font.pixelSize: 15

                        color: searchInput.activeFocus ? Colors.orange : Colors.cyan
                    }

                    TextInput {
                        id: searchInput

                        anchors {
                            top: parent.top
                            bottom: parent.bottom
                            left: parent.left
                            right: parent.right
                        }

                        anchors.leftMargin: 34
                        anchors.rightMargin: 10

                        text: root.searchQuery

                        font.family: "GohuFont 11 Nerd Font Mono"
                        font.pixelSize: 12

                        color: Colors.magenta

                        cursorDelegate: Rectangle {
                            width: 2
                            height: searchInput.cursorRectangle.height
                            color: Colors.orange
                        }

                        verticalAlignment: TextInput.AlignVCenter

                        selectByMouse: true

                        clip: true

                        Keys.onPressed: function(event) {
                            if (event.key === Qt.Key_Escape && root.menuOpen && root.keyboardActive) {
                                root.handleEscape();
                                event.accepted = true;
                            }
                        }
                        onTextChanged: {
                            if (root.searchQuery !== text)
                                root.searchQuery = text;
                        }
                    }

                    SafeDropShadow {
                        anchors.fill: searchInput

                        safeSource: searchInput
                        horizontalOffset: 0
                        verticalOffset: 0

                        radius: root.tightGlowRadius
                        samples: root.tightGlowSamples

                        color: Colors.magenta

                        opacity: 0.52

                        transparentBorder: true
                    }

                    GohuText {
                        anchors {
                            left: searchInput.left
                            verticalCenter: parent.verticalCenter
                        }

                        visible: searchInput.text.length === 0 && !searchInput.activeFocus

                        text: "SEARCH HISTORY..."

                        font.pixelSize: 11

                        color: Colors.cyan

                        opacity: 0.48
                    }

                    MouseArea {
                        id: searchMouse

                        anchors.fill: parent

                        hoverEnabled: true

                        acceptedButtons: Qt.NoButton

                        cursorShape: Qt.IBeamCursor
                    }
                }

                // ===== FILTER STRIP ==============================

                Row {
                    id: filterStrip

                    anchors {
                        top: searchBox.bottom
                        left: parent.left
                        right: parent.right
                    }

                    anchors.topMargin: 8
                    anchors.leftMargin: 14
                    anchors.rightMargin: 14

                    height: root.filterStripHeight

                    spacing: root.filterButtonSpacing

                    readonly property real buttonWidth: (width - (spacing * 7)) / 8

                    FilterButton {
                        width: filterStrip.buttonWidth
                        height: filterStrip.height
                        filterId: "all"
                        label: "COMBI"
                        accentColor: Colors.yellow
                    }

                    FilterButton {
                        width: filterStrip.buttonWidth
                        height: filterStrip.height
                        filterId: "favorites"
                        label: "FAVS"
                        accentColor: Colors.magenta
                    }

                    FilterButton {
                        width: filterStrip.buttonWidth
                        height: filterStrip.height
                        filterId: "apps"
                        label: "APPS"
                        accentColor: Colors.cyan
                    }

                    FilterButton {
                        width: filterStrip.buttonWidth
                        height: filterStrip.height
                        filterId: "social"
                        label: "SOCIAL"
                        accentColor: root.omnitrixGreen
                    }

                    FilterButton {
                        width: filterStrip.buttonWidth
                        height: filterStrip.height
                        filterId: "apollo"
                        label: "APOLLO"
                        accentColor: Colors.orange
                    }

                    FilterButton {
                        width: filterStrip.buttonWidth
                        height: filterStrip.height
                        filterId: "system"
                        label: "SYSTEM"
                        accentColor: Colors.white
                    }

                    FilterButton {
                        width: filterStrip.buttonWidth
                        height: filterStrip.height
                        filterId: "warning"
                        label: "WARNING"
                        accentColor: Colors.red
                    }

                    FilterButton {
                        width: filterStrip.buttonWidth
                        height: filterStrip.height
                        filterId: "manager"
                        label: "MANAGER"
                        accentColor: Colors.magenta
                    }
                }

                // New second header divider UNDER the filters.
                Rectangle {
                    id: headerLine

                    anchors {
                        bottom: parent.bottom
                        left: parent.left
                        right: parent.right
                    }

                    height: 1

                    color: Colors.cyan
                }

                SafeDropShadow {
                    anchors.fill: headerLine

                    safeSource: headerLine
                    horizontalOffset: 0
                    verticalOffset: 0

                    radius: 10
                    samples: 13

                    color: Colors.cyan

                    opacity: 0.60

                    transparentBorder: true
                }
            }

            // ===== CONTROL BAY ==================================
            //
            // Fixed physical bottom area.
            //
            // The ListView ends ABOVE this rectangle, so cards can never
            // scroll behind it.
            //
            // Same opacity as the main background, but Colors.dark gives
            // it a distinct control-deck surface.

            Rectangle {
                id: controlBay

                anchors {
                    bottom: parent.bottom
                    left: parent.left
                    right: parent.right
                }

                anchors.bottomMargin: root.controlBayBottomMargin
                anchors.leftMargin: root.controlBaySideMargin
                anchors.rightMargin: root.controlBaySideMargin

                height: root.controlBayHeight

                color: "transparent"

                border.width: 1
                border.color: Colors.cyan

                Rectangle {
                    anchors.fill: parent

                    color: Colors.dark

                    opacity: root.controlBayOpacity

                    z: -2
                }

                Rectangle {
                    id: controlBayTopLine

                    anchors {
                        top: parent.top
                        left: parent.left
                        right: parent.right
                    }

                    height: 1

                    color: Colors.cyan
                }

                SafeDropShadow {
                    anchors.fill: controlBayTopLine

                    safeSource: controlBayTopLine
                    horizontalOffset: 0
                    verticalOffset: 0

                    radius: 10
                    samples: 13

                    color: Colors.cyan

                    opacity: 0.60

                    transparentBorder: true
                }

                GlowText {
                    anchors {
                        top: parent.top
                        left: parent.left
                    }

                    anchors.topMargin: 14
                    anchors.leftMargin: 16

                    width: 180
                    height: 24

                    text: "CONTROL BAY"

                    pixelSize: 14

                    textColor: Colors.magenta
                    glowColor: Colors.magenta
                }

                GlowText {
                    anchors {
                        top: parent.top
                        right: parent.right
                    }

                    anchors.topMargin: 14
                    anchors.rightMargin: 16

                    width: 240
                    height: 24

                    text: "HISTORY: " + (NotificationsService.historyEnabled ? "ON" : "OFF") + "  //  " + NotificationsService.historyStatus.toUpperCase()

                    pixelSize: 10

                    textColor: Colors.cyan
                    glowColor: Colors.cyan

                    elideMode: Text.ElideRight
                }

                // Reserved structured deck for future sliders,
                // filters, routing controls, etc.
                Rectangle {
                    anchors {
                        top: parent.top
                        bottom: parent.bottom
                        left: parent.left
                        right: parent.right
                    }

                    anchors.topMargin: 48
                    anchors.bottomMargin: 12
                    anchors.leftMargin: 12
                    anchors.rightMargin: 12

                    color: "transparent"

                    border.width: 1
                    border.color: Colors.cyan

                    opacity: 0.18
                }
            }

            // ===== CLEAR-ALL CONFIRMATION ========================

            Item {
                id: clearAllConfirmOverlay

                anchors.fill: parent

                visible: root.pendingClearAllKey !== ""

                z: 100

                MouseArea {
                    anchors.fill: parent
                    acceptedButtons: Qt.AllButtons
                }

                Rectangle {
                    id: clearAllConfirmBox

                    anchors.centerIn: parent

                    width: Math.min(parent.width - 40, 360)
                    height: 152

                    color: Colors.dark

                    border.width: 2
                    border.color: Colors.red

                    SafeDropShadow {
                        anchors.fill: parent
                        safeSource: parent
                        horizontalOffset: 0
                        verticalOffset: 0
                        radius: 18
                        samples: 21
                        color: Colors.red
                        opacity: 0.62
                        z: -1
                        transparentBorder: true
                    }

                    GlowText {
                        anchors {
                            top: parent.top
                            left: parent.left
                            right: parent.right
                        }

                        anchors.topMargin: 18
                        anchors.leftMargin: 14
                        anchors.rightMargin: 14

                        height: 26

                        text: "CLEAR ALL NOTIFICATIONS?"
                        pixelSize: 15
                        textColor: Colors.red
                        glowColor: Colors.red
                        horizontalAlignment: Text.AlignHCenter
                    }

                    GohuText {
                        anchors {
                            top: parent.top
                            left: parent.left
                            right: parent.right
                        }

                        anchors.topMargin: 54
                        anchors.leftMargin: 18
                        anchors.rightMargin: 18

                        height: 22

                        text: root.pendingClearAllSource
                        font.pixelSize: 11
                        color: Colors.white
                        horizontalAlignment: Text.AlignHCenter
                        elide: Text.ElideRight
                    }

                    Row {
                        anchors {
                            bottom: parent.bottom
                            horizontalCenter: parent.horizontalCenter
                        }

                        anchors.bottomMargin: 18

                        spacing: 12

                        MiniButton {
                            width: 92
                            height: 32

                            label: "NO"
                            labelPixelSize: 11

                            onTriggered: {
                                root.cancelClearAll();
                            }
                        }

                        MiniButton {
                            width: 92
                            height: 32

                            label: "YES"
                            labelPixelSize: 11

                            danger: true

                            onTriggered: {
                                root.confirmClearAll();
                            }
                        }
                    }
                }
            }

            // ===== HISTORY AREA =================================
            //
            // There is always visible glass space between this viewport
            // and the fixed control bay.

            Item {
                id: historyArea

                anchors {
                    top: header.bottom
                    bottom: controlBay.top
                    left: parent.left
                    right: parent.right

                    topMargin: root.historyTopGap
                    bottomMargin: root.historyBottomGap
                    leftMargin: 10
                    rightMargin: 10
                }

                // ===== MANAGER ==================================

                Item {
                    id: managerPanel

                    anchors.fill: parent

                    visible: root.activeFilter === "manager"

                    Rectangle {
                        id: snoozeSettings

                        anchors {
                            top: parent.top
                            left: parent.left
                            right: parent.right
                        }

                        height: 122

                        color: "transparent"

                        border.width: 1
                        border.color: Colors.orange

                        Rectangle {
                            anchors.fill: parent
                            color: Colors.dark
                            opacity: 0.52
                            z: -1
                        }

                        GlowText {
                            anchors {
                                top: parent.top
                                left: parent.left
                            }

                            anchors.topMargin: 10
                            anchors.leftMargin: 12

                            width: 190
                            height: 22

                            text: "SNOOZE DURATION"
                            pixelSize: 13
                            textColor: Colors.orange
                            glowColor: Colors.orange
                        }

                        GlowText {
                            anchors {
                                top: parent.top
                                right: parent.right
                            }

                            anchors.topMargin: 10
                            anchors.rightMargin: 12

                            width: 210
                            height: 22

                            text: "DEFAULT: " + root.durationLabel(NotificationsService.defaultSnoozeDurationMs)
                            pixelSize: 11
                            textColor: Colors.cyan
                            glowColor: Colors.cyan
                            horizontalAlignment: Text.AlignRight
                        }

                        GohuText {
                            anchors {
                                top: parent.top
                                left: parent.left
                                right: parent.right
                            }

                            anchors.topMargin: 39
                            anchors.leftMargin: 12
                            anchors.rightMargin: 12

                            height: 18

                            text: "ZZ suppresses new popups from that source for this long."
                            font.pixelSize: 10
                            color: Colors.white
                            opacity: 0.78
                        }

                        Row {
                            anchors {
                                left: parent.left
                                right: parent.right
                                bottom: parent.bottom
                            }

                            anchors.leftMargin: 12
                            anchors.rightMargin: 12
                            anchors.bottomMargin: 12

                            height: 30
                            spacing: 6

                            readonly property real presetWidth: (width - spacing * 5) / 6

                            MiniButton {
                                width: parent.presetWidth
                                height: parent.height
                                label: "1H"
                                active: NotificationsService.defaultSnoozeDurationMs === 60 * 60 * 1000
                                onTriggered: NotificationsService.setDefaultSnoozeDurationMs(60 * 60 * 1000)
                            }

                            MiniButton {
                                width: parent.presetWidth
                                height: parent.height
                                label: "6H"
                                active: NotificationsService.defaultSnoozeDurationMs === 6 * 60 * 60 * 1000
                                onTriggered: NotificationsService.setDefaultSnoozeDurationMs(6 * 60 * 60 * 1000)
                            }

                            MiniButton {
                                width: parent.presetWidth
                                height: parent.height
                                label: "12H"
                                active: NotificationsService.defaultSnoozeDurationMs === 12 * 60 * 60 * 1000
                                onTriggered: NotificationsService.setDefaultSnoozeDurationMs(12 * 60 * 60 * 1000)
                            }

                            MiniButton {
                                width: parent.presetWidth
                                height: parent.height
                                label: "1D"
                                active: NotificationsService.defaultSnoozeDurationMs === 24 * 60 * 60 * 1000
                                onTriggered: NotificationsService.setDefaultSnoozeDurationMs(24 * 60 * 60 * 1000)
                            }

                            MiniButton {
                                width: parent.presetWidth
                                height: parent.height
                                label: "3D"
                                active: NotificationsService.defaultSnoozeDurationMs === 3 * 24 * 60 * 60 * 1000
                                onTriggered: NotificationsService.setDefaultSnoozeDurationMs(3 * 24 * 60 * 60 * 1000)
                            }

                            MiniButton {
                                width: parent.presetWidth
                                height: parent.height
                                label: "7D"
                                active: NotificationsService.defaultSnoozeDurationMs === 7 * 24 * 60 * 60 * 1000
                                onTriggered: NotificationsService.setDefaultSnoozeDurationMs(7 * 24 * 60 * 60 * 1000)
                            }
                        }
                    }

                    // Separate source-management sections. Left/Right selects
                    // the keyboard navigation list, but Enter never silently
                    // changes policy or removes a favorite.
                    Item {
                        id: managerSourceSections
                        anchors {
                            top: snoozeSettings.bottom
                            bottom: parent.bottom
                            left: parent.left
                            right: parent.right
                        }
                        anchors.topMargin: 14

                        Item {
                            id: dndManagerSection
                            anchors {
                                top: parent.top
                                left: parent.left
                                right: parent.right
                            }
                            height: Math.max(0, (parent.height - 14) / 2)

                            GlowText {
                                id: dndManagerTitle
                                anchors {
                                    top: parent.top
                                    left: parent.left
                                    right: parent.right
                                }
                                anchors.leftMargin: 4
                                anchors.rightMargin: 4
                                height: 24
                                text: "DO NOT DISTURB  //  " + managerDndPolicies.count
                                pixelSize: 13
                                textColor: Colors.magenta
                                glowColor: Colors.magenta
                                MouseArea {
                                    anchors.fill: parent
                                    onClicked: {
                                        root.managerSelectionSection = "dnd";
                                        root.listKeyboardSelectionActive = false;
                                    }
                                }
                            }

                            GohuText {
                                anchors {
                                    top: dndManagerTitle.bottom
                                    left: parent.left
                                    right: parent.right
                                }
                                anchors.topMargin: 2
                                anchors.leftMargin: 4
                                anchors.rightMargin: 4
                                height: 18
                                text: "Sources stay suppressed until explicitly ALLOWED."
                                font.pixelSize: 10
                                color: Colors.white
                                opacity: 0.72
                            }

                            ListView {
                                id: dndManagerList
                                anchors {
                                    top: dndManagerTitle.bottom
                                    bottom: parent.bottom
                                    left: parent.left
                                    right: parent.right
                                }
                                anchors.topMargin: 28
                                clip: true
                                spacing: 8
                                boundsBehavior: Flickable.StopAtBounds
                                model: managerDndPolicies

                                delegate: Rectangle {
                                    id: dndRule
                                    required property string appKey
                                    required property string source
                                    required property string sourceId
                                    width: dndManagerList.width
                                    height: 64
                                    color: "transparent"
                                    border.width: root.listKeyboardSelectionActive
                                        && root.managerSelectionSection === "dnd" && ListView.isCurrentItem ? 2 : 1
                                    border.color: root.listKeyboardSelectionActive
                                        && root.managerSelectionSection === "dnd" && ListView.isCurrentItem
                                        ? Colors.orange : Colors.magenta

                                    Rectangle {
                                        anchors.fill: parent
                                        color: Colors.dark
                                        opacity: 0.52
                                        z: -1
                                    }
                                    GlowText {
                                        anchors {
                                            top: parent.top
                                            left: parent.left
                                            right: allowDndButton.left
                                        }
                                        anchors.topMargin: 9
                                        anchors.leftMargin: 12
                                        anchors.rightMargin: 10
                                        height: 20
                                        text: dndRule.source !== "" ? dndRule.source : dndRule.appKey
                                        pixelSize: 13
                                        textColor: Colors.magenta
                                        glowColor: Colors.magenta
                                        elideMode: Text.ElideRight
                                    }
                                    GohuText {
                                        anchors {
                                            bottom: parent.bottom
                                            left: parent.left
                                            right: allowDndButton.left
                                        }
                                        anchors.bottomMargin: 9
                                        anchors.leftMargin: 12
                                        anchors.rightMargin: 10
                                        height: 16
                                        text: dndRule.sourceId !== "" ? dndRule.sourceId : dndRule.appKey
                                        font.pixelSize: 9
                                        color: Colors.cyan
                                        elide: Text.ElideRight
                                    }
                                    MiniButton {
                                        id: allowDndButton
                                        anchors {
                                            verticalCenter: parent.verticalCenter
                                            right: parent.right
                                        }
                                        anchors.rightMargin: 10
                                        width: 72
                                        height: 30
                                        label: "ALLOW"
                                        labelPixelSize: 10
                                        active: false
                                        onTriggered: {
                                            NotificationsService.setDnd(dndRule.appKey, dndRule.sourceId, dndRule.source, false);
                                        }
                                    }
                                }
                            }
                            NeonScrollBar {
                                flickable: dndManagerList
                                handleStyle: "star"
                                // The shared star's drop shadow must extend
                                // beyond the 16px track, not be clipped to it.
                                containGlow: false
                                handleGlowEnabled: true
                                handleGlowStyle: "drop"
                                handleDropGlowRadius: 12
                                handleDropGlowSamples: 17
                                handleDropGlowIdleOpacity: 0.78
                                handleDropGlowHoverOpacity: 0.95
                                y: dndManagerList.y
                                x: parent.width - width
                                height: dndManagerList.height
                                visible: dndManagerList.visible && scrollable
                            }
                            GlowText {
                                anchors.centerIn: dndManagerList
                                visible: managerDndPolicies.count === 0
                                width: dndManagerList.width - 40
                                height: 30
                                text: "NO SOURCES ON DND"
                                pixelSize: 12
                                textColor: Colors.cyan
                                glowColor: Colors.cyan
                                horizontalAlignment: Text.AlignHCenter
                            }
                        }

                        Item {
                            id: favoriteManagerSection
                            anchors {
                                top: dndManagerSection.bottom
                                bottom: parent.bottom
                                left: parent.left
                                right: parent.right
                            }
                            anchors.topMargin: 14

                            GlowText {
                                id: favoriteManagerTitle
                                anchors {
                                    top: parent.top
                                    left: parent.left
                                    right: parent.right
                                }
                                anchors.leftMargin: 4
                                anchors.rightMargin: 4
                                height: 24
                                text: "FAVORITES  //  " + NotificationsService.favoriteSources.count
                                pixelSize: 13
                                textColor: Colors.magenta
                                glowColor: Colors.magenta
                                MouseArea {
                                    anchors.fill: parent
                                    onClicked: {
                                        root.managerSelectionSection = "favorites";
                                        root.listKeyboardSelectionActive = false;
                                    }
                                }
                            }
                            GohuText {
                                anchors {
                                    top: favoriteManagerTitle.bottom
                                    left: parent.left
                                    right: parent.right
                                }
                                anchors.topMargin: 2
                                anchors.leftMargin: 4
                                anchors.rightMargin: 4
                                height: 18
                                text: "UNFAV removes the star, not saved notifications."
                                font.pixelSize: 10
                                color: Colors.white
                                opacity: 0.72
                            }
                            ListView {
                                id: favoriteManagerList
                                anchors {
                                    top: favoriteManagerTitle.bottom
                                    bottom: parent.bottom
                                    left: parent.left
                                    right: parent.right
                                }
                                anchors.topMargin: 28
                                clip: true
                                spacing: 8
                                boundsBehavior: Flickable.StopAtBounds
                                model: NotificationsService.favoriteSources
                                delegate: Rectangle {
                                    id: favoriteRule
                                    required property string appKey
                                    required property string source
                                    required property string sourceId
                                    width: favoriteManagerList.width
                                    height: 64
                                    color: "transparent"
                                    border.width: root.listKeyboardSelectionActive
                                        && root.managerSelectionSection === "favorites" && ListView.isCurrentItem ? 2 : 1
                                    border.color: root.listKeyboardSelectionActive
                                        && root.managerSelectionSection === "favorites" && ListView.isCurrentItem
                                        ? Colors.orange : Colors.magenta
                                    Rectangle {
                                        anchors.fill: parent
                                        color: Colors.dark
                                        opacity: 0.52
                                        z: -1
                                    }
                                    GlowText {
                                        anchors {
                                            top: parent.top
                                            left: parent.left
                                            right: removeFavoriteButton.left
                                        }
                                        anchors.topMargin: 9
                                        anchors.leftMargin: 12
                                        anchors.rightMargin: 10
                                        height: 20
                                        text: "✦  " + (favoriteRule.source !== "" ? favoriteRule.source : favoriteRule.appKey)
                                        pixelSize: 13
                                        textColor: Colors.magenta
                                        glowColor: Colors.magenta
                                        elideMode: Text.ElideRight
                                    }
                                    GohuText {
                                        anchors {
                                            bottom: parent.bottom
                                            left: parent.left
                                            right: removeFavoriteButton.left
                                        }
                                        anchors.bottomMargin: 9
                                        anchors.leftMargin: 12
                                        anchors.rightMargin: 10
                                        height: 16
                                        text: favoriteRule.sourceId !== "" ? favoriteRule.sourceId : favoriteRule.appKey
                                        font.pixelSize: 9
                                        color: Colors.cyan
                                        elide: Text.ElideRight
                                    }
                                    MiniButton {
                                        id: removeFavoriteButton
                                        anchors {
                                            verticalCenter: parent.verticalCenter
                                            right: parent.right
                                        }
                                        anchors.rightMargin: 10
                                        width: 72
                                        height: 30
                                        label: "UNFAV"
                                        labelPixelSize: 10
                                        active: true
                                        activeColor: Colors.magenta
                                        onTriggered: {
                                            NotificationsService.setFavorite(favoriteRule.appKey, favoriteRule.sourceId, favoriteRule.source, false);
                                        }
                                    }
                                }
                            }
                            NeonScrollBar {
                                flickable: favoriteManagerList
                                handleStyle: "star"
                                containGlow: false
                                handleGlowEnabled: true
                                handleGlowStyle: "drop"
                                handleDropGlowRadius: 12
                                handleDropGlowSamples: 17
                                handleDropGlowIdleOpacity: 0.78
                                handleDropGlowHoverOpacity: 0.95
                                y: favoriteManagerList.y
                                x: parent.width - width
                                height: favoriteManagerList.height
                                visible: favoriteManagerList.visible && scrollable
                            }
                            GlowText {
                                anchors.centerIn: favoriteManagerList
                                visible: NotificationsService.favoriteSources.count === 0
                                width: favoriteManagerList.width - 40
                                height: 30
                                text: "NO FAVORITE SOURCES"
                                pixelSize: 12
                                textColor: Colors.cyan
                                glowColor: Colors.cyan
                                horizontalAlignment: Text.AlignHCenter
                            }
                        }
                    }
                }

                // ===== LIST =====================================

                ListView {
                    id: historyList

                    visible: root.activeFilter !== "manager"

                    anchors {
                        top: parent.top
                        bottom: parent.bottom
                        left: parent.left
                        right: scrollBarArea.left
                    }

                    spacing: 0

                    clip: true

                    boundsBehavior: Flickable.StopAtBounds

                    model: filteredNotifications

                    reuseItems: true

                    header: Item {
                        width: 1
                        height: 12
                    }

                    footer: Item {
                        width: 1
                        height: 12
                    }

                    delegate: Item {
                        id: notificationEntry

                        required property int index
                        required property string notificationId
                        required property string source
                        required property string sourceId
                        required property string title
                        required property string message
                        required property string appIcon
                        required property string category
                        required property string severity
                        required property double createdAt
                        required property double updatedAt
                        required property string reportKind
                        required property string reportDetails
                        required property string updateKind
                        required property string updateToken
                        readonly property bool isReport: reportKind !== ""
                        readonly property bool isUpdateOffer:
                            root.updatesController !== null
                            && root.updatesController.isCurrent(updateKind, updateToken)

                        readonly property string appKey: root.appKeyFor(notificationEntry.sourceId, notificationEntry.source)

                        readonly property bool favorite: NotificationsService.favoritesRevision >= 0 && NotificationsService.isFavorite(notificationEntry.appKey)

                        readonly property bool snoozed: NotificationsService.policyRevision >= 0 && NotificationsService.isSnoozed(notificationEntry.appKey)
                        readonly property bool dnd: NotificationsService.policyRevision >= 0 && NotificationsService.isDnd(notificationEntry.appKey)

                        readonly property var classification: root.classificationFor(notificationEntry.source, notificationEntry.sourceId, notificationEntry.category, notificationEntry.severity)

                        readonly property string filterGroup: notificationEntry.classification.group

                        readonly property string baseTone: notificationEntry.classification.tone

                        readonly property color baseColor: root.baseColorForTone(notificationEntry.baseTone)

                        // Favorite is a VISUAL OVERRIDE, not a base category.
                        readonly property color notificationColor: notificationEntry.favorite ? Colors.magenta : notificationEntry.baseColor

                        readonly property color sourceColor: notificationEntry.favorite ? Colors.magenta : notificationEntry.baseColor

                        readonly property url resolvedAppIcon: root.resolveAppIcon(notificationEntry.appIcon, notificationEntry.sourceId)

                        // Only multiline ordinary notifications grow; the
                        // 116px one-line cards and report deck retain baseline.
                        readonly property real compactCardHeight: Math.max(
                            root.cardHeight,
                            notificationMessage.y + notificationMessage.height
                            + root.cardContentMargin + 4
                            + (notificationEntry.isUpdateOffer ? 32 : 0)
                        )
                        readonly property real extendedReportCardHeight: Math.max(
                            root.reportCardHeight,
                            reportText.y + reportText.contentHeight
                            + root.cardContentMargin + 2
                        )

                        width: historyList.width
                        height:
                            (notificationEntry.isReport ? notificationEntry.extendedReportCardHeight
                                                        : notificationEntry.compactCardHeight)
                            + (root.cardGlowVerticalGutter * 2)
                            + root.cardSpacing

                        // ===== CARD + RESERVED GLOW GUTTER =======

                        WindowPanelFrame {
                            id: card

                            anchors {
                                top: parent.top
                                left: parent.left
                                right: parent.right

                                topMargin: root.cardGlowVerticalGutter
                                leftMargin: root.cardGlowGutter
                                rightMargin: root.cardGlowGutter
                            }

                            height: notificationEntry.isReport ? notificationEntry.extendedReportCardHeight
                                                               : notificationEntry.compactCardHeight

                            fillColor: Colors.black
                            fillOpacity: root.cardFillOpacity

                            borderWidth: 1
                            borderColor: notificationEntry.notificationColor

                            // A separate orange outline shows where arrows
                            // will act without overriding the card's own tone.
                            Rectangle {
                                anchors.fill: parent
                                color: "transparent"
                                border.width: 2
                                border.color: Colors.orange
                                z: 40
                                visible: root.listKeyboardSelectionActive
                                         && historyList.currentIndex === notificationEntry.index
                            }

                            glowColor: notificationEntry.notificationColor
                            closeGlowSpread: root.cardCloseGlowSpread
                            closeGlowOpacity: root.cardCloseGlowOpacity
                            wideGlowSpread: root.cardWideGlowSpread
                            wideGlowOpacity: root.cardWideGlowOpacity

                            // Clicking the card means TAKE ME TO the app.
                            MouseArea {
                                id: cardClickArea

                                anchors.fill: parent

                                hoverEnabled: true
                                enabled: !notificationEntry.isReport
                                         && !notificationEntry.isUpdateOffer

                                z: 0

                                onClicked: {
                                    root.takeMeToApp(notificationEntry.sourceId, notificationEntry.source);
                                }
                            }

                            // Small internal accent rail.
                            Rectangle {
                                id: accentRail

                                anchors {
                                    top: parent.top
                                    bottom: parent.bottom
                                    left: parent.left

                                    topMargin: 8
                                    bottomMargin: 8
                                    leftMargin: 6
                                }

                                width: 2

                                color: notificationEntry.notificationColor

                                z: 1
                            }

                            SafeDropShadow {
                                anchors.fill: accentRail

                                safeSource: accentRail
                                horizontalOffset: 0
                                verticalOffset: 0

                                radius: 8
                                samples: 11

                                color: notificationEntry.notificationColor

                                opacity: 0.48

                                transparentBorder: true
                            }

                            // ===== FAVORITE ======================

                            MiniButton {
                                id: favoriteButton

                                anchors {
                                    top: parent.top
                                    left: parent.left
                                }

                                anchors.topMargin: root.cardContentMargin
                                anchors.leftMargin: root.cardContentMargin + 6

                                width: 28
                                height: 28

                                z: 2

                                active: notificationEntry.favorite

                                activeColor: Colors.magenta

                                label: active ? "✦" : "✧"

                                labelPixelSize: 17

                                onTriggered: {
                                    NotificationsService.toggleFavorite(notificationEntry.appKey, notificationEntry.sourceId, notificationEntry.source);
                                }
                            }

                            // ===== APP ICON ======================

                            Rectangle {
                                id: appIconBox

                                anchors {
                                    top: parent.top
                                    left: favoriteButton.right
                                }

                                anchors.topMargin: root.cardContentMargin
                                anchors.leftMargin: 7

                                width: root.appIconSize
                                height: root.appIconSize

                                z: 1

                                color: Colors.dark

                                border.width: 1
                                border.color: notificationEntry.sourceColor

                                Image {
                                    id: appIconImage

                                    anchors.fill: parent
                                    anchors.margins: root.appIconInnerMargin

                                    source: notificationEntry.resolvedAppIcon

                                    fillMode: Image.PreserveAspectFit

                                    asynchronous: true
                                }

                                // ONE icon only:
                                // real app icon when available,
                                // fallback glyph otherwise.
                                GohuText {
                                    anchors.centerIn: parent

                                    visible: appIconImage.status !== Image.Ready

                                    text: "-⋆♱⋆-"

                                    font.pixelSize: 9

                                    color: notificationEntry.sourceColor
                                }
                            }

                            // ===== RECEIVED / UPDATED TIME =====
                            // Right of the app icon and above the source.
                            GlowText {
                                id: receivedTimestamp
                                anchors {
                                    top: appIconBox.top
                                    left: appIconBox.right
                                    right: appControls.left
                                }
                                anchors.topMargin: -1
                                anchors.leftMargin: 9
                                anchors.rightMargin: 9
                                height: 12
                                z: 1
                                text: root.eventTimestamp(notificationEntry.createdAt, notificationEntry.updatedAt)
                                pixelSize: 9
                                textColor: Colors.white
                                glowColor: Colors.cyan
                                glowRadius: root.tightGlowRadius
                                glowSamples: root.tightGlowSamples
                                elideMode: Text.ElideRight
                            }

                            // ===== APP NAME ======================

                            GlowText {
                                id: appName
                                anchors {
                                    top: receivedTimestamp.bottom
                                    left: appIconBox.right
                                    right: appControls.left
                                }
                                anchors.topMargin: 1
                                anchors.leftMargin: 9
                                anchors.rightMargin: 9
                                height: 16
                                z: 1
                                text: notificationEntry.source
                                pixelSize: root.appNameFontSize
                                textColor: notificationEntry.sourceColor
                                glowColor: notificationEntry.sourceColor
                                elideMode: Text.ElideRight
                            }

                            // ===== CATEGORY / GROUP ==============

                            GlowText {
                                anchors {
                                    top: appName.bottom
                                    left: appIconBox.right
                                    right: appControls.left
                                }

                                anchors.leftMargin: 9
                                anchors.rightMargin: 9

                                height: 13

                                z: 1

                                text: notificationEntry.filterGroup.toUpperCase() + "  //  " + notificationEntry.severity.toUpperCase()

                                pixelSize: root.notificationMetaFontSize

                                textColor: notificationEntry.notificationColor
                                glowColor: notificationEntry.notificationColor

                                elideMode: Text.ElideRight
                            }

                            // ===== APP-WIDE / CARD CONTROLS ======
                            //
                            // ZZ + DND are app-wide.
                            // X dismisses only this notification.

                            Row {
                                id: appControls

                                anchors {
                                    top: parent.top
                                    right: parent.right
                                }

                                anchors.topMargin: root.cardContentMargin
                                anchors.rightMargin: root.cardContentMargin

                                spacing: 5

                                z: 3

                                MiniButton {
                                    width: 32
                                    height: 28

                                    label: "ZZ"

                                    active: notificationEntry.snoozed

                                    activeColor: Colors.orange

                                    onTriggered: {
                                        if (notificationEntry.snoozed)
                                            NotificationsService.clearSnooze(notificationEntry.appKey);
                                        else
                                            NotificationsService.snoozeApp(notificationEntry.appKey, notificationEntry.sourceId, notificationEntry.source);
                                    }
                                }

                                MiniButton {
                                    width: 38
                                    height: 28

                                    label: "DND"

                                    labelPixelSize: 9

                                    active: notificationEntry.dnd

                                    activeColor: Colors.orange

                                    onTriggered: {
                                        NotificationsService.toggleDnd(notificationEntry.appKey, notificationEntry.sourceId, notificationEntry.source);
                                    }
                                }

                                MiniButton {
                                    width: 60
                                    height: 28

                                    label: "CLEAR ALL"

                                    labelPixelSize: 9

                                    active: false
                                    danger: true

                                    onTriggered: {
                                        root.requestClearAllForApp(notificationEntry.appKey, notificationEntry.source);
                                    }
                                }

                                MiniButton {
                                    width: 28
                                    height: 28

                                    label: "×"

                                    labelPixelSize: 17

                                    active: false
                                    danger: true

                                    onTriggered: {
                                        root.dismissNotification(notificationEntry.notificationId);
                                    }
                                }
                            }

                            // ===== NOTIFICATION TITLE ============

                            GlowText {
                                id: notificationTitle

                                anchors {
                                    top: appIconBox.bottom
                                    left: parent.left
                                    right: parent.right
                                }

                                anchors.topMargin: 7
                                anchors.leftMargin: root.cardContentMargin + 8
                                anchors.rightMargin: root.cardContentMargin

                                height: 20

                                z: 1

                                text: notificationEntry.title

                                pixelSize: root.notificationTitleFontSize

                                textColor: notificationEntry.notificationColor
                                glowColor: notificationEntry.notificationColor

                                elideMode: Text.ElideRight
                            }

                            // ===== MESSAGE =======================

                            GlowText {
                                id: notificationMessage

                                anchors {
                                    top: notificationTitle.bottom
                                    left: parent.left
                                    right: bringHereButton.left
                                }

                                anchors.topMargin: 2
                                anchors.leftMargin: root.cardContentMargin + 8
                                anchors.rightMargin: 8

                                height: Math.max(19, Math.ceil(fullTextHeight))

                                z: 1

                                text: notificationEntry.message
                                visible: !notificationEntry.isReport

                                pixelSize: root.notificationMessageFontSize

                                textColor: Colors.white

                                // White text always glows cyan, but tightly.
                                glowColor: Colors.cyan
                                glowRadius: root.tightGlowRadius
                                glowSamples: root.tightGlowSamples

                                wrapMode: Text.Wrap
                                elideMode: Text.ElideNone
                            }


                            // ===== UPDATES // EXPLICIT DECISIONS ======
                            // These actions are available only for a current
                            // matching offer from the private update monitor;
                            // persisted history and external notifications
                            // cannot execute a stale update.
                            Row {
                                id: updateOfferActions
                                visible: notificationEntry.isUpdateOffer
                                anchors {
                                    left: parent.left
                                    bottom: parent.bottom
                                }
                                anchors.leftMargin: root.cardContentMargin + 8
                                anchors.bottomMargin: 8
                                spacing: 8
                                z: 3

                                MiniButton {
                                    width: 86
                                    height: 26
                                    label: "REVIEW"
                                    active: false
                                    onTriggered: {
                                        root.updatesController.review(
                                            notificationEntry.updateKind,
                                            notificationEntry.updateToken);
                                    }
                                }
                                MiniButton {
                                    width: 86
                                    height: 26
                                    label: "NOT NOW"
                                    active: false
                                    onTriggered: {
                                        root.updatesController.defer(
                                            notificationEntry.updateKind,
                                            notificationEntry.updateToken);
                                    }
                                }
                            }

                            // ===== MULTILINE REPORT DECK ===========
                            // Short app messages stay compact; longer history
                            // messages and report decks expand to fit their text.
                            Rectangle {
                                id: reportDivider
                                visible: notificationEntry.isReport
                                anchors {
                                    top: notificationTitle.bottom
                                    left: parent.left
                                    right: parent.right
                                }
                                anchors.topMargin: 7
                                anchors.leftMargin: root.cardContentMargin + 8
                                anchors.rightMargin: root.cardContentMargin + 8
                                height: 1
                                color: notificationEntry.notificationColor
                                opacity: 0.48
                            }

                            GohuText {
                                id: reportText
                                visible: notificationEntry.isReport
                                anchors {
                                    top: reportDivider.bottom
                                    bottom: parent.bottom
                                    left: parent.left
                                    right: parent.right
                                }
                                anchors.topMargin: 8
                                anchors.bottomMargin: 12
                                anchors.leftMargin: root.cardContentMargin + 8
                                anchors.rightMargin: root.cardContentMargin + 8
                                text: notificationEntry.reportDetails
                                font.pixelSize: 11
                                lineHeight: 1.25
                                color: Colors.white
                                wrapMode: Text.Wrap
                                elide: Text.ElideNone
                                verticalAlignment: Text.AlignTop
                                z: 1
                            }
                            // ===== BRING HERE / OPEN =============
                            //
                            // Card click:
                            //     TAKE ME TO APP
                            //
                            // This button:
                            //     BRING APP HERE / OPEN HERE

                            MiniButton {
                                id: bringHereButton
                                visible: !notificationEntry.isReport
                                         && !notificationEntry.isUpdateOffer

                                anchors {
                                    bottom: parent.bottom
                                    right: parent.right
                                }

                                anchors.bottomMargin: 8
                                anchors.rightMargin: root.cardContentMargin

                                width: 30
                                height: 24

                                z: 3

                                label: "⇲"

                                labelPixelSize: 15

                                active: false

                                onTriggered: {
                                    root.bringAppHere(notificationEntry.sourceId, notificationEntry.source);
                                }
                            }
                        }
                    }
                }

                // ===== CUSTOM SCROLL BAR ========================

                NeonScrollBar {
                    id: scrollBarArea

                    flickable: historyList
                    handleStyle: "star"
                    // Reuse NeonScrollBar's star Canvas and SafeDropShadow;
                    // allowing the halo outside its narrow track is essential.
                    containGlow: false
                    starAreaWidth: root.scrollBarAreaWidth
                    starHandleSize: 14

                    x: parent.width - width
                    y: 0
                    height: parent.height
                    z: 0

                    barAreaWidth: root.scrollBarAreaWidth
                    railWidth: root.scrollTrackWidth
                    barHandleWidth: root.scrollThumbWidth
                    minimumHandleHeight: root.scrollThumbMinHeight

                    railColor: Colors.cyan
                    railOpacity: 0.52
                    railRadius: 0
                    railGlowEnabled: true
                    railGlowOpacity: 0.18

                    handleColor: Colors.magenta
                    barHandleRadius: 0
                    handleBorderWidth: 0
                    handleGlowEnabled: true
                    handleGlowStyle: "drop"
                    handleDropGlowRadius: 12
                    handleDropGlowSamples: 17
                    handleDropGlowIdleOpacity: 0.78
                    handleDropGlowHoverOpacity: 0.95

                    wheelEnabled: false
                    pointerCursorShape: Qt.ArrowCursor

                    visible:
                        root.activeFilter !== "manager"
                        && scrollable
                }
            }
        }
    }
}
