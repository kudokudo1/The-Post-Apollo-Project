pragma Singleton

import QtQuick
import "." as FavoritesBackend

Singleton {
    id: root

    readonly property var store: FavoritesBackend.FavoritesStore

    // Temporary compatibility surface. Consumers that only need membership
    // state can move to FavoritesService without learning persistence details.
    readonly property var favoriteKeys: store.favoriteKeys
    readonly property var favoriteDetailActionKeys: store.favoriteDetailActionKeys
    readonly property var favoriteMonitorBoxKeys: store.favoriteMonitorBoxKeys
    readonly property var favoriteTaskMetricKeys: store.favoriteTaskMetricKeys

    function keyString(key) {
        if (key === undefined || key === null)
            return "";
        return String(key);
    }

    function contains(list, key) {
        const value = keyString(key);
        return value.length > 0 && list.indexOf(value) !== -1;
    }

    function toggled(list, key, prepend) {
        const value = keyString(key);
        if (!value)
            return null;

        const next = list.slice();
        const index = next.indexOf(value);
        const enabled = index < 0;

        if (index >= 0)
            next.splice(index, 1);
        else if (prepend)
            next.unshift(value);
        else
            next.push(value);

        return {
            values: next,
            enabled: enabled
        };
    }

    // Generic favorite membership. Key construction remains provider/adapter
    // responsibility; this service intentionally does not invent identity.
    function isFavoriteKey(key) {
        return contains(store.favoriteKeys, key);
    }

    function toggleFavoriteKey(key) {
        const result = toggled(store.favoriteKeys, key, true);
        if (!result)
            return false;

        store.favoriteKeys = result.values;
        return result.enabled;
    }

    // THERMAL/SYSTEM metric-box watches.
    function isMonitorBoxKey(key) {
        return contains(store.favoriteMonitorBoxKeys, key);
    }

    function toggleMonitorBoxKey(key) {
        const result = toggled(store.favoriteMonitorBoxKeys, key, true);
        if (!result)
            return false;

        store.favoriteMonitorBoxKeys = result.values;
        return result.enabled;
    }

    // Process metric watches.
    function isTaskMetricKey(key) {
        return contains(store.favoriteTaskMetricKeys, key);
    }

    function toggleTaskMetricKey(key) {
        const result = toggled(store.favoriteTaskMetricKeys, key, true);
        if (!result)
            return false;

        store.favoriteTaskMetricKeys = result.values;
        return result.enabled;
    }

    // Preferred detail actions preserve the donor's one-action-per-context
    // behavior. The caller owns construction of both context and action key.
    function isPreferredActionKey(key) {
        return contains(store.favoriteDetailActionKeys, key);
    }

    function togglePreferredActionKey(context, key) {
        const contextKey = keyString(context);
        const actionKey = keyString(key);

        if (!contextKey || !actionKey)
            return false;

        const prefix = contextKey + "|";
        const oldKeys = store.favoriteDetailActionKeys;
        const next = [];

        for (let i = 0; i < oldKeys.length; i++) {
            const existing = String(oldKeys[i]);
            if (existing.indexOf(prefix) !== 0)
                next.push(existing);
        }

        const wasFavorite = oldKeys.indexOf(actionKey) !== -1;

        // Match the donor exactly: selecting another action replaces the old
        // preferred action; selecting the same action clears it.
        if (!wasFavorite)
            next.push(actionKey);

        store.favoriteDetailActionKeys = next;
        return !wasFavorite;
    }
}
