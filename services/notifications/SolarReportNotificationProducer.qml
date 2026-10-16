import QtQuick
import Quickshell
import qs.services.notifications
import "SolarReportPolicy.js" as SolarPolicy

// Once per local calendar day, summarize the existing SpaceService products.
// This producer is observational only: no new fetches, actions, or predictions.
Scope {
    id: producer
    required property var spaceService
    property string deliveredDay: ""

    function historyContains(id) {
        const rows = NotificationsService.notifications;
        for (let index = 0; index < rows.count; ++index) {
            if (String(rows.get(index).id || "") === id)
                return true;
        }
        return false;
    }

    function maybePublish() {
        // Wait for persisted history before deduplicating across reloads.
        if (!NotificationsService.historyReady || !spaceService)
            return;

        const now = new Date();
        const day = SolarPolicy.localDayKey(now);
        const id = "apollo-solar-report-" + day;

        if (deliveredDay === day)
            return;

        if (historyContains(id)) {
            deliveredDay = day;
            return;
        }

        const data = SolarPolicy.snapshot(spaceService, now.getTime());
        if (!data)
            return;

        NotificationsService.pushRich({
            "id": id,
            "source": "SOLAR REPORT",
            "sourceId": "weather-space",
            "category": "internal",
            "severity": "normal",
            "title": "SOLAR REPORT // SPACE WEATHER",
            "message": SolarPolicy.summary(data),
            "tags": ["weather", "space", "solar", "daily-report"],
            "metrics": {
                "kp": data.kp,
                "solarWindKmS": data.solarWindKmS,
                "magneticBtNt": data.btNt,
                "magneticBzNt": data.bzNt,
                "solarFluxSfu": data.solarFluxSfu
            },
            "context": {
                "eventType": "solar-daily-report",
                "localDay": day,
                "source": "NOAA SWPC",
                "observationTimesUtc": data.observed,
                "destination": "weather-station-space"
            }
        });
        deliveredDay = day;
    }

    Connections {
        target: producer.spaceService

        function onReadyChanged() { producer.maybePublish(); }
        function onKpTimeChanged() { producer.maybePublish(); }
        function onSolarWindTimeChanged() { producer.maybePublish(); }
        function onMagneticFieldTimeChanged() { producer.maybePublish(); }
        function onSolarFluxTimeChanged() { producer.maybePublish(); }
    }

    Connections {
        target: NotificationsService
        function onHistoryReadyChanged() { producer.maybePublish(); }
    }

    // Date rollover and reconnects should not require opening Weather Station.
    // This timer reads cached data only and never initiates HTTP requests.
    Timer {
        interval: 600000
        repeat: true
        running: true
        onTriggered: producer.maybePublish()
    }

    Component.onCompleted: maybePublish()
}
