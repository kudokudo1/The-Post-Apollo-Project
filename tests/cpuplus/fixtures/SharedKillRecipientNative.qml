import QtQuick
// P3c3 main-lineage native qualification: exercise the recipient after the P3c2 parent merge.
import QtQuick.Window
import Quickshell
import "widgets/cpuplus"
import "services/system"
import "services/kill" as KillBackend
import qs.services.favorites

ShellRoot {
    id: smoke
    readonly property bool armed:
        Quickshell.env("POST_APOLLO_CPU_KILL_SMOKE") === "CI_DISPOSABLE_ONLY"
    property int phase: 0
    property int ticks: 0
    property bool done: false
    property int previousRevision: 0
    property real previousMiniOffset: 0
    property real previousCpuOffset: 0
    property real previousInfoHeight: 0
    property real previousInfoY: 0
    property real previousScopeHeight: 0
    property real previousArgumentsHeight: 0
    property var lastRow: null
    property var protectedGeometry: null
    property bool stableLayoutChecked: false
    property real priorInstrumentY: 0
    property var priorReviewGeometry: null
    property real priorCancelY: 0

    QtObject {
        id: fakePresentation
        function metricIsCritical(row, key) { return false; }
        function formatMemory(kib) { return Number(kib || 0).toFixed(0) + " KiB"; }
        function limitResultFor(row) { return {state:"unmanaged",message:"NO KILL-MANAGED LIMIT"}; }
        function hasSoftLimit(row) { return false; }
        function limitMinimumMiB(row) { return 128; }
        function limitMaximumMiB(row) { return 4096; }
        function limitMiB(row) { return 4096; }
        function limitPercent(row) { return 100; }
        function isFrozen(row) { return false; }
        function scopeProcessText(row) { return "PROCESS " + row.pid; }
    }

    QtObject {
        id: fakeGate
        property var presentationOwner: fakePresentation
        property var pending: null
        property bool busy: false
        readonly property bool bulkBlocked: fakeOwner.cpuBulkReview !== null
            || fakeOwner.hunterOperationPhase !== "idle" || fakeOwner.destructiveConfirmOpen
        property string feedback: ""
        property int preparations: 0
        property int confirmations: 0
        property int cancels: 0
        function exactRow(pid, ticks, name) {
            for (const r of fakeOwner.taskRows) {
                if (r.pid === pid && r.startTicks === ticks && r.comm === name)
                    return r;
            }
            return null;
        }
        function isProtected(pid, ticks, name) { return fakeOwner.taskRequiresDangerUnlock(exactRow(pid,ticks,name)); }
        function isUnlocked(pid, ticks, name, action) {
            return !!exactRow(pid,ticks,name) && (!isProtected(pid,ticks,name) || fakeOwner.taskDangerActionUnlockMode(
                exactRow(pid,ticks,name),action)!=="");
        }
        function currentLimitPercent(pid, ticks, name) { return 100; }
        function toggleOneShotUnlock(pid, ticks, name) {
            if (!exactRow(pid,ticks,name)) return false;
            fakeOwner.masterMode=fakeOwner.masterMode ? "" : "once";
            return true;
        }
        function prepare(pid, ticks, name, action, percent) {
            if (pending || busy || !exactRow(pid,ticks,name))
                return false;
            pending = {pid:pid, startTicks:ticks, name:name, action:action,
                       percent:percent};
            preparations++;
            feedback = "REVIEW AND CONFIRM // NOT EXECUTED";
            return true;
        }
        function cancel() {
            if (!pending || busy) return false;
            pending = null;
            cancels++;
            feedback = "CANCELLED";
            return true;
        }
        function confirm() {
            if (!pending || !exactRow(pending.pid,pending.startTicks,pending.name))
                return false;
            confirmations++;
            pending = null;
            feedback = "SYNTHETIC CONFIRMATION";
            return true;
        }
    }

    ProcessPresentationState {
        id: fakeHistory
        taskMiniCpuHistories: ({"pid:3442":[2,5,12]})
        taskMiniHunterMetricHistories: ({
            "cpu:pid:3442":[2,5,12], "mem:pid:3442":[20,21,23],
            "io:pid:3442":[0,1,2], "age:pid:3442":[0.5,0.7,0.9],
            "combined:pid:3442":[2,6,14]})
        taskMiniCpuIdentityHistories: ({})
        taskMiniDisplayRevision: 1
    }
    HunterPresentation {
        id: fakeHunter
        presentationState: fakeHistory
    }
    QtObject {
        id: fakeTelemetry
        property bool detailProbeLoading: false
        function resetDetailProbe(pid) {}
        function refreshDetailProbe(request) {}
    }
    KillBackend.TaskGraphController {
        id: fakeGraph
        extraDetailHistoryEnabled: true
        presentationState: fakeHistory
        hunterPresentation: fakeHunter
        telemetry: fakeTelemetry
        taskRows: fakeOwner.taskRows
    }
    KillBackend.KillDetailSession {
        id: fakeSession
        graph: fakeGraph
        state: fakeHistory
        rows: fakeOwner.taskRows
    }
    QtObject {
        id: fakeOwner
        property var hubProcessActionGate: fakeGate
        readonly property var actionGate: fakeGate
        property var taskRows: [{
            id: "task:3442", _taskRecord: true, pid: 3442, startTicks: 967833,
            comm:"synthetic-worker", name:"synthetic-worker",
            cpu:12, mem:4, rss:23456, vsz:100000,
            threads:3, state:"S", ppid:1, elapsed:"00:55",
            user:"ci", args:"synthetic-worker --test " + Array(150).fill("--synthetic-long-argument").join(" ")
        }]
        property alias taskMiniCpuHistories: fakeHistory.taskMiniCpuHistories
        property alias taskMiniHunterMetricHistories: fakeHistory.taskMiniHunterMetricHistories
        property alias taskMiniDisplayRevision: fakeHistory.taskMiniDisplayRevision
        property bool destructiveConfirmOpen: false
        readonly property bool donorActionBlocked: destructiveConfirmOpen
        readonly property var safety: QtObject {
            function dangerReason(row) { return fakeOwner.taskDangerReason(row); }
            function requiresDangerUnlock(row) { return fakeOwner.taskRequiresDangerUnlock(row); }
        }
        property var cpuBulkReview: null
        property bool cpuBulkOperation: false
        property string hunterOperationPhase: "idle"
        property string hunterOperationKind: ""
        property string cpuBulkMessage: ""
        property int bulkConfirmed: 0
        property int bulkCancelled: 0
        function cpuBulkCandidates(kind,metric,visibility) { return taskRows; }
        function prepareCpuBulkReview(kind,metric,visibility) {
            if (cpuBulkReview || cpuBulkOperation) return null;
            cpuBulkReview={kind:kind,metric:metric,visibility:visibility,label:"FAKE",
                targets:Array.from({length:60},function(_,i) {
                    return {pid:3442+i,startTicks:967833+i,name:["brave","systemd","kitty"][i%3]};
                })};
            return cpuBulkReview;
        }
        function cancelCpuBulkReview(review) {
            if (review !== cpuBulkReview) return false;
            cpuBulkReview=null; bulkCancelled++; return true;
        }
        function confirmCpuBulkReview(review) {
            if (review !== cpuBulkReview) return false;
            hunterOperationKind=review.kind; cpuBulkReview=null;
            cpuBulkOperation=true; hunterOperationPhase="running"; bulkConfirmed++;
            return true;
        }
        function acknowledgeCpuBulkReport() {
            cpuBulkOperation=false; hunterOperationPhase="idle"; return true;
        }
        property string masterMode: ""
        property var actionModes: ({})
        property bool protectTargets: true
        function taskRequiresDangerUnlock(row) { return !!row && protectTargets; }
        function taskDangerReason(row) { return "SYNTHETIC SESSION-CRITICAL PROCESS"; }
        function taskDangerUnlockMode(row) { return masterMode; }
        function taskDangerActionLocalUnlockMode(row,action) { return String(actionModes[action] || ""); }
        function taskDangerActionUnlockMode(row,action) {
            return masterMode || String(actionModes[action] || "");
        }
        function toggleTaskDangerStickyUnlock(row) {
            masterMode=masterMode==="sticky"?"":"sticky";
        }
        function toggleTaskDangerActionStickyUnlock(row,action) {
            let next=Object.assign({},actionModes);
            next[action]=next[action]==="sticky"?"":"sticky";
            actionModes=next;
        }
        function toggleTaskDangerActionUnlock(row,action) {
            let next=Object.assign({},actionModes);
            next[action]=next[action]?"":"once";
            actionModes=next;
        }
        function lockModeForIdentity(pid,birth,name,action,localOnly) {
            const row=fakeGate.exactRow(pid,birth,name);
            if (!row) return "";
            if (!action) return localOnly ? "" : taskDangerUnlockMode(row);
            return localOnly ? taskDangerActionLocalUnlockMode(row,action)
                             : taskDangerActionUnlockMode(row,action);
        }
        function toggleLockForIdentity(pid,birth,name,action,sticky) {
            const row=fakeGate.exactRow(pid,birth,name);
            if (!row || fakeGate.pending || fakeGate.busy || fakeGate.bulkBlocked
                    || !taskRequiresDangerUnlock(row)) return false;
            if (!action && sticky) toggleTaskDangerStickyUnlock(row);
            else if (action && sticky) toggleTaskDangerActionStickyUnlock(row,action);
            else if (action) toggleTaskDangerActionUnlock(row,action);
            else return fakeGate.toggleOneShotUnlock(pid,birth,name);
            return true;
        }
        function monitorResultIcon(row) { return "(╭ರ_•́)"; }
        property bool menuOpen: false
        property int selectedModeIndex: 0
        readonly property int killModeIndex: 7
        property int refreshes: 0
        readonly property var rows: taskRows
        function refreshSnapshot() { refreshes++; }
    }

    Window {
        id: win
        visible: smoke.armed
        width: 980
        height: 690
        Loader {
            id: scene
            anchors.fill: parent
            active: smoke.armed
            sourceComponent: CpuPlusKillWorkspace {
                graphSource: fakeHistory
                graphController: fakeGraph
                graphSession: fakeSession
                collectionSource: fakeOwner
                active: smoke.armed
            }
        }
    }

    function instrumentGeometry(view) {
        const names=["cpuPlusProcessIdentity","cpuPlusProcessStateHeader",
            "cpuPlusProcessKillSlot","cpuPlusProcessHeaderActions","cpuPlusProcessFreezeSlot",
            "cpuPlusProcessIndependentLockRail","cpuPlusProcessLockHelpButton",
            "cpuPlusKillInstrumentViewport","cpuPlusKillSharedTaskView","cpuPlusProcessLimitLockSlot",
            "cpuPlusSharedActionTarget"];
        return names.map(function(name) {
            const item=smoke.find(view,name);
            const p=item.mapToItem(view,0,0);
            return [p.x,p.y,item.width,item.height].map(v=>Math.round(v*100)/100);
        });
    }

    function find(item, name) {
        if (!item) return null;
        if (item.objectName === name) return item;
        for (const child of item.children || []) {
            const found = find(child,name);
            if (found) return found;
        }
        return null;
    }

    function check(ok, reason) {
        if (!ok) {
            console.error("CPU_KILL_NATIVE_FAIL // " + reason);
            done = true;
            Qt.quit();
            return false;
        }
        return true;
    }

    Timer {
        interval: 120
        repeat: true
        running: smoke.armed && !smoke.done
        onTriggered: {
            if (++smoke.ticks > 65) { smoke.check(false,"timeout"); return; }
            const view = scene.item;
            if (!view || view.width <= 0) return;
            const detail = smoke.find(view,"cpuPlusKillSharedTaskView");
            const targets = smoke.find(view,"cpuPlusKillLiveTargets");
            if (!detail || !targets
                    || (smoke.phase === 0 && targets.count !== 1)) {
                if (smoke.ticks > 12) {
                    smoke.check(false, "mount incomplete: loader="
                        + String(scene.status) + " view=" + (!!view)
                        + " detail=" + (!!detail) + " targets=" + (!!targets)
                        + " count=" + (targets ? targets.count : "none")
                        + " rows=" + fakeOwner.taskRows.length);
                }
                return;
            }

            if (smoke.phase === 0) {
                if (!smoke.check(!view.currentTask && fakeGate.preparations===0
                    && fakeGate.confirmations===0, "no default target / mutation"))
                    return;
                view.selectTarget(fakeOwner.taskRows[0]);
                smoke.phase = 1;
                return;
            }
            if (smoke.phase === 18) {
                if (!smoke.check(!smoke.find(view,"cpuPlusProcessMasterLock").visible
                    && smoke.find(view,"cpuPlusLockRiskHelp").text.indexOf("ORDINARY TARGET")>=0
                    && JSON.stringify(smoke.instrumentGeometry(view))===JSON.stringify(smoke.protectedGeometry),
                    "unprotected target keeps identical instrument and lock-slot geometry")) return;
                fakeOwner.protectTargets=true;
                smoke.phase=19;
                return;
            }
            if (smoke.phase === 19) {
                if (!smoke.check(smoke.find(view,"cpuPlusProcessMasterLock").visible
                    && smoke.find(view,"cpuPlusLockRiskHelp").text.indexOf("PROTECTED TARGET")>=0
                    && JSON.stringify(smoke.instrumentGeometry(view))===JSON.stringify(smoke.protectedGeometry),
                    "protected target restores locks without moving instruments")) return;
                smoke.stableLayoutChecked=true;
                smoke.phase=1;
                return;
            }
            if (smoke.phase === 1) {
                if (!smoke.stableLayoutChecked) {
                    smoke.protectedGeometry=smoke.instrumentGeometry(view);
                    fakeOwner.protectTargets=false;
                    smoke.phase=18;
                    return;
                }
                // K8d: the right surface is an identity-bound draft, never
                // an alternate Linux executor or a second confirmation gate.
                const consolePane=smoke.find(view,"cpuPlusKillResourceConsoleSurface");
                const cpuFilter=smoke.find(view,"cpuPlusResourceFilter-cpu");
                const memoryFilter=smoke.find(view,"cpuPlusResourceFilter-memory");
                const netFilter=smoke.find(view,"cpuPlusResourceFilter-network");
                const selectedPanel=smoke.find(view,"cpuPlusResourceSelectedPanel");
                const resourceInfo=smoke.find(view,"cpuPlusResourceInformationButton");
                const resourcePopup=smoke.find(view,"cpuPlusResourceInformationPopup");
                const headerSection=smoke.find(view,"cpuPlusResourceHeaderSection");
                const headerResourceTitle=smoke.find(view,"cpuPlusResourceSelectedTitle");
                const headerCapability=smoke.find(view,"cpuPlusResourceCapabilityStatus");
                const controlsScroll=smoke.find(view,"cpuPlusResourceConsoleScroll");
                const headerDivider=smoke.find(view,"cpuPlusResourceHeaderDivider");
                const footerDivider=smoke.find(view,"cpuPlusResourceFooterDivider");
                const draftActions=smoke.find(view,"cpuPlusResourceDraftActionsStrip");
                const clearDraft=smoke.find(view,"cpuPlusResourceClearDraft");
                const reviewDraft=smoke.find(view,"cpuPlusResourceReviewDraft");
                const primaryInstrument=smoke.find(view,"cpuPlusResourceInstrumentRow-cpu-quota");
                const primarySlider=smoke.find(view,"cpuPlusDraftSlider-cpu-quota");
                const primaryModes=smoke.find(view,"cpuPlusResourceInlineModes");
                const manualMode=smoke.find(view,"cpuPlusResourceMode-manual");
                const applyLocked=smoke.find(view,"cpuPlusResourceApplyLocked");
                const detailState = "console=" + (!!consolePane)
                    + " ready=" + (consolePane ? consolePane.selectionReady : "missing")
                    + " identity=" + (consolePane ? consolePane.targetIdentity : "missing")
                    + " cpuFilter=" + (!!cpuFilter)
                    + " cpuSelected=" + (cpuFilter ? cpuFilter.selected : "missing")
                    + " memoryFilter=" + (!!memoryFilter)
                    + " networkFilter=" + (!!netFilter)
                    + " selectedPanel=" + (selectedPanel ? selectedPanel.key : "missing")
                    + " apply=" + (!!applyLocked)
                    + " available=" + (applyLocked ? applyLocked.available : "missing")
                    + " draft=" + (consolePane ? consolePane.reviewLines.length : "missing")
                    + " prep=" + fakeGate.preparations + " confirm=" + fakeGate.confirmations;
                if (!smoke.check(consolePane && consolePane.selectionReady
                        && consolePane.targetIdentity.length>0
                        && cpuFilter && cpuFilter.selected && memoryFilter && netFilter
                        && selectedPanel && selectedPanel.key==="cpu"
                        && applyLocked && !applyLocked.available
                        && consolePane.reviewLines.length===0
                        && fakeGate.preparations===0 && fakeGate.confirmations===0,
                        "resource console mounts draft-only beside existing KILL controls; " + detailState)) return;
                // All seven filter buttons must fit simultaneously in the top bar.
                const filterButtons=["cpu","memory","swap","disk","threads","gpu","network"]
                    .map(function(key) { return smoke.find(view,"cpuPlusResourceFilter-"+key); });
                let lastEdge=-1;
                let oneRow=true;
                let selectedCount=0;
                let filterY=0;
                if (filterButtons.every(function(button) { return !!button; })) {
                    filterY=filterButtons[0].mapToItem(consolePane,0,0).y;
                    for (const button of filterButtons) {
                        const pos=button.mapToItem(consolePane,0,0);
                        if (!button.visible || pos.x<0 || pos.x<lastEdge-0.5
                                || pos.x+button.width>consolePane.width+0.5
                                || Math.abs(pos.y-filterY)>0.5 || button.width<30)
                            oneRow=false;
                        lastEdge=pos.x+button.width;
                        if (button.selected) selectedCount++;
                    }
                } else oneRow=false;
                if (!smoke.check(oneRow && selectedCount===1
                        && filterButtons.every(function(button) { return !!button; }),
                        "seven resource filters remain on one visible non-overlapping row")) return;
                // Match the Time widget: modes sit beside the first slider,
                // help is right-aligned below filters, and workspace actions
                // stay ABOVE the red divider. No process operation is possible.
                const infoPosition=resourceInfo ? resourceInfo.mapToItem(consolePane,0,0) : null;
                const filterPosition=cpuFilter ? cpuFilter.mapToItem(consolePane,0,0) : null;
                const modePosition=primaryModes && primaryInstrument
                    ? primaryModes.mapToItem(primaryInstrument,0,0) : null;
                const sliderPosition=primarySlider && primaryInstrument
                    ? primarySlider.mapToItem(primaryInstrument,0,0) : null;
                const clearPosition=clearDraft ? clearDraft.mapToItem(consolePane,0,0) : null;
                const footerPosition=footerDivider ? footerDivider.mapToItem(consolePane,0,0) : null;
                const headerTop=headerSection ? headerSection.mapToItem(consolePane,0,0) : null;
                const controlsTop=controlsScroll ? controlsScroll.mapToItem(consolePane,0,0) : null;
                if (!smoke.check(headerSection && headerResourceTitle
                        && headerCapability && controlsScroll && headerTop && controlsTop
                        && headerSection.height>=112
                        && controlsTop.y>=headerTop.y+headerSection.height-1
                        && headerResourceTitle.visible
                        && headerCapability.text.indexOf("NOT VERIFIED")>=0
                        && headerResourceTitle.text.indexOf("CPU")>=0,
                        "KILL right header is fixed, substantial, and controls begin below it")) return;
                if (!smoke.check(resourceInfo && resourcePopup && !resourcePopup.visible
                        && headerDivider && Qt.colorEqual(headerDivider.color,"#D16041")
                        && infoPosition && filterPosition
                        && infoPosition.x+resourceInfo.width<=consolePane.width+1
                        && infoPosition.x+resourceInfo.width>=consolePane.width-16
                        && infoPosition.y>=filterPosition.y+cpuFilter.height-1,
                        "resource information control is top-right below filters with red header rule")) return;
                if (!smoke.check(primaryModes && primaryInstrument && primarySlider
                        && manualMode && modePosition && sliderPosition
                        && modePosition.x>=sliderPosition.x+primarySlider.width-1
                        && Math.abs(modePosition.y-sliderPosition.y)<2,
                        "mode buttons occupy the primary slider row, not another control box")) return;
                if (!smoke.check(draftActions && clearDraft && reviewDraft && footerDivider
                        && clearPosition && footerPosition
                        && clearDraft.parent===reviewDraft.parent
                        && clearPosition.y+clearDraft.height<=footerPosition.y+1
                        && Qt.colorEqual(footerDivider.color,"#D16041")
                        && Qt.colorEqual(clearDraft.accentColor,"#D16041")
                        && Qt.colorEqual(reviewDraft.accentColor,"#F2BE4E")
                        && Qt.colorEqual(applyLocked.accentColor,"#9ECE6A")
                        && !applyLocked.available,
                        "draft actions above divider; clear red, review yellow, locked apply green")) return;
                resourceInfo.leftClicked(null);
                if (!smoke.check(resourcePopup.visible && fakeGate.preparations===0,
                        "resource information button opens read-only help")) return;
                resourceInfo.leftClicked(null);
                if (!smoke.check(!resourcePopup.visible,
                        "resource information button closes read-only help")) return;
                manualMode.leftClicked(null);
                if (!smoke.check(manualMode.selected && consolePane.modeFor("cpu")==="manual",
                        "inline MANUAL mode button stages only local draft state")) return;
                consolePane.stageMode("cpu","manual");
                consolePane.stageNumber("cpu","nice",9);
                if (!smoke.check(consolePane.hasDraft && consolePane.reviewLines.length===1
                        && consolePane.reviewLines[0].indexOf("NICE 9")>=0
                        && fakeGate.preparations===0 && fakeGate.confirmations===0,
                        "draft input never dispatches a process action")) return;
                // Fire the actual filter button signal, not the root helper,
                // to verify the same handler a pointer press reaches.
                netFilter.leftClicked(null);
                if (!smoke.check(consolePane.selectedKey==="network"
                        && !cpuFilter.selected && netFilter.selected
                        && selectedPanel.key==="network"
                        && consolePane.reviewLines.length===1
                        && fakeGate.preparations===0 && fakeGate.confirmations===0,
                        "top resource filters swap one editor without clearing the draft")) return;
                cpuFilter.leftClicked(null);
                if (!smoke.check(selectedPanel.key==="cpu" && cpuFilter.selected
                        && consolePane.reviewLines[0].indexOf("NICE 9")>=0,
                        "CPU draft survives category navigation")) return;
                reviewDraft.leftClicked(null);
                if (!smoke.check(consolePane.reviewing && fakeGate.confirmations===0,
                        "yellow review operates only on staged values")) return;
                clearDraft.leftClicked(null);
                if (!smoke.check(!consolePane.hasDraft && !consolePane.reviewing
                        && fakeGate.confirmations===0 && fakeGate.preparations===0,
                        "red clear draft does not affect owner state")) return;
                                const header=smoke.find(view,"cpuPlusProcessIdentity");
                const glyph=smoke.find(view,"cpuPlusProcessIdentityGlyph");
                const identityText=smoke.find(view,"cpuPlusProcessIdentityText");
                const name=smoke.find(view,"cpuPlusProcessIdentityName");
                const metadata=smoke.find(view,"cpuPlusProcessIdentityMetadata");
                const stateLabel=smoke.find(view,"cpuPlusProcessStateLabel");
                const gutter=smoke.find(view,"cpuPlusProcessGlowGutter");
                if (!smoke.check(glyph && identityText && name && metadata && stateLabel && gutter
                    && glyph.x+glyph.width<=identityText.x
                    && Math.abs(glyph.y+glyph.height/2-identityText.y-identityText.height/2)<1
                    && Qt.colorEqual(glyph.color,"#D16041")
                    && glyph.layer.enabled && name.layer.enabled && metadata.layer.enabled && stateLabel.layer.enabled
                    && !smoke.find(view,"taskMetricCard-pid")
                    && smoke.find(view,"taskMetricCard-swap")
                    && metadata.text.indexOf("PID ")>=0
                    && gutter.x>=8 && gutter.y>=8,
                    "red identity glyph beside centered glowing text and graph halo gutter")) return;
                const master=smoke.find(view,"cpuPlusProcessMasterLock");
                const actionTarget=smoke.find(view,"cpuPlusSharedActionTarget");
                const quick=smoke.find(view,"cpuPlusProcessHeaderActions");
                const kill=smoke.find(view,"cpuPlusProcessKillSlot");
                const freeze=smoke.find(view,"cpuPlusProcessFreezeSlot");
                const killLock=smoke.find(view,"cpuPlusProcessKillLockSlot");
                const freezeLock=smoke.find(view,"cpuPlusProcessFreezeLockSlot");
                const restartLock=smoke.find(view,"cpuPlusProcessRestartLockSlot");
                const lockRail=smoke.find(view,"cpuPlusProcessIndependentLockRail");
                const helpButton=smoke.find(view,"cpuPlusProcessLockHelpButton");
                const help=smoke.find(view,"cpuPlusProcessLockHelpPopup");
                const leftBay=smoke.find(view,"cpuPlusProcessControlBay");
                const rightBay=smoke.find(view,"cpuPlusProcessReservedBay");
                const search=smoke.find(view,"cpuPlusKillSearch");
                const hunter=smoke.find(view,"cpuPlusSharedHunterControls");
                const cursor=smoke.find(view,"cpuPlusKillAnimatedCursor");
                const searchHeader=smoke.find(view,"cpuPlusKillSearchHeader");
                const scroll=smoke.find(view,"cpuPlusKillTargetScroll");
                const top=smoke.find(view,"cpuPlusKillListTopDivider");
                const bottom=smoke.find(view,"cpuPlusKillListBottomDivider");
                if (!smoke.check(cursor && cursor.input===search && searchHeader.height===70
                    && search.height===22 && search.font.pixelSize===18
                    && view.displayedTargetCount===1
                    && scroll && scroll.starStyle && top && bottom
                    && Math.abs(scroll.y-top.y)<0.01
                    && Math.abs(scroll.y+scroll.height-bottom.y)<0.01,
                    "shared cursor mounted, donor search geometry and star track reaches both dividers")) return;
                if (!smoke.check(view.currentTask && view.currentTask.pid===3442
                    && detail.visible && header && header.visible
                    && master && master.visible && actionTarget
                    && leftBay && rightBay && leftBay.x < rightBay.x
                    && actionTarget.mapToItem(leftBay,0,0).x >= 0
                    && actionTarget.mapToItem(leftBay,0,0).x + actionTarget.width <= leftBay.width
                    && detail.mapToItem(leftBay,0,0).x >= 0
                    && detail.mapToItem(leftBay,0,0).x + detail.width <= leftBay.width
                    && detail.actionSection.parent===actionTarget
                    && quick && kill && freeze && killLock && freezeLock && restartLock && lockRail && helpButton && help
                    && detail.restartAction.parent===quick
                    && detail.freezeAction.parent===freeze
                    && detail.endAction.parent===kill
                    && detail.limitSlider.parent===detail.actionSection
                    && detail.restartAction.width===34 && detail.restartAction.height===34
                    && detail.freezeAction.width===34 && detail.freezeAction.height===34
                    && detail.endAction.width>detail.restartAction.width && detail.endAction.height===34
                    && detail.restartAction.showLabel && detail.freezeAction.showLabel && detail.endAction.showLabel
                    && kill.x < quick.x && quick.x < freeze.x
                    && killLock.parent===lockRail && restartLock.parent===lockRail && freezeLock.parent===lockRail
                    && killLock.y < restartLock.y && restartLock.y < freezeLock.y && freezeLock.y < helpButton.y
                    && freeze.mapToItem(leftBay,freeze.width,0).x + 6 <= lockRail.mapToItem(leftBay,0,0).x
                    && detail.freezeAction.label === "❆"
                    && detail.restartAction.label=== "⟳" && helpButton.label === "i"
                    && search && hunter
                    && smoke.find(view,"cpuPlusKillTargetScroll")
                    && smoke.find(view,"cpuPlusKillInstrumentViewport"),
                    "shared detail, identity, controls, scrollbar mounting")) return;
                const info=smoke.find(view,"cpuPlusProcessInformation");
                const infoButton=smoke.find(view,"cpuPlusProcessInformationButton");
                if (!smoke.check(info && infoButton && !info.visible && header.height>0 && !smoke.find(header,"cpuPlusProcessExactIdentity").visible && smoke.find(header,"cpuPlusProcessLiveOwner"),
                    "compact identity with hidden shared information")) return;
                if (!smoke.check(!help.visible && !help.open && helpButton.available, "lock help initially hidden")) return;
                helpButton.leftClicked(null);
                if (!smoke.check(!help.visible && !helpButton.selected && fakeGate.preparations===0, "click does not open hover-only help or request action")) return;
                info.open=true;
                if (!smoke.check(info.visible && infoButton.selected
                    && info.purpose==="synthetic-worker is one live Linux process. This panel shows its live CPU, memory, I/O, and age and can limit, freeze, or end this exact process."
                    && smoke.find(info,"processInformationScope")
                    && smoke.find(info,"processInformationArguments")
                    && smoke.find(info,"processInformationBirthIdentity").text.includes("967833")
                    && info.helpInk("CPU") !== info.helpInk("memory")
                    && info.height<=info.maximumHeight,
                    "bounded single-document information popup")) return;
                info.open=false;
                if (!smoke.check(!info.visible && !infoButton.selected,
                    "information closes without action")) return;
                fakeOwner.destructiveConfirmOpen=true;
                if (!smoke.check(view.legacyActionBlocked
                    && !view.prepareAction("end")
                    && !view.canChangeLock(view.currentTask)
                    && fakeGate.preparations===0,
                    "shared legacy exclusion refuses competing actions")) return;
                fakeOwner.destructiveConfirmOpen=false;
                if (!smoke.check(!view.legacyActionBlocked,
                    "legacy exclusion releases with owner state")) return;
                if (!smoke.check(view.toggleLock(view.currentTask,"restart",false)
                    && view.lockMode(view.currentTask,"restart")==="once"
                    && view.lockMode(view.currentTask,"kill")===""
                    && view.lockMode(view.currentTask,"freeze")===""
                    && detail.restartAction.available && !detail.endAction.available && !detail.freezeAction.available
                    && view.toggleLock(view.currentTask,"restart",false)
                    && !detail.restartAction.available, "restart lock is separate while master remains locked")) return;
                if (!smoke.check(view.toggleLock(view.currentTask,"limit",false)
                    && view.lockMode(view.currentTask,"limit")==="once"
                    && view.toggleLock(view.currentTask,"limit",true)
                    && view.lockMode(view.currentTask,"limit")==="sticky"
                    && view.toggleLock(view.currentTask,"",false)
                    && master.mode==="once"
                    && view.toggleLock(view.currentTask,"",true)
                    && master.mode==="sticky", "three real owner lock states")) return;
                // Exercise the real singleton in the fixture's disposable XDG directory.
                FavoritesService.toggleFavoriteKey("app|fixture-sentinel");
                view.toggleTaskFavorite(view.currentTask);
                if (!smoke.check(view.isTaskFavorite(view.currentTask)
                    && FavoritesStore.favoriteKeys[0]==="task|synthetic-worker"
                    && FavoritesService.isFavoriteKey("app|fixture-sentinel"),
                    "shared favorite identity and unrelated key preservation")) return;
                detail.host.toggleTaskMetricFavorite(view.currentTask,"cpu");
                if (!smoke.check(detail.host.isTaskMetricFavorite(view.currentTask,"cpu")
                    && FavoritesStore.favoriteTaskMetricKeys[0]==="taskmetric|synthetic-worker|cpu",
                    "shared metric favorite identity")) return;
                detail.host.toggleTaskMetricFavorite(view.currentTask,"cpu");
                if (!smoke.check(!detail.host.isTaskMetricFavorite(view.currentTask,"cpu")
                    && FavoritesStore.favoriteTaskMetricKeys.length===0,
                    "metric favorite removal")) return;
                view.toggleTaskFavorite(view.currentTask);
                if (!smoke.check(!view.isTaskFavorite(view.currentTask)
                    && FavoritesStore.favoriteKeys.length===1
                    && FavoritesService.isFavoriteKey("app|fixture-sentinel"),
                    "process favorite removal preserves other membership")) return;
                FavoritesService.toggleFavoriteKey("app|fixture-sentinel");
                // Exercise each real controller signal independently. The
                // donor's selective repaint is the authority, not the old CPU++ path.
                const revisions = () => [detail.cpuCanvas.graphRevision,
                    detail.memCanvas.graphRevision];
                const delta = before => JSON.stringify(revisions().map((n,i)=>n-before[i]));
                // COMBI has no local revision counter: shared history revision
                // drives its points. Its existing scroll state witnesses reset
                // and append behavior without instrumenting the renderer.
                const combi = detail.combiScoreCanvas;
                combi.resetGraphScroll();
                combi.graphScrollOffset=7;
                let before = revisions();
                fakeGraph.repaintCpuMem(true);
                if (!smoke.check(delta(before)==="[1,1]" && combi.graphScrollOffset===7,
                    "donor parity: CPU/MEM repaint excludes COMBI reset")) return;
                before = revisions();
                fakeGraph.repaintCpu(true);
                if (!smoke.check(delta(before)==="[1,0]" && combi.graphScrollOffset===7,
                    "donor parity: CPU-only repaint")) return;
                before = revisions();
                fakeGraph.repaintAll(true);
                if (!smoke.check(delta(before)==="[1,1]" && combi.graphScrollOffset===0,
                    "donor parity: full repaint resets COMBI")) return;
                combi.graphScrollOffset=7;
                before = revisions();
                fakeGraph.prepareCpuMemAppend();
                if (!smoke.check(delta(before)==="[1,1]" && combi.graphScrollOffset===7,
                    "donor parity: CPU/MEM append preparation excludes COMBI")) return;
                combi.resetGraphScroll();
                before = revisions();
                fakeGraph.prepareCombiAppend();
                if (!smoke.check(delta(before)==="[0,0]" && combi.graphScrollOffset>0,
                    "donor parity: COMBI append starts its own animation")) return;
                info.open=true;
                const initial=detail.cpuCanvas.graphRevision;
                fakeOwner.taskRows=[Object.assign({},fakeOwner.taskRows[0],{cpu:24,cpuInstant:37,mem:7})];
                fakeOwner.taskMiniCpuHistories=({"pid:3442":[5,12,37]});
                fakeOwner.taskMiniDisplayRevision++;
                if (!smoke.check(!fakeSession.accept({pid:3442,startTicks:967834,cpuPercent:99})
                    && fakeHistory.taskCpuHistory[fakeHistory.taskCpuHistory.length-1]!==37,
                    "general snapshot and wrong birth do not feed selected detail")) return;
                if (!smoke.check(fakeSession.accept({pid:3442,startTicks:967833,
                    cpuPercent:37,memPercent:7,rssKiB:23456,rssObserved:true,threadCount:29,swapKiB:65536,
                    ioRateBytes:1024,ioRateObserved:true,ageSeconds:55,ageObserved:true}),
                    "exact dedicated probe feeds shared history")) return;
                smoke.previousRevision=initial;
                smoke.phase=10;
                return;
            }
            if (smoke.phase===10) {
                const info=smoke.find(view,"cpuPlusProcessInformation");
                if (!smoke.check(info.open && info.visible,
                    "same birth identity refresh preserves information popup")) return;
                const mini=smoke.find(targets,"killTargetSharedMiniRenderer");
                if (!smoke.check(mini && mini.historyValues.length===3 && mini.historyValues[2]===37
                    && mini.graphScrollOffset>0 && detail.cpuCanvas.graphScrollOffset>0,
                    "same-length mini snapshot and main graph both animate after publication")) return;
                const viewport=smoke.find(view,"cpuPlusKillInstrumentViewport");
                const footer=smoke.find(view,"cpuPlusQuickControlFooter");
                const footerY=footer.mapToItem(view,0,0).y;
                if (!smoke.check(!viewport.interactive && viewport.contentHeight===viewport.height
                        && footer.visible && detail.limitSlider.visible
                        && footer.mapToItem(view,0,footer.height).y<=viewport.mapToItem(view,0,viewport.height).y,
                        "fixed quick controls within non-scrolling viewport")) return;
                // Select through the actual metric card signal, verify the
                // extra renderer mounts and that quick controls do not move.
                for (const [metric,card,expected] of [["rss","rss",23456/1024],["threads","threads",29],["io","io",1024/1048576],["age","uptime",55/60],["swap","swap",64]]) {
                    const toggle=smoke.find(view,"taskMetricToggle-"+card);
                    if (!smoke.check(toggle && toggle.enabled,"metric toggle "+card)) return;
                    toggle.clicked(null);
                    const extra=smoke.find(view,"cpuPlusDetailGraph-"+metric);
                    if (!smoke.check(view.selectedGraphKeys.length<=2 && extra
                        && extra.historyValues.length===1
                        && Math.abs(extra.historyValues[0]-expected)<0.00001
                        && extra.historyLimit===132 && extra.scrollDuration===920
                        && Math.abs(footer.mapToItem(view,0,0).y-footerY)<1,
                        "selected observed graph "+metric)) return;
                }
                view.selectedGraphKeys=["cpu","mem"];
                if (!smoke.check(!smoke.find(view,"cpuPlusDetailGraph-rss")
                    && !smoke.find(view,"cpuPlusDetailGraph-threads")
                    && !smoke.find(view,"cpuPlusDetailGraph-io")
                    && !smoke.find(view,"cpuPlusDetailGraph-age")
                    && !smoke.find(view,"cpuPlusDetailGraph-swap"),
                    "unselected extra graph renderers released")) return;
                smoke.previousMiniOffset=mini.graphScrollOffset;
                smoke.previousCpuOffset=detail.cpuCanvas.graphScrollOffset;
                // Test-only long scope injection. The actual hosts retain their
                // owner-projected scope bindings; no real process or command runs.
                info.scopeText = Array(100).fill("SYNTHETIC SCOPE / CHILD PID 3442").join("\n");
                smoke.phase=15;
                return;
            }
            if (smoke.phase===15) {
                const mini=smoke.find(targets,"killTargetSharedMiniRenderer");
                if (!smoke.check(mini && mini.graphScrollOffset<smoke.previousMiniOffset
                    && detail.cpuCanvas.graphScrollOffset<smoke.previousCpuOffset,
                    "mini and large graph offsets advance across frames")) return;
                const info=smoke.find(view,"cpuPlusProcessInformation");
                const scope=smoke.find(info,"processInformationScopeScroll");
                const args=smoke.find(info,"processInformationArgumentsScroll");
                const grow=smoke.find(info,"processInformationGrow");
                const shrink=smoke.find(info,"processInformationShrink");
                const command=smoke.find(info,"processInformationCommandFrame");
                if (!smoke.check(scope && args && grow && shrink && command
                    && info.sizeLevel===0 && grow.available && !shrink.available
                    && scope.height>0 && args.height>0
                    && scope.contentHeight>scope.height && args.contentHeight>args.height,
                    "compact level has two bounded independent scroll bodies")) return;
                const before=command.y;
                scope.contentY=12;
                if (!smoke.check(scope.contentY===12 && args.contentY===0 && command.y===before,
                    "scope scrolling does not move command box")) return;
                args.contentY=15;
                if (!smoke.check(scope.contentY===12 && args.contentY===15 && command.y===before,
                    "command scrolling does not move scope or its own box")) return;
                smoke.previousInfoHeight=info.height;
                smoke.previousInfoY=info.y;
                smoke.previousScopeHeight=scope.height;
                smoke.previousArgumentsHeight=args.height;
                grow.resizeRequested(1);
                smoke.phase=16;
                return;
            }
            if (smoke.phase===16) {
                const info=smoke.find(view,"cpuPlusProcessInformation");
                const scope=smoke.find(info,"processInformationScopeScroll");
                const args=smoke.find(info,"processInformationArgumentsScroll");
                const grow=smoke.find(info,"processInformationGrow");
                if (!smoke.check(info.sizeLevel===1 && info.height>smoke.previousInfoHeight
                    && info.y < smoke.previousInfoY && info.y===info.expandedTop
                    && scope.height>=smoke.previousScopeHeight && args.height>=smoke.previousArgumentsHeight,
                    "upper level moves above state divider and enlarges both bodies")) return;
                smoke.previousInfoHeight=info.height;
                smoke.previousInfoY=info.y;
                smoke.previousScopeHeight=scope.height;
                smoke.previousArgumentsHeight=args.height;
                grow.resizeRequested(1);
                smoke.phase=17;
                return;
            }
            if (smoke.phase===17) {
                const info=smoke.find(view,"cpuPlusProcessInformation");
                const scope=smoke.find(info,"processInformationScopeScroll");
                const args=smoke.find(info,"processInformationArgumentsScroll");
                const grow=smoke.find(info,"processInformationGrow");
                const shrink=smoke.find(info,"processInformationShrink");
                if (!smoke.check(info.sizeLevel===2 && !grow.available && shrink.available
                    && info.y===info.fullTop && info.y < smoke.previousInfoY
                    && info.y < smoke.find(view,"cpuPlusProcessStateHeader").y
                    && Math.abs(info.height-info.maximumHeight)<1
                    && info.height>smoke.previousInfoHeight
                    && scope.height>=smoke.previousScopeHeight && args.height>=smoke.previousArgumentsHeight,
                    "full usable bay with independently grown section bodies")) return;
                info.resizeBy(1);
                if (!smoke.check(info.sizeLevel===2,"maximum step clamps")) return;
                shrink.resizeRequested(-1);
                shrink.resizeRequested(-1);
                if (!smoke.check(info.sizeLevel===0 && info.y===info.compactTop,"shrink restores compact position")) return;
                info.open=false;
                if (!smoke.check(detail.cpuCanvas.graphRevision>smoke.previousRevision,
                    "new owner sample repaints shared detail")) return;
                const observed=detail.presentationState.taskCpuHistory;
                if (!smoke.check(observed[observed.length-1]===37,
                    "detail graph reads instantaneous CPU, not lifetime ps average")) return;
                const revision=detail.cpuCanvas.graphRevision;
                view.selectTarget(view.currentTask);
                if (!smoke.check(detail.cpuCanvas.graphRevision===revision,
                    "hover same target does not reset graph")) return;
                const search=smoke.find(view,"cpuPlusKillSearch");
                search.text="not-present";
                const cursor=smoke.find(view,"cpuPlusKillAnimatedCursor");
                if (!smoke.check(cursor.typingRecently && cursor.cursorStarsVisible
                    && cursor.trailingStarPhase===0,
                    "text change resets original animated cursor phase")) return;
                smoke.phase=11;
                return;
            }
            if (smoke.phase===11) {
                if (!smoke.check(targets.count===0 && !view.exactTargetAvailable
                    && !view.prepareAction("end"),
                    "search hides selected target and locks actuation")) return;
                smoke.find(view,"cpuPlusKillSearch").text="synthetic";
                view.setKillViewMode(view.killViewHunter);
                view.setHunterVisibilityMode(view.hunterVisibilityAll);
                // view requests are serialized, so explicitly switch after first settles
                smoke.phase=12;
                return;
            }
            if (smoke.phase===12) {
                if (view.modelBlank) return;
                if (view.killViewMode!==view.killViewHunter) {
                    view.setKillViewMode(view.killViewHunter); return;
                }
                if (view.hunterVisibilityMode!==view.hunterVisibilityAll) {
                    view.setHunterVisibilityMode(view.hunterVisibilityAll); return;
                }
                if (!smoke.check(targets.count===1
                    && view.hunterMetricMode===view.hunterMetricCombined,
                    "shared Hunter / COMBI / ALL filters")) return;
                const different={pid:9999,comm:"other",cpuInstant:42,rss:1048576,ioRate:0};
                if (!smoke.check(view.taskRowMetric(different).indexOf("42.0%")>=0
                    && view.taskRowMetric(different).indexOf("1024 MiB")>=0
                    && view.taskRowMetric(different)!==view.taskRowMetric(view.currentTask),
                    "Hunter row label comes from that row, not selected detail")) return;
                view.setHunterVisibilityMode(view.hunterVisibilityTargets);
                smoke.phase=13;
                return;
            }
            if (smoke.phase===13) {
                if (view.modelBlank) return;
                if (!smoke.check(targets.count===0 && !view.exactTargetAvailable
                    && !view.prepareAction("end"),
                    "protected row excluded by TARGETS and not actionable")) return;
                view.setHunterVisibilityMode(view.hunterVisibilityProtected);
                smoke.phase=14;
                return;
            }
            if (smoke.phase===14) {
                if (view.modelBlank) return;
                if (!smoke.check(targets.count===1,"PROTECTED filter uses owner policy")) return;
                smoke.priorInstrumentY=smoke.find(view,"cpuPlusKillInstrumentViewport").contentY;
                smoke.priorReviewGeometry=smoke.instrumentGeometry(view);
                if (!smoke.check(view.prepareAction("end")
                    && fakeGate.preparations===1
                    && fakeGate.confirmations===0
                    && view.hasOwnedPending
                    && smoke.find(view,"cpuPlusProcessReviewWarning").text.indexOf("WARNING // PROTECTED PROCESS")>=0
                    && smoke.find(view,"cpuPlusProcessReviewWarning").text.indexOf("SYNTHETIC SESSION-CRITICAL PROCESS")>=0,
                    "prepare protected review with risk warning, without execution"))
                    return;
                smoke.phase=24;
                return;
            }
            if (smoke.phase===24) {
                const panel=smoke.find(view,"cpuPlusRightReviewPanel");
                const right=smoke.find(view,"cpuPlusProcessReservedBay");
                const cancel=smoke.find(view,"cpuPlusSingleCancel");
                const confirm=smoke.find(view,"cpuPlusSingleConfirm");
                if (!smoke.check(panel.visible && panel.parent===right && panel.y===5
                    && detail.visible && confirm.available && cancel.available && cancel.normalFace
                    && Qt.colorEqual(cancel.idleForegroundColor,"#DCF3FA")
                    && Qt.colorEqual(cancel.hoverFillColor,"#F2BE4E")
                    && Math.abs(panel.height-cancel.mapToItem(panel,0,cancel.height).y-5)<1
                    && smoke.find(view,"cpuPlusKillInstrumentViewport").contentY===smoke.priorInstrumentY
                    && JSON.stringify(smoke.instrumentGeometry(view))===JSON.stringify(smoke.priorReviewGeometry),
                    "single review top aligned, ends at cancel and leaves resource viewport unchanged")) return;
                cancel.leftClicked(null);
                smoke.phase = 2;
                return;
            }
            if (smoke.phase === 2) {
                if (!smoke.check(fakeGate.pending===null
                    && fakeGate.cancels===1
                    && fakeGate.confirmations===0, "cancelled without execution"))
                    return;
                if (!smoke.check(view.prepareAction("freeze")
                    && view.hasOwnedPending, "freeze prepared")) return;
                smoke.find(view,"cpuPlusSingleConfirm").leftClicked(null);
                smoke.phase = 3;
                return;
            }
            if (smoke.phase === 3) {
                if (!smoke.check(fakeGate.confirmations===1
                    && fakeGate.pending===null
                    && !view.hasOwnedPending, "confirm controls only"))
                    return;
                if (!smoke.check(view.prepareAction("end") && view.hasOwnedPending,
                    "prepare before process removal")) return;
                smoke.lastRow = fakeOwner.taskRows[0];
                const pendingInfo=smoke.find(view,"cpuPlusProcessInformation");
                pendingInfo.open=true;
                if (!smoke.check(!pendingInfo.open && !pendingInfo.visible,
                    "information cannot obscure pending confirmation")) return;
                fakeOwner.taskRows = [];
                smoke.phase = 4;
                return;
            }
            if (smoke.phase===20) {
                const panel=smoke.find(view,"cpuPlusRightReviewPanel");
                const right=smoke.find(view,"cpuPlusProcessReservedBay");
                const list=smoke.find(view,"cpuPlusBulkReview");
                const cancel=smoke.find(view,"cpuPlusBulkCancel");
                const confirm=smoke.find(view,"cpuPlusBulkConfirm");
                const count=smoke.find(view,"cpuPlusCapturedTargetNumber");
                if (!smoke.check(panel.visible && panel.parent===right && panel.y===5
                    && list.count===60 && list.contentHeight>list.height
                    && count.text==="60" && Qt.colorEqual(count.color,"#C74EC7")
                    && confirm.available && cancel.available
                    && Math.abs(panel.height-cancel.mapToItem(panel,0,cancel.height).y-5)<1
                    && fakeOwner.bulkConfirmed===0,
                    "long captured list scrolls independently of fixed confirm/cancel footer")) return;
                smoke.priorCancelY=cancel.mapToItem(right,0,0).y;
                list.contentY=100;
                smoke.phase=21;
                return;
            }
            if (smoke.phase===21) {
                const cancel=smoke.find(view,"cpuPlusBulkCancel");
                const right=smoke.find(view,"cpuPlusProcessReservedBay");
                if (!smoke.check(Math.abs(cancel.mapToItem(right,0,0).y-smoke.priorCancelY)<0.1
                    && smoke.find(view,"cpuPlusBulkReview").contentY>0,
                    "captured list scroll does not move footer")) return;
                cancel.leftClicked(null);
                if (!smoke.check(fakeOwner.bulkCancelled===1 && !view.hasBulkReview
                    && fakeOwner.bulkConfirmed===0,"bulk cancellation sends no command")) return;
                if (!smoke.check(view.requestKillMice(),"prepare second captured review")) return;
                smoke.find(view,"cpuPlusBulkConfirm").leftClicked(null);
                if (!smoke.check(fakeOwner.bulkConfirmed===1 && view.bulkOperation
                    && !view.hasBulkReview && !view.confirmBulk(),
                    "bulk review consumed once, progress remains owner-owned")) return;
                console.log("CPU_KILL_NATIVE_PASS");
                smoke.done=true;
                Qt.quit();
                return;
            }
            if (!smoke.check(!smoke.find(view,"cpuPlusProcessInformation").open
                && !smoke.find(view,"cpuPlusProcessInformation").visible,
                "disappearing process closes information")) return;
            if (!smoke.check(!view.currentTask && !view.exactTargetAvailable
                && !view.prepareAction("end") && !view.hasOwnedPending
                && fakeGate.pending===null && fakeGate.cancels===2
                && fakeGate.confirmations===1, "stale selection refusal and owned review cancelled"))
                return;
            fakeOwner.taskRows = [smoke.lastRow];
            if (!smoke.check(view.requestKillHogs() && view.hasBulkReview
                    && fakeOwner.bulkConfirmed===0
                    && fakeOwner.cpuBulkReview.metric===view.hunterMetricMode,
                    "bulk click prepares only, uses recipient metric")) return;
            smoke.phase=20;
            return;
        }
    }

    Component.onCompleted: if (!armed) Qt.quit()
}
