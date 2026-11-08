import QtQuick
import QtQuick.Controls
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import qs.services.social
import "FinanceChassisPolicy.js" as FinanceChassisPolicy
import "../components"

// CAMERA M1 // Screenshot shutter + read-only picture gallery + a reversible,
// explicitly confirmed Desktop screenshot cleanup. Separate PanelWindow:
// Social, TV/Media and a native Zoom application may stay open independently.
PanelWindow {
    id: camera

    property bool menuOpen: false
    property bool busy: false
    property string pendingAction: ""
    property string activeView: "capture"
    property string feedback: "OPEN CAMERA // CAPTURE, GALLERY, OR CLEANUP"
    property var statusReport: null
    property var galleryFiles: []
    property int galleryTotal: 0
    property int galleryPageIndex: 0
    property bool galleryHasMore: false
    property bool galleryScanTruncated: false
    property bool galleryShotsOnly: false
    property string galleryMediaFilter: "all"
    property string galleryRequestedMediaFilter: "all"
    property bool recording: false
    property string recordingMode: ""
    property string webcamDevice: ""
    property string galleryCustomFolder: ""
    property string galleryRequestedQuery: ""
    property string galleryRequestedFolder: ""
    property bool galleryRequestedShotsOnly: false
    property string selectedPath: ""
    property var selectedRecord: null
    property var trashPreview: null
    property var selectedTrashPreview: null
    property string lastTrashReceipt: ""
    // One Camera deletion queue used by Batch now and future Swipe/Hunt
    // presentations. Marking files is never equivalent to moving them.
    // Mass deletion belongs to CLEANUP. BATCH and SWIPE share this queue;
    // neither input mode can move files without an explicit backend plan.
    property string cleanupTechnique: "batch"
    readonly property bool batchMode: activeView === "cleanup"
                                      && cleanupTechnique !== "desktop"
    property string cleanupSearchQuery: ""
    property string cleanupCustomFolder: ""
    property string cleanupMediaFilter: "all"
    property string galleryRequestedView: "gallery"
    property var batchPaths: []
    property var batchPreview: null
    property string batchReviewKey: ""
    property string batchReceipt: ""
    property int swipeIndex: 0
    property var swipeHistory: []
    property string captureMode: "region"
    // Read Social's active identity and provider alias metadata, not login state.
    readonly property var zoomSocialIdentity: SocialIdentityStore.snapshot
    readonly property string zoomIdentityId: String(zoomSocialIdentity.activeId || "")
    readonly property var zoomAccountNames:
        SocialAccountDetailsStore.accountNamesFor(zoomIdentityId, "zoom")
    property string selectedZoomAccountId: ""
    property var zoomClientStatus: null
    property string zoomInternetState: "NOT_CHECKED"
    property string zoomServiceState: "NOT_CHECKED"
    property string zoomLastChecked: ""
    property bool zoomEnterQueued: false
    // Camera M4d: X/Instagram-style private browser guest in a measured bay.
    // Only a verified native actor/viewport enables the alpha + input hole.
    property bool zoomWebDocked: false
    // A previously verified guest remains visually presented while Sway
    // repositions it. The input cutout STILL requires zoomWebDocked, and a
    // missing/unverified/failed actor clears this presentation latch.
    property bool zoomWebVisualHeld: false
    property bool zoomWebBusy: false
    property string zoomWebState: "NOT_STARTED"
    // Typed Sway rectangle deltas only; never expose browser titles or logins.
    property var zoomWebRectDelta: null
    property string zoomWebIdentity: "identity-1"
    // Camera's Zoom guest has an independent frame-owned viewport. Do not
    // derive compositor placement from the shared Capture/Gallery page.
    // A single measured rectangle feeds host placement and the input hole.
    // Browser gets near-full-width frame while the header's button row
    // retains its own comfortable inset; no independent Sway coordinates.
    readonly property int zoomWebEdgeInset: 2
    readonly property int zoomBayInset: Math.max(0, Math.round(zoomViewport.x))
    readonly property int zoomBayTop: Math.max(0, Math.round(zoomViewport.y))
    // The previous 4px guest-only bottom clearance was painted BLACK
    // inside Camera's otherwise transparent Zoom frame, visibly making
    // the page end before the lower border. Transfer those same four pixels
    // to Zoom's enclosing frame instead: the guest's measured target size
    // is UNCHANGED, but the outer bottom border follows the guest again.
    // Preserve the 1px standard frame inset, top, controls and Sway safety.
    readonly property int zoomBayBottom: 1
    readonly property int zoomFrameBottomFit: 16
    readonly property int zoomGuestBottomClearance: 0
    // Keep #1505's raised compact controls and common 3px deck spacing.
    // The first 8px rise improved all three sizes; a subsequent native screenshot
    // calls for another 5px. Rise is now 13px total from the #1505 deck.
    // Raise only the browser actor/viewport, retaining its bottom.
    // A short visual underlap is covered by the opaque Camera mode-row matte;
    // the input hole still begins at the real deck bottom, never in buttons.
    readonly property int zoomDeckGap: 3
    readonly property int zoomBrowserRise: 13
    readonly property int zoomControlDeckBottom: Math.max(0, Math.round(
        cameraBodyColumn.y + cameraModes.y + cameraModes.height))
    readonly property int zoomBayWidth: Math.max(0, Math.round(zoomViewport.width))
    readonly property int zoomBayHeight: Math.max(0, Math.round(zoomViewport.height))
    // Sway measured the browser at 92,126 718x514, exactly the old
    // 8px right / 14px up / 16px narrower / 28px shorter adjustment.
    // Those trims, not workspace offset, caused the visible gap.
    // The launcher, live follower and input cutout share this untrimmed
    // viewport rectangle. Host coordinates remain output-relative until
    // converted to absolute Sway coordinates by the existing host.
    readonly property int zoomActorLeft: zoomBayInset
    readonly property int zoomActorTop: zoomBayTop
    readonly property int zoomActorWidth: zoomBayWidth
    readonly property int zoomActorHeight: zoomBayHeight
    // The mode row owns its full button height. No guest overlap into
    // Camera's controls; compact chassis gives the web body room below.
    // The browser can sit behind Camera chrome, but its input cutout must
    // never cut through the row of live Camera mode buttons.
    readonly property int zoomInputTop: Math.max(
        zoomActorTop, zoomControlDeckBottom)
    readonly property int zoomInputHeight: Math.max(
        0, zoomActorHeight - (zoomInputTop - zoomActorTop))
    property bool zoomWebNeedsRealign: false
    property int zoomFollowRevision: 0

    function sendZoomFollowTarget() {
        if (!zoomFollowProcess.running || !menuOpen || activeView !== "zoom")
            return false;
        zoomFollowRevision++;
        zoomFollowProcess.write(JSON.stringify({
            op: "target", revision: zoomFollowRevision,
            output: zoomWebOutput,
            x: Math.round(camera.margins.left + camera.glowGutter + zoomActorLeft),
            y: Math.round(camera.frameTopInset + zoomActorTop),
            width: zoomActorWidth, height: zoomActorHeight
        }) + "\n");
        return true;
    }

    function consumeZoomFollow(raw) {
        var reply = null;
        try { reply = JSON.parse(String(raw || "")); } catch (e) {}
        if (!reply || reply.kind !== "zoom-web-follow"
                || !menuOpen || activeView !== "zoom"
                || Number(reply.revision) !== zoomFollowRevision)
            return;
        const aligned = reply.aligned === true && reply.state === "ALIGNED";
        zoomWebDocked = aligned;
        if (aligned) {
            zoomWebVisualHeld = true;
        } else if (reply.state === "MISSING" || reply.state === "UNVERIFIED"
                   || reply.state === "FAILED") {
            // No stale browser should remain exposed on loss of trust.
            zoomWebVisualHeld = false;
        }
        // CHECKING/MISALIGNED during an ordinary resize keep the already
        // authenticated actor visually present, but with input closed.
        zoomWebState = aligned ? "WEB_APP_DOCKED"
                     : "FOLLOWER // " + String(reply.state || "UNVERIFIED");
    }

    function scheduleZoomWebRealign() {
        if (!menuOpen || activeView !== "zoom")
            return;
        // Camera remains the geometry leader, just as Social is before
        // its browser's initial dock. The physical Sway actor follows the
        // latest viewport even when QML geometry did not trigger another
        // one-shot launch.
        zoomWebDocked = false;
        if (zoomFollowProcess.running) {
            // QML emits separate x/y/width/height signals while resizing.
            // Coalesce those before requesting physical Sway movement.
            zoomWebFollowTargetDebounce.restart();
            return;
        }
        if (zoomWebBusy) {
            // Never accept a stale geometry verification after a resize.
            zoomWebNeedsRealign = true;
            return;
        }
        zoomWebRealign.restart();
    }
    readonly property string zoomWebOutput: camera.screen ? String(camera.screen.name || "") : ""
    function zoomWebArgs(action) {
        return ["python3", "-I", "-B", Quickshell.shellPath("scripts/camera/ZoomWebHost.py"),
                action, "--identity", zoomWebIdentity,
                "--output", zoomWebOutput,
                "--x", String(camera.margins.left + camera.glowGutter + zoomActorLeft),
                "--y", String(camera.frameTopInset + zoomActorTop),
                "--width", String(zoomActorWidth), "--height", String(zoomActorHeight)];
    }
    function enterZoomWeb() {
        if (!menuOpen || activeView !== "zoom" || zoomWebBusy)
            return false;
        if (zoomFollowProcess.running) {
            zoomWebDocked = false;
            zoomWebFollowTargetDebounce.restart();
            return true;
        }
        zoomWebDocked = false;
        zoomWebVisualHeld = false;
        zoomWebRectDelta = null;
        zoomWebNeedsRealign = false;
        zoomWebBusy = true;
        zoomWebState = "LAUNCHING_WEB_APP";
        zoomWebProcess.exec(zoomWebArgs("enter"));
        return true;
    }
    function hideZoomWeb() {
        zoomWebDocked = false;  // input cutout closes before guest is hidden
        zoomWebVisualHeld = false;
        zoomWebFollowTargetDebounce.stop();
        zoomFollowProcess.running = false;
        zoomWebState = "HIDDEN";
        zoomWebHideProcess.exec(zoomWebArgs("hide"));
    }
    function consumeZoomWeb(raw) {
        zoomWebBusy = false;
        var reply = null;
        try { reply = JSON.parse(String(raw || "")); }
        catch (e) {}
        if (!menuOpen || activeView !== "zoom") {
            hideZoomWeb();
            return;
        }
        if (zoomWebNeedsRealign) {
            // Host checked an older rectangle. Reverify the existing guest
            // without clearing the visual latch during a normal resize.
            zoomWebNeedsRealign = false;
            zoomWebDocked = false;
            zoomWebState = "REALIGNING_WEB_APP";
            zoomWebRealign.restart();
            return;
        }
        const initiallyDocked = !!(reply && reply.ok === true && reply.docked === true);
        zoomWebDocked = false; // follower must verify the current viewport
        zoomWebRectDelta = reply && Array.isArray(reply.rectDelta)
            && reply.rectDelta.length === 4 ? reply.rectDelta : null;
        zoomWebState = initiallyDocked ? "FOLLOWER // STARTING"
                        : "WEB_HOST_UNAVAILABLE // " + String(reply && (reply.error || reply.state) || "NO_RESULT");
        if (initiallyDocked) {
            // First verified alignment is still established by the follower.
            zoomFollowProcess.running = true;
            feedback = "ZOOM WEB // CONTINUOUS SIZE AND POSITION FOLLOW";
        } else {
            zoomWebVisualHeld = false;
            feedback = "ZOOM WEB // " + zoomWebState;
        }
    }
    onZoomActorLeftChanged: scheduleZoomWebRealign()
    onZoomActorTopChanged: scheduleZoomWebRealign()
    onZoomActorWidthChanged: scheduleZoomWebRealign()
    onZoomActorHeightChanged: scheduleZoomWebRealign()
    onZoomWebOutputChanged: scheduleZoomWebRealign()
    onDockCenterXChanged: scheduleZoomWebRealign()
    property var zoomLaunchObservation: null
    property string zoomLaunchState: "NOT_CHECKED"
    property string zoomLaunchMessage: "LAUNCH // NOT CHECKED"
    // Missing installations must show an actionable setup, not a disabled button.
    property bool zoomSetupVisible: false
    // Explicit two-click installer gate; cleared on closing or changing modes.
    property string zoomInstallChoice: ""
    property string zoomInstallNotice: ""
    onZoomIdentityIdChanged: selectedZoomAccountId = ""
    // The native slurp overlay owns the region drag; Camera unmaps while it runs.
    property bool nativeRegionSelecting: false
    // Finance sizing in medium/fullscreen; the compact deck gets enough
    // width and height to contain normal-size buttons and the Zoom browser.
    // One mapped PanelWindow persists across all size changes.
    property string chassisLevel: "compact"
    property real dockCenterX: 0
    readonly property int glowGutter: 12
    readonly property int frameTopInset: 9
    readonly property int bottomScreenGap: 8
    readonly property int viewportWidth:
        camera.screen && camera.screen.width > 0 ? camera.screen.width : 2560
    readonly property int viewportHeight:
        camera.screen && camera.screen.height > 0 ? camera.screen.height : 1440
    readonly property var financeSize: FinanceChassisPolicy.frame(
        chassisLevel, viewportWidth, viewportHeight,
        glowGutter, frameTopInset, bottomScreenGap)
    readonly property int frameWidth:
        chassisLevel === "compact"
        ? Math.max(1, Math.min(784, viewportWidth - 2 * glowGutter))
        : financeSize.width
    // Finance supplies the expanded/fullscreen *content* height. Camera's
    // Zoom mode also contains a header, divider and four-button deck; it
    // previously deducted that chrome from the browser's 900px budget.
    // Measure the actual live deck rather than stacking guessed Y offsets.
    // Only Zoom gets the extra height; other modes retain Finance sizing.
    readonly property int zoomDeckReserve: Math.max(
        0, zoomControlDeckBottom + zoomDeckGap + zoomBayBottom)
    readonly property int availableFrameHeight: Math.max(
        1, viewportHeight - frameTopInset - bottomScreenGap)
    // Expanded has room to add the mode deck above Finance's 900px content.
    // Fullscreen does NOT: on DP-3 the Sway workarea begins 82px below
    // output Y=0, while viewportHeight still reports the full 1440px.
    // Extending the 1345px Finance fullscreen frame to 1423px made
    // ZoomWebHost reject its physical rectangle as OUTSIDE_WORKAREA.
    // Preserve Finance's fullscreen budget; keep expanded's deck reserve.
    // Finance/chassis baseline is unchanged for Capture, Gallery, Cleanup.
    // Zoom's 16px-only frame reduction includes the former 4px guest
    // clearance. This moves the black-painted frame bottom UP without
    // changing the physical browser's height in any chassis.
    readonly property int frameHeightBase:
        chassisLevel === "compact"
        ? Math.max(1, Math.min(699, availableFrameHeight))
        : camera.activeView === "zoom" && chassisLevel === "expanded"
          ? Math.min(availableFrameHeight,
                     financeSize.height + zoomDeckReserve)
          : financeSize.height
    readonly property int frameHeight: Math.max(
        1, frameHeightBase
           - (camera.activeView === "zoom" ? zoomFrameBottomFit : 0))
    readonly property int gutter: glowGutter
    function expandChassis() {
        chassisLevel = FinanceChassisPolicy.step(chassisLevel, 1);
    }
    function collapseChassis() {
        chassisLevel = FinanceChassisPolicy.step(chassisLevel, -1);
    }
    // Filename filtering and pagination run against the complete backend
    // inventory, not just the first page of 150 results.
    readonly property var filteredFiles: galleryFiles

    function toggle() {
        // Do not remap the Camera layer above the native selector in progress.
        if (!nativeRegionSelecting)
            menuOpen = !menuOpen;
    }

    onMenuOpenChanged: {
        if (!menuOpen) {
            zoomInstallChoice = "";
            zoomEnterQueued = false;
            if (activeView === "zoom")
                hideZoomWeb();
            return;
        }
        if (activeView === "zoom") {
            // Reopening the Camera on Zoom also restores the native experience.
            openZoomMode();
        } else if (statusReport === null && !busy) {
            run("status", ["status"]);
        }
    }

    onBusyChanged: {
        if (!busy && zoomEnterQueued && menuOpen && activeView === "zoom") {
            zoomEnterQueued = false;
            Qt.callLater(function() {
                if (!camera.busy && camera.menuOpen && camera.activeView === "zoom")
                    camera.run("zoomEnter", ["zoom-enter"]);
            });
        }
    }

    function fileUrl(path) {
        // Encode each path segment; raw "#" or "?" in filenames must not
        // become URL fragments or queries and break thumbnails.
        return "file://" + String(path || "").split("/")
                .map(function(segment) { return encodeURIComponent(segment); }).join("/");
    }

    function run(action, argumentsList) {
        if (busy)
            return false;
        busy = true;
        pendingAction = action;
        feedback = "CAMERA // " + action.toUpperCase() + " REQUESTED";
        cameraProcess.exec([
            "python3", "-I", "-B",
            Quickshell.shellPath("scripts/camera/camera_cli.py")
        ].concat(argumentsList));
        return true;
    }

    function loadGallery(append, targetView) {
        if (busy)
            return false;
        // The same bounded inventory is displayed independently in Gallery
        // (viewing) or Cleanup (mass selection). Do not force navigation.
        const destination = targetView === "cleanup" || targetView === "gallery"
                            ? targetView
                            : activeView === "cleanup" ? "cleanup" : "gallery";
        activeView = destination;
        const cleaning = destination === "cleanup";
        const nextPage = append === true ? galleryPageIndex + 1 : 0;
        if (append !== true) {
            selectedPath = "";
            selectedRecord = null;
            selectedTrashPreview = null;
            batchPaths = [];
            batchPreview = null;
            batchReviewKey = "";
            swipeIndex = 0;
            swipeHistory = [];
            galleryFiles = [];
        } else if (!galleryHasMore) {
            return false;
        }
        galleryRequestedView = destination;
        galleryRequestedQuery = cleaning ? cleanupSearchQuery.trim()
                                         : gallerySearch.text.trim();
        galleryRequestedFolder = cleaning ? cleanupCustomFolder : galleryCustomFolder;
        galleryRequestedShotsOnly = cleaning ? false : galleryShotsOnly;
        galleryRequestedMediaFilter = cleaning ? cleanupMediaFilter : galleryMediaFilter;
        return run("gallery", [
            "gallery",
            "--page", String(nextPage),
            "--query", galleryRequestedQuery,
            "--folder", galleryRequestedFolder,
            "--media-filter", galleryRequestedMediaFilter
        ].concat(galleryRequestedShotsOnly ? ["--shots-only"] : []));
    }

    function selectImage(record) {
        selectedRecord = record;
        selectedPath = String(record && record.path || "");
        selectedTrashPreview = null;
        lastTrashReceipt = "";
        zoomViewer.reset();
    }

    function previewSelectedTrash() {
        if (busy || !selectedPath)
            return false;
        selectedTrashPreview = null;
        return run("previewSelected", ["preview-selected", selectedPath]);
    }

    function confirmSelectedTrash() {
        const plan = selectedTrashPreview;
        if (busy || !plan || !plan.planId || plan.path !== selectedPath)
            return false;
        selectedTrashPreview = null;
        return run("trashSelected", ["trash-selected", plan.planId, "MOVE_TO_TRASH"]);
    }

    // The queue is presentation-neutral. Batch checkboxes, Swipe and Hunt
    // must all mark/unmark here, NEVER call gio directly.
    function batchContains(path) {
        return batchPaths.indexOf(String(path || "")) >= 0;
    }

    function batchToggle(record) {
        if (!batchMode || busy || !record || !record.path)
            return false;
        const path = String(record.path);
        const next = batchPaths.slice();
        const index = next.indexOf(path);
        if (index >= 0)
            next.splice(index, 1);
        else if (next.length < 500)
            next.push(path);
        else {
            feedback = "BATCH // 500 FILE LIMIT // REVIEW OR CLEAR";
            return false;
        }
        batchPaths = next;
        batchPreview = null;
        batchReviewKey = "";
        swipeHistory = [];
        return true;
    }

    function batchSelectLoaded(nameNeedle) {
        if (!batchMode || busy)
            return false;
        const needle = String(nameNeedle || "").trim().toLowerCase();
        const next = batchPaths.slice();
        for (let i = 0; i < galleryFiles.length; i++) {
            const record = galleryFiles[i];
            if (!record || !record.path || (needle &&
                    String(record.name || "").toLowerCase().indexOf(needle) < 0))
                continue;
            if (next.indexOf(record.path) < 0) {
                if (next.length >= 500) {
                    feedback = "BATCH // 500 FILE LIMIT // REVIEW OR CLEAR";
                    break;
                }
                next.push(record.path);
            }
        }
        batchPaths = next;
        batchPreview = null;
        batchReviewKey = "";
        swipeHistory = [];
        return true;
    }

    function batchClear() {
        if (busy) return false;
        batchPaths = [];
        batchPreview = null;
        batchReviewKey = "";
        swipeHistory = [];
        return true;
    }

    function swipeDecide(action) {
        if (busy || activeView !== "cleanup" || cleanupTechnique !== "swipe"
                || swipeIndex >= galleryFiles.length
                || ["trash", "keep", "skip"].indexOf(action) < 0)
            return false;
        const record = galleryFiles[swipeIndex];
        if (!record || !record.path)
            return false;
        const previousQueue = batchPaths.slice();
        const next = previousQueue.slice();
        const index = next.indexOf(record.path);
        if (action === "trash" && index < 0) {
            if (next.length >= 500) {
                feedback = "SWIPE // 500 FILE LIMIT // REVIEW OR CLEAR";
                return false;
            }
            next.push(record.path);
        } else if (action === "keep" && index >= 0)
            next.splice(index, 1);
        const history = swipeHistory.slice();
        history.push({index: swipeIndex, paths: previousQueue, decision: action});
        swipeHistory = history;
        swipeIndex += 1;
        batchPaths = next;
        batchPreview = null;
        batchReviewKey = "";
        feedback = "SWIPE // " + action.toUpperCase()
                   + " // " + swipeIndex + "/" + galleryFiles.length
                   + " // QUEUED " + batchPaths.length;
        return true;
    }

    function swipeUndo() {
        if (busy || activeView !== "cleanup" || cleanupTechnique !== "swipe"
                || swipeHistory.length === 0)
            return false;
        const history = swipeHistory.slice();
        const last = history.pop();
        swipeHistory = history;
        swipeIndex = last.index;
        batchPaths = last.paths.slice();
        batchPreview = null;
        batchReviewKey = "";
        feedback = "SWIPE // UNDID " + last.decision.toUpperCase();
        return true;
    }

    function previewBatchTrash() {
        if (busy || !batchMode || batchPaths.length === 0)
            return false;
        batchPreview = null;
        batchReviewKey = JSON.stringify(batchPaths);
        return run("previewBatch", ["preview-batch", batchReviewKey,
                                    "--folder", cleanupCustomFolder]);
    }

    function confirmBatchTrash() {
        const plan = batchPreview;
        if (busy || !batchMode || !plan || !plan.planId
                || Number(plan.count) !== batchPaths.length
                || batchReviewKey !== JSON.stringify(batchPaths))
            return false;
        batchPreview = null;
        return run("trashBatch", ["trash-batch", plan.planId, "MOVE_TO_TRASH"]);
    }

    function prepareCapture(mode) {
        if (busy || nativeRegionSelecting
                || (mode !== "region" && mode !== "focused" && mode !== "all"))
            return false;
        captureMode = mode;
        if (mode === "region") {
            // The one click hands control to the native Wayland selector.
            // Unmap our persistent overlay so it cannot cover slurp or
            // intercept its pointer/keyboard focus.
            nativeRegionSelecting = true;
            feedback = "REGION // DRAG TO SELECT // RELEASE TO SAVE // ESC CANCELS";
        } else {
            feedback = "CAMERA // HIDING PANEL BEFORE SHUTTER";
        }
        menuOpen = false;
        shutterDelay.restart();
        return true;
    }

    function openZoomMode() {
        activeView = "zoom";
        zoomInstallChoice = "";
        // Zoom Web App is the PRIMARY app surface, as with Social X/Instagram.
        // It owns its login/calls. Native Zoom is an optional fallback below.
        enterZoomWeb();
    }

    function prepareZoomInstall(choice) {
        if (busy || (choice !== "official-rpm" && choice !== "community-flatpak"))
            return false;
        zoomInstallChoice = choice;
        zoomInstallNotice = "";
        Qt.callLater(function() {
            if (camera.zoomInstallChoice === choice)
                zoomPage.contentY = Math.max(0, zoomPage.contentHeight - zoomPage.height);
        });
        return true;
    }

    function confirmZoomInstall() {
        const choice = zoomInstallChoice;
        if (busy || (choice !== "official-rpm" && choice !== "community-flatpak"))
            return false;
        const started = run("zoomInstall", [
            "zoom-install", choice, "CONFIRM_ZOOM_INSTALL"
        ]);
        if (started) {
            zoomInstallChoice = "";
            zoomInstallNotice = choice === "community-flatpak"
                ? "INSTALL IN PROGRESS // USER FLATPAK // KEEP CAMERA RUNNING"
                : "INSTALL IN PROGRESS // OFFICIAL RPM // AUTH MAY BE REQUIRED";
        }
        return started;
    }

    function launchZoomClient() {
        zoomLaunchState = "CHECKING";
        zoomLaunchMessage = "ZOOM // STARTING CLIENT // VERIFYING WINDOW";
        return run("zoomOpen", ["zoom-open"]);
    }

    function checkZoomWindow() {
        return run("zoomLaunchCheck", ["zoom-launch-check"]);
    }

    function openZoomDirectly() {
        if (busy || !zoomClientStatus || !zoomClientStatus.available)
            return false;
        zoomLaunchState = "CHECKING";
        zoomLaunchMessage = "ZOOM // OPEN OR FOCUS REQUESTED";
        return run("zoomActivate", ["zoom-activate"]);
    }

    function webcamPhoto() {
        return run("webcamPhoto", ["webcam-photo", "--device", webcamDevice]);
    }

    function startRecording(mode) {
        if (busy || recording) return false;
        return run("recordStart", ["record-start", mode, "--device", webcamDevice]);
    }

    function stopRecording() {
        if (busy || !recording) return false;
        return run("recordStop", ["record-stop"]);
    }

    function previewCleanup() {
        trashPreview = null;
        return run("preview", ["preview-trash"]);
    }

    function confirmCleanup() {
        const plan = trashPreview;
        if (busy || !plan || !plan.planId || plan.count <= 0)
            return false;
        // This action can move files, unlike gallery and preview. Never
        // invoke it from a timer, page change, or automatic action.
        const id = plan.planId;
        trashPreview = null;
        return run("trash", ["trash", id, "MOVE_TO_TRASH"]);
    }

    function consume(raw) {
        const action = pendingAction;
        if (!action)
            return;
        pendingAction = "";
        busy = false;
        // Restore the Camera surface only after slurp has exited, including
        // cancel and backend-error paths.
        if (action === "capture")
            nativeRegionSelecting = false;
        let payload = null;
        try { payload = JSON.parse(String(raw || "").trim()); }
        catch (error) {
            feedback = "CAMERA // INVALID BACKEND RESPONSE";
            if (action === "capture")
                menuOpen = true;
            return;
        }
        if (!payload || payload.ok !== true) {
            if (action === "zoomOpen" || action === "zoomActivate") {
                zoomLaunchCheckTimer.stop();
                zoomLaunchState = "FAILED";
                zoomLaunchMessage = payload
                    && payload.error === "ZOOM_START_EXITED_NONZERO"
                    ? "ZOOM // PROCESS EXITED WITH ERROR "
                      + String(payload.exitCode || "UNKNOWN")
                      + " // TRY TERMINAL COMMAND BELOW"
                    : "ZOOM // LAUNCH FAILED // CHECK TERMINAL DIAGNOSTICS";
            }
            if (action === "zoomInstall") {
                const error = String(payload && payload.error || "INSTALL_UNAVAILABLE");
                zoomInstallChoice = "";
                zoomSetupVisible = true;
                zoomInstallNotice = error === "ZOOM_RPM_NOT_DOWNLOADED"
                    ? "RPM NOT FOUND // DOWNLOAD OFFICIAL FEDORA RPM TO ~/Downloads/"
                    : error === "ZOOM_RPM_SIGNATURE_UNVERIFIED"
                      ? "RPM SIGNATURE NOT VERIFIED // IMPORT ZOOM'S OFFICIAL KEY FIRST"
                      : error === "RPM_INSTALL_TIMEOUT_CHECK_DEPLOYMENT"
                        || error === "FLATPAK_INSTALL_TIMEOUT_CHECK_STATUS"
                        ? "INSTALL STATUS UNCERTAIN // RECHECK BEFORE RETRYING"
                        : "INSTALL FAILED // " + error;
            }
            if (action === "zoomOpen"
                    && payload && payload.error === "ZOOM_CLIENT_NOT_INSTALLED") {
                zoomClientStatus = {available: false, client: "none"};
                zoomSetupVisible = true;
                feedback = "ZOOM // CLIENT NOT INSTALLED // SEE SETUP OPTIONS";
                return;
            }
            feedback = "CAMERA // " + String(payload && payload.error || "ACTION_FAILED");
            if (action === "capture")
                menuOpen = true;
            return;
        }
        if (action === "zoomEnter") {
            zoomClientStatus = {
                available: payload.installed === true,
                client: payload.client || "none",
                installation: payload.installation || "none"
            };
            zoomSetupVisible = payload.installed !== true;
            if (payload.launch === "NOT_INSTALLED") {
                zoomLaunchState = "NOT_INSTALLED";
                zoomLaunchMessage = "ZOOM // NOT INSTALLED // USE DOWNLOAD ABOVE";
            } else if (payload.launch === "FAILED") {
                zoomLaunchState = "FAILED";
                zoomLaunchMessage = "ZOOM // START FAILED // "
                                  + String(payload.launchError || "UNAVAILABLE");
            } else if (payload.launch === "ALREADY_RUNNING") {
                zoomLaunchState = payload.windowState === "VISIBLE"
                    ? "VISIBLE" : payload.windowState === "OTHER_WORKSPACE"
                      ? "OTHER_WORKSPACE" : "RUNNING_NO_WINDOW";
                zoomLaunchMessage = zoomLaunchState === "VISIBLE"
                    ? "ZOOM // VISIBLE WINDOW FOUND"
                    : zoomLaunchState === "OTHER_WORKSPACE"
                      ? "ZOOM // WINDOW ON ANOTHER WORKSPACE"
                      : "ZOOM // PROCESS RUNNING // NO WINDOW DETECTED";
            } else {
                zoomLaunchState = "UNVERIFIED";
                zoomLaunchMessage = "ZOOM // STARTED REQUEST // VERIFYING WINDOW";
            }
            feedback = zoomLaunchMessage;
            Qt.callLater(function() {
                if (!camera.busy && camera.menuOpen && camera.activeView === "zoom")
                    camera.run("zoomConnectivity", ["zoom-connectivity"]);
            });
        } else if (action === "zoomConnectivity") {
            zoomInternetState = payload.internet;
            zoomServiceState = payload.zoomService;
            zoomLastChecked = payload.checkedAt || "";
            if (camera.zoomLaunchState !== "NOT_INSTALLED")
                zoomLaunchCheckTimer.restart();
        } else if (action === "zoomInstall") {
            zoomInstallChoice = "";
            if (payload.restartRequired) {
                zoomInstallNotice = "OFFICIAL ZOOM RPM STAGED // REBOOT REQUIRED";
                feedback = "ZOOM // SYSTEM DEPLOYMENT STAGED // NO AUTOMATIC REBOOT";
            } else {
                zoomInstallNotice = "ZOOM FLATPAK INSTALLED // RECHECKING";
                feedback = "ZOOM // USER FLATPAK INSTALLED";
                Qt.callLater(function() {
                    if (!camera.busy && camera.activeView === "zoom")
                        camera.run("zoomStatus", ["zoom-status"]);
                });
            }
        } else if (action === "zoomStatus") {
            zoomClientStatus = payload;
            zoomSetupVisible = !payload.available;
            feedback = payload.available ? "ZOOM // CLIENT DETECTED // ACCOUNT UNVERIFIED"
                                         : "ZOOM // NOT INSTALLED // SETUP OPTIONS BELOW";
            if (payload.available)
                Qt.callLater(function() {
                    if (!camera.busy && camera.menuOpen && camera.activeView === "zoom")
                        camera.run("zoomEnter", ["zoom-enter"]);
                });
        } else if (action === "zoomOpen") {
            zoomLaunchState = "UNVERIFIED";
            zoomLaunchMessage = "ZOOM // LAUNCH SUBMITTED // WINDOW NOT VERIFIED YET";
            feedback = "ZOOM // START COMMAND ACCEPTED // CHECKING WINDOW";
            zoomLaunchCheckTimer.restart();
        } else if (action === "zoomActivate") {
            if (payload.activation === "WINDOW_FOCUSED") {
                zoomLaunchState = "VISIBLE";
                zoomLaunchMessage = "ZOOM // EXISTING WINDOW FOCUSED";
            } else {
                zoomLaunchState = "UNVERIFIED";
                zoomLaunchMessage = "ZOOM // OPEN REQUESTED // WINDOW NOT YET CONFIRMED";
                zoomLaunchCheckTimer.restart();
            }
            feedback = zoomLaunchMessage;
        } else if (action === "zoomLaunchCheck") {
            zoomLaunchObservation = payload;
            if (payload.windowState === "VISIBLE") {
                zoomLaunchState = "VISIBLE";
                zoomLaunchMessage = "ZOOM // WINDOW VISIBLE // READY TO USE";
            } else if (payload.windowState === "OTHER_WORKSPACE") {
                zoomLaunchState = "OTHER_WORKSPACE";
                zoomLaunchMessage = "ZOOM // WINDOW FOUND ON ANOTHER WORKSPACE";
            } else if (payload.flatpakRunning === true) {
                zoomLaunchState = "RUNNING_NO_WINDOW";
                zoomLaunchMessage = "ZOOM // FLATPAK RUNNING // WINDOW NOT DETECTED";
            } else if (payload.windowState === "UNKNOWN") {
                zoomLaunchState = "UNKNOWN";
                zoomLaunchMessage = "ZOOM // COMPOSITOR WINDOW CHECK UNAVAILABLE";
            } else {
                zoomLaunchState = "NOT_FOUND";
                zoomLaunchMessage = "ZOOM // NO WINDOW FOUND // SEE TERMINAL DIAGNOSTICS";
            }
            feedback = zoomLaunchMessage;
        } else if (action === "status") {
            statusReport = payload;
            recording = payload.recording && payload.recording.recording === true;
            recordingMode = recording ? payload.recording.mode : "";
            feedback = "CAMERA // TOOL STATUS READY";
        } else if (action === "recordStart") {
            recording = true;
            recordingMode = payload.mode;
            feedback = "RECORDING // " + payload.mode.toUpperCase() + " // PRESS STOP TO SAVE";
        } else if (action === "recordStop") {
            recording = false;
            recordingMode = "";
            feedback = "RECORDING SAVED // " + payload.name;
            activeView = "gallery";
            galleryMediaFilter = "videos";
            Qt.callLater(function() { camera.loadGallery(false); });
        } else if (action === "webcamPhoto") {
            feedback = "WEBCAM PHOTO SAVED // " + payload.name;
            activeView = "gallery";
            galleryMediaFilter = "webcam";
            Qt.callLater(function() { camera.loadGallery(false); });
        } else if (action === "capture") {
            feedback = "CAPTURE SAVED // " + payload.name;
            menuOpen = true;
            activeView = "gallery";
            Qt.callLater(function() { camera.loadGallery(); });
        } else if (action === "gallery") {
            const page = Number(payload.page || 0);
            galleryFiles = page > 0
                ? galleryFiles.concat(payload.files || [])
                : (payload.files || []);
            galleryPageIndex = page;
            galleryTotal = Number(payload.total || 0);
            galleryHasMore = payload.hasMore === true;
            galleryScanTruncated = payload.truncated === true;
            feedback = "GALLERY // " + galleryFiles.length + "/" + galleryTotal
                       + (galleryScanTruncated ? " // SCAN LIMIT REACHED" : "");
            // If the user typed while scanning, run the newest query next.
            if ((galleryRequestedView === "cleanup"
                  ? cleanupSearchQuery.trim() !== galleryRequestedQuery
                     || cleanupCustomFolder !== galleryRequestedFolder
                     || cleanupMediaFilter !== galleryRequestedMediaFilter
                  : gallerySearch.text.trim() !== galleryRequestedQuery
                     || galleryCustomFolder !== galleryRequestedFolder
                     || galleryShotsOnly !== galleryRequestedShotsOnly
                     || galleryMediaFilter !== galleryRequestedMediaFilter))
                gallerySearchDebounce.restart();
        } else if (action === "previewBatch") {
            if (batchMode && activeView === "cleanup"
                    && batchReviewKey === JSON.stringify(batchPaths)
                    && cleanupCustomFolder === galleryRequestedFolder) {
                batchPreview = payload;
                feedback = "BATCH // REVIEW " + payload.count
                           + " FILES // NO FILES MOVED";
            }
        } else if (action === "trashBatch") {
            batchReceipt = "BATCH TRASH // MOVED " + payload.moved
                           + " // SKIPPED " + payload.skipped
                           + " // FAILED " + payload.failed;
            feedback = batchReceipt;
            batchPaths = [];
            batchReviewKey = "";
            batchPreview = null;
            swipeIndex = 0;
            swipeHistory = [];
            Qt.callLater(function() { camera.loadGallery(false, "cleanup"); });
        } else if (action === "previewSelected") {
            if (payload.path === selectedPath) {
                selectedTrashPreview = payload;
                feedback = "CONFIRM // MOVE ONE IMAGE TO TRASH";
            }
        } else if (action === "trashSelected") {
            selectedPath = "";
            selectedRecord = null;
            selectedTrashPreview = null;
            lastTrashReceipt = "MOVED TO TRASH // " + payload.name;
            feedback = lastTrashReceipt;
            // Always refresh after the confirmed file is moved.
            Qt.callLater(function() { camera.loadGallery(false); });
        } else if (action === "preview") {
            trashPreview = payload;
            feedback = "PREVIEW // " + payload.count
                       + " SCREENSHOT-LIKE DESKTOP IMAGES // NOTHING MOVED";
        } else if (action === "trash") {
            feedback = "TRASH // MOVED " + payload.moved
                       + " // SKIPPED " + payload.skipped
                       + " // FAILED " + payload.failed;
            // Keep the receipt visible in the cleanup view.
        }
    }

    implicitWidth: frameWidth + 2 * glowGutter
    implicitHeight: frameHeight + frameTopInset + bottomScreenGap
    anchors { top: true; bottom: false; left: true; right: false }
    // All three modes' visible frames begin at y=9, matching Finance and
    // other standard menus rather than the former y=103 Camera position.
    // Preserve Camera's original compact horizontal position.
    margins {
        top: 0
        left: chassisLevel === "compact"
              ? Math.max(0, Math.min(54, viewportWidth - implicitWidth))
              : FinanceChassisPolicy.leftMargin(
                    chassisLevel, dockCenterX, viewportWidth, implicitWidth)
    }
    exclusiveZone: 0
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus:
        menuOpen && !zoomWebVisualHeld ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None
    // Avoid keyboard focus thrash during routine browser geometry changes.
    // The actual input cutout remains guarded by live zoomWebDocked.
    focusable: menuOpen && !zoomWebVisualHeld
    color: "transparent"
    surfaceFormat.opaque: false
    visible: !camera.nativeRegionSelecting
    mask: Region {
        x: camera.glowGutter
        y: camera.frameTopInset
        width: camera.menuOpen ? camera.frameWidth : 0
        height: camera.menuOpen ? camera.frameHeight : 0
        Region {
            // Coordinates relative to the enclosing frame input region.
            // No hole until the browser actor and exact bay are confirmed.
            x: camera.zoomActorLeft
            y: camera.zoomInputTop
            width: camera.zoomWebDocked ? camera.zoomActorWidth : 0
            height: camera.zoomWebDocked ? camera.zoomInputHeight : 0
            intersection: Intersection.Subtract
        }
    }

    // Read-only status check after an explicit launch. No retries or hidden
    // background Zoom starts; the user can click CHECK WINDOW again later.
    // Connectivity is sampled on Zoom entry only. Background HEAD retries
    // made the indicators oscillate despite a working local desktop.
    // Another mode-entry performs a new snapshot; no active network poller.

    Timer {
        id: zoomLaunchCheckTimer
        interval: 4000
        repeat: false
        onTriggered: {
            if (camera.menuOpen && camera.activeView === "zoom" && !camera.busy)
                camera.checkZoomWindow();
        }
    }

    Timer {
        id: zoomWebFollowTargetDebounce
        interval: 90
        repeat: false
        onTriggered: camera.sendZoomFollowTarget()
    }
    Timer {
        id: zoomWebRealign
        interval: 240
        repeat: false
        onTriggered: {
            if (camera.menuOpen && camera.activeView === "zoom") {
                if (camera.zoomWebBusy)
                    zoomWebRealign.restart();
                else
                    camera.enterZoomWeb();
            }
        }
    }
    Process {
        id: zoomWebProcess
        running: false
        stdout: StdioCollector {
            onStreamFinished: camera.consumeZoomWeb(this.text)
        }
        onExited: function(code, status) {
            // Collector may finish just after process exit. Fall closed if
            // malformed or absent JSON left the host action busy.
            Qt.callLater(function() {
                if (camera.zoomWebBusy) {
                    const retry = camera.zoomWebNeedsRealign;
                    camera.zoomWebBusy = false;
                    camera.zoomWebDocked = false;
                    camera.zoomWebNeedsRealign = false;
                    camera.zoomWebState = retry ? "REALIGNING_WEB_APP"
                                               : "WEB_HOST_PROCESS_UNVERIFIED";
                    if (retry && camera.menuOpen && camera.activeView === "zoom")
                        zoomWebRealign.restart();
                }
            });
        }
    }
    // The same direct Sway IPC transport used by Social keeps the actual
    // browser actor in Camera's latest viewport, not just a QML cutout.
    Process {
        id: zoomFollowProcess
        command: ["python3", "-I", "-B",
                  Quickshell.shellPath("scripts/camera/ZoomWebFollow.py"),
                  "--identity", camera.zoomWebIdentity]
        running: false
        stdinEnabled: true
        stdout: SplitParser {
            onRead: function(data) {
                camera.consumeZoomFollow(String(data || "").trim());
            }
        }
        onStarted: camera.sendZoomFollowTarget()
        onExited: function(code, status) {
            if (camera.menuOpen && camera.activeView === "zoom") {
                camera.zoomWebDocked = false;
                camera.zoomWebVisualHeld = false;
                camera.zoomWebState = "FOLLOWER // EXITED";
            }
        }
    }
    Process {
        id: zoomWebHideProcess
        running: false
    }

    Process {
        id: cameraProcess
        running: false
        stdout: StdioCollector {
            onStreamFinished: camera.consume(this.text)
        }
        onExited: function(code, status) {
            const action = camera.pendingAction;
            // The collector normally clears pendingAction on a JSON result.
            // Missing interpreter/abrupt process failures must not wedge
            // all future buttons in a permanent busy state.
            Qt.callLater(function() {
                if (camera.pendingAction === action && camera.busy) {
                    camera.pendingAction = "";
                    camera.busy = false;
                    camera.feedback = "CAMERA // BACKEND PROCESS UNAVAILABLE";
                    if (action === "zoomInstall") {
                        camera.zoomInstallNotice = "INSTALL RESULT UNKNOWN // CHECK ZOOM STATUS";
                        camera.zoomSetupVisible = true;
                    }
                    if (action === "capture") {
                        camera.nativeRegionSelecting = false;
                        camera.menuOpen = true;
                    }
                }
            });
        }
    }

    Timer {
        id: shutterDelay
        // Allow the Camera layer-shell surface to fully unmap before slurp
        // requests compositor focus. Other screenshot modes are unaffected.
        interval: 350
        repeat: false
        onTriggered: camera.run("capture", ["capture", camera.captureMode])
    }

    Timer {
        id: gallerySearchDebounce
        interval: 330
        repeat: false
        onTriggered: {
            if ((camera.activeView === "gallery"
                    || camera.activeView === "cleanup") && !camera.busy)
                camera.loadGallery(false);
        }
    }

    // Scroll through old screenshots continuously. Only fetch the next
    // bounded page on reaching the end, and keep a visible manual fallback.
    Timer {
        id: galleryAutoNext
        interval: 120
        repeat: false
        onTriggered: {
            if ((camera.activeView === "gallery"
                    || camera.activeView === "cleanup") && !camera.busy
                    && camera.galleryHasMore)
                camera.loadGallery(true);
        }
    }

    WindowPanelFrame {
        id: frame
        anchors.fill: parent
        anchors.leftMargin: camera.glowGutter
        anchors.rightMargin: camera.glowGutter
        anchors.topMargin: camera.frameTopInset
        anchors.bottomMargin: camera.bottomScreenGap
        visible: camera.menuOpen
        focus: camera.menuOpen
        fillColor: Colors.black
        // Expose the web app ONLY through a compositor-measured slot.
        // Clipping applies to Camera's own QML content, not the separate
        // Sway browser actor; retain its explicitly verified geometry.
        fillOpacity: camera.zoomWebVisualHeld ? 0.0 : 0.97
        clipContent: camera.zoomWebVisualHeld
        borderColor: Colors.cyan
        borderWidth: 1
        glowVisible: camera.menuOpen
        glowColor: Colors.magenta
        Keys.onEscapePressed: function(event) {
            if (camera.activeFocusItem
                    && camera.activeFocusItem !== frame) {
                camera.activeFocusItem.focus = false;
            } else {
                camera.menuOpen = false;
            }
            event.accepted = true;
        }

        Rectangle {
            // Preserve opaque chrome above and below the live browser bay.
            x: 0
            y: 0
            width: parent.width
            height: camera.zoomActorTop
            color: Colors.black
            visible: camera.zoomWebVisualHeld
        }
        Rectangle {
            x: 0
            y: camera.zoomActorTop + camera.zoomActorHeight
            width: parent.width
            height: Math.max(0, parent.height - y)
            color: Colors.black
            visible: camera.zoomWebVisualHeld
        }

        // The native browser intentionally has a 2px inset on EACH side.
        // With frame.fillOpacity=0, those strips otherwise expose whichever
        // unrelated desktop windows happen to be behind Camera. Seal only
        // the frame-local perimeter; never draw outside the Camera surface.
        // The external browser window and the mask remain untouched.
        Rectangle {
            id: zoomWebLeftEdgeSeal
            x: 0
            y: camera.zoomActorTop
            width: Math.max(0, camera.zoomActorLeft)
            height: Math.max(0, camera.zoomActorHeight)
            color: Colors.black
            visible: camera.zoomWebVisualHeld
        }
        Rectangle {
            id: zoomWebRightEdgeSeal
            x: camera.zoomActorLeft + camera.zoomActorWidth
            y: camera.zoomActorTop
            width: Math.max(0, frame.width - x)
            height: Math.max(0, camera.zoomActorHeight)
            color: Colors.black
            visible: camera.zoomWebVisualHeld
        }

        // One frame-owned viewport for the real web actor, its input mask
        // and the local fallback UI. It is independent of cameraPage's
        // size/visibility, so the browser fills the body in every chassis.
        Item {
            id: zoomViewport
            // Zoom is a separate physical Sway guest. Fit its client to the
            // frame's inner edges rather than the narrower content Column,
            // and keep the actual browser, mask and host on this one rect.
            // Keep controls in their #1505 positions. Lift the physical
            // browser 13px total (8px previous + 5px additional) in all three
            // sizes. Its bottom follows the Zoom-mode Camera frame itself.
            // The opaque deck covers its small overlap and the input mask
            // stays clamped below the buttons. Follower uses this same rect.
            x: camera.zoomWebEdgeInset
            y: camera.zoomControlDeckBottom + camera.zoomDeckGap
               - camera.zoomBrowserRise
            width: Math.max(0, frame.width - 2 * camera.zoomWebEdgeInset)
            // The browser ends at the normal 1px bottom frame inset.
            // The 4px opaque gutter was removed by shortening the outer
            // Zoom-only Camera frame, NOT by enlarging the physical guest.
            // Strict Sway physical-bottom verification remains in effect.
            height: Math.max(0, frame.height - y - camera.zoomBayBottom
                             - camera.zoomGuestBottomClearance)
            visible: camera.menuOpen && camera.activeView === "zoom"

            Flickable {
                id: zoomPage
                anchors.fill: parent
                visible: camera.activeView === "zoom" && !camera.zoomWebVisualHeld
                clip: true
                contentHeight: zoomContent.implicitHeight
                boundsBehavior: Flickable.StopAtBounds

                Column {
                    id: zoomContent
                    width: zoomPage.width
                    spacing: 12

                    GohuText {
                        width: parent.width
                        color: Colors.yellow
                        font.pixelSize: 11
                        wrapMode: Text.WordWrap
                        text: "ZOOM WEB // " + camera.zoomWebState
                              + " // Login and Join/New Meeting live in the hosted browser view when docked."
                    }
                    GohuText {
                        width: parent.width
                        visible: camera.zoomWebRectDelta !== null
                        color: Colors.orange
                        font.pixelSize: 10
                        wrapMode: Text.WordWrap
                        text: camera.zoomWebRectDelta
                              ? "DOCK DELTA // X " + camera.zoomWebRectDelta[0]
                                + " / Y " + camera.zoomWebRectDelta[1]
                                + " / W " + camera.zoomWebRectDelta[2]
                                + " / H " + camera.zoomWebRectDelta[3]
                              : ""
                    }

                    ActionButton {
                        width: parent.width
                        height: 38
                        label: "RETRY ZOOM WEB HOST"
                        labelPixelSize: 11
                        accentColor: Colors.magenta
                        available: !camera.zoomWebBusy
                        onLeftClicked: camera.enterZoomWeb()
                    }
                    Row {
                        id: zoomHeaderRow
                        width: parent.width
                        height: 35
                        spacing: 8
                        GohuText {
                            width: parent.width - 136
                            height: 33
                            font.pixelSize: 16
                            color: Colors.magenta
                            verticalAlignment: Text.AlignVCenter
                            text: "ZOOM // MEETINGS"
                        }
                        ActionButton {
                            width: 128
                            height: 33
                            label: "↓ DOWNLOAD"
                            visible: false // Canonical control is the Camera top-right header.
                            labelPixelSize: 11
                            accentColor: Colors.magenta
                            onLeftClicked: {
                                camera.zoomSetupVisible = !camera.zoomSetupVisible;
                                if (camera.zoomSetupVisible)
                                    Qt.callLater(function() {
                                        zoomPage.contentY = Math.max(0, zoomPage.contentHeight - zoomPage.height);
                                    });
                            }
                        }
                    }

                    Row {
                        id: zoomStatusRail
                        width: parent.width
                        height: 39
                        spacing: 5
                        Repeater {
                            model: [
                                {name: "APP", value: camera.zoomClientStatus === null
                                        ? "CHECKING" : camera.zoomClientStatus.available
                                          ? "INSTALLED" : "MISSING"},
                                {name: "WEB CHECK", value: camera.zoomInternetState},
                                {name: "ZOOM CHECK", value: camera.zoomServiceState},
                                {name: "LOGIN", value: "UNKNOWN"}
                            ]
                            Rectangle {
                                width: (zoomStatusRail.width - 3 * zoomStatusRail.spacing) / 4
                                height: 37
                                color: Colors.dark
                                border.width: 1
                                border.color: modelData.value === "REACHABLE"
                                              || modelData.value === "INSTALLED"
                                              ? Colors.cyan : modelData.value === "UNREACHABLE"
                                                || modelData.value === "MISSING"
                                                ? Colors.red : Colors.orange
                                GohuText {
                                    anchors.centerIn: parent
                                    width: parent.width - 4
                                    font.pixelSize: 9
                                    horizontalAlignment: Text.AlignHCenter
                                    elide: Text.ElideRight
                                    color: Colors.white
                                    text: modelData.name + " // " + modelData.value
                                }
                            }
                        }
                    }
                    GohuText {
                        width: parent.width
                        wrapMode: Text.WordWrap
                        font.pixelSize: 10
                        color: Colors.cyan
                        text: "ONE WEB CHECK ON ENTRY // FAILED HTTPS PROBES MEAN UNVERIFIED, NOT OFFLINE // ZOOM LOGIN NOT VERIFIED"
                    }

                    ActionButton {
                        width: parent.width
                        height: 48
                        label: "OPEN / FOCUS ZOOM APP"
                        labelPixelSize: 14
                        accentColor: Colors.magenta
                        available: !camera.busy && camera.zoomClientStatus !== null
                                   && camera.zoomClientStatus.available
                        onLeftClicked: camera.openZoomDirectly()
                    }
                    GohuText {
                        width: parent.width
                        wrapMode: Text.WordWrap
                        font.pixelSize: 11
                        color: Colors.white
                        text: "THEN IN ZOOM: SIGN IN IF NEEDED → NEW MEETING OR JOIN. CAMERA CANNOT START A ZOOM CALL WITHOUT THE PROVIDER'S AUTHENTICATED MEETING CONTROLS."
                    }

                    Rectangle {
                        width: parent.width
                        height: 2
                        color: Colors.cyan
                    }

                    GohuText {
                        width: parent.width
                        font.pixelSize: 13
                        color: Colors.white
                        text: "SOCIAL IDENTITY // " + camera.zoomIdentityId
                    }

                    GohuText {
                        width: parent.width
                        wrapMode: Text.WordWrap
                        font.pixelSize: 10
                        color: Colors.cyan
                        text: "ACCOUNT NAMES LIVE FROM SOCIAL // USER SETTINGS // ACCOUNT NAMES // ZOOM"
                    }

                    GohuText {
                        width: parent.width
                        font.pixelSize: 11
                        color: Colors.yellow
                        text: camera.zoomAccountNames.length
                              ? "SAVED ZOOM NAMES // " + camera.zoomAccountNames.length
                              : "NO ZOOM ACCOUNT NAMES FOR THIS SOCIAL IDENTITY"
                    }

                    Repeater {
                        model: camera.zoomAccountNames
                        ActionButton {
                            width: zoomContent.width
                            height: 38
                            label: modelData.label + " // ALIAS ONLY"
                            labelPixelSize: 11
                            accentColor: Colors.white
                            selected: camera.selectedZoomAccountId === modelData.id
                            onLeftClicked: camera.selectedZoomAccountId = modelData.id
                        }
                    }

                    GohuText {
                        width: parent.width
                        wrapMode: Text.WordWrap
                        font.pixelSize: 10
                        color: Colors.orange
                        text: "ZOOM SIGN-IN // UNVERIFIED. The native Zoom client owns sign-in and meeting controls. Social identities and aliases never block opening this mode or prove Zoom login."
                    }

                    Rectangle {
                        width: parent.width
                        height: 2
                        color: Colors.cyan
                    }

                    GohuText {
                        width: parent.width
                        font.pixelSize: 12
                        color: camera.zoomClientStatus && camera.zoomClientStatus.available
                               ? Colors.cyan : Colors.orange
                        text: camera.zoomClientStatus === null
                              ? "ZOOM CLIENT // NOT CHECKED"
                              : camera.zoomClientStatus.available
                                ? "ZOOM CLIENT // INSTALLED (" + camera.zoomClientStatus.client.toUpperCase() + ")"
                                : "ZOOM CLIENT // NOT FOUND"
                    }

                    // OPEN / FOCUS above also works when Flatpak has a
                    // background process but no detected window.

                    GohuText {
                        width: parent.width
                        wrapMode: Text.WordWrap
                        font.pixelSize: 11
                        color: camera.zoomLaunchState === "VISIBLE"
                               ? Colors.cyan
                               : camera.zoomLaunchState === "FAILED"
                                 || camera.zoomLaunchState === "NOT_FOUND"
                                 ? Colors.red : Colors.yellow
                        text: camera.zoomLaunchMessage
                    }

                    ActionButton {
                        width: parent.width
                        height: 34
                        visible: camera.zoomLaunchState === "FAILED"
                                 || camera.zoomLaunchState === "NOT_FOUND"
                                 || camera.zoomLaunchState === "RUNNING_NO_WINDOW"
                        label: "CHECK ZOOM WINDOW / PROCESS"
                        labelPixelSize: 10
                        accentColor: Colors.cyan
                        available: !camera.busy
                        onLeftClicked: camera.checkZoomWindow()
                    }

                    Column {
                        width: parent.width
                        spacing: 5
                        visible: camera.zoomClientStatus !== null
                                 && camera.zoomClientStatus.client === "flatpak"
                                 && (camera.zoomLaunchState === "FAILED"
                                     || camera.zoomLaunchState === "NOT_FOUND"
                                     || camera.zoomLaunchState === "RUNNING_NO_WINDOW"
                                     || camera.zoomLaunchState === "UNKNOWN")
                        GohuText {
                            width: parent.width
                            wrapMode: Text.WordWrap
                            font.pixelSize: 10
                            color: Colors.orange
                            text: "STARTUP DIAGNOSTICS // RUN IN TERMINAL TO SEE ZOOM'S REAL ERROR OUTPUT. NO AUTOMATIC PERMISSION CHANGES."
                        }
                        TextField {
                            width: parent.width
                            height: 32
                            readOnly: true
                            selectByMouse: true
                            font.pixelSize: 10
                            color: Colors.white
                            text: camera.zoomClientStatus.installation === "system"
                                  ? "flatpak run --system us.zoom.Zoom"
                                  : "flatpak run --user us.zoom.Zoom"
                            background: Rectangle {
                                color: Colors.black
                                border.width: 1
                                border.color: Colors.cyan
                            }
                        }
                    }

                    // Stay inside Camera: an absent client gets explicit
                    // local setup guidance rather than a dead launch control.
                    Column {
                        id: zoomInstallGuide
                        width: parent.width
                        spacing: 10
                        visible: camera.zoomSetupVisible

                        Rectangle {
                            width: parent.width
                            height: 2
                            color: Colors.magenta
                        }
                        GohuText {
                            width: parent.width
                            height: 22
                            font.pixelSize: 13
                            color: Colors.magenta
                            text: "ZOOM // INSTALL REQUIRED"
                        }
                        GohuText {
                            width: parent.width
                            wrapMode: Text.WordWrap
                            font.pixelSize: 11
                            color: Colors.white
                            text: "A Zoom desktop client must be installed to start meetings. The Zoom mode stays available, and no installation starts automatically."
                        }

                        GohuText {
                            width: parent.width
                            font.pixelSize: 11
                            color: Colors.cyan
                            text: "OPTION A // OFFICIAL FEDORA RPM"
                        }
                        GohuText {
                            width: parent.width
                            wrapMode: Text.WordWrap
                            font.pixelSize: 10
                            color: Colors.white
                            text: "Download Zoom Workplace for Linux (Fedora, 64-bit) from Zoom. On Silverblue, install the saved RPM using rpm-ostree and reboot when ready."
                        }
                        ActionButton {
                            width: parent.width
                            height: 36
                            label: "ZOOM OFFICIAL DOWNLOAD // OPENS BROWSER"
                            labelPixelSize: 10
                            accentColor: Colors.cyan
                            // User-clicked navigation only; do not open browser on tab entry.
                            onLeftClicked: Qt.openUrlExternally("https://zoom.us/download?os=linux")
                        }
                        TextField {
                            width: parent.width
                            height: 34
                            readOnly: true
                            selectByMouse: true
                            font.pixelSize: 10
                            color: Colors.white
                            text: "sudo rpm-ostree install ~/Downloads/zoom_x86_64.rpm"
                            background: Rectangle {
                                color: Colors.black
                                border.width: 1
                                border.color: Colors.cyan
                            }
                        }
                        GohuText {
                            width: parent.width
                            wrapMode: Text.WordWrap
                            font.pixelSize: 10
                            color: Colors.orange
                            text: "Use the actual downloaded RPM filename. The rpm-ostree command stages a new deployment; it does not change the running system until reboot."
                        }
                        ActionButton {
                            width: parent.width
                            height: 38
                            label: "INSTALL DOWNLOADED OFFICIAL RPM"
                            labelPixelSize: 11
                            accentColor: Colors.magenta
                            available: !camera.busy
                            onLeftClicked: camera.prepareZoomInstall("official-rpm")
                        }

                        GohuText {
                            width: parent.width
                            font.pixelSize: 11
                            color: Colors.cyan
                            text: "OPTION B // FLATHUB COMMUNITY PACKAGE"
                        }
                        TextField {
                            width: parent.width
                            height: 34
                            readOnly: true
                            selectByMouse: true
                            font.pixelSize: 10
                            color: Colors.white
                            text: "flatpak install flathub us.zoom.Zoom"
                            background: Rectangle {
                                color: Colors.black
                                border.width: 1
                                border.color: Colors.cyan
                            }
                        }
                        GohuText {
                            width: parent.width
                            wrapMode: Text.WordWrap
                            font.pixelSize: 10
                            color: Colors.orange
                            text: "The Zoom package on Flathub is community-maintained and unverified by Zoom. No installation is automatic."
                        }
                        ActionButton {
                            width: parent.width
                            height: 38
                            label: "INSTALL COMMUNITY FLATPAK"
                            labelPixelSize: 11
                            accentColor: Colors.magenta
                            available: !camera.busy
                            onLeftClicked: camera.prepareZoomInstall("community-flatpak")
                        }

                        Column {
                            id: zoomInstallConfirm
                            width: parent.width
                            spacing: 8
                            visible: camera.zoomInstallChoice !== ""

                            Rectangle {
                                width: parent.width
                                height: 2
                                color: Colors.yellow
                            }
                            GohuText {
                                width: parent.width
                                height: 22
                                font.pixelSize: 12
                                color: Colors.yellow
                                text: "CONFIRM // INSTALL ZOOM"
                            }
                            GohuText {
                                width: parent.width
                                font.pixelSize: 11
                                color: Colors.white
                                wrapMode: Text.WordWrap
                                text: camera.zoomInstallChoice === "official-rpm"
                                      ? "Install the signed Zoom RPM already downloaded to ~/Downloads/zoom_x86_64.rpm. May request administrator authorization. Stages a system deployment; reboot is manual."
                                      : "Install the community-maintained, unverified Zoom Flatpak into your user account. Adds the per-user Flathub repository if needed and downloads dependencies. No system-wide install."
                            }
                            Row {
                                width: parent.width
                                height: 42
                                spacing: 9
                                ActionButton {
                                    width: (parent.width - parent.spacing) * 0.62
                                    height: 40
                                    label: "CONFIRM INSTALL"
                                    labelPixelSize: 12
                                    accentColor: Colors.magenta
                                    available: !camera.busy
                                    onLeftClicked: camera.confirmZoomInstall()
                                }
                                ActionButton {
                                    width: (parent.width - parent.spacing) * 0.38
                                    height: 40
                                    label: "CANCEL"
                                    labelPixelSize: 11
                                    accentColor: Colors.cyan
                                    available: !camera.busy
                                    onLeftClicked: camera.zoomInstallChoice = ""
                                }
                            }
                        }
                        ActionButton {
                            width: parent.width
                            height: 38
                            label: "RECHECK ZOOM AFTER INSTALL"
                            labelPixelSize: 11
                            accentColor: Colors.yellow
                            available: !camera.busy
                            onLeftClicked: camera.run("zoomStatus", ["zoom-status"])
                        }
                    }

                    GohuText {
                        width: parent.width
                        visible: camera.zoomInstallNotice !== ""
                        wrapMode: Text.WordWrap
                        font.pixelSize: 11
                        color: Colors.yellow
                        text: camera.zoomInstallNotice
                    }

                    GohuText {
                        width: parent.width
                        wrapMode: Text.WordWrap
                        font.pixelSize: 11
                        color: Colors.white
                        text: "Zoom opens its official local app. Sign in, start, and join meetings there. No passwords or OAuth tokens are shared with Camera."
                    }

                    GohuText {
                        width: parent.width
                        wrapMode: Text.WordWrap
                        font.pixelSize: 10
                        color: Colors.orange
                        text: "EMBEDDED VIDEO // NOT YET CONNECTED. Requires separately validated Zoom SDK and Stage Director containment."
                    }
                }
            }

        }

        // The physical browser rises 13px relative to the original deck slot.
        // Cover the FULL 42px row independently of viewport.y, including
        // the 10px visual underlap, without affecting input.
        // Matte is still behind all Camera buttons and has no handlers.
        Rectangle {
            id: zoomModeDeckMatte
            x: 0
            y: cameraBodyColumn.y + cameraModes.y
            width: frame.width
            // The measured button boundary, not the raised browser top,
            // decides matte height; 1px seals compositor rounding.
            height: Math.max(0, camera.zoomControlDeckBottom - y + 1)
            color: Colors.black
            visible: camera.menuOpen && camera.activeView === "zoom"
                     && camera.zoomWebVisualHeld
        }

        Column {
            id: cameraBodyColumn
            readonly property bool compactZoomDeck:
                camera.activeView === "zoom" && camera.chassisLevel === "compact"
            anchors.fill: parent
            // Keep full-size buttons in the compact deck, but lift the
            // header + mode row together instead of raising Zoom underneath.
            // Expanded/fullscreen and non-Zoom modes retain their spacing.
            anchors.margins: camera.activeView === "zoom" ? 12 : 18
            anchors.topMargin: compactZoomDeck ? 8
                              : camera.activeView === "zoom" ? 12 : 18
            spacing: compactZoomDeck ? 4
                     : camera.activeView === "zoom" ? 8 : 12

            Row {
                id: cameraHeader
                width: parent.width
                height: cameraBodyColumn.compactZoomDeck ? 32 : 37
                spacing: 8

                GohuText {
                    width: parent.width - (30 * 2 + 38 + cameraHeader.spacing * 3)
                           - (camera.activeView === "zoom" ? 110 : 0)
                    height: parent.height
                    verticalAlignment: Text.AlignVCenter
                    text: (camera.activeView === "zoom" ? "CAMERA // ZOOM WEB"
                          : "CAMERA // CAPTURE + LIBRARY")
                          + " [" + camera.chassisLevel.toUpperCase() + "]"
                    font.pixelSize: 18
                    color: Colors.magenta
                    elide: Text.ElideRight
                }

                // Keep setup available when the live Zoom browser fills its
                // page and the former in-page download button is hidden.
                ActionButton {
                    width: 102
                    height: 31
                    visible: camera.activeView === "zoom"
                    label: "↓ DOWNLOAD"
                    labelPixelSize: 10
                    accentColor: Colors.magenta
                    onLeftClicked: {
                        if (camera.zoomWebDocked)
                            camera.hideZoomWeb();
                        camera.zoomSetupVisible = !camera.zoomSetupVisible;
                        if (!camera.zoomSetupVisible && camera.activeView === "zoom")
                            camera.enterZoomWeb();
                    }
                }

                // Finance-style ↓/↑ geometry controls: they resize the
                // existing mapped Camera surface, never create another.
                ActionButton {
                    id: cameraCollapseButton
                    width: 30
                    height: 30
                    label: "↓"
                    labelPixelSize: 17
                    accentColor: Colors.cyan
                    available: camera.chassisLevel !== "compact"
                    onLeftClicked: camera.collapseChassis()
                }
                ActionButton {
                    id: cameraExpandButton
                    width: 30
                    height: 30
                    label: "↑"
                    labelPixelSize: 17
                    accentColor: Colors.magenta
                    available: camera.chassisLevel !== "fullscreen"
                    onLeftClicked: camera.expandChassis()
                }
                ActionButton {
                    width: 38
                    height: 31
                    label: "X"
                    accentColor: Colors.red
                    destructive: true
                    onLeftClicked: camera.menuOpen = false
                }
            }

            Rectangle {
                width: parent.width
                height: 2
                color: Colors.cyan
            }

            Row {
                id: cameraModes
                width: parent.width
                // Leave breathing room below 34px action buttons rather
                // than positioning the hosted browser inside the button row.
                height: 42
                spacing: 8

                Repeater {
                    model: [
                        {id: "capture", label: "CAPTURE"},
                        {id: "gallery", label: "GALLERY"},
                        {id: "zoom", label: "ZOOM"},
                        {id: "cleanup", label: "CLEANUP"}
                    ]
                    ActionButton {
                        width: (cameraModes.width - 3 * cameraModes.spacing) / 4
                        height: 34
                        label: modelData.label
                        labelPixelSize: 12
                        accentColor: Colors.white
                        selected: camera.activeView === modelData.id
                        selectedFillColor: Colors.yellow
                        selectedForegroundColor: Colors.magenta
                        selectedBorderColor: Colors.magenta
                        onLeftClicked: {
                            if (modelData.id !== "zoom") {
                                camera.zoomInstallChoice = "";
                                if (camera.activeView === "zoom")
                                    camera.hideZoomWeb();
                            }
                            if (modelData.id === "gallery")
                                camera.loadGallery(false, "gallery");
                            else if (modelData.id === "cleanup") {
                                camera.activeView = "cleanup";
                                camera.cleanupTechnique = "batch";
                                camera.loadGallery(false, "cleanup");
                            } else if (modelData.id === "zoom")
                                camera.openZoomMode();
                            else
                                camera.activeView = modelData.id;
                        }
                    }
                }
            }

            Item {
                id: cameraPage
                width: parent.width
                // Capture, Gallery and Cleanup keep their existing shared
                // page. Zoom is hosted by the sibling zoomViewport instead.
                visible: camera.activeView !== "zoom"
                height: frame.height - 169

                Flickable {
                    id: capturePage
                    anchors.fill: parent
                    visible: camera.activeView === "capture"
                    clip: true
                    contentHeight: captureContent.implicitHeight
                    boundsBehavior: Flickable.StopAtBounds
                    Column {
                        id: captureContent
                        width: capturePage.width
                        spacing: 10

                    GohuText {
                        width: parent.width
                        font.pixelSize: 14
                        color: Colors.white
                        text: "SHUTTER // WHAT SHOULD BE CAPTURED?"
                    }
                    GohuText {
                        width: parent.width
                        wrapMode: Text.WordWrap
                        font.pixelSize: 11
                        color: Colors.cyan
                        text: "Capture one focused monitor, select a rectangle, or capture the entire desktop. The Camera panel hides before the shutter."
                    }

                    Row {
                        width: parent.width
                        height: 57
                        spacing: 12
                        ActionButton {
                            width: (parent.width - 2 * parent.spacing) / 3
                            height: 55
                            label: "REGION"
                            labelPixelSize: 13
                            accentColor: Colors.white
                            available: !camera.busy
                            onLeftClicked: camera.prepareCapture("region")
                        }
                        ActionButton {
                            width: (parent.width - 2 * parent.spacing) / 3
                            height: 55
                            label: "ONE SCREEN"
                            labelPixelSize: 12
                            accentColor: Colors.white
                            available: !camera.busy
                            onLeftClicked: camera.prepareCapture("focused")
                        }
                        ActionButton {
                            width: (parent.width - 2 * parent.spacing) / 3
                            height: 55
                            label: "BOTH"
                            labelPixelSize: 13
                            accentColor: Colors.white
                            available: !camera.busy
                            onLeftClicked: camera.prepareCapture("all")
                        }
                    }

                    GohuText {
                        width: parent.width
                        font.pixelSize: 12
                        color: Colors.magenta
                        text: "WEBCAM // PHOTO + VIDEO"
                    }
                    Row {
                        width: parent.width
                        height: 34
                        spacing: 8
                        GohuText {
                            width: 110
                            height: 32
                            verticalAlignment: Text.AlignVCenter
                            color: Colors.cyan
                            font.pixelSize: 11
                            text: "CAMERA DEVICE"
                        }
                        ComboBox {
                            id: webcamSelector
                            width: parent.width - 118
                            height: 32
                            model: camera.statusReport && camera.statusReport.videoDevices
                                   ? camera.statusReport.videoDevices : []
                            onActivated: function(index) {
                                camera.webcamDevice = String(webcamSelector.textAt(index));
                            }
                        }
                    }
                    Row {
                        width: parent.width
                        height: 43
                        spacing: 8
                        ActionButton {
                            width: (parent.width - 16) / 3
                            height: 42
                            label: "TAKE PHOTO"
                            labelPixelSize: 11
                            accentColor: Colors.cyan
                            available: !camera.busy && !camera.recording
                            onLeftClicked: camera.webcamPhoto()
                        }
                        ActionButton {
                            width: (parent.width - 16) / 3
                            height: 42
                            label: "RECORD WEBCAM"
                            labelPixelSize: 10
                            accentColor: Colors.magenta
                            available: !camera.busy && !camera.recording
                            onLeftClicked: camera.startRecording("webcam")
                        }
                        ActionButton {
                            width: (parent.width - 16) / 3
                            height: 42
                            label: "RECORD SCREEN"
                            labelPixelSize: 10
                            accentColor: Colors.yellow
                            available: !camera.busy && !camera.recording
                            onLeftClicked: camera.startRecording("screen")
                        }
                    }
                    Row {
                        width: parent.width
                        height: 42
                        spacing: 10
                        GohuText {
                            width: parent.width - 180
                            height: 40
                            verticalAlignment: Text.AlignVCenter
                            color: camera.recording ? Colors.red : Colors.cyan
                            font.pixelSize: 12
                            text: camera.recording
                                  ? "● RECORDING // " + camera.recordingMode.toUpperCase()
                                  : "RECORDER // STANDBY"
                        }
                        ActionButton {
                            width: 170
                            height: 40
                            label: "STOP + SAVE"
                            labelPixelSize: 12
                            destructive: true
                            accentColor: Colors.red
                            available: camera.recording && !camera.busy
                            onLeftClicked: camera.stopRecording()
                        }
                    }
                    GohuText {
                        width: parent.width
                        height: 23
                        font.pixelSize: 10
                        color: Colors.cyan
                        text: "WEBCAM // FFmpeg " + (camera.statusReport && camera.statusReport.ffmpeg ? "READY" : "MISSING")
                              + " · SCREEN // " + (camera.statusReport && camera.statusReport.wfRecorder ? "READY" : "MISSING")
                        elide: Text.ElideRight
                    }
                    GohuText {
                        width: parent.width
                        wrapMode: Text.WordWrap
                        font.pixelSize: 11
                        color: Colors.white
                        text: "SAVE TO // ~/Pictures/Screenshots/Post-Apollo"
                    }

                    GohuText {
                        width: parent.width
                        wrapMode: Text.WordWrap
                        font.pixelSize: 10
                        color: Colors.cyan
                        text: "The image is a normal PNG file on disk. Camera displays the same file later; no duplicate picture database."
                    }

                    ActionButton {
                        width: 160
                        height: 34
                        label: "CHECK TOOLS"
                        labelPixelSize: 11
                        accentColor: Colors.yellow
                        available: !camera.busy
                        onLeftClicked: camera.run("status", ["status"])
                    }

                    GohuText {
                        width: parent.width
                        wrapMode: Text.WordWrap
                        color: Colors.white
                        font.pixelSize: 11
                        text: camera.statusReport === null
                              ? "TOOLS // UNKNOWN"
                              : "GRIM " + (camera.statusReport.grim ? "READY" : "MISSING")
                              + " // SLURP " + (camera.statusReport.slurp ? "READY" : "MISSING")
                              + " // SWAY " + (camera.statusReport.swaymsg ? "READY" : "MISSING")
                              + " // GIO TRASH " + (camera.statusReport.gio ? "READY" : "MISSING")
                    }
                    }
                }

                Row {
                    id: galleryPage
                    anchors.fill: parent
                    visible: camera.activeView === "gallery"
                    spacing: 12

                    Column {
                        width: Math.floor(parent.width * 0.30)
                        height: parent.height
                        spacing: 8

                        Row {
                            width: parent.width
                            height: 34
                            spacing: 8
                            GohuText {
                                width: parent.width - 92
                                height: parent.height
                                verticalAlignment: Text.AlignVCenter
                                color: Colors.white
                                font.pixelSize: 11
                                text: "LIBRARY // " + camera.galleryFiles.length
                                      + "/" + camera.galleryTotal
                                elide: Text.ElideRight
                            }
                            ActionButton {
                                width: 84
                                height: 32
                                label: "REFRESH"
                                labelPixelSize: 10
                                available: !camera.busy
                                accentColor: Colors.cyan
                                onLeftClicked: camera.loadGallery(false)
                            }
                        }

                        TextField {
                            id: gallerySearch
                            width: parent.width
                            height: 35
                            placeholderText: "SEARCH ALL FILES BY NAME"
                            placeholderTextColor: Colors.cyan
                            color: Colors.magenta
                            font.family: "GohuFont 11 Nerd Font Mono"
                            font.pixelSize: 11
                            selectByMouse: true
                            background: Rectangle {
                                color: Colors.black
                                border.width: 1
                                border.color: gallerySearch.activeFocus
                                              ? Colors.magenta : Colors.cyan
                            }
                            onTextChanged: {
                                if (camera.activeView === "gallery")
                                    gallerySearchDebounce.restart();
                            }
                            Keys.onPressed: function(event) {
                                if (event.key === Qt.Key_Escape) {
                                    gallerySearch.focus = false;
                                    event.accepted = true;
                                }
                            }
                        }

                        Row {
                            width: parent.width
                            height: 34
                            spacing: 8

                            TextField {
                                id: galleryFolderInput
                                width: parent.width - 154
                                height: 32
                                color: Colors.white
                                placeholderText: "MORE FOLDERS: ~/Pictures/old"
                                placeholderTextColor: Colors.cyan
                                font.pixelSize: 10
                                selectByMouse: true
                                background: Rectangle {
                                    color: Colors.black
                                    border.width: 1
                                    border.color: galleryFolderInput.activeFocus
                                                  ? Colors.magenta : Colors.cyan
                                }
                                Keys.onPressed: function(event) {
                                    if (event.key === Qt.Key_Escape) {
                                        galleryFolderInput.focus = false;
                                        event.accepted = true;
                                    }
                                }
                                onAccepted: {
                                    camera.galleryCustomFolder = text.trim();
                                    camera.loadGallery(false);
                                }
                            }
                            ActionButton {
                                width: 72
                                height: 32
                                label: "SCAN"
                                labelPixelSize: 10
                                accentColor: Colors.cyan
                                available: !camera.busy
                                onLeftClicked: {
                                    camera.galleryCustomFolder =
                                        galleryFolderInput.text.trim();
                                    camera.loadGallery(false);
                                }
                            }
                            ActionButton {
                                width: 66
                                height: 32
                                label: "CLEAR"
                                labelPixelSize: 10
                                accentColor: Colors.white
                                available: !camera.busy
                                onLeftClicked: {
                                    galleryFolderInput.text = "";
                                    camera.galleryCustomFolder = "";
                                    camera.loadGallery(false);
                                }
                            }
                        }

                        Column {
                            width: parent.width
                            spacing: 4
                            Repeater {
                                model: [
                                    [{id: "all", label: "ALL IMAGES"},
                                     {id: "screenshots", label: "SCREENSHOTS"},
                                     {id: "webcam", label: "WEBCAM"}],
                                    [{id: "videos", label: "VIDEOS"},
                                     {id: "screen-recordings", label: "SCREEN VIDEO"}]
                                ]
                                Row {
                                    id: filterRow
                                    property var rowItems: modelData
                                    width: galleryPage.width * 0.30
                                    height: 29
                                    spacing: 4
                                    Repeater {
                                        model: filterRow.rowItems
                                        ActionButton {
                                            width: (filterRow.width - (filterRow.rowItems.length - 1) * filterRow.spacing) / filterRow.rowItems.length
                                            height: 27
                                            label: modelData.label
                                            labelPixelSize: 8
                                            selected: camera.galleryMediaFilter === modelData.id
                                            accentColor: Colors.white
                                            onLeftClicked: {
                                                camera.galleryShotsOnly = false;
                                                camera.galleryMediaFilter = modelData.id;
                                                camera.loadGallery(false);
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        Item {
                            width: parent.width
                            height: Math.max(120, galleryPage.height - 241)

                            ListView {
                                id: photoList
                                anchors.fill: parent
                                anchors.rightMargin: 17
                                spacing: 5
                                clip: true
                                model: camera.filteredFiles
                                boundsBehavior: Flickable.StopAtBounds
                                onAtYEndChanged: {
                                    if (atYEnd && camera.activeView === "gallery"
                                            && camera.galleryHasMore && !camera.busy)
                                        galleryAutoNext.restart();
                                }

                                delegate: ActionButton {
                                    width: photoList.width
                                    height: 48
                                    label: "        " + modelData.name
                                    labelPixelSize: 9
                                    labelHorizontalAlignment: Text.AlignLeft
                                    contentPadding: 6
                                    accentColor: Colors.white
                                    selected: camera.selectedPath === modelData.path
                                    selectedFillColor: Colors.yellow
                                    selectedForegroundColor: Colors.magenta
                                    selectedBorderColor: Colors.magenta
                                    onLeftClicked: camera.selectImage(modelData)

                                    Image {
                                        width: 35
                                        height: 35
                                        x: 5
                                        y: 5
                                        source: modelData.mediaType && modelData.mediaType.indexOf("video") >= 0
                                                ? "" : camera.fileUrl(modelData.path)
                                        sourceSize.width: 94
                                        sourceSize.height: 94
                                        fillMode: Image.PreserveAspectFit
                                        cache: false
                                        asynchronous: true
                                    }
                                }
                            }

                            NeonScrollBar {
                                flickable: photoList
                                x: parent.width - width - 1
                                height: photoList.height
                                geometryMode: "viewport"
                                handleStyle: "star"
                                visible: scrollable
                            }
                        }

                        Row {
                            width: parent.width
                            height: 32
                            spacing: 8
                            GohuText {
                                width: parent.width - 123
                                height: parent.height
                                verticalAlignment: Text.AlignVCenter
                                text: camera.galleryScanTruncated
                                      ? "SCAN LIMIT // SELECT A FOLDER"
                                      : camera.galleryHasMore
                                      ? "MORE OLD PHOTOS AVAILABLE"
                                      : "ALL MATCHES LOADED"
                                elide: Text.ElideRight
                                font.pixelSize: 9
                                color: camera.galleryScanTruncated
                                       ? Colors.yellow : Colors.cyan
                            }
                            ActionButton {
                                width: 115
                                height: 30
                                label: "LOAD 120 MORE"
                                labelPixelSize: 10
                                accentColor: Colors.white
                                available: camera.galleryHasMore && !camera.busy
                                onLeftClicked: camera.loadGallery(true)
                            }
                        }
                    }

                    Column {
                        width: parent.width - Math.floor(parent.width * 0.30)
                               - parent.spacing
                        height: parent.height
                        spacing: 7

                        GohuText {
                            width: parent.width
                            height: 18
                            text: "VIEWFINDER // WHEEL ZOOM · DRAG PAN"
                            font.pixelSize: 10
                            color: Colors.cyan
                        }

                        CameraImageViewer {
                            id: zoomViewer
                            width: parent.width
                            height: galleryPage.height - 230
                            source: camera.selectedPath && camera.selectedRecord
                                    && camera.selectedRecord.mediaType.indexOf("video") < 0
                                    ? camera.fileUrl(camera.selectedPath) : ""
                        }

                        GohuText {
                            width: parent.width
                            height: 21
                            visible: camera.selectedRecord !== null
                                     && camera.selectedRecord.mediaType.indexOf("video") >= 0
                            color: Colors.magenta
                            font.pixelSize: 11
                            text: "VIDEO SELECTED // OPEN IN LOCAL VIDEO PLAYER"
                        }
                        ActionButton {
                            width: parent.width
                            height: 30
                            visible: camera.selectedRecord !== null
                                     && camera.selectedRecord.mediaType.indexOf("video") >= 0
                            label: "PLAY VIDEO"
                            labelPixelSize: 11
                            accentColor: Colors.cyan
                            onLeftClicked: Qt.openUrlExternally(camera.fileUrl(camera.selectedPath))
                        }
                        Row {
                            width: parent.width
                            height: 32
                            spacing: 7
                            ActionButton {
                                width: (parent.width - 95 - 14) / 2
                                height: 30
                                label: "ZOOM -"
                                labelPixelSize: 10
                                accentColor: Colors.white
                                available: !!camera.selectedPath
                                onLeftClicked: zoomViewer.changeZoom(
                                    0.8, zoomViewer.width / 2, zoomViewer.height / 2)
                            }
                            ActionButton {
                                width: 95
                                height: 30
                                label: "FIT / RESET"
                                labelPixelSize: 10
                                accentColor: Colors.cyan
                                available: !!camera.selectedPath
                                onLeftClicked: zoomViewer.reset()
                            }
                            ActionButton {
                                width: (parent.width - 95 - 14) / 2
                                height: 30
                                label: "ZOOM +"
                                labelPixelSize: 10
                                accentColor: Colors.white
                                available: !!camera.selectedPath
                                onLeftClicked: zoomViewer.changeZoom(
                                    1.25, zoomViewer.width / 2, zoomViewer.height / 2)
                            }
                        }

                        GohuText {
                            width: parent.width
                            height: 36
                            font.pixelSize: 10
                            color: Colors.white
                            wrapMode: Text.WrapAnywhere
                            text: camera.selectedRecord !== null
                                ? camera.selectedRecord.name + "\n"
                                  + "FILE MODIFIED // " + Qt.formatDateTime(
                                      new Date(camera.selectedRecord.modifiedMs),
                                      "yyyy-MM-dd HH:mm:ss")
                                : "SELECT A PICTURE // ALL ORIGINAL FILES STAY ON DISK"
                        }

                        ActionButton {
                            width: parent.width
                            height: 36
                            label: "MOVE SELECTED TO TRASH"
                            labelPixelSize: 11
                            accentColor: Colors.red
                            destructive: true
                            available: !camera.busy && !!camera.selectedPath
                            onLeftClicked: camera.previewSelectedTrash()
                        }

                        Row {
                            width: parent.width
                            height: 34
                            visible: camera.selectedTrashPreview !== null
                            spacing: 8
                            ActionButton {
                                width: (parent.width - parent.spacing) / 2
                                height: 33
                                label: "CANCEL"
                                labelPixelSize: 11
                                accentColor: Colors.cyan
                                onLeftClicked: camera.selectedTrashPreview = null
                            }
                            ActionButton {
                                width: (parent.width - parent.spacing) / 2
                                height: 33
                                label: "CONFIRM TRASH"
                                labelPixelSize: 10
                                accentColor: Colors.red
                                destructive: true
                                available: !camera.busy
                                onLeftClicked: camera.confirmSelectedTrash()
                            }
                        }

                        GohuText {
                            width: parent.width
                            height: 24
                            font.pixelSize: 9
                            color: camera.selectedTrashPreview
                                   ? Colors.red : Colors.cyan
                            wrapMode: Text.WordWrap
                            text: camera.selectedTrashPreview
                                ? "CONFIRM ONE FILE // " + camera.selectedTrashPreview.name
                                : camera.lastTrashReceipt
                                  ? camera.lastTrashReceipt
                                  : "TRASH IS REVERSIBLE // NOT PERMANENT DELETE"
                        }
                    }
                }

                Column {
                    id: cleanupPage
                    anchors.fill: parent
                    visible: camera.activeView === "cleanup"
                    spacing: 7

                    Row {
                        width: parent.width
                        height: 24
                        spacing: 12
                        GohuText {
                            width: parent.width - 182
                            height: parent.height
                            verticalAlignment: Text.AlignVCenter
                            font.pixelSize: 13
                            color: Colors.white
                            text: "CLEANUP // FILE REVIEW"
                        }
                        GohuText {
                            width: 170
                            height: parent.height
                            verticalAlignment: Text.AlignVCenter
                            font.pixelSize: 10
                            color: Colors.magenta
                            text: "TRASH QUEUE // " + camera.batchPaths.length + "/500"
                        }
                    }

                    Row {
                        id: cleanupModeRow
                        width: parent.width
                        height: 33
                        spacing: 6
                        Repeater {
                            model: [
                                {id: "batch", label: "BATCH"},
                                {id: "swipe", label: "SWIPE"},
                                {id: "desktop", label: "DESKTOP"},
                                {id: "hunt", label: "HUNT // NEXT"}
                            ]
                            ActionButton {
                                width: (cleanupModeRow.width - 3 * cleanupModeRow.spacing) / 4
                                height: 32
                                label: modelData.label
                                labelPixelSize: 10
                                selected: camera.cleanupTechnique === modelData.id
                                accentColor: modelData.id === "hunt"
                                             ? Colors.white : Colors.magenta
                                available: !camera.busy && modelData.id !== "hunt"
                                onLeftClicked: {
                                    camera.cleanupTechnique = modelData.id;
                                    camera.batchPreview = null;
                                    camera.batchReviewKey = "";
                                    if (modelData.id === "swipe")
                                        Qt.callLater(function() {
                                            swipeDeck.forceActiveFocus();
                                        });
                                }
                            }
                        }
                    }

                    Row {
                        width: parent.width
                        height: 32
                        spacing: 6
                        visible: camera.cleanupTechnique !== "desktop"
                        TextField {
                            id: cleanupSearch
                            width: parent.width * 0.52
                            height: 30
                            text: camera.cleanupSearchQuery
                            placeholderText: "SEARCH MEDIA BY NAME"
                            placeholderTextColor: Colors.cyan
                            color: Colors.white
                            font.pixelSize: 10
                            selectByMouse: true
                            background: Rectangle {
                                color: Colors.black
                                border.width: 1
                                border.color: cleanupSearch.activeFocus
                                              ? Colors.magenta : Colors.cyan
                            }
                            onTextChanged: {
                                camera.cleanupSearchQuery = text;
                                if (camera.activeView === "cleanup")
                                    gallerySearchDebounce.restart();
                            }
                        }
                        TextField {
                            id: cleanupFolderInput
                            width: parent.width * 0.30
                            height: 30
                            text: camera.cleanupCustomFolder
                            placeholderText: "OPTIONAL FOLDER"
                            placeholderTextColor: Colors.cyan
                            color: Colors.white
                            font.pixelSize: 9
                            selectByMouse: true
                            background: Rectangle {
                                color: Colors.black
                                border.width: 1
                                border.color: Colors.cyan
                            }
                            onAccepted: {
                                camera.cleanupCustomFolder = text.trim();
                                camera.loadGallery(false, "cleanup");
                            }
                        }
                        ActionButton {
                            width: Math.max(45, parent.width * 0.18 - 12)
                            height: 30
                            label: "SCAN"
                            labelPixelSize: 9
                            accentColor: Colors.cyan
                            available: !camera.busy
                            onLeftClicked: {
                                camera.cleanupCustomFolder = cleanupFolderInput.text.trim();
                                camera.loadGallery(false, "cleanup");
                            }
                        }
                    }

                    Row {
                        id: cleanupFilterRow
                        width: parent.width
                        height: 28
                        spacing: 5
                        visible: camera.cleanupTechnique !== "desktop"
                        Repeater {
                            model: [
                                {id: "all", label: "ALL"},
                                {id: "screenshots", label: "SHOTS"},
                                {id: "webcam", label: "WEBCAM"},
                                {id: "videos", label: "VIDEOS"},
                                {id: "screen-recordings", label: "SCREEN VIDEO"}
                            ]
                            ActionButton {
                                width: (cleanupFilterRow.width - 4 * cleanupFilterRow.spacing) / 5
                                height: 27
                                label: modelData.label
                                labelPixelSize: 9
                                accentColor: Colors.white
                                selected: camera.cleanupMediaFilter === modelData.id
                                available: !camera.busy
                                onLeftClicked: {
                                    camera.cleanupMediaFilter = modelData.id;
                                    camera.loadGallery(false, "cleanup");
                                }
                            }
                        }
                    }

                    Item {
                        id: cleanupWorkArea
                        width: parent.width
                        height: camera.cleanupTechnique === "desktop"
                                ? Math.max(170, cleanupPage.height - 135)
                                : Math.max(145, cleanupPage.height - 260)

                        Row {
                            id: cleanupBatchView
                            anchors.fill: parent
                            spacing: 9
                            visible: camera.cleanupTechnique === "batch"

                            Column {
                                width: Math.floor(parent.width * 0.53)
                                height: parent.height
                                spacing: 5
                                Row {
                                    width: parent.width
                                    height: 28
                                    spacing: 5
                                    ActionButton {
                                        width: (parent.width - 5) / 2
                                        height: 27
                                        label: "SELECT LOADED"
                                        labelPixelSize: 9
                                        accentColor: Colors.cyan
                                        available: !camera.busy && camera.galleryFiles.length > 0
                                        onLeftClicked: camera.batchSelectLoaded("")
                                    }
                                    ActionButton {
                                        width: (parent.width - 5) / 2
                                        height: 27
                                        label: "CLEAR QUEUE"
                                        labelPixelSize: 9
                                        accentColor: Colors.yellow
                                        available: !camera.busy && camera.batchPaths.length > 0
                                        onLeftClicked: camera.batchClear()
                                    }
                                }
                                Row {
                                    width: parent.width
                                    height: 29
                                    spacing: 5
                                    TextField {
                                        id: batchNameNeedle
                                        width: parent.width - 83
                                        height: 28
                                        placeholderText: "NAME CONTAINS..."
                                        placeholderTextColor: Colors.cyan
                                        color: Colors.white
                                        font.pixelSize: 9
                                        selectByMouse: true
                                        background: Rectangle {
                                            color: Colors.black
                                            border.width: 1
                                            border.color: Colors.cyan
                                        }
                                    }
                                    ActionButton {
                                        width: 78
                                        height: 28
                                        label: "MATCH"
                                        labelPixelSize: 9
                                        accentColor: Colors.magenta
                                        available: !camera.busy && batchNameNeedle.text.trim().length > 0
                                        onLeftClicked: camera.batchSelectLoaded(batchNameNeedle.text)
                                    }
                                }
                                Item {
                                    width: parent.width
                                    height: Math.max(75, cleanupWorkArea.height - 101)
                                    ListView {
                                        id: cleanupBatchList
                                        anchors.fill: parent
                                        anchors.rightMargin: 12
                                        model: camera.galleryFiles
                                        spacing: 4
                                        clip: true
                                        boundsBehavior: Flickable.StopAtBounds
                                        delegate: Row {
                                            width: cleanupBatchList.width
                                            height: 44
                                            spacing: 5
                                            ActionButton {
                                                width: parent.width * 0.75 - 5
                                                height: 43
                                                label: "      " + modelData.name
                                                labelPixelSize: 9
                                                labelHorizontalAlignment: Text.AlignLeft
                                                contentPadding: 5
                                                selected: camera.selectedPath === modelData.path
                                                accentColor: Colors.white
                                                onLeftClicked: camera.selectImage(modelData)
                                                Image {
                                                    width: 30
                                                    height: 30
                                                    x: 3
                                                    y: 6
                                                    source: modelData.mediaType
                                                            && modelData.mediaType.indexOf("video") >= 0
                                                            ? "" : camera.fileUrl(modelData.path)
                                                    fillMode: Image.PreserveAspectFit
                                                    asynchronous: true
                                                    cache: false
                                                }
                                            }
                                            ActionButton {
                                                width: parent.width * 0.25
                                                height: 43
                                                label: camera.batchContains(modelData.path)
                                                       ? "QUEUED" : "+ QUEUE"
                                                labelPixelSize: 9
                                                selected: camera.batchContains(modelData.path)
                                                accentColor: Colors.magenta
                                                available: !camera.busy
                                                onLeftClicked: camera.batchToggle(modelData)
                                            }
                                        }
                                    }
                                    NeonScrollBar {
                                        flickable: cleanupBatchList
                                        x: parent.width - width - 1
                                        height: parent.height
                                        geometryMode: "viewport"
                                        handleStyle: "star"
                                        visible: scrollable
                                    }
                                }
                                Row {
                                    width: parent.width
                                    height: 29
                                    spacing: 7
                                    GohuText {
                                        width: parent.width - 120
                                        height: parent.height
                                        verticalAlignment: Text.AlignVCenter
                                        font.pixelSize: 9
                                        color: Colors.cyan
                                        text: camera.galleryFiles.length + "/"
                                              + camera.galleryTotal + " LOADED"
                                    }
                                    ActionButton {
                                        width: 112
                                        height: 28
                                        label: "LOAD 120 MORE"
                                        labelPixelSize: 8
                                        accentColor: Colors.cyan
                                        available: !camera.busy && camera.galleryHasMore
                                        onLeftClicked: camera.loadGallery(true, "cleanup")
                                    }
                                }
                            }
                            Column {
                                width: parent.width - Math.floor(parent.width * 0.53)
                                       - parent.spacing
                                height: parent.height
                                spacing: 5
                                GohuText {
                                    width: parent.width
                                    height: 16
                                    font.pixelSize: 10
                                    color: Colors.cyan
                                    text: "SELECTED PREVIEW"
                                }
                                CameraImageViewer {
                                    id: cleanupViewer
                                    width: parent.width
                                    height: Math.max(65, cleanupWorkArea.height - 88)
                                    source: camera.selectedRecord
                                            && camera.selectedRecord.mediaType.indexOf("video") < 0
                                            ? camera.fileUrl(camera.selectedPath) : ""
                                }
                                GohuText {
                                    width: parent.width
                                    height: 20
                                    elide: Text.ElideRight
                                    font.pixelSize: 9
                                    color: Colors.white
                                    text: camera.selectedRecord
                                          ? camera.selectedRecord.name
                                          : "SELECT MEDIA ON THE LEFT"
                                }
                                ActionButton {
                                    width: parent.width
                                    height: 29
                                    visible: camera.selectedRecord
                                             && camera.selectedRecord.mediaType.indexOf("video") >= 0
                                    label: "PLAY VIDEO"
                                    labelPixelSize: 9
                                    accentColor: Colors.cyan
                                    onLeftClicked: Qt.openUrlExternally(
                                                       camera.fileUrl(camera.selectedPath))
                                }
                            }
                        }

                        Column {
                            id: cleanupSwipeView
                            anchors.fill: parent
                            spacing: 6
                            visible: camera.cleanupTechnique === "swipe"

                            GohuText {
                                width: parent.width
                                height: 17
                                font.pixelSize: 10
                                color: Colors.magenta
                                text: "SWIPE // LEFT TRASH QUEUE · RIGHT KEEP · DOWN SKIP · Z UNDO"
                            }
                            Item {
                                id: swipeDeck
                                width: parent.width
                                height: Math.max(90, cleanupWorkArea.height - 91)
                                focus: camera.activeView === "cleanup"
                                       && camera.cleanupTechnique === "swipe"
                                property var currentRecord:
                                    camera.swipeIndex < camera.galleryFiles.length
                                    ? camera.galleryFiles[camera.swipeIndex] : null
                                property real dragX: 0
                                property real dragY: 0
                                Keys.onPressed: function(event) {
                                    if (event.key === Qt.Key_Left) {
                                        camera.swipeDecide("trash");
                                        event.accepted = true;
                                    } else if (event.key === Qt.Key_Right) {
                                        camera.swipeDecide("keep");
                                        event.accepted = true;
                                    } else if (event.key === Qt.Key_Down) {
                                        camera.swipeDecide("skip");
                                        event.accepted = true;
                                    } else if (event.key === Qt.Key_Z
                                               || event.key === Qt.Key_Backspace) {
                                        camera.swipeUndo();
                                        event.accepted = true;
                                    }
                                }

                                Item {
                                    id: swipeVisualCard
                                    anchors.fill: parent
                                    transform: Translate {
                                        x: swipeDeck.dragX
                                        y: swipeDeck.dragY
                                    }
                                    rotation: swipeDeck.dragX / 24

                                Rectangle {
                                    anchors.centerIn: parent
                                    width: Math.min(parent.width - 20, 580)
                                    height: parent.height - 2
                                    radius: 8
                                    color: Colors.black
                                    border.color: Colors.magenta
                                    border.width: 1
                                }
                                Image {
                                    anchors.centerIn: parent
                                    width: Math.min(parent.width - 36, 550)
                                    height: Math.max(40, parent.height - 55)
                                    visible: swipeDeck.currentRecord !== null
                                             && swipeDeck.currentRecord.mediaType.indexOf("video") < 0
                                    source: visible
                                            ? camera.fileUrl(swipeDeck.currentRecord.path) : ""
                                    fillMode: Image.PreserveAspectFit
                                    cache: false
                                    asynchronous: true
                                }
                                GohuText {
                                    anchors.centerIn: parent
                                    visible: swipeDeck.currentRecord === null
                                             || swipeDeck.currentRecord.mediaType.indexOf("video") >= 0
                                    font.pixelSize: 13
                                    color: Colors.cyan
                                    text: swipeDeck.currentRecord === null
                                          ? camera.galleryHasMore
                                            ? "END OF LOADED PAGE // LOAD MORE"
                                            : "ROUND COMPLETE"
                                          : "VIDEO // USE BATCH PREVIEW TO PLAY"
                                }
                                GohuText {
                                    anchors.bottom: parent.bottom
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    width: Math.min(parent.width - 35, 540)
                                    height: 28
                                    horizontalAlignment: Text.AlignHCenter
                                    elide: Text.ElideMiddle
                                    font.pixelSize: 10
                                    color: Colors.white
                                    text: swipeDeck.currentRecord !== null
                                          ? swipeDeck.currentRecord.name
                                          : "NO MORE LOADED FILES"
                                }
                                GohuText {
                                    anchors.top: parent.top
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    height: 24
                                    visible: Math.abs(swipeDeck.dragX) > 35
                                             || swipeDeck.dragY > 40
                                    font.pixelSize: 14
                                    color: swipeDeck.dragX < -35 ? Colors.red
                                           : swipeDeck.dragX > 35 ? Colors.cyan
                                           : Colors.yellow
                                    text: swipeDeck.dragX < -35 ? "QUEUE FOR TRASH"
                                          : swipeDeck.dragX > 35 ? "KEEP"
                                          : "SKIP"
                                }
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    enabled: swipeDeck.currentRecord !== null && !camera.busy
                                    property real startX: 0
                                    property real startY: 0
                                    onPressed: function(mouse) {
                                        startX = mouse.x;
                                        startY = mouse.y;
                                        swipeDeck.dragX = 0;
                                        swipeDeck.dragY = 0;
                                        swipeDeck.forceActiveFocus();
                                    }
                                    onPositionChanged: function(mouse) {
                                        if (pressed) {
                                            swipeDeck.dragX = Math.max(-180, Math.min(
                                                180, mouse.x - startX));
                                            swipeDeck.dragY = Math.max(-120, Math.min(
                                                120, mouse.y - startY));
                                        }
                                    }
                                    onReleased: function(mouse) {
                                        const dx = mouse.x - startX;
                                        const dy = mouse.y - startY;
                                        swipeDeck.dragX = 0;
                                        swipeDeck.dragY = 0;
                                        if (Math.abs(dx) >= 65 && Math.abs(dx) > Math.abs(dy))
                                            camera.swipeDecide(dx < 0 ? "trash" : "keep");
                                        else if (dy >= 65)
                                            camera.swipeDecide("skip");
                                    }
                                    onCanceled: {
                                        swipeDeck.dragX = 0;
                                        swipeDeck.dragY = 0;
                                    }
                                }
                            }
                            Row {
                                width: parent.width
                                height: 32
                                spacing: 6
                                ActionButton {
                                    width: (parent.width - 18) / 4
                                    height: 31
                                    label: "LEFT · QUEUE"
                                    labelPixelSize: 10
                                    accentColor: Colors.red
                                    available: !camera.busy
                                               && camera.swipeIndex < camera.galleryFiles.length
                                    onLeftClicked: camera.swipeDecide("trash")
                                }
                                ActionButton {
                                    width: (parent.width - 18) / 4
                                    height: 31
                                    label: "RIGHT · KEEP"
                                    labelPixelSize: 10
                                    accentColor: Colors.cyan
                                    available: !camera.busy
                                               && camera.swipeIndex < camera.galleryFiles.length
                                    onLeftClicked: camera.swipeDecide("keep")
                                }
                                ActionButton {
                                    width: (parent.width - 18) / 4
                                    height: 31
                                    label: "DOWN · SKIP"
                                    labelPixelSize: 10
                                    accentColor: Colors.yellow
                                    available: !camera.busy
                                               && camera.swipeIndex < camera.galleryFiles.length
                                    onLeftClicked: camera.swipeDecide("skip")
                                }
                                ActionButton {
                                    width: (parent.width - 18) / 4
                                    height: 31
                                    label: "UNDO"
                                    labelPixelSize: 10
                                    accentColor: Colors.magenta
                                    available: !camera.busy && camera.swipeHistory.length > 0
                                    onLeftClicked: camera.swipeUndo()
                                }
                            }
                            Row {
                                width: parent.width
                                height: 22
                                spacing: 8
                                GohuText {
                                    width: parent.width - 130
                                    height: parent.height
                                    font.pixelSize: 9
                                    color: Colors.cyan
                                    text: "CARD " + Math.min(camera.swipeIndex + 1,
                                                              camera.galleryFiles.length)
                                          + "/" + camera.galleryFiles.length
                                          + " // QUEUED " + camera.batchPaths.length
                                }
                                ActionButton {
                                    width: 122
                                    height: 22
                                    label: "LOAD 120 MORE"
                                    labelPixelSize: 8
                                    accentColor: Colors.white
                                    available: !camera.busy && camera.galleryHasMore
                                               && camera.swipeIndex >= camera.galleryFiles.length
                                    onLeftClicked: camera.loadGallery(true, "cleanup")
                                }
                            }
                        }

                        Flickable {
                            id: cleanupDesktopView
                            anchors.fill: parent
                            visible: camera.cleanupTechnique === "desktop"
                            clip: true
                            contentHeight: desktopCleanupContent.implicitHeight
                            boundsBehavior: Flickable.StopAtBounds
                            Column {
                                id: desktopCleanupContent
                                width: cleanupWorkArea.width - 18
                                spacing: 12
                                GohuText {
                                    width: parent.width
                                    font.pixelSize: 14
                                    color: Colors.white
                                    text: "DESKTOP // SCREENSHOT CLEANUP"
                                }
                                GohuText {
                                    width: parent.width
                                    wrapMode: Text.WordWrap
                                    font.pixelSize: 11
                                    color: Colors.cyan
                                    text: "Matches Desktop screenshot-like PNG/JPEG/WEBP only. Other photos and subfolders remain untouched."
                                }
                                ActionButton {
                                    width: 210
                                    height: 40
                                    label: "PREVIEW MATCHES"
                                    labelPixelSize: 11
                                    accentColor: Colors.white
                                    available: !camera.busy
                                    onLeftClicked: camera.previewCleanup()
                                }
                                GohuText {
                                    width: parent.width
                                    font.pixelSize: 12
                                    color: Colors.white
                                    text: camera.trashPreview
                                          ? "MATCHES // " + camera.trashPreview.count
                                            + " // BYTES " + camera.trashPreview.bytes
                                          : "MATCHES // NOT PREVIEWED"
                                }
                                GohuText {
                                    width: parent.width
                                    height: 95
                                    wrapMode: Text.WrapAnywhere
                                    color: Colors.cyan
                                    font.pixelSize: 10
                                    text: camera.trashPreview && camera.trashPreview.sample
                                          ? "EXAMPLES // " + camera.trashPreview.sample.join(" // ")
                                          : "Preview before moving screenshot files to Trash."
                                }
                                ActionButton {
                                    width: 225
                                    height: 43
                                    label: camera.trashPreview
                                           ? "MOVE " + camera.trashPreview.count + " TO TRASH"
                                           : "TRASH REQUIRES PREVIEW"
                                    labelPixelSize: 11
                                    accentColor: Colors.red
                                    destructive: true
                                    available: !camera.busy && camera.trashPreview !== null
                                               && Number(camera.trashPreview.count) > 0
                                               && !!camera.trashPreview.planId
                                    onLeftClicked: camera.confirmCleanup()
                                }
                                GohuText {
                                    width: parent.width
                                    wrapMode: Text.WordWrap
                                    font.pixelSize: 10
                                    color: Colors.red
                                    text: "RECOVERABLE TRASH ONLY // NO PERMANENT DELETE // PLAN EXPIRES IN 10 MINUTES"
                                }
                            }
                        }
                    }

                    Row {
                        width: parent.width
                        height: 34
                        visible: camera.cleanupTechnique !== "desktop"
                        spacing: 8
                        ActionButton {
                            width: (parent.width - 8) * 0.46
                            height: 33
                            label: "REVIEW QUEUE // " + camera.batchPaths.length
                            labelPixelSize: 11
                            accentColor: Colors.yellow
                            available: !camera.busy && camera.batchPaths.length > 0
                            onLeftClicked: camera.previewBatchTrash()
                        }
                        GohuText {
                            width: (parent.width - 8) * 0.54
                            height: 33
                            verticalAlignment: Text.AlignVCenter
                            font.pixelSize: 10
                            color: camera.galleryScanTruncated ? Colors.red : Colors.cyan
                            text: camera.galleryScanTruncated
                                  ? "SCAN LIMIT // SELECT A FOLDER"
                                  : camera.batchPreview
                                    ? "READY TO CONFIRM // " + camera.batchPreview.count
                                    : "NO FILES MOVED // TRASH IS REVERSIBLE"
                        }
                    }
                    GohuText {
                        width: parent.width
                        height: 31
                        visible: camera.cleanupTechnique !== "desktop"
                        wrapMode: Text.WrapAnywhere
                        font.pixelSize: 10
                        color: camera.batchPreview ? Colors.yellow : Colors.cyan
                        text: camera.batchPreview
                              ? "REVIEW // " + camera.batchPreview.count + " FILES // "
                                + camera.batchPreview.bytes + " BYTES // "
                                + camera.batchPreview.sample.join(" · ")
                              : camera.batchReceipt
                                ? camera.batchReceipt
                                : "SELECT OR SWIPE TO QUEUE // FINAL CONFIRMATION REQUIRED"
                    }
                    Row {
                        width: parent.width
                        height: 33
                        visible: camera.cleanupTechnique !== "desktop"
                                 && camera.batchPreview !== null
                        spacing: 8
                        ActionButton {
                            width: (parent.width - 8) / 2
                            height: 32
                            label: "CANCEL"
                            labelPixelSize: 10
                            accentColor: Colors.cyan
                            onLeftClicked: camera.batchPreview = null
                        }
                        ActionButton {
                            width: (parent.width - 8) / 2
                            height: 32
                            label: "CONFIRM TRASH"
                            labelPixelSize: 10
                            accentColor: Colors.red
                            destructive: true
                            available: !camera.busy
                            onLeftClicked: camera.confirmBatchTrash()
                        }
                    }
                }

            }

            GohuText {
                width: parent.width
                // Zoom owns the full body both before and after docking.
                // Keep Camera's global footer in the other three modes only.
                visible: camera.activeView !== "zoom"
                font.pixelSize: 10
                color: Colors.yellow
                elide: Text.ElideRight
                text: camera.busy ? "CAMERA // PROCESSING" : camera.feedback
            }
        }
    }
}
