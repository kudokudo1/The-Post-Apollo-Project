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

    SocialMessageRouter {
        id: messageRouter
        appIndex: messagingWindow.activeAppIndex
    }

    IpcHandler {
        target: "messaging"

        function closeMenu(): void {
            messagingWindow.menuOpen = false;
        }
    }
    Process {
        id: discordShowProcess

        onExited: function(exitCode, exitStatus) {
            // Opening the native Discord window necessarily causes Sway to
            // focus Vesktop. Only a keyboard-initiated Main Mode switch
            // requests the Social selector back. Mouse clicks still open
            // Discord with normal application focus.
            if (!messagingWindow.restoreSelectorAfterDiscordShow)
                return;
            if (!messagingWindow.menuOpen || !messagingWindow.discordSelected)
                return;
            messagingWindow.focusZone = messagingWindow.appZone;
            messagingWindow.syncSocialGeometry(true);
            Qt.callLater(function() {
                if (messagingWindow.menuOpen && messagingWindow.discordSelected
                        && messagingWindow.focusZone === messagingWindow.appZone)
                    messagingWindow.focusAppSelector();
            });
        }
    }

    // X runs as a separate browser app; Chromium owns its private profile.
    Process {
        id: xShowProcess
        property string launchSite: "x"
        stderr: StdioCollector {
            onStreamFinished: {
                var detail = String(text || "").trim();
                if (detail !== "" && xShowProcess.launchSite === messagingWindow.browserSite)
                    messagingWindow.xError = detail;
            }
        }
        onExited: function(exitCode, exitStatus) {
            // A previous site's startup must not seize the current selection.
            if (xShowProcess.launchSite !== messagingWindow.browserSite)
                return;
            if (exitCode !== 0 && messagingWindow.xError === "")
                messagingWindow.xError = xShowProcess.launchSite.toUpperCase() + " window could not be opened";
            if (!messagingWindow.menuOpen || !messagingWindow.xSelected) {
                messagingWindow.hideX();
                return;
            }
            messagingWindow.requestGroupGeometry();
            if (messagingWindow.restoreSelectorAfterXShow) {
                messagingWindow.restoreSelectorAfterXShow = false;
                messagingWindow.focusZone = messagingWindow.appZone;
                messagingWindow.syncSocialGeometry(true);
                Qt.callLater(function() {
                    if (messagingWindow.menuOpen && messagingWindow.xSelected)
                        messagingWindow.focusAppSelector();
                });
            }
        }
    }

    Process {
        id: xHideProcess
        command: ["python3", Quickshell.shellPath("widgets/messanger/XBrowser.py"), "hide", "all"]
    }

    Process {
        id: providerDesktopHideProcess
        // The helper refuses to hide anything without our Sway window mark
        // and exact provider process identity.
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
                            messagingWindow.syncSocialGeometry(!messagingWindow.externalSelected);

                            if (messagingWindow.discordSelected && messagingWindow.discordReady) {
                                messagingWindow.syncDiscordGeometry(false);
                            } else if (messagingWindow.xSelected && messagingWindow.xReady) {
                                messagingWindow.syncXGeometry(false);
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
        repeat: true

        property int attempts: 0

        onTriggered: {
            if (!messagingWindow.menuOpen) {
                stop();
                return;
            }

            messagingWindow.syncSocialGeometry(!messagingWindow.externalSelected);

            attempts++;

            if (messagingWindow.socialReady || attempts >= 6) {
                stop();

                if (!messagingWindow.externalSelected)
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
                // A stale Vesktop position cannot become authoritative while
                // the Social FloatingWindow is still being positioned.
                if (!messagingWindow.socialReady) {
                    messagingWindow.requestGroupGeometry();
                    return;
                }
                messagingWindow.discordReady = true;
                messagingWindow.syncDiscordGeometry(true);
            }
        }
    }

    // After a Mod-move/resize of the social window while Discord is active,
    // wait until the drag settles before raising Discord again. Doing it during
    // the drag would cancel Sway's move/resize operation.
    Timer {
        id: xRaiseDelay
        interval: 260
        repeat: false
        onTriggered: messagingWindow.raiseX()
    }

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
    // Tab navigation belongs to the Social selector, not the external
    // Discord window. Only set while a keyboard Main Mode transition opens it.
    property bool restoreSelectorAfterDiscordShow: false
    property bool restoreSelectorAfterXShow: false
    property string xError: ""

    property int focusZone: 0

    readonly property int appZone: 0
    readonly property int contactZone: 1
    readonly property int chatZone: 2

    // selectedIndex is only the selector highlight / keyboard cursor.
    // activeAppIndex is the app that is actually open.
    property int activeAppIndex: 0

    // Leave a 1 px cyan shell visible around Vesktop.
    property int discordInset: 1

    readonly property bool nativeChatSelected: activeAppIndex === 0 || activeAppIndex === 2
    readonly property bool discordSelected: activeAppIndex === 1
    readonly property bool providerAccessSelected:
        activeAppIndex === 14 || activeAppIndex === 15 ||
        (activeAppIndex >= 26 && activeAppIndex <= 31)
    property bool providerWebOpen: false
    // Only a direct Dock click manages a provider window. Never attach on
    // mere selection, login status, or account-manager identity switch.
    property bool providerDesktopManaged: false
    property string providerDesktopService: ""
    // xSelected retains the existing external-browser focus contract.
    readonly property bool xSelected: (activeAppIndex >= 3 && activeAppIndex <= 13) || (activeAppIndex >= 16 && activeAppIndex <= 25)
        || ((activeAppIndex === 14 || activeAppIndex === 15 || activeAppIndex === 28) && providerWebOpen)
    readonly property string browserSite:
        activeAppIndex === 14 && providerWebOpen ? "whatsappweb" :
        activeAppIndex === 15 && providerWebOpen ? "messengerweb" :
        activeAppIndex === 28 && providerWebOpen ? "linechrome" :
        activeAppIndex === 4 ? "instagram" :
        activeAppIndex === 5 ? "facebook" :
        activeAppIndex === 6 ? "reddit" :
        activeAppIndex === 7 ? "threads" :
        activeAppIndex === 8 ? "pinterest" :
        activeAppIndex === 9 ? "truthsocial" :
        activeAppIndex === 10 ? "bluesky" :
        activeAppIndex === 11 ? "tumblr" :
        activeAppIndex === 12 ? "tiktok" :
        activeAppIndex === 13 ? "snapchat" :
        activeAppIndex === 16 ? "linkedin" :
        activeAppIndex === 17 ? "mastodon" :
        activeAppIndex === 18 ? "nextdoor" :
        activeAppIndex === 19 ? "steamchat" :
        activeAppIndex === 20 ? "element" :
        activeAppIndex === 21 ? "groupme" :
        activeAppIndex === 22 ? "lemon8" :
        activeAppIndex === 23 ? "quora" :
        activeAppIndex === 24 ? "pixelfed" :
        activeAppIndex === 25 ? "zalo" : "x"
    readonly property bool externalSelected: discordSelected || xSelected || providerDesktopManaged
    onBrowserSiteChanged: updateGeometryHelperMode()

    onDiscordSelectedChanged: updateGeometryHelperMode()
    onDiscordReadyChanged: updateGeometryHelperMode()
    onDiscordDockedChanged: {
        updateGeometryHelperMode();
        if (!discordDocked || !menuOpen || !discordSelected)
            return;

        // Keyboard Main-Mode switching keeps the selector focused; direct
        // Discord activation lets Vesktop own focus after the verified dock.
        if (restoreSelectorAfterDiscordShow) {
            restoreSelectorAfterDiscordShow = false;
            focusZone = appZone;
            syncSocialGeometry(true);
            Qt.callLater(function() {
                if (menuOpen && discordSelected)
                    focusAppSelector();
            });
        } else {
            discordRaiseDelay.restart();
        }
    }
    onXSelectedChanged: updateGeometryHelperMode()
    onXReadyChanged: updateGeometryHelperMode()

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
    // The Notification window's VISIBLE frame is inset by 8px on both
    // ends. Social's FloatingWindow has no comparable visible-frame inset:
    // size it to that actual frame, not to Notifications' outer window.
    property var notificationsReference: null
    readonly property int notificationsFrameInset:
        notificationsReference ? notificationsReference.frameInset : 8
    readonly property int notificationsBottomMargin:
        notificationsReference ? notificationsReference.panelBottomMargin : 5
    property int defaultPanelHeight: Math.max(
        minimumSharedHeight,
        notificationsReference
        ? Math.round(notificationsReference.height) - 2 * notificationsFrameInset
        : (screen ? Math.round(screen.height) : 1360)
          - notificationsBottomMargin - 2 * notificationsFrameInset
    )

    property int sharedPanelWidth: defaultPanelWidth
    property int sharedPanelHeight: defaultPanelHeight

    property int sharedPanelX: 0
    property int sharedPanelY: 0

    property bool sharedPositionReady: false
    property bool socialReady: false
    property bool discordReady: false
    // Only after initial Social-owned placement may Vesktop lead $mod moves.
    property bool discordDocked: false
    property bool discordConfigured: false
    property bool xReady: false
    property bool xConfigured: false

    property double ignoreSocialGeometryUntil: 0
    property double ignoreDiscordGeometryUntil: 0
    property double ignoreXGeometryUntil: 0

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

    // Sway's visible workspace rect begins BELOW the reserved top bar/gap.
    // That is the same upper rail the other menus actually open against.
    // Do not use QScreen.geometry.y (the physical output top), which placed
    // Social behind the bar and clipped its header in the live screenshot.
    // The workspace origin already includes the rail offset: no extra inset.
    // Only the default opening Y changes. Manual Sway moves still win.
    readonly property int defaultPanelY: Math.round(swayAreaY)

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

            width: messagingWindow.menuOpen ? (messagingWindow.externalSelected ? messagingWindow.appSelectorWidth : socialWindow.width) : 0

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

    function initialSocialDockAligned(rect) {
        if (!rect)
            return false;
        const tolerance = 2; // Floating-window pixel rounding at startup.
        return Math.abs(Number(rect.x) - sharedPanelX) <= tolerance
            && Math.abs(Number(rect.y) - sharedPanelY) <= tolerance
            && Math.abs(Number(rect.width) - sharedPanelWidth) <= tolerance
            && Math.abs(Number(rect.height) - sharedPanelHeight) <= tolerance;
    }

    function discordRectNearShared(rect) {
        return rectNear(rect, discordX, discordY, discordWidth, discordHeight);
    }

    function initialDiscordDockAligned(rect) {
        // The compositor may round a floating window by a pixel. Require
        // actual placement in the slot, not exact fractional pixel identity.
        if (!rect)
            return false;
        const tolerance = 2;
        return Math.abs(Number(rect.x) - discordX) <= tolerance
            && Math.abs(Number(rect.y) - discordY) <= tolerance
            && Math.abs(Number(rect.width) - discordWidth) <= tolerance
            && Math.abs(Number(rect.height) - discordHeight) <= tolerance;
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
            discordReady: discordReady,
            discordDocked: discordDocked,
            xSelected: xSelected,
            xReady: xReady,
            browserSite: browserSite
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

    function helperShowDiscord(focusWindow) {
        sendGeometryHelper({
            op: "showDiscord",
            focus: focusWindow === true
        });
    }

    function helperHideDiscord() {
        sendGeometryHelper({ op: "hideDiscord" });
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
        // Hidden scratchpad Vesktop nodes are still discoverable so the helper
        // can target them by con_id, but they do not participate in geometry
        // until the compositor reports the client visible.
        var discordRect = discordNode && discordNode.visible ? discordNode.rect : null;

        // First map/configure the social FloatingWindow at the shared default
        // geometry. Do not adopt Sway's temporary tiled/map geometry.
        if (!socialReady) {
            if (socialRect && initialSocialDockAligned(socialRect)) {
                socialReady = true;
            } else if (now >= ignoreSocialGeometryUntil) {
                syncSocialGeometry(!discordSelected);
            }
        }

        var socialChanged = socialReady && socialRect && now >= ignoreSocialGeometryUntil && !socialRectNearShared(socialRect);

        if (xSelected) {
            // X uses the shared external window slot, but its own lifecycle.
            var xNode = payload[browserSite];
            var xRect = xNode ? xNode.rect : null;
            if (!xRect) {
                if (socialChanged)
                    adoptSocialGeometry(socialRect);
                return;
            }
            if (!xReady) {
                xReady = true;
                syncXGeometry(true);
                return;
            }
            if (payload.fastLeader && payload.shared) {
                sharedPanelX = Math.round(Number(payload.shared.x));
                sharedPanelY = Math.round(Number(payload.shared.y));
                sharedPanelWidth = Math.max(minimumSharedWidth, Math.round(Number(payload.shared.width)));
                sharedPanelHeight = Math.max(minimumSharedHeight, Math.round(Number(payload.shared.height)));
                return;
            }
            var xChanged = now >= ignoreXGeometryUntil && !discordRectNearShared(xRect);
            if (socialChanged && xChanged) {
                if (xNode.focused && (!socialNode || !socialNode.focused)) {
                    adoptDiscordGeometry(xRect);
                    syncSocialGeometry(false);
                } else {
                    adoptSocialGeometry(socialRect);
                    syncXGeometry(false);
                    xRaiseDelay.restart();
                }
            } else if (xChanged) {
                adoptDiscordGeometry(xRect);
                syncSocialGeometry(false);
            } else if (socialChanged) {
                adoptSocialGeometry(socialRect);
                syncXGeometry(false);
                xRaiseDelay.restart();
            }
            return;
        }

        // Sessions / Telegram: the normal social window is the thing the user
        // Mod-moves/resizes, so it directly updates the shared geometry.
        if (!discordSelected) {
            if (socialChanged)
                adoptSocialGeometry(socialRect);

            return;
        }

        // The first mapped Social rectangle is authoritative on activation.
        if (!socialReady || !discordRect)
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

        // On every activation Social places Discord first. A scratchpad view
        // can retain its old position; never let that pull Social away.
        if (!discordDocked) {
            if (initialDiscordDockAligned(discordRect)) {
                discordDocked = true;
            } else if (now >= ignoreDiscordGeometryUntil) {
                syncDiscordGeometry(false);
            }
            return;
        }

        // Only after confirmed docking can focused Discord lead geometry.
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

    function syncXGeometry(focusWindow) {
        if (!menuOpen || !xSelected || !xReady || !sharedPositionReady)
            return;

        ignoreXGeometryUntil = Date.now() + 280;
        // Existing discord* values describe the shared external-app slot.
        syncHelperWindow(browserSite, discordX, discordY, discordWidth,
                         discordHeight, focusWindow, !xConfigured);
        xConfigured = true;
    }

    function raiseX() {
        if (!menuOpen || !xSelected || !xReady)
            return;
        sendGeometryHelper({ op: "focusX" });
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

        discordReady = false;
        discordDocked = false;
        discordConfigured = false;
        ignoreDiscordGeometryUntil = 0;

        discordStartupFallback.restart();

        if (discordShowProcess.running)
            discordShowProcess.running = false;

        if (!swayGeometryReady)
            refreshSwayGeometry();

        // Launch only the provider process here. Window discovery and every
        // Sway mutation are owned by DiscordGeometry.py after it finds the
        // real runtime container id. This supports both native Wayland and
        // XWayland Vesktop identities without hard-coded app_id commands.
        discordShowProcess.exec(["bash", "-lc",
            "if ! flatpak ps --columns=application 2>/dev/null "
            + "| grep -Fxq 'dev.vencord.Vesktop'; then "
            + "setsid -f flatpak run dev.vencord.Vesktop >/dev/null 2>&1; "
            + "fi"
        ]);

        helperShowDiscord(restoreSelectorAfterDiscordShow !== true);

        Qt.callLater(function () {
            messagingWindow.requestGroupGeometry();
        });
    }

    function hideDiscord() {
        restoreSelectorAfterDiscordShow = false;
        discordRaiseDelay.stop();
        discordStartupFallback.stop();
        discordReady = false;
        discordDocked = false;
        discordConfigured = false;
        ignoreDiscordGeometryUntil = 0;

        if (discordShowProcess.running)
            discordShowProcess.running = false;

        helperHideDiscord();
    }

    // ============================================================
    // X APP LIFECYCLE
    // ============================================================

    function showX() {
        if (!menuOpen || !xSelected)
            return;
        xError = "";
        xReady = false;
        xConfigured = false;
        ignoreXGeometryUntil = 0;
        if (xHideProcess.running)
            xHideProcess.running = false;
        if (!swayGeometryReady)
            refreshSwayGeometry();
        if (xShowProcess.running)
            xShowProcess.running = false;
        xShowProcess.launchSite = browserSite;
        xShowProcess.exec(["python3", Quickshell.shellPath("widgets/messanger/XBrowser.py"), "show", browserSite]);
    }

    function hideX() {
        restoreSelectorAfterXShow = false;
        xRaiseDelay.stop();
        xReady = false;
        xConfigured = false;
        ignoreXGeometryUntil = 0;
        if (xHideProcess.running)
            xHideProcess.running = false;
        xHideProcess.running = true;
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

    function hideProviderDesktop() {
        if (!providerDesktopManaged || providerDesktopService === "")
            return;
        const managedService = providerDesktopService;
        providerDesktopManaged = false;
        providerDesktopService = "";
        if (providerDesktopHideProcess.running)
            providerDesktopHideProcess.running = false;
        providerDesktopHideProcess.exec([
            "python3", Quickshell.shellPath("services/messaging/DesktopWindowBridge.py"),
            "hide", managedService
        ]);
    }

    function openProviderWeb(service) {
        // A provider website is a provider-owned UI, not a native message API.
        if (!menuOpen || providerWebOpen)
            return;
        if ((service === "whatsapp" && activeAppIndex !== 14)
                || (service === "messenger" && activeAppIndex !== 15)
                || (service === "line" && activeAppIndex !== 28))
            return;
        if (service !== "whatsapp" && service !== "messenger" && service !== "line")
            return;
        providerWebOpen = true;
        hideDiscord();
        xError = "";
        showX();
    }

    function activateApp(index, retainSelectorFocus) {
        hideProviderDesktop();
        if (providerWebOpen) {
            hideX();
            providerWebOpen = false;
        }
        // Disarm Discord before the selector flips: otherwise an already
        // focused Vesktop could send one stale fast-follow update first.
        if (index === 1) {
            discordReady = false;
            discordDocked = false;
        }
        // Clear the old selection before swapping adapters; never briefly
        // render a Sessions thread under Telegram or vice versa.
        contactList.clearSelection();
        activeAppIndex = index;

        if (retainSelectorFocus === true) {
            focusZone = appZone;
            appSelector.keyboardActive = true;
        }

        if (index === 1) {
            hideX();
            restoreSelectorAfterDiscordShow = retainSelectorFocus === true;
            showDiscord();
            return;
        }

        if ((index >= 3 && index <= 13) || (index >= 16 && index <= 25)) {
            hideDiscord();
            restoreSelectorAfterXShow = retainSelectorFocus === true;
            showX();
            return;
        }

        hideDiscord();
        hideX();

        // Returning to native Sessions / Telegram / placeholder modes restores the normal
        // social FloatingWindow, preserving the same Mod move/resize controls.
        syncSocialGeometry(true);

        Qt.callLater(function () {
            keyboardFocus.forceActiveFocus();
        });

        if (messagingWindow.nativeChatSelected && contactList.conversations.length > 0)
            focusContacts();
    }

    function acceptSelectedApp() {
        // The cursor may have been inside a family that was just collapsed.
        // Never route Enter/Right to a hidden or no-longer-visible provider.
        if (appSelector.isAppVisible(appSelector.selectedIndex))
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

    WindowPanelFrame {
        id: messagingContent

        parent: socialWindow.contentItem
        anchors.fill: parent

        visible: messagingWindow.menuOpen

        fillColor: Colors.black
        // External apps float above the normal Social pane surfaces. Keep the
        // same chassis underneath Discord that X/browser apps already use.
        fillOpacity: 0.20
        borderVisible: false
        radius: 0

        // Social already composes its glow from its app/contact surfaces.
        // Preserve that visual balance instead of adding a second outer aura.
        glowVisible: false

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

                // The in-rail settings sheet is not an application.
                // Escape returns to the app rail; other keys must not invisibly
                // activate apps while their buttons are hidden.
                if (appSelector.settingsOpen) {
                    if (event.key === Qt.Key_Escape)
                        appSelector.settingsOpen = false;
                    event.accepted = true;
                    return;
                }

                // Nurse 3c // Main Modes are the existing app-selector choices.
                // Tab changes the active application just like its clicked mode
                // button; chat/composer focus stays reserved to the editor.
                if (messagingWindow.focusZone !== messagingWindow.chatZone
                        && (event.key === Qt.Key_Tab
                            || event.key === Qt.Key_Backtab)) {
                    const count = appSelector.visibleAppIndices.length;
                    if (count > 1) {
                        const reverse = event.key === Qt.Key_Backtab
                            || (event.modifiers & Qt.ShiftModifier) !== 0;
                        const index = appSelector.nextActiveAppIndex(
                            messagingWindow.activeAppIndex, reverse);
                        if (index >= 0) {
                            appSelector.selectedIndex = index;
                            messagingWindow.activateApp(index, true);
                        }
                    }
                    event.accepted = true;
                    return;
                }

                // ================================================
                // APP SELECTOR
                // ================================================

                if (messagingWindow.focusZone === messagingWindow.appZone) {
                    if (event.key === Qt.Key_Up) {
                        appSelector.keyboardActive = true;

                        appSelector.moveSelection(-1);

                        event.accepted = true;
                        return;
                    }

                    if (event.key === Qt.Key_Down) {
                        appSelector.keyboardActive = true;

                        appSelector.moveSelection(1);

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
                            messagingWindow.hideDiscord();

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
            // WhatsApp and Messenger are reserved for future Session-style adapters.
            // Do not show fake contacts or launch external browser windows.
            statusText: messagingWindow.xSelected ? messagingWindow.xError
                       : messagingWindow.activeAppIndex === 2 ? messageRouter.telegramStatus
                       : messagingWindow.providerAccessSelected
                           ? "NATIVE // " + messageRouter.accessBackendMode
                       : ""

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

            onSettingsOpenChanged: {
                if (settingsOpen && messagingWindow.menuOpen)
                    messagingWindow.focusAppSelector();
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

            // Discord keeps the normal contact panel instantiated underneath
            // Vesktop; discordMode only empties its inner contents.
            visible: messagingWindow.menuOpen && !providerAccessPanel.visible
                     && !messagingWindow.providerDesktopManaged

            discordMode: messagingWindow.externalSelected

            z: 2

            keyboardFocused: messagingWindow.focusZone === messagingWindow.contactZone

            // ----------------------------------------------------
            // ACTIVE BACKEND CONTACTS
            // ----------------------------------------------------

            conversations: messageRouter.conversations

            // ----------------------------------------------------
            // CONVERSATION CHANGE
            // ----------------------------------------------------

            onSelectedConversationChanged: {
                if (messagingWindow.nativeChatSelected && selectedConversation)
                    messageRouter.loadMessages(selectedConversation.id);
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
        // IN-MENU TELEGRAM ACCOUNT CONNECTION
        // ========================================================

        TelegramConnectPanel {
            id: telegramConnectPanel
            adapter: messageRouter.telegramBackend
            x: messagingWindow.appSelectorWidth + messagingWindow.contactListWidth
            y: 0
            width: Math.max(1, messagingContent.width - x)
            height: messagingContent.height
            visible: messagingWindow.menuOpen && messagingWindow.activeAppIndex === 2
                     && messageRouter.telegramNeedsSetup
            z: 2
        }

        // ========================================================
        // NON-NATIVE PROVIDER ACCESS // DESKTOP + WEB FALLBACKS
        // ========================================================

        ProviderAccessPanel {
            id: providerAccessPanel
            serviceIndex: messagingWindow.activeAppIndex
            backendMode: messageRouter.accessBackendMode
            backendDetail: messageRouter.accessBackendDetail
            x: messagingWindow.appSelectorWidth
            y: 0
            width: Math.max(1, messagingContent.width - x)
            height: messagingContent.height
            visible: messagingWindow.menuOpen && messagingWindow.providerAccessSelected
                     && !messagingWindow.providerWebOpen && !messagingWindow.providerDesktopManaged
            z: 2
            onBrowserRequested: function(serviceId) {
                messagingWindow.openProviderWeb(serviceId);
            }
            onDesktopDocked: function(serviceId) {
                if (!messagingWindow.menuOpen)
                    return;
                if ((serviceId === "signal" && messagingWindow.activeAppIndex !== 26)
                    || (serviceId === "viber" && messagingWindow.activeAppIndex !== 29)
                    || (serviceId === "wechat" && messagingWindow.activeAppIndex !== 27))
                    return;
                messagingWindow.providerDesktopService = serviceId;
                messagingWindow.providerDesktopManaged = true;
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

            // Discord keeps the normal chat panel instantiated underneath
            // Vesktop; discordMode only empties its inner contents.
            visible: messagingWindow.menuOpen && !telegramConnectPanel.visible
                     && !providerAccessPanel.visible
                     && !messagingWindow.providerDesktopManaged

            discordMode: messagingWindow.externalSelected

            z: 1

            // ----------------------------------------------------
            // ACTIVE CONVERSATION
            // ----------------------------------------------------

            conversation: messagingWindow.nativeChatSelected ? contactList.selectedConversation : null
            scopeId: messagingWindow.nativeChatSelected && conversation
                     ? messageRouter.serviceId + ":" + String(conversation.id) : ""
            sendEnabled: messageRouter.sendEnabled

            // ----------------------------------------------------
            // MESSAGES
            // ----------------------------------------------------

            messages: messagingWindow.nativeChatSelected && contactList.selectedConversation
                      && String(messageRouter.selectedConversationId) === String(contactList.selectedConversation.id)
                      ? messageRouter.messages : []

            // ----------------------------------------------------
            // LOADING
            // ----------------------------------------------------

            loading: messagingWindow.nativeChatSelected ? messageRouter.messagesLoading : false

            // ----------------------------------------------------
            // LOAD ERROR
            // ----------------------------------------------------

            error: messagingWindow.nativeChatSelected ? messageRouter.messagesError : ""

            // ----------------------------------------------------
            // SENDING
            // ----------------------------------------------------

            sending: messagingWindow.nativeChatSelected ? messageRouter.sending : false

            // ----------------------------------------------------
            // SEND ERROR
            // ----------------------------------------------------

            sendError: messagingWindow.nativeChatSelected ? messageRouter.sendError : ""

            // ----------------------------------------------------
            // SEND SUCCESS
            // ----------------------------------------------------

            sendSuccessSerial: messagingWindow.nativeChatSelected ? messageRouter.sendSuccessSerial : 0

            // ----------------------------------------------------
            // SEND MESSAGE
            // ----------------------------------------------------

            onSendRequested: function (conversationId, text) {
                if (messagingWindow.nativeChatSelected)
                    messageRouter.sendMessage(conversationId, text);
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
        if (!menuOpen)
            hideProviderDesktop();
        // Do not resume into a stale settings page after Social closes.
        // External-web fallbacks stay separate from each provider's native
        // unsupported status; reset without touching provider login sessions.
        providerWebOpen = false;
        appSelector.settingsOpen = false;
        setGeometryWatch(menuOpen);

        if (menuOpen) {
            messagingWindow.setGeometryWatch(true);

            // The BAR Sessions button opens the menu on Sessions.
            contactList.clearSelection();
            activeAppIndex = 0;
            appSelector.selectedIndex = 0;
            Qt.callLater(function() { appSelector.ensureValidSelection(); });

            messagingWindow.hideDiscord();
            messagingWindow.hideX();

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
            messagingWindow.hideX();

            contactList.clearSelection();
            activeAppIndex = 0;
            focusZone = appZone;
            keyboardFocus.focus = false;
            socialReady = false;
        }
    }
}
