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
    property string captureMode: "region"
    // Read Social's active identity and provider alias metadata, not login state.
    readonly property var zoomSocialIdentity: SocialIdentityStore.snapshot
    readonly property string zoomIdentityId: String(zoomSocialIdentity.activeId || "")
    readonly property var zoomAccountNames:
        SocialAccountDetailsStore.accountNamesFor(zoomIdentityId, "zoom")
    property string selectedZoomAccountId: ""
    property var zoomClientStatus: null
    // Missing installations must show an actionable setup, not a disabled button.
    property bool zoomSetupVisible: false
    // Explicit two-click installer gate; cleared on closing or changing modes.
    property string zoomInstallChoice: ""
    property string zoomInstallNotice: ""
    onZoomIdentityIdChanged: selectedZoomAccountId = ""
    // The native slurp overlay owns the region drag; Camera unmaps while it runs.
    property bool nativeRegionSelecting: false
    // Same finance-size policy and top/bottom chrome budget for medium
    // and fullscreen, while preserving Camera's existing 770x675 compact
    // frame. One mapped PanelWindow persists across all size changes.
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
        ? Math.max(1, Math.min(770, viewportWidth - 2 * glowGutter))
        : financeSize.width
    readonly property int frameHeight:
        chassisLevel === "compact"
        ? Math.max(1, Math.min(675, viewportHeight
                               - frameTopInset - bottomScreenGap))
        : financeSize.height
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
        if (!menuOpen)
            zoomInstallChoice = "";
        // Read-only tool status on explicit open; no image copies or writes.
        if (menuOpen && statusReport === null && !busy)
            run("status", ["status"]);
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

    function loadGallery(append) {
        if (busy)
            return false;
        activeView = "gallery";
        const nextPage = append === true ? galleryPageIndex + 1 : 0;
        if (append !== true) {
            selectedPath = "";
            selectedRecord = null;
            selectedTrashPreview = null;
            galleryFiles = [];
        } else if (!galleryHasMore) {
            return false;
        }
        galleryRequestedQuery = gallerySearch.text.trim();
        galleryRequestedFolder = galleryCustomFolder;
        galleryRequestedShotsOnly = galleryShotsOnly;
        galleryRequestedMediaFilter = galleryMediaFilter;
        return run("gallery", [
            "gallery",
            "--page", String(nextPage),
            "--query", galleryRequestedQuery,
            "--folder", galleryCustomFolder,
            "--media-filter", galleryMediaFilter
        ].concat(galleryShotsOnly ? ["--shots-only"] : []));
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
        if (!busy)
            run("zoomStatus", ["zoom-status"]);
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
        return run("zoomOpen", ["zoom-open"]);
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
        if (action === "zoomInstall") {
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
            feedback = payload.available ? "ZOOM // CLIENT DETECTED // LOGIN UNKNOWN"
                                         : "ZOOM // NOT INSTALLED // SETUP OPTIONS BELOW";
        } else if (action === "zoomOpen") {
            feedback = "ZOOM // OPEN REQUESTED // SIGN IN THROUGH ZOOM CLIENT";
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
            if (gallerySearch.text.trim() !== galleryRequestedQuery
                    || galleryCustomFolder !== galleryRequestedFolder
                    || galleryShotsOnly !== galleryRequestedShotsOnly
                    || galleryMediaFilter !== galleryRequestedMediaFilter)
                gallerySearchDebounce.restart();
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
        menuOpen ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None
    focusable: menuOpen
    color: "transparent"
    surfaceFormat.opaque: false
    visible: !camera.nativeRegionSelecting
    mask: Region {
        x: camera.glowGutter
        y: camera.frameTopInset
        width: camera.menuOpen ? camera.frameWidth : 0
        height: camera.menuOpen ? camera.frameHeight : 0
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
            if (camera.activeView === "gallery" && !camera.busy)
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
            if (camera.activeView === "gallery" && !camera.busy
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
        fillOpacity: 0.97
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

        Column {
            anchors.fill: parent
            anchors.margins: 18
            spacing: 12

            Row {
                id: cameraHeader
                width: parent.width
                height: 37
                spacing: 8

                GohuText {
                    width: parent.width - (30 * 2 + 38 + cameraHeader.spacing * 3)
                    height: parent.height
                    verticalAlignment: Text.AlignVCenter
                    text: "CAMERA // CAPTURE + LIBRARY"
                          + " [" + camera.chassisLevel.toUpperCase() + "]"
                    font.pixelSize: 18
                    color: Colors.magenta
                    elide: Text.ElideRight
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
                height: 38
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
                            if (modelData.id !== "zoom")
                                camera.zoomInstallChoice = "";
                            if (modelData.id === "gallery")
                                camera.loadGallery();
                            else if (modelData.id === "zoom")
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
                            height: galleryPage.height - 241

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

                Flickable {
                    id: zoomPage
                    anchors.fill: parent
                    visible: camera.activeView === "zoom"
                    clip: true
                    contentHeight: zoomContent.implicitHeight
                    boundsBehavior: Flickable.StopAtBounds

                    Column {
                        id: zoomContent
                        width: zoomPage.width
                        spacing: 12

                        GohuText {
                            width: parent.width
                            height: 31
                            font.pixelSize: 16
                            color: Colors.magenta
                            text: "ZOOM // MEETINGS"
                        }

                        GohuText {
                            width: parent.width
                            wrapMode: Text.WordWrap
                            font.pixelSize: 11
                            color: Colors.cyan
                            text: "CAMERA MODE // NATIVE ZOOM CLIENT + SOCIAL ACCOUNT LABELS"
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
                            text: "Account names are display labels, not active Zoom login sessions. Selecting an alias does NOT switch the Zoom client account."
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

                        Row {
                            width: parent.width
                            height: 42
                            spacing: 10

                            ActionButton {
                                width: 150
                                height: 40
                                label: "CHECK ZOOM"
                                labelPixelSize: 11
                                accentColor: Colors.cyan
                                available: !camera.busy
                                onLeftClicked: camera.run("zoomStatus", ["zoom-status"])
                            }

                            ActionButton {
                                width: parent.width - 160
                                height: 40
                                label: camera.zoomClientStatus && camera.zoomClientStatus.available
                                       ? "OPEN ZOOM CLIENT"
                                       : camera.zoomSetupVisible ? "HIDE INSTALL STEPS"
                                       : "SET UP ZOOM"
                                labelPixelSize: 12
                                accentColor: Colors.magenta
                                available: !camera.busy
                                onLeftClicked: {
                                    if (camera.zoomClientStatus && camera.zoomClientStatus.available)
                                        camera.launchZoomClient();
                                    else
                                        camera.zoomSetupVisible = !camera.zoomSetupVisible;
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
                                text: "A Zoom desktop client must be installed first. Camera detects it after CHECK ZOOM. This panel never installs anything automatically."
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

                Column {
                    id: cleanupPage
                    anchors.fill: parent
                    visible: camera.activeView === "cleanup"
                    spacing: 18

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
                        text: "This first cleanup identifies PNG/JPEG/WEBP files on Desktop whose names include Screenshot, Screen Shot, grim, or other screenshot-tool names. Ordinary photos are excluded. No subfolders are scanned."
                    }

                    ActionButton {
                        width: 210
                        height: 43
                        label: "PREVIEW MATCHES"
                        labelPixelSize: 12
                        accentColor: Colors.white
                        available: !camera.busy
                        onLeftClicked: camera.previewCleanup()
                    }

                    GohuText {
                        width: parent.width
                        font.pixelSize: 13
                        color: Colors.white
                        text: camera.trashPreview
                            ? "MATCHES // " + camera.trashPreview.count
                              + " // BYTES " + camera.trashPreview.bytes
                            : "MATCHES // NOT PREVIEWED"
                    }

                    GohuText {
                        width: parent.width
                        height: 132
                        wrapMode: Text.WrapAnywhere
                        color: Colors.cyan
                        font.pixelSize: 10
                        text: camera.trashPreview && camera.trashPreview.sample
                              ? "EXAMPLES // " + camera.trashPreview.sample.join(" // ")
                              : "Preview before any cleanup. Photos outside the matching Desktop list remain untouched."
                    }

                    ActionButton {
                        width: 235
                        height: 45
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
                        text: "TRASH IS REVERSIBLE // NO PERMANENT DELETE. Files changed after preview are skipped. The plan expires after 10 minutes."
                    }
                }

            }

            GohuText {
                width: parent.width
                font.pixelSize: 10
                color: Colors.yellow
                elide: Text.ElideRight
                text: camera.busy ? "CAMERA // PROCESSING" : camera.feedback
            }
        }
    }
}
