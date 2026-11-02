import QtQuick
import Quickshell
import Quickshell.Io
import "WeatherLiveHistoryPolicy.js" as HistoryPolicy

// One writer for bounded Weather live history.
//
// This is chronology, not operational fallback:
// - no provider fetches
// - no timers
// - no forecasts
// - no radar/lightning frame archive
// - no NWS/USGS/GDACS duplication where upstream already supplies history
Scope {
    id: history

    readonly property string storagePath:
        Quickshell.dataDir + "/weather-live-history-v1.json"

    property string storageState: "loading"
    property string errorCode: ""
    property var document: HistoryPolicy.initialDocument()
    property var pendingDocument: null
    property var queuedDocument: null
    property var deferredSamples: []

    readonly property int revision:
        document && Number.isSafeInteger(Number(document.revision))
        ? Number(document.revision) : 0

    signal sampleSaved(string sourceId)

    function samples(sourceId, scopeKey, nowMs) {
        if (storageState !== "ready" && storageState !== "empty"
                && storageState !== "saving")
            return [];
        return HistoryPolicy.samples(
            workingDocument(), sourceId, scopeKey, nowMs
        );
    }

    function count(sourceId, scopeKey, nowMs) {
        return samples(sourceId, scopeKey, nowMs).length;
    }

    function latest(sourceId, scopeKey, nowMs) {
        const rows = samples(sourceId, scopeKey, nowMs);
        return rows.length > 0 ? rows[rows.length - 1] : null;
    }

    function trend(sourceId, scopeKey, field, nowMs) {
        return HistoryPolicy.numericTrend(
            workingDocument(), sourceId, scopeKey, field, nowMs
        );
    }

    function workingDocument() {
        if (queuedDocument)
            return queuedDocument;
        if (pendingDocument)
            return pendingDocument;
        return document;
    }

    function deferSample(
        sourceId, scopeKey, observedAtMs,
        receivedAtMs, payload, savedAtMs
    ) {
        const row = {
            "sourceId": String(sourceId || ""),
            "scopeKey": String(scopeKey || ""),
            "observedAtMs": Number(observedAtMs),
            "receivedAtMs": Number(receivedAtMs),
            "payload": payload,
            "savedAtMs": Number(savedAtMs)
        };
        const next = deferredSamples.slice();
        next.push(row);
        // A pathological startup storm should not create an unbounded queue.
        if (next.length > 64)
            next.splice(0, next.length - 64);
        deferredSamples = next;
        return true;
    }

    function append(
        sourceId, scopeKey, observedAtMs, receivedAtMs, payload
    ) {
        const now = Date.now();

        if (storageState === "loading") {
            return deferSample(
                sourceId, scopeKey, observedAtMs,
                receivedAtMs, payload, now
            );
        }

        if (storageState !== "ready"
                && storageState !== "empty"
                && storageState !== "saving")
            return false;

        const result = HistoryPolicy.append(
            workingDocument(),
            sourceId,
            scopeKey,
            observedAtMs,
            receivedAtMs,
            payload,
            now
        );
        if (!result.ok)
            return false;

        queuedDocument = result.document;
        if (storageState !== "saving")
            Qt.callLater(history.flushQueued);
        return true;
    }

    function applyDeferredSamples() {
        if ((storageState !== "ready" && storageState !== "empty")
                || deferredSamples.length === 0)
            return false;

        const pending = deferredSamples.slice();
        deferredSamples = [];
        let base = document;

        for (let i = 0; i < pending.length; i++) {
            const row = pending[i];
            const result = HistoryPolicy.append(
                base,
                row.sourceId,
                row.scopeKey,
                row.observedAtMs,
                row.receivedAtMs,
                row.payload,
                row.savedAtMs
            );
            if (!result.ok) {
                storageState = "error";
                errorCode = "DEFERRED_SAMPLE_INVALID";
                queuedDocument = null;
                return false;
            }
            base = result.document;
        }

        queuedDocument = base;
        Qt.callLater(history.flushQueued);
        return true;
    }

    function acceptLoaded(raw) {
        if (storageState === "saving")
            return;

        const result = HistoryPolicy.parse(raw, Date.now());
        if (!result.ok) {
            document = HistoryPolicy.initialDocument();
            pendingDocument = null;
            queuedDocument = null;
            deferredSamples = [];
            storageState = result.reason === "UNSUPPORTED_VERSION"
                           ? "unsupported" : "error";
            errorCode = result.reason;
            return;
        }

        document = result.document;
        storageState = Object.keys(document.series).length > 0
                       ? "ready" : "empty";
        errorCode = "";
        Qt.callLater(history.applyDeferredSamples);
    }

    function flushQueued() {
        if (!queuedDocument
                || (storageState !== "ready" && storageState !== "empty"))
            return false;

        pendingDocument = queuedDocument;
        queuedDocument = null;
        storageState = "saving";
        errorCode = "";

        historyFile.setText(
            JSON.stringify(pendingDocument, null, 2) + "\n"
        );
        return true;
    }

    FileView {
        id: historyFile

        path: history.storagePath
        watchChanges: false
        atomicWrites: true
        blockWrites: false
        printErrors: false

        onLoaded: history.acceptLoaded(historyFile.text())

        onLoadFailed: function(error) {
            if (history.storageState === "saving")
                return;

            if (error === FileViewError.FileNotFound) {
                history.document = HistoryPolicy.initialDocument();
                history.storageState = "empty";
                history.errorCode = "";
                Qt.callLater(history.applyDeferredSamples);
            } else {
                history.document = HistoryPolicy.initialDocument();
                history.deferredSamples = [];
                history.storageState = "error";
                history.errorCode = "FILE_LOAD_FAILED";
            }
        }

        onSaved: {
            if (history.storageState !== "saving"
                    || !history.pendingDocument)
                return;

            const savedDocument = history.pendingDocument;
            history.document = savedDocument;
            history.pendingDocument = null;
            history.storageState =
                Object.keys(savedDocument.series).length > 0
                ? "ready" : "empty";
            history.errorCode = "";

            const ids = Object.keys(savedDocument.series);
            for (let i = 0; i < ids.length; i++)
                history.sampleSaved(ids[i]);

            if (history.queuedDocument)
                Qt.callLater(history.flushQueued);
        }

        onSaveFailed: function(error) {
            history.pendingDocument = null;
            history.queuedDocument = null;
            history.deferredSamples = [];
            history.storageState = "error";
            history.errorCode = "FILE_SAVE_FAILED";
        }
    }
}
