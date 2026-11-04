pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import "TimeSettingsPolicy.js" as Policy
import "WorldZoneSearch.js" as ZoneSearch

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
    // One in-flight atomic write plus the latest queued adjustment. A burst
    // of button clicks updates the display immediately without concurrent
    // FileView writes, and the last accepted offset wins on disk.
    property var pendingDocument: null
    property var queuedDocument: null

    readonly property int displayOffsetMs:
        queuedDocument !== null ? Number(queuedDocument.displayOffsetMs)
        : pendingDocument !== null ? Number(pendingDocument.displayOffsetMs)
        : document ? Number(document.displayOffsetMs || 0) : 0
    readonly property string displayOffsetLabel:
        Policy.formatOffset(displayOffsetMs)
    readonly property bool canEdit:
        storageState === "ready" || storageState === "empty"
        || storageState === "saving"

    // Evidence-based attention for the dock. An unapplied zone choice or
    // disabled NTP alone does NOT prove the host clock is inaccurate.
    readonly property bool displayDeviationActive: displayOffsetMs !== 0
    // Explicit reference checks only: disabled NTP and a pending timezone
    // choice are not evidence that the computer's time is wrong.
    property bool referenceChecking: false
    property string referenceStatus: "unchecked"
    property string referenceMessage: "NO EXTERNAL MEASUREMENT"
    property double referenceOffsetMs: 0
    property double referenceUncertaintyMs: 0
    property string referenceSource: "NONE"
    property double referenceCheckedAtMs: 0
    property bool postResyncVerificationPending: false
    readonly property int referenceMaxAgeMs: 15 * 60 * 1000
    readonly property int referenceWarningThresholdMs: 1000

    function hasFreshReference(nowEpochMs) {
        return referenceStatus === "measured"
               && Number.isFinite(nowEpochMs)
               && nowEpochMs >= referenceCheckedAtMs
               && nowEpochMs - referenceCheckedAtMs <= referenceMaxAgeMs;
    }

    function dockZoneOffsetMismatch(nowEpochMs) {
        if (hostInfo.status !== "ready" || !Number.isFinite(nowEpochMs))
            return false;
        const text = String(hostInfo.utcOffset || "");
        const match = /^UTC([+-])(\d{2}):(\d{2})$/.exec(text);
        if (!match)
            return false; // Unknown is not evidence of mismatch.
        const hostMinutes =
            (match[1] === "-" ? -1 : 1)
            * (Number(match[2]) * 60 + Number(match[3]));
        const qmlMinutes = -new Date(nowEpochMs).getTimezoneOffset();
        return hostMinutes !== qmlMinutes;
    }

    function referenceIsOutOfSync(nowEpochMs) {
        return hasFreshReference(nowEpochMs)
               && (Math.abs(referenceOffsetMs) >= referenceWarningThresholdMs
                   || referenceUncertaintyMs >= referenceWarningThresholdMs);
    }

    // The Clock header and dock use identical evidence and expiry. A
    // successful command is not proof of accuracy; NTP=off is not a fault.
    function clockAccuracyState(nowEpochMs) {
        if (resyncStatus === "working" || resyncStatus === "auth-preparing")
            return "syncing";
        if (referenceChecking)
            return "checking";
        if (referenceIsOutOfSync(nowEpochMs))
            return "out-of-sync";
        if (dockZoneOffsetMismatch(nowEpochMs))
            return "zone-mismatch";
        if (displayDeviationActive)
            return "dirty";
        if (hasFreshReference(nowEpochMs))
            return "in-sync";
        if (resyncStatus === "failed" || resyncStatus === "cancelled"
                || resyncStatus === "unavailable")
            return "sync-error";
        return "unverified";
    }

    function clockAccuracyLabel(nowEpochMs) {
        switch (clockAccuracyState(nowEpochMs)) {
        case "syncing": return "SYNCING";
        case "checking": return "CHECKING";
        case "out-of-sync": return "OUT OF SYNC";
        case "zone-mismatch": return "ZONE DIFF";
        case "dirty": return "DIRTY";
        case "in-sync": return "IN SYNC";
        case "sync-error": return "SYNC ERROR";
        default: return "UNCHECKED";
        }
    }

    function clockAccuracyDetail(nowEpochMs) {
        const state = clockAccuracyState(nowEpochMs);
        if (state === "syncing")
            return "CHRONY / AUTH";
        if (state === "checking")
            return "REFERENCE";
        if (state === "out-of-sync" || state === "in-sync") {
            if (referenceSource === "CHRONY_TRACKING")
                return "TRACKING EST.";
            return "ERR " + (Math.abs(referenceOffsetMs) / 1000).toFixed(2) + "S";
        }
        if (state === "zone-mismatch")
            return "OFFSET DIFF";
        if (state === "dirty")
            return "CAL " + displayOffsetLabel;
        if (state === "sync-error")
            return "SEE SETTINGS";
        return "NO FRESH REF";
    }

    function dockTimeUnderlined(nowEpochMs) {
        return displayDeviationActive
               || dockZoneOffsetMismatch(nowEpochMs)
               || referenceIsOutOfSync(nowEpochMs);
    }

    function runPostResyncVerification() {
        if (!postResyncVerificationPending || resyncProcess.running
                || authSessionActive)
            return;
        postResyncVerificationPending = false;
        checkTimeAccuracy();
    }

    function checkTimeAccuracy() {
        if (referenceChecking || authSessionActive)
            return false;
        referenceChecking = true;
        referenceStatus = "checking";
        referenceMessage = "CHECKING CONFIGURED CHRONY REFERENCE...";
        referenceCheckedAtMs = 0;
        referenceUncertaintyMs = 0;
        referenceSource = "NONE";
        referenceProcess.exec([
            "python3", "-B", "-I",
            Quickshell.shellPath("services/time/TimeHostControl.py"), "measure"
        ]);
        return true;
    }

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
    // A stable gate for the whole authorization session. Never unload the
    // Polkit agent in between changing the pending and running properties.
    property bool authSessionActive: false
    property string authFlowStage: "NO REQUEST RECEIVED"
    property string authActionId: ""

    // Clock Settings reuses the same IANA zone search/parser as TimeW WORLD.
    // All zone data comes from read-only host tzdata; no duplicate writer.
    property var zoneCatalog: []
    property bool zoneCatalogLoading: false
    property bool zoneCatalogLoaded: false
    property bool zoneCatalogFailed: false
    property var zoneCountryNames: ({})
    property string zoneCountryTable: ""
    readonly property var zoneCountryIndex:
        ZoneSearch.parseCountryZones(zoneCountryTable, zoneCountryNames)

    property string zoneChoice: ""
    property bool timezoneConfirmRequired: false
    property bool timezoneAuthPending: false
    property string timezoneStatus: "idle"
    property string timezoneMessage: "NOT REQUESTED"
    property string timezoneErrorCode: ""

    function adjustedEpochMs(epochMs) {
        return Policy.adjustedEpochMs(epochMs, displayOffsetMs);
    }

    function beginOffsetWrite(nextDocument) {
        pendingDocument = nextDocument;
        storageState = "saving";
        settingsFile.setText(JSON.stringify(pendingDocument, null, 2) + "\n");
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
        errorCode = "";
        if (pendingDocument !== null) {
            // Do not invoke FileView.setText while an atomic write is
            // outstanding; coalesce successive clicks into one queued value.
            queuedDocument = next.document;
        } else {
            beginOffsetWrite(next.document);
        }
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
        queuedDocument = null;
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
        if (resyncProcess.running || authSessionActive || resyncAuthPending
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
                || resyncAuthPending || authSessionActive)
            return;
        resyncConfirmRequired = false;
        authSessionActive = true;
        authFlowStage = "WAITING FOR AUTHENTICATION REQUEST";
        authActionId = "";
        resyncAuthPending = true;
        resyncStatus = "auth-preparing";
        resyncAuthPath = "REGISTERING NATIVE POLKIT";
        resyncErrorCode = "";
        resyncMessage = "PREPARING GRAPHICAL POLKIT AUTHORIZATION...";
        // Never show a pre-sync reading as freshly confirmed after a
        // privileged correction or a new burst request.
        referenceStatus = "unchecked";
        referenceCheckedAtMs = 0;
        referenceUncertaintyMs = 0;
        referenceSource = "NONE";
        postResyncVerificationPending = false;
        authRegistrationFallback.restart();
    }

    function launchResyncAfterAgentReady(nativeRegistered) {
        if (!resyncAuthPending || resyncProcess.running)
            return;
        authRegistrationFallback.stop();
        resyncAuthPath = nativeRegistered === true
            ? "NATIVE POLKIT AGENT REGISTERED"
            : "EXISTING SESSION AGENT FALLBACK (UNVERIFIED)";
        // Set running before clearing pending; the root loader is held by
        // authSessionActive until the child process exits.
        resyncStatus = "working";
        resyncAuthPending = false;
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
        onTriggered: {
            timeSettings.launchResyncAfterAgentReady(false);
            timeSettings.launchTimezoneAfterAgentReady(false);
        }
    }

    function loadZoneCatalog() {
        if (zoneCatalogLoading || zoneCatalogLoaded)
            return;
        zoneCatalogLoading = true;
        zoneCatalogFailed = false;
        zoneCatalogProcess.exec(["timedatectl", "list-timezones", "--no-pager"]);
        countryNamesProcess.exec(["cat", "/usr/share/zoneinfo/iso3166.tab"]);
        countryZonesProcess.exec(["cat", "/usr/share/zoneinfo/zone.tab"]);
    }

    function prepareTimezone(zoneId) {
        if (authSessionActive || timezoneStatus === "working"
                || !ZoneSearch.contains(zoneCatalog, zoneId))
            return false;
        zoneChoice = zoneId;
        if (zoneId === hostInfo.timezone) {
            timezoneConfirmRequired = false;
            timezoneStatus = "unchanged";
            timezoneMessage = "SYSTEM ALREADY USES " + zoneId;
            return true;
        }
        timezoneConfirmRequired = true;
        timezoneStatus = "confirm";
        timezoneMessage = "CONFIRM SYSTEM-WIDE TIMEZONE // " + zoneId;
        return true;
    }

    function cancelTimezone() {
        timezoneConfirmRequired = false;
        // Revert the visible selection to the verified host zone. A cancelled
        // candidate must never look like an already-applied timezone.
        zoneChoice = "";
        if (timezoneStatus === "confirm") {
            timezoneStatus = "idle";
            timezoneMessage = "TIMEZONE CHANGE CANCELLED";
        }
    }

    function requestTimezone() {
        if (!timezoneConfirmRequired || authSessionActive
                || !ZoneSearch.contains(zoneCatalog, zoneChoice))
            return;
        timezoneConfirmRequired = false;
        authSessionActive = true;
        authFlowStage = "WAITING FOR AUTHENTICATION REQUEST";
        authActionId = "";
        timezoneAuthPending = true;
        timezoneStatus = "auth-preparing";
        timezoneErrorCode = "";
        timezoneMessage = "PREPARING SYSTEM TIMEZONE AUTHORIZATION...";
        authRegistrationFallback.restart();
    }

    function launchTimezoneAfterAgentReady(nativeRegistered) {
        if (!timezoneAuthPending || !authSessionActive
                || timezoneProcess.running)
            return;
        authRegistrationFallback.stop();
        // Keep the same registered PolkitAgent alive until timedatectl exits.
        timezoneStatus = "working";
        timezoneAuthPending = false;
        timezoneMessage = "AUTHENTICATE TO CHANGE SYSTEM TIMEZONE...";
        timezoneProcess.exec([
            "python3", "-B", "-I",
            Quickshell.shellPath("services/time/TimeHostControl.py"),
            "set-timezone", zoneChoice
        ]);
    }

    Process {
        id: zoneCatalogProcess
        running: false
        stdout: StdioCollector {
            onStreamFinished: {
                const zones = ZoneSearch.parseCatalog(this.text);
                if (zones.length > 0) {
                    timeSettings.zoneCatalog = zones;
                    timeSettings.zoneCatalogLoaded = true;
                    timeSettings.zoneCatalogFailed = false;
                }
            }
        }
        onExited: function(code, exitStatus) {
            timeSettings.zoneCatalogLoading = false;
            if (code !== 0 || !timeSettings.zoneCatalogLoaded)
                timeSettings.zoneCatalogFailed = true;
        }
    }
    Process {
        id: countryNamesProcess
        running: false
        stdout: StdioCollector {
            onStreamFinished:
                timeSettings.zoneCountryNames =
                    ZoneSearch.parseCountryNames(this.text)
        }
    }
    Process {
        id: countryZonesProcess
        running: false
        stdout: StdioCollector {
            onStreamFinished: timeSettings.zoneCountryTable = this.text
        }
    }
    Process {
        id: timezoneProcess
        running: false
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const output = JSON.parse(this.text);
                    timeSettings.timezoneStatus =
                        String(output.status || "failed");
                    timeSettings.timezoneMessage =
                        String(output.message || "TIMEZONE RESULT UNAVAILABLE");
                    timeSettings.timezoneErrorCode =
                        String(output.errorCode || "");
                } catch (error) {
                    timeSettings.timezoneStatus = "failed";
                    timeSettings.timezoneErrorCode = "ZONE_RESPONSE";
                    timeSettings.timezoneMessage = "TIMEZONE RESPONSE INVALID";
                }
            }
        }
        onExited: function(code, exitStatus) {
            timeSettings.authSessionActive = false;
            if (code !== 0) {
                timeSettings.timezoneStatus = "failed";
                timeSettings.timezoneErrorCode = "ZONE_PROCESS";
                timeSettings.timezoneMessage = "TIMEZONE PROCESS FAILED";
            }
            timeSettings.refreshHostStatus();
        }
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
            const saved = timeSettings.pendingDocument;
            const queued = timeSettings.queuedDocument;
            timeSettings.document = saved;
            timeSettings.pendingDocument = null;
            timeSettings.queuedDocument = null;
            timeSettings.errorCode = "";
            if (queued !== null
                    && queued.displayOffsetMs !== saved.displayOffsetMs) {
                timeSettings.beginOffsetWrite(queued);
            } else {
                timeSettings.storageState = "ready";
            }
        }
        onSaveFailed: function(error) {
            timeSettings.pendingDocument = null;
            timeSettings.queuedDocument = null;
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
        id: referenceProcess
        running: false
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const value = JSON.parse(this.text);
                    const offset = Number(value.offsetMs);
                    const uncertainty = Number(value.uncertaintyMs || 0);
                    if (value.status === "measured"
                            && Number.isFinite(offset)
                            && Number.isFinite(uncertainty)
                            && uncertainty >= 0) {
                        timeSettings.referenceOffsetMs = offset;
                        timeSettings.referenceUncertaintyMs = uncertainty;
                        timeSettings.referenceSource =
                            String(value.source || "CHRONYD_ONESHOT");
                        timeSettings.referenceCheckedAtMs = Date.now();
                        timeSettings.referenceStatus = "measured";
                        timeSettings.referenceMessage =
                            "REFERENCE // "
                            + (offset / 1000).toFixed(3) + "S"
                            + (timeSettings.referenceSource === "CHRONY_TRACKING"
                               ? " // DAEMON TRACKING ESTIMATE"
                               : " // CHRONYD MEASUREMENT");
                    } else {
                        timeSettings.referenceStatus = "unavailable";
                        timeSettings.referenceMessage =
                            String(value.message || "NO REFERENCE SAMPLE");
                    }
                } catch (error) {
                    timeSettings.referenceStatus = "unavailable";
                    timeSettings.referenceMessage = "REFERENCE RESULT INVALID";
                }
            }
        }
        onExited: function(code, exitStatus) {
            timeSettings.referenceChecking = false;
            if (code !== 0) {
                timeSettings.referenceStatus = "unavailable";
                timeSettings.referenceMessage = "REFERENCE PROCESS FAILED";
            }
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
                    timeSettings.postResyncVerificationPending =
                        value.status === "completed"
                        || value.status === "requested";
                    if (timeSettings.postResyncVerificationPending) {
                        timeSettings.referenceStatus = "unchecked";
                        timeSettings.referenceCheckedAtMs = 0;
                        timeSettings.referenceMessage =
                            "SYNC REQUEST ACCEPTED // VERIFYING RESULT...";
                    }
                    timeSettings.runPostResyncVerification();
                } catch (error) {
                    timeSettings.resyncStatus = "failed";
                    timeSettings.resyncMessage = "RESYNC RESULT UNAVAILABLE";
                }
                timeSettings.refreshHostStatus();
            }
        }
        onExited: function(code, exitStatus) {
            timeSettings.authSessionActive = false;
            if (code !== 0) {
                timeSettings.postResyncVerificationPending = false;
                timeSettings.resyncStatus = "failed";
                timeSettings.resyncMessage = "RESYNC PROCESS FAILED";
            }
            // Collector/exited callbacks may arrive in either order. A single
            // pending flag ensures both completed and requested paths get
            // exactly one read-only follow-up check, not a second time change.
            timeSettings.runPostResyncVerification();
        }
    }
}
