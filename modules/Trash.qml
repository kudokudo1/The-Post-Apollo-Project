import Quickshell
import QtQuick
import QtQuick.Controls
import Quickshell.Io
import Quickshell.Wayland
import "../components"
import "../widgets"

// TRASH // Bottom-left utility backed by the user's existing GIO Trash.
// The 50x50 dock button retains Power's exact edge clearances; the panel is
// larger independently, as required by the dock/widget composition contract.
PanelWindow {
    id: trashLauncher

    property bool menuOpen: false
    // Lifecycle navigation is presentation-only until owner-specific
    // record adapters are approved. Only "trash" has destructive authority.
    property string activeMode: "trash"
    readonly property var lifecycleModes: ["cleanup", "archive", "trash", "burn"]

    // The Cleanup UI itself now lives here; CameraW supplies only its
    // established scan, queue, preview and recoverable file operation logic.
    property var cameraCleanupController: null
    readonly property var cleanupContentView: cleanupViewLoader.item
    property int cameraCleanupQueueCount: 0
    property bool cameraCleanupBusy: false

    // Universal record inventory v1. Read-only and source-owned. The index
    // carries NO archive/trash/burn actions for Weather or demo web scrapes.
    property var archiveRows: []
    property var archiveSources: []
    property bool archiveBusy: false
    property string archiveState: "NOT_SCANNED"
    property string archiveFilter: "all"
    property string archiveSearchText: ""

    // Trash++-owned local research copies are separate from source records.
    // Finance's original DEMO crawl stays read-only, and Hospital/Weather are
    // never write targets. Revision increments protect concurrent changes.
    property var researchRows: []
    property int researchRevision: 0
    property int researchBinCount: 0
    property string researchBinDigest: ""
    property bool researchBusy: false
    property string researchPending: ""
    property string researchState: "NOT_SCANNED"
    property string researchBurnId: ""
    property string researchBurnScope: "" // "" | "copy" | "all"
    property string researchBurnTitle: ""
    property int researchBurnRevision: -1
    property int researchBurnCount: 0
    property string researchBurnDigest: ""
    property bool researchBurnPointerRelocated: false
    property bool researchBurnClickArmed: false
    property bool researchBurnLoadComplete: false
    property real researchBurnLoadProgress: 0

    // One Burn view + one confirmation + one post-operation receipt.
    // System files remain GIO-owned; copies remain managed-store-owned.
    property string burnFilter: "all" // all | files | records | events | research
    property string burnUiStage: "" // "" | clicked | working | result | error
    property var burnReceiptItems: []
    property int burnReceiptCount: 0
    property int burnReceiptRequested: 0
    property bool burnReceiptVerified: false
    property string burnReceiptMessage: ""
    property string burnReceiptScope: ""
    readonly property bool burnConfirmationOpen:
        confirmMode !== "" || researchBurnId !== "" || burnUiStage !== ""
    readonly property var burnDisplayRows: {
        const fileRows = (burnFilter === "all" || burnFilter === "files")
            ? items.map(function(row) {
                return {entryType:"file", title:row.name, name:row.name,
                        original:row.original, uri:row.uri,
                        originLabel:row.originLabel};
            }) : [];
        const copyRows = researchBinRows.filter(function(row) {
            return burnFilter !== "files"
                   && (burnFilter !== "events" || row.kind === "SAVED EVENT")
                   && (burnFilter !== "research" || row.kind === "SAVED RESEARCH");
        }).map(function(row) {
            return {entryType:"record", title:row.title, record:row,
                    originLabel:row.source + " // " + row.recordedAt};
        });
        return fileRows.concat(copyRows);
    }

    function showBurnReceipt(payload, scope, attempted) {
        // Accept only an explicit backend outcome, never a guessed success.
        const list = payload && Array.isArray(payload.burnedItems)
            ? payload.burnedItems : [];
        burnReceiptItems = list.slice(0, 2500).map(function(row) {
            return {name:String(row.name || "UNNAMED"),
                    kind:String(row.kind || "UNKNOWN"),
                    source:String(row.source || row.original || "")};
        });
        burnReceiptCount = burnReceiptItems.length;
        burnReceiptRequested = attempted;
        burnReceiptVerified = payload && payload.verified === true
                              && payload.partial !== true
                              && burnReceiptCount === attempted;
        burnReceiptScope = scope;
        burnReceiptMessage = burnReceiptVerified
            ? "BURN VERIFIED // " + burnReceiptCount + " ITEMS"
            : "PARTIAL OR UNVERIFIED // "
              + burnReceiptCount + " CONFIRMED OF " + attempted;
        burnUiStage = "result";
        activeMode = "burn";
    }

    function failBurnReceipt(message) {
        burnReceiptVerified = false;
        burnReceiptMessage = "NOT CONFIRMED // "
                             + String(message || "BACKEND UNAVAILABLE");
        burnUiStage = "error";
        activeMode = "burn";
    }

    function dismissBurnReceipt() {
        if (burnUiStage === "working" || burnUiStage === "clicked")
            return false;
        burnCommitDelay.stop();
        clearConfirmation();
        clearResearchBurn();
        burnUiStage = "";
        burnReceiptItems = [];
        burnReceiptCount = 0;
        burnReceiptRequested = 0;
        burnReceiptVerified = false;
        burnReceiptMessage = "";
        burnReceiptScope = "";
        activeMode = "burn";
        return true;
    }

    readonly property var researchBinRows: researchRows.filter(function(row) {
        return row.state === "trashed";
    })
    readonly property var archiveFilteredRows: archiveRows.concat(researchRows).filter(function(row) {
        const selected = archiveFilter;
        if (selected === "events" && row.kind !== "EVENT HISTORY") return false;
        if (selected === "dossiers" && row.kind !== "SAVED DOSSIER") return false;
        if (selected === "scrapes" && row.kind !== "WEB SCRAPE") return false;
        if (selected === "copies" && ((row.kind !== "SAVED RESEARCH"
                                      && row.kind !== "SAVED EVENT")
                                      || row.state !== "archived")) return false;
        if (selected === "bin" && ((row.kind !== "SAVED RESEARCH"
                                   && row.kind !== "SAVED EVENT")
                                   || row.state !== "trashed")) return false;
        const q = archiveSearchText.trim().toLowerCase();
        return !q || (String(row.title) + " " + String(row.source)
                      + " " + String(row.details) + " " + String(row.id))
                     .toLowerCase().indexOf(q) >= 0;
    })

    function refreshArchive() {
        if (!menuOpen || activeMode !== "archive" || archiveBusy)
            return false;
        archiveBusy = true;
        archiveState = "SCANNING";
        archiveProcess.exec([
            "python3", "-I", "-B",
            Quickshell.shellPath("scripts/trash/record_index.py"),
            "index", Quickshell.dataDir
        ]);
        return true;
    }

    function consumeArchive(raw) {
        if (!archiveBusy)
            return;
        archiveBusy = false;
        let reply = null;
        try { reply = JSON.parse(String(raw || "").trim()); }
        catch (error) {
            archiveState = "STALE // INVALID INDEX RESPONSE";
            return;
        }
        if (!reply || reply.ok !== true || reply.kind !== "record-index"
                || reply.readOnly !== true
                || !Array.isArray(reply.items) || !Array.isArray(reply.sources)) {
            archiveState = "STALE // SOURCE INDEX UNAVAILABLE";
            return;
        }
        archiveRows = reply.items;
        archiveSources = reply.sources;
        archiveState = "READY";
    }

    function runResearch(action, args) {
        if (!menuOpen || researchBusy
                || (researchBurnId !== ""
                    && !(burnUiStage === "working"
                         && ["burn", "burn-all"].indexOf(action) >= 0))
                || (activeMode !== "archive" && activeMode !== "burn"
                    && !(activeMode === "trash"
                         && ["list", "restore", "burn"].indexOf(action) >= 0)))
            return false;
        if (["list", "archive", "archive-event", "trash", "restore", "burn",
             "burn-all"].indexOf(action) < 0)
            return false;
        if (activeMode === "trash"
                && ["list", "restore", "burn"].indexOf(action) < 0)
            return false;
        researchBusy = true;
        researchPending = action;
        researchState = action.toUpperCase() + " // REQUESTED";
        researchProcess.exec([
            "python3", "-I", "-B",
            Quickshell.shellPath("scripts/trash/research_records.py"),
            action, Quickshell.dataDir
        ].concat(args || []));
        return true;
    }

    function refreshResearch() {
        if (researchBurnId !== "")
            return false;
        return runResearch("list", []);
    }

    function consumeResearch(raw) {
        if (!researchBusy)
            return;
        const action = researchPending;
        researchPending = "";
        researchBusy = false;
        let payload = null;
        try { payload = JSON.parse(String(raw || "").trim()); }
        catch (error) {
            researchState = "STALE // INVALID MANAGED RESPONSE";
            if (action === "burn" || action === "burn-all")
                failBurnReceipt(researchState);
            return;
        }
        if (!payload || payload.ok !== true
                || payload.kind !== "managed-research"
                || !Array.isArray(payload.items)
                || typeof payload.revision !== "number"
                || typeof payload.binCount !== "number"
                || typeof payload.binDigest !== "string") {
            researchState = "STALE // " + String(payload && payload.error
                                                || "RESEARCH STORE UNAVAILABLE");
            if (action === "burn" || action === "burn-all")
                failBurnReceipt(researchState);
            return;
        }
        researchRows = payload.items;
        researchRevision = payload.revision;
        researchBinCount = payload.binCount;
        researchBinDigest = payload.binDigest;
        researchState = action === "list" ? "READY // SAVED RESEARCH"
                                         : action.toUpperCase() + " // COMPLETE";
        if (action === "burn" || action === "burn-all") {
            const expected = researchBurnScope === "all"
                             ? researchBurnCount : 1;
            showBurnReceipt(payload, researchBurnScope === "all"
                            ? "MANAGED COPIES // ALL" : "MANAGED COPY",
                            expected);
        }
    }

    function saveDemoCopy(row) {
        if (!row || row.kind !== "WEB SCRAPE" || !row.sourceUrl
                || !row.sourceObservedAt)
            return false;
        return runResearch("archive", [
            String(row.sourceUrl), String(row.sourceObservedAt),
            String(researchRevision)
        ]);
    }

    function saveWeatherEventCopy(row) {
        if (!row || row.kind !== "EVENT HISTORY"
                || !row.sourceEventKey
                || typeof row.sourceLastCapturedAtMs !== "number")
            return false;
        return runResearch("archive-event", [
            String(row.sourceEventKey),
            String(row.sourceLastCapturedAtMs),
            String(researchRevision)
        ]);
    }

    function trashResearchCopy(row) {
        if (!row || (row.kind !== "SAVED RESEARCH"
                      && row.kind !== "SAVED EVENT")
                || row.state !== "archived")
            return false;
        return runResearch("trash", [String(row.id), String(researchRevision)]);
    }

    function restoreResearchCopy(row) {
        if (!row || (row.kind !== "SAVED RESEARCH"
                      && row.kind !== "SAVED EVENT")
                || row.state !== "trashed")
            return false;
        return runResearch("restore", [String(row.id), String(researchRevision)]);
    }

    function clearResearchBurn() {
        researchBurnArmAnimation.stop();
        researchBurnId = "";
        researchBurnScope = "";
        researchBurnTitle = "";
        researchBurnRevision = -1;
        researchBurnCount = 0;
        researchBurnDigest = "";
        researchBurnPointerRelocated = false;
        researchBurnClickArmed = false;
        researchBurnLoadComplete = false;
        researchBurnLoadProgress = 0;
    }

    function armResearchBurn(row) {
        if (!menuOpen || researchBusy || busy || confirmMode !== ""
                || researchBurnId !== "" || burnUiStage !== ""
                || !row || (row.kind !== "SAVED RESEARCH"
                            && row.kind !== "SAVED EVENT")
                || row.state !== "trashed"
                || researchRows.findIndex(function(r) {
                       return r.id === row.id && r.state === "trashed";
                   }) < 0)
            return false;
        researchBurnId = String(row.id);
        researchBurnScope = "copy";
        researchBurnTitle = String(row.title);
        researchBurnRevision = researchRevision;
        researchBurnPointerRelocated = false;
        researchBurnClickArmed = false;
        researchBurnLoadComplete = false;
        researchBurnLoadProgress = 0;
        activeMode = "burn";
        return true;
    }

    function armResearchBurnAll() {
        if (!menuOpen || activeMode !== "burn" || researchBusy || busy
                || confirmMode !== "" || researchBurnId !== ""
                || burnUiStage !== "" || researchBinCount < 1
                || researchBinCount !== researchBinRows.length
                || researchBinDigest.length !== 64)
            return false;
        researchBurnId = "__managed_bin_all__"; // impossible record ID
        researchBurnScope = "all";
        researchBurnTitle = researchBinCount + " TRASHED MANAGED COPIES";
        researchBurnCount = researchBinCount;
        researchBurnDigest = researchBinDigest;
        researchBurnRevision = researchRevision;
        researchBurnPointerRelocated = false;
        researchBurnClickArmed = false;
        researchBurnLoadComplete = false;
        researchBurnLoadProgress = 0;
        return true;
    }

    function advanceResearchBurn() {
        const isFile = confirmMode === "item" || confirmMode === "all";
        const isCopy = researchBurnId !== "";
        if (burnUiStage !== "" || (!isFile && !isCopy)
                || !researchBurnPointerRelocated || researchBusy || busy
                || (isCopy && researchBurnRevision !== researchRevision)
                || (isFile && confirmMode === "all"
                    && (confirmRevision !== revision
                        || confirmCount !== total)))
            return false;
        if (!researchBurnClickArmed) {
            researchBurnClickArmed = true;
            researchBurnLoadComplete = false;
            researchBurnLoadProgress = 0;
            researchBurnArmAnimation.restart();
            return true;
        }
        if (!researchBurnLoadComplete)
            return false;
        // Display the clicked magenta feedback first. Deletion starts only
        // after a separate short, visible feedback interval.
        burnUiStage = "clicked";
        burnCommitDelay.restart();
        return true;
    }

    function confirmResearchBurn() {
        if (!researchBurnId || !researchBurnPointerRelocated
                || !researchBurnClickArmed || !researchBurnLoadComplete
                || burnUiStage !== "working"
                || researchBurnRevision !== researchRevision
                || researchBusy || busy)
            return false;
        if (researchBurnScope === "all") {
            if (activeMode !== "burn"
                    || researchBurnCount < 1
                    || researchBurnCount !== researchBinCount
                    || researchBurnCount !== researchBinRows.length
                    || researchBurnDigest !== researchBinDigest)
                return false;
            const rev = researchBurnRevision;
            const count = researchBurnCount;
            const digest = researchBurnDigest;
            return runResearch("burn-all", [
                String(rev), String(count), digest,
                "BURN_ALL_MANAGED_COPIES_CONFIRMED"
            ]);
        }
        if (researchBurnScope !== "copy"
                || researchRows.findIndex(function(row) {
                    return row.id === researchBurnId && row.state === "trashed";
                }) < 0)
            return false;
        const id = researchBurnId;
        const rev = researchBurnRevision;
        return runResearch("burn", [
            id, String(rev), "BURN_SAVED_COPY_CONFIRMED"
        ]);
    }

    function requestCameraCleanup(technique) {
        const requested = String(technique || "");
        if (!menuOpen || activeMode !== "cleanup" || confirmMode !== ""
                || cameraCleanupBusy || !cameraCleanupController
                || ["batch", "grid", "swipe", "hunt", "desktop", "queue"]
                    .indexOf(requested) < 0)
            return false;
        const accepted = cameraCleanupController.openCleanupFromTrash(requested);
        if (!accepted) {
            status = "CLEANUP // CAMERA SCAN BUSY OR UNAVAILABLE";
            return false;
        }
        status = "CLEANUP // " + requested.toUpperCase()
                 + " // SHARED CAMERA QUEUE";
        return true;
    }

    function setMode(nextMode) {
        const requested = String(nextMode || "");
        if (busy || researchBusy || confirmMode !== ""
                || researchBurnId !== "" || burnUiStage !== ""
                || lifecycleModes.indexOf(requested) < 0)
            return false;
        if (requested === "cleanup" && activeMode !== "cleanup") {
            if (!cameraCleanupController || cameraCleanupBusy
                    || !cameraCleanupController.openCleanupFromTrash("batch")) {
                status = "CLEANUP // CAMERA SCAN BUSY OR UNAVAILABLE";
                return false;
            }
        }
        if (activeMode === "cleanup" && requested !== "cleanup"
                && cameraCleanupController)
            cameraCleanupController.suspendHostedCleanup();
        activeMode = requested;
        if (menuOpen)
            Qt.callLater(function() {
                if (trashLauncher.activeMode === "archive") {
                    trashLauncher.refreshArchive();
                    trashLauncher.refreshResearch();
                } else if (trashLauncher.activeMode === "burn"
                           || trashLauncher.activeMode === "trash")
                    trashLauncher.refreshResearch();
            });
        return true;
    }

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
        || pendingAction === "burn-all" || researchBurnId !== ""
        || researchPending === "burn" || researchPending === "burn-all"
        || burnUiStage !== ""

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
    property bool burnAllPointerRelocated: false

    // One visual Trash list. Files still use GIO and saved records still
    // use the isolated, revision-controlled managed-copy backend.
    property string trashViewFilter: "all"
    readonly property bool trashShowsFiles:
        trashViewFilter === "all" || trashViewFilter === "files"
    readonly property var trashDisplayRows: {
        const fileRows = trashShowsFiles
            ? filteredItems.map(function(item) {
                return {entryType:"file", name:item.name,
                        originLabel:item.originLabel, uri:item.uri,
                        original:item.original};
            }) : [];
        const needle = String(trashSearch.text || "").trim().toLowerCase();
        const copyRows = researchBinRows.filter(function(row) {
            if (trashViewFilter === "files") return false;
            if (trashViewFilter === "events" && row.kind !== "SAVED EVENT")
                return false;
            if (trashViewFilter === "research" && row.kind !== "SAVED RESEARCH")
                return false;
            return !needle || (String(row.title) + " " + String(row.source)
                               + " " + String(row.details) + " " + String(row.id))
                               .toLowerCase().indexOf(needle) >= 0;
        }).map(function(row) {
            return {entryType:"record", name:row.title, kind:row.kind,
                    originLabel:row.source + " // " + row.recordedAt,
                    record:row};
        });
        return fileRows.concat(copyRows);
    }

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
        burnAllPointerRelocated = false;
    }

    function toggle() {
        if (burnUiStage === "clicked" || burnUiStage === "working"
                || burnUiStage === "result" || burnUiStage === "error")
            return false;
        menuOpen = !menuOpen;
        clearConfirmation();
        clearResearchBurn();
        if (menuOpen) {
            // Opening keeps the existing one-shot Trash inventory refresh.
            // Cleanup is hosted here; never open a separate Camera panel.
            refresh(true);
            if (activeMode === "cleanup" && cameraCleanupController)
                cameraCleanupController.openCleanupFromTrash(
                    cameraCleanupController.cleanupTechnique);
            if (activeMode === "archive")
                Qt.callLater(function() {
                    trashLauncher.refreshArchive();
                    trashLauncher.refreshResearch();
                });
            else if (activeMode === "burn" || activeMode === "trash")
                Qt.callLater(function() { trashLauncher.refreshResearch(); });
        }
    }

    onMenuOpenChanged: {
        if (!menuOpen) {
            burnCommitDelay.stop();
            burnUiStage = "";
            clearConfirmation();
            clearResearchBurn();
            if (cameraCleanupController)
                cameraCleanupController.suspendHostedCleanup();
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
            if (action === "burn" || action === "burn-all")
                failBurnReceipt(status);
            return;
        }
        if (!payload || payload.ok !== true) {
            lastError = true;
            status = "TRASH // " + String(payload && payload.error
                                              || "BACKEND_UNAVAILABLE");
            // A failed operation never implies items were deleted.
            if (action === "burn" || action === "burn-all")
                failBurnReceipt(status);
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
            if (action === "burn" || action === "burn-all") {
                const expected = action === "burn" ? 1 : confirmCount;
                showBurnReceipt(payload, action === "burn"
                                ? "SYSTEM TRASH // FILE" : "SYSTEM TRASH // ALL",
                                expected);
                receipt = burnReceiptMessage;
            } else {
                receipt = "RESTORED // " + String(payload.name || "");
            }
            status = receipt;
            // Refresh inventory WITHOUT dismissing the confirmed result.
            Qt.callLater(function() {
                if (trashLauncher.menuOpen && !trashLauncher.busy)
                    trashLauncher.refresh(false, true);
            });
        }
    }

    function restoreItem(item) {
        if (busy || !item) return;
        clearConfirmation();
        run("restore", ["restore", String(item.uri), String(item.original)]);
    }

    function armBurn(item) {
        if (!menuOpen || busy || researchBusy || !item
                || confirmMode !== "" || researchBurnId !== ""
                || burnUiStage !== "")
            return false;
        clearConfirmation();
        clearResearchBurn();
        confirmMode = "item";
        confirmUri = String(item.uri);
        confirmOriginal = String(item.original);
        confirmName = String(item.name);
        activeMode = "burn";
        return true;
    }

    function armBurnAll() {
        if (!menuOpen || activeMode !== "burn" || burnFilter !== "files"
                || busy || researchBusy || total < 1 || revision.length !== 64
                || confirmMode !== "" || researchBurnId !== ""
                || burnUiStage !== "")
            return false;
        clearConfirmation();
        clearResearchBurn();
        confirmMode = "all";
        confirmRevision = revision;
        confirmCount = total;
        burnAllPointerRelocated = false;
        return true;
    }

    function confirmBurn() {
        if (busy || researchBusy || burnUiStage !== "working"
                || !researchBurnPointerRelocated
                || !researchBurnClickArmed || !researchBurnLoadComplete)
            return false;
        if (confirmMode === "item" && confirmUri) {
            return run("burn", ["burn", confirmUri, confirmOriginal,
                                "BURN_CONFIRMED"]);
        }
        if (confirmMode === "all" && confirmCount > 0
                && activeMode === "burn"
                && confirmRevision === revision
                && confirmCount === total) {
            // Same spatial/two-click modal as managed-copy Burn. GIO
            // independently revalidates count and revision.
            return run("burn-all", ["burn-all", confirmRevision,
                                    String(confirmCount),
                                    "BURN_ALL_CONFIRMED"]);
        }
        return false;
    }


    IpcHandler {
        target: "trash"

        function toggle() {
            trashLauncher.toggle();
        }
    }

    // The search field may retain activeFocus even when the operator is not
    // typing. Never let that suppress every live refresh. Updating the list
    // does not clear the filter's text, focus, or insertion position.
    // This timer is a fallback if the GIO watcher cannot deliver an event.
    Timer {
        id: trashLiveTimer
        interval: 15000
        repeat: true
        triggeredOnStart: false
        running: trashLauncher.menuOpen
        onTriggered: {
            if (trashLauncher.menuOpen && !trashLauncher.busy
                    && trashLauncher.confirmMode === "")
                trashLauncher.refresh(false, true);
        }
    }

    // GIO's virtual trash:/// directory can be monitored across mounts.
    // Debounce bursts of create/remove signals into ONE read-only index
    // request; there is no filesystem write or Burn action on an event.
    Timer {
        id: trashEventDebounce
        interval: 450
        repeat: false
        onTriggered: {
            if (trashLauncher.menuOpen && !trashLauncher.busy
                    && trashLauncher.confirmMode === "")
                trashLauncher.refresh(false, true);
        }
    }

    Process {
        id: trashChangeMonitor
        command: ["gio", "monitor", "--dir=trash:///"]
        running: trashLauncher.menuOpen
        stdout: SplitParser {
            onRead: function(data) {
                if (trashLauncher.menuOpen && String(data || "").trim() !== "")
                    trashEventDebounce.restart();
            }
        }
    }

    // Separate process, separate stdout and no shared destructive command
    // channel. This process can only run the read-only record-index command.
    Process {
        id: archiveProcess
        running: false
        stdout: StdioCollector {
            onStreamFinished: trashLauncher.consumeArchive(this.text)
        }
        onExited: function(code, status) {
            Qt.callLater(function() {
                if (trashLauncher.archiveBusy) {
                    trashLauncher.archiveBusy = false;
                    trashLauncher.archiveState = "STALE // INDEX PROCESS FAILED";
                }
            });
        }
    }

    // First remote click visibly loads before the destructive second click.
    NumberAnimation {
        id: researchBurnArmAnimation
        target: trashLauncher
        property: "researchBurnLoadProgress"
        from: 0
        to: 1
        duration: 850
        easing.type: Easing.Linear
        onFinished: {
            if (trashLauncher.researchBurnId !== ""
                    && trashLauncher.researchBurnClickArmed)
                trashLauncher.researchBurnLoadComplete = true;
        }
    }

    // The second click gets a visible magenta feedback pulse before the
    // actual subprocess begins. Cancelling or closing never commits.
    Timer {
        id: burnCommitDelay
        interval: 420
        repeat: false
        onTriggered: {
            if (!trashLauncher.menuOpen || trashLauncher.burnUiStage !== "clicked")
                return;
            trashLauncher.burnUiStage = "working";
            const accepted = trashLauncher.confirmMode !== ""
                ? trashLauncher.confirmBurn()
                : trashLauncher.confirmResearchBurn();
            if (!accepted)
                trashLauncher.failBurnReceipt("STALE OR UNAVAILABLE BURN TARGET");
        }
    }

    // Dedicated writer for ONLY Trash++'s managed demo research copies.
    // It never shares the GIO file-deletion process or Finance crawler writer.
    Process {
        id: researchProcess
        running: false
        stdout: StdioCollector {
            onStreamFinished: trashLauncher.consumeResearch(this.text)
        }
        onExited: function(code, status) {
            const action = trashLauncher.researchPending;
            Qt.callLater(function() {
                if (trashLauncher.researchBusy
                        && trashLauncher.researchPending === action) {
                    trashLauncher.researchBusy = false;
                    trashLauncher.researchPending = "";
                    trashLauncher.researchState = "STALE // RESEARCH PROCESS FAILED";
                    if (action === "burn" || action === "burn-all")
                        trashLauncher.failBurnReceipt(trashLauncher.researchState);
                }
            });
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
                    if (action === "burn" || action === "burn-all")
                        trashLauncher.failBurnReceipt(trashLauncher.status);
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
                if (trashLauncher.researchBurnId !== "")
                    trashLauncher.clearResearchBurn();
                else if (trashLauncher.confirmMode !== "")
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
                    text: "TRASH++ // " + trashLauncher.activeMode.toUpperCase()
                          + " // " + trashLauncher.chassisSize.toUpperCase()
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
                id: trashLifecycleModes
                width: parent.width
                height: 28
                spacing: 5

                Repeater {
                    model: ["CLEANUP", "ARCHIVE", "TRASH", "BURN"]
                    delegate: ActionButton {
                        required property string modelData
                        width: (trashLifecycleModes.width - 15) / 4
                        height: 28
                        label: modelData
                        labelPixelSize: 10
                        accentColor: modelData === "BURN"
                                     ? Colors.red : Colors.cyan
                        selected: trashLauncher.activeMode
                                  === modelData.toLowerCase()
                        available: !trashLauncher.busy
                        onLeftClicked: trashLauncher.setMode(
                                           modelData.toLowerCase())
                    }
                }
            }

            Row {
                width: parent.width
                height: 23
                visible: trashLauncher.activeMode === "trash"
                spacing: 7

                GohuText {
                    width: parent.width - 203
                    height: 23
                    font.pixelSize: 10
                    color: Colors.white
                    verticalAlignment: Text.AlignVCenter
                    text: "FILES " + trashLauncher.total
                          + " // RECORDS " + trashLauncher.researchBinRows.length
                }

                ActionButton {
                    width: 92
                    height: 23
                    label: "RECORD BIN " + trashLauncher.researchBinRows.length
                    labelPixelSize: 9
                    accentColor: Colors.orange
                    available: !trashLauncher.researchBusy
                    onLeftClicked: trashLauncher.trashViewFilter = "records"
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
                visible: trashLauncher.activeMode === "trash"
                width: parent.width
                height: 33
                placeholderText: "SEARCH TRASH // FILES, EVENTS OR RESEARCH COPIES"
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

            Row {
                id: trashSourceFilters
                width: parent.width
                height: 27
                spacing: 4
                visible: trashLauncher.activeMode === "trash"

                Repeater {
                    model: [
                        {id:"all", label:"ALL"},
                        {id:"files", label:"FILES"},
                        {id:"records", label:"RECORDS"},
                        {id:"events", label:"EVENTS"},
                        {id:"research", label:"RESEARCH"}
                    ]
                    ActionButton {
                        required property var modelData
                        width: (trashSourceFilters.width - 16) / 5
                        height: 26
                        label: modelData.label
                        labelPixelSize: 9
                        accentColor: modelData.id === "files"
                                     ? Colors.cyan
                                     : modelData.id === "records"
                                     ? Colors.orange : Colors.magenta
                        selected: trashLauncher.trashViewFilter === modelData.id
                        onLeftClicked: trashLauncher.trashViewFilter = modelData.id
                    }
                }
            }

            Item {
                id: trashListBox
                visible: trashLauncher.activeMode === "trash"
                width: parent.width
                height: Math.max(90, trashMenu.height - 323
                                 - (trashLauncher.confirmMode === "item" ? 46 : 0))

                ListView {
                    id: trashFileList
                    width: parent.width - 18
                    height: parent.height
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds
                    spacing: 4
                    model: trashLauncher.trashDisplayRows

                    delegate: Rectangle {
                        id: trashEntry
                        required property var modelData
                        width: trashFileList.width
                        height: 55
                        color: Colors.dark
                        border.width: 1
                        border.color: trashEntry.modelData.entryType === "record"
                                      ? Colors.orange : Colors.green
                        radius: 0

                        Column {
                            x: 6
                            y: 5
                            width: parent.width - 146
                            spacing: 3

                            GohuText {
                                width: parent.width
                                height: 19
                                text: (trashEntry.modelData.entryType === "record"
                                       ? "[COPY] " : "[FILE] ")
                                      + String(trashEntry.modelData.name || "UNNAMED")
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
                                           && !trashLauncher.researchBusy
                                           && trashLauncher.researchBurnId === ""
                                onLeftClicked: {
                                    if (trashEntry.modelData.entryType === "record")
                                        trashLauncher.restoreResearchCopy(
                                            trashEntry.modelData.record);
                                    else
                                        trashLauncher.restoreItem(
                                            trashEntry.modelData);
                                }
                            }

                            ActionButton {
                                width: 55
                                height: 31
                                label: trashEntry.modelData.entryType === "record"
                                       ? "BURN COPY" : "BURN"
                                labelPixelSize: 9
                                accentColor: Colors.red
                                destructive: true
                                available: !trashLauncher.busy
                                           && !trashLauncher.researchBusy
                                           && trashLauncher.researchBurnId === ""
                                onLeftClicked: {
                                    if (trashEntry.modelData.entryType === "record")
                                        trashLauncher.armResearchBurn(
                                            trashEntry.modelData.record);
                                    else
                                        trashLauncher.armBurn(
                                            trashEntry.modelData);
                                }
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
                    visible: trashLauncher.trashDisplayRows.length === 0
                    font.pixelSize: 11
                    color: Colors.cyan
                    text: trashLauncher.total === 0
                          && trashLauncher.researchBinRows.length === 0
                          ? "TRASH EMPTY // NOTHING TO RESTORE"
                          : "NO MATCHES // CHOOSE A SOURCE FILTER"
                }
            }

            Row {
                width: parent.width
                height: 26
                visible: trashLauncher.activeMode === "trash"
                spacing: 6

                ActionButton {
                    width: 79
                    height: 26
                    label: "PREVIOUS"
                    labelPixelSize: 9
                    accentColor: Colors.cyan
                    available: trashLauncher.trashShowsFiles
                               && !trashLauncher.busy && trashLauncher.page > 0
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
                    text: trashLauncher.trashShowsFiles
                          ? "FILE PAGE " + (trashLauncher.page + 1) + " // "
                            + Math.max(1, Math.ceil(trashLauncher.total
                                                    / trashLauncher.pageSize))
                          : "MANAGED BIN // " + trashLauncher.trashDisplayRows.length
                }

                ActionButton {
                    width: 79
                    height: 26
                    label: "NEXT"
                    labelPixelSize: 9
                    accentColor: Colors.cyan
                    available: trashLauncher.trashShowsFiles
                               && !trashLauncher.busy
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
                visible: trashLauncher.activeMode === "trash"
                spacing: 8

                GohuText {
                    width: parent.width - 125
                    height: 32
                    color: Colors.cyan
                    font.pixelSize: 10
                    verticalAlignment: Text.AlignVCenter
                    text: "RESTORE HERE // BURN IN ONE WORKSPACE"
                }

                ActionButton {
                    width: 117
                    height: 32
                    label: "OPEN BURN"
                    labelPixelSize: 10
                    accentColor: Colors.red
                    available: !trashLauncher.busy && !trashLauncher.researchBusy
                    onLeftClicked: trashLauncher.setMode("burn")
                }
            }

            Item {
                id: lifecyclePreparation
                width: parent.width
                height: Math.max(145, trashMenu.height - 136)
                visible: trashLauncher.activeMode !== "trash"

                // The original Camera Batch/Swipe/Hunt/Desktop/Queue page is
                // physically rendered in this Trash++ surface. There is no
                // redirect to the Camera window and no cloned queue.
                Flickable {
                    id: cleanupPageViewport
                    anchors.fill: parent
                    visible: trashLauncher.activeMode === "cleanup"
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds
                    contentWidth: width
                    contentHeight: Math.max(height, 525)
                    interactive: trashLauncher.cameraCleanupController
                                 && trashLauncher.cameraCleanupController.cleanupTechnique
                                    !== "swipe"
                                 && trashLauncher.cameraCleanupController.cleanupTechnique
                                    !== "hunt"

                    Item {
                        width: cleanupPageViewport.width
                        height: cleanupPageViewport.contentHeight

                        Loader {
                            id: cleanupViewLoader
                            anchors.fill: parent
                            active: trashLauncher.menuOpen
                                    && trashLauncher.activeMode === "cleanup"
                                    && trashLauncher.cameraCleanupController !== null
                            sourceComponent: Component {
                                CameraCleanupView {
                                    camera: trashLauncher.cameraCleanupController
                                }
                            }
                        }
                    }
                }

                Item {
                    id: archiveRecordsView
                    anchors.fill: parent
                    visible: trashLauncher.activeMode === "archive"

                    Column {
                        anchors.fill: parent
                        anchors.margins: 8
                        spacing: 6

                        Row {
                            width: parent.width
                            height: 28
                            spacing: 8
                            GohuText {
                                width: parent.width - 100
                                height: parent.height
                                color: Colors.yellow
                                font.pixelSize: 12
                                verticalAlignment: Text.AlignVCenter
                                text: "ARCHIVE // INVENTORY // "
                                      + (trashLauncher.archiveRows.length
                                         + trashLauncher.researchRows.length)
                            }
                            ActionButton {
                                width: 92
                                height: 27
                                label: trashLauncher.archiveBusy
                                       ? "SCANNING" : "REFRESH"
                                labelPixelSize: 10
                                accentColor: Colors.green
                                available: !trashLauncher.archiveBusy
                                onLeftClicked: trashLauncher.refreshArchive()
                            }
                        }

                        GohuText {
                            width: parent.width
                            height: 17
                            font.pixelSize: 9
                            color: trashLauncher.archiveState.indexOf("STALE") === 0
                                   ? Colors.red : Colors.cyan
                            elide: Text.ElideRight
                            text: trashLauncher.archiveState + " // "
                                + trashLauncher.researchState + " // "
                                + trashLauncher.archiveSources.map(function(v) {
                                    return v.id + ":" + v.state;
                                }).join(" // ")
                        }

                        TextField {
                            id: archiveSearch
                            width: parent.width
                            height: 32
                            color: Colors.white
                            font.pixelSize: 10
                            placeholderTextColor: Colors.cyan
                            placeholderText: "FIND RECORDS // SAVED COPIES // BIN"
                            text: trashLauncher.archiveSearchText
                            onTextChanged: trashLauncher.archiveSearchText = text
                            background: Rectangle {
                                color: Colors.dark
                                border.width: 1
                                border.color: Colors.cyan
                                radius: 0
                            }
                        }

                        Row {
                            id: archiveFilterRow
                            width: parent.width
                            height: 27
                            spacing: 4

                            Repeater {
                                model: [
                                    {id:"all", label:"ALL"},
                                    {id:"events", label:"EVENTS"},
                                    {id:"dossiers", label:"DOSSIERS"},
                                    {id:"scrapes", label:"SCRAPES"},
                                    {id:"copies", label:"COPIES"},
                                    {id:"bin", label:"BIN"}
                                ]
                                ActionButton {
                                    required property var modelData
                                    width: (archiveFilterRow.width - 20) / 6
                                    height: 26
                                    label: modelData.label
                                    labelPixelSize: 9
                                    accentColor: modelData.id === "all"
                                                 ? Colors.magenta : Colors.cyan
                                    selected: trashLauncher.archiveFilter === modelData.id
                                    onLeftClicked: trashLauncher.archiveFilter = modelData.id
                                }
                            }
                        }

                        Item {
                            id: archiveEntriesBox
                            width: parent.width
                            height: Math.max(80, archiveRecordsView.height - 190)
                            ListView {
                                id: archiveEntriesList
                                width: parent.width - 17
                                height: parent.height
                                clip: true
                                boundsBehavior: Flickable.StopAtBounds
                                spacing: 5
                                model: trashLauncher.archiveFilteredRows

                                delegate: Rectangle {
                                    required property var modelData
                                    width: archiveEntriesList.width
                                    height: 86
                                    color: Colors.dark
                                    radius: 0
                                    border.width: 1
                                    border.color: modelData.state === "trashed"
                                                  ? Colors.orange : Colors.cyan

                                    Column {
                                        anchors.fill: parent
                                        anchors.margins: 6
                                        anchors.rightMargin: 126
                                        spacing: 3

                                        GohuText {
                                            width: parent.width
                                            height: 18
                                            font.pixelSize: 11
                                            color: Colors.white
                                            elide: Text.ElideRight
                                            text: String(modelData.title || "UNTITLED RECORD")
                                        }
                                        GohuText {
                                            width: parent.width
                                            height: 17
                                            font.pixelSize: 9
                                            color: Colors.magenta
                                            elide: Text.ElideRight
                                            text: String(modelData.source)
                                                  + " // " + String(modelData.kind)
                                                  + (modelData.state
                                                     ? " // " + String(modelData.state).toUpperCase()
                                                     : "")
                                        }
                                        GohuText {
                                            width: parent.width
                                            height: 17
                                            font.pixelSize: 9
                                            color: Colors.cyan
                                            elide: Text.ElideRight
                                            text: String(modelData.recordedAt)
                                                  + " // " + String(modelData.details)
                                        }
                                    }

                                    Column {
                                        anchors.right: parent.right
                                        anchors.rightMargin: 5
                                        anchors.verticalCenter: parent.verticalCenter
                                        width: 109
                                        spacing: 4

                                        ActionButton {
                                            width: parent.width
                                            height: 30
                                            visible: modelData.kind === "WEB SCRAPE"
                                                     || modelData.kind === "EVENT HISTORY"
                                                     || modelData.kind === "SAVED RESEARCH"
                                                     || modelData.kind === "SAVED EVENT"
                                            label: modelData.kind === "WEB SCRAPE"
                                                   || modelData.kind === "EVENT HISTORY"
                                                   ? "SAVE COPY"
                                                   : modelData.state === "trashed"
                                                   ? "RESTORE" : "TRASH COPY"
                                            labelPixelSize: 9
                                            accentColor: modelData.state === "trashed"
                                                         ? Colors.green
                                                         : (modelData.kind === "SAVED RESEARCH"
                                                            || modelData.kind === "SAVED EVENT")
                                                         ? Colors.red : Colors.cyan
                                            available: !trashLauncher.researchBusy
                                                       && !trashLauncher.archiveBusy
                                                       && trashLauncher.researchBurnId === ""
                                            onLeftClicked: {
                                                if (modelData.kind === "WEB SCRAPE")
                                                    trashLauncher.saveDemoCopy(modelData);
                                                else if (modelData.kind === "EVENT HISTORY")
                                                    trashLauncher.saveWeatherEventCopy(modelData);
                                                else if (modelData.state === "trashed")
                                                    trashLauncher.restoreResearchCopy(modelData);
                                                else
                                                    trashLauncher.trashResearchCopy(modelData);
                                            }
                                        }

                                        ActionButton {
                                            width: parent.width
                                            height: 29
                                            visible: (modelData.kind === "SAVED RESEARCH"
                                                      || modelData.kind === "SAVED EVENT")
                                                     && modelData.state === "trashed"
                                            label: "BURN COPY"
                                            labelPixelSize: 9
                                            accentColor: Colors.red
                                            destructive: true
                                            available: !trashLauncher.researchBusy
                                                       && trashLauncher.researchBurnId === ""
                                            onLeftClicked: trashLauncher.armResearchBurn(modelData)
                                        }
                                    }
                                }
                            }

                            NeonScrollBar {
                                flickable: archiveEntriesList
                                x: parent.width - width - 1
                                height: parent.height
                                geometryMode: "viewport"
                                handleStyle: "star"
                                visible: scrollable
                            }

                            GohuText {
                                anchors.centerIn: parent
                                visible: !trashLauncher.archiveBusy
                                         && !trashLauncher.researchBusy
                                         && trashLauncher.archiveFilteredRows.length === 0
                                color: Colors.cyan
                                font.pixelSize: 11
                                text: trashLauncher.archiveRows.length === 0
                                         && trashLauncher.researchRows.length === 0
                                      ? "NO ARCHIVED RECORDS FOUND"
                                      : "NO MATCHES // TRY ANOTHER FILTER"
                            }
                        }

                        GohuText {
                            width: parent.width
                            height: 24
                            color: Colors.yellow
                            font.pixelSize: 9
                            wrapMode: Text.WordWrap
                            text: "SAVE COPY // WEATHER EVENTS OR DEMO SCRAPES. TRASH / RESTORE / BURN AFFECT ONLY TRASH++ COPIES."
                        }
                    }
                }

                Item {
                    id: researchBurnReview
                    anchors.fill: parent
                    visible: trashLauncher.activeMode === "burn"

                    Column {
                        anchors.fill: parent
                        anchors.margins: 8
                        spacing: 7

                        GohuText {
                            width: parent.width
                            height: 24
                            font.pixelSize: 13
                            color: Colors.yellow
                            text: "BURN // " + trashLauncher.total + " FILES // "
                                  + trashLauncher.researchBinRows.length + " COPIES"
                        }

                        GohuText {
                            width: parent.width
                            height: 34
                            font.pixelSize: 9
                            color: Colors.cyan
                            wrapMode: Text.WordWrap
                            text: "ONE BURN WORKSPACE // file deletion uses GIO; saved copies use their own verified store. Every Burn uses the same confirmation and result screen."
                        }

                        Row {
                            id: burnSourceFilters
                            width: parent.width
                            height: 27
                            spacing: 4
                            Repeater {
                                model: [
                                    {id:"all", label:"ALL"},
                                    {id:"files", label:"FILES"},
                                    {id:"records", label:"COPIES"},
                                    {id:"events", label:"EVENTS"},
                                    {id:"research", label:"RESEARCH"}
                                ]
                                ActionButton {
                                    required property var modelData
                                    width: (burnSourceFilters.width - 16) / 5
                                    height: 27
                                    label: modelData.label
                                    labelPixelSize: 9
                                    accentColor: modelData.id === "files"
                                                 ? Colors.cyan : Colors.magenta
                                    selected: trashLauncher.burnFilter === modelData.id
                                    available: trashLauncher.burnUiStage === ""
                                    onLeftClicked: trashLauncher.burnFilter = modelData.id
                                }
                            }
                        }

                        Item {
                            width: parent.width
                            height: Math.max(90, researchBurnReview.height - 194)

                            ListView {
                                id: researchBurnList
                                width: parent.width - 14
                                height: parent.height
                                clip: true
                                spacing: 5
                                boundsBehavior: Flickable.StopAtBounds
                                model: trashLauncher.burnDisplayRows

                                delegate: Rectangle {
                                    required property var modelData
                                    width: researchBurnList.width
                                    height: 59
                                    color: Colors.dark
                                    radius: 0
                                    border.width: 1
                                    border.color: modelData.entryType === "file"
                                                  ? Colors.green : Colors.orange

                                    Column {
                                        anchors.left: parent.left
                                        anchors.leftMargin: 6
                                        anchors.right: burnCopyButton.left
                                        anchors.rightMargin: 8
                                        anchors.verticalCenter: parent.verticalCenter
                                        spacing: 4

                                        GohuText {
                                            width: parent.width
                                            height: 18
                                            font.pixelSize: 10
                                            color: Colors.white
                                            elide: Text.ElideMiddle
                                            text: (modelData.entryType === "file"
                                                   ? "[FILE] " : "[COPY] ")
                                                  + String(modelData.title)
                                        }

                                        GohuText {
                                            width: parent.width
                                            height: 16
                                            font.pixelSize: 9
                                            color: Colors.cyan
                                            elide: Text.ElideMiddle
                                            text: String(modelData.originLabel || "")
                                        }
                                    }

                                    ActionButton {
                                        id: burnCopyButton
                                        anchors.right: parent.right
                                        anchors.rightMargin: 6
                                        anchors.verticalCenter: parent.verticalCenter
                                        width: 105
                                        height: 33
                                        label: "BURN"
                                        labelPixelSize: 10
                                        accentColor: Colors.red
                                        destructive: true
                                        available: !trashLauncher.busy
                                                   && !trashLauncher.researchBusy
                                                   && !trashLauncher.burnConfirmationOpen
                                        onLeftClicked: {
                                            if (modelData.entryType === "file")
                                                trashLauncher.armBurn(modelData);
                                            else
                                                trashLauncher.armResearchBurn(modelData.record);
                                        }
                                    }
                                }
                            }

                            NeonScrollBar {
                                flickable: researchBurnList
                                x: parent.width - width - 1
                                height: parent.height
                                geometryMode: "viewport"
                                handleStyle: "star"
                                visible: scrollable
                            }

                            GohuText {
                                anchors.centerIn: parent
                                visible: trashLauncher.burnDisplayRows.length === 0
                                color: Colors.cyan
                                font.pixelSize: 11
                                text: "NOTHING IN THIS BURN FILTER"
                            }
                        }

                        Row {
                            width: parent.width
                            height: 32
                            spacing: 8
                            ActionButton {
                                width: Math.max(128, parent.width - 151)
                                height: 32
                                label: "VIEW TRASH"
                                labelPixelSize: 10
                                accentColor: Colors.green
                                available: trashLauncher.burnUiStage === ""
                                           && !trashLauncher.burnConfirmationOpen
                                onLeftClicked: trashLauncher.setMode("trash")
                            }

                            // One Burn All control. Its scope comes from the
                            // selected filter; there is no combined backend
                            // that silently grants authority over both stores.
                            ActionButton {
                                id: burnAllManagedCopiesButton
                                width: 143
                                height: 32
                                label: "BURN ALL"
                                labelPixelSize: 10
                                accentColor: Colors.red
                                destructive: true
                                available: !trashLauncher.busy
                                           && !trashLauncher.researchBusy
                                           && !trashLauncher.burnConfirmationOpen
                                           && (trashLauncher.burnFilter === "files"
                                               ? trashLauncher.total > 0
                                                 && trashLauncher.revision.length === 64
                                               : trashLauncher.burnFilter === "records"
                                                 && trashLauncher.researchBinCount > 0
                                                 && trashLauncher.researchBinCount
                                                    === trashLauncher.researchBinRows.length)
                                onLeftClicked: {
                                    if (trashLauncher.burnFilter === "files")
                                        trashLauncher.armBurnAll();
                                    else if (trashLauncher.burnFilter === "records")
                                        trashLauncher.armResearchBurnAll();
                                }
                            }
                        }

                        GohuText {
                            width: parent.width
                            height: 23
                            font.pixelSize: 9
                            color: Colors.yellow
                            wrapMode: Text.WordWrap
                            text: trashLauncher.burnFilter === "files"
                                  ? "BURN ALL // SYSTEM TRASH ONLY"
                                  : trashLauncher.burnFilter === "records"
                                  ? "BURN ALL // MANAGED COPIES ONLY"
                                  : "BURN ALL // CHOOSE FILES OR COPIES FOR EXACT SCOPE"
                        }
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

        // All GIO file and managed-copy Burns share the single modal below.
        // Their backends and verified inventories remain strictly separate.
        // This modal is a separate, distant target from the per-row BURN
        // action. It only authorizes deleting an already-trashed, locally
        // managed demo research COPY, never any source-owned original.
        Rectangle {
            id: managedResearchBurnConfirm
            anchors.fill: parent
            z: 95
            visible: trashLauncher.burnConfirmationOpen
            color: Colors.black
            radius: 0
            border.width: 2
            border.color: Colors.orange

            MouseArea {
                anchors.fill: parent
                acceptedButtons: Qt.LeftButton | Qt.RightButton
                onClicked: function(mouse) { mouse.accepted = true; }
            }

            Column {
                id: burnReviewContent
                anchors.centerIn: parent
                width: Math.min(parent.width - 30, 360)
                spacing: 14
                visible: trashLauncher.burnUiStage !== "result"
                         && trashLauncher.burnUiStage !== "error"

                GohuText {
                    width: parent.width
                    font.pixelSize: 17
                    text: (trashLauncher.researchBurnScope === "all"
                           || trashLauncher.confirmMode === "all")
                          ? "BURN ALL // FINAL REVIEW"
                          : "BURN ITEM // FINAL REVIEW"
                    color: Colors.red
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.WordWrap
                }

                Rectangle {
                    width: parent.width
                    height: 2
                    color: Colors.orange
                }

                GohuText {
                    width: parent.width
                    font.pixelSize: 11
                    color: Colors.yellow
                    text: trashLauncher.confirmMode === "all"
                          ? "SCOPE // SYSTEM TRASH // " + trashLauncher.confirmCount + " FILES"
                          : trashLauncher.confirmMode === "item"
                          ? "SCOPE // ONE SYSTEM TRASH FILE"
                          : trashLauncher.researchBurnScope === "all"
                          ? "SCOPE // MANAGED BIN // " + trashLauncher.researchBurnCount + " COPIES"
                          : "SCOPE // ONE TRASH++ MANAGED COPY"
                    wrapMode: Text.WordWrap
                }

                GohuText {
                    width: parent.width
                    font.pixelSize: 13
                    color: Colors.white
                    elide: Text.ElideRight
                    text: trashLauncher.confirmMode === "all"
                          ? trashLauncher.confirmCount + " SYSTEM TRASH FILES"
                          : trashLauncher.confirmMode === "item"
                          ? trashLauncher.confirmName
                          : trashLauncher.researchBurnTitle
                }

                GohuText {
                    width: parent.width
                    font.pixelSize: 11
                    color: Colors.cyan
                    wrapMode: Text.WordWrap
                    text: trashLauncher.confirmMode === "all"
                          ? "This empties Linux Trash across mounts, but never managed copies or source-owned Weather, Hospital or Finance records. GIO rechecks the full index revision."
                          : trashLauncher.confirmMode === "item"
                          ? "This permanently removes ONE verified Linux Trash file. Managed copies and source records remain untouched."
                          : trashLauncher.researchBurnScope === "all"
                          ? "This destroys ONLY " + trashLauncher.researchBurnCount
                            + " trashed managed copies. Linux Trash and active copies remain untouched. The backend rechecks count, revision and digest."
                          : "This permanently deletes ONE managed copy. Original Weather events, research sources, Hospital and Finance records remain untouched."
                }

                GohuText {
                    width: parent.width
                    font.pixelSize: 10
                    color: Colors.orange
                    wrapMode: Text.WordWrap
                    text: "MOVE TO THE LEFT BUTTON, CLICK ONCE TO LOAD, THEN CLICK AGAIN TO BURN."
                }

                Row {
                    width: parent.width
                    height: 43
                    spacing: 12

                    Item {
                        id: managedResearchRemoteTarget
                        width: Math.max(145, parent.width - 131)
                        height: 43

                        HoverHandler {
                            id: managedResearchArrival
                            onHoveredChanged: {
                                if (hovered && trashLauncher.burnConfirmationOpen
                                        && trashLauncher.burnUiStage === "")
                                    trashLauncher.researchBurnPointerRelocated = true;
                            }
                        }

                        // Keep the regular ActionButton chassis opaque black
                        // in idle, hover, pressed AND fully-armed states.
                        // Progress lives in its rich content slot so it draws
                        // above the black button fill, not behind an opaque
                        // overlay. White and clipped black labels ensure that
                        // text stays readable while orange crosses each glyph.
                        ActionButton {
                            id: confirmManagedResearchBurn
                            anchors.fill: parent
                            label: ""
                            accentColor: Colors.red
                            destructive: true

                            idleFillColor: Colors.black
                            hoverFillColor: Colors.black
                            pressedFillColor: Colors.black
                            selectedFillColor: Colors.black
                            keyboardSelectedFillColor: Colors.black

                            idleBorderWidth: 2
                            hoverBorderWidth: 2
                            pressedBorderWidth: 2
                            idleBorderColor: Colors.red
                            hoverBorderColor: Colors.red
                            pressedBorderColor: Colors.red
                            keyboardSelectedBorderColor: Colors.red

                            // Opaque black in idle. A brief magenta halo marks
                            // the committed click before irreversible backend IO.
                            selected: trashLauncher.burnUiStage === "clicked"
                            selectedBorderWidth: 2
                            selectedBorderColor: Colors.magenta
                            contentGlowEnabled: false
                            softGlowEnabled: false
                            wideGlowEnabled: trashLauncher.burnUiStage === "clicked"
                            wideGlowSelectedOpacity: 0.36
                            selectedWideGlowColor: Colors.magenta
                            unavailableOpacity: 1.0
                            available: !trashLauncher.busy
                                       && !trashLauncher.researchBusy
                                       && trashLauncher.burnUiStage === ""
                                       && trashLauncher.burnConfirmationOpen
                                       && (trashLauncher.confirmMode !== ""
                                           || trashLauncher.researchBurnRevision
                                              === trashLauncher.researchRevision)
                            onLeftClicked: trashLauncher.advanceResearchBurn()

                            Item {
                                id: researchBurnFace
                                anchors.fill: parent
                                readonly property bool loading:
                                    trashLauncher.researchBurnClickArmed
                                    && !trashLauncher.researchBurnLoadComplete
                                readonly property string displayedLabel:
                                    trashLauncher.burnUiStage === "clicked"
                                    ? "CONFIRMING..."
                                    : trashLauncher.burnUiStage === "working"
                                    ? "BURNING..."
                                    : !trashLauncher.researchBurnPointerRelocated
                                    ? "MOVE HERE TO ARM"
                                    : !trashLauncher.researchBurnClickArmed
                                    ? "CLICK TO ARM"
                                    : !trashLauncher.researchBurnLoadComplete
                                    ? "LOADING SAFETY..."
                                    : "CLICK AGAIN // BURN"

                                // Full-height orange fill is visible ONLY
                                // during the 850 ms arming animation. At full
                                // load the normal solid-black button returns.
                                Rectangle {
                                    id: researchBurnLoadFill
                                    x: 2
                                    y: 2
                                    width: Math.max(0, parent.width - 4)
                                           * trashLauncher.researchBurnLoadProgress
                                    height: Math.max(0, parent.height - 4)
                                    color: Colors.orange
                                    radius: 0
                                    visible: researchBurnFace.loading
                                }

                                GohuText {
                                    id: researchBurnLabelWhite
                                    anchors.centerIn: parent
                                    width: Math.max(0, parent.width - 12)
                                    height: parent.height
                                    font.pixelSize: 10
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                    elide: Text.ElideRight
                                    color: Colors.white
                                    text: researchBurnFace.displayedLabel
                                }

                                // Black text is revealed over exactly the
                                // portion where the orange fill has passed.
                                // The white label stays visible elsewhere.
                                Item {
                                    id: researchBurnLabelClip
                                    x: researchBurnLoadFill.x
                                    y: researchBurnLoadFill.y
                                    width: researchBurnLoadFill.width
                                    height: researchBurnLoadFill.height
                                    clip: true
                                    visible: researchBurnFace.loading

                                    GohuText {
                                        x: researchBurnLabelWhite.x
                                           - researchBurnLabelClip.x
                                        y: researchBurnLabelWhite.y
                                           - researchBurnLabelClip.y
                                        width: researchBurnLabelWhite.width
                                        height: researchBurnLabelWhite.height
                                        font.pixelSize: 10
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                        elide: Text.ElideRight
                                        color: Colors.black
                                        text: researchBurnFace.displayedLabel
                                    }
                                }
                            }
                        }
                    }

                    ActionButton {
                        id: cancelManagedResearchBurn
                        width: 119
                        height: 43
                        label: "CANCEL // SAFE"
                        labelPixelSize: 10
                        accentColor: Colors.cyan
                        available: trashLauncher.burnUiStage === ""
                        onLeftClicked: trashLauncher.dismissBurnReceipt()
                    }
                }

                GohuText {
                    width: parent.width
                    font.pixelSize: 10
                    color: Colors.green
                    text: "CANCEL RETURNS TO BURN // NO DELETION"
                    wrapMode: Text.WordWrap
                }
            }

            // Stays here until DONE. Every listed name came from the actual
            // successful backend result, never a guessed input selection.
            Column {
                id: burnResultContent
                anchors.centerIn: parent
                width: Math.min(parent.width - 30, 370)
                spacing: 10
                visible: trashLauncher.burnUiStage === "result"
                         || trashLauncher.burnUiStage === "error"

                GohuText {
                    width: parent.width
                    font.pixelSize: 17
                    horizontalAlignment: Text.AlignHCenter
                    color: trashLauncher.burnReceiptVerified
                           ? Colors.green : Colors.orange
                    wrapMode: Text.WordWrap
                    text: trashLauncher.burnUiStage === "error"
                          ? "BURN // VERIFICATION FAILED"
                          : trashLauncher.burnReceiptVerified
                          ? "BURN // VERIFIED RESULT"
                          : "BURN // PARTIAL OR UNVERIFIED"
                }
                Rectangle {
                    width: parent.width
                    height: 2
                    color: Colors.orange
                }
                GohuText {
                    width: parent.width
                    font.pixelSize: 11
                    color: Colors.yellow
                    wrapMode: Text.WordWrap
                    text: trashLauncher.burnReceiptScope
                          + " // " + trashLauncher.burnReceiptCount
                          + " CONFIRMED OF " + trashLauncher.burnReceiptRequested
                }
                GohuText {
                    width: parent.width
                    font.pixelSize: 11
                    color: trashLauncher.burnReceiptVerified
                           ? Colors.cyan : Colors.orange
                    wrapMode: Text.WordWrap
                    text: trashLauncher.burnReceiptMessage
                }

                Item {
                    width: parent.width
                    height: Math.max(85, Math.min(210, trashMenu.height - 245))
                    ListView {
                        id: burnReceiptList
                        anchors.fill: parent
                        clip: true
                        spacing: 4
                        boundsBehavior: Flickable.StopAtBounds
                        model: trashLauncher.burnReceiptItems
                        delegate: Rectangle {
                            required property var modelData
                            width: burnReceiptList.width
                            height: 45
                            color: Colors.dark
                            radius: 0
                            border.width: 1
                            border.color: Colors.cyan
                            Column {
                                anchors.fill: parent
                                anchors.margins: 4
                                spacing: 2
                                GohuText {
                                    width: parent.width
                                    height: 16
                                    font.pixelSize: 10
                                    color: Colors.white
                                    elide: Text.ElideMiddle
                                    text: String(modelData.name)
                                }
                                GohuText {
                                    width: parent.width
                                    height: 15
                                    font.pixelSize: 9
                                    color: Colors.cyan
                                    elide: Text.ElideMiddle
                                    text: String(modelData.kind)
                                          + " // " + String(modelData.source)
                                }
                            }
                        }
                    }
                    NeonScrollBar {
                        flickable: burnReceiptList
                        x: parent.width - width
                        height: parent.height
                        geometryMode: "viewport"
                        handleStyle: "star"
                        visible: scrollable
                    }
                    GohuText {
                        anchors.centerIn: parent
                        visible: trashLauncher.burnReceiptItems.length === 0
                        font.pixelSize: 10
                        color: Colors.orange
                        text: "NO DELETIONS VERIFIED // REVIEW STATUS ABOVE"
                    }
                }

                ActionButton {
                    id: burnReceiptDone
                    width: parent.width
                    height: 40
                    label: "DONE // RETURN TO BURN"
                    labelPixelSize: 11
                    accentColor: Colors.green
                    onLeftClicked: trashLauncher.dismissBurnReceipt()
                }
            }
        }
    }
}
