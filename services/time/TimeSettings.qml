pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import "TimeSettingsPolicy.js" as Policy

// Shared time configuration owner. CLOCK is the first consumer; CPU++ can
// import qs.services.time without borrowing a window or creating another
// filesystem writer. Neither calibration nor refresh edits Linux system time.
Scope {
    id: timeSettings

    readonly property string storagePath:
        Quickshell.dataDir + "/time-settings-v1.json"
    property string storageState: "loading"
    property string errorCode: ""
    property var document: Policy.initialDocument()
    property var pendingDocument: null

    readonly property int displayOffsetMs:
        document ? Number(document.displayOffsetMs || 0) : 0
    readonly property string displayOffsetLabel:
        Policy.formatOffset(displayOffsetMs)
    readonly property bool canEdit:
        (storageState === "ready" || storageState === "empty")
        && pendingDocument === null

    property var hostInfo: ({ status: "unavailable", timezone: "UNKNOWN",
                               utcOffset: "UNKNOWN", dstActive: false,
                               ntpEnabled: "unknown",
                               ntpSynchronized: "unknown",
                               rtcLocal: "unknown" })
    property bool hostRefreshing: false
    property string hostError: ""
    property string resyncStatus: "idle"
    property bool resyncConfirmRequired: false
    // Signal to the root-shell LazyLoader to register a temporary, native
    // Quickshell Polkit authentication agent. Registration must precede pkexec.
    property bool resyncAuthPending: false
    property string resyncAuthPath: "NOT REQUESTED"
    property string resyncMessage: "NOT REQUESTED"
    property string resyncErrorCode: ""
    property bool diagnosticBusy: false
    property string diagnosticMessage: "NOT CHECKED"
    property string diagnosticDetail: ""

    function adjustedEpochMs(epochMs) {
        return Policy.adjustedEpochMs(epochMs, displayOffsetMs);
    }

    function persistOffset(ms) {
        if (!canEdit) {
            errorCode = "STORAGE_NOT_READY";
            return false;
        }
        const next = Policy.withOffset(document, ms);
        if (!next.ok) {
            errorCode = next.reason;
            return false;
        }
        pendingDocument = next.document;
        errorCode = "";
        storageState = "saving";
        settingsFile.setText(JSON.stringify(pendingDocument, null, 2) + "\n");
        return true;
    }

    function adjustDisplayMs(delta) {
        if (!Number.isInteger(delta))
            return false;
        return persistOffset(displayOffsetMs + delta);
    }

    function resetDisplay() {
        return persistOffset(0);
    }

    function acceptSaved(raw) {
        if (storageState === "saving")
            return;
        const parsed = Policy.parse(raw);
        if (!parsed.ok) {
            storageState = parsed.reason === "UNSUPPORTED_VERSION"
                           ? "unsupported" : "error";
            errorCode = parsed.reason;
            return;
        }
        document = parsed.document;
        pendingDocument = null;
        storageState = "ready";
        errorCode = "";
    }

    function refreshHostStatus() {
        if (hostRefreshing)
            return;
        hostRefreshing = true;
        hostError = "";
        hostStatusProcess.exec([
            "python3", "-B", "-I",
            Quickshell.shellPath("services/time/TimeHostControl.py"), "status"
        ]);
    }

    function diagnoseResync() {
        if (diagnosticBusy)
            return;
        diagnosticBusy = true;
        diagnosticMessage = "CHECKING CHRONY PREREQUISITES...";
        diagnosticDetail = "";
        diagnosticsProcess.exec([
            "python3", "-B", "-I",
            Quickshell.shellPath("services/time/TimeHostControl.py"), "diagnose"
        ]);
    }

    function prepareResync() {
        if (resyncProcess.running || resyncAuthPending
                || resyncStatus === "working")
            return;
        resyncConfirmRequired = true;
        resyncStatus = "confirm";
        resyncMessage = "CONFIRM ONE-SHOT HOST TIME CORRECTION BELOW";
    }

    function cancelResync() {
        if (!resyncConfirmRequired)
            return;
        resyncConfirmRequired = false;
        resyncStatus = "idle";
        resyncMessage = "RESYNC CANCELLED // CLOCK UNCHANGED";
    }

    // The user's CONFIRM click requests auth setup, NOT a direct pkexec.
    // When the native agent registers, or an existing desktop agent is
    // expected, launchResyncAfterAgentReady() starts the original fixed argv.
    function requestResync() {
        if (!resyncConfirmRequired || resyncProcess.running
                || resyncAuthPending)
            return;
        resyncConfirmRequired = false;
        resyncAuthPending = true;
        resyncStatus = "auth-preparing";
        resyncAuthPath = "REGISTERING NATIVE POLKIT";
        resyncErrorCode = "";
        resyncMessage = "PREPARING GRAPHICAL POLKIT AUTHORIZATION...";
        authRegistrationFallback.restart();
    }

    function launchResyncAfterAgentReady(nativeRegistered) {
        if (!resyncAuthPending || resyncProcess.running)
            return;
        resyncAuthPending = false;
        authRegistrationFallback.stop();
        resyncAuthPath = nativeRegistered === true
            ? "NATIVE POLKIT AGENT REGISTERED"
            : "EXISTING SESSION AGENT FALLBACK (UNVERIFIED)";
        resyncStatus = "working";
        resyncErrorCode = "";
        resyncMessage = "AUTHENTICATE TO REQUEST ONE-SHOT TIME CORRECTION...";
        resyncProcess.exec([
            "python3", "-B", "-I",
            Quickshell.shellPath("services/time/TimeHostControl.py"), "resync"
        ]);
    }

    // If another graphical Polkit agent already owns the session, native
    // registration can fail legitimately. Give it a chance, then let pkexec
    // use the existing agent. On a broken setup the backend reports a clear
    // auth error rather than silently retrying or bypassing authorization.
    Timer {
        id: authRegistrationFallback
        interval: 2500
        repeat: false
        onTriggered: timeSettings.launchResyncAfterAgentReady(false)
    }

    FileView {
        id: settingsFile
        path: timeSettings.storagePath
        watchChanges: false
        atomicWrites: true
        blockWrites: false
        printErrors: false

        onLoaded: timeSettings.acceptSaved(settingsFile.text())
        onLoadFailed: function(error) {
            if (timeSettings.storageState === "saving")
                return;
            if (error === FileViewError.FileNotFound) {
                timeSettings.document = Policy.initialDocument();
                timeSettings.storageState = "empty";
                timeSettings.errorCode = "";
            } else {
                timeSettings.storageState = "error";
                timeSettings.errorCode = "FILE_LOAD_FAILED";
            }
        }
        onSaved: {
            if (timeSettings.storageState !== "saving"
                    || timeSettings.pendingDocument === null)
                return;
            timeSettings.document = timeSettings.pendingDocument;
            timeSettings.pendingDocument = null;
            timeSettings.storageState = "ready";
            timeSettings.errorCode = "";
        }
        onSaveFailed: function(error) {
            timeSettings.pendingDocument = null;
            timeSettings.storageState = "error";
            timeSettings.errorCode = "FILE_SAVE_FAILED";
        }
    }

    Process {
        id: hostStatusProcess
        running: false
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const value = JSON.parse(this.text);
                    if (value.status !== "ready")
                        throw new Error("host status unavailable");
                    timeSettings.hostInfo = value;
                    timeSettings.hostError = "";
                } catch (error) {
                    timeSettings.hostError = "HOST STATUS UNAVAILABLE";
                }
            }
        }
        onExited: function(code, exitStatus) {
            timeSettings.hostRefreshing = false;
            if (code !== 0)
                timeSettings.hostError = "HOST STATUS READ FAILED";
        }
    }

    Process {
        id: diagnosticsProcess
        running: false
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const output = JSON.parse(this.text);
                    timeSettings.diagnosticMessage =
                        String(output.message || "DIAGNOSTIC UNAVAILABLE");
                    timeSettings.diagnosticDetail =
                        String(output.detail || output.errorCode || "");
                } catch (error) {
                    timeSettings.diagnosticMessage = "DIAGNOSTIC RESPONSE INVALID";
                    timeSettings.diagnosticDetail = "";
                }
            }
        }
        onExited: function(code, exitStatus) {
            timeSettings.diagnosticBusy = false;
            if (code !== 0) {
                timeSettings.diagnosticMessage = "DIAGNOSTIC PROCESS FAILED";
                timeSettings.diagnosticDetail = "";
            }
        }
    }

    Process {
        id: resyncProcess
        running: false
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const value = JSON.parse(this.text);
                    timeSettings.resyncStatus = String(value.status || "failed");
                    timeSettings.resyncMessage =
                        String(value.message || "NO RESYNC RESULT");
                    timeSettings.resyncErrorCode =
                        String(value.errorCode || "");
                } catch (error) {
                    timeSettings.resyncStatus = "failed";
                    timeSettings.resyncMessage = "RESYNC RESULT UNAVAILABLE";
                }
                timeSettings.refreshHostStatus();
            }
        }
        onExited: function(code, exitStatus) {
            if (code !== 0) {
                timeSettings.resyncStatus = "failed";
                timeSettings.resyncMessage = "RESYNC PROCESS FAILED";
            }
        }
    }
}
