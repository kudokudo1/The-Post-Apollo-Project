pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import "PublisherAccessIntentPolicy.js" as Policy

// An intent ledger, NOT an authorization store. QML cannot approve a grant.
// Connections/Identity owns future authenticated account and process evidence.
Scope {
    id: store
    readonly property string storagePath:
        Quickshell.dataDir + "/publisher-access-intents-v1.json"
    property string storageState: "loading"
    property string errorCode: ""
    property string actionError: ""
    property var document: Policy.emptyDocument()
    property var pendingDocument: null
    property string pendingIntentId: ""
    property string pendingAction: ""
    readonly property var snapshot: Policy.view(storageState,document,errorCode)
    readonly property bool canPublish: false
    signal actionCompleted(string action,string intentId)

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
        actionError = "";
        errorCode = "";
        intentsFile.reload();
        return true;
    }
    function apply(result,action) {
        if ((storageState !== "ready" && storageState !== "empty")
                || pendingDocument !== null) {
            actionError = "STORAGE_NOT_WRITABLE";
            return false;
        }
        if (!result || result.ok !== true) {
            actionError = result && result.reason ? result.reason : "INVALID_INTENT";
            return false;
        }
        actionError = "";
        if (result.unchanged) {
            actionCompleted("already_requested",result.intentId);
            return true;
        }
        pendingDocument = result.document;
        pendingIntentId = result.intentId;
        pendingAction = action;
        storageState = "saving";
        intentsFile.setText(JSON.stringify(pendingDocument,null,2) + "\n");
        return true; // Admission, NOT local FileView acknowledgment.
    }
    function requestAccess(identityId,context,provider,accountAlias,scope) {
        return apply(Policy.request(document,identityId,context,
                                   provider,accountAlias,scope,Date.now()),
                     "requested");
    }
    function withdrawRequest(id) {
        return apply(Policy.withdraw(document,id,Date.now()),"withdrawn");
    }
    function publishPermission(request,receipt) {
        // The only answer reachable from an untrusted QML/client path is DENY.
        return Policy.evaluate(request,receipt);
    }

    FileView {
        id: intentsFile
        path: store.storagePath
        watchChanges: false
        atomicWrites: true
        blockWrites: false
        printErrors: false
        onLoaded: store.acceptLoaded(intentsFile.text())
        onLoadFailed: function(error) {
            if (store.storageState === "saving") return;
            if (error === FileViewError.FileNotFound) {
                store.document = Policy.emptyDocument();
                store.storageState = "empty";
                store.errorCode = "";
            } else {
                store.storageState = "error";
                store.errorCode = "FILE_LOAD_FAILED";
            }
        }
        onSaved: {
            if (store.storageState !== "saving" || !store.pendingDocument)
                return;
            store.document = store.pendingDocument;
            store.pendingDocument = null;
            var action = store.pendingAction, id = store.pendingIntentId;
            store.pendingAction = "";
            store.pendingIntentId = "";
            store.storageState = "ready";
            store.errorCode = "";
            store.actionCompleted(action,id);
        }
        onSaveFailed: function(error) {
            store.pendingDocument = null;
            store.pendingAction = "";
            store.pendingIntentId = "";
            store.storageState = "error";
            store.errorCode = "FILE_SAVE_FAILED";
            store.actionError = "FILE_SAVE_FAILED";
        }
    }
}
