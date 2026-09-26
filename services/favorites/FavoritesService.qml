pragma Singleton

import QtQuick
import "." as FavoritesBackend

QtObject {
    id: root

    readonly property var store: FavoritesBackend.FavoritesStore

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

        return { values: next, enabled: enabled };
    }

    function replaced(list, oldKey, newKey) {
        const oldValue = keyString(oldKey);
        const newValue = keyString(newKey);

        if (!oldValue || !newValue || oldValue === newValue)
            return { values: list.slice(), changed: false };

        const next = list.slice();
        const oldIndex = next.indexOf(oldValue);

        if (oldIndex < 0)
            return { values: next, changed: false };

        const newIndex = next.indexOf(newValue);

        if (newIndex >= 0)
            next.splice(oldIndex, 1);
        else
            next[oldIndex] = newValue;

        return { values: next, changed: true };
    }

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

    function replaceFavoriteKey(oldKey, newKey) {
        const result = replaced(store.favoriteKeys, oldKey, newKey);

        if (!result.changed)
            return false;

        store.favoriteKeys = result.values;
        return true;
    }

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

        if (!wasFavorite)
            next.push(actionKey);

        store.favoriteDetailActionKeys = next;
        return !wasFavorite;
    }
}
