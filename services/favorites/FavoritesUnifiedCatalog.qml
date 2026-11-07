import QtQuick
import "FavoritesReadOnlyAdapters.js" as Adapters
import "FavoritesCatalogPolicy.js" as CatalogPolicy

// U2 opt-in READ-ONLY catalog. Consumers inject the ORIGINAL singleton
// owners; creating this object never creates a provider or a second writer.
// Only presentational descriptors are emitted, never action credentials.
QtObject {
    id: catalog

    property var appControlSource: null  // FavoritesStore singleton
    property var worldSource: null       // TimeSettings singleton
    property var placesSource: null      // PlaceRegistry singleton

    function copyValues(value) {
        if (value === null || value === undefined
                || typeof value.length !== "number"
                || value.length < 0 || value.length > 4096)
            return [];
        const out = [];
        for (let i = 0; i < value.length; ++i)
            out.push(value[i]);
        return out;
    }

    // QML property dependencies are intentionally read here: owner edits to
    // favorites or saved places automatically invalidate this binding.
    readonly property var snapshot: {
        const groups = [];

        if (appControlSource) {
            const record = Adapters.appControl({
                favoriteKeys:copyValues(appControlSource.favoriteKeys),
                favoriteDetailActionKeys:copyValues(
                    appControlSource.favoriteDetailActionKeys),
                favoriteMonitorBoxKeys:copyValues(
                    appControlSource.favoriteMonitorBoxKeys),
                favoriteTaskMetricKeys:copyValues(
                    appControlSource.favoriteTaskMetricKeys)
            });
            groups.push({
                id:"appcontrol",label:"APP CONTROL",
                state:"unknown",items:record.items,
                invalidCount:record.invalidCount
            });
        }

        if (worldSource) {
            const record = Adapters.worldClock({
                zones:copyValues(worldSource.worldFavoriteZones)
            });
            groups.push({
                id:"time",label:"WORLD CLOCK",
                state:String(worldSource.worldFavoriteState || "unknown"),
                items:record.items,invalidCount:record.invalidCount
            });
        }

        if (placesSource) {
            const record = Adapters.places(
                copyValues(placesSource.savedPlaces));
            groups.push({
                id:"places",label:"SAVED PLACES",
                state:String(placesSource.storageState || "unknown"),
                items:record.items,invalidCount:record.invalidCount
            });
        }

        return CatalogPolicy.build(groups);
    }
}
