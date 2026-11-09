import Quickshell
import QtQuick
import QtQuick.Controls
import Quickshell.Io
import Quickshell.Wayland
import "../components"

// TRASH // Bottom-left utility backed by the user's existing GIO Trash.
// The 50x50 dock button retains Power's exact edge clearances; the panel is
// larger independently, as required by the dock/widget composition contract.
PanelWindow {
    id: trashLauncher

    property bool menuOpen: false

    // Four chassis sizes share ONE mapped PanelWindow. The dock button never
    // changes its 50x50 geometry or 25px-left/20px-bottom position.
    property string chassisSize: "compact"
    readonly property var chassisSizes: ["compact", "medium", "large", "full"]
    readonly property int usableWidth: screen ? screen.width : 2560
    readonly property int usableHeight: screen ? screen.height : 1440
    readonly property int frameWidth: Math.max(320, Math.min(
        chassisSize === "compact" ? 420
        : chassisSize === "medium" ? 620
        : chassisSize === "large" ? 900 : usableWidth - 55,
        usableWidth - 55))
    readonly property int frameHeight: Math.max(330, Math.min(
        chassisSize === "compact" ? 450
        : chassisSize === "medium" ? 570
        : chassisSize === "large" ? 730 : usableHeight - 120,
        usableHeight - 120))
    readonly property bool burnWarning:
        confirmMode !== "" || pendingAction === "burn"
        || pendingAction === "burn-all"

    function stepChassis(direction) {
        const index = chassisSizes.indexOf(chassisSize);
        chassisSize = chassisSizes[Math.max(0, Math.min(
            chassisSizes.length - 1, index + direction))];
    }

    property bool busy: false
    property string pendingAction: ""
    property var items: []
    property int total: 0
    property int page: 0
    property int pageSize: 80
    property string revision: ""
    property string status: "READY // OPEN TO SCAN SYSTEM TRASH"
    property string receipt: ""
    property bool lastError: false
    property bool indexReady: false

    // Visible "LIVE" means that GIO returned a successful full Trash index.
    // Merely opening the menu or starting a request never claims freshness.
    readonly property string liveLabel:
        !menuOpen ? "OFF"
        : busy ? (pendingAction === "index" || pendingAction === "index-live"
                  ? "SYNC" : "BUSY")
        : lastError ? "STALE"
        : indexReady ? "LIVE" : "WAIT"
    readonly property color liveColor:
        liveLabel === "LIVE" ? Colors.omnitrix
        : liveLabel === "STALE" ? Colors.red
        : Colors.orange

    property string confirmMode: "" // "" | "item" | "all"
    property string confirmUri: ""
    property string confirmOriginal: ""
    property string confirmName: ""
    property string confirmRevision: ""
    property int confirmCount: 0

    readonly property var filteredItems: items.filter(function(item) {
        const needle = String(trashSearch.text || "").trim().toLowerCase();
        if (!needle) return true;
        return (String(item.name) + " " + String(item.originLabel))
                .toLowerCase().indexOf(needle) !== -1;
    })

    function clearConfirmation() {
        confirmMode = "";
        confirmUri = "";
        confirmOriginal = "";
        confirmName = "";
        confirmRevision = "";
        confirmCount = 0;
    }

    function toggle() {
        menuOpen = !menuOpen;
        clearConfirmation();
        if (menuOpen) {
            // Open is visual/pointer-only. Do not steal keyboard ownership
            // from the currently focused desktop application.
            refresh(true);
        }
    }

    function run(action, args, passive) {
        if (busy) return false;
        busy = true;
        pendingAction = action;
        if (passive !== true) {
            lastError = false;
            status = "TRASH // " + action.toUpperCase() + " REQUESTED";
        }
        trashProcess.exec(["python3", "-I", "-B",
                           Quickshell.shellPath("scripts/trash/trash_cli.py")]
                          .concat(args));
        return true;
    }

    function refresh(clearReceipt, passive) {
        if (busy) return false;
        if (clearReceipt === true)
            receipt = "";
        // Passive polling never triggers destructive operations or overwrites
        // the user's most recent status while the inventory is unchanged.
        return run(passive === true ? "index-live" : "index",
                   ["index", String(page)], passive === true);
    }

    function consume(raw) {
        const action = pendingAction;
        if (!action) return;
        pendingAction = "";
        busy = false;
        let payload = null;
        try { payload = JSON.parse(String(raw || "").trim()); }
        catch (error) {
            lastError = true;
            status = "TRASH // INVALID BACKEND RESPONSE";
            return;
        }
        if (!payload || payload.ok !== true) {
            lastError = true;
            status = "TRASH // " + String(payload && payload.error
                                              || "BACKEND_UNAVAILABLE");
            // Keep the current queue for inspection; a failed operation never
            // implies items were restored or permanently deleted.
            return;
        }
        if (action === "index" || action === "index-live") {
            const nextRevision = String(payload.revision || "");
            const changed = !indexReady || nextRevision !== revision;
            // Keep delegates, cursor and scroll position intact when a live
            // poll reports exactly the same complete inventory.
            if (action === "index" || changed)
                items = Array.isArray(payload.items) ? payload.items : [];
            total = Number(payload.total) || 0;
            page = Number(payload.page) || 0;
            pageSize = Number(payload.pageSize) || 80;
            revision = nextRevision;
            indexReady = true;
            lastError = false;
            if (action === "index" || changed)
                status = receipt || ("TRASH // " + total + " ITEMS");
        } else {
            receipt = action === "restore"
                    ? "RESTORED // " + String(payload.name || "")
                    : action === "burn"
                    ? "BURNED // " + String(payload.name || "")
                    : "BURN ALL // COMPLETE";
            status = receipt;
            clearConfirmation();
            // One refresh after an explicit operation; never a background
            // polling timer and never a second destructive action.
            Qt.callLater(function() {
                if (trashLauncher.menuOpen && !trashLauncher.busy)
                    trashLauncher.refresh();
            });
        }
    }

    function restoreItem(item) {
        if (busy || !item) return;
        clearConfirmation();
        run("restore", ["restore", String(item.uri), String(item.original)]);
    }

    function armBurn(item) {
        if (busy || !item) return;
        clearConfirmation();
        confirmMode = "item";
        confirmUri = String(item.uri);
        confirmOriginal = String(item.original);
        confirmName = String(item.name);
    }

    function armBurnAll() {
        if (busy || total < 1 || revision.length !== 64) return;
        clearConfirmation();
        confirmMode = "all";
        confirmRevision = revision;
        confirmCount = total;
    }

    function confirmBurn() {
        if (busy) return;
        if (confirmMode === "item" && confirmUri) {
            run("burn", ["burn", confirmUri, confirmOriginal, "BURN_CONFIRMED"]);
        } else if (confirmMode === "all" && confirmCount > 0) {
            run("burn-all", ["burn-all", confirmRevision,
                             String(confirmCount), "BURN_ALL_CONFIRMED"]);
        }
    }

    IpcHandler {
        target: "trash"

        function toggle() {
            trashLauncher.toggle();
        }
    }

    // One immediate refresh is performed in toggle(). Then refresh only
    // while visible, every 15s, and never during an armed Burn or text edit.
    // Unchanged snapshots do not rebuild ListView delegates.
    Timer {
        id: trashLiveTimer
        interval: 15000
        repeat: true
        triggeredOnStart: false
        running: trashLauncher.menuOpen
        onTriggered: {
            if (trashLauncher.menuOpen && !trashLauncher.busy
                    && trashLauncher.confirmMode === ""
                    && !trashSearch.activeFocus)
                trashLauncher.refresh(false, true);
        }
    }

    Process {
        id: trashProcess
        running: false
        stdout: StdioCollector {
            onStreamFinished: trashLauncher.consume(this.text)
        }
        onExited: function(code, status) {
            const action = trashLauncher.pendingAction;
            // Missing Python or a crashed subprocess must never leave the
            // entire Trash panel stuck with disabled buttons.
            Qt.callLater(function() {
                if (trashLauncher.busy && trashLauncher.pendingAction === action) {
                    trashLauncher.pendingAction = "";
                    trashLauncher.busy = false;
                    trashLauncher.lastError = true;
                    trashLauncher.status = "TRASH // BACKEND PROCESS UNAVAILABLE";
                }
            });
        }
    }

    anchors {
        top: false
        bottom: true
        left: true
        right: false
    }

    // Power edge math: 10px outer + 15px inner = 25px from left;
    // 10px window bottom + 10px button offset = 20px from bottom.
    margins {
        top: 0
        bottom: 10
        left: 10
        right: 0
    }

    implicitWidth: frameWidth + 30
    implicitHeight: frameHeight + 90

    color: "transparent"
    // OnDemand allows the text filter to accept keyboard input when clicked,
    // without claiming Exclusive focus merely because the panel is open.
    WlrLayershell.keyboardFocus: menuOpen
                                    ? WlrKeyboardFocus.OnDemand
                                    : WlrKeyboardFocus.None
    focusable: menuOpen

    // Only the visible button and, when open, the panel take pointer input.
    mask: Region {
        Region {
            item: trashButton
        }

        Region {
            x: trashMenu.x
            y: trashMenu.y
            width: trashMenu.visible ? trashMenu.width : 0
            height: trashMenu.visible ? trashMenu.height : 0
        }
    }

    Item {
        id: trashArea
        width: trashLauncher.implicitWidth
        height: trashLauncher.implicitHeight
        anchors.left: parent.left
        anchors.bottom: parent.bottom

        DockButton {
            id: trashButton
            x: 15
            y: trashArea.height - 60
            width: 50
            height: 50
            z: 1
            radius: width / 100

            acceptedButtons: Qt.LeftButton
            open: trashLauncher.menuOpen

            // Match top-row DockButton glow strengths, radii and spreads
            // by inheriting its numeric defaults rather than Power's
            // intentionally subdued overrides. Color planes stay independent:
            // closed icon = white with Omnitrix sampled glow;
            // closed chassis = green; open = yellow + magenta icon/glows.
            normalForegroundColor: Colors.white
            hoverForegroundColor: Colors.white
            pressedForegroundColor: Colors.white
            openForegroundColor: Colors.magenta

            normalContentGlowColor: Colors.omnitrix
            hoverContentGlowColor: Colors.omnitrix
            pressedContentGlowColor: Colors.omnitrix

            normalDockGlowColor: Colors.green
            hoverDockGlowColor: Colors.green
            pressedDockGlowColor: Colors.green

            openFillColor: Colors.yellow
            openGlowColor: Colors.magenta

            // The sampled glow follows the actual rendered glyph at every
            // interaction state, instead of painting a detached silhouette.
            contentGlowSource: trashGlyph

            Text {
                id: trashGlyph
                anchors.centerIn: parent
                // Text-presentation variation keeps the glyph monochrome.
                text: "♻︎"
                font.pixelSize: 35
                color: trashButton.foregroundColor
            }

            onLeftClicked: trashLauncher.toggle()
        }
    }

    // Use the same reusable frame family as Finance/AppControl panels.
    // Burn arming affects only this panel's outline and halo; the dock's
    // magenta OPEN identity and the user's data are otherwise unchanged.
    WindowPanelFrame {
        id: trashMenu
        x: 15
        y: 15
        width: trashLauncher.frameWidth
        height: trashLauncher.frameHeight
        z: 1
        radius: 0
        fillColor: Colors.black
        fillOpacity: 0.95
        borderWidth: 1
        borderColor: trashLauncher.burnWarning ? Colors.orange : Colors.green
        glowVisible: trashLauncher.menuOpen
        glowColor: trashLauncher.burnWarning ? Colors.red : Colors.green
        closeGlowSpread: 6
        closeGlowOpacity: 0.56
        wideGlowSpread: 12
        wideGlowOpacity: 0.20

        visible: trashLauncher.menuOpen
        focus: false

        Keys.onPressed: function(event) {
            if (event.key === Qt.Key_Escape) {
                if (trashLauncher.confirmMode !== "")
                    trashLauncher.clearConfirmation();
                else
                    trashLauncher.menuOpen = false;
                event.accepted = true;
            }
        }

        Column {
            anchors.fill: parent
            anchors.margins: 9
            spacing: 6

            Row {
                width: parent.width
                height: 29
                spacing: 6

                GohuText {
                    width: parent.width - 184
                    height: parent.height
                    text: "TRASH // INDEX // " + trashLauncher.chassisSize.toUpperCase()
                    color: Colors.magenta
                    font.pixelSize: 14
                    verticalAlignment: Text.AlignVCenter
                    elide: Text.ElideRight
                }

                // Finance-style in-place size stepping: no extra window.
                ActionButton {
                    id: collapseTrashButton
                    width: 28
                    height: 28
                    label: "↓"
                    labelPixelSize: 17
                    accentColor: Colors.cyan
                    available: trashLauncher.chassisSize !== "compact"
                    onLeftClicked: trashLauncher.stepChassis(-1)
                }

                ActionButton {
                    id: expandTrashButton
                    width: 28
                    height: 28
                    label: "↑"
                    labelPixelSize: 17
                    accentColor: Colors.magenta
                    available: trashLauncher.chassisSize !== "full"
                    onLeftClicked: trashLauncher.stepChassis(1)
                }

                // This indicator is a real GIO index heartbeat, not a
                // decorative "online" claim. STALE is shown after failures.
                Rectangle {
                    id: trashLiveIndicator
                    width: 68
                    height: 27
                    color: Colors.dark
                    radius: 0
                    border.width: 1
                    border.color: trashLauncher.liveColor

                    GohuText {
                        anchors.centerIn: parent
                        text: "● " + trashLauncher.liveLabel
                        color: trashLauncher.liveColor
                        font.pixelSize: 10
                    }
                }

                // Finance red-close treatment, using the shared ActionButton
                // rather than duplicating free-standing shadows/MouseArea.
                ActionButton {
                    id: closeTrashButton
                    width: 34
                    height: 28
                    label: "×"
                    labelPixelSize: 20
                    contentPadding: 4
                    accentColor: Colors.red
                    destructive: true
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
                    onLeftClicked: trashLauncher.toggle()
                }
            }

            Rectangle {
                width: parent.width
                height: 2
                color: Colors.cyan
            }

            Row {
                width: parent.width
                height: 23
                spacing: 7

                GohuText {
                    width: parent.width - 104
                    height: 23
                    font.pixelSize: 11
                    color: Colors.white
                    verticalAlignment: Text.AlignVCenter
                    text: "SYSTEM TRASH // " + trashLauncher.total + " ITEMS"
                }

                ActionButton {
                    width: 97
                    height: 23
                    label: trashLauncher.busy ? "WORKING" : "REFRESH"
                    labelPixelSize: 10
                    accentColor: Colors.green
                    available: !trashLauncher.busy
                    onLeftClicked: trashLauncher.refresh(true)
                }
            }

            TextField {
                id: trashSearch
                width: parent.width
                height: 33
                placeholderText: "FILTER THIS PAGE // FILE NAME OR LOCATION"
                color: Colors.white
                font.pixelSize: 11
                placeholderTextColor: Colors.cyan
                selectionColor: Colors.magenta
                background: Rectangle {
                    color: Colors.dark
                    border.color: Colors.cyan
                    border.width: 1
                    radius: 0
                }
            }

            Item {
                id: trashListBox
                width: parent.width
                height: Math.max(100, trashMenu.height - 250
                                 - (trashLauncher.confirmMode !== "" ? 46 : 0))

                ListView {
                    id: trashFileList
                    width: parent.width - 18
                    height: parent.height
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds
                    spacing: 4
                    model: trashLauncher.filteredItems

                    delegate: Rectangle {
                        id: trashEntry
                        required property var modelData
                        width: trashFileList.width
                        height: 55
                        color: Colors.dark
                        border.width: 1
                        border.color: Colors.green
                        radius: 0

                        Column {
                            x: 6
                            y: 5
                            width: parent.width - 146
                            spacing: 3

                            GohuText {
                                width: parent.width
                                height: 19
                                text: String(trashEntry.modelData.name || "UNNAMED FILE")
                                color: Colors.white
                                font.pixelSize: 11
                                verticalAlignment: Text.AlignVCenter
                                elide: Text.ElideMiddle
                            }

                            GohuText {
                                width: parent.width
                                height: 17
                                text: String(trashEntry.modelData.originLabel || "")
                                color: Colors.cyan
                                font.pixelSize: 9
                                verticalAlignment: Text.AlignVCenter
                                elide: Text.ElideMiddle
                            }
                        }

                        Row {
                            anchors.right: parent.right
                            anchors.rightMargin: 5
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 5

                            ActionButton {
                                width: 68
                                height: 31
                                label: "RESTORE"
                                labelPixelSize: 10
                                accentColor: Colors.green
                                available: !trashLauncher.busy
                                onLeftClicked: trashLauncher.restoreItem(
                                                   trashEntry.modelData)
                            }

                            ActionButton {
                                width: 55
                                height: 31
                                label: "BURN"
                                labelPixelSize: 10
                                accentColor: Colors.red
                                destructive: true
                                available: !trashLauncher.busy
                                onLeftClicked: trashLauncher.armBurn(
                                                   trashEntry.modelData)
                            }
                        }
                    }
                }

                NeonScrollBar {
                    flickable: trashFileList
                    x: parent.width - width - 1
                    height: parent.height
                    geometryMode: "viewport"
                    handleStyle: "star"
                    visible: scrollable
                }

                GohuText {
                    anchors.centerIn: parent
                    visible: trashLauncher.filteredItems.length === 0
                    font.pixelSize: 11
                    color: Colors.cyan
                    text: trashLauncher.total === 0
                          ? "TRASH EMPTY // NOTHING TO RESTORE"
                          : "NO MATCHES ON THIS PAGE"
                }
            }

            Row {
                width: parent.width
                height: 26
                spacing: 6

                ActionButton {
                    width: 79
                    height: 26
                    label: "PREVIOUS"
                    labelPixelSize: 9
                    accentColor: Colors.cyan
                    available: !trashLauncher.busy && trashLauncher.page > 0
                    onLeftClicked: {
                        trashLauncher.page--;
                        trashLauncher.refresh(true);
                    }
                }

                GohuText {
                    width: parent.width - 170
                    height: 26
                    color: Colors.white
                    font.pixelSize: 10
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    text: "PAGE " + (trashLauncher.page + 1) + " // "
                          + Math.max(1, Math.ceil(trashLauncher.total
                                                  / trashLauncher.pageSize))
                }

                ActionButton {
                    width: 79
                    height: 26
                    label: "NEXT"
                    labelPixelSize: 9
                    accentColor: Colors.cyan
                    available: !trashLauncher.busy
                               && (trashLauncher.page + 1)
                                  * trashLauncher.pageSize < trashLauncher.total
                    onLeftClicked: {
                        trashLauncher.page++;
                        trashLauncher.refresh(true);
                    }
                }
            }

            Row {
                width: parent.width
                height: 32
                spacing: 8

                GohuText {
                    width: parent.width - 125
                    height: 32
                    color: Colors.cyan
                    font.pixelSize: 10
                    verticalAlignment: Text.AlignVCenter
                    text: "RESTORE // RECOVERABLE"
                }

                ActionButton {
                    width: 117
                    height: 32
                    label: "BURN ALL"
                    labelPixelSize: 11
                    accentColor: Colors.red
                    destructive: true
                    available: !trashLauncher.busy && trashLauncher.total > 0
                               && trashLauncher.revision.length === 64
                    onLeftClicked: trashLauncher.armBurnAll()
                }
            }

            Rectangle {
                width: parent.width
                height: trashLauncher.confirmMode === "" ? 0 : 40
                visible: trashLauncher.confirmMode !== ""
                color: Colors.dark
                border.width: 1
                border.color: Colors.red

                Row {
                    anchors.fill: parent
                    anchors.margins: 4
                    spacing: 5

                    GohuText {
                        width: parent.width - 179
                        height: parent.height
                        color: Colors.yellow
                        font.pixelSize: 10
                        verticalAlignment: Text.AlignVCenter
                        elide: Text.ElideRight
                        text: trashLauncher.confirmMode === "all"
                              ? "BURN ALL " + trashLauncher.confirmCount
                                + " ITEMS? // IRREVERSIBLE"
                              : "BURN // " + trashLauncher.confirmName
                    }

                    ActionButton {
                        width: 71
                        height: 29
                        label: "CANCEL"
                        labelPixelSize: 9
                        accentColor: Colors.cyan
                        onLeftClicked: trashLauncher.clearConfirmation()
                    }

                    ActionButton {
                        width: 98
                        height: 29
                        label: "CONFIRM BURN"
                        labelPixelSize: 9
                        accentColor: Colors.red
                        destructive: true
                        available: !trashLauncher.busy
                        onLeftClicked: trashLauncher.confirmBurn()
                    }
                }
            }

            GohuText {
                width: parent.width
                height: 21
                font.pixelSize: 10
                color: trashLauncher.lastError ? Colors.red : Colors.yellow
                elide: Text.ElideRight
                verticalAlignment: Text.AlignVCenter
                text: trashLauncher.status
            }
        }
    }
}
