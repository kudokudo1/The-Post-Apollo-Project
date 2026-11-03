import QtQuick
import Quickshell

// M26-D disposable provider replacement. Never performs network I/O.
// Only the isolated test tree uses this file; production GdacsService is
// copied and then temporarily replaced inside the CI sandbox.
Scope {
    property var cacheStore: null
    property bool active: false
    property bool ready: true
    property bool failed: false
    property string errorText: ""
    property bool loading: false
    property date lastUpdated: new Date()
    property var events: [{
        id: "FL:M26D:1",
        eventId: "M26D",
        episodeId: "1",
        eventType: "FL",
        eventTypeLabel: "FLOOD",
        name: "SYNTHETIC M26D GDACS EVENT",
        alertLevel: "ORANGE",
        alertScore: 1,
        alertToken: "orange",
        isCurrent: true,
        country: "TEST",
        iso3: "TST",
        source: "GDACS",
        latitude: 0,
        longitude: 0,
        coordinates: "0.00, 0.00",
        geometryType: "Point",
        fromUtc: "2026-11-03 00:00 UTC",
        toUtc: "2026-11-03 00:00 UTC",
        timeMs: Date.now() - 60000,
        severity: 1,
        severityText: "SYNTHETIC, NOT A REAL ALERT",
        severityUnit: "",
        reportUrl: "",
        detailsUrl: ""
    }]

    function refresh(force) { return false; }
}
