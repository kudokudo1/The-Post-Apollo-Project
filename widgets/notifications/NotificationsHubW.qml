import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.components
import qs.services.notifications
import QtQuick.Effects
import Qt5Compat.GraphicalEffects

PanelWindow {
    id: root

    property bool menuOpen: false

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
    property int notificationMessageFontSize: 12
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
    }

    onActiveFilterChanged: {
        root.scheduleFilteredModelRebuild();
    }

    onSearchQueryChanged: {
        root.scheduleFilteredModelRebuild();
    }

    Component.onCompleted: {
        root.scheduleFilteredModelRebuild();
        root.rebuildManagerDndPolicies();
    }

    // ===== APP-WIDE CARD STATE ==================================
    //
    // Favorite remains a lightweight visual frontend state.
    // Snooze and DND are persistent backend policy in NotificationsService.

    property var appStates: ({})

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
        property int horizontalAlignment: Text.AlignLeft

        GohuText {
            id: glowLabel

            anchors.fill: parent

            text: glowText.text

            font.pixelSize: glowText.pixelSize

            color: glowText.textColor

            elide: glowText.elideMode

            horizontalAlignment: glowText.horizontalAlignment
            verticalAlignment: Text.AlignVCenter
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
    }

    function close() {
        menuOpen = false;
    }

    function toggle() {
        menuOpen = !menuOpen;
    }

    // ===== APP STATE HELPERS ====================================

    function appKeyFor(sourceId, source) {
        return NotificationsService.sourceKey(sourceId, source);
    }

    function stateForApp(appKey) {
        var current = root.appStates[appKey];

        if (current !== undefined)
            return current;

        return {
            favorite: false
        };
    }

    function setAppFlag(appKey, flagName, enabled) {
        var nextStates = ({});

        for (var existingKey in root.appStates)
            nextStates[existingKey] = root.appStates[existingKey];

        var current = root.stateForApp(appKey);

        var nextState = {
            favorite: current.favorite === true
        };

        nextState[flagName] = enabled === true;

        nextStates[appKey] = nextState;

        // Replace the WHOLE object so all cards from this app receive
        // the state update at the same time.
        root.appStates = nextStates;
    }

    function toggleAppFlag(appKey, flagName) {
        var current = root.stateForApp(appKey);

        root.setAppFlag(appKey, flagName, current[flagName] !== true);
    }

    // ===== CLEAN NOTIFICATION CLASSIFICATION ====================
    //
    // filterGroup is mutually exclusive:
    //
    // warning
    // apollo
    // social
    // system
    // apps
    //
    // The visual tone is derived from that group:
    //
    // warning -> red
    // apollo  -> orange
    // social  -> Omnitrix green
    // system  -> cyan
    // apps    -> cyan
    //
    // Favorite is NOT another base category.
    // Favorite is a magenta visual override.

    function classificationFor(source, sourceId, category, severity) {
        var sourceText = String(source || "").trim().toLowerCase();
        var sourceIdText = String(sourceId || "").trim().toLowerCase();
        var categoryText = String(category || "").trim().toLowerCase();
        var severityText = String(severity || "").trim().toLowerCase();

        // Warning / caution always wins.
        if (severityText === "warning" || severityText === "critical" || severityText === "emergency" || categoryText === "warning" || categoryText === "critical" || categoryText === "emergency") {
            return {
                group: "warning",
                tone: "warning"
            };
        }

        // Apollo itself speaking to the operator.
        if (sourceText.indexOf("apollo") !== -1 || sourceIdText.indexOf("apollo") !== -1 || categoryText === "apollo" || categoryText === "internal" || categoryText === "reminder" || categoryText === "important" || severityText === "important" || severityText === "reminder") {
            return {
                group: "apollo",
                tone: "apollo"
            };
        }

        // Social / voice / audio / media / fullscreen.
        if (categoryText === "social" || categoryText === "friend" || categoryText === "friends" || categoryText === "message" || categoryText === "communication" || categoryText === "audio" || categoryText === "voice" || categoryText === "media" || categoryText === "fullscreen") {
            return {
                group: "social",
                tone: "social"
            };
        }

        // Explicit technical/system classifications.
        if (categoryText === "system" || categoryText === "technical" || categoryText === "network" || categoryText === "hardware" || categoryText === "resource" || categoryText === "telemetry") {
            return {
                group: "system",
                tone: "system"
            };
        }

        // Normal exterior application notification.
        return {
            group: "apps",
            tone: "system"
        };
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

    function scheduleFilteredModelRebuild() {
        filteredModelRefreshTimer.restart();
    }

    function rebuildFilteredNotifications() {
        filteredNotifications.clear();

        if (root.activeFilter === "manager")
            return;

        for (var i = 0; i < NotificationsService.notifications.count; i++) {
            var entry = NotificationsService.notifications.get(i);
            var classification = root.classificationFor(entry.source, entry.sourceId, entry.category, entry.severity);

            if (!root.notificationMatches(entry.source, entry.title, entry.message, entry.category, entry.severity, classification.group))
                continue;

            filteredNotifications.append({
                "notificationId": String(entry.id || ""),
                "source": String(entry.source || ""),
                "sourceId": String(entry.sourceId || ""),
                "title": String(entry.title || ""),
                "message": String(entry.message || ""),
                "appIcon": String(entry.appIcon || ""),
                "category": String(entry.category || "generic"),
                "severity": String(entry.severity || "normal")
            });
        }

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

    function notificationMatches(source, title, message, category, severity, filterGroup) {
        if (root.activeFilter !== "all" && root.activeFilter !== filterGroup)
            return false;

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
            opacity: root.frameCloseGlowOpacity
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

                        color: Colors.white

                        verticalAlignment: TextInput.AlignVCenter

                        selectByMouse: true

                        clip: true

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

                        color: Colors.cyan

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

                    readonly property real buttonWidth: (width - (spacing * 6)) / 7

                    FilterButton {
                        width: filterStrip.buttonWidth
                        height: filterStrip.height
                        filterId: "all"
                        label: "ALL"
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
                        filterId: "system"
                        label: "SYSTEM"
                        accentColor: root.omnitrixGreen
                    }

                    FilterButton {
                        width: filterStrip.buttonWidth
                        height: filterStrip.height
                        filterId: "social"
                        label: "SOCIAL"
                        accentColor: Colors.yellow
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

                    GlowText {
                        id: dndManagerTitle

                        anchors {
                            top: snoozeSettings.bottom
                            left: parent.left
                            right: parent.right
                        }

                        anchors.topMargin: 14
                        anchors.leftMargin: 4
                        anchors.rightMargin: 4

                        height: 24

                        text: "DO NOT DISTURB  //  " + managerDndPolicies.count
                        pixelSize: 13
                        textColor: Colors.magenta
                        glowColor: Colors.magenta
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

                        text: "Sources stay suppressed until you explicitly ALLOW them again."
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
                            border.width: 1
                            border.color: Colors.magenta

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

                        readonly property string appKey: root.appKeyFor(notificationEntry.sourceId, notificationEntry.source)

                        readonly property var sharedAppState: root.stateForApp(notificationEntry.appKey)

                        readonly property bool snoozed: NotificationsService.policyRevision >= 0 && NotificationsService.isSnoozed(notificationEntry.appKey)
                        readonly property bool dnd: NotificationsService.policyRevision >= 0 && NotificationsService.isDnd(notificationEntry.appKey)

                        readonly property var classification: root.classificationFor(notificationEntry.source, notificationEntry.sourceId, notificationEntry.category, notificationEntry.severity)

                        readonly property string filterGroup: notificationEntry.classification.group

                        readonly property string baseTone: notificationEntry.classification.tone

                        readonly property color baseColor: root.baseColorForTone(notificationEntry.baseTone)

                        // Favorite is a VISUAL OVERRIDE, not a base category.
                        readonly property color notificationColor: notificationEntry.sharedAppState.favorite === true ? Colors.magenta : notificationEntry.baseColor

                        readonly property color sourceColor: notificationEntry.sharedAppState.favorite === true ? Colors.magenta : notificationEntry.baseColor

                        readonly property url resolvedAppIcon: root.resolveAppIcon(notificationEntry.appIcon, notificationEntry.sourceId)

                        width: historyList.width
                        height:
                            root.cardHeight
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

                            height: root.cardHeight

                            fillColor: Colors.black
                            fillOpacity: root.cardFillOpacity

                            borderWidth: 1
                            borderColor: notificationEntry.notificationColor

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

                                active: notificationEntry.sharedAppState.favorite === true

                                activeColor: Colors.magenta

                                label: active ? "✦" : "✧"

                                labelPixelSize: 17

                                onTriggered: {
                                    root.toggleAppFlag(notificationEntry.appKey, "favorite");
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

                            // ===== APP NAME ======================

                            GlowText {
                                id: appName

                                anchors {
                                    top: parent.top
                                    left: appIconBox.right
                                    right: appControls.left
                                }

                                anchors.topMargin: root.cardContentMargin
                                anchors.leftMargin: 9
                                anchors.rightMargin: 9

                                height: 20

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

                                height: 15

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
                                    width: 108
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

                                height: 19

                                z: 1

                                text: notificationEntry.message

                                pixelSize: root.notificationMessageFontSize

                                textColor: Colors.white

                                // White text always glows cyan, but tightly.
                                glowColor: Colors.cyan
                                glowRadius: root.tightGlowRadius
                                glowSamples: root.tightGlowSamples

                                elideMode: Text.ElideRight
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
                    railGlowEnabled: false

                    handleColor: Colors.magenta
                    barHandleRadius: 0
                    handleBorderWidth: 0
                    handleGlowStyle: "drop"
                    handleDropGlowRadius: 10
                    handleDropGlowSamples: 13
                    handleDropGlowIdleOpacity: 0.60
                    handleDropGlowHoverOpacity: 0.60

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
