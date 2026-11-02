import QtQuick
import Quickshell
import Quickshell.Io
import "WeatherPersistentCachePolicy.js" as CachePolicy
import "WeatherRuntimePolicy.js" as RuntimePolicy

// One writer for Weather Station's reboot-surviving last-known cache.
// This store is operational fallback only. It is NOT Weather history,
// event dossiers, a provider fetcher, or a source of truth newer than live data.
Scope {
    id: cache

    readonly property string storagePath:
        Quickshell.dataDir + "/weather-last-known-v1.json"

    property string storageState: "loading"
    property string errorCode: ""
    property var document: CachePolicy.initialDocument()
    property var pendingDocument: null
    property var queuedDocument: null
    property var deferredUpdates: ({})

    readonly property int revision:
        document && Number.isSafeInteger(Number(document.revision))
        ? Number(document.revision) : 0

    signal recordSaved(string sourceId)

    function record(sourceId, nowMs, scopeKey) {
        if (storageState !== "ready" && storageState !== "empty")
            return null;

        const saved = CachePolicy.record(document, sourceId);
        if (!saved)
            return null;

        const expectedScope = String(scopeKey || "");
        if (expectedScope !== ""
                && String(saved.scopeKey || "") !== expectedScope)
            return null;

        const spec = RuntimePolicy.sourceSpec(sourceId);
        const expireMs = spec ? Number(spec.expireMs) || 0 : 0;
        const now = Number(nowMs);
        if (!isFinite(now) || now <= 0 || expireMs <= 0)
            return null;

        const age = Math.max(0, now - Number(saved.receivedAtMs));
        return age <= expireMs ? saved : null;
    }

    function acceptLoaded(raw) {
        if (storageState === "saving")
            return;

        const result = CachePolicy.parse(raw);
        if (!result.ok) {
            document = CachePolicy.initialDocument();
            pendingDocument = null;
            queuedDocument = null;
            deferredUpdates = ({});
            storageState = result.reason === "UNSUPPORTED_VERSION"
                           ? "unsupported" : "error";
            errorCode = result.reason;
            return;
        }

        document = result.document;
        storageState = Object.keys(document.records).length > 0
                       ? "ready" : "empty";
        errorCode = "";
        Qt.callLater(cache.applyDeferredUpdates);
    }

    function deferRecord(
        sourceId, receivedAtMs, payload, savedAtMs,
        scopeKey, requestKey
    ) {
        const record = CachePolicy.normalizeRecord(sourceId, {
            "receivedAtMs": receivedAtMs,
            "savedAtMs": savedAtMs,
            "scopeKey": scopeKey,
            "requestKey": requestKey,
            "payload": payload
        });
        if (!record)
            return false;

        const next = ({});
        const keys = Object.keys(deferredUpdates);
        for (let i = 0; i < keys.length; i++)
            next[keys[i]] = deferredUpdates[keys[i]];
        next[String(sourceId)] = record;
        deferredUpdates = next;
        return true;
    }

    function workingDocument() {
        if (queuedDocument)
            return queuedDocument;
        if (pendingDocument)
            return pendingDocument;
        return document;
    }

    function put(
        sourceId, receivedAtMs, payload,
        scopeKey, requestKey
    ) {
        const now = Date.now();

        if (storageState === "loading")
            return deferRecord(
                sourceId, receivedAtMs, payload, now,
                scopeKey, requestKey
            );

        if (storageState !== "ready"
                && storageState !== "empty"
                && storageState !== "saving")
            return false;

        const result = CachePolicy.upsert(
            workingDocument(),
            sourceId,
            receivedAtMs,
            payload,
            now,
            scopeKey,
            requestKey
        );
        if (!result.ok)
            return false;

        queuedDocument = result.document;
        if (storageState !== "saving")
            Qt.callLater(cache.flushQueued);
        return true;
    }

    function applyDeferredUpdates() {
        if ((storageState !== "ready" && storageState !== "empty")
                || Object.keys(deferredUpdates).length === 0)
            return false;

        const updates = deferredUpdates;
        deferredUpdates = ({});
        const ids = Object.keys(updates).sort();
        let base = document;

        for (let i = 0; i < ids.length; i++) {
            const record = updates[ids[i]];
            const result = CachePolicy.upsert(
                base,
                ids[i],
                record.receivedAtMs,
                record.payload,
                record.savedAtMs,
                record.scopeKey,
                record.requestKey
            );
            if (!result.ok) {
                storageState = "error";
                errorCode = "DEFERRED_UPDATE_INVALID";
                queuedDocument = null;
                return false;
            }
            base = result.document;
        }

        queuedDocument = base;
        Qt.callLater(cache.flushQueued);
        return true;
    }

    function flushQueued() {
        if (!queuedDocument
                || (storageState !== "ready" && storageState !== "empty"))
            return false;

        pendingDocument = queuedDocument;
        queuedDocument = null;
        storageState = "saving";
        errorCode = "";

        cacheFile.setText(
            JSON.stringify(pendingDocument, null, 2) + "\n"
        );
        return true;
    }

    FileView {
        id: cacheFile

        path: cache.storagePath
        watchChanges: false
        atomicWrites: true
        blockWrites: false
        printErrors: false

        onLoaded: cache.acceptLoaded(cacheFile.text())

        onLoadFailed: function(error) {
            if (cache.storageState === "saving")
                return;

            if (error === FileViewError.FileNotFound) {
                cache.document = CachePolicy.initialDocument();
                cache.storageState = "empty";
                cache.errorCode = "";
                Qt.callLater(cache.applyDeferredUpdates);
            } else {
                cache.document = CachePolicy.initialDocument();
                cache.deferredUpdates = ({});
                cache.storageState = "error";
                cache.errorCode = "FILE_LOAD_FAILED";
            }
        }

        onSaved: {
            if (cache.storageState !== "saving" || !cache.pendingDocument)
                return;

            const savedDocument = cache.pendingDocument;
            cache.document = savedDocument;
            cache.pendingDocument = null;
            cache.storageState = Object.keys(savedDocument.records).length > 0
                                 ? "ready" : "empty";
            cache.errorCode = "";

            const ids = Object.keys(savedDocument.records);
            for (let i = 0; i < ids.length; i++)
                cache.recordSaved(ids[i]);

            if (cache.queuedDocument)
                Qt.callLater(cache.flushQueued);
        }

        onSaveFailed: function(error) {
            cache.pendingDocument = null;
            cache.queuedDocument = null;
            cache.deferredUpdates = ({});
            cache.storageState = "error";
            cache.errorCode = "FILE_SAVE_FAILED";
        }
    }
}
