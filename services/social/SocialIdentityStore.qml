pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import "SocialIdentityPolicy.js" as IdentityPolicy

// Single writer for Social identity ORGANIZATION metadata. Sessions, browser
// profiles, QR pairing, secret storage and live account switching stay separate.
// Missing config is an in-memory default; disk writes need an explicit action.
Scope {
    id: identities

    readonly property string storagePath:
        Quickshell.dataDir + "/social-identities-v1.json"

    property string storageState: "loading"
    property string errorCode: ""
    property var document: IdentityPolicy.initialDocument()
    property var pendingDocument: null
    readonly property var snapshot:
        IdentityPolicy.view(storageState, document, errorCode)

    function acceptLoaded(raw) {
        if (storageState === "saving")
            return;
        const result = IdentityPolicy.parse(raw);
        if (!result.ok) {
            document = IdentityPolicy.initialDocument();
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
        if (storageState === "saving")
            return false;
        storageState = "loading";
        errorCode = "";
        identityFile.reload();
        return true;
    }

    function stage(result) {
        if ((storageState !== "ready" && storageState !== "empty")
                || !result || result.ok !== true)
            return false;
        pendingDocument = result.document;
        storageState = "saving";
        errorCode = "";
        // No optimistic visibility and no overwrite of invalid/newer schema.
        identityFile.setText(JSON.stringify(pendingDocument, null, 2) + "\n");
        return true;
    }

    function createIdentity(name, mode, copyFromId) {
        return stage(IdentityPolicy.create(
            document, name, mode, copyFromId));
    }

    // A UI layout preference only. The running service, native adapter and
    // browser profiles are deliberately NOT changed by this operation.
    function selectIdentity(id) {
        return stage(IdentityPolicy.select(document, id));
    }

    // User-clicked family header. Persist only the current identity layout;
    // no service, browser profile or account-session activation.
    function toggleFamily(familyId) {
        return stage(IdentityPolicy.toggleFamily(document, familyId));
    }

    FileView {
        id: identityFile
        path: identities.storagePath
        watchChanges: false
        atomicWrites: true
        blockWrites: false
        printErrors: false

        onLoaded: identities.acceptLoaded(identityFile.text())

        onLoadFailed: function(error) {
            if (identities.storageState === "saving")
                return;
            if (error === FileViewError.FileNotFound) {
                identities.document = IdentityPolicy.initialDocument();
                identities.storageState = "empty";
                identities.errorCode = "";
            } else {
                identities.storageState = "error";
                identities.errorCode = "FILE_LOAD_FAILED";
            }
        }

        onSaved: {
            if (identities.storageState !== "saving" || !identities.pendingDocument)
                return;
            identities.document = identities.pendingDocument;
            identities.pendingDocument = null;
            identities.storageState = "ready";
            identities.errorCode = "";
        }

        onSaveFailed: function(error) {
            identities.pendingDocument = null;
            identities.storageState = "error";
            identities.errorCode = "FILE_SAVE_FAILED";
        }
    }
}
