pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import "PlacePolicy.js" as PlacePolicy

// One local writer for Home and temporary Explore location context.
// No inference, network fetch, weather-provider routing or alert-point edits.
Scope {
    id: registry

    readonly property string storagePath:
        Quickshell.dataDir + "/places-v1.json"

    property string storageState: "loading"
    property string errorCode: ""
    property var document: PlacePolicy.initialDocument()
    property var pendingDocument: null
    // Expiry is calculated against wall-clock milliseconds. It is never
    // reconstructed as a fresh duration after a Quickshell restart.
    property double clockMs: Date.now()

    readonly property var homePlace:
        document && document.home ? document.home : null
    readonly property bool hasHome: homePlace !== null
    readonly property bool canSaveHome:
        (storageState === "ready" || storageState === "empty")
        && pendingDocument === null
    readonly property bool canChangeExplore: canSaveHome && hasHome
    readonly property bool hasStoredExplore:
        document && document.explore !== null && document.explore !== undefined
    readonly property var activeExplore:
        PlacePolicy.activeExplore(document, clockMs)
    readonly property var effectivePlace:
        PlacePolicy.effectivePlace(document, clockMs)
    readonly property string contextKind:
        PlacePolicy.contextKind(document, clockMs)
    readonly property double remainingMs:
        activeExplore && activeExplore.expiresAtMs !== null
        ? Math.max(0, activeExplore.expiresAtMs - clockMs) : 0

    Timer {
        interval: 1000
        repeat: true
        // A finished timed exploration stops ticking. Its old persisted
        // record is ignored by effectivePlace after expiry and on restart.
        running: registry.activeExplore !== null
                 && registry.activeExplore.expiresAtMs !== null
        onTriggered: registry.clockMs = Date.now()
    }

    function acceptLoaded(raw) {
        if (storageState === "saving")
            return;
        const result = PlacePolicy.parse(raw);
        if (!result.ok) {
            errorCode = result.reason;
            storageState = result.reason === "UNSUPPORTED_VERSION"
                           ? "unsupported" : "error";
            return;
        }
        document = result.document;
        pendingDocument = null;
        clockMs = Date.now();
        errorCode = "";
        storageState = document.home || document.explore ? "ready" : "empty";
    }

    function beginWrite(result) {
        if (!result.ok) {
            errorCode = result.reason;
            return false;
        }
        pendingDocument = result.document;
        errorCode = "";
        storageState = "saving";
        placeFile.setText(JSON.stringify(pendingDocument, null, 2) + "\n");
        return true;
    }

    function saveHome(label, latitude, longitude) {
        if (!canSaveHome) {
            errorCode = "STORAGE_NOT_READY";
            return false;
        }
        return beginWrite(PlacePolicy.withHome(
            document, label, latitude, longitude
        ));
    }

    function exploreHere(label, latitude, longitude, durationKey) {
        if (!canChangeExplore) {
            errorCode = hasHome ? "STORAGE_NOT_READY" : "HOME_NOT_SET";
            return false;
        }
        clockMs = Date.now();
        return beginWrite(PlacePolicy.withExplore(
            document, label, latitude, longitude, durationKey, clockMs
        ));
    }

    function returnHome() {
        if (!canSaveHome) {
            errorCode = "STORAGE_NOT_READY";
            return false;
        }
        return beginWrite(PlacePolicy.withoutExplore(document));
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
            registry.clockMs = Date.now();
            registry.errorCode = "";
            registry.storageState = registry.document.home
                                     || registry.document.explore
                                     ? "ready" : "empty";
        }

        onSaveFailed: function(error) {
            registry.pendingDocument = null;
            registry.errorCode = "FILE_SAVE_FAILED";
            registry.storageState = "error";
        }
    }
}
