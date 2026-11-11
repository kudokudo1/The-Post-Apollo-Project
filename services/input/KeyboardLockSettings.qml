pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import "KeyboardLockPolicy.js" as Policy

// Sole owner of persistent keyboard startup intent. This is not the current
// physical key state. Only a second, explicit confirmation runs the Sway helper.
Scope {
    id: settings

    readonly property string storagePath:
        Quickshell.dataDir + "/keyboard-lock-startup-v1.json"
    property string storageState: "loading"
    property string storageError: ""
    property var document: Policy.initialDocument()
    property var pendingDocument: null
    property var queuedDocument: null
    property bool confirmRequired: false

    readonly property bool canEdit:
        storageState === "ready" || storageState === "empty"
        || storageState === "saving"
    readonly property bool canApply:
        storageState === "ready" && pendingDocument === null
        && queuedDocument === null && !applying && !inspecting
    readonly property var effectiveDocument:
        queuedDocument !== null ? queuedDocument
        : pendingDocument !== null ? pendingDocument : document
    readonly property string numMode: effectiveDocument.num
    readonly property string capsMode: effectiveDocument.caps

    property string hostStatus: "unchecked"
    property string hostError: ""
    property string installedNum: ""
    property string installedCaps: ""
    property bool inspecting: false
    property bool applying: false
    property string feedback: "STARTUP POLICY NOT YET INSPECTED"
    readonly property bool profileInstalled:
        hostStatus === "installed"
        && installedNum === numMode && installedCaps === capsMode

    function beginWrite(next) {
        pendingDocument = next;
        storageState = "saving";
        storageError = "";
        profileFile.setText(JSON.stringify(next, null, 2) + "\n");
    }

    function choose(lockName, mode) {
        if (!canEdit)
            return false;
        const choice = Policy.withMode(effectiveDocument, lockName, mode);
        if (!choice.ok) {
            storageError = choice.reason;
            return false;
        }
        confirmRequired = false;
        if (pendingDocument !== null)
            queuedDocument = choice.document;
        else
            beginWrite(choice.document);
        feedback = "PREFERENCE SAVING // SWAY NOT RELOADED";
        return true;
    }

    function prepareApply() {
        if (!canApply)
            return false;
        confirmRequired = true;
        feedback = "CONFIRM USER SWAY STARTUP CONFIG CHANGE";
        return true;
    }
    function cancelApply() {
        confirmRequired = false;
        feedback = "CONFIG CHANGE CANCELLED";
    }
    function requestApply() {
        if (!confirmRequired || !canApply)
            return false;
        confirmRequired = false;
        applying = true;
        hostError = "";
        feedback = "WRITING USER SWAY STARTUP FILES";
        applyProcess.exec([
            "python3", "-B", "-I",
            Quickshell.shellPath("services/input/SwayKeyboardStartup.py"),
            "apply", document.num, document.caps
        ]);
        return true;
    }
    function inspectHost() {
        if (inspecting || applying)
            return false;
        inspecting = true;
        hostError = "";
        inspectProcess.exec([
            "python3", "-B", "-I",
            Quickshell.shellPath("services/input/SwayKeyboardStartup.py"),
            "status"
        ]);
        return true;
    }
    function acceptHostReply(raw) {
        try {
            const reply = JSON.parse(String(raw));
            const status = String(reply.status || "");
            if (status === "installed") {
                hostStatus = "installed";
                installedNum = String(reply.num || "");
                installedCaps = String(reply.caps || "");
                hostError = "";
                feedback = "SWAY FILE INSTALLED // EFFECTIVE NEXT SWAY START";
            } else if (status === "not_installed") {
                hostStatus = "not_installed";
                installedNum = "";
                installedCaps = "";
                hostError = "";
                feedback = "SWAY FILE NOT YET INSTALLED";
            } else {
                hostStatus = "unavailable";
                installedNum = "";
                installedCaps = "";
                hostError = String(reply.code || "HOST_UNAVAILABLE");
                feedback = "SWAY STARTUP FILE UNAVAILABLE";
            }
        } catch (_) {
            hostStatus = "unavailable";
            hostError = "INVALID_HOST_REPLY";
            feedback = "SWAY HELPER RESPONSE INVALID";
        }
    }

    FileView {
        id: profileFile
        path: settings.storagePath
        watchChanges: false
        atomicWrites: true
        blockWrites: false
        printErrors: false
        onLoaded: {
            if (settings.storageState === "saving")
                return;
            const parsed = Policy.parse(profileFile.text());
            if (!parsed.ok) {
                settings.storageState = "error";
                settings.storageError = parsed.reason;
                return;
            }
            settings.document = parsed.document;
            settings.storageState = "ready";
            settings.storageError = "";
        }
        onLoadFailed: function(error) {
            if (settings.storageState === "saving")
                return;
            if (error === FileViewError.FileNotFound) {
                settings.document = Policy.initialDocument();
                settings.storageState = "empty";
                settings.storageError = "";
            } else {
                settings.storageState = "error";
                settings.storageError = "PROFILE_LOAD_FAILED";
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
            if (queued !== null &&
                    (queued.num !== saved.num || queued.caps !== saved.caps)) {
                settings.beginWrite(queued);
            } else {
                settings.storageState = "ready";
                settings.feedback = "PREFERENCES SAVED // APPLY TO SWAY WHEN READY";
            }
        }
        onSaveFailed: function(error) {
            settings.pendingDocument = null;
            settings.queuedDocument = null;
            settings.storageState = "error";
            settings.storageError = "PROFILE_SAVE_FAILED";
            settings.feedback = "PREFERENCES NOT SAVED";
        }
    }
    Process {
        id: inspectProcess
        running: false
        stdout: StdioCollector {
            onStreamFinished: settings.acceptHostReply(this.text)
        }
        onExited: function(code, exitStatus) {
            settings.inspecting = false;
            if (code !== 0 && settings.hostStatus !== "unavailable") {
                settings.hostStatus = "unavailable";
                settings.hostError = "HOST_INSPECT_FAILED";
            }
        }
    }
    Process {
        id: applyProcess
        running: false
        stdout: StdioCollector {
            onStreamFinished: settings.acceptHostReply(this.text)
        }
        onExited: function(code, exitStatus) {
            settings.applying = false;
            if (code !== 0 && settings.hostStatus !== "unavailable") {
                settings.hostStatus = "unavailable";
                settings.hostError = "HOST_APPLY_FAILED";
            }
        }
    }
}
