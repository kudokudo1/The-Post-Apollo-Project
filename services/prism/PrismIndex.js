.pragma library

// PRISM // Registration index for contexts that actually mount Prism.
// New installations add one verified entry here alongside their dock/widget
// wiring. This is a source-backed directory, not service discovery, scanning,
// readiness telemetry or a claim that color definitions have been written.
var placements = [
    {
        id: "post-apollo",
        name: "POST APOLLO",
        location: "BOTTOM DOCK // BESIDE TRASH",
        source: "modules/PrismDock.qml",
        definitions: 0
    }
];

function registered() {
    // Copy container/records so downstream views cannot rewrite this registry.
    return placements.map(function(p) {
        return {
            id: p.id,
            name: p.name,
            location: p.location,
            source: p.source,
            definitions: p.definitions
        };
    });
}
