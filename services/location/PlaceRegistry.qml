pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import "PlacePolicy.js" as PlacePolicy

// One local writer for manually selected Home coordinates.
// Does not infer a location, route weather requests or mutate alert points.
Scope {
    id: registry

    readonly property string storagePath:
        Quickshell.dataDir + "/places-v1.json"

    property string storageState: "loading"
    property string errorCode: ""
    property var document: PlacePolicy.initialDocument()
    property var pendingDocument: null

    readonly property var homePlace:
        document && document.home ? document.home : null
    readonly property bool hasHome: homePlace !== null
    readonly property bool canSaveHome:
        (storageState === "ready" || storageState === "empty")
        && pendingDocument === null

    function acceptLoaded(raw) {
        if (storageState === "saving")
            return;
        const result = PlacePolicy.parse(raw);
        if (!result.ok) {
            storageState = result.reason === "UNSUPPORTED_VERSION"
                           ? "unsupported" : "error";
            errorCode = result.reason;
            return;
        }
        document = result.document;
        pendingDocument = null;
        storageState = document.home ? "ready" : "empty";
        errorCode = "";
    }

    function saveHome(label, latitude, longitude) {
        if (!canSaveHome) {
            errorCode = "STORAGE_NOT_READY";
            return false;
        }
        const result = PlacePolicy.withHome(
            document, label, latitude, longitude
        );
        if (!result.ok) {
            errorCode = result.reason;
            return false;
        }
        pendingDocument = result.document;
        storageState = "saving";
        errorCode = "";
        placeFile.setText(JSON.stringify(pendingDocument, null, 2) + "\n");
        return true;
    }

    FileView {
        id: placeFile
        path: registry.storagePath
        watchChanges: false
        atomicWrites: true
        blockWrites: false
        printErrors: false

        onLoaded: registry.acceptLoaded(placeFile.text())

        onLoadFailed: function(error) {
            if (registry.storageState === "saving")
                return;
            if (error === FileViewError.FileNotFound) {
                registry.document = PlacePolicy.initialDocument();
                registry.pendingDocument = null;
                registry.storageState = "empty";
                registry.errorCode = "";
            } else {
                registry.storageState = "error";
                registry.errorCode = "FILE_LOAD_FAILED";
            }
        }

        onSaved: {
            if (registry.storageState !== "saving"
                    || registry.pendingDocument === null)
                return;
            registry.document = registry.pendingDocument;
            registry.pendingDocument = null;
            registry.storageState = "ready";
            registry.errorCode = "";
        }

        onSaveFailed: function(error) {
            registry.pendingDocument = null;
            registry.storageState = "error";
            registry.errorCode = "FILE_SAVE_FAILED";
        }
    }
}
