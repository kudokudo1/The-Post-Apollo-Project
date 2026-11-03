import QtQuick
import Quickshell
import Quickshell.Io
import "WeatherPlaceCachePolicy.js" as Policy

// Single local writer for exact Home/Explore coordinates. The legacy
// weather-last-known-v1.json file remains untouched and unscoped.
Scope {
    id: placeCache

    readonly property string storagePath:
        Quickshell.dataDir + "/weather-place-last-known-v1.json"
    property string storageState: "loading"
    property string errorCode: ""
    property var document: Policy.initialDocument()
    property var pendingDocument: null
    property var queuedDocument: null
    property var deferredUpdates: []

    function record(kind, scopeKey, nowMs) {
        if (storageState !== "ready" && storageState !== "empty"
                && storageState !== "saving")
            return null;
        // Only the last atomically confirmed document is authoritative.
        return Policy.record(document, kind, scopeKey, nowMs);
    }

    function workingDocument() {
        if (queuedDocument)
            return queuedDocument;
        if (pendingDocument)
            return pendingDocument;
        return document;
    }

    function put(kind, scopeKey, receivedAtMs, provider, payload) {
        const validated = Policy.upsert(
            Policy.initialDocument(),kind,scopeKey,receivedAtMs,provider,payload
        );
        if (!validated.ok)
            return false;

        if (storageState === "loading") {
            if (deferredUpdates.length >= 64)
                return false;
            deferredUpdates = deferredUpdates.concat([{
                kind:kind,scopeKey:scopeKey,receivedAtMs:receivedAtMs,
                provider:provider,payload:validated.document.records[0].payload
            }]);
            return true;
        }
        if (storageState !== "ready" && storageState !== "empty"
                && storageState !== "saving")
            return false;

        const result = Policy.upsert(
            workingDocument(),kind,scopeKey,receivedAtMs,provider,payload
        );
        if (!result.ok)
            return false;
        queuedDocument = result.document;
        if (storageState !== "saving")
            Qt.callLater(placeCache.flushQueued);
        return true;
    }

    function acceptLoaded(raw) {
        if (storageState === "saving")
            return;
        const parsed = Policy.parse(raw);
        if (!parsed.ok) {
            pendingDocument = null;
            queuedDocument = null;
            deferredUpdates = [];
            errorCode = parsed.reason;
            storageState = parsed.reason === "UNSUPPORTED_VERSION"
                           ? "unsupported" : "error";
            return;
        }
        document = parsed.document;
        errorCode = "";
        storageState = document.records.length ? "ready" : "empty";
        Qt.callLater(placeCache.applyDeferredUpdates);
    }

    function applyDeferredUpdates() {
        if (storageState !== "ready" && storageState !== "empty")
            return false;
        if (!deferredUpdates.length)
            return true;
        const updates = deferredUpdates;
        deferredUpdates = [];
        let next = document;
        for (let i = 0; i < updates.length; i++) {
            const u = updates[i];
            const result = Policy.upsert(
                next,u.kind,u.scopeKey,u.receivedAtMs,u.provider,u.payload
            );
            if (!result.ok) {
                queuedDocument = null;
                errorCode = "DEFERRED_UPDATE_INVALID";
                storageState = "error";
                return false;
            }
            next = result.document;
        }
        queuedDocument = next;
        Qt.callLater(placeCache.flushQueued);
        return true;
    }

    function flushQueued() {
        if (!queuedDocument || (storageState !== "ready"
                                && storageState !== "empty"))
            return false;
        pendingDocument = queuedDocument;
        queuedDocument = null;
        errorCode = "";
        storageState = "saving";
        placeFile.setText(JSON.stringify(pendingDocument,null,2) + "\n");
        return true;
    }

    FileView {
        id: placeFile
        path: placeCache.storagePath
        watchChanges: false
        atomicWrites: true
        blockWrites: false
        printErrors: false

        onLoaded: placeCache.acceptLoaded(placeFile.text())

        onLoadFailed: function(error) {
            if (placeCache.storageState === "saving")
                return;
            if (error === FileViewError.FileNotFound) {
                placeCache.document = Policy.initialDocument();
                placeCache.errorCode = "";
                placeCache.storageState = "empty";
                Qt.callLater(placeCache.applyDeferredUpdates);
            } else {
                placeCache.pendingDocument = null;
                placeCache.queuedDocument = null;
                placeCache.deferredUpdates = [];
                placeCache.errorCode = "FILE_LOAD_FAILED";
                placeCache.storageState = "error";
            }
        }

        onSaved: {
            if (placeCache.storageState !== "saving"
                    || !placeCache.pendingDocument)
                return;
            const saved = placeCache.pendingDocument;
            placeCache.document = saved;
            placeCache.pendingDocument = null;
            placeCache.errorCode = "";
            placeCache.storageState = saved.records.length ? "ready" : "empty";
            if (placeCache.queuedDocument)
                Qt.callLater(placeCache.flushQueued);
        }

        onSaveFailed: function(error) {
            placeCache.pendingDocument = null;
            placeCache.queuedDocument = null;
            placeCache.deferredUpdates = [];
            placeCache.errorCode = "FILE_SAVE_FAILED";
            placeCache.storageState = "error";
        }
    }
}
