import QtQuick
import Quickshell
import "../../services/favorites/FavoritesAppControlDisplayPolicy.js" as Display

// AppControl-owned display projection for external consumers. This object
// does not launch, toggle, persist or grant any AppControl capabilities.
// CPU++ receives only menu, safe visible item name and favorite type.
QtObject {
    id: root
    property var appControlOwner: null
    property var favoritesStore: null

    function copyValues(value) {
        if (!value || typeof value.length !== "number"
                || value.length < 0 || value.length > 4096)
            return [];
        const rows=[];
        for (let i=0; i<value.length; ++i) rows.push(value[i]);
        return rows;
    }

    readonly property var records: Display.build({
        favoriteKeys: root.favoritesStore
            ? copyValues(root.favoritesStore.favoriteKeys) : [],
        favoriteDetailActionKeys: root.favoritesStore
            ? copyValues(root.favoritesStore.favoriteDetailActionKeys) : [],
        favoriteMonitorBoxKeys: root.favoritesStore
            ? copyValues(root.favoritesStore.favoriteMonitorBoxKeys) : [],
        favoriteTaskMetricKeys: root.favoritesStore
            ? copyValues(root.favoritesStore.favoriteTaskMetricKeys) : []
    }, {
        apps: copyValues(DesktopEntries.applications.values),
        thermalRows: root.appControlOwner
            ? copyValues(root.appControlOwner.thermalRows) : [],
        fanRows: root.appControlOwner
            ? copyValues(root.appControlOwner.fanRows) : [],
        systemRows: root.appControlOwner
            ? copyValues(root.appControlOwner.systemRows) : [],
        taskRows: root.appControlOwner
            ? copyValues(root.appControlOwner.taskRows) : [],
        // Use original live WINDOWS/TABS labels only for an exact saved match.
        // Neither full window metadata nor private tabs reach CPU++.
        swayWindows: root.appControlOwner
            ? copyValues(root.appControlOwner.swayWindows) : [],
        appTabs: root.appControlOwner
            ? copyValues(root.appControlOwner.appTabs) : []
    })
}
