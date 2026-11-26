import QtQuick
import QtQuick.Effects
import Qt5Compat.GraphicalEffects
import Quickshell
import "../../components"
import "../appcontrol"
import "../../services/system"
import "../../services/kill" as KillBackend

// CPU++ owns navigation and presentation. KillStore owns live telemetry and
// mini histories; AppControl temporarily owns the birth-time-verified action gate. No second poller,
// kill/prlimit backend, detached command, or historical-census actuation.
Item {
    id: workspace
    objectName: "cpuPlusSharedKillWorkspace"
    required property var appControlWindow
    required property var graphSource
    required property var graphController
    required property var graphSession
    readonly property var history: graphSource
    readonly property var detailGraph: graphController
    property bool active: true

    readonly property var gate: appControlWindow
        ? appControlWindow.hubProcessActionGate : null
    readonly property var taskRows: appControlWindow
        && Array.isArray(appControlWindow.taskRows)
        ? appControlWindow.taskRows : []

    // The live owner continues to own sampling and the persistent store.
    // These are CPU++-local view choices, never AppControl's current mode.
    readonly property int displayedTargetCount: filteredRows.length
    property int instrumentWidth: 390
    property int targetWidth: 260
    readonly property int killModeIndex: 7
    readonly property int selectedModeIndex: killModeIndex
    readonly property int killViewNormal: 0
    readonly property int killViewHunter: 1
    property int killViewMode: killViewNormal
    readonly property int hunterMetricCombined: 0
    readonly property int hunterMetricCpu: 1
    readonly property int hunterMetricMemory: 2
    readonly property int hunterMetricIo: 3
    readonly property int hunterMetricAge: 4
    property int hunterMetricMode: hunterMetricCombined
    readonly property int hunterVisibilityTargets: 0
    readonly property int hunterVisibilityProtected: 1
    readonly property int hunterVisibilityAll: 2
    property int hunterVisibilityMode: hunterVisibilityTargets
    readonly property string hunterCombiIcon: hunterGraph.combiIcon
    readonly property string metricKey: ["combined","cpu","mem","io","age"][hunterMetricMode]
    readonly property int miniHistoryRevision: graphSource
        ? Number(graphSource.taskMiniDisplayRevision || 0) : 0
    readonly property var ownerFavoriteStore: appControlWindow
        ? appControlWindow.favoriteStore : null
    property var bulkReview: null
    readonly property bool bulkAvailable: !!appControlWindow
        && typeof appControlWindow.prepareCpuBulkReview === "function"
    readonly property bool hasBulkReview: !!bulkReview && bulkAvailable
        && appControlWindow.cpuBulkReview === bulkReview
    readonly property bool bulkOperation: bulkAvailable && !!appControlWindow.cpuBulkOperation
    readonly property bool hunterOperationActive: bulkOperation
        && appControlWindow.hunterOperationPhase === "running"
    readonly property bool destructiveConfirmOpen: hasBulkReview || bulkOperation
    readonly property string destructiveConfirmKind: hasBulkReview ? bulkReview.kind
        : bulkOperation ? appControlWindow.hunterOperationKind : ""
    property bool ready: false
    property bool modelBlank: false
    property int viewSerial: 0
    property int hoveredIndex: -1
    property var orderIds: []
    readonly property var orderSlots: {
        const result = Object.create(null);
        for (let i=0; i<orderIds.length; ++i) result[orderIds[i]]=i;
        return result;
    }

    function keyOf(row) {
        return String(row.id || ("task:" + row.pid));
    }
    // Presentation only: capture identity, eligibility and dispatch remain owner-owned.
    // Linux comm is not a reliable application catalog. Recognize explicit
    // program families, treating other names as ordinary process names.
    function reviewProcessColor(name) {
        const key=String(name || "").toLowerCase().trim();
        if (/^(sway($|[-_])|quickshell($|[-_])|kitty($|[-_])|foot($|[-_])|alacritty($|[-_])|wezterm($|[-_])|ghostty($|[-_])|konsole($|[-_])|gnome-terminal|xterm($|[-_])|xwayland|xorg($|[-_])|waybar($|[-_])|hyprland($|[-_])|weston($|[-_])|wlr-randr|swaybg|swayidle|swaylock|mako($|[-_])|bash$|zsh$|fish$|sh$|zellij($|[-_])|tmux($|[-_]))/.test(key))
            return Colors.omnitrix;
        if (/^(brave|firefox|chromium|chrome|vivaldi|opera|thunderbird|vesktop|discord|spotify|code($|[-_])|codium|obsidian|libreoffice|soffice|gimp|krita|blender|vlc($|[-_])|mpv($|[-_])|steam($|[-_])|nautilus|dolphin|thunar|telegram|signal-desktop|obs($|[-_])|proton-mail)/.test(key))
            return Colors.cyan;
        return Colors.green;
    }
    function escapeReviewText(value) {
        return String(value).replace(/&/g,"&amp;").replace(/</g,"&lt;")
            .replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#39;");
    }
    function reviewInk(value, ink) {
        return '<font color="' + String(ink) + '">' + escapeReviewText(value) + '</font>';
    }
    function reviewTargetText(target, ink) {
        const name=String(target.name || target.comm || "PROCESS");
        const tokens=name.split(/([ \t.,:;_\/\\()[\]{}+\-!?@#$%&*=|<>’'"]+)/);
        return tokens.map(function(token,i) {
            return reviewInk(token,i%2 ? Colors.white : ink);
        }).join("") + reviewInk(" [PID ",Colors.white)
            + reviewInk(String(target.pid || "?"),ink) + reviewInk("]",Colors.white);
    }

    function protectedProcessRisk(row) {
        const reason = row && appControlWindow && appControlWindow.taskDangerReason
            ? String(appControlWindow.taskDangerReason(row) || "") : "";
        return "Changing a critical process can freeze the desktop, interrupt essential services, end your session or force a reboot. Unsaved work may be lost."
            + (reason ? "\n" + reason : "");
    }
    function isProtected(row) {
        // Read-only classification, identical to donor filter. Avoid a full
        // exact-row search for every row; mutations still require gate.exactRow.
        if (!row || !appControlWindow || !gate) return true;
        if (appControlWindow.taskRequiresDangerUnlock)
            return appControlWindow.taskRequiresDangerUnlock(row);
        return gate.isProtected(Number(row.pid),Number(row.startTicks),
                                String(row.comm || ""));
    }
    function hunterMetricAccent() { return hunterGraph.metricAccent(); }
    function hunterActive(row) {
        if (!row || !row._taskRecord) return false;
        // Same qualification thresholds as the donor's KILL/HUNTER view.
        if (hunterMetricMode === hunterMetricMemory)
            return hunterGraph.taskMemoryMiB(row) >= 16;
        if (hunterMetricMode === hunterMetricIo)
            return hunterGraph.taskIoRate(row) >= 1024;
        if (hunterMetricMode === hunterMetricAge)
            return hunterGraph.elapsedSeconds(row.elapsed) > 0;
        if (hunterMetricMode === hunterMetricCombined
                && hunterGraph.taskMemoryMiB(row) >= 128) return true;
        return hunterGraph.taskPeak(row) >= 0.35
            || hunterGraph.taskAverage(row) >= 0.15;
    }
    function visibleForView(row) {
        if (!row || row._taskRecord !== true) return false;
        if (killViewMode !== killViewHunter) return true;
        if (!hunterActive(row)) return false;
        if (hunterVisibilityMode === hunterVisibilityAll) return true;
        return hunterVisibilityMode === hunterVisibilityProtected
            ? isProtected(row) : !isProtected(row);
    }
    function rankRows(rows) {
        // Compute each score once, then keep stable slots during publication.
        const ranked = rows.map(function(row) {
            return {row:row, hunter:killViewMode === killViewHunter
                ? hunterGraph.taskMetricScore(row) : 0,
                cpu:Number(row.cpu || 0), mem:Number(row.mem || 0),
                pid:Number(row.pid || 0)};
        });
        ranked.sort(function(a,b) {
            return b.hunter-a.hunter || b.cpu-a.cpu || b.mem-a.mem || a.pid-b.pid;
        });
        return ranked.map(function(record) { return keyOf(record.row); });
    }
    function updateOrder(reset) {
        if (reset) { orderIds=rankRows(taskRows.filter(visibleForView)); return; }
        const known=Object.create(null);
        const live=Object.create(null);
        for (const row of taskRows) if (row && row._taskRecord) live[keyOf(row)]=true;
        const retained=orderIds.filter(function(key) { return !!live[key]; });
        for (const key of retained) known[key]=true;
        const added=rankRows(taskRows.filter(function(row) {
            return row && !known[keyOf(row)] && visibleForView(row);
        }));
        const next=retained.concat(added);
        if (next.length!==orderIds.length || next.some((x,i)=>x!==orderIds[i]))
            orderIds=next;
    }
    readonly property var filteredRows: {
        if (modelBlank || !active) return [];
        const query=processSearch.text.trim().toLowerCase();
        const revision=killViewMode===killViewHunter ? miniHistoryRevision : 0;
        const slots=orderSlots;
        return taskRows.filter(function(row) {
            if (!visibleForView(row)) return false;
            if (!query) return true;
            return [row.comm,row.args,row.user,row.pid,row.ppid,row.state]
                .join(" ").toLowerCase().indexOf(query)!==-1;
        }).sort(function(a,b) {
            const x=slots[keyOf(a)], y=slots[keyOf(b)];
            if (x!==undefined && y!==undefined) return x-y;
            if (x!==undefined) return -1;
            if (y!==undefined) return 1;
            return Number(a.pid)-Number(b.pid);
        });
    }
    function changeView(kind,value) {
        if (locallyPending || hasBulkReview || (gate && (gate.pending || gate.busy))) return;
        const serial=++viewSerial;
        hoveredIndex=-1;
        // Donor blank/reset strategy: no live rowsMoved storm on filter changes.
        modelBlank=true;
        Qt.callLater(function() {
            if (serial!==viewSerial || !active) return;
            if (kind==="view") killViewMode=value===killViewHunter?killViewHunter:killViewNormal;
            if (kind==="metric") hunterMetricMode=Math.max(0,Math.min(4,Number(value)));
            if (kind==="visibility") hunterVisibilityMode=Math.max(0,Math.min(2,Number(value)));
            updateOrder(true);
            Qt.callLater(function() {
                if (serial!==viewSerial || !active) return;
                modelBlank=false;
                targets.positionViewAtBeginning();
                repaintDetail(true);
            });
        });
    }
    function setKillViewMode(mode) { changeView("view",mode); }
    function setHunterMetricMode(mode) { changeView("metric",mode); }
    function setHunterVisibilityMode(mode) { changeView("visibility",mode); }
    function taskGlyph(row) {
        return appControlWindow && appControlWindow.monitorResultIcon
            ? appControlWindow.monitorResultIcon(row) : "(╭ర_•́)";
    }
    function taskRowMetric(row) {
        if (!row) return "NO METRIC";
        if (killViewMode !== killViewHunter)
            return "CPU "+Number(row.cpu || 0).toFixed(1)+"% • MEM "
                +Number(row.mem || 0).toFixed(1)+"%";

        // Donor hunterMetricReason semantics, with the recipient's metric
        // mode. Never call metricGraphValue here: it reads selected-detail
        // history, not the identity of this individual selector row.
        const revision=miniHistoryRevision;
        if (hunterMetricMode===hunterMetricCpu)
            return "CPU HOG • "+hunterGraph.taskPeak(row).toFixed(1)
                +"% PEAK • "+hunterGraph.taskAverage(row).toFixed(1)+"% RECENT";
        if (hunterMetricMode===hunterMetricMemory)
            return "MEMORY HOG • "+hunterGraph.taskMemoryMiB(row).toFixed(0)+" MiB RSS";
        if (hunterMetricMode===hunterMetricIo)
            return "I/O HOG • R "+hunterGraph.formatBytesPerSecond(row.ioReadRate)
                +" • W "+hunterGraph.formatBytesPerSecond(row.ioWriteRate);
        if (hunterMetricMode===hunterMetricAge)
            return "OLD PROCESS • "+hunterGraph.formatAge(hunterGraph.elapsedSeconds(row.elapsed));
        return hunterCombiIcon+" • CPU "+hunterGraph.taskPeak(row).toFixed(1)
            +"% • MEM "+hunterGraph.taskMemoryMiB(row).toFixed(0)
            +" MiB • I/O "+hunterGraph.formatBytesPerSecond(hunterGraph.taskIoRate(row));
    }
    function taskFavoriteKey(row) {
        return appControlWindow && appControlWindow.taskFavoriteKey
            ? appControlWindow.taskFavoriteKey(row) : "";
    }
    function isTaskFavorite(row) {
        const key=taskFavoriteKey(row);
        return !!key && !!ownerFavoriteStore
            && ownerFavoriteStore.favoriteKeys.indexOf(key)!==-1;
    }
    function toggleTaskFavorite(row) {
        const key=taskFavoriteKey(row);
        if (!active || !key || !ownerFavoriteStore) return;
        // Use the donor's persistent key and singleton without moving its UI.
        const next=ownerFavoriteStore.favoriteKeys.slice();
        const index=next.indexOf(key);
        if (index>=0) next.splice(index,1); else next.unshift(key);
        ownerFavoriteStore.favoriteKeys=next;
    }
    readonly property var miniGeometry: graphGeometry
    readonly property int miniHistoryLimit: history.taskMiniHistoryLimit
    readonly property int miniScrollDuration: history.taskMiniGraphScrollDuration
    function taskDisplayName(row) {
        return appControlWindow && appControlWindow.resultDisplayName
            ? appControlWindow.resultDisplayName(row, appControlWindow.killModeIndex)
            : String(row.comm || row.name || "PROCESS")
    }
    function miniHistory(row,key) {
        if (key==="normal")
            return detailGraph.miniCpuHistoryByIdentity("",row);
        return detailGraph.miniHunterHistoryForMetric(row,key);
    }
    function miniMetricRange(key) { return hunterGraph.metricRangeForKey(key); }
    function miniRange(key) {
        return key==="io" ? 0.25 : key==="age" ? 1.0 : 5.0;
    }
    function miniGraphPoints(row,key,w,h) {
        return graphGeometry.linePoints(miniHistory(row,key),w,h,
            miniRange(key),miniHistoryLimit,2,3);
    }
    // The shared owner computes candidates; only the explicit metric and
    // visibility are supplied. Search never silently changes global scope.
    function bulkCandidates(kind) {
        if (!active || !bulkAvailable) return [];
        if (bulkOperation) return [{}]; // existing report can be reopened
        if (hasBulkReview || locallyPending || (gate && (gate.pending || gate.busy))) return [];
        const revision = miniHistoryRevision;
        return appControlWindow.cpuBulkCandidates(kind,hunterMetricMode,hunterVisibilityMode);
    }
    function killAllEligibleTasks() { return bulkCandidates("kill-all"); }
    function hunterHogCandidates() { return bulkCandidates("kill-hogs"); }
    function hunterMouseCandidates() { return bulkCandidates("kill-mice"); }
    function requestBulk(kind) {
        if (!active || !bulkAvailable) return false;
        if (bulkOperation || hasBulkReview) return true;
        if (locallyPending || modelBlank || (gate && (gate.pending || gate.busy))) return false;
        bulkReview = appControlWindow.prepareCpuBulkReview(kind,hunterMetricMode,hunterVisibilityMode);
        return hasBulkReview;
    }
    function requestKillAllEligibleTasks() { return requestBulk("kill-all"); }
    function requestKillHogs() { return requestBulk("kill-hogs"); }
    function requestKillMice() { return requestBulk("kill-mice"); }
    function cancelBulk() {
        if (hasBulkReview) appControlWindow.cancelCpuBulkReview(bulkReview);
        bulkReview = null;
    }
    function confirmBulk() {
        if (!active || !hasBulkReview) return false;
        const accepted = appControlWindow.confirmCpuBulkReview(bulkReview);
        if (accepted) bulkReview = null;
        return accepted;
    }

    property int selectedPid: 0
    property double selectedStartTicks: 0
    property string selectedComm: ""
    property bool locallyPending: false
    property var ownedPendingRef: null
    property int stagedLimitPercent: -1

    function matchingRow() {
        for (let i = 0; i < taskRows.length; i++) {
            const row = taskRows[i];
            if (row && row._taskRecord === true
                    && Number(row.pid) === selectedPid
                    && Number(row.startTicks) === selectedStartTicks
                    && String(row.comm || "") === selectedComm)
                return row;
        }
        return null;
    }
    readonly property var currentTask: matchingRow()
    readonly property bool selectedTargetVisible: !modelBlank
        && !!currentTask && filteredRows.some(sameTarget)
    readonly property bool exactTargetAvailable: !!gate && !!currentTask
        && selectedTargetVisible
        && !!gate.exactRow(selectedPid, selectedStartTicks, selectedComm)
    readonly property bool hasOwnedPending: !!gate && locallyPending
        && !!ownedPendingRef && gate.pending === ownedPendingRef && !gate.busy

    function cancelOwned() {
        if (gate && locallyPending && ownedPendingRef
                && gate.pending === ownedPendingRef && !gate.busy)
            gate.cancel();
        locallyPending = false;
        ownedPendingRef = null;
    }

    function sameTarget(row) {
        return !!row && Number(row.pid)===selectedPid
            && Number(row.startTicks)===selectedStartTicks
            && String(row.comm || "")===selectedComm;
    }
    function selectTarget(row) {
        if (!row || !active || modelBlank || locallyPending
                || (gate && gate.busy) || !filteredRows.some(function(candidate) {
                    return Number(candidate.pid)===Number(row.pid)
                        && Number(candidate.startTicks)===Number(row.startTicks)
                        && String(candidate.comm || "")===String(row.comm || "");
                })) return false;
        if (sameTarget(row)) return true; // hovering over the current row must not reset graphs
        stagedLimitPercent=-1;
        selectedPid=Number(row.pid || 0);
        selectedStartTicks=Number(row.startTicks || 0);
        selectedComm=String(row.comm || "");
        taskHost.detailFocused=false;
        taskHost.selectedDetailActionIndex=-1;
        graphSession.selectCpu(row);
        actuatorScroll.contentY=0;
        return true;
    }

    function repaintDetail(reset) {
        if (!ready || !details) return;
        details.cpuCanvas.requestPaint(false,!!reset);
        details.memCanvas.requestPaint(false,!!reset);
        details.combiScoreCanvas.requestPaint(false,!!reset);
    }
    function cycleTarget(direction) {
        if (!active || locallyPending || modelBlank) return;
        const rows=filteredRows;
        if (!rows.length) return;
        const i=rows.findIndex(sameTarget);
        const n=i<0 ? (direction<0?rows.length-1:0)
            : (i+(direction<0?-1:1)+rows.length)%rows.length;
        if (selectTarget(rows[n])) {
            targets.currentIndex=n;
            targets.positionViewAtIndex(n,ListView.Contain);
            taskHost.keyboardActive=true;
        }
    }

    function requestRefresh() {
        if (active && appControlWindow && appControlWindow.refreshTaskManager)
            appControlWindow.refreshTaskManager();
    }

    function prepareAction(action, percent) {
        const row = currentTask;
        if (!active || !exactTargetAvailable || !gate || locallyPending
                || hasBulkReview || bulkOperation || appControlWindow.destructiveConfirmOpen)
            return false;
        const ok = gate.prepare(
            Number(row.pid), Number(row.startTicks), String(row.comm),
            action, action === "limit" ? Number(percent) : 0
        );
        if (ok) {
            ownedPendingRef = gate.pending;
            locallyPending = !!ownedPendingRef;
        }
        return !!ok;
    }

    function lockMode(row, action) {
        if (!row || !gate || !appControlWindow) return "";
        const exact=gate.exactRow(Number(row.pid),Number(row.startTicks),String(row.comm || ""));
        if (!exact) return "";
        if (!action)
            return appControlWindow.taskDangerUnlockMode
                ? appControlWindow.taskDangerUnlockMode(exact) : "";
        return appControlWindow.taskDangerActionUnlockMode
            ? appControlWindow.taskDangerActionUnlockMode(exact,action) : "";
    }
    function localLockMode(row, action) {
        if (!row || !gate || !appControlWindow || !action) return "";
        const exact=gate.exactRow(Number(row.pid),Number(row.startTicks),String(row.comm || ""));
        return exact && appControlWindow.taskDangerActionLocalUnlockMode
            ? appControlWindow.taskDangerActionLocalUnlockMode(exact,action) : "";
    }
    function canChangeLock(row) {
        return active && exactTargetAvailable && sameTarget(row)
            && !!gate && !gate.pending && !gate.busy
            && !hasBulkReview && !bulkOperation
            && !appControlWindow.destructiveConfirmOpen && isProtected(row);
    }
    function toggleLock(row,action,sticky) {
        if (!canChangeLock(row)) return false;
        const exact=gate.exactRow(selectedPid,selectedStartTicks,selectedComm);
        if (!exact) return false;
        if (!action && !sticky)
            return gate.toggleOneShotUnlock(selectedPid,selectedStartTicks,selectedComm);
        // Reuse the existing shared owner's master/per-action runtime states.
        // No new grant store; the existing action gate still verifies birth
        // identity before a confirmed command. Sticky state is owner policy.
        if (!action && sticky && appControlWindow.toggleTaskDangerStickyUnlock)
            appControlWindow.toggleTaskDangerStickyUnlock(exact);
        else if (action && sticky && appControlWindow.toggleTaskDangerActionStickyUnlock)
            appControlWindow.toggleTaskDangerActionStickyUnlock(exact,action);
        else if (action && !sticky && appControlWindow.toggleTaskDangerActionUnlock)
            appControlWindow.toggleTaskDangerActionUnlock(exact,action);
        else return false;
        return true;
    }
    onCurrentTaskChanged: {
        if (!currentTask && locallyPending) cancelOwned();
    }
    onSelectedTargetVisibleChanged: {
        // A live Hunter ranking can remove a row during review. Cancel only
        // our own unsent request; a submitted operation remains owner-owned.
        if (!selectedTargetVisible && locallyPending && gate && !gate.busy)
            cancelOwned();
    }
    onTaskRowsChanged: {
        if (!ready || !active) return;
        if (!modelBlank) updateOrder(false);
    }
    onActiveChanged: {
        if (ready) graphSession.setCpuActive(active);
        if (!active) { cancelOwned(); cancelBulk(); }
        else if (ready) {
            graphSession.selectCpu(currentTask);
            requestRefresh();
        }
    }
    Component.onCompleted: {
        ready=true;
        graphSession.setCpuActive(active);
        updateOrder(true);
        requestRefresh();
    }
    Component.onDestruction: { graphSession.setCpuActive(false); cancelOwned(); cancelBulk(); }
    // The existing AppControl timer already samples in all modes; do not
    // create a competing periodic refresh request from the recipient.
    Connections {
        target: workspace.gate
        function onPendingChanged() {
            if (workspace.gate
                    && workspace.gate.pending !== workspace.ownedPendingRef) {
                workspace.locallyPending = false;
                workspace.ownedPendingRef = null;
            }
        }
    }

    GraphHistory { id: graphGeometry }
    HunterPresentation {
        id: hunterGraph
        presentationState: history
        metricMode: workspace.hunterMetricMode
    }
    Connections {
        target: workspace.graphController
        function onPrepareCpuMemAppend() {
            if (workspace.ready && workspace.graphSession.matches(workspace.currentTask)) {
                details.cpuCanvas.requestPaint(true);
                details.memCanvas.requestPaint(true);
            }
        }
        function onPrepareCombiAppend() {
            if (workspace.ready && workspace.graphSession.matches(workspace.currentTask))
                details.combiScoreCanvas.requestPaint(true);
        }
        function onRepaintCpuMem(reset) { workspace.repaintDetail(reset); }
        function onRepaintCpu(reset) {
            if (workspace.ready) details.cpuCanvas.requestPaint(false,!!reset);
        }
        function onRepaintAll(reset) { workspace.repaintDetail(reset); }
    }
    ScriptModel {
        id: liveTargetModel
        objectProp: "id"
        values: workspace.filteredRows
    }

    QtObject {
        id: processView
        readonly property var currentTask: workspace.currentTask
        readonly property var presentation: workspace.gate
            ? workspace.gate.presentationOwner : null

        function metricIsCritical(entry, metricId) {
            return presentation ? presentation.metricIsCritical(entry, metricId) : false;
        }
        function formatMemory(kib) {
            return presentation ? presentation.formatMemory(kib) : "N/A";
        }
        function requiresDangerUnlock(entry) {
            return workspace.gate && entry
                ? workspace.gate.isProtected(Number(entry.pid),
                    Number(entry.startTicks), String(entry.comm || "")) : true;
        }
        function dangerActionUnlocked(entry, actionKind) {
            return workspace.gate && entry
                ? workspace.gate.isUnlocked(Number(entry.pid),
                    Number(entry.startTicks), String(entry.comm || ""),
                    String(actionKind || "")) : false;
        }
        function relockDangerAction(entry, actionKind) {
            // The action gate consumes one-shot unlocks on confirm/cancel.
            // A slider preview must not silently mutate shared safety state.
        }
        function hasSoftLimit() {
            return presentation && currentTask
                ? presentation.hasSoftLimit(currentTask) : false;
        }
        function limitMinimumMiB(entry) {
            return presentation && (entry || currentTask)
                ? presentation.limitMinimumMiB(entry || currentTask) : 128;
        }
        function limitMaximumMiB(entry) {
            return presentation && (entry || currentTask)
                ? presentation.limitMaximumMiB(entry || currentTask) : 8192;
        }
        function limitMiB() {
            return presentation && currentTask
                ? presentation.limitMiB(currentTask) : 0;
        }
        function limitPercent() {
            if (workspace.stagedLimitPercent >= 0)
                return workspace.stagedLimitPercent;
            return presentation && currentTask
                ? presentation.limitPercent(currentTask) : 100;
        }
        function setLimitPercent(percent) {
            if (!workspace.exactTargetAvailable) return;
            workspace.stagedLimitPercent =
                Math.max(0, Math.min(100, Math.round(Number(percent || 0))));
            // Preview only. Existing actuator review requires APPLY then CONFIRM.
        }
        function setLimitMiB(mib) {
            if (!currentTask || !presentation) return;
            const minimum = presentation.limitMinimumMiB(currentTask);
            const maximum = presentation.limitMaximumMiB(currentTask);
            const pct = Number(mib) >= maximum ? 100
                : ((Number(mib) - minimum) / Math.max(1, maximum - minimum)) * 98.5;
            setLimitPercent(pct);
        }
        function isFrozen() {
            return presentation && currentTask
                ? presentation.isFrozen(currentTask) : false;
        }
        function requestRestart() { workspace.prepareAction("restart"); }
        function requestTerminate() { workspace.prepareAction("end"); }
        function toggleFreeze() {
            workspace.prepareAction(isFrozen() ? "resume" : "freeze");
        }
        function scopeProcessText() {
            return presentation && currentTask
                ? presentation.scopeProcessText(currentTask)
                : "NO VERIFIED LIVE PROCESS SELECTED";
        }
    }

    QtObject {
        id: taskHost
        property bool detailFocused: false
        property bool keyboardActive: false
        property bool modeRailFocused: false
        property int selectedDetailActionIndex: -1
        readonly property bool menuOpen: workspace.active
        readonly property bool hunterMetricView: workspace.killViewMode === workspace.killViewHunter
        function setKeyboardActive(value) { keyboardActive = !!value; }
        function clearModeRailFocus() { modeRailFocused = false; }
        function setDetailFocused(value) { detailFocused = !!value; }
        function setDetailActionIndex(index) {
            selectedDetailActionIndex = Number(index);
        }
        function moveDetailSelection(direction) {
            const indices=[0,-2,1,2];
            const position=indices.indexOf(selectedDetailActionIndex);
            selectedDetailActionIndex=indices[Math.max(0,Math.min(indices.length-1,
                position+(direction<0?-1:1)))];
            ensureDetailActionVisible();
        }
        function ensureDetailActionVisible() {
            const item=selectedDetailActionIndex===-2 ? details.limitSlider
                : selectedDetailActionIndex===0 ? details.restartAction
                : selectedDetailActionIndex===1 ? details.freezeAction
                : selectedDetailActionIndex===2 ? details.endAction : null;
            if (!item || !actuatorScroll || item.parent === headerActions || item.parent === killSlot || item.parent === freezeSlot) return;
            const y=item.mapToItem(actuatorScroll.contentItem,0,0).y;
            if (y<actuatorScroll.contentY) actuatorScroll.contentY=Math.max(0,y);
            else if (y+item.height>actuatorScroll.contentY+actuatorScroll.height)
                actuatorScroll.contentY=Math.max(0,y+item.height-actuatorScroll.height);
        }
        function isTaskMetricFavorite(entry, metricId) {
            return workspace.appControlWindow && entry
                ? workspace.appControlWindow.isTaskMetricFavorite(entry, metricId)
                : false;
        }
        function toggleTaskMetricFavorite(entry, metricId) {
            if (workspace.appControlWindow && entry)
                workspace.appControlWindow.toggleTaskMetricFavorite(entry, metricId);
        }
    }

    Component {
        id: safetyLock
        ProcessSafetyLock { controller: workspace }
    }

    Row {
        id: bays
        anchors.fill: parent
        spacing: 0

        Rectangle {
            id: instrumentBay
            objectName: "cpuPlusProcessControlBay"
            width: Math.min(workspace.instrumentWidth, Math.max(0,bays.width-targetBay.width))
            height: bays.height
            color: Colors.dark
            border.width: 1
            border.color: Colors.orange

            GohuText {
                id: instrumentTitle
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.topMargin: 16
                anchors.leftMargin: 16
                text: "KILL // TASK MANAGER"
                color: Colors.magenta
                font.pixelSize: 13
            }
            Rectangle {
                id: instrumentHeaderLine
                objectName: "cpuPlusKillHeaderDivider"
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: instrumentTitle.bottom
                anchors.leftMargin: 10
                anchors.rightMargin: 10
                anchors.topMargin: 6
                height: 2
                color: Colors.red
                RectangularShadow {
                    anchors.fill: parent
                    spread: 3
                    z: -1
                    opacity: 0.38
                    color: parent.color
                }
            }
            Item {
                id: processIdentity
                objectName: "cpuPlusProcessIdentity"
                anchors.top: instrumentHeaderLine.bottom
                anchors.topMargin: 7
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.margins: 8
                height: identityContent.implicitHeight + 16
                visible: !!workspace.currentTask
                Column {
                    id: identityContent
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 8
                    anchors.rightMargin: 38
                    spacing: 4
                    GohuText {
                        width: parent.width
                        text: workspace.currentTask
                            ? workspace.taskGlyph(workspace.currentTask)+"  "+String(workspace.currentTask.comm)
                            : ""
                        textFormat: Text.PlainText
                        font.pixelSize: 16
                        color: Colors.orange
                        elide: Text.ElideRight
                    }
                    GohuText {
                        width: parent.width
                        text: workspace.currentTask
                            ? "PID "+workspace.selectedPid+" • "+String(workspace.currentTask.user || "?")
                              +" • "+String(workspace.currentTask.state || "?") : ""
                        textFormat: Text.PlainText
                        font.pixelSize: 12
                        color: Colors.white
                        elide: Text.ElideRight
                    }
                    GohuText {
                        width: parent.width
                        wrapMode: Text.Wrap
                        objectName: "cpuPlusProcessExactIdentity"
                        visible: !workspace.exactTargetAvailable
                        text: workspace.exactTargetAvailable
                            ? "EXACT LIVE PID + START TICKS + NAME"
                            : workspace.currentTask && !workspace.selectedTargetVisible
                            ? "TARGET OUTSIDE CURRENT FILTER // CONTROLS LOCKED"
                            : "TARGET IDENTITY NOT VERIFIED // CONTROLS LOCKED"
                        color: workspace.exactTargetAvailable ? Colors.white : Colors.orange
                        font.pixelSize: 10
                    }
                    GohuText {
                        width: parent.width
                        wrapMode: Text.Wrap
                        objectName: "cpuPlusProcessLiveOwner"
                        text: "Live owner • explicit review before dispatch"
                        color: Colors.white
                        font.pixelSize: 10
                    }

                }
                ProcessInformationButton {
                    objectName: "cpuPlusProcessInformationButton"
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 6
                    selected: cpuProcessInformation.open
                    available: cpuProcessInformation.contextActive
                    onLeftClicked: cpuProcessInformation.open = !cpuProcessInformation.open
                }
            }
            Item {
                id: processStateHeader
                objectName: "cpuPlusProcessStateHeader"
                anchors.top: processIdentity.visible ? processIdentity.bottom : instrumentHeaderLine.bottom
                anchors.topMargin: 4
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.leftMargin: 8
                anchors.rightMargin: 8
                // Reserve the full lock rail even when no individual locks are visible.
                height: Math.max(48, lockRail.reservedHeight + 7 + 32 - processIdentity.height - 4)
                visible: !!workspace.currentTask
                GohuText {
                    anchors.left: parent.left
                    anchors.leftMargin: 8
                    anchors.right: headerLocks.left
                    anchors.rightMargin: 4
                    anchors.verticalCenter: headerLocks.verticalCenter
                    elide: Text.ElideRight
                    text: "PROCESS STATE"
                    color: Colors.red
                    font.pixelSize: 13
                }
                Row {
                    id: headerLocks
                    anchors.right: parent.right
                    anchors.rightMargin: 42
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: 7
                    spacing: 5
                    enabled: workspace.exactTargetAvailable && !workspace.locallyPending
                        && !workspace.hasBulkReview && !workspace.bulkOperation
                        && !!workspace.gate && !workspace.gate.pending && !workspace.gate.busy
                    Item {
                        width: 30; height: 34
                        ProcessSafetyLock {
                            objectName: "cpuPlusProcessMasterLock"
                            anchors.centerIn: parent
                            width: 30; height: 26
                            controller: workspace
                            taskItem: workspace.currentTask
                            accentColor: Colors.magenta
                        }
                    }
                    Item {
                        id: killSlot
                        objectName: "cpuPlusProcessKillSlot"
                        width: 88; height: 34

                    }
                    Item {
                        id: headerActions
                        objectName: "cpuPlusProcessHeaderActions"
                        width: 34; height: 34
                    }
                    Item {
                        id: freezeSlot
                        objectName: "cpuPlusProcessFreezeSlot"
                        width: 34; height: 34

                    }

                }

                Rectangle {
                    anchors.bottom: parent.bottom
                    width: parent.width
                    height: 1
                    color: Colors.red
                }
            }
            Column {
                id: lockRail
                objectName: "cpuPlusProcessIndependentLockRail"
                anchors.right: instrumentBay.right
                anchors.rightMargin: 8
                anchors.bottom: processStateHeader.bottom
                anchors.bottomMargin: 7
                spacing: 2
                width: 26
                visible: !!workspace.currentTask
                z: 2
                readonly property bool protectedTarget: !!workspace.currentTask && workspace.isProtected(workspace.currentTask)
                readonly property int reservedHeight: 3 * 23 + 3 * spacing + 22
                Item {
                    id: killLockSlot
                    objectName: "cpuPlusProcessKillLockSlot"
                    width: parent.width; height: 23
                    // Keep this slot in the layout; the loaded lock itself is conditional.
                }
                Item {
                    id: restartLockSlot
                    objectName: "cpuPlusProcessRestartLockSlot"
                    width: parent.width; height: 23
                    // Keep this slot in the layout; the loaded lock itself is conditional.
                }
                Item {
                    id: freezeLockSlot
                    objectName: "cpuPlusProcessFreezeLockSlot"
                    width: parent.width; height: 23
                    // Keep this slot in the layout; the loaded lock itself is conditional.
                }
            ProcessInformationButton {
                id: lockHelpButton
                objectName: "cpuPlusProcessLockHelpButton"
                anchors.horizontalCenter: parent.horizontalCenter
                Accessible.name: "Lock usage help"
                selected: false
                available: !!workspace.currentTask && !workspace.locallyPending
                    && !workspace.hasBulkReview && !workspace.bulkOperation
                    && !!workspace.gate && !workspace.gate.pending && !workspace.gate.busy
                    && !workspace.appControlWindow.destructiveConfirmOpen && !cpuProcessInformation.open
            }
            }
            Flickable {
                id: actuatorScroll
                objectName: "cpuPlusKillInstrumentViewport"
                anchors.top: workspace.currentTask ? processStateHeader.bottom : instrumentHeaderLine.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.margins: 8
                clip: true
                contentWidth: width
                contentHeight: actuatorBody.implicitHeight + 12
                Column {
                id: actuatorBody
                width: Math.max(0,actuatorScroll.width-14)
                spacing: 6
                GohuText {
                    id: emptyTarget
                    visible: !workspace.currentTask
                    width: parent.width
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.Wrap
                    text: "SELECT A LIVE PROCESS IN THE MIDDLE BAY"
                    color: Colors.cyan
                    font.pixelSize: 12
                }
                TaskManagerView {
                    id: details
                    objectName: "cpuPlusKillSharedTaskView"
                    width: parent.width
                    visible: !!workspace.currentTask
                    host: taskHost
                    presentationState: history
                    graphDataAvailable: workspace.graphSession.matches(workspace.currentTask)
                    processController: processView
                    graphGeometry: graphGeometry
                    hunterGraph: hunterGraph
                    searchInputTarget: processSearch
                    safetyLockComponent: safetyLock
                    actionTarget: leftActions
                    quickActionTarget: headerActions
                    lockTarget: limitLockSlot
                    killActionTarget: killSlot
                    freezeActionTarget: freezeSlot
                    killLockTarget: killLockSlot
                    restartLockTarget: restartLockSlot
                    freezeLockTarget: freezeLockSlot
                    viewportHeight: actuatorScroll.height - 12
                }

                Item {
                    id: limitLockSlot
                    objectName: "cpuPlusProcessLimitLockSlot"
                    width: parent.width
                    height: 26
                    visible: !!workspace.currentTask
                }
                Column {
                    id: leftActions
                    objectName: "cpuPlusSharedActionTarget"
                    width: parent.width
                    spacing: 6
                    visible: !!workspace.currentTask
                    enabled: workspace.exactTargetAvailable && !workspace.locallyPending
                }
                GohuText {
                    width: parent.width
                    visible: workspace.stagedLimitPercent >= 0
                    text: "LIMIT PREVIEW // " + workspace.stagedLimitPercent + "%"
                    color: Colors.yellow
                    font.pixelSize: 12
                }
                Rectangle {
                    width: parent.width
                    height: 34
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.yellow
                    visible: workspace.stagedLimitPercent >= 0
                    opacity: workspace.exactTargetAvailable && !workspace.locallyPending ? 1 : 0.45
                    GohuText {
                        anchors.centerIn: parent
                        text: "APPLY LIMIT // REVIEW"
                        color: Colors.yellow
                        font.pixelSize: 11
                    }
                    MouseArea {
                        anchors.fill: parent
                        enabled: workspace.exactTargetAvailable
                                 && !workspace.locallyPending
                        onClicked: workspace.prepareAction(
                            "limit", workspace.stagedLimitPercent)
                    }
                }
                GohuText {
                    width: parent.width
                    wrapMode: Text.Wrap
                    text: workspace.gate ? workspace.gate.feedback : "NO SHARED ACTION OWNER"
                    color: Colors.orange
                    font.pixelSize: 10
                }

                }
            }
            NeonScrollBar {
                objectName: "cpuPlusKillActuatorScroll"
                flickable: actuatorScroll
                geometryMode: "viewport"
                visible: scrollable
                railColor: Colors.red
                handleColor: Colors.magenta
                wheelEnabled: false
            }
            Rectangle {
                id: lockHelp
                objectName: "cpuPlusProcessLockHelpPopup"
                readonly property bool open: lockHelpButton.hovered && lockHelpButton.available && workspace.active
                visible: open
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: processStateHeader.bottom
                anchors.margins: 8
                height: helpContent.implicitHeight + 14
                z: 401
                color: Colors.black
                border.color: Colors.yellow
                clip: true
                MouseArea {
                    anchors.fill: parent
                    onWheel: function(wheel) { wheel.accepted = true }
                }
                Column {
                    id: helpContent
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 7
                    spacing: 4
                    Row {
                        width: parent.width
                        height: 24
                        GohuText {
                            width: parent.width
                            height: parent.height
                            text: "LOCK // HELP"
                            verticalAlignment: Text.AlignVCenter
                            color: Colors.yellow
                            font.pixelSize: 12
                            layer.enabled: lockHelp.visible
                            layer.effect: DropShadow { radius: 6; samples: 7; opacity: 0.60; color: Colors.yellow; transparentBorder: true }
                        }
                    }
                    GohuText {
                        id: lockRiskText
                        objectName: "cpuPlusLockRiskHelp"
                        width: parent.width
                        text: lockRail.protectedTarget
                            ? "PROTECTED TARGET // These locks guard critical processes. Stopping or restarting one can disable the desktop, end your session or force a reboot."
                            : "ORDINARY TARGET // No extra safety locks are required. Actions still require review and confirmation."
                        wrapMode: Text.Wrap
                        textFormat: Text.PlainText
                        color: lockRail.protectedTarget ? Colors.red : Colors.white
                        font.pixelSize: 11
                        layer.enabled: lockHelp.visible
                        layer.effect: DropShadow { radius: 6; samples: 7; opacity: 0.60; color: lockRiskText.color; transparentBorder: true }
                    }
                    Rectangle { width: parent.width; height: 1; color: Colors.orange; opacity: 0.7 }
                    Repeater {
                        model: [
                            { name: "MASTER", ink: Colors.magenta, detail: "Unlock all. Closing it clears every individual grant." },
                            { name: "KILL", ink: Colors.red, detail: "Authorize ending this process." },
                            { name: "RESTART", ink: Colors.yellow, detail: "Authorize restart only." },
                            { name: "FREEZE / THAW", ink: Colors.cyan, detail: "Authorize pause or resume only." },
                            { name: "LIMIT", ink: Colors.yellow, detail: "Separate lock beside the limit control." }
                        ]
                        delegate: Row {
                            required property var modelData
                            width: helpContent.width
                            spacing: 6
                            GohuText {
                            id: helpGlowText2
                                width: Math.min(112, parent.width * 0.36)
                                text: modelData.name
                                color: modelData.ink
                                font.pixelSize: 11
                            layer.enabled: lockHelp.visible
                            layer.effect: DropShadow { radius: 6; samples: 7; opacity: 0.60; color: helpGlowText2.color; transparentBorder: true }
                                wrapMode: Text.Wrap
                            }
                            GohuText {
                            id: helpGlowText3
                                width: Math.max(0, parent.width - 6 - Math.min(112, parent.width * 0.36))
                                text: modelData.detail
                                color: Colors.white
                                font.pixelSize: 11
                            layer.enabled: lockHelp.visible
                            layer.effect: DropShadow { radius: 6; samples: 7; opacity: 0.60; color: helpGlowText3.color; transparentBorder: true }
                                wrapMode: Text.Wrap
                            }
                        }
                    }
                    Rectangle { width: parent.width; height: 1; color: Colors.orange; opacity: 0.7 }
                    GohuText {
                            id: helpGlowText4
                        width: parent.width
                        text: "Left click lock: one-shot • Right click: sticky."
                        color: Colors.yellow
                        font.pixelSize: 11
                            layer.enabled: lockHelp.visible
                            layer.effect: DropShadow { radius: 6; samples: 7; opacity: 0.60; color: helpGlowText4.color; transparentBorder: true }
                        wrapMode: Text.Wrap
                    }
                    GohuText {
                            id: helpGlowText5
                        width: parent.width
                        text: "Individual locks work independently. Master overrides them while open. A + or key marks an individual grant."
                        color: Colors.white
                        font.pixelSize: 11
                            layer.enabled: lockHelp.visible
                            layer.effect: DropShadow { radius: 6; samples: 7; opacity: 0.60; color: helpGlowText5.color; transparentBorder: true }
                        wrapMode: Text.Wrap
                    }
                    GohuText {
                            id: helpGlowText6
                        width: parent.width
                        text: "UNLOCK ≠ EXECUTE // Review and confirm. Dispatch is not proof of success."
                        color: Colors.red
                        font.pixelSize: 11
                            layer.enabled: lockHelp.visible
                            layer.effect: DropShadow { radius: 6; samples: 7; opacity: 0.60; color: helpGlowText6.color; transparentBorder: true }
                        wrapMode: Text.Wrap
                    }
                }
            }
            ProcessInformationPanel {
                id: cpuProcessInformation
                objectName: "cpuPlusProcessInformation"
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.leftMargin: 6
                anchors.rightMargin: 6
                compactTop: processStateHeader.y + processStateHeader.height + 6
                expandedTop: processStateHeader.y
                fullTop: 6
                maximumHeight: Math.max(0, instrumentBay.height - fullTop - 6)
                contextActive: workspace.active && !!workspace.currentTask
                    && !workspace.locallyPending && !workspace.hasBulkReview && !workspace.bulkOperation
                task: contextActive ? workspace.currentTask : null
                purpose: open && contextActive && task && workspace.appControlWindow.taskSimplePurpose
                    ? workspace.appControlWindow.taskSimplePurpose(task) : ""
                scopeText: open && contextActive && task ? processView.scopeProcessText() : ""
                virtualMemory: open && contextActive && task ? processView.formatMemory(task.vsz) : "?"
            }

        }

        Rectangle {
            id: targetBay
            width: Math.min(workspace.targetWidth,bays.width)
            height: bays.height
            color: Colors.black
            border.width: 1
            border.color: Colors.orange
            Rectangle {
                id: searchHeader
                objectName: "cpuPlusKillSearchHeader"
                width: parent.width
                height: 70
                anchors.top: parent.top
                color: Colors.black
                Item {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.leftMargin: 15
                    anchors.rightMargin: 15
                    anchors.topMargin: 9
                    height: 22
                    GohuText {
                        id: targetTitle
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.verticalCenter: parent.verticalCenter
                        text: "KILL"
                        font.pixelSize: 19
                        color: Colors.red
                    }
                    SafeDropShadow {
                        anchors.fill: targetTitle
                        safeSource: targetTitle
                        radius: 14
                        samples: 11
                        z: 2
                        opacity: 0.75
                        color: Colors.red
                        transparentBorder: true
                    }
                    Rectangle {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        anchors.leftMargin: -15
                        anchors.rightMargin: -15
                        transform: Translate { y: 4 }
                        height: 1
                        color: Colors.red
                        RectangularShadow {
                            anchors.fill: parent
                            spread: 3
                            z: -1
                            opacity: 0.38
                            color: parent.color
                        }
                    }
                }
                TextInput {
                    id: processSearch
                    objectName: "cpuPlusKillSearch"
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    anchors.leftMargin: 15
                    anchors.rightMargin: 15
                    anchors.bottomMargin: 3
                    height: 22
                    font.family: "GohuFont 11 Nerd Font Mono"
                    font.pixelSize: 18
                    verticalAlignment: TextInput.AlignVCenter
                    color: Colors.magenta
                    selectionColor: Colors.yellow
                    selectedTextColor: Colors.black
                    cursorVisible: activeFocus
                    cursorDelegate: Item { width: 0; height: 0; visible: false; opacity: 0.0 }
                    clip: true
                    selectByMouse: true
                    readOnly: workspace.locallyPending || (!!workspace.gate && workspace.gate.busy)
                    layer.enabled: true
                    layer.effect: DropShadow {
                        horizontalOffset: 0
                        verticalOffset: 0
                        radius: 7
                        samples: 9
                        opacity: 0.30
                        color: Colors.magenta
                        transparentBorder: true
                    }
                }
                AnimatedTextCursor {
                    objectName: "cpuPlusKillAnimatedCursor"
                    input: processSearch
                }
                Rectangle {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    height: 1
                    color: Colors.red
                    RectangularShadow {
                        anchors.fill: parent
                        spread: 3
                        z: -1
                        opacity: 0.38
                        color: parent.color
                    }
                }
            }
            HunterControls {
                id: hunterControls
                objectName: "cpuPlusSharedHunterControls"
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: searchHeader.bottom
                anchors.bottom: parent.bottom
                controller: workspace
                onFocusSearchRequested: processSearch.forceActiveFocus()
            }
            ListView {
                id: targets
                objectName: "cpuPlusKillLiveTargets"
                anchors.top: searchHeader.bottom
                anchors.topMargin: hunterControls.topSelectorHeight+6
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.leftMargin: 4
                anchors.rightMargin: 20
                anchors.bottomMargin: hunterControls.bottomSelectorHeight
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                highlightMoveDuration: 0
                highlightResizeDuration: 0
                model: liveTargetModel
                delegate: ProcessTargetRow {
                    required property var modelData
                    required property int index
                    width: targets.width
                    entry: modelData
                    controller: workspace
                    selected: workspace.sameTarget(modelData)
                    hovered: workspace.hoveredIndex===index
                    onSelectedRequested: workspace.selectTarget(modelData)
                    onFavoriteSelectedRequested: workspace.selectTarget(modelData)
                }
                // Viewport-level tracker from donor behavior. Real mouse
                // movement selects the row; scrolling under a stationary
                // pointer or a pending confirmation must not steal selection.
                MouseArea {
                    anchors.fill: parent
                    z: 100
                    hoverEnabled: true
                    acceptedButtons: Qt.NoButton
                    onPositionChanged: function(mouse) {
                        if (targets.moving || workspace.locallyPending) return;
                        const i=targets.indexAt(mouse.x,mouse.y+targets.contentY);
                        workspace.hoveredIndex=i;
                        if (i>=0 && i<workspace.filteredRows.length) {
                            taskHost.keyboardActive=false;
                            workspace.selectTarget(workspace.filteredRows[i]);
                        }
                    }
                    onExited: workspace.hoveredIndex=-1
                    onWheel: function(wheel) { wheel.accepted=false; }
                }
            }
            Rectangle {
                objectName: "cpuPlusKillListTopDivider"
                x: 0; y: searchHeader.height + hunterControls.topSelectorHeight
                width: parent.width; height: 1; color: Colors.red; z: 261
            }
            Rectangle {
                objectName: "cpuPlusKillListBottomDivider"
                x: 0; y: parent.height - hunterControls.bottomSelectorHeight
                width: parent.width; height: 1; color: Colors.red; z: 271
            }
            NeonScrollBar {
                objectName: "cpuPlusKillTargetScroll"
                flickable: targets
                geometryMode: "viewport"
                accountForContentOrigin: true
                handleStyle: "star"
                z: 300
                topInset: 0
                bottomInset: 0
                y: searchHeader.height + hunterControls.topSelectorHeight
                height: Math.max(0, targetBay.height - y - hunterControls.bottomSelectorHeight)
                x: targetBay.width-width-3
                visible: scrollable
                railColor: Colors.red
                handleColor: Colors.magenta
                wheelEnabled: false
            }

        }

        Rectangle {
            id: resourceBay
            objectName: "cpuPlusProcessReservedBay"
            width: Math.max(0,bays.width-instrumentBay.width-targetBay.width)
            height: bays.height
            color: Colors.dark
            border.width: 1
            border.color: Colors.orange

            // A separate, top-aligned review surface. Only the captured list
            // or report body scrolls; the resource viewport and footer do not.
            Rectangle {
                id: reviewPanel
                objectName: "cpuPlusRightReviewPanel"
                readonly property bool capture: workspace.hasBulkReview
                readonly property bool single: workspace.hasOwnedPending
                readonly property bool report: workspace.bulkOperation
                readonly property bool reportReady: report
                    && workspace.appControlWindow.hunterOperationPhase === "report"
                readonly property bool verifying: workspace.locallyPending && !!workspace.gate
                    && workspace.gate.busy && workspace.gate.pending === workspace.ownedPendingRef
                readonly property var singleTarget: single || verifying ? workspace.ownedPendingRef : null
                readonly property color panelInk: singleTarget
                    ? workspace.reviewProcessColor(singleTarget.name) : Colors.red
                readonly property real bodyRoom: Math.max(0, resourceBay.height - 20
                    - reviewHeading.implicitHeight - reviewFooter.implicitHeight
                    - 2 * reviewContent.spacing)
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.margins: 5
                height: Math.min(Math.max(0, resourceBay.height - 10), reviewContent.implicitHeight + 10)
                visible: capture || single || report || verifying
                color: Colors.black
                border.width: 1
                border.color: panelInk

                RectangularShadow {
                    anchors.fill: parent
                    spread: 4
                    z: -1
                    opacity: 0.45
                    color: reviewPanel.panelInk
                }
                Column {
                    id: reviewContent
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 5
                    spacing: 7
                    Column {
                        id: reviewHeading
                        width: parent.width
                        spacing: 5
                        GohuText {
                            id: reviewTitle
                            width: parent.width
                            wrapMode: Text.Wrap
                            color: Colors.red
                            font.pixelSize: 13
                            text: reviewPanel.capture ? "REVIEW // " + workspace.bulkReview.label
                                : reviewPanel.report ? "BULK // " + String(workspace.appControlWindow.hunterOperationKind).toUpperCase()
                                : reviewPanel.singleTarget ? "REVIEW // " + String(reviewPanel.singleTarget.action).toUpperCase() : ""
                            layer.enabled: reviewPanel.visible
                            layer.effect: DropShadow { radius: 6; samples: 7; opacity: 0.65; color: Colors.red; transparentBorder: true }
                        }
                        Rectangle { width: parent.width; height: 1; color: Colors.red }
                        Row {
                            objectName: "cpuPlusCapturedTargetCount"
                            width: parent.width
                            visible: reviewPanel.capture
                            spacing: 6
                            Item {
                                width: capturedCount.implicitWidth
                                height: capturedCount.implicitHeight
                                GohuText {
                                    id: capturedCount
                                    objectName: "cpuPlusCapturedTargetNumber"
                                    text: reviewPanel.capture ? String(workspace.bulkReview.targets.length) : ""
                                    color: Colors.magenta
                                    font.pixelSize: 13
                                }
                                SafeDropShadow {
                                    anchors.fill: capturedCount
                                    safeSource: capturedCount
                                    requestedVisible: reviewPanel.capture
                                    radius: 6; samples: 7; opacity: 0.75
                                    color: Colors.magenta
                                    transparentBorder: true
                                }
                            }
                            Item {
                                width: capturedLabel.implicitWidth
                                height: capturedLabel.implicitHeight
                                GohuText {
                                    id: capturedLabel
                                    objectName: "cpuPlusCapturedTargetLabel"
                                    text: "CAPTURED TARGETS"
                                    color: Colors.red
                                    font.pixelSize: 13
                                }
                                SafeDropShadow {
                                    anchors.fill: capturedLabel
                                    safeSource: capturedLabel
                                    requestedVisible: reviewPanel.capture
                                    radius: 6; samples: 7; opacity: 0.75
                                    color: Colors.red
                                    transparentBorder: true
                                }
                            }
                        }
                        GohuText {
                            width: parent.width
                            visible: reviewPanel.capture
                            text: "GLOBAL SCOPE • NOT SEARCH RESULTS\nNO COMMAND SENT • PROTECTION RECHECKED BEFORE DISPATCH"
                            wrapMode: Text.Wrap
                            color: Colors.white
                            font.pixelSize: 11
                            layer.enabled: visible
                            layer.effect: DropShadow { radius: 5; samples: 7; opacity: 0.45; color: Colors.white; transparentBorder: true }
                        }
                        Item {
                            width: parent.width
                            height: singleIdentity.implicitHeight
                            visible: !!reviewPanel.singleTarget
                            GohuText {
                                id: singleIdentity
                                objectName: "cpuPlusSingleReviewIdentity"
                                width: parent.width
                                wrapMode: Text.WrapAnywhere
                                textFormat: Text.RichText
                                text: reviewPanel.singleTarget ? workspace.reviewTargetText(reviewPanel.singleTarget,reviewPanel.panelInk) : ""
                                font.pixelSize: 13
                            }
                            SafeDropShadow {
                                anchors.fill: singleIdentity
                                safeSource: singleIdentity
                                requestedVisible: parent.visible
                                radius: 6; samples: 7; opacity: 0.65
                                color: reviewPanel.panelInk
                                transparentBorder: true
                            }
                        }
                    }
                    ListView {
                        id: captureList
                        objectName: "cpuPlusBulkReview"
                        width: parent.width
                        height: visible ? Math.min(reviewPanel.bodyRoom, count * 36) : 0
                        visible: reviewPanel.capture
                        clip: true
                        boundsBehavior: Flickable.StopAtBounds
                        model: reviewPanel.capture ? workspace.bulkReview.targets : []
                        onModelChanged: contentY = 0
                        delegate: Item {
                            required property var modelData
                            readonly property color processInk: workspace.reviewProcessColor(modelData.name)
                            width: captureList.width - (captureScroll.visible ? 18 : 0)
                            height: 36
                            GohuText {
                                id: capturedIdentity
                                width: parent.width
                                anchors.verticalCenter: parent.verticalCenter
                                text: workspace.reviewTargetText(modelData,parent.processInk)
                                textFormat: Text.RichText
                                font.pixelSize: 12
                                wrapMode: Text.WrapAnywhere
                            }
                            SafeDropShadow {
                                anchors.fill: capturedIdentity
                                safeSource: capturedIdentity
                                requestedVisible: reviewPanel.capture
                                radius: 6; samples: 7; opacity: 0.65
                                color: parent.processInk
                                transparentBorder: true
                            }
                        }
                    }
                    Flickable {
                        id: reviewTextScroll
                        width: parent.width
                        height: visible ? Math.min(reviewPanel.bodyRoom, reviewMessage.implicitHeight) : 0
                        visible: reviewPanel.single || reviewPanel.report || reviewPanel.verifying
                        clip: true
                        boundsBehavior: Flickable.StopAtBounds
                        contentWidth: width
                        contentHeight: reviewMessage.implicitHeight
                        onVisibleChanged: if (visible) contentY = 0
                        GohuText {
                            id: reviewMessage
                            objectName: "cpuPlusProcessReviewWarning"
                            width: Math.max(0,reviewTextScroll.width - (messageScroll.visible ? 18 : 0))
                            wrapMode: Text.Wrap
                            textFormat: Text.PlainText
                            text: reviewPanel.single
                                ? ("CONFIRM " + String(reviewPanel.singleTarget.action).toUpperCase()
                                    + "\nNO COMMAND HAS BEEN SENT"
                                    + (workspace.isProtected(workspace.currentTask)
                                        ? "\nWARNING // PROTECTED PROCESS\n" + workspace.protectedProcessRisk(workspace.currentTask)
                                        : ""))
                                : reviewPanel.verifying ? workspace.gate.feedback
                                : reviewPanel.report ? workspace.appControlWindow.cpuBulkMessage : ""
                            color: reviewPanel.report ? Colors.white : Colors.red
                            font.pixelSize: 12
                            layer.enabled: reviewTextScroll.visible
                            layer.effect: DropShadow { radius: 5; samples: 7; opacity: 0.45; color: reviewMessage.color; transparentBorder: true }
                        }
                    }
                    Column {
                        id: reviewFooter
                        width: parent.width
                        spacing: 6
                        ActionButton {
                            id: reviewConfirm
                            objectName: reviewPanel.capture ? "cpuPlusBulkConfirm" : "cpuPlusSingleConfirm"
                            width: parent.width
                            height: 38
                            visible: reviewPanel.capture || reviewPanel.single
                            available: workspace.active && (reviewPanel.capture
                                ? workspace.hasBulkReview : workspace.hasOwnedPending && workspace.exactTargetAvailable)
                            label: reviewPanel.capture ? "CONFIRM CAPTURE" : "CONFIRM REQUEST"
                            labelPixelSize: 12
                            accentColor: Colors.red
                            destructive: true
                            acceptedButtons: Qt.LeftButton
                            idleForegroundColor: Colors.red
                            hoverForegroundColor: Colors.red
                            idleContentGlowColor: Colors.red
                            hoverContentGlowColor: Colors.red
                            contentGlowIdleOpacity: 0.82
                            contentGlowHoverOpacity: 1.0
                            softGlowIdleOpacity: 0.55
                            softGlowHoverOpacity: 0.9
                            onLeftClicked: {
                                if (workspace.hasBulkReview) workspace.confirmBulk();
                                else if (workspace.gate && workspace.hasOwnedPending
                                        && workspace.exactTargetAvailable)
                                    workspace.gate.confirm();
                            }
                        }
                        ActionButton {
                            id: reviewCancel
                            objectName: reviewPanel.capture || reviewPanel.report ? "cpuPlusBulkCancel" : "cpuPlusSingleCancel"
                            width: parent.width
                            height: 34
                            visible: reviewPanel.capture || reviewPanel.single || reviewPanel.reportReady
                            available: workspace.active && visible
                            label: reviewPanel.reportReady ? "ACKNOWLEDGE" : "CANCEL"
                            labelPixelSize: 12
                            normalFace: true
                            accentColor: Colors.red
                            acceptedButtons: Qt.LeftButton
                            idleForegroundColor: Colors.white
                            hoverForegroundColor: Colors.white
                            pressedForegroundColor: Colors.white
                            hoverFillColor: Colors.red
                            pressedFillColor: Colors.dark
                            idleBorderColor: Colors.red
                            hoverBorderColor: Colors.red
                            pressedBorderColor: Colors.red
                            idleContentGlowColor: Colors.red
                            hoverContentGlowColor: Colors.red
                            pressedContentGlowColor: Colors.red
                            contentGlowIdleOpacity: 0.72
                            contentGlowHoverOpacity: 1.0
                            softGlowEnabled: true
                            idleSoftGlowColor: Colors.red
                            hoverSoftGlowColor: Colors.red
                            pressedSoftGlowColor: Colors.red
                            softGlowIdleOpacity: 0.55
                            softGlowHoverOpacity: 0.9
                            onLeftClicked: {
                                if (workspace.hasBulkReview) workspace.cancelBulk();
                                else if (workspace.hasOwnedPending) workspace.cancelOwned();
                                else if (reviewPanel.reportReady) workspace.appControlWindow.acknowledgeCpuBulkReport();
                            }
                        }
                    }
                }
                NeonScrollBar {
                    id: captureScroll
                    objectName: "cpuPlusCaptureReviewScroll"
                    flickable: captureList
                    geometryMode: "viewport"
                    accountForContentOrigin: true
                    topInset: 0; bottomInset: 0
                    x: reviewPanel.width - width - 4
                    y: reviewContent.y + captureList.y
                    visible: reviewPanel.capture && scrollable
                    handleStyle: "star"
                    railColor: Colors.red
                    handleColor: Colors.magenta
                    wheelEnabled: false
                }
                NeonScrollBar {
                    id: messageScroll
                    flickable: reviewTextScroll
                    geometryMode: "viewport"
                    topInset: 0; bottomInset: 0
                    x: reviewPanel.width - width - 4
                    y: reviewContent.y + reviewTextScroll.y
                    visible: reviewTextScroll.visible && scrollable
                    handleStyle: "star"
                    railColor: Colors.red
                    handleColor: Colors.magenta
                    wheelEnabled: false
                }
            }
        }
    }
}
