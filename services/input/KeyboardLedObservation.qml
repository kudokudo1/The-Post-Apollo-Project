pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import qs.services.input
import "KeyboardLedPolicy.js" as Policy

// Opt-in LED BRIGHTNESS proxy, not Sway/XKB lock state. No key events,
// /dev/input, privileged access, Sway IPC changes or compositor writes.
Scope {
    id: ledMonitor

    readonly property string storagePath:
        Quickshell.dataDir + "/keyboard-led-observations-v1.json"
    property string storageState: "loading"
    property string storageError: ""
    property var document: Policy.initialDocument()
    property var pendingDocument: null
    property var queuedDocument: null
    readonly property var effectiveDocument:
        queuedDocument !== null ? queuedDocument
        : pendingDocument !== null ? pendingDocument : document
    readonly property bool monitoringEnabled: effectiveDocument.enabled
    readonly property bool canEdit:
        storageState === "ready" || storageState === "empty"
        || storageState === "saving"

    property bool sampling: false
    property bool sampleReturned: false
    property string probeError: ""
    property string sourceStatus: "not_checked"
    property string numStatus: "not_checked"
    property string capsStatus: "not_checked"
    property string candidateNum: "unknown"
    property string candidateCaps: "unknown"
    property int stableNum: 0
    property int stableCaps: 0
    property double lastSampleAtMs: 0
    property double nowMs: Date.now()
    readonly property string currentNum:
        numStatus === "observed" && stableNum >= 2
        ? candidateNum : "unknown"
    readonly property string currentCaps:
        capsStatus === "observed" && stableCaps >= 2
        ? candidateCaps : "unknown"
    readonly property bool fresh:
        monitoringEnabled && lastSampleAtMs > 0
        && nowMs >= lastSampleAtMs
        && nowMs - lastSampleAtMs <= 6000
    readonly property bool canCopyToStartup:
        fresh && currentNum !== "unknown" && currentCaps !== "unknown"
        && KeyboardLockSettings.canEdit
        && !KeyboardLockSettings.confirmRequired
    readonly property string savedNum: effectiveDocument.num.value
    readonly property string savedCaps: effectiveDocument.caps.value
    readonly property double savedNumAtMs: effectiveDocument.num.observedAtMs
    readonly property double savedCapsAtMs: effectiveDocument.caps.observedAtMs

    function beginWrite(next) {
        pendingDocument = next;
        storageState = "saving";
        storageError = "";
        observationsFile.setText(JSON.stringify(next, null, 2) + "\n");
    }
    function persist(next) {
        if (!canEdit || !Policy.validDocument(next))
            return false;
        if (pendingDocument !== null)
            queuedDocument = next;
        else
            beginWrite(next);
        return true;
    }
    function clearLive() {
        numStatus = "not_checked";
        capsStatus = "not_checked";
        sourceStatus = "not_checked";
        candidateNum = "unknown";
        candidateCaps = "unknown";
        stableNum = 0;
        stableCaps = 0;
        lastSampleAtMs = 0;
    }
    function setMonitoringEnabled(enabled) {
        if (!canEdit || typeof enabled !== "boolean")
            return false;
        const updated = Policy.withEnabled(effectiveDocument, enabled);
        if (!updated.ok)
            return false;
        if (!enabled)
            clearLive();
        return persist(updated.document);
    }
    function sampleOnce() {
        if (sampling)
            return false;
        sampling = true;
        sampleReturned = false;
        probeError = "";
        sampleProcess.exec([
            "python3", "-B", "-I",
            Quickshell.shellPath("services/input/KeyboardLedProbe.py"),
            "sample"
        ]);
        return true;
    }
    function parseLock(reply) {
        if (!reply || typeof reply !== "object"
                || !["observed", "absent", "unreadable", "conflict",
                     "too_many"].includes(reply.status))
            return {status:"unreadable", value:"unknown"};
        if (reply.status !== "observed")
            return {status:reply.status, value:"unknown"};
        if ((reply.value !== "on" && reply.value !== "off")
                || !Number.isInteger(reply.count)
                || reply.count < 1 || reply.count > 24)
            return {status:"unreadable", value:"unknown"};
        return {status:"observed", value:reply.value};
    }
    function recordStable(lock, value, atMs) {
        if (!monitoringEnabled || !canEdit || value === "unknown")
            return;
        const updated = Policy.withObserved(effectiveDocument, lock, value, atMs);
        if (updated.ok && updated.changed)
            persist(updated.document);
    }
    function receiveSample(raw) {
        sampleReturned = true;
        nowMs = Date.now();
        let reply;
        try { reply = JSON.parse(String(raw)); }
        catch (_) {
            probeError = "INVALID_PROBE_RESPONSE";
            clearLive();
            return;
        }
        if (!reply || reply.source !== "linux-led-brightness-proxy"
                || reply.status !== "sampled") {
            probeError = "PROBE_UNAVAILABLE";
            clearLive();
            return;
        }
        const num = parseLock(reply.num);
        const caps = parseLock(reply.caps);
        sourceStatus = "led_proxy";
        numStatus = num.status;
        capsStatus = caps.status;
        lastSampleAtMs = nowMs;

        if (num.status === "observed") {
            stableNum = candidateNum === num.value
                ? Math.min(3, stableNum + 1) : 1;
            candidateNum = num.value;
        } else {
            candidateNum = "unknown";
            stableNum = 0;
        }
        if (caps.status === "observed") {
            stableCaps = candidateCaps === caps.value
                ? Math.min(3, stableCaps + 1) : 1;
            candidateCaps = caps.value;
        } else {
            candidateCaps = "unknown";
            stableCaps = 0;
        }
        if (stableNum >= 2)
            recordStable("num", candidateNum, nowMs);
        if (stableCaps >= 2)
            recordStable("caps", candidateCaps, nowMs);
    }
    function copyObservedToStartup() {
        // Independent explicit UI action: this never edits Sway files.
        // Existing KeyboardLockSettings confirmation remains mandatory.
        if (!canCopyToStartup)
            return false;
        const okNum = KeyboardLockSettings.choose("num", currentNum);
        const okCaps = okNum && KeyboardLockSettings.choose("caps", currentCaps);
        return okNum && okCaps;
    }

    Timer {
        id: periodicSample
        interval: 2200
        running: ledMonitor.monitoringEnabled && ledMonitor.canEdit
        repeat: true
        triggeredOnStart: true
        onTriggered: {
            ledMonitor.nowMs = Date.now();
            ledMonitor.sampleOnce();
        }
    }
    Process {
        id: sampleProcess
        running: false
        stdout: StdioCollector {
            onStreamFinished: ledMonitor.receiveSample(this.text)
        }
        onExited: function(code, exitStatus) {
            ledMonitor.sampling = false;
            if (code !== 0 || !ledMonitor.sampleReturned) {
                ledMonitor.probeError = "LED_PROBE_FAILED";
                ledMonitor.clearLive();
            }
        }
    }
    FileView {
        id: observationsFile
        path: ledMonitor.storagePath
        watchChanges: false
        atomicWrites: true
        blockWrites: false
        printErrors: false
        onLoaded: {
            if (ledMonitor.storageState === "saving")
                return;
            const parsed = Policy.parse(observationsFile.text());
            if (!parsed.ok) {
                ledMonitor.storageState = "error";
                ledMonitor.storageError = parsed.reason;
                return;
            }
            ledMonitor.document = parsed.document;
            ledMonitor.storageState = "ready";
        }
        onLoadFailed: function(error) {
            if (ledMonitor.storageState === "saving")
                return;
            if (error === FileViewError.FileNotFound) {
                ledMonitor.document = Policy.initialDocument();
                ledMonitor.storageState = "empty";
            } else {
                ledMonitor.storageState = "error";
                ledMonitor.storageError = "OBSERVATION_LOAD_FAILED";
            }
        }
        onSaved: {
            if (ledMonitor.pendingDocument === null)
                return;
            const saved = ledMonitor.pendingDocument;
            const queued = ledMonitor.queuedDocument;
            ledMonitor.document = saved;
            ledMonitor.pendingDocument = null;
            ledMonitor.queuedDocument = null;
            if (queued !== null && JSON.stringify(queued) !== JSON.stringify(saved))
                ledMonitor.beginWrite(queued);
            else
                ledMonitor.storageState = "ready";
        }
        onSaveFailed: function(error) {
            ledMonitor.pendingDocument = null;
            ledMonitor.queuedDocument = null;
            ledMonitor.storageState = "error";
            ledMonitor.storageError = "OBSERVATION_SAVE_FAILED";
        }
    }
}
