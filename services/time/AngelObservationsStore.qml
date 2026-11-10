pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import "AngelObservationPolicy.js" as Journal
import "AngelNoteDraftPolicy.js" as Draft

// ANGEL owns one local observation journal. It is NOT the Notes, Tasks,
// Weather archives or a second host clock. Nothing writes until RECORD or
// a confirmed DELETE; no network, continuous polling, or auto-observation.
Scope {
    id: angel

    readonly property string storagePath:
        Quickshell.dataDir + "/angel-observations-v1.json"
    // A separate small, atomic draft is committed BEFORE a note journal write.
    // Existing observations stay in the original v1 file; no migration.
    readonly property string draftPath:
        Quickshell.dataDir + "/angel-note-draft-v1.json"

    property string storageState: "loading"
    property string errorCode: ""
    property string feedback: "LOADING LOCAL OBSERVATIONS"
    property var document: Journal.emptyDocument()
    property var pendingDocument: null
    property string pendingKind: ""
    property string pendingNoteId: ""
    // "draft" -> sidecar ack; "journal" -> observation journal ack.
    // Never start two writer operations on the same journal concurrently.
    property string writePhase: ""
    property string draftState: "loading"
    property var noteDraft: null
    property var pendingNoteDraft: null
    property bool recoveryDiskChecked: false
    property bool recoveryCheckPending: false
    readonly property var observations: document.observations
    readonly property int total: observations.length
    readonly property bool writable:
        (storageState === "ready" || storageState === "empty")
        && draftState === "empty" && writePhase === ""
    readonly property string noteDraftDisposition:
        storageState === "ready" || storageState === "empty"
        ? Draft.disposition(noteDraft, observations) : "unverified"

    // These are receipt signals, NOT "accepted into a write queue" signals.
    signal noteSaved(string id)
    signal noteSaveFailed(string id, string reason)

    function acceptLoaded(raw) {
        if (writePhase !== "")
            return;
        const loaded = Journal.parse(raw);
        if (!loaded.ok) {
            recoveryCheckPending = false;
            recoveryDiskChecked = false;
            storageState = loaded.reason === "UNSUPPORTED_VERSION"
                           ? "unsupported" : "error";
            errorCode = loaded.reason;
            feedback = "JOURNAL INVALID // DATA PRESERVED ON DISK";
            return;
        }
        document = loaded.document;
        // Initial load is NOT an explicit check for the recovery action.
        // Only a fresh CHECK DISK request can arm a retry.
        recoveryDiskChecked = recoveryCheckPending;
        recoveryCheckPending = false;
        storageState = document.observations.length ? "ready" : "empty";
        errorCode = "";
        feedback = "JOURNAL READY // " + document.observations.length;
    }

    function reloadFromDisk() {
        // A timed-out write might STILL finish. No reload/retry until
        // it has acknowledged or a fresh process has removed the writer.
        if (writePhase !== "")
            return false;
        recoveryDiskChecked = false;
        storageState = "loading";
        errorCode = "";
        feedback = "RELOADING JOURNAL";
        journalFile.reload();
        return true;
    }

    function beginJournalWrite(nextDocument, kind, noteId) {
        pendingDocument = nextDocument;
        pendingKind = kind;
        pendingNoteId = noteId || "";
        writePhase = "journal";
        storageState = "saving";
        errorCode = "";
        feedback = "WRITING // NOT YET SAVED";
        saveWatchdog.restart();
        journalFile.setText(JSON.stringify(pendingDocument, null, 2) + "\n");
        return true;
    }

    function stage(next) {
        if (!writable)
            return false;
        if (!next || next.ok !== true) {
            feedback = "NOT RECORDED // " + String(
                next && next.reason ? next.reason : "INVALID_RECORD");
            return false;
        }
        return beginJournalWrite(next.document, "journal", "");
    }

    function record(digits, capture, observedAtMs) {
        return stage(Journal.create(document, digits, capture, observedAtMs));
    }

    function deleteObservation(id, confirmed) {
        return stage(Journal.remove(document, id, confirmed));
    }

    // An explicit review flag is a journal edit, never a deletion or a
    // claim that a number has no traditional interpretation.
    function toggleErrObservation(id) {
        return stage(Journal.toggleErr(document, id));
    }

    function saveObservationNote(id, note) {
        if (!writable) {
            feedback = "NOTE NOT STARTED // JOURNAL OR DRAFT NEEDS RECOVERY";
            return false;
        }
        const next = Journal.setNote(document, id, note);
        if (!next.ok) {
            feedback = "NOTE NOT STARTED // " + next.reason;
            return false;
        }
        const row = observations.find(function(item) { return item.id === id; });
        const prepared = Draft.create(row, note, Date.now());
        if (!prepared.ok) {
            feedback = "NOTE NOT STARTED // " + prepared.reason;
            return false;
        }
        pendingDocument = next.document;
        pendingKind = "note";
        pendingNoteId = id;
        pendingNoteDraft = prepared.document.draft;
        draftState = "writing";
        storageState = "drafting";
        writePhase = "draft";
        errorCode = "";
        feedback = "PRESERVING NOTE DRAFT // NOT YET SAVED";
        saveWatchdog.restart();
        draftFile.setText(JSON.stringify(prepared.document, null, 2) + "\n");
        return true;
    }

    function acceptDraftLoaded(raw) {
        if (draftState === "writing" || draftState === "clearing")
            return;
        const result = Draft.parse(raw);
        if (!result.ok) {
            draftState = "error";
            errorCode = result.reason;
            feedback = "DRAFT INVALID // FILE PRESERVED FOR RECOVERY";
            return;
        }
        noteDraft = result.document.draft;
        draftState = noteDraft ? "ready" : "empty";
        if (noteDraft)
            feedback = "RECOVERY DRAFT FOUND // CHECK DISK BEFORE RETRY";
    }

    function checkRecoveryFromDisk() {
        if (writePhase !== "" || draftState !== "ready")
            return false;
        recoveryCheckPending = true;
        if (!reloadFromDisk()) {
            recoveryCheckPending = false;
            return false;
        }
        return true;
    }

    function retryNoteDraft() {
        if (writePhase !== "" || draftState !== "ready"
                || !recoveryDiskChecked
                || (storageState !== "ready" && storageState !== "empty")
                || noteDraftDisposition !== "recoverable") {
            feedback = "RETRY BLOCKED // CHECK DISK OR RESOLVE CONFLICT";
            return false;
        }
        const next = Journal.setNote(document, noteDraft.id, noteDraft.after);
        if (!next.ok)
            return false;
        return beginJournalWrite(next.document, "note", noteDraft.id);
    }

    function clearVerifiedDraft() {
        if (writePhase !== "" || draftState !== "ready"
                || !recoveryDiskChecked
                || noteDraftDisposition !== "already-saved") {
            feedback = "CLEAR BLOCKED // VERIFY JOURNAL FIRST";
            return false;
        }
        beginDraftClear();
        return true;
    }

    function beginDraftClear() {
        // Clearing is never part of the journal transaction. Only clear
        // after the journal has acknowledged success or disk proves it.
        draftState = "clearing";
        draftFile.setText(JSON.stringify(Draft.emptyDocument()) + "\n");
    }

    FileView {
        id: journalFile
        path: angel.storagePath
        watchChanges: false
        atomicWrites: true
        blockWrites: false
        printErrors: false

        onLoaded: angel.acceptLoaded(journalFile.text())
        onLoadFailed: function(error) {
            if (angel.writePhase !== "")
                return;
            angel.recoveryCheckPending = false;
            angel.recoveryDiskChecked = false;
            if (error === FileViewError.FileNotFound) {
                angel.document = Journal.emptyDocument();
                angel.storageState = "empty";
                angel.errorCode = "";
                angel.feedback = "JOURNAL EMPTY // READY TO RECORD";
            } else {
                angel.storageState = "error";
                angel.errorCode = "FILE_LOAD_FAILED";
                angel.feedback = "JOURNAL UNAVAILABLE // NO FILE CHANGES";
            }
        }
        onSaved: {
            // A late acknowledgment after watchdog expiry remains valid.
            if (angel.writePhase !== "journal" || angel.pendingDocument === null)
                return;
            saveWatchdog.stop();
            const kind = angel.pendingKind;
            const id = angel.pendingNoteId;
            angel.document = angel.pendingDocument;
            angel.pendingDocument = null;
            angel.pendingKind = "";
            angel.pendingNoteId = "";
            angel.writePhase = "";
            angel.storageState = angel.document.observations.length
                                 ? "ready" : "empty";
            angel.errorCode = "";
            angel.feedback = "SAVED TO LOCAL JOURNAL";
            if (kind === "note") {
                angel.noteSaved(id);
                angel.beginDraftClear();
            }
        }
        onSaveFailed: function(error) {
            if (angel.writePhase !== "journal")
                return;
            // Failed journal writes never delete the already-saved note draft.
            saveWatchdog.stop();
            const kind = angel.pendingKind;
            const id = angel.pendingNoteId;
            angel.pendingDocument = null;
            angel.pendingKind = "";
            angel.pendingNoteId = "";
            angel.writePhase = "";
            angel.storageState = "error";
            angel.errorCode = "FILE_SAVE_FAILED";
            angel.feedback = "SAVE FAILED // LAST CONFIRMED DATA RETAINED";
            if (kind === "note")
                angel.noteSaveFailed(id, "FILE_SAVE_FAILED");
        }
    }

    // The draft file is a small independent atomic checkpoint, not a second
    // observation journal. It must acknowledge before any note journal write.
    FileView {
        id: draftFile
        path: angel.draftPath
        watchChanges: false
        atomicWrites: true
        blockWrites: false
        printErrors: false

        onLoaded: angel.acceptDraftLoaded(draftFile.text())
        onLoadFailed: function(error) {
            if (angel.draftState === "writing" || angel.draftState === "clearing")
                return;
            if (error === FileViewError.FileNotFound) {
                angel.noteDraft = null;
                angel.draftState = "empty";
            } else {
                angel.draftState = "error";
                angel.errorCode = "DRAFT_LOAD_FAILED";
                angel.feedback = "DRAFT UNAVAILABLE // NO FILE CHANGES";
            }
        }
        onSaved: {
            if (angel.draftState === "writing" && angel.writePhase === "draft"
                    && angel.pendingDocument !== null) {
                angel.noteDraft = angel.pendingNoteDraft;
                angel.pendingNoteDraft = null;
                angel.draftState = "ready";
                // This is the FIRST moment a new note has a durable recovery
                // checkpoint. Now start the original journal's atomic write.
                const next = angel.pendingDocument;
                const id = angel.pendingNoteId;
                angel.beginJournalWrite(next, "note", id);
            } else if (angel.draftState === "clearing") {
                angel.noteDraft = null;
                angel.draftState = "empty";
                angel.feedback = "SAVED TO LOCAL JOURNAL";
            }
        }
        onSaveFailed: function(error) {
            if (angel.draftState === "writing" && angel.writePhase === "draft") {
                saveWatchdog.stop();
                const id = angel.pendingNoteId;
                angel.pendingDocument = null;
                angel.pendingNoteDraft = null;
                angel.pendingKind = "";
                angel.pendingNoteId = "";
                angel.writePhase = "";
                angel.storageState = "error";
                angel.draftState = "error";
                angel.errorCode = "DRAFT_SAVE_FAILED";
                angel.feedback = "NOTE NOT SAVED // KEEP TEXT AND CHECK DISK";
                angel.noteSaveFailed(id, "DRAFT_SAVE_FAILED");
            } else if (angel.draftState === "clearing") {
                // Main journal save already succeeded. Keep the draft
                // available, require explicit check before clearing.
                angel.draftState = "ready";
                angel.feedback = "NOTE SAVED // DRAFT CLEANUP NEEDS REVIEW";
            }
        }
    }

    Timer {
        id: saveWatchdog
        interval: 12000
        repeat: false
        onTriggered: {
            if (angel.writePhase === "")
                return;
            // Timeout does NOT imply failure and never permits a retry.
            // A FileView worker might still commit; keep the transaction
            // and original draft until an acknowledgment or process restart.
            angel.storageState = "stalled";
            angel.errorCode = "SAVE_ACK_TIMEOUT";
            angel.feedback = "WRITE STALLED // NO RETRY // RESTART TO RECOVER";
            if (angel.pendingKind === "note")
                angel.noteSaveFailed(angel.pendingNoteId, "SAVE_ACK_TIMEOUT");
        }
    }
}
