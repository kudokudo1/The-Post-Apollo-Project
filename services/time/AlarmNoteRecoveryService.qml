pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import "AlarmManagerPolicy.js" as AlarmPolicy
import "AlarmNoteDraftPolicy.js" as Draft

// Clock note recovery is a sidecar and NOT a second writer of time-alarms-v2.
// Only AlarmManagerService may change live alarms, even for recovered notes.
Scope {
    id: recovery
    readonly property string draftPath: Quickshell.dataDir + "/alarm-note-draft-v1.json"
    readonly property string alarmPath: AlarmManagerService.storagePath

    property string draftState: "loading"
    property string phase: ""
    property string feedback: "NOTE RECOVERY LOADING"
    property var noteDraft: null
    property var pendingDraft: null
    property var pendingPatch: null
    property int pendingId: 0
    property string pendingSource: ""
    property bool timedOut: false
    property bool lastUnchanged: false

    property bool checkPending: false
    property bool diskChecked: false
    property var diskDocument: null
    readonly property string disposition: diskChecked
        ? Draft.disposition(noteDraft, diskDocument) : "unverified"
    readonly property bool writable: draftState === "empty" && phase === ""
        && AlarmManagerService.storageState === "ready"
        && AlarmManagerService.pendingDocument === null
        && AlarmManagerService.queuedDocument === null
    readonly property bool canRetry: phase === "" && draftState === "ready"
        && diskChecked && disposition === "recoverable"
        && AlarmManagerService.storageState === "ready"
        && AlarmManagerService.pendingDocument === null
        && AlarmManagerService.queuedDocument === null
        && JSON.stringify(AlarmManagerService.document)
             === JSON.stringify(diskDocument)
    readonly property bool canClear: phase === "" && draftState === "ready"
        && diskChecked && disposition === "already-saved"

    signal noteSaved(int alarmId)
    signal noteSaveFailed(int alarmId, string reason)

    function saveWithPatch(id, edit) {
        lastUnchanged = false;
        if (!writable) {
            feedback = "NOTE NOT STARTED // SAVE BUSY OR RECOVERY NEEDED";
            return false;
        }
        const row = AlarmManagerService.findAlarm(id);
        if (!row || !edit || !Object.prototype.hasOwnProperty.call(edit, "note")
                || !AlarmPolicy.validNote(edit.note)) {
            feedback = "INVALID NOTE";
            return false;
        }
        const normalized = edit.note.trim();
        const patch = Object.assign({}, edit, {note: normalized});
        const checked = AlarmPolicy.update(AlarmManagerService.document, id,
                                          patch, Date.now());
        if (!checked.ok) {
            feedback = checked.error;
            return false;
        }
        if ((row.note || "") === normalized) {
            lastUnchanged = true;
            feedback = "NOTE UNCHANGED // NO DRAFT REQUIRED";
            return false;
        }
        const prepared = Draft.create(row, normalized, Date.now());
        if (!prepared.ok) {
            feedback = prepared.reason;
            return false;
        }
        pendingDraft = prepared.document.draft;
        pendingPatch = patch;
        pendingId = id;
        pendingSource = JSON.stringify(AlarmManagerService.document);
        phase = "draft";
        draftState = "writing";
        diskChecked = false;
        timedOut = false;
        feedback = "STAGING DURABLE NOTE // NOT YET SAVED";
        saveWatchdog.restart();
        draftFile.setText(JSON.stringify(prepared.document) + "\n");
        return true;
    }
    function saveNote(id, note) {
        return saveWithPatch(id, {note: note});
    }
    function abortPending(reason) {
        saveWatchdog.stop();
        const id = pendingId;
        pendingPatch = null;
        pendingDraft = null;
        pendingSource = "";
        pendingId = 0;
        phase = "";
        timedOut = false;
        feedback = reason;
        noteSaveFailed(id, reason);
    }
    function beginCanonicalWrite() {
        // A queued timer or another edit may have changed the source while
        // the sidecar was being written. Never apply a stale edit.
        if (timedOut) {
            abortPending("DRAFT SAVED // CHECK DISK AFTER RESTART");
            return;
        }
        if (AlarmManagerService.storageState !== "ready"
                || AlarmManagerService.pendingDocument !== null
                || AlarmManagerService.queuedDocument !== null
                || pendingSource !== JSON.stringify(AlarmManagerService.document)
                || Draft.disposition(pendingDraft, AlarmManagerService.document)
                     !== "recoverable") {
            abortPending("SOURCE CHANGED // NOTE RECOVERY REQUIRED");
            return;
        }
        phase = "journal";
        const id = pendingId;
        if (!AlarmManagerService.saveAlarm(id, pendingPatch))
            abortPending("ALARM WRITE REFUSED // DRAFT PRESERVED");
    }
    function observeCanonicalWrite() {
        if (phase !== "journal") return;
        if (AlarmManagerService.storageState === "ready") {
            const row = AlarmManagerService.findAlarm(pendingId);
            if (!row || (row.note || "") !== pendingDraft.after) {
                abortPending("NOTE RESULT MISMATCH // DRAFT PRESERVED");
                return;
            }
            saveWatchdog.stop();
            const id = pendingId;
            pendingPatch = null;
            pendingSource = "";
            pendingId = 0;
            pendingDraft = null;
            timedOut = false;
            feedback = "NOTE SAVED // CLEARING RECOVERY DRAFT";
            noteSaved(id);
            beginClear();
        } else if (AlarmManagerService.storageState === "error") {
            abortPending("ALARM SAVE FAILED // DRAFT PRESERVED");
        }
    }
    function beginClear() {
        // Called only after the canonical writer acknowledged or the user
        // explicitly verified that the note is already in the disk document.
        phase = "clear";
        draftState = "clearing";
        draftFile.setText(JSON.stringify(Draft.emptyDocument()) + "\n");
    }
    function checkDisk() {
        if (phase !== "" || draftState !== "ready") return false;
        diskChecked = false;
        diskDocument = null;
        checkPending = true;
        feedback = "CHECKING ACTUAL ALARM FILE // READ ONLY";
        alarmReadFile.reload();
        return true;
    }
    function retryVerified() {
        if (!canRetry) {
            feedback = "RETRY REFUSED // CHECK DISK OR RESOLVE CONFLICT";
            return false;
        }
        const row = AlarmManagerService.findAlarm(noteDraft.id);
        if (!row || Draft.disposition(noteDraft, AlarmManagerService.document)
                     !== "recoverable") {
            feedback = "SOURCE MOVED // RETRY REFUSED";
            return false;
        }
        pendingDraft = noteDraft;
        pendingPatch = {note: noteDraft.after};
        pendingId = noteDraft.id;
        pendingSource = JSON.stringify(AlarmManagerService.document);
        timedOut = false;
        phase = "journal";
        diskChecked = false;
        feedback = "RETRYING VERIFIED NOTE // NOT YET SAVED";
        saveWatchdog.restart();
        if (!AlarmManagerService.saveAlarmNote(pendingId, pendingDraft.after)) {
            abortPending("RETRY NOT ACCEPTED // DRAFT PRESERVED");
            return false;
        }
        return true;
    }
    function clearVerified() {
        if (!canClear) {
            feedback = "CLEAR REFUSED // CHECK DISK FIRST";
            return false;
        }
        diskChecked = false;
        beginClear();
        return true;
    }

    Connections {
        target: AlarmManagerService
        function onStorageStateChanged() { recovery.observeCanonicalWrite(); }
    }

    FileView {
        id: draftFile
        path: recovery.draftPath
        watchChanges: false
        atomicWrites: true
        blockWrites: false
        printErrors: false
        onLoaded: {
            if (recovery.phase !== "") return;
            const result = Draft.parse(draftFile.text());
            if (!result.ok) {
                recovery.draftState = "error";
                recovery.feedback = "DRAFT INVALID // FILE PRESERVED";
                return;
            }
            recovery.noteDraft = result.document.draft;
            recovery.draftState = recovery.noteDraft ? "ready" : "empty";
            recovery.feedback = recovery.noteDraft
                ? "RECOVERY DRAFT FOUND // CHECK DISK" : "NOTE RECOVERY READY";
        }
        onLoadFailed: function(error) {
            if (recovery.phase !== "") return;
            if (error === FileViewError.FileNotFound) {
                recovery.noteDraft = null;
                recovery.draftState = "empty";
                recovery.feedback = "NOTE RECOVERY READY";
            } else {
                recovery.draftState = "error";
                recovery.feedback = "DRAFT FILE UNREADABLE // PRESERVED";
            }
        }
        onSaved: {
            if (recovery.phase === "draft" && recovery.draftState === "writing") {
                recovery.noteDraft = recovery.pendingDraft;
                recovery.draftState = "ready";
                recovery.beginCanonicalWrite();
            } else if (recovery.phase === "clear") {
                recovery.noteDraft = null;
                recovery.pendingDraft = null;
                recovery.draftState = "empty";
                recovery.phase = "";
                recovery.diskChecked = false;
                recovery.feedback = "NOTE RECOVERY READY";
            }
        }
        onSaveFailed: function(error) {
            if (recovery.phase === "draft") {
                recovery.draftState = "error";
                recovery.abortPending("DRAFT WRITE FAILED // NOTE NOT SAVED");
            } else if (recovery.phase === "clear") {
                recovery.phase = "";
                recovery.draftState = "ready";
                recovery.feedback = "NOTE SAVED // DRAFT CLEAR FAILED";
            }
        }
    }

    // Independent read-only reload: the initial load never authorizes a retry.
    FileView {
        id: alarmReadFile
        path: recovery.alarmPath
        watchChanges: false
        printErrors: false
        onLoaded: {
            if (!recovery.checkPending) return;
            recovery.checkPending = false;
            const parsed = AlarmPolicy.parse(alarmReadFile.text());
            if (!parsed.ok) {
                recovery.feedback = "CHECK FAILED // ALARMS INVALID";
                return;
            }
            recovery.diskDocument = parsed.document;
            recovery.diskChecked = true;
            recovery.feedback = "DISK CHECK // " + recovery.disposition.toUpperCase();
        }
        onLoadFailed: function(error) {
            if (!recovery.checkPending) return;
            recovery.checkPending = false;
            recovery.diskChecked = false;
            recovery.feedback = "ALARM DISK UNREADABLE // NO RETRY";
        }
    }
    Timer {
        id: saveWatchdog
        interval: 12000
        repeat: false
        onTriggered: {
            if (recovery.phase !== "draft" && recovery.phase !== "journal")
                return;
            recovery.timedOut = true;
            recovery.feedback = "WRITE STALLED // NO RETRY // RESTART TO CHECK";
            recovery.noteSaveFailed(recovery.pendingId, "SAVE_ACK_TIMEOUT");
            // Do not release phase: a late FileView acknowledgment may still
            // arrive. It must not permit a competing write in this process.
        }
    }
}
