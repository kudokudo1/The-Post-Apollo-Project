import QtQuick

// Team 8 — APPS Core identity handoff.
//
// Team 8 owns DesktopEntries as catalog/launch inputs but does not own
// cross-provider semantic identity. This adapter delegates DesktopEntry
// observation construction to Team 7's frozen evidence contract.
//
// No alias vocabulary, normalization rule, lifetime class, relationship kind,
// resolver scoring, or canonical application key is implemented here.
QtObject {
    id: adapter

    // Expected Team 7 contract:
    //   desktopEntryObservation(entry) -> observation envelope
    required property var identityEvidence

    function available() {
        return !!identityEvidence
            && typeof identityEvidence.desktopEntryObservation === "function";
    }

    function observationForEntry(entry) {
        if (!entry || !available())
            return null;

        return identityEvidence.desktopEntryObservation(entry);
    }

    function providerKeyForEntry(entry) {
        const observation = observationForEntry(entry);

        return observation
            ? String(observation.providerKey || "")
            : "";
    }

    function rawForEntry(entry) {
        const observation = observationForEntry(entry);

        return observation && observation.raw
            ? observation.raw
            : {};
    }
}
