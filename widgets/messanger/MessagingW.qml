import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import "../../components"
import "../../services/messaging"
import QtQuick.Effects
import Qt5Compat.GraphicalEffects

PanelWindow {
    id: messagingWindow

    // ============================================================
    // CONTROLLER WINDOW
    // ============================================================
    //
    // shell.qml still talks to THIS PanelWindow, so its existing anchors and
    // margins continue to define the DEFAULT social-menu placement.
    //
    // The visible social menu itself now lives in socialWindow, a normal
    // FloatingWindow. That is what gives Sessions / Discord / Telegram the
    // same Sway $mod move/resize controls.

    WlrLayershell.layer: WlrLayer.Overlay

    // ============================================================
    // BACKEND
    // ============================================================

    SessionAdapter {
        id: sessionAdapter
    }

    IpcHandler {
        target: "messaging"

        function closeMenu(): void {
            messagingWindow.menuOpen = false;
        }
    }
    Process {
        id: discordShowProcess
    }

    Process {
        id: discordHideProcess
        command: ["swaymsg", "[app_id=\"vesktop\"] move scratchpad"]
    }

    Process {
        id: discordLeaveProcess
        command: ["swaymsg", "[app_id=\"vesktop\"]", "move", "scratchpad"]
    }
    // Persistent Sway IPC helper.
    //
    // Unlike the old Timer -> bash -> swaymsg -> jq loop, this process stays
    // alive and keeps direct Sway IPC sockets open. Geometry arrives as a
    // newline-delimited JSON stream, and live move/resize commands are sent
    // back through the same helper over stdin.
    Process {
        id: groupGeometryHelper

        command: ["python3", Quickshell.shellPath("widgets/messanger/DiscordGeometry.py"), "--interval-ms", String(messagingWindow.geometryPollIntervalMs)]

        running: true
        stdinEnabled: true

        stdout: SplitParser {
            onRead: function (data) {
                var raw = String(data || "").trim();

                if (raw.length === 0)
                    return;

                try {
                    messagingWindow.reconcileGroupGeometry(JSON.parse(raw));
                } catch (e) {
                    console.log("MessagingW: failed to read helper geometry:", e);
                }
            }
        }

        stderr: SplitParser {
            onRead: function (data) {
                var message = String(data || "").trim();

                if (message.length > 0)
                    console.log("DiscordGeometry:", message);
            }
        }

        onStarted: {
            messagingWindow.configureGeometryHelper();
            messagingWindow.updateGeometryHelperMode();
            messagingWindow.setGeometryWatch(messagingWindow.menuOpen);

            if (messagingWindow.menuOpen)
                messagingWindow.requestGroupGeometry();
        }
    }

    Process {
        id: swayGeometryProcess

        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    var workspaces = JSON.parse(text);

                    var workspace = workspaces.find(function (w) {
                        return w.visible && messagingWindow.screen && w.output === messagingWindow.screen.name;
                    });

                    if (!workspace) {
                        console.log("MessagingW: no visible Sway workspace found for screen");
                        return;
                    }

                    messagingWindow.swayAreaX = workspace.rect.x;
                    messagingWindow.swayAreaY = workspace.rect.y;
                    messagingWindow.swayAreaWidth = workspace.rect.width;
                    messagingWindow.swayAreaHeight = workspace.rect.height;
                    messagingWindow.swayGeometryReady = true;

                    messagingWindow.initializeSharedPosition();

                    if (messagingWindow.menuOpen) {
                        Qt.callLater(function () {
                            messagingWindow.syncSocialGeometry(!messagingWindow.discordSelected);

                            if (messagingWindow.discordSelected && messagingWindow.discordReady) {
                                messagingWindow.syncDiscordGeometry(false);
                            }
                        });
                    }
                } catch (e) {
                    console.log("MessagingW: failed to read Sway workspace geometry:", e);
                }
            }
        }
    }

    // Give the normal FloatingWindow a moment to map before Sway receives the
    // first floating/resize/move command.
    Timer {
        id: socialFocusDelay

        interval: 20
        repeat: false

        property int attempts: 0

        onTriggered: {
            if (!messagingWindow.menuOpen) {
                //stop();
                return;
            }

            messagingWindow.syncSocialGeometry(!messagingWindow.discordSelected);

            attempts++;

            if (messagingWindow.socailReady || attempts >= 6) {
                stop();

                if (!messagingWindow.discordSelected)
                    keyboardFocus.forceActiveFocus();
            }
        }
    }

    // Safety fallback: if Vesktop keeps the splash-sized surface longer than
    // expected, promote it after a few seconds instead of leaving Discord in
    // startup mode forever. This does not change the launch lifecycle; it only
    // decides when the visible window may be snapped to the shared slot.
    Timer {
        id: discordStartupFallback

        interval: 6000
        repeat: false

        onTriggered: {
            if (messagingWindow.menuOpen && messagingWindow.discordSelected && !messagingWindow.discordReady) {
                messagingWindow.discordReady = true;
                messagingWindow.syncDiscordGeometry(true);
            }
        }
    }

    // After a Mod-move/resize of the social window while Discord is active,
    // wait until the drag settles before raising Discord again. Doing it during
    // the drag would cancel Sway's move/resize operation.
    Timer {
        id: discordRaiseDelay

        interval: 260
        repeat: false

        onTriggered: {
            if (messagingWindow.menuOpen && messagingWindow.discordSelected && messagingWindow.discordReady) {
                messagingWindow.raiseDiscord();
            }
        }
    }

    // ============================================================
    // WINDOW STATE
    // ============================================================

    property bool menuOpen: false

    property int focusZone: 0

    readonly property int appZone: 0
    readonly property int contactZone: 1
    readonly property int chatZone: 2

    // selectedIndex is only the selector highlight / keyboard cursor.
    // activeAppIndex is the app that is actually open.
    property int activeAppIndex: 0

    // Leave a 1 px cyan shell visible around Vesktop.
    property int discordInset: 1

    readonly property bool discordSelected: activeAppIndex === 1

    onDiscordSelectedChanged: updateGeometryHelperMode()
    onDiscordReadyChanged: updateGeometryHelperMode()

    // ============================================================
    // SHARED GEOMETRY
    // ============================================================
    //
    // There is ONE geometry state for the whole social unit.
    //
    // Sessions / Telegram:
    //   the FloatingWindow can be Mod-moved/resized and updates these values.
    //
    // Discord:
    //   Discord can be Mod-moved/resized and updates these same values, while
    //   the social FloatingWindow follows behind it. Moving/resizing the social
    //   window also updates the same state and Discord follows.

    property int defaultPanelWidth: 1210
    property int defaultPanelHeight: 1355

    property int sharedPanelWidth: defaultPanelWidth
    property int sharedPanelHeight: defaultPanelHeight

    property int sharedPanelX: 0
    property int sharedPanelY: 0

    property bool sharedPositionReady: false
    property bool socialReady: false
    property bool discordReady: false
    property bool discordConfigured: false

    property double ignoreSocialGeometryUntil: 0
    property double ignoreDiscordGeometryUntil: 0

    property int geometryTolerance: 0

    // Direct Sway IPC sampling rate. The helper now also performs the live
    // follower move itself, so there is no QML round trip in the hot path.
    property int geometryPollIntervalMs: 8

    // Only used BEFORE the real Discord window is ready. A little Vesktop /
    // Vencord splash window is centered inside the already-full Discord slot
    // and is NEVER allowed to resize the social menu.
    property int discordStartupMaxWidth: 760
    property int discordStartupMaxHeight: 760

    implicitWidth: sharedPanelWidth
    implicitHeight: sharedPanelHeight

    // ============================================================
    // DEFAULT POSITION FROM shell.qml
    // ============================================================

    anchors {
        top: false
        bottom: true
        right: true
        left: false
    }

    margins {
        top: 0
        bottom: 80
        right: 10
        left: 0
    }

    exclusiveZone: 0

    color: "transparent"
    surfaceFormat.opaque: false

    // Keep this controller PanelWindow alive permanently, but make it fully
    // click-through. The visible/clickable menu is socialWindow below.
    visible: true
    focusable: false

    mask: Region {
        x: 0
        y: 0
        width: 0
        height: 0
    }

    // ============================================================
    // COLUMN WIDTHS
    // ============================================================

    property int appSelectorWidth: 110
    property int contactListWidth: 200
    property int discordGap: 0

    onAppSelectorWidthChanged: configureGeometryHelper()
    onContactListWidthChanged: configureGeometryHelper()
    onDiscordGapChanged: configureGeometryHelper()
    onDiscordInsetChanged: configureGeometryHelper()

    readonly property int minimumSharedWidth: appSelectorWidth + contactListWidth + 1

    readonly property int minimumSharedHeight: 260

    // ============================================================
    // SWAY / GLOBAL GEOMETRY
    // ============================================================

    property int swayAreaX: 0
    property int swayAreaY: 0
    property int swayAreaWidth: 0
    property int swayAreaHeight: 0
    property bool swayGeometryReady: false

    // shell.qml anchors this controller to the top/right. These values are only
    // used to seed the group the first time; after that the shared X/Y persist
    // and can be changed from Sway move operations.
    readonly property int defaultPanelX: swayAreaX + swayAreaWidth - margins.right - defaultPanelWidth

    readonly property int defaultPanelY: swayAreaY + margins.top

    readonly property int discordX: sharedPanelX + appSelectorWidth + discordGap + discordInset

    readonly property int discordY: sharedPanelY + discordInset

    readonly property int discordWidth: Math.max(1, sharedPanelWidth - appSelectorWidth - discordGap - (discordInset * 2))

    readonly property int discordHeight: Math.max(1, sharedPanelHeight - (discordInset * 2))

    // ============================================================
    // VISIBLE SOCIAL WINDOW
    // ============================================================
    //
    // This is a NORMAL toplevel window, so Sway's existing floating_modifier
    // gives Sessions / Discord / Telegram the same $mod move/resize behavior.
    // It stays behind Discord; only the AppSelector part accepts clicks while
    // Discord is active, so the right side passes input through to Vesktop.

    FloatingWindow {
        id: socialWindow

        title: "QS_SOCIAL_MENU"
        screen: messagingWindow.screen

        width: messagingWindow.sharedPanelWidth
        height: messagingWindow.sharedPanelHeight

        minimumSize: Qt.size(messagingWindow.minimumSharedWidth, messagingWindow.minimumSharedHeight)

        visible: messagingWindow.menuOpen

        color: "transparent"
        surfaceFormat.opaque: false

        mask: Region {
            x: 0
            y: 0

            width: messagingWindow.menuOpen ? (messagingWindow.discordSelected ? messagingWindow.appSelectorWidth : socialWindow.width) : 0

            height: messagingWindow.menuOpen ? socialWindow.height : 0
        }
    }

    // ============================================================
    // GEOMETRY HELPERS
    // ============================================================

    function initializeSharedPosition() {
        if (!swayGeometryReady || sharedPositionReady)
            return;

        sharedPanelX = Math.round(defaultPanelX);
        sharedPanelY = Math.round(defaultPanelY);
        sharedPositionReady = true;
    }

    function rectNear(rect, x, y, width, height) {
        if (!rect)
            return false;

        return Math.abs(Number(rect.x) - x) <= geometryTolerance && Math.abs(Number(rect.y) - y) <= geometryTolerance && Math.abs(Number(rect.width) - width) <= geometryTolerance && Math.abs(Number(rect.height) - height) <= geometryTolerance;
    }

    function socialRectNearShared(rect) {
        return rectNear(rect, sharedPanelX, sharedPanelY, sharedPanelWidth, sharedPanelHeight);
    }

    function discordRectNearShared(rect) {
        return rectNear(rect, discordX, discordY, discordWidth, discordHeight);
    }

    function adoptSocialGeometry(rect) {
        if (!rect)
            return;

        sharedPanelX = Math.round(Number(rect.x));
        sharedPanelY = Math.round(Number(rect.y));
        sharedPanelWidth = Math.max(minimumSharedWidth, Math.round(Number(rect.width)));
        sharedPanelHeight = Math.max(minimumSharedHeight, Math.round(Number(rect.height)));
    }

    function adoptDiscordGeometry(rect) {
        if (!rect)
            return;

        var newDiscordWidth = Math.max(contactListWidth + 1, Math.round(Number(rect.width)));

        sharedPanelX = Math.round(Number(rect.x)) - appSelectorWidth - discordGap - discordInset;

        sharedPanelY = Math.round(Number(rect.y)) - discordInset;

        sharedPanelWidth = appSelectorWidth + discordGap + newDiscordWidth + (discordInset * 2);

        sharedPanelHeight = Math.max(minimumSharedHeight, Math.round(Number(rect.height)) + (discordInset * 2));
    }

    function sendGeometryHelper(payload) {
        if (!groupGeometryHelper.running)
            return false;

        groupGeometryHelper.write(JSON.stringify(payload) + "\n");

        return true;
    }

    function configureGeometryHelper() {
        sendGeometryHelper({
            op: "config",
            appSelectorWidth: appSelectorWidth,
            contactListWidth: contactListWidth,
            discordGap: discordGap,
            discordInset: discordInset,
            minimumSharedWidth: minimumSharedWidth,
            minimumSharedHeight: minimumSharedHeight
        });
    }

    function updateGeometryHelperMode() {
        sendGeometryHelper({
            op: "mode",
            discordSelected: discordSelected,
            discordReady: discordReady
        });
    }

    function setGeometryWatch(enabled) {
        sendGeometryHelper({
            op: "watch",
            enabled: enabled
        });
    }

    function requestGroupGeometry() {
        sendGeometryHelper({
            op: "sample"
        });
    }

    function syncHelperWindow(target, x, y, width, height, focusWindow, setupWindow) {
        sendGeometryHelper({
            op: "sync",
            target: target,
            x: Math.round(x),
            y: Math.round(y),
            width: Math.max(1, Math.round(width)),
            height: Math.max(1, Math.round(height)),
            focus: focusWindow === true,
            setup: setupWindow === true
        });
    }

    function helperCenterDiscord(x, y) {
        sendGeometryHelper({
            op: "centerDiscord",
            x: Math.round(x),
            y: Math.round(y)
        });
    }

    function helperFocusDiscord() {
        sendGeometryHelper({
            op: "focusDiscord"
        });
    }

    function reconcileGroupGeometry(payload) {
        if (!menuOpen || !payload)
            return;

        var now = Date.now();
        var socialNode = payload.social;
        var discordNode = payload.discord;
        var socialRect = socialNode ? socialNode.rect : null;
        var discordRect = discordNode ? discordNode.rect : null;

        // First map/configure the social FloatingWindow at the shared default
        // geometry. Do not adopt Sway's temporary tiled/map geometry.
        if (!socialReady) {
            if (socialRect && socialRectNearShared(socialRect)) {
                socialReady = true;
            } else if (now >= ignoreSocialGeometryUntil) {
                syncSocialGeometry(!discordSelected);
            }
        }

        var socialChanged = socialReady && socialRect && now >= ignoreSocialGeometryUntil && !socialRectNearShared(socialRect);

        // Sessions / Telegram: the normal social window is the thing the user
        // Mod-moves/resizes, so it directly updates the shared geometry.
        if (!discordSelected) {
            if (socialChanged)
                adoptSocialGeometry(socialRect);

            return;
        }

        if (!discordRect)
            return;

        // The little Vesktop/Vencord startup window is a guest inside the
        // already-full Discord slot. It is centered, never adopted as geometry.
        if (!discordReady) {
            if (discordLooksLikeStartup(discordRect)) {
                centerDiscordStartup(discordRect);
                return;
            }

            // The real Discord window has appeared. The existing shared social
            // geometry wins for its INITIAL placement/size.
            discordReady = true;
            discordStartupFallback.stop();
            syncDiscordGeometry(true);
            return;
        }

        // While one member is actively focused, DiscordGeometry.py already
        // moved the follower directly through Sway IPC. QML only adopts the
        // canonical shared state here; it does NOT send a second follower
        // command back through the helper.
        if (payload.fastLeader && payload.shared) {
            sharedPanelX = Math.round(Number(payload.shared.x));
            sharedPanelY = Math.round(Number(payload.shared.y));
            sharedPanelWidth = Math.max(minimumSharedWidth, Math.round(Number(payload.shared.width)));
            sharedPanelHeight = Math.max(minimumSharedHeight, Math.round(Number(payload.shared.height)));

            return;
        }

        var discordChanged = now >= ignoreDiscordGeometryUntil && !discordRectNearShared(discordRect);

        if (!socialChanged && !discordChanged)
            return;

        // If both differ in the same compositor snapshot, use the focused one
        // as the user's active resize/move source.
        if (socialChanged && discordChanged) {
            if (discordNode.focused && !socialNode.focused) {
                adoptDiscordGeometry(discordRect);
                syncSocialGeometry(false);
            } else {
                adoptSocialGeometry(socialRect);
                syncDiscordGeometry(false);
                discordRaiseDelay.restart();
            }
            return;
        }

        if (discordChanged) {
            adoptDiscordGeometry(discordRect);
            syncSocialGeometry(false);
            return;
        }

        if (socialChanged) {
            adoptSocialGeometry(socialRect);
            syncDiscordGeometry(false);
            discordRaiseDelay.restart();
        }
    }

    function discordLooksLikeStartup(rect) {
        if (!rect || discordReady)
            return false;

        var width = Math.round(Number(rect.width));
        var height = Math.round(Number(rect.height));

        return (width <= discordStartupMaxWidth && height <= discordStartupMaxHeight) || (width < discordWidth * 0.55 && height < discordHeight * 0.55);
    }

    function centerDiscordStartup(rect) {
        if (!rect || !sharedPositionReady)
            return;

        var width = Math.round(Number(rect.width));
        var height = Math.round(Number(rect.height));

        var x = Math.round(discordX + Math.max(0, discordWidth - width) / 2);

        var y = Math.round(discordY + Math.max(0, discordHeight - height) / 2);

        // Do not resize the splash. Only center it inside the full shell.
        ignoreDiscordGeometryUntil = Date.now() + 180;

        helperCenterDiscord(x, y);
    }

    function syncSocialGeometry(focusWindow) {
        if (!menuOpen || !sharedPositionReady)
            return;

        ignoreSocialGeometryUntil = Date.now() + 80;

        // Only repeat the floating/border setup while the social window is
        // still being mapped into its initial shared geometry. During live
        // following we send ONLY the newest geometry, so stale moves do not
        // queue behind the cursor.
        syncHelperWindow("social", sharedPanelX, sharedPanelY, sharedPanelWidth, sharedPanelHeight, focusWindow, !socialReady);
    }

    function syncDiscordGeometry(focusWindow) {
        if (!menuOpen || !discordSelected || !discordReady || !sharedPositionReady) {
            return;
        }

        ignoreDiscordGeometryUntil = Date.now() + 280;

        syncHelperWindow("discord", discordX, discordY, discordWidth, discordHeight, focusWindow, !discordConfigured);

        discordConfigured = true;
    }

    function raiseDiscord() {
        if (!menuOpen || !discordSelected || !discordReady)
            return;

        helperFocusDiscord();
    }

    function refreshSwayGeometry() {
        if (swayGeometryProcess.running)
            swayGeometryProcess.running = false;

        swayGeometryProcess.exec(["swaymsg", "-r", "-t", "get_workspaces"]);
    }

    // ============================================================
    // DISCORD LIFECYCLE
    // ============================================================

    function showDiscord() {
        if (!menuOpen || !discordSelected)
            return;

        discordConfigured = false;
        ignoreDiscordGeometryUntil = 0;

        if (!discordReady)
            discordStartupFallback.restart();

        if (discordLeaveProcess.running)
            discordLeaveProcess.running = false;

        if (discordShowProcess.running)
            discordShowProcess.running = false;

        if (!swayGeometryReady)
            refreshSwayGeometry();

        // Preserve the existing launch/scratchpad behavior. The difference is
        // that we no longer resize the first little startup window. The group
        // geometry poll will center that splash until the real window appears.
        discordShowProcess.exec(["bash", "-lc", "if ! swaymsg -t get_tree | grep -q '\"app_id\": \"vesktop\"'; then " + "setsid -f flatpak run dev.vencord.Vesktop >/dev/null 2>&1; " + "for i in $(seq 1 100); do " + "swaymsg -t get_tree | grep -q '\"app_id\": \"vesktop\"' && break; " + "sleep 0.1; " + "done; " + "fi; " + "swaymsg '[app_id=\"vesktop\"] move scratchpad'; " + "swaymsg '[app_id=\"vesktop\"] scratchpad show'"]);

        Qt.callLater(function () {
            messagingWindow.requestGroupGeometry();
        });
    }

    function hideDiscord() {
        discordRaiseDelay.stop();
        discordStartupFallback.stop();
        discordConfigured = false;
        ignoreDiscordGeometryUntil = 0;

        if (discordShowProcess.running)
            discordShowProcess.running = false;

        if (discordHideProcess.running)
            discordHideProcess.running = false;

        discordHideProcess.running = true;
    }

    // ============================================================
    // FOCUS / APP HELPERS
    // ============================================================

    function focusAppSelector() {
        focusZone = appZone;
        appSelector.keyboardActive = true;
        keyboardFocus.forceActiveFocus();
    }

    function focusContacts() {
        if (contactList.conversations.length === 0)
            return;

        focusZone = contactZone;
        contactList.keyboardActive = true;
        contactList.ensureValidIndex();
        keyboardFocus.forceActiveFocus();
    }

    function focusComposer() {
        if (!contactList.selectedConversation)
            return;

        focusZone = chatZone;
        chatFeed.focusMessageInput();
    }

    function activateApp(index) {
        activeAppIndex = index;
        contactList.clearSelection();

        if (index === 1) {
            showDiscord();
            return;
        }

        hideDiscord();

        // Returning to Sessions / Telegram puts focus back on the same normal
        // social FloatingWindow, preserving the same Mod move/resize controls.
        syncSocialGeometry(true);

        Qt.callLater(function () {
            keyboardFocus.forceActiveFocus();
        });

        if (index === 0 && contactList.conversations.length > 0)
            focusContacts();
    }

    function acceptSelectedApp() {
        activateApp(appSelector.selectedIndex);
    }

    function activateCurrentContact() {
        if (!contactList.activateCurrent())
            return;

        focusComposer();
    }

    function returnToContacts() {
        if (contactList.conversations.length === 0) {
            focusAppSelector();
            return;
        }

        focusZone = contactZone;
        contactList.keyboardActive = true;
        contactList.ensureValidIndex();
        keyboardFocus.forceActiveFocus();
    }

    // ============================================================
    // VISUAL CONTENT
    // ============================================================

    Item {
        id: messagingContent

        parent: socialWindow.contentItem
        anchors.fill: parent

        visible: messagingWindow.menuOpen

        // ========================================================
        // BACKGROUND
        // ========================================================

        Rectangle {
            id: messagingBackground

            anchors.fill: parent

            color: Colors.black
            opacity: 0.20

            radius: 0

            z: -100
        }

        // ========================================================
        // KEYBOARD CONTROLLER
        // ========================================================

        Item {
            id: keyboardFocus

            anchors.fill: parent

            focus: messagingWindow.menuOpen && messagingWindow.focusZone !== messagingWindow.chatZone

            z: 0

            Keys.onPressed: function (event) {
                if (!messagingWindow.menuOpen)
                    return;

                // ================================================
                // APP SELECTOR
                // ================================================

                if (messagingWindow.focusZone === messagingWindow.appZone) {
                    if (event.key === Qt.Key_Up) {
                        appSelector.keyboardActive = true;

                        if (appSelector.selectedIndex > 0) {
                            appSelector.selectedIndex--;
                        } else {
                            appSelector.selectedIndex = appSelector.messagingApps.length - 1;
                        }

                        event.accepted = true;
                        return;
                    }

                    if (event.key === Qt.Key_Down) {
                        appSelector.keyboardActive = true;

                        if (appSelector.selectedIndex < appSelector.messagingApps.length - 1) {
                            appSelector.selectedIndex++;
                        } else {
                            appSelector.selectedIndex = 0;
                        }

                        event.accepted = true;
                        return;
                    }

                    if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                        messagingWindow.acceptSelectedApp();

                        event.accepted = true;
                        return;
                    }

                    if (event.key === Qt.Key_Right) {
                        messagingWindow.acceptSelectedApp();

                        event.accepted = true;
                        return;
                    }

                    if (event.key === Qt.Key_Escape) {
                        if (messagingWindow.discordSelected)
                            //if (activeAppIndex === DISCORD_INDEX)
                            discordLeaveProcess.running = true;

                        messagingWindow.menuOpen = false;

                        event.accepted = true;
                        return;
                    }
                }

                // ================================================
                // CONTACT LIST
                // ================================================

                if (messagingWindow.focusZone === messagingWindow.contactZone) {
                    if (event.key === Qt.Key_Up) {
                        contactList.keyboardActive = true;

                        contactList.moveSelection(-1);

                        event.accepted = true;
                        return;
                    }

                    if (event.key === Qt.Key_Down) {
                        contactList.keyboardActive = true;

                        contactList.moveSelection(1);

                        event.accepted = true;
                        return;
                    }

                    if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                        messagingWindow.activateCurrentContact();

                        event.accepted = true;
                        return;
                    }

                    if (event.key === Qt.Key_Right) {
                        messagingWindow.activateCurrentContact();

                        event.accepted = true;
                        return;
                    }

                    if (event.key === Qt.Key_Left) {
                        messagingWindow.focusAppSelector();

                        event.accepted = true;
                        return;
                    }

                    if (event.key === Qt.Key_Escape) {
                        messagingWindow.focusAppSelector();

                        event.accepted = true;
                        return;
                    }
                }
            }
        }

        // ========================================================
        // APP SELECTOR
        // ========================================================

        AppSelector {
            id: appSelector

            width: messagingWindow.appSelectorWidth
            height: parent.height

            anchors {
                left: parent.left
                top: parent.top
                bottom: parent.bottom
            }

            z: 3

            onSelectedIndexChanged: {
                // Hover / keyboard movement only changes the highlight.
                if (messagingWindow.focusZone === messagingWindow.appZone && !messagingWindow.discordSelected) {
                    keyboardFocus.forceActiveFocus();
                }
            }

            // The AppSelector's OWN MouseArea emits this only
            // on a real click.
            onAppActivated: function (index) {
                messagingWindow.activateApp(index);
            }
        }

        // ========================================================
        // CONTACT LIST
        // ========================================================

        ContactList {
            id: contactList

            x: messagingWindow.appSelectorWidth
            y: 0

            width: messagingWindow.contactListWidth
            height: messagingContent.height

            visible: messagingWindow.menuOpen

            discordMode: messagingWindow.discordSelected

            z: 2

            keyboardFocused: messagingWindow.focusZone === messagingWindow.contactZone

            // ----------------------------------------------------
            // ACTIVE BACKEND CONTACTS
            // ----------------------------------------------------

            conversations: messagingWindow.activeAppIndex === 0 ? sessionAdapter.conversations : []

            // ----------------------------------------------------
            // CONVERSATION CHANGE
            // ----------------------------------------------------

            onSelectedConversationChanged: {
                if (messagingWindow.activeAppIndex === 0 && selectedConversation) {
                    sessionAdapter.loadMessages(selectedConversation.id);
                }
            }

            // ----------------------------------------------------
            // MOUSE CLICK
            // ----------------------------------------------------

            onContactClicked: {
                messagingWindow.focusZone = messagingWindow.contactZone;

                contactList.keyboardActive = false;

                keyboardFocus.forceActiveFocus();
            }
        }

        // ========================================================
        // CHAT FEED
        // ========================================================

        ChatFeed {
            id: chatFeed

            x: messagingWindow.appSelectorWidth + messagingWindow.contactListWidth

            y: 0

            width: Math.max(1, messagingContent.width - x)

            height: messagingContent.height

            visible: messagingWindow.menuOpen

            discordMode: messagingWindow.discordSelected

            z: 1

            // ----------------------------------------------------
            // ACTIVE CONVERSATION
            // ----------------------------------------------------

            conversation: messagingWindow.activeAppIndex === 0 ? contactList.selectedConversation : null

            // ----------------------------------------------------
            // MESSAGES
            // ----------------------------------------------------

            messages: messagingWindow.activeAppIndex === 0 ? sessionAdapter.messages : []

            // ----------------------------------------------------
            // LOADING
            // ----------------------------------------------------

            loading: messagingWindow.activeAppIndex === 0 ? sessionAdapter.messagesLoading : false

            // ----------------------------------------------------
            // LOAD ERROR
            // ----------------------------------------------------

            error: messagingWindow.activeAppIndex === 0 ? sessionAdapter.messagesError : ""

            // ----------------------------------------------------
            // SENDING
            // ----------------------------------------------------

            sending: messagingWindow.activeAppIndex === 0 ? sessionAdapter.sending : false

            // ----------------------------------------------------
            // SEND ERROR
            // ----------------------------------------------------

            sendError: messagingWindow.activeAppIndex === 0 ? sessionAdapter.sendError : ""

            // ----------------------------------------------------
            // SEND SUCCESS
            // ----------------------------------------------------

            sendSuccessSerial: messagingWindow.activeAppIndex === 0 ? sessionAdapter.sendSuccessSerial : 0

            // ----------------------------------------------------
            // SEND MESSAGE
            // ----------------------------------------------------

            onSendRequested: function (conversationId, text) {
                if (messagingWindow.activeAppIndex === 0) {
                    sessionAdapter.sendMessage(conversationId, text);
                }
            }

            // ----------------------------------------------------
            // LEFT / ESCAPE FROM CHAT
            // ----------------------------------------------------

            onComposerEscapeRequested: {
                messagingWindow.returnToContacts();
            }
        }
    }

    // ============================================================
    // OPEN / CLOSE
    // ============================================================

    onMenuOpenChanged: {
        setGeometryWatch(menuOpen);

        if (menuOpen) {
            messagingWindow.setGeometryWatch(true);

            // The BAR Sessions button opens the menu on Sessions.
            activeAppIndex = 0;
            appSelector.selectedIndex = 0;

            messagingWindow.hideDiscord();

            sharedPanelWidth = defaultPanelWidth;
            sharedPanelHeight = defaultPanelHeight;

            sharedPanelX = Math.round(defaultPanelX);
            sharedPanelY = Math.round(defaultPanelY);

            focusZone = appZone;
            appSelector.keyboardActive = true;

            socialReady = false;
            refreshSwayGeometry();

            Qt.callLater(function () {
                if (sharedPositionReady)
                    messagingWindow.syncSocialGeometry(true);
            });

            socialFocusDelay.attempts = 0;
            socialFocusDelay.restart();
        } else {
            messagingWindow.setGeometryWatch(false);

            if (discordLeaveProcess.running)
                discordLeaveProcess.running = false;

            discordLeaveProcess.running = true;

            activeAppIndex = 0;
            focusZone = appZone;
            keyboardFocus.focus = false;
            socialReady = false;
        }
    }
}
