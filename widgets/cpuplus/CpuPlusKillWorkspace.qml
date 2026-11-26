import QtQuick
import Quickshell
import "../../components"
import "../appcontrol"
import "../../services/system"

// CPU++ owns navigation and presentation. AppControl owns the one live
// ProcessTelemetry and the birth-time-verified action gate. No second poller,
// kill/prlimit backend, detached command, or historical-census actuation.
Item {
    id: workspace
    objectName: "cpuPlusSharedKillWorkspace"
    required property var appControlWindow
    property bool active: true

    readonly property var gate: appControlWindow
        ? appControlWindow.hubProcessActionGate : null
    readonly property var taskRows: appControlWindow
        && Array.isArray(appControlWindow.taskRows)
        ? appControlWindow.taskRows : []

    // The live owner continues to own sampling and the persistent store.
    // These are CPU++-local view choices, never AppControl's current mode.
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
    readonly property int miniHistoryRevision: appControlWindow
        ? Number(appControlWindow.taskMiniDisplayRevision || 0) : 0
    readonly property var ownerFavoriteStore: appControlWindow
        ? appControlWindow.favoriteStore : null
    readonly property bool hunterOperationActive: false
    readonly property bool destructiveConfirmOpen: false
    readonly property string destructiveConfirmKind: ""
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
    function isProtected(row) {
        return !!row && !!gate && gate.isProtected(
            Number(row.pid), Number(row.startTicks), String(row.comm || ""));
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
        const revision=miniHistoryRevision;
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
        if (locallyPending || (gate && gate.busy)) return;
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
        return killViewMode===killViewHunter
            ? hunterGraph.metricGraphValue(row)+" • PID "+row.pid
            : "CPU "+Number(row.cpu || 0).toFixed(1)+"% • MEM "
               +Number(row.mem || 0).toFixed(1)+"%";
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
    function miniGraphPoints(row,key,w,h) {
        const values=key==="normal"
            ? detailGraph.miniCpuHistoryByIdentity("",row)
            : detailGraph.miniHunterHistoryForMetric(row,key);
        return graphGeometry.linePoints(values,w,h,
            key==="normal"?5:hunterGraph.metricRangeForKey(key),48,2,2);
    }
    // Mount the actual shared HunterControls including its bottom buttons.
    // Bulk dispatch is deliberately held until its owner can provide a
    // CPU++-local capture/confirmation contract. Empty eligibility disables
    // those buttons; it does not silently route a hidden donor confirmation.
    function killAllEligibleTasks() { return []; }
    function hunterHogCandidates() { return []; }
    function hunterMouseCandidates() { return []; }
    function requestKillAllEligibleTasks() { return false; }
    function requestKillHogs() { return false; }
    function requestKillMice() { return false; }

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
    readonly property bool exactTargetAvailable: !!gate && !!currentTask
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
        if (!row || !active || locallyPending || (gate && gate.busy)) return false;
        if (sameTarget(row)) return true; // hovering over the current row must not reset graphs
        stagedLimitPercent=-1;
        selectedPid=Number(row.pid || 0);
        selectedStartTicks=Number(row.startTicks || 0);
        selectedComm=String(row.comm || "");
        taskHost.detailFocused=false;
        taskHost.selectedDetailActionIndex=-1;
        history.resetDetailHistories();
        history.taskHistoryPid=selectedPid;
        const preload=detailGraph.miniCpuHistoryByIdentity("",row);
        history.taskCpuHistory=preload.slice(-history.taskHistoryLimit);
        history.taskMemHistory=[Math.max(0,Number(row.mem || 0))];
        detailGraph.seedHunterDetailHistories(row);
        repaintDetail(true);
        detailsScroll.contentY=0;
        return true;
    }

    function repaintDetail(reset) {
        if (!ready || !details) return;
        details.cpuCanvas.requestPaint(false,!!reset);
        details.memCanvas.requestPaint(false,!!reset);
        details.combiScoreCanvas.requestPaint(false,!!reset);
    }
    function appendCurrentHistory() {
        const row=matchingRow();
        if (!row || !active || !ready) return;
        // Use real owner snapshots only. The shared graph controller publishes
        // bounded history arrays and starts the original scrolling animations.
        detailGraph.appendTaskHistoryValues(Number(row.cpu || 0),Number(row.mem || 0));
        detailGraph.appendSelectedTaskHunterHistories(row,Number(row.cpu || 0),
            Number(row.rss || 0),Number(row.mem || 0));
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
        if (!active || !exactTargetAvailable || !gate || locallyPending)
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
    function canChangeLock(row) {
        return active && exactTargetAvailable && sameTarget(row)
            && !!gate && !gate.pending && !gate.busy
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
    onTaskRowsChanged: {
        if (!ready || !active) return;
        if (!modelBlank) updateOrder(false);
        appendCurrentHistory();
    }
    onActiveChanged: {
        if (!active) cancelOwned();
        else if (ready) requestRefresh();
    }
    Component.onCompleted: {
        ready=true;
        updateOrder(true);
        requestRefresh();
    }
    Component.onDestruction: cancelOwned()
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
    ProcessPresentationState {
        id: history
        taskMiniCpuHistories: workspace.appControlWindow
            ? (workspace.appControlWindow.taskMiniCpuHistories || ({})) : ({})
        taskMiniHunterMetricHistories: workspace.appControlWindow
            ? (workspace.appControlWindow.taskMiniHunterMetricHistories || ({})) : ({})
        taskMiniHistoryRevision: workspace.miniHistoryRevision
    }
    HunterPresentation {
        id: hunterGraph
        presentationState: history
        metricMode: workspace.hunterMetricMode
    }
    TaskGraphController {
        id: detailGraph
        presentationState: history
        hunterPresentation: hunterGraph
        // Only append/seed presentation methods are used. The donor owns
        // process acquisition and its selected-detail probe.
        telemetry: null
        onPrepareCpuMemAppend: {
            if (workspace.ready) {
                details.cpuCanvas.requestPaint(true);
                details.memCanvas.requestPaint(true);
            }
        }
        onPrepareCombiAppend: {
            if (workspace.ready) details.combiScoreCanvas.requestPaint(true);
        }
        onRepaintCpuMem: function(reset) { workspace.repaintDetail(reset); }
        onRepaintCpu: function(reset) {
            if (workspace.ready) details.cpuCanvas.requestPaint(false,!!reset);
        }
        onRepaintAll: function(reset) { workspace.repaintDetail(reset); }
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
            // Preview only. Right bay requires APPLY then CONFIRM.
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
            selectedDetailActionIndex = Math.max(-2, Math.min(2,
                selectedDetailActionIndex + Number(direction || 0)));
        }
        function ensureDetailActionVisible() {
            const actions=[details.restartAction,details.limitSlider,
                details.freezeAction,details.endAction];
            const item=actions[selectedDetailActionIndex+1];
            if (!item || !actuatorScroll) return;
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
            width: Math.min(workspace.instrumentWidth, Math.max(0,bays.width-targetBay.width))
            height: bays.height
            color: Colors.dark
            border.width: 1
            border.color: Colors.orange

            GohuText {
                id: instrumentTitle
                anchors.top: parent.top
                anchors.topMargin: 14
                anchors.horizontalCenter: parent.horizontalCenter
                text: "PROCESS // TASK MANAGER"
                color: Colors.magenta
                font.pixelSize: 12
            }
            Rectangle {
                id: processIdentity
                objectName: "cpuPlusProcessIdentity"
                anchors.top: instrumentTitle.bottom
                anchors.topMargin: 7
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.margins: 8
                height: 114
                color: Colors.black
                border.color: Colors.cyan
                border.width: 1
                visible: !!workspace.currentTask
                Column {
                    anchors.fill: parent
                    anchors.margins: 8
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
                        height: Math.max(0,parent.height-43)
                        text: workspace.currentTask && workspace.appControlWindow.taskSimplePurpose
                            ? workspace.appControlWindow.taskSimplePurpose(workspace.currentTask) : ""
                        textFormat: Text.PlainText
                        font.pixelSize: 10
                        color: Colors.white
                        opacity: 0.58
                        wrapMode: Text.Wrap
                        elide: Text.ElideRight
                        clip: true
                    }
                }
            }
            Item {
                id: processStateHeader
                objectName: "cpuPlusProcessStateHeader"
                anchors.top: processIdentity.visible ? processIdentity.bottom : instrumentTitle.bottom
                anchors.topMargin: 4
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.leftMargin: 8
                anchors.rightMargin: 8
                height: 30
                visible: !!workspace.currentTask
                GohuText {
                    anchors.left: parent.left
                    anchors.leftMargin: 8
                    anchors.verticalCenter: parent.verticalCenter
                    text: "PROCESS STATE"
                    color: Colors.red
                    font.pixelSize: 13
                }
                ProcessSafetyLock {
                    objectName: "cpuPlusProcessMasterLock"
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    width: 30
                    height: 26
                    controller: workspace
                    taskItem: workspace.currentTask
                    accentColor: Colors.magenta
                }
                Rectangle {
                    anchors.bottom: parent.bottom
                    width: parent.width
                    height: 1
                    color: Colors.red
                }
            }
            GohuText {
                id: emptyTarget
                visible: !workspace.currentTask
                anchors.centerIn: parent
                width: parent.width - 25
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.Wrap
                text: "SELECT A LIVE PROCESS IN THE MIDDLE BAY"
                color: Colors.cyan
                font.pixelSize: 12
            }
            Flickable {
                id: detailsScroll
                anchors.top: processStateHeader.bottom
                anchors.topMargin: 8
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.margins: 6
                clip: true
                visible: !!workspace.currentTask
                contentWidth: width
                contentHeight: details.implicitHeight + 20
                TaskManagerView {
                    id: details
                    objectName: "cpuPlusKillSharedTaskView"
                    x: 8
                    width: Math.max(0,detailsScroll.width - 20)
                    host: taskHost
                    presentationState: history
                    processController: processView
                    graphGeometry: graphGeometry
                    hunterGraph: hunterGraph
                    searchInputTarget: processSearch
                    safetyLockComponent: safetyLock
                    actionTarget: rightActions
                }
            }
            NeonScrollBar {
                objectName: "cpuPlusKillDetailScroll"
                flickable: detailsScroll
                geometryMode: "viewport"
                visible: detailsScroll.visible && scrollable
                railColor: Colors.red
                handleColor: Colors.magenta
                wheelEnabled: false
            }
        }

        Rectangle {
            id: targetBay
            width: Math.min(workspace.targetWidth,bays.width)
            height: bays.height
            color: Colors.black
            border.width: 1
            border.color: Colors.orange
            GohuText {
                id: targetTitle
                anchors.top: parent.top
                anchors.topMargin: 14
                anchors.horizontalCenter: parent.horizontalCenter
                text: workspace.killViewMode===workspace.killViewHunter ? "HUNTER" : "KILL"
                color: Colors.red
                font.pixelSize: 12
            }
            Rectangle {
                id: searchHeader
                anchors.top: targetTitle.bottom
                anchors.topMargin: 7
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.margins: 6
                height: 27
                color: Colors.black
                border.color: Colors.red
                TextInput {
                    id: processSearch
                    objectName: "cpuPlusKillSearch"
                    anchors.fill: parent
                    anchors.margins: 4
                    font.family: "GohuFont 11 Nerd Font Mono"
                    font.pixelSize: 14
                    color: Colors.magenta
                    selectionColor: Colors.yellow
                    selectedTextColor: Colors.black
                    clip: true
                    selectByMouse: true
                }
                GohuText {
                    anchors.left: parent.left
                    anchors.leftMargin: 4
                    anchors.verticalCenter: parent.verticalCenter
                    text: "SEARCH PROCESSES"
                    color: Colors.white
                    opacity: 0.45
                    font.pixelSize: 10
                    visible: processSearch.text.length===0 && !processSearch.activeFocus
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
                anchors.rightMargin: 14
                anchors.bottomMargin: hunterControls.bottomSelectorHeight+18
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
            NeonScrollBar {
                objectName: "cpuPlusKillTargetScroll"
                flickable: targets
                geometryMode: "viewport"
                accountForContentOrigin: true
                x: targetBay.width-width-3
                visible: scrollable
                railColor: Colors.red
                handleColor: Colors.magenta
                wheelEnabled: false
            }
            GohuText {
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottom: parent.bottom
                anchors.bottomMargin: hunterControls.bottomSelectorHeight+2
                text: String(workspace.filteredRows.length)+" TARGETS • BULK HOLD"
                color: Colors.orange
                font.pixelSize: 9
            }
        }

        Rectangle {
            id: actuatorBay
            width: Math.max(0,bays.width-instrumentBay.width-targetBay.width)
            height: bays.height
            color: Colors.dark
            border.width: 1
            border.color: Colors.orange
            Flickable {
                id: actuatorScroll
                anchors.fill: parent
                anchors.margins: 8
                clip: true
                contentWidth: width
                contentHeight: actuatorBody.implicitHeight + 12
                Column {
                id: actuatorBody
                width: Math.max(0,actuatorScroll.width-14)
                spacing: 12
                GohuText {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "PROCESS // ACTUATORS"
                    color: Colors.magenta
                    font.pixelSize: 12
                }
                GohuText {
                    width: parent.width
                    wrapMode: Text.Wrap
                    text: workspace.currentTask
                        ? (String(workspace.currentTask.comm)
                           + " // PID " + workspace.selectedPid)
                        : "NO LIVE PROCESS SELECTED"
                    color: Colors.cyan
                    font.pixelSize: 12
                }
                GohuText {
                    width: parent.width
                    wrapMode: Text.Wrap
                    text: workspace.exactTargetAvailable
                        ? "EXACT LIVE PID + START TICKS + NAME"
                        : "TARGET IDENTITY NOT VERIFIED // CONTROLS LOCKED"
                    color: workspace.exactTargetAvailable ? Colors.white : Colors.orange
                    font.pixelSize: 10
                }
                GohuText {
                    width: parent.width
                    wrapMode: Text.Wrap
                    text: "Live owner • explicit review before dispatch"
                    color: Colors.white
                    font.pixelSize: 10
                }
                Column {
                    id: rightActions
                    objectName: "cpuPlusSharedActionTarget"
                    width: parent.width
                    spacing: 12
                    visible: !!workspace.currentTask
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
                GohuText {
                    width: parent.width
                    visible: workspace.hasOwnedPending
                    wrapMode: Text.Wrap
                    text: workspace.hasOwnedPending
                        ? ("CONFIRM " + String(workspace.gate.pending.action).toUpperCase()
                           + " FOR PID " + String(workspace.gate.pending.pid)
                           + "\nNO COMMAND HAS BEEN SENT")
                        : ""
                    color: Colors.red
                    font.pixelSize: 12
                }
                Rectangle {
                    width: parent.width
                    height: 38
                    visible: workspace.hasOwnedPending
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.red
                    GohuText {
                        anchors.centerIn: parent
                        text: "CONFIRM REQUEST"
                        color: Colors.red
                        font.pixelSize: 12
                    }
                    MouseArea {
                        anchors.fill: parent
                        enabled: workspace.hasOwnedPending
                        onClicked: {
                            if (workspace.gate && workspace.hasOwnedPending)
                                workspace.gate.confirm()
                        }
                    }
                }
                Rectangle {
                    width: parent.width
                    height: 34
                    visible: workspace.hasOwnedPending
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.cyan
                    GohuText {
                        anchors.centerIn: parent
                        text: "CANCEL"
                        color: Colors.cyan
                        font.pixelSize: 12
                    }
                    MouseArea {
                        anchors.fill: parent
                        onClicked: workspace.cancelOwned()
                    }
                }
                GohuText {
                    width: parent.width
                    wrapMode: Text.Wrap
                    text: "Left click lock: one-shot • Right click: sticky. Existing owner safety policy applies. Dispatch is not proof of success."
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
        }
    }
}
