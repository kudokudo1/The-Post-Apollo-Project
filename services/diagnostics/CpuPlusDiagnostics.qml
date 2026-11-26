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
    property string compareBeforeId: ""
    property string compareAfterId: ""
    function selectComparison(side, reportId) {
        if (archiveBusy || archiveStatus !== "READY") return false;
        const row = archiveRows.find(item => item.id === reportId);
        if (!row || row.status !== "COMPLETE") return false;
        if (side === "before") compareBeforeId = row.id;
        else if (side === "after") compareAfterId = row.id;
        else return false;
        return true;
    }
    readonly property var archiveRows: archive.rows
    readonly property string archiveStatus: archive.status
    readonly property bool archiveBusy: archive.busy
    DiagnosticReportArchive { id: archive }

    function loadHistory() {
        if (busy) return false;
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

    function requestConfigured(configuration) {
        if (!configuration || typeof configuration !== "object") return false;
        const descriptor=Object.getOwnPropertyDescriptor(configuration,"kind");
        if (!descriptor || !Object.prototype.hasOwnProperty.call(descriptor,"value")) return false;
        return request(descriptor.value, configuration);
    }

    function request(job, configuration) {
        if (busy || faulted || worker.running || archive.busy) return false;
        const configured = configuration !== undefined;
        const plan = configured
            ? Calibration.observerLaunchPlan(configuration, path => Quickshell.shellPath(path), Quickshell.dataDir) : null;
        if (configured && (!plan || plan.config.kind !== job)) return false;
        const args = plan ? plan.args : Policy.argumentsFor(job, path => Quickshell.shellPath(path), Quickshell.dataDir);
        if (!args) return false;
        activeCalibration = plan ? JSON.stringify(plan.config) : "";
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
        busy = true;
        if (job === "appcontrol") recordMode();
        feedback = "RUNNING // " + job.toUpperCase();
        deadline.restart();
        worker.exec(args);
        return true;
    }

    function cancel() {
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

    function selectExactReport(job, reportId) {
        if (!reportFor(job, reportId)) return false;
        selectedReport = job;
        selectedArchiveId = reports[job] && reports[job].id === reportId ? "" : reportId;
        memoryMenuIndex = 4;
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
        busy = false;
        captureFinished(kind, captureId);
    }

    function finish() {
        if (!busy || !received || !exited) return;
        deadline.stop();
        if (kind === "appcontrol" && !cancelled && exitOk && output.length <= maximumReport)
            output = Policy.combineAppControl(output, modeRecords, openingRecords, diagnosticOverflow, killWorkRecords, workRecords) || "";
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
                                owner.output.length <= owner.maximumReport ? owner.output : "");
            worker.running = false;
        }
    }

    Process {
        id: worker
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
