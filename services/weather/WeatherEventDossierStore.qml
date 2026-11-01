import QtQuick
import Quickshell
import Quickshell.Io
import "WeatherEventDossierPolicy.js" as DossierPolicy

// Explicit operator-saved MAP event dossiers.
// Public-source event metadata only; no automatic write loop and no secrets.
// The file is versioned, bounded and atomically replaced through FileView.
Scope {
    id: store

    readonly property string storagePath:
        Quickshell.dataDir + "/weather-event-dossiers-v1.json"

    property string storageState: "loading" // loading, empty, ready, saving, error
    property string errorCode: ""
    property var document: DossierPolicy.initialDocument()
    property var pendingDocument: null
    property string lastAction: ""
    readonly property var summary: DossierPolicy.summary(document)
    readonly property var recentDossiers: DossierPolicy.recent(document, 5)
    signal dossierSaved()
    signal archiveCleared()

    function acceptLoaded(raw) {
        if (storageState === "saving")
            return;
        const parsed = DossierPolicy.parse(raw);
        if (!parsed.ok) {
            document = DossierPolicy.initialDocument();
            storageState = "error";
            errorCode = parsed.reason;
            return;
        }
        document = parsed.document;
        storageState = parsed.empty ? "empty" : "ready";
        errorCode = "";
    }

    function stage(result, action) {
        if ((storageState !== "ready" && storageState !== "empty")
                || !result || result.ok !== true)
            return false;
        pendingDocument = result.document;
        lastAction = String(action || "");
        storageState = "saving";
        errorCode = "";
        dossierFile.setText(JSON.stringify(pendingDocument, null, 2) + "\n");
        return true;
    }

    function saveDossier(anchor, relations) {
        if (storageState !== "ready" && storageState !== "empty")
            return false;
        const result = DossierPolicy.addDossier(
            document, anchor, relations, Date.now()
        );
        if (!result.ok) {
            errorCode = result.reason;
            return false;
        }
        return stage(result, "save");
    }

    function clearArchive() {
        if (storageState !== "ready" && storageState !== "empty")
            return false;
        const result = DossierPolicy.clearDocument(document);
        if (!result.ok) {
            errorCode = result.reason;
            return false;
        }
        return stage(result, "clear");
    }

    function reloadFromDisk() {
        if (storageState === "saving")
            return false;
        storageState = "loading";
        errorCode = "";
        dossierFile.reload();
        return true;
    }

    FileView {
        id: dossierFile
        path: store.storagePath
        watchChanges: false
        atomicWrites: true
        blockWrites: false
        printErrors: false

        onLoaded: store.acceptLoaded(dossierFile.text())

        onLoadFailed: function(error) {
            if (store.storageState === "saving")
                return;
            if (error === FileViewError.FileNotFound) {
                store.document = DossierPolicy.initialDocument();
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
            store.storageState = store.document.dossiers.length > 0
                               ? "ready" : "empty";
            store.errorCode = "";
            const action = store.lastAction;
            store.lastAction = "";
            if (action === "save")
                store.dossierSaved();
            else if (action === "clear")
                store.archiveCleared();
        }

        onSaveFailed: function(error) {
            store.pendingDocument = null;
            store.lastAction = "";
            store.storageState = "error";
            store.errorCode = "FILE_SAVE_FAILED";
        }
    }
}
