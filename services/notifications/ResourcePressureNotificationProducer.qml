import QtQuick
import Quickshell
import qs.services.notifications
import "ResourcePressurePolicy.js" as PressurePolicy

// Read-only observer of shared CPU++ SystemTelemetry. No polling, Process,
// resource mutation, process termination or OS settings changes.
Scope {
    id: producer
    required property var telemetry
    property var metricStates: ({
        memory: PressurePolicy.initial(),
        storage: PressurePolicy.initial()
    })

    function publish(kind, event, metrics, observedMs) {
        const recovered = event === "recovered";
        const critical = event === "critical";
        const label = kind === "memory" ? "MEMORY" : "ROOT STORAGE";
        const value = kind === "memory" ? metrics.memory : metrics.storage;
        const threshold = PressurePolicy.thresholds(kind);
        const used = value.toFixed(1) + "%";
        let message = label + " // " + used + " USED";
        if (recovered) {
            message += " // BELOW " + threshold.recovered
                       + "% RECOVERY THRESHOLD.";
        } else {
            message += " // SUSTAINED ABOVE "
                       + (critical ? threshold.critical : threshold.warning)
                       + "% CONFIGURED ALERT THRESHOLD.";
        }
        if (kind === "memory" && metrics.swap !== null)
            message += " SWAP // " + metrics.swap.toFixed(1) + "% USED.";
        message += " Review CPU++ SYSTEM. No automatic action was taken.";

        NotificationsService.pushRich({
            "source": "CPU++",
            "sourceId": "cpu-plus-resource-pressure",
            "category": "internal",
            "severity": recovered ? "normal"
                                  : critical ? "critical" : "warning",
            "title": "CPU++ // " + label + " "
                     + (recovered ? "RECOVERED"
                                 : critical ? "CRITICAL" : "PRESSURE"),
            "message": message,
            "tags": ["cpu-plus", "system", "resource-pressure", kind],
            "metrics": {
                "memoryPercent": metrics.memory,
                "swapPercent": metrics.swap,
                "rootStoragePercent": metrics.storage,
                "thresholdPercent": recovered ? threshold.recovered
                                             : critical ? threshold.critical
                                                        : threshold.warning
            },
            "context": {
                "eventType": "resource-pressure-" + event,
                "origin": "apollo",
                "domain": "system",
                "metric": kind,
                "observedAtUtc": new Date(observedMs).toISOString(),
                "sampling": "existing active monitoring only"
            }
        });
    }

    function observe() {
        if (!producer.telemetry || producer.telemetry.errorText
                || !NotificationsService.historyReady)
            return;

        const metrics = PressurePolicy.observation(producer.telemetry.systemRows);
        if (!metrics)
            return;

        const now = Date.now();
        const next = Object.assign({}, producer.metricStates);
        for (const kind of ["memory", "storage"]) {
            const value = metrics[kind];
            if (value === null)
                continue;
            const result = PressurePolicy.transition(next[kind], kind, value, now);
            next[kind] = result.state;
            if (result.event)
                producer.publish(kind, result.event, metrics, now);
        }
        producer.metricStates = next;
    }

    Connections {
        target: producer.telemetry
        function onRefreshed() { producer.observe(); }
    }
}
