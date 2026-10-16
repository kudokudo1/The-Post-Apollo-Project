import QtQuick
import Quickshell
import qs.services.notifications
import "SolarReportPolicy.js" as SolarReportPolicy
import "SolarStormPolicy.js" as StormPolicy

// Reuses SpaceService's NOAA Kp data/timestamps. No new curl/polling/TIMER,
// forecasts or official NOAA alert claims. Persistent IDs dedupe reloads.
Scope {
    id: producer
    required property var spaceService
    property var kpState: StormPolicy.initial()

    function historyContains(id) {
        const rows = NotificationsService.notifications;
        for (let i = 0; i < rows.count; ++i) {
            if (String(rows.get(i).id || "") === id)
                return true;
        }
        return false;
    }

    function observe() {
        if (!NotificationsService.historyReady
                || !producer.spaceService || !producer.spaceService.kpReady)
            return;
        const observedMs = SolarReportPolicy.observationTimeMs(producer.spaceService.kpTime);
        const now = Date.now();
        const result = StormPolicy.transition(producer.kpState, producer.spaceService.kp,
                                              observedMs, now);
        producer.kpState = result.state;
        if (result.emit === 0)
            return;

        const id = "apollo-noaa-kp-storm-" + observedMs;
        if (producer.historyContains(id))
            return;

        const severe = result.emit >= 3;
        const band = "G" + result.emit;
        const observedAt = new Date(observedMs).toISOString();
        NotificationsService.pushRich({
            "id": id,
            "source": "WEATHER STATION",
            "sourceId": "weather-space-storm",
            "category": "internal",
            "severity": severe ? "critical" : "warning",
            "title": "SPACE WEATHER // " + band + " STORM "
                     + (result.kind === "escalated" ? "ESCALATED" : "OBSERVED"),
            "message": "NOAA SWPC observed planetary Kp "
                     + Number(producer.spaceService.kp).toFixed(1) + " (" + band
                     + ") at " + observedAt + ". "
                     + "This is an observed Kp threshold, not a forecast "
                     + "or an official NOAA warning. Review Weather Station SPACE.",
            "tags": ["weather", "space", "solar", "geomagnetic-storm"],
            "metrics": {
                "kp": Number(producer.spaceService.kp),
                "stormLevel": result.emit
            },
            "context": {
                "eventType": "geomagnetic-storm-" + result.kind,
                "origin": "apollo",
                "domain": "weather",
                "source": "NOAA SWPC",
                "observationTimeUtc": observedAt
            }
        });
    }

    Connections {
        target: producer.spaceService
        function onKpTimeChanged() { producer.observe(); }
        function onKpReadyChanged() { producer.observe(); }
    }
    Connections {
        target: NotificationsService
        function onHistoryReadyChanged() { producer.observe(); }
    }
    Component.onCompleted: observe()
}
