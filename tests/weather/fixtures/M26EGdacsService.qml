import QtQuick
import Quickshell
// M26-E isolated fake feed: no HTTP, timer, cache, or real warnings.
Scope {
    property var cacheStore: null
    property bool active: false
    property bool ready: true
    property bool failed: false
    property bool loading: false
    property bool usingPersistentCache: false
    property string errorText: ""
    property date lastUpdated: new Date()
    property var events: [{
        id: "M26E-SHARED",
        eventId: "M26E",
        episodeId: "1",
        eventType: "FL",
        eventTypeLabel: "FLOOD",
        name: "SYNTHETIC GDACS TEST",
        alertLevel: "ORANGE",
        alertToken: "orange",
        alertScore: 1,
        isCurrent: true,
        latitude: 0,
        longitude: 0,
        timeMs: Date.now() - 60000,
        coordinates: "0.00, 0.00",
        fromUtc: "2026-11-03 00:00 UTC",
        toUtc: "2026-11-03 00:00 UTC",
        country: "TEST",
        severityText: "SYNTHETIC EVENT",
        reportUrl: "",
        detailsUrl: ""
    }]
    function refresh(force) {return false;}
}
