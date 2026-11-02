import QtQuick
import Quickshell
import Quickshell.Io
import "WeatherDossierArchivePolicy.js" as DossierPolicy
import "../../widgets/weather/StationDossierSerializationPolicy.js" as DossierCodec

// M25 sole writer for an independent, explicitly requested dossier archive.
// Provider-native M19's store and file remain completely separate.
Scope {
    id: dossierArchive

    readonly property string storagePath:
        Quickshell.dataDir + "/weather-dossier-archive-v1.json"

    property string storageState: "loading"
    property string errorCode: ""
    property string lastResultCode: ""
    property string lastSourceId: ""
    property string lastEventId: ""
    property int lastSequence: 0

    property var document: DossierPolicy.empty()
    property var pendingDocument: null

    readonly property int revision:
        document && Number.isSafeInteger(document.revision)
        ? document.revision : 0

    signal dossierSaved(string sourceId, string eventId, int sequence)

    function eventCount(sourceId, eventId) {
        return DossierPolicy.countForEvent(
            document, sourceId, eventId, DossierCodec
        );
    }

    function latest(sourceId, eventId) {
        return DossierPolicy.latest(
            document, sourceId, eventId, DossierCodec
        );
    }

    function capture(staged, capturedAtMs) {
        // Explicit action only. No calls from component initialization,
        // provider refresh, data arrival or selected-event change.
        if (storageState !== "ready" && storageState !== "empty") {
            lastResultCode = storageState === "loading"
                ? "ARCHIVE_LOADING"
                : storageState === "saving" ? "ARCHIVE_BUSY"
                : "STORE_UNAVAILABLE";
            return false;
        }

        const result = DossierPolicy.append(
            document, staged, capturedAtMs, DossierCodec
        );
        if (!result.ok) {
            lastResultCode = result.reason;
            return false;
        }

        lastSourceId = staged.candidate.selectedEvent.sourceId;
        lastEventId = staged.candidate.selectedEvent.eventId;
        lastSequence = result.sequence;
        pendingDocument = result.document;
        lastResultCode = "SAVING";
        storageState = "saving";
        archiveFile.setText(JSON.stringify(result.document) + "\n");
        return true;
    }

    function acceptLoaded(raw) {
        if (storageState === "saving")
            return;
        const result = DossierPolicy.parse(raw, DossierCodec);
        if (!result.ok) {
            // Preserve the unreadable file, never overwrite it with 'empty'.
            document = DossierPolicy.empty();
            pendingDocument = null;
            storageState = result.reason === "UNSUPPORTED_VERSION"
                ? "unsupported" : "error";
            errorCode = result.reason;
            lastResultCode = result.reason;
            return;
        }
        document = result.document;
        pendingDocument = null;
        storageState = result.count > 0 ? "ready" : "empty";
        errorCode = "";
        lastResultCode = "";
    }

    FileView {
        id: archiveFile
        path: dossierArchive.storagePath
        atomicWrites: true
        watchChanges: false
        blockWrites: false
        printErrors: false

        onLoaded: dossierArchive.acceptLoaded(archiveFile.text())

        onLoadFailed: function(error) {
            if (dossierArchive.storageState === "saving")
                return;
            dossierArchive.pendingDocument = null;
            if (error === FileViewError.FileNotFound) {
                dossierArchive.document = DossierPolicy.empty();
                dossierArchive.storageState = "empty";
                dossierArchive.errorCode = "";
                dossierArchive.lastResultCode = "";
            } else {
                dossierArchive.document = DossierPolicy.empty();
                dossierArchive.storageState = "error";
                dossierArchive.errorCode = "FILE_LOAD_FAILED";
                dossierArchive.lastResultCode = dossierArchive.errorCode;
            }
        }

        onSaved: {
            if (dossierArchive.storageState !== "saving"
                    || !dossierArchive.pendingDocument)
                return;
            dossierArchive.document = dossierArchive.pendingDocument;
            dossierArchive.pendingDocument = null;
            dossierArchive.storageState = "ready";
            dossierArchive.errorCode = "";
            dossierArchive.lastResultCode = "SAVED";
            dossierArchive.dossierSaved(
                dossierArchive.lastSourceId,
                dossierArchive.lastEventId,
                dossierArchive.lastSequence
            );
        }

        onSaveFailed: function(error) {
            dossierArchive.pendingDocument = null;
            dossierArchive.storageState = "error";
            dossierArchive.errorCode = "FILE_SAVE_FAILED";
            dossierArchive.lastResultCode = dossierArchive.errorCode;
            // No retry or overwrite on uncertain outcome.
        }
    }
}
