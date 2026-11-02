import QtQuick
import Quickshell
import Quickshell.Io
import "WeatherEventArchivePolicy.js" as ArchivePolicy

// One writer for durable, operator-requested Weather event evidence.
//
// This archive is not:
// - operational last-known cache;
// - M10 scalar live history;
// - radar/lightning frame cache;
// - automatic browsing history.
//
// Only an explicit operator archive request writes a source-native snapshot.
Scope {
    id: archive

    readonly property string storagePath:
        Quickshell.dataDir + "/weather-event-archive-v1.json"

    property string storageState: "loading"
    property string errorCode: ""
    property string lastResultCode: ""
    property string lastEventKey: ""
    property int lastSnapshotCount: 0

    property var document: ArchivePolicy.initialDocument()
    property var pendingDocument: null
    property var queuedDocument: null
    property var deferredRequests: []

    readonly property int revision: {
        const current = workingDocument();
        return current && Number.isSafeInteger(Number(current.revision))
            ? Number(current.revision) : 0;
    }

    signal snapshotSaved(string sourceId, string eventId, int count)

    function workingDocument() {
        if (queuedDocument)
            return queuedDocument;
        if (pendingDocument)
            return pendingDocument;
        return document;
    }

    function eventCount(nowMs) {
        return ArchivePolicy.eventCount(
            workingDocument(),
            Number(nowMs) > 0 ? Number(nowMs) : Date.now()
        );
    }

    function snapshotCount(sourceId, eventId, nowMs) {
        return ArchivePolicy.snapshotCount(
            workingDocument(),
            sourceId,
            eventId,
            Number(nowMs) > 0 ? Number(nowMs) : Date.now()
        );
    }

    function snapshots(sourceId, eventId, nowMs) {
        return ArchivePolicy.snapshots(
            workingDocument(),
            sourceId,
            eventId,
            Number(nowMs) > 0 ? Number(nowMs) : Date.now()
        );
    }

    function latest(sourceId, eventId, nowMs) {
        return ArchivePolicy.latest(
            workingDocument(),
            sourceId,
            eventId,
            Number(nowMs) > 0 ? Number(nowMs) : Date.now()
        );
    }

    function deferRequest(sourceId, row, capturedAtMs) {
        const next = deferredRequests.slice();
        next.push({
            "sourceId": String(sourceId || ""),
            "row": row,
            "capturedAtMs": Number(capturedAtMs)
        });
        if (next.length > 32)
            next.splice(0, next.length - 32);
        deferredRequests = next;
        lastResultCode = "QUEUED";
        return true;
    }

    function archiveEvent(sourceId, row) {
        const now = Date.now();

        if (storageState === "loading")
            return deferRequest(sourceId, row, now);

        if (storageState !== "ready"
                && storageState !== "empty"
                && storageState !== "saving") {
            lastResultCode = "STORE_UNAVAILABLE";
            return false;
        }

        const result = ArchivePolicy.append(
            workingDocument(), sourceId, row, now
        );
        if (!result.ok) {
            lastResultCode = result.reason || "ARCHIVE_REJECTED";
            lastEventKey = "";
            lastSnapshotCount = 0;
            return false;
        }

        lastEventKey = result.eventKey;
        lastSnapshotCount = result.count;
        if (!result.changed) {
            lastResultCode = result.duplicate ? "UNCHANGED" : "NO_CHANGE";
            return true;
        }

        queuedDocument = result.document;
        lastResultCode = "QUEUED";
        if (storageState !== "saving")
            Qt.callLater(archive.flushQueued);
        return true;
    }

    function applyDeferredRequests() {
        if ((storageState !== "ready" && storageState !== "empty")
                || deferredRequests.length === 0)
            return false;

        const pending = deferredRequests.slice();
        deferredRequests = [];
        let base = document;
        let changed = false;
        let finalKey = "";
        let finalCount = 0;

        for (let i = 0; i < pending.length; i++) {
            const row = pending[i];
            const result = ArchivePolicy.append(
                base,
                row.sourceId,
                row.row,
                row.capturedAtMs
            );
            if (!result.ok) {
                storageState = "error";
                errorCode = "DEFERRED_ARCHIVE_INVALID";
                queuedDocument = null;
                lastResultCode = errorCode;
                return false;
            }
            base = result.document;
            changed = changed || result.changed;
            finalKey = result.eventKey;
            finalCount = result.count;
        }

        lastEventKey = finalKey;
        lastSnapshotCount = finalCount;
        if (!changed) {
            lastResultCode = "UNCHANGED";
            return true;
        }

        queuedDocument = base;
        lastResultCode = "QUEUED";
        Qt.callLater(archive.flushQueued);
        return true;
    }

    function acceptLoaded(raw) {
        if (storageState === "saving")
            return;

        const result = ArchivePolicy.parse(raw, Date.now());
        if (!result.ok) {
            document = ArchivePolicy.initialDocument();
            pendingDocument = null;
            queuedDocument = null;
            deferredRequests = [];
            storageState = result.reason === "UNSUPPORTED_VERSION"
                           ? "unsupported" : "error";
            errorCode = result.reason;
            lastResultCode = result.reason;
            return;
        }

        document = result.document;
        storageState = Object.keys(document.events).length > 0
                       ? "ready" : "empty";
        errorCode = "";
        lastResultCode = "";
        Qt.callLater(archive.applyDeferredRequests);
    }

    function flushQueued() {
        if (!queuedDocument
                || (storageState !== "ready" && storageState !== "empty"))
            return false;

        pendingDocument = queuedDocument;
        queuedDocument = null;
        storageState = "saving";
        errorCode = "";

        archiveFile.setText(
            JSON.stringify(pendingDocument, null, 2) + "\n"
        );
        return true;
    }

    FileView {
        id: archiveFile

        path: archive.storagePath
        watchChanges: false
        atomicWrites: true
        blockWrites: false
        printErrors: false

        onLoaded: archive.acceptLoaded(archiveFile.text())

        onLoadFailed: function(error) {
            if (archive.storageState === "saving")
                return;

            if (error === FileViewError.FileNotFound) {
                archive.document = ArchivePolicy.initialDocument();
                archive.storageState = "empty";
                archive.errorCode = "";
                archive.lastResultCode = "";
                Qt.callLater(archive.applyDeferredRequests);
            } else {
                archive.document = ArchivePolicy.initialDocument();
                archive.deferredRequests = [];
                archive.storageState = "error";
                archive.errorCode = "FILE_LOAD_FAILED";
                archive.lastResultCode = archive.errorCode;
            }
        }

        onSaved: {
            if (archive.storageState !== "saving"
                    || !archive.pendingDocument)
                return;

            const savedDocument = archive.pendingDocument;
            archive.document = savedDocument;
            archive.pendingDocument = null;
            archive.storageState =
                Object.keys(savedDocument.events).length > 0
                ? "ready" : "empty";
            archive.errorCode = "";
            archive.lastResultCode = "SAVED";

            if (archive.lastEventKey) {
                const splitAt = archive.lastEventKey.indexOf("|");
                const sourceId = splitAt > 0
                    ? archive.lastEventKey.slice(0, splitAt) : "";
                const eventId = splitAt > 0
                    ? archive.lastEventKey.slice(splitAt + 1) : "";
                if (sourceId && eventId) {
                    archive.snapshotSaved(
                        sourceId,
                        eventId,
                        archive.lastSnapshotCount
                    );
                }
            }

            if (archive.queuedDocument)
                Qt.callLater(archive.flushQueued);
        }

        onSaveFailed: function(error) {
            archive.pendingDocument = null;
            archive.queuedDocument = null;
            archive.deferredRequests = [];
            archive.storageState = "error";
            archive.errorCode = "FILE_SAVE_FAILED";
            archive.lastResultCode = archive.errorCode;
        }
    }
}
