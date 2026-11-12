pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import "PublisherMediaPolicy.js" as Policy

// P1.2 one local metadata owner, separate from P1.1 draft text records.
// File references are never automatically opened, copied, moved or deleted.
Scope {
    id: registry
    readonly property string storagePath:
        Quickshell.dataDir + "/publisher-media-v1.json"
    property string storageState: "loading"
    property string errorCode: ""
    property string actionError: ""
    property var document: Policy.emptyDocument()
    property var pendingDocument: null
    property var pendingOperation: null
    readonly property var snapshot: Policy.view(storageState, document, errorCode)
    signal operationFinished(string kind, string draftId, string assetId)

    function acceptLoaded(raw) {
        if (storageState === "saving") return;
        var result = Policy.parse(raw);
        if (!result.ok) {
            storageState = result.reason === "UNSUPPORTED_VERSION"
                           ? "unsupported" : "error";
            errorCode = result.reason;
            return;
        }
        document = result.document;
        storageState = "ready";
        errorCode = "";
    }
    function reloadFromDisk() {
        if (storageState === "saving" || pendingDocument !== null)
            return false;
        storageState = "loading";
        errorCode = "";
        actionError = "";
        mediaFile.reload();
        return true;
    }
    function stage(result, kind) {
        if ((storageState !== "ready" && storageState !== "empty")
                || pendingDocument !== null) {
            actionError = "STORAGE_NOT_WRITABLE";
            return false;
        }
        if (!result || result.ok !== true) {
            actionError = result && result.reason
                          ? result.reason : "INVALID_ACTION";
            return false;
        }
        if (result.unchanged) {
            operationFinished(kind, result.draftId || "", result.assetId || "");
            actionError = "";
            return true;
        }
        pendingDocument = result.document;
        pendingOperation = {
            kind:kind, draftId:result.draftId || "",
            assetId:result.assetId || ""
        };
        storageState = "saving";
        actionError = "";
        mediaFile.setText(JSON.stringify(pendingDocument, null, 2) + "\n");
        return true; // Only request admission; onSaved confirms local FileView.
    }
    function registerMedia(info) {
        if (!snapshot.writable) {
            actionError = "STORAGE_NOT_WRITABLE";
            return false;
        }
        return stage(Policy.register(document, info, Date.now()), "registered");
    }
    function attachMedia(draftId, assetId) {
        if (!snapshot.writable) {
            actionError = "STORAGE_NOT_WRITABLE";
            return false;
        }
        return stage(Policy.attach(document, draftId, assetId), "attached");
    }
    function detachMedia(draftId, assetId) {
        if (!snapshot.writable) {
            actionError = "STORAGE_NOT_WRITABLE";
            return false;
        }
        return stage(Policy.detach(document, draftId, assetId), "detached");
    }

    FileView {
        id: mediaFile
        path: registry.storagePath
        watchChanges: false
        atomicWrites: true
        blockWrites: false
        printErrors: false
        onLoaded: registry.acceptLoaded(mediaFile.text())
        onLoadFailed: function(error) {
            if (registry.storageState === "saving") return;
            if (error === FileViewError.FileNotFound) {
                registry.document = Policy.emptyDocument();
                registry.storageState = "empty";
                registry.errorCode = "";
            } else {
                registry.storageState = "error";
                registry.errorCode = "FILE_LOAD_FAILED";
            }
        }
        onSaved: {
            if (registry.storageState !== "saving"
                    || !registry.pendingDocument || !registry.pendingOperation)
                return;
            registry.document = registry.pendingDocument;
            var completed = registry.pendingOperation;
            registry.pendingDocument = null;
            registry.pendingOperation = null;
            registry.storageState = "ready";
            registry.errorCode = "";
            registry.operationFinished(completed.kind, completed.draftId,
                                       completed.assetId);
        }
        onSaveFailed: function(error) {
            registry.pendingDocument = null;
            registry.pendingOperation = null;
            registry.storageState = "error";
            registry.actionError = "FILE_SAVE_FAILED";
            registry.errorCode = "FILE_SAVE_FAILED";
        }
    }
}
