import QtQuick

// Team 8 — APPS Core mode policy.
//
// Pure APPS-specific state policy only. It does not refresh RUN, mutate host
// selection, move a host result view, change focus, or reset generic detail state.
QtObject {
    id: policy

    required property var coreProvider

    function normalizeSourceMode(mode) {
        if (mode === coreProvider.sourceHidden)
            return coreProvider.sourceHidden;

        if (mode === coreProvider.sourceFlatpak)
            return coreProvider.sourceFlatpak;

        return coreProvider.sourceNative;
    }

    function normalizeLaunchMode(mode) {
        if (mode === coreProvider.launchToolbox)
            return coreProvider.launchToolbox;

        if (mode === coreProvider.launchBottle)
            return coreProvider.launchBottle;

        return coreProvider.launchNormal;
    }

    function counterpartIndex(entries, previousName, sourceMode) {
        const rows = Array.isArray(entries)
            ? entries
            : [];

        if (rows.length === 0)
            return -1;

        const wanted =
            String(previousName || "").trim().toLowerCase();
        const normalizedSource =
            normalizeSourceMode(sourceMode);

        if (wanted.length > 0) {
            for (let i = 0; i < rows.length; i++) {
                const entry = rows[i];

                if (!coreProvider.entryMatchesSource(
                        entry,
                        normalizedSource)) {
                    continue;
                }

                if (String(entry && entry.name || "")
                        .trim()
                        .toLowerCase() === wanted) {
                    return i;
                }
            }
        }

        return 0;
    }

    function sourceChangePlan(entries, previousName, requestedMode) {
        const mode = normalizeSourceMode(requestedMode);

        return {
            sourceMode: mode,
            needsHiddenCatalogRefresh:
                mode === coreProvider.sourceHidden,
            restoreIndex:
                counterpartIndex(
                    entries,
                    previousName,
                    mode
                )
        };
    }

    function launchChangePlan(requestedMode) {
        return {
            launchMode: normalizeLaunchMode(requestedMode)
        };
    }
}
