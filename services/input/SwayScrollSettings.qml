pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import "MouseScrollPolicy.js" as Policy

// The only owner of mouse/touchpad scroll settings.
// Real host changes use guarded Sway get_inputs + input identifier scroll_factor.
// Saving a preference NEVER automatically changes the compositor on startup.
Scope {
    id: settings

    readonly property string storagePath:
        Quickshell.dataDir + "/sway-mouse-scroll-preferences-v1.json"
    property string storeState: "loading"
    property string storeError: ""
    property var document: Policy.initialDocument()
    property var pendingDocument: null
    property var queuedDocument: null
    readonly property var effectiveDocument:
        queuedDocument !== null ? queuedDocument
        : pendingDocument !== null ? pendingDocument : document
    readonly property bool canStore:
        storeState === "ready" || storeState === "empty"
        || storeState === "saving"

    property var devices: []
    property string selectedId: ""
    property double stagedFactor: 1
    property double undoFactor: -1
    property string undoId: ""
    property bool confirmationRequired: false
    property bool querying: false
    property bool applying: false
    property bool queryReturned: false
    property bool applyReturned: false
    property string hostStatus: "unchecked"
    property string hostError: ""
    property string feedback: "REFRESH TO INSPECT SWAY POINTER DEVICES"
    property string applyId: ""
    property double applyOriginal: 1
    property double applyTarget: 1

    readonly property bool busy: querying || applying
    readonly property bool canApply:
        !busy && selectedDevice !== null
        && Policy.validFactor(stagedFactor)
        && !confirmationRequired
    readonly property var selectedDevice: findSelected()
    readonly property var savedFactor: Policy.get(effectiveDocument, selectedId)
    readonly property bool canRestore:
        !busy && selectedDevice !== null && undoId === selectedId
        && Policy.validFactor(undoFactor)
        && Math.abs(undoFactor - Number(selectedDevice.factor)) > 0.001

    function findSelected() {
        for (let i=0; i<devices.length; i++) {
            if (devices[i].identifier === selectedId)
                return devices[i];
        }
        return null;
    }
    function refresh() {
        if (busy)
            return false;
        querying = true;
        queryReturned = false;
        hostError = "";
        feedback = "READING SWAY INPUT DEVICE STATE";
        queryProcess.exec([
            "python3", "-B", "-I",
            Quickshell.shellPath("services/input/SwayScrollControl.py"),
            "list"
        ]);
        return true;
    }
    function selectDevice(identifier) {
        if (busy || typeof identifier !== "string")
            return false;
        const item = devices.find(x => x.identifier === identifier);
        if (!item)
            return false;
        selectedId = identifier;
        stagedFactor = Number(item.factor);
        confirmationRequired = false;
        feedback = "SELECTED // " + String(item.name);
        return true;
    }
    function stageFactor(value) {
        if (busy || !selectedDevice || !Policy.validFactor(value))
            return false;
        stagedFactor = value;
        confirmationRequired = false;
        feedback = "STAGED ONLY // NOT APPLIED TO SWAY";
        return true;
    }
    function stageSavedFactor() {
        if (savedFactor === null)
            return false;
        return stageFactor(savedFactor);
    }
    function stageRestore() {
        if (!canRestore)
            return false;
        return stageFactor(undoFactor);
    }
    function prepareApply() {
        if (!canApply)
            return false;
        if (Math.abs(Number(selectedDevice.factor) - stagedFactor) <= 0.001) {
            feedback = "ALREADY ACTIVE // NO CHANGE NECESSARY";
            return false;
        }
        confirmationRequired = true;
        feedback = "CONFIRM LIVE SWAY POINTER SCROLL CHANGE";
        return true;
    }
    function cancelApply() {
        confirmationRequired = false;
        feedback = "LIVE CHANGE CANCELLED";
    }
    function confirmApply() {
        if (!confirmationRequired || busy || !selectedDevice
                || !Policy.validFactor(stagedFactor))
            return false;
        applyId = selectedId;
        applyTarget = stagedFactor;
        applyOriginal = Number(selectedDevice.factor);
        confirmationRequired = false;
        applying = true;
        applyReturned = false;
        hostError = "";
        feedback = "APPLYING AND VERIFYING SWAY SCROLL FACTOR";
        applyProcess.exec([
            "python3", "-B", "-I",
            Quickshell.shellPath("services/input/SwayScrollControl.py"),
            "apply", applyId,
            applyTarget.toFixed(2),
            applyOriginal.toFixed(3)
        ]);
        return true;
    }
    function acceptQuery(raw) {
        queryReturned = true;
        let reply;
        try { reply = JSON.parse(String(raw)); }
        catch (_) { hostError = "INVALID_LIST_REPLY"; hostStatus = "unavailable"; return; }
        if (!reply || reply.status !== "ok"
                || !Array.isArray(reply.devices)
                || reply.devices.length > 64) {
            hostError = String(reply && reply.code || "NO_DEVICE_LIST");
            hostStatus = "unavailable";
            return;
        }
        let checked = [];
        for (const dev of reply.devices) {
            if (!dev || !Policy.validId(dev.identifier)
                    || !Number.isFinite(dev.factor)
                    || dev.factor < 0.25 || dev.factor > 6)
                continue;
            checked.push({
                identifier: dev.identifier,
                name: String(dev.name || dev.identifier).slice(0,100),
                kind: dev.kind === "touchpad" ? "touchpad" : "pointer",
                factor: Number(dev.factor)
            });
        }
        devices = checked;
        hostStatus = "ready";
        hostError = "";
        const selected = findSelected();
        if (!selected) {
            selectedId = checked.length ? checked[0].identifier : "";
            const current = findSelected();
            stagedFactor = current ? Number(current.factor) : 1;
        }
        feedback = checked.length
            ? "SWAY POINTERS // " + checked.length + " DETECTED"
            : "NO SUPPORTED SWAY POINTER DEVICE";
    }
    function storeApplied(identifier, factor) {
        if (!canStore)
            return;
        const updated = Policy.withFactor(effectiveDocument, identifier, factor);
        if (!updated.ok) {
            storeError = updated.reason;
            return;
        }
        if (pendingDocument !== null)
            queuedDocument = updated.document;
        else
            beginWrite(updated.document);
    }
    function beginWrite(next) {
        pendingDocument = next;
        storeState = "saving";
        storeError = "";
        profileFile.setText(JSON.stringify(next, null, 2) + "\n");
    }
    function acceptApply(raw) {
        applyReturned = true;
        let reply;
        try { reply = JSON.parse(String(raw)); }
        catch (_) { hostError = "INVALID_APPLY_REPLY"; hostStatus = "unavailable"; return; }
        if (!reply || (reply.status !== "applied"
                         && reply.status !== "unchanged")
                || reply.identifier !== applyId
                || Math.abs(Number(reply.factor) - applyTarget) > 0.001) {
            hostError = String(reply && reply.code || "APPLY_NOT_VERIFIED");
            hostStatus = "unavailable";
            return;
        }
        hostStatus = "ready";
        hostError = "";
        undoFactor = Number(reply.before);
        undoId = reply.identifier;
        devices = devices.map(function(item) {
            if (item.identifier === reply.identifier)
                return {identifier:item.identifier,name:item.name,
                        kind:item.kind,factor:Number(reply.factor)};
            return item;
        });
        storeApplied(reply.identifier, Number(reply.factor));
        feedback = "LIVE SWAY CHANGE VERIFIED // STARTUP NOT YET WIRED";
    }

    FileView {
        id: profileFile
        path: settings.storagePath
        watchChanges: false
        atomicWrites: true
        blockWrites: false
        printErrors: false
        onLoaded: {
            if (settings.storeState === "saving")
                return;
            const parsed = Policy.parse(profileFile.text());
            if (!parsed.ok) {
                settings.storeState = "error";
                settings.storeError = parsed.reason;
                return;
            }
            settings.document = parsed.document;
            settings.storeState = "ready";
            settings.storeError = "";
        }
        onLoadFailed: function(error) {
            if (settings.storeState === "saving")
                return;
            if (error === FileViewError.FileNotFound) {
                settings.document = Policy.initialDocument();
                settings.storeState = "empty";
                settings.storeError = "";
            } else {
                settings.storeState = "error";
                settings.storeError = "PROFILE_LOAD_FAILED";
            }
        }
        onSaved: {
            if (settings.pendingDocument === null)
                return;
            const saved = settings.pendingDocument;
            const queued = settings.queuedDocument;
            settings.document = saved;
            settings.pendingDocument = null;
            settings.queuedDocument = null;
            if (queued !== null
                    && JSON.stringify(queued) !== JSON.stringify(saved))
                settings.beginWrite(queued);
            else
                settings.storeState = "ready";
        }
        onSaveFailed: function(error) {
            settings.pendingDocument = null;
            settings.queuedDocument = null;
            settings.storeState = "error";
            settings.storeError = "PROFILE_SAVE_FAILED";
        }
    }
    Process {
        id: queryProcess
        running: false
        stdout: StdioCollector {
            onStreamFinished: settings.acceptQuery(this.text)
        }
        onExited: function(code, exitStatus) {
            settings.querying = false;
            if (code !== 0 || !settings.queryReturned) {
                settings.hostStatus = "unavailable";
                settings.hostError = settings.hostError || "SWAY_QUERY_FAILED";
            }
        }
    }
    Process {
        id: applyProcess
        running: false
        stdout: StdioCollector {
            onStreamFinished: settings.acceptApply(this.text)
        }
        onExited: function(code, exitStatus) {
            settings.applying = false;
            if (code !== 0 || !settings.applyReturned) {
                settings.hostStatus = "unavailable";
                settings.hostError = settings.hostError || "SWAY_APPLY_FAILED";
                settings.feedback = "LIVE CHANGE NOT VERIFIED // REFRESH";
            }
        }
    }
}
