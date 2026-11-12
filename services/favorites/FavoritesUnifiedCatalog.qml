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
    property var alarmSource: null       // AlarmManagerService singleton (READ ONLY)
    property var angelDefaultSource: null // FavoritesDefaultStore singleton (READ ONLY)

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

        if (alarmSource) {
            const record = Adapters.clockAlarms(
                copyValues(alarmSource.document && alarmSource.document.alarms));
            groups.push({
                id:"clock-alarm",label:"ALARMS",
                state:String(alarmSource.storageState || "unknown"),
                items:record.items,invalidCount:record.invalidCount
            });
        }

        if (angelDefaultSource) {
            const record = Adapters.angelNumbers(
                copyValues(angelDefaultSource.favoriteKeys));
            groups.push({
                id:"angel",label:"ANGEL",
                state:String(angelDefaultSource.storageState || "unknown"),
                items:record.items,invalidCount:record.invalidCount
            });
        }
        // Prioritize Clock-owned saved items: a large AppControl catalog
        // cannot crowd time zones, alarms or Angel numbers out of 60 rows.
        const order = ["time", "clock-alarm", "angel", "places", "appcontrol"];
        groups.sort(function(a,b) {
            return order.indexOf(a.id) - order.indexOf(b.id);
        });
        return CatalogPolicy.build(groups);
    }
}
