pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import "TimeSettingsPolicy.js" as Policy
import "TimeAutoCheckPolicy.js" as AutoCheck
import "TimeReferencePolicy.js" as Reference
import "WorldZoneSearch.js" as ZoneSearch
import "WorldFavoritesPolicy.js" as Favorites

// Shared time configuration owner. CLOCK is the first consumer; CPU++ can
// import qs.services.time without borrowing a window or creating another
// filesystem writer. Neither calibration nor refresh edits Linux system time.
Scope {
    id: timeSettings

    readonly property string storagePath:
        Quickshell.dataDir + "/time-settings-v1.json"
    // Favorites are a separate document owned by this shared TIME service.
    // The display-calibration v1 schema and Linux time are never touched.
    readonly property string worldFavoritesPath:
        Quickshell.dataDir + "/time-world-favorites-v1.json"
    property string storageState: "loading"
    property string errorCode: ""
    property var document: Policy.initialDocument()
    // One in-flight atomic write plus the latest queued adjustment. A burst
    // of button clicks updates the display immediately without concurrent
    // FileView writes, and the last accepted offset wins on disk.
    property var pendingDocument: null
    property var queuedDocument: null

    // Durable, independent auto-reference preference. Never reuses the
    // display-calibration v1 document or privileged RESYNC confirmation flow.
    readonly property string autoCheckStoragePath:
        Quickshell.dataDir + "/time-auto-check-v1.json"
    property string autoCheckStorageState: "loading"
    property string autoCheckErrorCode: ""
    property var autoCheckDocument: AutoCheck.initialDocument()
    property var autoCheckPendingDocument: null
    property var autoCheckQueuedDocument: null
    property double autoLastStartedAtMs: 0
    // One reload-trigger per instantiated Quickshell service, not per save.
    property bool autoCheckReloadHandled: false
    property bool autoCheckOpenPendingWhileLoading: false
    property bool autoCheckInFlight: false
    property bool autoCheckResultSeen: false
    property bool autoCheckExited: false
    property bool autoCheckExitOk: false
    property string autoCheckResult: "NO AUTOMATIC MEASUREMENT"
    readonly property bool autoCheckEnabled:
        !!autoCheckDocument.enabled
    readonly property int autoCheckIntervalHours:
        Number(autoCheckDocument.intervalHours || 6)
    readonly property bool autoCheckOnReload:
        autoCheckDocument.checkOnReload !== false
    readonly property bool autoCheckOnClockOpen:
        autoCheckDocument.checkOnClockOpen !== false
    readonly property double autoCheckLastAttemptAtMs:
        Math.max(autoLastStartedAtMs, Number(autoCheckDocument.lastAttemptAtMs || 0))
    readonly property double autoCheckNextDueAtMs:
        AutoCheck.nextDueAtMs(autoCheckDocument, autoLastStartedAtMs)
    readonly property bool autoCheckCanEdit:
        autoCheckStorageState === "ready" || autoCheckStorageState === "empty"
        || autoCheckStorageState === "saving"

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
    // Tracks manual checks and post-RESYNC verification as well as AUTO.
    // This is session-only; automatic attempts also have a durable timestamp.
    property double referenceLastAttemptAtMs: 0
    property bool referenceAttemptSucceeded: false
    property string referenceFailureMessage: ""
    property double referenceFailureAtMs: 0

    // Durable measurement evidence, independent of cadence and RESYNC.
    readonly property string referenceStoragePath:
        Quickshell.dataDir + "/time-reference-v1.json"
    property string referenceStorageState: "loading"
    property string referenceStoreError: ""
    property var referenceDocument: Reference.initialDocument()
    property var referenceLoadedDocument: null
    property var referencePendingDocument: null
    property var referenceQueuedDocument: null
    property bool referenceStoreReadDone: false
    property bool referenceBootReadDone: false
    property bool referenceRestoreHandled: false
    property string referenceBootId: ""
    // Local arithmetic only; never starts Chrony or a network request.
    property double referenceNowMs: Date.now()
    readonly property var referenceEstimate:
        Reference.estimate(referenceDocument, referenceNowMs, referenceBootId)
    readonly property string referenceLiveDetail:
        referenceEstimate.available
        ? (referenceEstimate.fresh ? "ESTIMATE" : "STALE")
          + " // OFFSET " + (referenceEstimate.offsetMs / 1000).toFixed(3)
          + "S // UNCERTAINTY "
          + (referenceEstimate.uncertaintyMs / 1000).toFixed(3) + "S"
          + (referenceEstimate.predicted ? " // TREND" : " // HELD")
        : "NO VALID CACHED REFERENCE"
    property bool postResyncVerificationPending: false
    readonly property int referenceMaxAgeMs: 15 * 60 * 1000
    readonly property int referenceWarningThresholdMs: 1000

    function hasFreshReference(nowEpochMs) {
        if (referenceStatus !== "measured" || !Number.isFinite(nowEpochMs))
            return false;
        const projected = Reference.estimate(referenceDocument, nowEpochMs,
                                             referenceBootId);
        // No boot-id means the result is session-only and never durable.
        return projected.available ? projected.fresh
               : referenceBootId === "" && referenceCheckedAtMs > 0
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
        // Only the portion of the estimate that exceeds its source error
        // bound can count as evidence that the host clock is wrong.
        return hasFreshReference(nowEpochMs)
               && Math.abs(referenceEstimate.available ? referenceEstimate.offsetMs
                            : referenceOffsetMs)
               - (referenceEstimate.available ? referenceEstimate.uncertaintyMs
                  : referenceUncertaintyMs) >= referenceWarningThresholdMs;
    }

    function referenceIsUncertain(nowEpochMs) {
        return hasFreshReference(nowEpochMs)
               && !referenceIsOutOfSync(nowEpochMs)
               && Math.abs(referenceEstimate.available ? referenceEstimate.offsetMs
                            : referenceOffsetMs)
               + (referenceEstimate.available ? referenceEstimate.uncertaintyMs
                  : referenceUncertaintyMs) >= referenceWarningThresholdMs;
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
        if (referenceIsUncertain(nowEpochMs))
            return "uncertain";
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
        case "uncertain": return "UNCERTAIN";
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
        if (state === "uncertain")
            return "ERROR BOUND";
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
        referenceAttemptSucceeded = false;
        if (referenceCheckedAtMs <= 0)
            referenceStatus = "checking";
        // Do not destroy the previous measurement while a new check runs.
        referenceMessage = "CHECKING CONFIGURED CHRONY REFERENCE...";
        referenceLastAttemptAtMs = Date.now();
        referenceProcess.exec([
            "python3", "-B", "-I",
            Quickshell.shellPath("services/time/TimeHostControl.py"), "measure"
        ]);
        return true;
    }

    function writeReferenceDocument(next) {
        referencePendingDocument = next;
        referenceStorageState = "saving";
        referenceFile.setText(JSON.stringify(next, null, 2) + "\n");
    }

    function persistReferenceDocument(next) {
        referenceDocument = next; // update live view before disk save
        if (referenceStorageState !== "ready"
                && referenceStorageState !== "empty"
                && referenceStorageState !== "saving")
            return;
        if (referencePendingDocument !== null)
            referenceQueuedDocument = next;
        else
            writeReferenceDocument(next);
    }

    function noteReferenceFailure(message) {
        referenceAttemptSucceeded = false;
        referenceFailureAtMs = Date.now();
        referenceFailureMessage = String(message || "REFERENCE UNAVAILABLE");
        referenceStatus = referenceCheckedAtMs > 0 ? "measured" : "unavailable";
        referenceMessage = referenceFailureMessage;
        // Preserve the old sample: a failure is not evidence of zero offset.
        const next = Reference.withFailure(referenceDocument,
                                           referenceFailureAtMs,
                                           referenceFailureMessage);
        if (next.ok)
            persistReferenceDocument(next.document);
    }

    function recordReferenceMeasurement(output) {
        const now = Date.now();
        const offset = Number(output.offsetMs);
        const uncertainty = Number(output.uncertaintyMs);
        const source = String(output.source || "");
        if (!Number.isFinite(offset) || !Number.isFinite(uncertainty)
                || uncertainty < 0 || Math.abs(offset) > 86400000
                || uncertainty > 86400000
                || (source !== "CHRONY_TRACKING"
                    && source !== "CHRONYD_ONESHOT")) {
            noteReferenceFailure("INVALID REFERENCE MEASUREMENT");
            return;
        }
        referenceOffsetMs = offset;
        referenceUncertaintyMs = uncertainty;
        referenceSource = source;
        referenceCheckedAtMs = now;
        referenceStatus = "measured";
        referenceAttemptSucceeded = true;
        referenceFailureMessage = "";
        referenceFailureAtMs = 0;
        referenceMessage = "REFERENCE // " + (offset / 1000).toFixed(3) + "S"
                           + (source === "CHRONY_TRACKING"
                              ? " // DAEMON TRACKING ESTIMATE"
                              : " // CHRONYD MEASUREMENT");
        const next = Reference.withMeasurement(referenceDocument,
            { offsetMs: offset, uncertaintyMs: uncertainty, source: source },
            now, referenceBootId);
        if (next.ok)
            persistReferenceDocument(next.document);
    }

    function restoreReferenceAfterLoad() {
        if (referenceRestoreHandled || !referenceStoreReadDone
                || !referenceBootReadDone)
            return;
        referenceRestoreHandled = true;
        const saved = referenceLoadedDocument || Reference.initialDocument();
        if (referenceCheckedAtMs <= 0)
            referenceDocument = saved;
        const projected = Reference.estimate(referenceDocument, Date.now(),
                                              referenceBootId);
        if (projected.available && referenceCheckedAtMs <= 0) {
            const sample = referenceDocument.sample;
            referenceOffsetMs = sample.offsetMs;
            referenceUncertaintyMs = sample.uncertaintyMs;
            referenceSource = sample.source;
            referenceCheckedAtMs = sample.checkedAtMs;
            referenceStatus = "measured";
            referenceMessage = projected.fresh
                ? "CACHED REFERENCE // NO EXTRA QUERY"
                : "CACHED REFERENCE STALE // A NEW CHECK MAY BE DUE";
        }
        if (referenceDocument.lastFailureAtMs > 0) {
            referenceFailureAtMs = referenceDocument.lastFailureAtMs;
            referenceFailureMessage = referenceDocument.lastError;
            autoCheckResult = "UNAVAILABLE // " + referenceFailureMessage;
        } else if (projected.available) {
            autoCheckResult = "CACHED // " + referenceLiveDetail;
        }
        referenceLoadedDocument = null;
        maybeBeginStartupAutoChecks();
    }

    function maybeBeginStartupAutoChecks() {
        if (autoCheckReloadHandled || autoCheckStorageState === "loading"
                || !referenceRestoreHandled)
            return;
        autoCheckReloadHandled = true;
        Qt.callLater(function() {
            if (autoCheckOpenPendingWhileLoading) {
                autoCheckOpenPendingWhileLoading = false;
                timeSettings.checkOnClockOpened();
            }
            timeSettings.maybeAutoCheckTime("reload");
            timeSettings.maybeAutoCheckTime();
        });
    }

    function invalidateReferenceForResync() {
        referenceStatus = "unchecked";
        referenceCheckedAtMs = 0;
        referenceUncertaintyMs = 0;
        referenceSource = "NONE";
        const previous = referenceDocument;
        persistReferenceDocument({ version: Reference.VERSION, sample: null,
            lastAttemptAtMs: previous.lastAttemptAtMs,
            lastFailureAtMs: previous.lastFailureAtMs,
            lastError: previous.lastError });
    }

    function writeAutoCheck(next) {
        autoCheckPendingDocument = next;
        autoCheckStorageState = "saving";
        autoCheckFile.setText(JSON.stringify(next, null, 2) + "\n");
    }

    function saveAutoCheck(next) {
        if (!autoCheckCanEdit)
            return false;
        if (autoCheckPendingDocument !== null)
            autoCheckQueuedDocument = next;
        else
            writeAutoCheck(next);
        return true;
    }

    function setAutoCheckEnabled(enabled) {
        if (!autoCheckCanEdit || typeof enabled !== "boolean")
            return false;
        const base = autoCheckQueuedDocument || autoCheckPendingDocument
                     || autoCheckDocument;
        const next = AutoCheck.withSchedule(base, enabled, base.intervalHours);
        if (!next.ok)
            return false;
        return saveAutoCheck(next.document);
    }

    function setAutoCheckIntervalHours(hours) {
        if (!autoCheckCanEdit)
            return false;
        const base = autoCheckQueuedDocument || autoCheckPendingDocument
                     || autoCheckDocument;
        const next = AutoCheck.withSchedule(base, base.enabled, Number(hours));
        if (!next.ok)
            return false;
        return saveAutoCheck(next.document);
    }

    function setAutoCheckTrigger(name, enabled) {
        if (!autoCheckCanEdit || typeof enabled !== "boolean")
            return false;
        const base = autoCheckQueuedDocument || autoCheckPendingDocument
                     || autoCheckDocument;
        const next = AutoCheck.withTrigger(base, name, enabled);
        if (!next.ok)
            return false;
        return saveAutoCheck(next.document);
    }

    function checkOnClockOpened() {
        if (autoCheckStorageState === "loading" || !referenceRestoreHandled) {
            autoCheckOpenPendingWhileLoading = true;
            return false;
        }
        return maybeAutoCheckTime("clock-open");
    }

    function maybeAutoCheckTime(trigger) {
        const reason = trigger || "interval";
        // Use the latest accepted edit, so a toggle immediately suppresses
        // its trigger even while its atomic save is still in flight.
        const active = autoCheckQueuedDocument || autoCheckPendingDocument
                       || autoCheckDocument;
        if (!autoCheckCanEdit || !AutoCheck.triggerEnabled(active, reason)
                || autoCheckInFlight || referenceChecking || authSessionActive
                || resyncAuthPending || resyncProcess.running)
            return false;
        const now = Date.now();
        const estimate = Reference.estimate(referenceDocument, now,
                                             referenceBootId);
        if (!AutoCheck.canStartAutomaticCheck(active, reason, now,
                                              autoLastStartedAtMs,
                                              referenceLastAttemptAtMs,
                                              { ready: referenceRestoreHandled,
                                                fresh: estimate.fresh,
                                                hasMeasurement: estimate.available,
                                                lastFailureAtMs: referenceFailureAtMs }))
            return false;
        if (!checkTimeAccuracy())
            return false;
        autoLastStartedAtMs = now;
        autoCheckInFlight = true;
        autoCheckResultSeen = false;
        autoCheckExited = false;
        autoCheckExitOk = false;
        autoCheckResult = "CHECKING // " + reason.toUpperCase()
                          + " // CONFIGURED CHRONY REFERENCE";
        const next = AutoCheck.withAttempt(active, now);
        if (next.ok && !saveAutoCheck(next.document))
            autoCheckErrorCode = "SCHEDULE_NOT_SAVED";
        return true;
    }

    function completeAutoReferenceIfReady() {
        if (!autoCheckInFlight || !autoCheckExited
                || (!autoCheckResultSeen && autoCheckExitOk))
            return;
        autoResultDeadline.stop();
        autoCheckInFlight = false;
        // Keep the measured deviation and its uncertainty visible instead
        // of repeating an uninformative OUT OF SYNC label on every open.
        // No second Chrony request is made to format a cached result.
        const offset = (referenceOffsetMs / 1000).toFixed(3) + "S";
        const uncertainty = (referenceUncertaintyMs / 1000).toFixed(3) + "S";
        autoCheckResult = !autoCheckExitOk
                          || !referenceAttemptSucceeded
                          ? "UNAVAILABLE // " + referenceMessage
                          : referenceIsOutOfSync(Date.now())
                          ? "OUT OF SYNC // OFFSET " + offset
                            + " // UNCERTAINTY " + uncertainty
                          : "MEASURED // OFFSET " + offset
                            + " // UNCERTAINTY " + uncertainty;
    }

    Timer {
        interval: 1000
        running: true
        repeat: true
        onTriggered: timeSettings.referenceNowMs = Date.now()
    }

    Timer {
        // A minute-level wakeup avoids a week-long timer being lost to reload.
        // Last attempt is saved separately to survive Quickshell restarts.
        interval: 60 * 1000
        running: true
        repeat: true
        onTriggered: timeSettings.maybeAutoCheckTime()
    }

    Timer {
        id: autoResultDeadline
        interval: 3000
        repeat: false
        onTriggered: {
            if (timeSettings.autoCheckInFlight) {
                timeSettings.autoCheckExitOk = false;
                timeSettings.completeAutoReferenceIfReady();
            }
        }
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

    property string worldFavoriteState: "loading"
    property string worldFavoriteError: ""
    property string worldFavoriteMessage: "FAVORITES // LOADING"
    property var worldFavoriteDocument: Favorites.initialDocument()
    property var worldFavoritePendingDocument: null
    property var worldFavoriteQueuedDocument: null
    readonly property var worldFavoriteZones:
        worldFavoriteQueuedDocument !== null ? worldFavoriteQueuedDocument.zones
        : worldFavoritePendingDocument !== null ? worldFavoritePendingDocument.zones
        : worldFavoriteDocument.zones
    readonly property int worldFavoriteLimit: Favorites.MAX_FAVORITES
    readonly property bool worldFavoriteCanEdit:
        worldFavoriteState === "empty" || worldFavoriteState === "ready"
        || worldFavoriteState === "saving"

    function isWorldFavorite(zoneId) {
        return Favorites.contains(worldFavoriteZones, zoneId);
    }

    function beginWorldFavoriteWrite(nextDocument) {
        worldFavoritePendingDocument = nextDocument;
        worldFavoriteState = "saving";
        worldFavoritesFile.setText(JSON.stringify(nextDocument, null, 2) + "\n");
    }

    function toggleWorldFavorite(zoneId, installedZones) {
        if (!worldFavoriteCanEdit) {
            worldFavoriteMessage = "FAVORITES STORE NOT READY";
            return false;
        }
        // WORLD resolves selections only through the installed tzdata list.
        // A stale/hand-edited saved favorite is never blindly put into TZ.
        if (!ZoneSearch.contains(installedZones, zoneId)) {
            worldFavoriteMessage = "ZONE NOT INSTALLED // NOTHING SAVED";
            return false;
        }
        const next = Favorites.toggle(worldFavoriteZones, zoneId);
        if (!next.ok) {
            worldFavoriteMessage = next.reason;
            return false;
        }
        worldFavoriteError = "";
        worldFavoriteMessage = next.added
            ? "STARRED // " + zoneId : "UNSTARRED // " + zoneId;
        if (worldFavoritePendingDocument !== null) {
            // Coalesce rapid star taps; only the latest state is saved.
            worldFavoriteQueuedDocument = next.document;
        } else {
            beginWorldFavoriteWrite(next.document);
        }
        return true;
    }

    function loadWorldFavoriteDocument(raw) {
        if (worldFavoriteState === "saving")
            return;
        const parsed = Favorites.parse(raw);
        if (!parsed.ok) {
            worldFavoriteState =
                parsed.reason === "UNSUPPORTED_VERSION" ? "unsupported" : "error";
            worldFavoriteError = parsed.reason;
            worldFavoriteMessage = "FAVORITES FILE INVALID // NOT OVERWRITTEN";
            return;
        }
        worldFavoriteDocument = parsed.document;
        worldFavoritePendingDocument = null;
        worldFavoriteQueuedDocument = null;
        worldFavoriteState = "ready";
        worldFavoriteError = "";
        worldFavoriteMessage = "FAVORITES READY";
    }

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
        invalidateReferenceForResync();
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
        id: worldFavoritesFile
        path: timeSettings.worldFavoritesPath
        watchChanges: false
        atomicWrites: true
        blockWrites: false
        printErrors: false

        onLoaded: timeSettings.loadWorldFavoriteDocument(worldFavoritesFile.text())
        onLoadFailed: function(error) {
            if (timeSettings.worldFavoriteState === "saving")
                return;
            if (error === FileViewError.FileNotFound) {
                timeSettings.worldFavoriteDocument = Favorites.initialDocument();
                timeSettings.worldFavoriteState = "empty";
                timeSettings.worldFavoriteError = "";
                timeSettings.worldFavoriteMessage = "FAVORITES EMPTY";
            } else {
                timeSettings.worldFavoriteState = "error";
                timeSettings.worldFavoriteError = "FAVORITES_LOAD_FAILED";
                timeSettings.worldFavoriteMessage = "FAVORITES FILE NOT LOADED";
            }
        }
        onSaved: {
            if (timeSettings.worldFavoriteState !== "saving"
                    || timeSettings.worldFavoritePendingDocument === null)
                return;
            const saved = timeSettings.worldFavoritePendingDocument;
            const queued = timeSettings.worldFavoriteQueuedDocument;
            timeSettings.worldFavoriteDocument = saved;
            timeSettings.worldFavoritePendingDocument = null;
            timeSettings.worldFavoriteQueuedDocument = null;
            timeSettings.worldFavoriteError = "";
            if (queued !== null
                    && JSON.stringify(queued.zones) !== JSON.stringify(saved.zones)) {
                timeSettings.beginWorldFavoriteWrite(queued);
            } else {
                timeSettings.worldFavoriteState = "ready";
            }
        }
        onSaveFailed: function(error) {
            timeSettings.worldFavoritePendingDocument = null;
            timeSettings.worldFavoriteQueuedDocument = null;
            timeSettings.worldFavoriteState = "error";
            timeSettings.worldFavoriteError = "FAVORITES_SAVE_FAILED";
            timeSettings.worldFavoriteMessage = "FAVORITES NOT SAVED // CHECK STORAGE";
        }
    }

    // This read-only kernel file changes on reboot; an old wall-clock
    // timestamp must not authorize an old sample on a new boot.
    FileView {
        id: referenceBootFile
        path: "/proc/sys/kernel/random/boot_id"
        watchChanges: false
        onLoaded: {
            const boot = referenceBootFile.text().trim().toLowerCase();
            timeSettings.referenceBootId = Reference.bootId(boot) ? boot : "";
            timeSettings.referenceBootReadDone = true;
            timeSettings.restoreReferenceAfterLoad();
        }
        onLoadFailed: function(error) {
            timeSettings.referenceBootId = "";
            timeSettings.referenceBootReadDone = true;
            timeSettings.restoreReferenceAfterLoad();
        }
    }

    FileView {
        id: referenceFile
        path: timeSettings.referenceStoragePath
        watchChanges: false
        atomicWrites: true
        blockWrites: false
        printErrors: false
        onLoaded: {
            if (timeSettings.referenceStorageState === "saving")
                return;
            const parsed = Reference.parse(referenceFile.text());
            timeSettings.referenceLoadedDocument = parsed.ok
                ? parsed.document : Reference.initialDocument();
            timeSettings.referenceStorageState = parsed.ok
                ? "ready" : "error";
            timeSettings.referenceStoreError = parsed.ok ? "" : parsed.reason;
            timeSettings.referenceStoreReadDone = true;
            timeSettings.restoreReferenceAfterLoad();
        }
        onLoadFailed: function(error) {
            if (timeSettings.referenceStorageState === "saving")
                return;
            const missing = error === FileViewError.FileNotFound;
            timeSettings.referenceLoadedDocument = Reference.initialDocument();
            timeSettings.referenceStorageState = missing ? "empty" : "error";
            timeSettings.referenceStoreError = missing
                ? "" : "REFERENCE_LOAD_FAILED";
            timeSettings.referenceStoreReadDone = true;
            timeSettings.restoreReferenceAfterLoad();
        }
        onSaved: {
            if (timeSettings.referenceStorageState !== "saving"
                    || timeSettings.referencePendingDocument === null)
                return;
            const saved = timeSettings.referencePendingDocument;
            const queued = timeSettings.referenceQueuedDocument;
            timeSettings.referencePendingDocument = null;
            timeSettings.referenceQueuedDocument = null;
            timeSettings.referenceStoreError = "";
            if (queued !== null && JSON.stringify(saved) !== JSON.stringify(queued))
                timeSettings.writeReferenceDocument(queued);
            else
                timeSettings.referenceStorageState = "ready";
        }
        onSaveFailed: function(error) {
            timeSettings.referencePendingDocument = null;
            timeSettings.referenceQueuedDocument = null;
            timeSettings.referenceStorageState = "error";
            timeSettings.referenceStoreError = "REFERENCE_SAVE_FAILED";
        }
    }

    FileView {
        id: autoCheckFile
        path: timeSettings.autoCheckStoragePath
        watchChanges: false
        atomicWrites: true
        blockWrites: false
        printErrors: false

        onLoaded: {
            if (timeSettings.autoCheckStorageState === "saving")
                return;
            const parsed = AutoCheck.parse(autoCheckFile.text());
            if (!parsed.ok) {
                timeSettings.autoCheckStorageState =
                    parsed.reason === "UNSUPPORTED_VERSION" ? "unsupported" : "error";
                timeSettings.autoCheckErrorCode = parsed.reason;
                return;
            }
            timeSettings.autoCheckDocument = parsed.document;
            timeSettings.autoCheckStorageState = "ready";
            timeSettings.autoCheckErrorCode = "";
            timeSettings.maybeBeginStartupAutoChecks();
        }
        onLoadFailed: function(error) {
            if (timeSettings.autoCheckStorageState === "saving")
                return;
            timeSettings.autoCheckStorageState =
                error === FileViewError.FileNotFound ? "empty" : "error";
            timeSettings.autoCheckErrorCode =
                error === FileViewError.FileNotFound ? "" : "SCHEDULE_LOAD_FAILED";
            timeSettings.maybeBeginStartupAutoChecks();
        }
        onSaved: {
            if (timeSettings.autoCheckStorageState !== "saving"
                    || timeSettings.autoCheckPendingDocument === null)
                return;
            const saved = timeSettings.autoCheckPendingDocument;
            const queued = timeSettings.autoCheckQueuedDocument;
            timeSettings.autoCheckDocument = saved;
            timeSettings.autoCheckPendingDocument = null;
            timeSettings.autoCheckQueuedDocument = null;
            timeSettings.autoCheckErrorCode = "";
            if (queued !== null && JSON.stringify(queued) !== JSON.stringify(saved))
                timeSettings.writeAutoCheck(queued);
            else {
                timeSettings.autoCheckStorageState = "ready";
                Qt.callLater(timeSettings.maybeAutoCheckTime);
            }
        }
        onSaveFailed: function(error) {
            timeSettings.autoCheckPendingDocument = null;
            timeSettings.autoCheckQueuedDocument = null;
            timeSettings.autoCheckStorageState = "error";
            timeSettings.autoCheckErrorCode = "SCHEDULE_SAVE_FAILED";
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
                    if (value.status === "measured")
                        timeSettings.recordReferenceMeasurement(value);
                    else
                        timeSettings.noteReferenceFailure(
                            String(value.message || value.errorCode || "NO REFERENCE SAMPLE"));
                } catch (error) {
                    timeSettings.noteReferenceFailure("REFERENCE RESULT INVALID");
                }
                if (timeSettings.autoCheckInFlight) {
                    timeSettings.autoCheckResultSeen = true;
                    timeSettings.completeAutoReferenceIfReady();
                }
            }
        }
        onExited: function(code, exitStatus) {
            timeSettings.referenceChecking = false;
            if (code !== 0)
                timeSettings.noteReferenceFailure("REFERENCE PROCESS FAILED");
            if (timeSettings.autoCheckInFlight) {
                timeSettings.autoCheckExited = true;
                timeSettings.autoCheckExitOk = code === 0;
                timeSettings.completeAutoReferenceIfReady();
                if (timeSettings.autoCheckInFlight)
                    autoResultDeadline.restart();
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
