import QtQuick
import QtQuick.Controls
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
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
        menuOpen = !menuOpen;
    }

    onMenuOpenChanged: {
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
        return run("gallery", [
            "gallery",
            "--page", String(nextPage),
            "--query", galleryRequestedQuery,
            "--folder", galleryCustomFolder
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
        if (busy || (mode !== "region" && mode !== "focused" && mode !== "all"))
            return false;
        captureMode = mode;
        feedback = "CAMERA // HIDING PANEL BEFORE SHUTTER";
        menuOpen = false;
        shutterDelay.restart();
        return true;
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
        let payload = null;
        try { payload = JSON.parse(String(raw || "").trim()); }
        catch (error) {
            feedback = "CAMERA // INVALID BACKEND RESPONSE";
            if (action === "capture")
                menuOpen = true;
            return;
        }
        if (!payload || payload.ok !== true) {
            feedback = "CAMERA // " + String(payload && payload.error || "ACTION_FAILED");
            if (action === "capture")
                menuOpen = true;
            return;
        }
        if (action === "status") {
            statusReport = payload;
            feedback = "CAMERA // TOOL STATUS READY";
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
                    || galleryShotsOnly !== galleryRequestedShotsOnly)
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
    visible: true
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
                    if (action === "capture")
                        camera.menuOpen = true;
                }
            });
        }
    }

    Timer {
        id: shutterDelay
        interval: 250
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
                        {id: "cleanup", label: "CLEANUP"}
                    ]
                    ActionButton {
                        width: (cameraModes.width - 2 * cameraModes.spacing) / 3
                        height: 34
                        label: modelData.label
                        labelPixelSize: 12
                        accentColor: Colors.white
                        selected: camera.activeView === modelData.id
                        selectedFillColor: Colors.yellow
                        selectedForegroundColor: Colors.magenta
                        selectedBorderColor: Colors.magenta
                        onLeftClicked: {
                            if (modelData.id === "gallery")
                                camera.loadGallery();
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

                Column {
                    id: capturePage
                    anchors.fill: parent
                    visible: camera.activeView === "capture"
                    spacing: 18

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

                Row {
                    id: galleryPage
                    anchors.fill: parent
                    visible: camera.activeView === "gallery"
                    spacing: 12

                    Column {
                        width: Math.floor(parent.width * 0.54)
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

                        Row {
                            width: parent.width
                            height: 30
                            spacing: 8
                            ActionButton {
                                width: (parent.width - parent.spacing) / 2
                                height: 28
                                label: "ALL IMAGES"
                                labelPixelSize: 10
                                selected: !camera.galleryShotsOnly
                                accentColor: Colors.white
                                onLeftClicked: {
                                    camera.galleryShotsOnly = false;
                                    camera.loadGallery(false);
                                }
                            }
                            ActionButton {
                                width: (parent.width - parent.spacing) / 2
                                height: 28
                                label: "SCREENSHOTS"
                                labelPixelSize: 10
                                selected: camera.galleryShotsOnly
                                accentColor: Colors.white
                                onLeftClicked: {
                                    camera.galleryShotsOnly = true;
                                    camera.loadGallery(false);
                                }
                            }
                        }

                        Item {
                            width: parent.width
                            height: galleryPage.height - 205

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
                                    height: 58
                                    label: "         " + modelData.name
                                    labelPixelSize: 10
                                    labelHorizontalAlignment: Text.AlignLeft
                                    contentPadding: 6
                                    accentColor: Colors.white
                                    selected: camera.selectedPath === modelData.path
                                    selectedFillColor: Colors.yellow
                                    selectedForegroundColor: Colors.magenta
                                    selectedBorderColor: Colors.magenta
                                    onLeftClicked: camera.selectImage(modelData)

                                    Image {
                                        width: 47
                                        height: 47
                                        x: 5
                                        y: 5
                                        source: camera.fileUrl(modelData.path)
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
                        width: parent.width - Math.floor(parent.width * 0.54)
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
                            source: camera.selectedPath
                                    ? camera.fileUrl(camera.selectedPath) : ""
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
