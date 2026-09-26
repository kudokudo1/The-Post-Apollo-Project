import QtQuick
import Quickshell
import "." as FavoritesBackend

Scope {
    id: root

    // Provider lifetime remains external. A future host integration supplies
    // the already-live FileService instance.
    required property var fileService

    // Count requests rather than store a boolean so duplicate requests for the
    // same identity remain paired with duplicate provider completions.
    property var pendingIdentities: ({})

    signal resolutionFinished(string identity, var resolution)

    function pendingCount(identity) {
        return Number(
            pendingIdentities[String(identity || "")] || 0
        );
    }

    function markPending(identity) {
        const key = String(identity || "");
        const next = Object.assign({}, pendingIdentities);
        next[key] = Number(next[key] || 0) + 1;
        pendingIdentities = next;
    }

    function consumePending(identity) {
        const key = String(identity || "");
        const count = Number(pendingIdentities[key] || 0);

        if (count <= 0)
            return false;

        const next = Object.assign({}, pendingIdentities);

        if (count === 1)
            delete next[key];
        else
            next[key] = count - 1;

        pendingIdentities = next;
        return true;
    }

    function resolveFavoriteKey(key) {
        const ref =
            FavoritesBackend.FileFavoritesAdapter
                .reconstructionReference(key);

        if (!ref || !fileService
                || !fileService.resolveFavoriteIdentity)
            return false;

        // FileService may emit an invalid result synchronously, so register the
        // request before entering the provider.
        markPending(ref.identity);

        const accepted =
            fileService.resolveFavoriteIdentity(ref.identity);

        // A false provider return normally means the provider already emitted
        // an invalid completion synchronously. If a non-conforming provider
        // rejects silently, avoid leaking a pending request.
        if (!accepted && pendingCount(ref.identity) > 0)
            consumePending(ref.identity);

        return accepted;
    }

    Connections {
        target: root.fileService

        function onFavoriteResolutionFinished(identity, resolution) {
            const key = String(identity || "");

            if (!root.consumePending(key))
                return;

            // Do not reinterpret provider filesystem truth. Forward the exact
            // FileService result object to the Favorites reconstruction layer.
            root.resolutionFinished(key, resolution);
        }
    }
}
