pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import "CpuPlusDiagnosticsPolicy.js" as Policy
import "DiagnosticCalibration.js" as Calibration

// Session owner, independent of the demand-loaded CPU++ pane.
// No process or timer runs until an explicit button request.
Scope {
    id: owner
    // Session presentation state; never stores an armed capacity request.
    property int memoryMenuIndex: 0
    property string selectedReport: "memory"
    // Opaque session-scoped capture identity; never used as authorization.
    readonly property string sessionTag: Date.now().toString(36) + "-" + (Math.random().toString(36).slice(2) || "0") + "-" + (Math.random().toString(36).slice(2) || "0")
    property int captureSequence: 0
    property string captureId: ""
    signal captureFinished(string job, string reportId)
    property string selectedArchiveId: ""
    property bool pendingReportView: false
    property string compareBeforeId: ""
    property string compareAfterId: ""
    function selectComparison(side, reportId) {
        if (archiveBusy || archiveStatus !== "READY") return false;
        const row = archiveRows.find(item => item.id === reportId);
        if (!row || row.status !== "COMPLETE" || ["workflow","stall","hostcpu","gpu","diskio","swapio","netio"].includes(row.kind)) return false;
        if (side === "before") compareBeforeId = row.id;
        else if (side === "after") compareAfterId = row.id;
        else return false;
        return true;
    }
    readonly property var archiveRows: archive.rows
    readonly property string archiveStatus: archive.status
    readonly property bool archiveBusy: archive.busy
    DiagnosticReportArchive { id: archive }
    // One durable catalog owner across demand-loaded diagnostic views.
    DiagnosticWorkflowStore {
        id: workflowStore
        onCompleted: function(outcome) {
            owner.workshopPresetFeedback = outcome==="READY" ?
                (owner.pendingCatalogEdit ? "SAVED // LOCAL WORKFLOW LIBRARY" : "READY // LOCAL WORKFLOW LIBRARY") :
                outcome==="CONFLICT" ? "CONFLICT // RELOAD REQUIRED" : "NOT CONFIRMED // RELOAD REQUIRED";
            const wasEdit=owner.pendingCatalogEdit;
            owner.pendingCatalogEdit=false;
            // Publish only after the store has qualified its terminal receipt.
            owner.workflowCatalogCompleted(outcome,wasEdit,workflowStore.document);
        }
    }
    signal workflowCatalogCompleted(string outcome, bool wasEdit, var confirmedDocument)
    property bool pendingCatalogEdit: false
    readonly property var workflowRows: workflowStore.rows
    readonly property var workflowFavorites: workflowStore.favorites
    readonly property string workflowCatalogStatus: workflowStore.status
    readonly property bool workflowCatalogReady: workflowStore.ready
    readonly property bool workflowCatalogBusy: workflowStore.busy
    function loadWorkflowCatalog() {
        if (busy || archiveBusy || faulted || setActive || workflowStore.busy) return false;
        return workflowStore.load();
    }
    function setWorkflowFavorite(id, value) {
        if (workshopPresetLocked || !workflowStore.ready) return false;
        return editWorkflowCatalog({action:"favorite",id:id,favorite:value});
    }
    function runFavoriteWorkflow(id) {
        if (workshopPresetLocked || !workflowStore.ready) return false;
        const row=workflowStore.favorites.find(r=>r.id===id);
        if (!row) return false;
        if (row.execution==="fixed") return request(row.kind);
        if (row.execution==="configured") return requestWorkshopCapture(row.plan);
        return false;
    }

    function loadHistory() {
        if (busy || setActive || workflowCatalogBusy) return false;
        return archive.invoke({action: "list"});
    }
    function selectLatest(job) {
        if (!Policy.validKind(job)) return;
        selectedArchiveId = "";
        selectedReport = job;
    }
    property bool busy: false
    property bool faulted: false
    property string kind: ""
    property string feedback: "READY // ON DEMAND"
    property var reports: ({})
    property bool received: false
    property bool exited: false
    property bool exitOk: false
    property int exitCode: -1
    property bool cancelled: false
    property string output: ""
    readonly property int maximumReport: 65536
    property string appControlMode: "unavailable"
    readonly property bool appControlCaptureActive: busy && kind === "appcontrol" && !cancelled && !exited
    property var openingRecords: []
    property var killWorkRecords: []
    property var workRecords: []
    property var modeRecords: []
    property bool diagnosticOverflow: false
    property bool workflowStallRequested: false
    readonly property bool stallCaptureActive: busy && (kind === "stall" || (kind === "workflow" && workflowStallRequested)) && !cancelled && !exited
    property var stallTicks: []
    property bool stallOverflow: false

    function recordStallTick(timestampMs) {
        if (!stallCaptureActive || stallOverflow) return;
        // Do not publish a reactive model or copy the history every tick.
        if (!Number.isSafeInteger(timestampMs) || timestampMs<=0 || stallTicks.length>=1500
                || (stallTicks.length && timestampMs<=stallTicks[stallTicks.length-1])) {
            stallOverflow=true;
            return;
        }
        stallTicks.push(timestampMs);
    }
    onAppControlModeChanged: {
        if (appControlCaptureActive) recordMode();
    }
    function recordMode() {
        if (modeRecords.length >= 128) { diagnosticOverflow = true; return; }
        modeRecords.push({tsMs: Date.now(), mode: appControlMode});
    }
    function recordOpening(stage, sequence, elapsedMs, timestampMs) {
        if (!appControlCaptureActive) return;
        if (openingRecords.length >= 140) { diagnosticOverflow = true; return; }
        openingRecords.push({stage:stage, sequence:sequence, elapsedMs:elapsedMs, tsMs:timestampMs});
    }

    function recordKillWork(stage, elapsedMs, timestampMs) {
        if (!appControlCaptureActive) return;
        if (killWorkRecords.length >= 512) { diagnosticOverflow = true; return; }
        killWorkRecords.push({stage:stage, elapsedMs:elapsedMs, tsMs:timestampMs});
    }

    function recordWork(stage, elapsedMs, timestampMs) {
        if (!appControlCaptureActive) return;
        if (workRecords.length >= 256) { diagnosticOverflow = true; return; }
        workRecords.push({stage:stage, elapsedMs:elapsedMs, tsMs:timestampMs, mode:appControlMode});
    }

    // Detached serialization freezes the submitted calibration for completion validation.
    property string activeCalibration: ""
    property var storageProgress: null
    property bool storageProgressFault: false
    property double storageRequestWallMs: 0
    property var activeStorageConfig: null
    function acceptStorageProgress(line) {
        if (!busy || cancelled || !activeStorageConfig || storageProgressFault || !line.startsWith("STORAGE_PROGRESS ")) return;
        const p=Policy.storageLiveProgress(line,activeStorageConfig,storageProgress,storageRequestWallMs,Date.now());
        if (!p) { storageProgressFault=true; storageProgress=null; return; }
        storageProgress=p;
    }

    // Session-owned draft, not authorization. No persistence or auto-start.
    property var workshopDraft: ({durationSeconds:30, selected:["threads","memory"],
        threadIntervalMs:1000, memoryIntervalMs:10000, censusIntervalMs:10000, topCount:4, stallThresholdMs:350,
        hostCpuIntervalMs:1000, gpuIntervalMs:1000, diskIoIntervalMs:1000, swapIoIntervalMs:1000, netIoIntervalMs:1000,
        storageCadenceExplicit:false, storageSampleSeconds:1, storageReportSeconds:10})
    property var memoryWorkshopDraft: ({durationSeconds:30, selected:["memory"], memoryIntervalMs:10000})
    // CPU has independent session calibration; switching SYSTEM targets never
    // overwrites the general workshop or starts a capture.
    property var cpuWorkshopDraft: ({durationSeconds:30, selected:["census"], hostCpuIntervalMs:1000,
        threadIntervalMs:1000, memoryIntervalMs:10000, censusIntervalMs:10000, topCount:4, stallThresholdMs:350,
        storageCadenceExplicit:false, storageSampleSeconds:1, storageReportSeconds:10})
    property var gpuWorkshopDraft: ({durationSeconds:10, selected:["gpu"], gpuIntervalMs:1000,
        threadIntervalMs:1000, memoryIntervalMs:10000, censusIntervalMs:10000, topCount:4, stallThresholdMs:350,
        hostCpuIntervalMs:1000, storageCadenceExplicit:false, storageSampleSeconds:1, storageReportSeconds:10})
    property var storageWorkshopDraft: ({durationSeconds:30, selected:["storage"],
        threadIntervalMs:1000, memoryIntervalMs:10000, censusIntervalMs:10000, topCount:4, stallThresholdMs:350,
        hostCpuIntervalMs:1000, gpuIntervalMs:1000, diskIoIntervalMs:1000, storageCadenceExplicit:true, storageSampleSeconds:1, storageReportSeconds:10})
    property var swapWorkshopDraft: ({durationSeconds:10, selected:["swapio"], swapIoIntervalMs:1000})
    property var netWorkshopDraft: ({durationSeconds:10, selected:["netio"], netIoIntervalMs:1000})
    function draftForSubject(subject) {
        return subject==="CPU" ? cpuWorkshopDraft : subject==="GPU" ? gpuWorkshopDraft
            : subject==="STORAGE" ? storageWorkshopDraft : subject==="SWAP" ? swapWorkshopDraft : subject==="NETWORK" ? netWorkshopDraft : subject==="MEMORY" ? memoryWorkshopDraft : workshopDraft;
    }
    function setDraftForSubject(subject, draft) {
        if (workshopPresetLocked || !draft || !Array.isArray(draft.selected)
                || !["CPU","GPU","STORAGE","SWAP","NETWORK","MEMORY","SYSTEM","ALL"].includes(subject)
                || !draft.selected.every(k=>Calibration.workshopSubjectKinds(subject).includes(k))) return false;
        if (subject==="CPU") cpuWorkshopDraft=draft;
        else if (subject==="GPU") gpuWorkshopDraft=draft;
        else if (subject==="STORAGE") storageWorkshopDraft=draft;
        else if (subject==="SWAP") swapWorkshopDraft=draft;
        else if (subject==="NETWORK") netWorkshopDraft=draft;
        else if (subject==="MEMORY") memoryWorkshopDraft=draft;
        else workshopDraft=draft;
        return true;
    }
    // Library and QUICK are projections of the same confirmed catalog.
    readonly property var workshopPresets: workflowStore.rows
    property string workshopPresetFeedback: "NOT LOADED // LOCAL WORKFLOW LIBRARY"
    readonly property bool workshopPresetLocked: busy || archiveBusy || faulted || setActive || workflowCatalogBusy
    function editWorkflowCatalog(change) {
        if (workshopPresetLocked || !workflowStore.ready) return false;
        if (!workflowStore.edit(change)) {
            workshopPresetFeedback="INVALID EDIT // CHECK NAME OR CALIBRATION";
            return false;
        }
        pendingCatalogEdit=true;
        workshopPresetFeedback="SAVING // WAIT FOR CONFIRMATION";
        return true;
    }
    function saveWorkshopPreset(name, subject = "ALL") {
        if (workshopPresetLocked || !workflowStore.ready) return false;
        const plan=Calibration.workshopPlanFromDraft(draftForSubject(subject));
        if (!Calibration.workshopPlanMatchesSubject(plan,subject)) {
            workshopPresetFeedback="INVALID CALIBRATION";
            return false;
        }
        return editWorkflowCatalog({action:"create",name:name,plan:plan,favorite:false});
    }
    function loadWorkshopPreset(name, subject = "ALL") {
        if (workshopPresetLocked || !workflowStore.ready) return false;
        const p=workshopPresets.find(row=>row.name===name);
        const next=p && p.execution==="configured" && Calibration.workshopDraftFromPlan(p.plan);
        if (!next) {workshopPresetFeedback="PRESET UNAVAILABLE";return false;}
        if (!Calibration.workshopPlanMatchesSubject(p.plan,subject) || !setDraftForSubject(subject,next)) {
            workshopPresetFeedback="WORKFLOW OUTSIDE SUBJECT"; return false;
        }
        workshopPresetFeedback="LOADED // PREPARE REQUIRED";
        return true;
    }
    function removeWorkshopPreset(name) {
        if (workshopPresetLocked || !workflowStore.ready) return false;
        const row=workshopPresets.find(r=>r.name===name);
        return !!row && editWorkflowCatalog({action:"remove",id:row.id});
    }
    // Session-only mixer. The owner, not the view, owns an explicit ordered run.
    property var workshopQueue: []
    property var workshopSets: []
    property bool setActive: false
    property bool setDispatching: false
    property bool setStopRequested: false
    property string setFeedback: "QUEUE // READY"
    property var setRunItems: []
    property var setRunResults: []
    property int setRunIndex: 0
    property string setCurrentId: ""
    property string setCurrentKind: ""
    readonly property var queuePreview: Calibration.validatedWorkshopSet(workshopQueue)
    function queueWorkshop(name) {
        if (workshopPresetLocked || !workflowStore.ready) return false;
        const p=workshopPresets.find(x=>x.name===name);
        // Queue custody remains detached calibration snapshots, not catalog IDs.
        const next=p && p.execution==="configured" &&
            Calibration.validatedWorkshopSet(workshopQueue.concat([{name:p.name,plan:p.plan}]));
        if(!next){setFeedback="LIMIT // 4 STEPS / 240s";return false;}
        workshopQueue=next.items;setFeedback="QUEUED // "+name;return true;
    }
    function moveWorkshopQueue(index,delta) {
        if(workshopPresetLocked||!Number.isInteger(index)||![-1,1].includes(delta)
            ||index<0||index>=workshopQueue.length||index+delta<0||index+delta>=workshopQueue.length)return false;
        const rows=workshopQueue.slice(),row=rows.splice(index,1)[0];
        rows.splice(index+delta,0,row);workshopQueue=rows;return true;
    }
    function removeWorkshopQueue(index) {
        if(workshopPresetLocked||!Number.isInteger(index)||index<0||index>=workshopQueue.length)return false;
        workshopQueue=workshopQueue.filter((_,i)=>i!==index);return true;
    }
    function clearWorkshopQueue() {
        if(workshopPresetLocked)return false;
        workshopQueue=[];setFeedback="QUEUE CLEARED";return true;
    }
    function saveWorkshopSet(name) {
        if(workshopPresetLocked||!queuePreview||typeof name!=="string"
            ||!/^[A-Za-z0-9][A-Za-z0-9 _-]{0,31}$/.test(name)||name.trim()!==name
            ||workshopSets.length>=12||workshopSets.some(x=>x.name.toLowerCase()===name.toLowerCase()))return false;
        workshopSets=workshopSets.concat([{name:name,items:queuePreview.items}]);
        setFeedback="SET SAVED // SESSION ONLY";return true;
    }
    function loadWorkshopSet(name) {
        if(workshopPresetLocked)return false;
        const row=workshopSets.find(x=>x.name===name),next=row&&Calibration.validatedWorkshopSet(row.items);
        if(!next)return false;
        workshopQueue=next.items;setFeedback="SET LOADED // RUN REQUIRED";return true;
    }
    function removeWorkshopSet(name) {
        if(workshopPresetLocked||!workshopSets.some(x=>x.name===name))return false;
        workshopSets=workshopSets.filter(x=>x.name!==name);return true;
    }
    function startWorkshopSet(exact) {
        if(workshopPresetLocked||!queuePreview||exact!==JSON.stringify(queuePreview.items))return false;
        const frozen=Calibration.validatedWorkshopSet(JSON.parse(exact));
        if(!frozen)return false;
        setRunItems=frozen.items;setRunResults=[];setRunIndex=0;setCurrentId="";setCurrentKind="";
        setStopRequested=false;setActive=true;
        dispatchSetStep();return true;
    }
    function finishSet(status) {
        setActive=false;setDispatching=false;setCurrentId="";setCurrentKind="";
        setFeedback=status+" // "+setRunResults.filter(x=>x.status==="COMPLETE").length+"/"+setRunItems.length+" COMPLETE";
    }
    function dispatchSetStep() {
        if(!setActive||busy||archiveBusy)return;
        if(setCurrentId!==""){
            // The preceding capture must have an exact successful report AND
            // a confirmed archive receipt before another child can launch.
            const row=archiveStatus==="READY"&&archiveRows.find(x=>x.id===setCurrentId&&x.kind===setCurrentKind);
            const status=row&&["COMPLETE","CANCELLED"].includes(row.status)?row.status:"NOT VERIFIED";
            setRunResults=setRunResults.concat([{name:setRunItems[setRunIndex].name,id:setCurrentId,
                kind:setCurrentKind,status:status}]);
            setCurrentId="";setCurrentKind="";
            if(setStopRequested){finishSet("SET CANCELLED");return;}
            if(status!=="COMPLETE"){finishSet("SET STOPPED");return;}
            setRunIndex++;
        }
        if(setStopRequested){finishSet("SET CANCELLED");return;}
        if(faulted||archive.faulted){finishSet("SET NOT VERIFIED");return;}
        if(setRunIndex>=setRunItems.length){finishSet("SET COMPLETE");return;}
        const step=setRunItems[setRunIndex];
        setDispatching=true;
        let accepted=false;
        try {accepted=requestWorkshopCapture(step.plan);} finally {setDispatching=false;}
        if(!accepted){finishSet("SET LAUNCH REFUSED");return;}
        setCurrentId=captureId;setCurrentKind=kind;
        setFeedback="STEP "+(setRunIndex+1)+"/"+setRunItems.length+" // "+step.name;
    }
    // Archive owns its async completion; no polling or additional child.
    onArchiveBusyChanged: if(setActive&&!archiveBusy) Qt.callLater(dispatchSetStep)
    function stopWorkshopSet() {
        if(!setActive)return;
        setStopRequested=true;setFeedback="SET STOPPING";
        if(busy)cancel();
        else if(!archiveBusy)Qt.callLater(dispatchSetStep);
    }
    property string workshopRunId: ""
    property string workshopRunKind: ""
    property string workshopRunPlan: ""
    property double workshopStartedMs: 0
    property int workshopDurationSeconds: 0

    function requestWorkshopCapture(plan) {
        if (!plan || !Array.isArray(plan.instruments) || plan.instruments.length < 1) return false;
        const single = plan.instruments.length === 1;
        const job = single ? plan.instruments[0].kind : "workflow";
        const config = single ? Object.assign({},plan.instruments[0],{durationSeconds:plan.durationSeconds}) : plan;
        const frozen = JSON.stringify(plan);
        if (!(single ? requestConfigured(config) : requestWorkflow(config))) return false;
        workshopRunId = captureId;
        workshopRunKind = job;
        workshopRunPlan = frozen;
        workshopStartedMs = Date.now();
        workshopDurationSeconds = plan.durationSeconds;
        return true;
    }


    function requestConfigured(configuration) {
        if (!configuration || typeof configuration !== "object") return false;
        const descriptor=Object.getOwnPropertyDescriptor(configuration,"kind");
        if (!descriptor || !Object.prototype.hasOwnProperty.call(descriptor,"value")) return false;
        return request(descriptor.value, configuration);
    }

    function requestWorkflow(configuration) {
        if (configuration === undefined) return false;
        return request("workflow", configuration);
    }

    function request(job, configuration) {
        if (busy || faulted || worker.running || archive.busy || workflowCatalogBusy || (setActive && !setDispatching)) return false;
        const configured = configuration !== undefined;
        const plan = configured
            ? (job === "workflow"
                ? Calibration.workflowLaunchPlan(configuration, path => Quickshell.shellPath(path), Quickshell.dataDir)
                : Calibration.observerLaunchPlan(configuration, path => Quickshell.shellPath(path), Quickshell.dataDir)) : null;
        if (configured && (!plan || (job !== "workflow" && plan.config.kind !== job))) return false;
        const args = plan ? plan.args : Policy.argumentsFor(job, path => Quickshell.shellPath(path), Quickshell.dataDir);
        if (!args) return false;
        activeCalibration = plan ? JSON.stringify(job === "workflow" ? plan.plan : plan.config) : "";
        storageProgress=null;
        storageProgressFault=false;
        storageRequestWallMs=Date.now();
        activeStorageConfig=plan && job==="storage" ? plan.config : plan && job==="workflow"
            ? (()=>{const c=plan.plan.instruments.find(x=>x.kind==="storage");return c?Object.assign({},c,{durationSeconds:plan.plan.durationSeconds}):null;})() : null;
        kind = job;
        captureSequence += 1;
        captureId = sessionTag + "-" + captureSequence;
        selectLatest(job);
        received = false;
        exited = false;
        exitOk = false;
        exitCode = -1;
        cancelled = false;
        output = "";
        openingRecords = [];
        killWorkRecords = [];
        workRecords = [];
        modeRecords = [];
        diagnosticOverflow = false;
        stallTicks = [];
        stallOverflow = false;
        workflowStallRequested = job === "workflow" && !!plan && plan.plan.instruments.some(c=>c.kind==="stall");
        busy = true;
        if (job === "appcontrol") recordMode();
        feedback = "RUNNING // " + job.toUpperCase();
        deadline.restart();
        worker.exec(args);
        return true;
    }

    function cancel() {
        if (setActive) setStopRequested=true;
        if (!busy || cancelled) return;
        cancelled = true;
        feedback = "STOPPING DIAGNOSTIC // WAIT FOR EXIT";
        worker.running = false;
    }

    function reportFor(job, reportId) {
        if (!Policy.validKind(job) || typeof reportId !== "string" || !reportId)
            return null;
        const report = reports[job];
        if (report && report.id === reportId) return report;
        return archiveRows.find(row => row.kind === job && row.id === reportId) || null;
    }

    function selectExactReport(job, reportId, openReport = true) {
        if (!reportFor(job, reportId)) return false;
        selectedReport = job;
        selectedArchiveId = reports[job] && reports[job].id === reportId ? "" : reportId;
        if (openReport) {
            memoryMenuIndex = 4;
            pendingReportView = true;
        }
        return true;
    }

    function publishResult(status, summary, text) {
        const next = Object.assign({}, reports);
        next[kind] = {id: captureId, status: status, summary: summary,
                      text: text, finishedAt: new Date().toISOString()};
        reports = next;
        archive.invoke({action: "save", record: Object.assign({kind: kind}, next[kind])});
        feedback = status + " // " + kind.toUpperCase();
        output = "";
        activeCalibration = "";
        activeStorageConfig=null;
        busy = false;
        captureFinished(kind, captureId);
        if(setActive&&!archiveBusy)Qt.callLater(dispatchSetStep);
    }

    function finish() {
        if (!busy || !received || !exited) return;
        deadline.stop();
        if (kind === "appcontrol" && !cancelled && exitOk && output.length <= maximumReport)
            output = Policy.combineAppControl(output, modeRecords, openingRecords, diagnosticOverflow, killWorkRecords, workRecords) || "";
        if (kind === "stall") {
            const report = !cancelled && exitOk && activeCalibration && !stallOverflow
                ? Policy.combineStall(output, stallTicks, JSON.parse(activeCalibration)) : null;
            publishResult(cancelled ? "CANCELLED" : report ? "COMPLETE" : "NOT VERIFIED",
                report ? Policy.summarize("stall", report) : cancelled ? "CAPTURE STOPPED" : "STALL COVERAGE OR CLOCK NOT VERIFIED",
                report || "");
            stallTicks=[];
            return;
        }
        if (kind === "workflow") {
            const expected = activeCalibration ? JSON.parse(activeCalibration) : null;
            if (workflowStallRequested) output = Policy.attachWorkflowStall(output,expected,stallTicks,stallOverflow) || "";
            stallTicks=[];
            const evidence = expected && Policy.workflowEvidence(output, expected);
            const status = cancelled ? "CANCELLED" : exitOk && evidence && evidence.status === "COLLECTED" ? "COMPLETE" : "NOT VERIFIED";
            publishResult(status, evidence ? evidence.summary : (cancelled ? "CAPTURE STOPPED" : "NO VERIFIED WORKFLOW // EXIT " + exitCode),
                          evidence ? output : "");
            return;
        }
        const calibrationMatches = !activeCalibration ||
            Policy.configuredEvidence(kind, output, JSON.parse(activeCalibration)) !== null;
        const summary = !cancelled && exitOk && output.length <= maximumReport && calibrationMatches
            ? Policy.summarize(kind, output) : null;
        publishResult(cancelled ? "CANCELLED" : summary ? "COMPLETE" : "NOT VERIFIED",
                      summary || (cancelled ? "CAPTURE STOPPED" : "NO VERIFIED RESULT // EXIT " + exitCode),
                      output.length <= maximumReport ? output : "");
    }

    Timer {
        id: deadline
        interval: 155000
        repeat: false
        onTriggered: {
            if (!owner.busy) return;
            // Missing exit/stream notification: refuse another run rather than
            // accepting late output under a new request identity.
            owner.faulted = true;
            owner.publishResult("NOT VERIFIED", "RUNNER UNAVAILABLE // COMPLETION NOT OBSERVED",
                                owner.kind !== "workflow" && owner.kind !== "stall" && owner.output.length <= owner.maximumReport ? owner.output : "");
            worker.running = false;
        }
    }

    Process {
        id: worker
        stderr: SplitParser {
            onRead: data => owner.acceptStorageProgress(data)
        }
        stdout: StdioCollector {
            onStreamFinished: {
                if (!owner.busy) return;
                owner.output = this.text;
                owner.received = true;
                owner.finish();
            }
        }
        onExited: function(code, exitStatus) {
            if (!owner.busy) return;
            owner.exitCode = code;
            owner.exitOk = code === 0 && exitStatus === 0;
            owner.exited = true;
            owner.finish();
        }
    }
}
