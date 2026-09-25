pragma Singleton

import QtQuick

QtObject {
    id: root

    // FILES owns semantic file identity. Favorites only translates that
    // provider-owned identity into persisted membership/reconstruction refs.
    readonly property string providerPrefix: "file:"
    readonly property string parentPrefix: "file:parent:"

    function stringValue(value) {
        if (value === undefined || value === null)
            return "";
        return String(value);
    }

    function isFileRecord(entry) {
        return !!entry && entry._fileRecord === true;
    }

    function isParentRecord(entry) {
        if (!entry)
            return false;

        if (entry.isParent === true)
            return true;

        const id = stringValue(entry.id);
        return id.indexOf(parentPrefix) === 0;
    }

    function canPersist(entry) {
        if (!isFileRecord(entry) || isParentRecord(entry))
            return false;

        return providerIdentity(entry).length > 0;
    }

    // Consume only the identity emitted by FileService. Favorites must not
    // synthesize canonical FILE identity from path or presentation fields.
    function providerIdentity(entry) {
        if (!isFileRecord(entry) || isParentRecord(entry))
            return "";

        const id = stringValue(entry.id);

        if (id.indexOf(providerPrefix) === 0
                && id.indexOf(parentPrefix) !== 0)
            return id;

        // Do not synthesize provider identity from path here. A FILE record
        // without a FileService-owned id is not canonical yet.
        return "";
    }

    function canonicalFavoriteKey(entry) {
        return providerIdentity(entry);
    }

    function isCanonicalFavoriteKey(key) {
        const value = stringValue(key);

        return value.indexOf(providerPrefix) === 0
               && value.indexOf(parentPrefix) !== 0
               && value.length > providerPrefix.length;
    }

    function pathFromCanonicalKey(key) {
        const value = stringValue(key);

        if (!isCanonicalFavoriteKey(value))
            return "";

        return value.slice(providerPrefix.length);
    }

    // Historical FILE favorites use AppControl's generic fallback:
    //     mode:<FILES mode index>:<display label>
    // Keep construction explicit and caller-supplied because the numeric mode
    // index remains host navigation state, not provider identity.
    function legacyFavoriteKey(entry, filesModeIndex) {
        if (!isFileRecord(entry) || isParentRecord(entry))
            return "";

        const label = stringValue(entry.label || entry.name);
        const modeIndex = Number(filesModeIndex);

        if (!label || !isFinite(modeIndex))
            return "";

        return "mode:" + String(modeIndex) + ":" + label;
    }

    function isLegacyFavoriteKeyForEntry(key, entry, filesModeIndex) {
        const legacy = legacyFavoriteKey(entry, filesModeIndex);
        return legacy.length > 0 && stringValue(key) === legacy;
    }

    function matchingFavoriteKey(entry, filesModeIndex, favoriteKeys) {
        if (!entry || !favoriteKeys)
            return "";

        const canonical = canonicalFavoriteKey(entry);

        if (canonical && favoriteKeys.indexOf(canonical) !== -1)
            return canonical;

        const legacy = legacyFavoriteKey(entry, filesModeIndex);

        if (legacy && favoriteKeys.indexOf(legacy) !== -1)
            return legacy;

        return "";
    }

    function isFavorite(entry, filesModeIndex, favoriteKeys) {
        return matchingFavoriteKey(
            entry,
            filesModeIndex,
            favoriteKeys
        ).length > 0;
    }

    // Provider-specific migration proposal only. FavoritesService owns the
    // actual key replacement/deduplication and persistence.
    function migrationPlan(entry, filesModeIndex, favoriteKeys) {
        const source = favoriteKeys || [];
        const canonical = canonicalFavoriteKey(entry);
        const legacy = legacyFavoriteKey(entry, filesModeIndex);

        if (!canonical || !legacy)
            return null;

        if (source.indexOf(legacy) < 0)
            return null;

        return {
            oldKey: legacy,
            newKey: canonical
        };
    }

    // Stable reconstruction reference only. Resolving this path into a live
    // FILE row belongs to FileService; Favorites must not stat/probe files.
    function reconstructionReference(key) {
        const path = pathFromCanonicalKey(key);

        if (!path)
            return null;

        return {
            provider: "files",
            identity: stringValue(key),
            path: path
        };
    }
}
