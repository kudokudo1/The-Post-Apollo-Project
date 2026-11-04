pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import "AngelObservationPolicy.js" as Journal

// ANGEL owns one local observation journal. It is NOT the Notes, Tasks,
// Weather archives or a second host clock. Nothing writes until RECORD or
// a confirmed DELETE; no network, continuous polling, or auto-observation.
Scope {
    id: angel

    readonly property string storagePath:
        Quickshell.dataDir + "/angel-observations-v1.json"

    property string storageState: "loading"
    property string errorCode: ""
    property string feedback: "LOADING LOCAL OBSERVATIONS"
    property var document: Journal.emptyDocument()
    property var pendingDocument: null
    readonly property var observations: document.observations
    readonly property int total: observations.length
    readonly property bool writable:
        storageState === "ready" || storageState === "empty"

    function acceptLoaded(raw) {
        if (storageState === "saving")
            return;
        const loaded = Journal.parse(raw);
        if (!loaded.ok) {
            storageState = loaded.reason === "UNSUPPORTED_VERSION"
                           ? "unsupported" : "error";
            errorCode = loaded.reason;
            feedback = "JOURNAL INVALID // DATA PRESERVED ON DISK";
            return;
        }
        document = loaded.document;
        storageState = document.observations.length ? "ready" : "empty";
        errorCode = "";
        feedback = "JOURNAL READY // " + document.observations.length;
    }

    function reloadFromDisk() {
        if (storageState === "saving")
            return false;
        storageState = "loading";
        errorCode = "";
        feedback = "RELOADING JOURNAL";
        journalFile.reload();
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
        pendingDocument = next.document;
        storageState = "saving";
        errorCode = "";
        feedback = "WRITING // NOT YET SAVED";
        journalFile.setText(JSON.stringify(pendingDocument, null, 2) + "\n");
        return true;
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

    FileView {
        id: journalFile
        path: angel.storagePath
        watchChanges: false
        atomicWrites: true
        blockWrites: false
        printErrors: false

        onLoaded: angel.acceptLoaded(journalFile.text())
        onLoadFailed: function(error) {
            if (angel.storageState === "saving")
                return;
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
            if (angel.storageState !== "saving" || angel.pendingDocument === null)
                return;
            angel.document = angel.pendingDocument;
            angel.pendingDocument = null;
            angel.storageState = angel.document.observations.length
                                 ? "ready" : "empty";
            angel.errorCode = "";
            angel.feedback = "SAVED TO LOCAL JOURNAL";
        }
        onSaveFailed: function(error) {
            // Confirmed data stays intact. A failed new observation is never
            // displayed as persisted and cannot silently be retried.
            angel.pendingDocument = null;
            angel.storageState = "error";
            angel.errorCode = "FILE_SAVE_FAILED";
            angel.feedback = "SAVE FAILED // LAST CONFIRMED DATA RETAINED";
        }
    }
}
