import QtQuick
import Quickshell
import qs.services.notifications
import "CpuPlusTelemetryHealthPolicy.js" as HealthPolicy

// Passive completion observer only. The shared CPU++ SystemTelemetry owns
// sampling. No new Process, Timer, hardware control, or monitoring activation.
Scope {
    id: producer
    required property var telemetry
    property var state: HealthPolicy.initial()

    function receive(healthy) {
        if (!NotificationsService.historyReady)
            return;
        const now = Date.now();
        const decision = HealthPolicy.transition(producer.state, healthy, now);
        producer.state = decision.state;
        if (!decision.event)
            return;
        const restored = decision.event === "restored";
        NotificationsService.pushRich({
            "source": "CPU++",
            "sourceId": "cpu-plus-telemetry-health",
            "category": "internal",
            "severity": restored ? "normal" : "warning",
            "title": restored ? "CPU++ // MONITOR DATA RESTORED"
                              : "CPU++ // MONITOR DATA UNAVAILABLE",
            "message": restored
                ? "Two completed CPU++ telemetry samples succeeded again."
                : "Two completed CPU++ telemetry attempts reported errors."
                  + " Latest sensor data may be stale. Review CPU++ diagnostics.",
            "tags": ["cpu-plus", "system", "monitor-health"],
            "context": {
                "eventType": restored ? "cpu-monitor-restored"
                                      : "cpu-monitor-unavailable",
                "origin": "apollo",
                "domain": "system",
                "evidence": "completed shared CPU++ telemetry observations",
                "observedAtUtc": new Date(now).toISOString()
            }
        });
    }

    Connections {
        target: producer.telemetry
        function onMonitorObservation(healthy) { producer.receive(healthy); }
    }
}
