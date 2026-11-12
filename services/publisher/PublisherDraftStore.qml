pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import "PublisherDraftPolicy.js" as Policy

// P1 local-only draft writer. No provider auth, publishing or background queue.
// The Social identity selector is NOT permission to access another account.
Scope {
    id: drafts

    readonly property string storagePath:
        Quickshell.dataDir + "/publisher-drafts-v1.json"
    property string storageState: "loading"
    property string errorCode: ""
    property string actionError: ""
    property var document: Policy.emptyDocument()
    property var pendingDocument: null
    readonly property var snapshot: Policy.view(storageState, document, errorCode)
    signal savedSuccessfully(string draftId)
    property string pendingDraftId: ""

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
        draftFile.reload();
        return true;
    }
    function saveDraft(id, title, body) {
        if ((storageState !== "ready" && storageState !== "empty")
                || pendingDocument !== null) {
            actionError = "STORAGE_NOT_WRITABLE";
            return false;
        }
        var result = Policy.saveDraft(document, id, title, body, Date.now());
        if (!result.ok) {
            actionError = result.reason;
            return false;
        }
        pendingDocument = result.document;
        pendingDraftId = result.draftId;
        storageState = "saving";
        actionError = "";
        draftFile.setText(JSON.stringify(pendingDocument, null, 2) + "\n");
        return true; // Request admitted, NOT yet saved.
    }

    FileView {
        id: draftFile
        path: drafts.storagePath
        watchChanges: false
        atomicWrites: true
        blockWrites: false
        printErrors: false

        onLoaded: drafts.acceptLoaded(draftFile.text())
        onLoadFailed: function(error) {
            if (drafts.storageState === "saving") return;
            if (error === FileViewError.FileNotFound) {
                drafts.document = Policy.emptyDocument();
                drafts.storageState = "empty";
                drafts.errorCode = "";
            } else {
                drafts.storageState = "error";
                drafts.errorCode = "FILE_LOAD_FAILED";
            }
        }
        onSaved: {
            if (drafts.storageState !== "saving" || !drafts.pendingDocument)
                return;
            drafts.document = drafts.pendingDocument;
            drafts.pendingDocument = null;
            drafts.storageState = "ready";
            drafts.errorCode = "";
            var savedId = drafts.pendingDraftId;
            drafts.pendingDraftId = "";
            drafts.savedSuccessfully(savedId);
        }
        onSaveFailed: function(error) {
            drafts.pendingDocument = null;
            drafts.pendingDraftId = "";
            drafts.storageState = "error";
            drafts.errorCode = "FILE_SAVE_FAILED";
            drafts.actionError = "FILE_SAVE_FAILED";
        }
    }
}
