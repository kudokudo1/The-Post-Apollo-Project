import QtQuick

// Team 8 — APPS Core selection policy.
//
// Pure APPS remembrance/restore semantics only. It never mutates host selection,
// ListView position, focus, or navigation state.
QtObject {
    id: policy

    required property var catalogPolicy

    function rememberedKeyFor(entry) {
        return catalogPolicy.entryKey(entry);
    }

    function restoreIndex(entries, rememberedKey) {
        const rows = Array.isArray(entries)
            ? entries
            : [];

        if (rows.length === 0)
            return -1;

        const key = String(rememberedKey || "");

        if (key.length > 0) {
            for (let i = 0; i < rows.length; i++) {
                if (catalogPolicy.entryKey(rows[i]) === key)
                    return i;
            }
        }

        return 0;
    }
}
