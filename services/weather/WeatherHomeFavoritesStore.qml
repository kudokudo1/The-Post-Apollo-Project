import QtQuick
import Quickshell
import Quickshell.Io
import "WeatherHomeFavoritesPolicy.js" as FavoritePolicy

// W2b // The only Weather HOME bookmark writer. Completely independent
// from services/favorites/FavoritesStore.qml and appcontrol-favorites.json.
// Values are stable identities only, never measurement data or liveness.
Scope {
    id: store

    readonly property string storagePath:
        Quickshell.dataDir + "/weather-home-favorites-v1.json"

    property string storageState: "loading"
    property string errorCode: ""
    property string lastResultCode: ""
    property var document: FavoritePolicy.empty()
    property var pendingDocument: null

    readonly property var panelRoutes: document.panelRoutes
    readonly property var cardKeys: document.cardKeys
    readonly property int revision: document.revision
    readonly property bool writable:
        storageState === "ready" || storageState === "empty"

    signal favoritesLoaded()
    signal favoritesSaved(int revision)

    function acceptLoaded(raw) {
        if (storageState === "saving")
            return;
        const decoded = FavoritePolicy.parse(raw);
        if (!decoded.ok) {
            document = FavoritePolicy.empty();
            pendingDocument = null;
            errorCode = decoded.reason;
            lastResultCode = decoded.reason;
            storageState = decoded.reason === "UNSUPPORTED_VERSION"
                ? "unsupported" : "error";
            // The existing unreadable file is preserved and never repaired
            // or overwritten silently by this implementation.
            return;
        }
        document = decoded.document;
        pendingDocument = null;
        errorCode = "";
        lastResultCode = "";
        storageState = decoded.document.revision > 0 ? "ready" : "empty";
        favoritesLoaded();
    }

    function commitChange(result) {
        if (!writable) {
            lastResultCode = storageState === "saving"
                ? "STORE_BUSY" : "STORE_UNAVAILABLE";
            return false;
        }
        if (!result || !result.ok) {
            lastResultCode = result ? result.reason : "INVALID_CHANGE";
            return false;
        }
        if (!result.changed) {
            lastResultCode = "UNCHANGED";
            return true;
        }
        pendingDocument = result.document;
        storageState = "saving";
        lastResultCode = "SAVING";
        favoritesFile.setText(JSON.stringify(result.document, null, 2) + "\n");
        return true;
    }

    function replacePanelFavorites(routes) {
        // This is called only on an explicit FAVORITE button click.
        if (!writable) {
            lastResultCode = "STORE_UNAVAILABLE";
            return false;
        }
        return commitChange(FavoritePolicy.replacePanels(document,routes));
    }

    function toggleCardFavorite(sourceId, cardId) {
        // Only explicit per-card pin/unpin clicks enter this writer.
        if (!writable) {
            lastResultCode = "STORE_UNAVAILABLE";
            return false;
        }
        const key = String(sourceId || "") + "|" + String(cardId || "");
        return commitChange(FavoritePolicy.toggleCard(document,key));
    }

    FileView {
        id: favoritesFile
        path: store.storagePath
        atomicWrites: true
        watchChanges: false
        blockWrites: false
        printErrors: false

        onLoaded: store.acceptLoaded(favoritesFile.text())

        onLoadFailed: function(error) {
            if (store.storageState === "saving")
                return;
            store.pendingDocument = null;
            if (error === FileViewError.FileNotFound) {
                store.document = FavoritePolicy.empty();
                store.storageState = "empty";
                store.errorCode = "";
                store.lastResultCode = "";
                store.favoritesLoaded();
            } else {
                store.document = FavoritePolicy.empty();
                store.storageState = "error";
                store.errorCode = "FILE_LOAD_FAILED";
                store.lastResultCode = store.errorCode;
            }
        }

        onSaved: {
            if (store.storageState !== "saving" || !store.pendingDocument)
                return;
            store.document = store.pendingDocument;
            store.pendingDocument = null;
            store.storageState = "ready";
            store.errorCode = "";
            store.lastResultCode = "SAVED";
            store.favoritesSaved(store.revision);
        }

        onSaveFailed: function(error) {
            store.pendingDocument = null;
            store.storageState = "error";
            store.errorCode = "FILE_SAVE_FAILED";
            store.lastResultCode = store.errorCode;
            // No optimistic confirmation, retry, migration or overwrite.
        }
    }
}
