pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import "FavoritesDefaultPolicy.js" as Policy

// U1 local default writer for NEW providers only. Never touches existing
// AppControl / Weather / Time / Places / Notifications / Hospital / RADIO data.
// No provider execution, migration, personal/org scope or desktop activation.
Scope {
    id: root

    readonly property string storagePath:
        Quickshell.dataDir + "/favorites-default-v1.json"
    property string storageState: "loading"
    property string errorCode: ""
    property string lastResultCode: ""
    property var document: Policy.empty()
    property var pendingDocument: null
    property var queuedDocument: null

    readonly property var visibleDocument:
        queuedDocument !== null ? queuedDocument
        : pendingDocument !== null ? pendingDocument : document
    readonly property var favoriteKeys: visibleDocument.favorites
    readonly property var pinnedKeys: visibleDocument.pins
    readonly property int revision: visibleDocument.revision
    readonly property int savedRevision: document.revision
    readonly property bool canEdit:
        storageState === "ready" || storageState === "empty"
        || storageState === "saving"
    readonly property bool busy: storageState === "saving"

    signal favoritesLoaded()
    signal favoritesSaved(int revision)
    signal favoritesSaveFailed(string reason)

    function acceptsKey(key) {
        return Policy.checkKey(key).ok;
    }

    function isFavorite(key) {
        return Policy.contains(visibleDocument,"favorite",key);
    }

    function isPinned(key) {
        return Policy.contains(visibleDocument,"pin",key);
    }

    function startWrite(next) {
        pendingDocument = next;
        queuedDocument = null;
        storageState = "saving";
        lastResultCode = "SAVING";
        // Dispatch in the next event-loop turn, not from FileView.onSaved or
        // a nested consumer callback. Rapid taps coalesce before this write.
        writeDispatchTimer.start();
    }

    function requestFeature(feature,key,enabled) {
        if (!canEdit) {
            lastResultCode = "STORE_UNAVAILABLE";
            return false;
        }
        const result = Policy.setFeature(visibleDocument,feature,key,enabled);
        if (!result.ok) {
            lastResultCode = result.reason;
            return false;
        }
        if (!result.changed) {
            lastResultCode = "UNCHANGED";
            return true;
        }
        errorCode = "";
        if (pendingDocument !== null) {
            // Only the latest uncommitted document survives rapid UI taps.
            // One FileView write in flight; next revision is serialized later.
            queuedDocument = result.document;
            lastResultCode = "QUEUED";
        } else {
            startWrite(result.document);
        }
        // True means accepted into the bounded save queue, NOT durable.
        return true;
    }

    function setFavorite(key,enabled) {
        return requestFeature("favorite",key,enabled);
    }

    function toggleFavorite(key) {
        return setFavorite(key,!isFavorite(key));
    }

    function setPinned(key,enabled) {
        return requestFeature("pin",key,enabled);
    }

    function togglePinned(key) {
        return setPinned(key,!isPinned(key));
    }

    function acceptLoaded(raw) {
        if (storageState === "saving")
            return;
        const result = Policy.parse(raw);
        if (!result.ok) {
            pendingDocument = null;
            queuedDocument = null;
            storageState = result.reason === "UNSUPPORTED_VERSION"
                ? "unsupported" : "error";
            errorCode = result.reason;
            lastResultCode = result.reason;
            // Never repair or overwrite unreadable/unknown-version files.
            return;
        }
        document = result.document;
        pendingDocument = null;
        queuedDocument = null;
        errorCode = "";
        lastResultCode = "";
        storageState = "ready";
        favoritesLoaded();
    }

    Timer {
        id: writeDispatchTimer
        interval: 0
        repeat: false
        onTriggered: {
            if (root.storageState !== "saving"
                    || root.pendingDocument === null)
                return;
            preferencesFile.setText(JSON.stringify(root.pendingDocument,null,2)
                                    + "\n");
        }
    }

    FileView {
        id: preferencesFile
        path: root.storagePath
        atomicWrites: true
        watchChanges: false
        blockWrites: false
        printErrors: false

        onLoaded: root.acceptLoaded(preferencesFile.text())

        onLoadFailed: function(error) {
            if (root.storageState === "saving")
                return;
            root.pendingDocument = null;
            root.queuedDocument = null;
            if (error === FileViewError.FileNotFound) {
                root.document = Policy.empty();
                root.errorCode = "";
                root.lastResultCode = "";
                root.storageState = "empty";
                root.favoritesLoaded();
            } else {
                root.errorCode = "FILE_LOAD_FAILED";
                root.lastResultCode = root.errorCode;
                root.storageState = "error";
            }
        }

        onSaved: {
            if (root.storageState !== "saving"
                    || root.pendingDocument === null)
                return;
            const saved = root.pendingDocument;
            const waiting = root.queuedDocument;
            root.document = saved;
            root.pendingDocument = null;
            root.queuedDocument = null;
            root.errorCode = "";
            if (waiting !== null) {
                root.startWrite(waiting);
            } else {
                root.storageState = "ready";
                root.lastResultCode = "SAVED";
            }
            root.favoritesSaved(saved.revision);
        }

        onSaveFailed: function(error) {
            root.pendingDocument = null;
            root.queuedDocument = null;
            root.storageState = "error";
            root.errorCode = "FILE_SAVE_FAILED";
            root.lastResultCode = root.errorCode;
            // In-memory confirmed state remains last successful write.
            // No optimistic success, silent retry or destructive repair.
            root.favoritesSaveFailed(root.errorCode);
        }
    }
}
