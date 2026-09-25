import QtQuick

// Team 8 — APPS Core catalog policy.
//
// Pure catalog/search/ranking behavior. No ScriptModel, host search box,
// Favorites store, RUN discovery, or semantic cross-provider identity.
//
// Favorites may influence APPS ordering through an injected preference
// predicate. Team 8 does not know how that preference is persisted.
QtObject {
    id: policy

    required property var coreProvider

    function entryKey(entry) {
        if (!entry)
            return "";

        if (entry.id)
            return String(entry.id);

        return String(entry.name || "");
    }

    function searchHaystack(entry) {
        if (!entry)
            return "";

        return (
            String(entry.name || "") + " "
            + String(entry.genericName || "") + " "
            + String(entry.comment || "") + " "
            + String(entry.keywords || "") + " "
            + coreProvider.sourceLabel(entry)
        ).toLowerCase();
    }

    function matchesSearch(entry, queryText) {
        const query = String(queryText || "").trim().toLowerCase();

        if (!query)
            return true;

        return searchHaystack(entry).indexOf(query) !== -1;
    }

    function hiddenMatchesSearch(entry, queryText) {
        if (!entry || !entry._hiddenCommand)
            return false;

        const query = String(queryText || "").trim().toLowerCase();

        if (!query)
            return true;

        return String(entry.name || "")
            .toLowerCase()
            .indexOf(query) !== -1;
    }

    function preferenceValue(entry, preferencePredicate) {
        if (typeof preferencePredicate !== "function")
            return false;

        try {
            return !!preferencePredicate(entry);
        } catch (error) {
            // Ranking is presentation policy. A failing optional preference
            // signal must not make the application catalog disappear.
            return false;
        }
    }

    function compareEntries(a, b, sourceMode, preferencePredicate) {
        const aPreferred = preferenceValue(a, preferencePredicate);
        const bPreferred = preferenceValue(b, preferencePredicate);

        if (aPreferred !== bPreferred)
            return aPreferred ? -1 : 1;

        const nameCompare =
            String(a && a.name || "").localeCompare(
                String(b && b.name || "")
            );

        if (nameCompare !== 0)
            return nameCompare;

        // Preserve donor semantics: source mode does not remove Native/Flatpak
        // rows. It only promotes rows that match the selected source after the
        // primary display-name ordering tie.
        const aMatches =
            coreProvider.entryMatchesSource(a, sourceMode);
        const bMatches =
            coreProvider.entryMatchesSource(b, sourceMode);

        if (aMatches !== bMatches)
            return aMatches ? -1 : 1;

        return entryKey(a).localeCompare(entryKey(b));
    }

    function desktopRows(entries, queryText, sourceMode,
                         preferencePredicate) {
        const source = Array.isArray(entries)
            ? entries
            : [];
        const filtered = [];

        for (let i = 0; i < source.length; i++) {
            const entry = source[i];

            if (matchesSearch(entry, queryText))
                filtered.push(entry);
        }

        filtered.sort(function(a, b) {
            return policy.compareEntries(
                a,
                b,
                sourceMode,
                preferencePredicate
            );
        });

        return filtered;
    }

    function hiddenRows(entries, queryText) {
        const source = Array.isArray(entries)
            ? entries
            : [];
        const filtered = [];

        for (let i = 0; i < source.length; i++) {
            const entry = source[i];

            if (hiddenMatchesSearch(entry, queryText))
                filtered.push(entry);
        }

        filtered.sort(function(a, b) {
            return String(a && a.name || "").localeCompare(
                String(b && b.name || "")
            );
        });

        return filtered;
    }

    function rows(entries, hiddenEntries, queryText, sourceMode,
                  preferencePredicate) {
        if (sourceMode === coreProvider.sourceHidden) {
            return hiddenRows(
                hiddenEntries,
                queryText
            );
        }

        return desktopRows(
            entries,
            queryText,
            sourceMode,
            preferencePredicate
        );
    }
}
