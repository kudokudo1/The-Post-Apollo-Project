import QtQuick
import Quickshell
import qs.services.notifications
import "CpuPlusSystemReportPolicy.js" as SystemPolicy

// Read-only daily observation of existing CPU++ / AppControl system samples.
// Never starts sampling, terminates processes, or changes system settings.
Scope {
    id: producer
    required property var telemetry
    property string deliveredDay: ""
    property double lastObservedAtMs: 0

    function historyContains(id) {
        const rows = NotificationsService.notifications;
        for (let i = 0; i < rows.count; ++i) {
            if (String(rows.get(i).id || "") === id)
                return true;
        }
        return false;
    }

    function maybePublish() {
        if (!NotificationsService.historyReady || !telemetry
                || telemetry.errorText
                || !Array.isArray(telemetry.systemRows))
            return;

        const now = new Date();
        // Do not label cached readings as live after a long idle interval.
        if (lastObservedAtMs <= 0
                || now.getTime() - lastObservedAtMs > 15000)
            return;

        const day = SystemPolicy.localDayKey(now);
        const id = "apollo-system-report-" + day;
        if (deliveredDay === day)
            return;
        if (historyContains(id)) {
            deliveredDay = day;
            return;
        }

        const record = SystemPolicy.observation(
            telemetry.systemRows, lastObservedAtMs);
        if (!record)
            return;

        NotificationsService.pushRich({
            "id": id,
            "source": "CPU++",
            "sourceId": "cpu-plus-system",
            "category": "internal",
            "severity": "normal",
            "title": "CPU++ // SYSTEM REPORT",
            "message": SystemPolicy.summary(record),
            "tags": ["cpu-plus", "system", "observation", "report"],
            "metrics": {
                "cpuPercent": record.cpuPercent,
                "memoryPercent": record.memoryPercent,
                "swapPercent": record.swapPercent,
                "rootStoragePercent": record.rootStoragePercent,
                "gpuPercent": record.gpuPercent,
                "networkUp": record.networkUp,
                "networkDown": record.networkDown,
                "networkUnknown": record.networkUnknown
            },
            "context": {
                "eventType": "system-observation-report",
                "origin": "apollo",
                "domain": "system",
                "localDay": day,
                "observedAtUtc": record.observedAtUtc,
                "sampling": "existing active monitoring only"
            }
        });
        deliveredDay = day;
    }

    Connections {
        target: producer.telemetry
        function onRefreshed() {
            if (producer.telemetry.errorText)
                return;
            producer.lastObservedAtMs = Date.now();
            producer.maybePublish();
        }
    }

    Connections {
        target: NotificationsService
        function onHistoryReadyChanged() { producer.maybePublish(); }
    }
}
