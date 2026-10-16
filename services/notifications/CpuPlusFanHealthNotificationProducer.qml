import QtQuick
import Quickshell
import qs.services.notifications
import "CpuPlusFanHealthPolicy.js" as FanPolicy

// Passive consumer of CPU++ / AppControl's existing SystemTelemetry.fanRows.
// It never starts sampling, changes PWM, or controls a process/fan.
Scope {
    id: producer
    required property var telemetry
    property var fanStates: ({})

    function observe() {
        if (!producer.telemetry || producer.telemetry.errorText
                || !Array.isArray(producer.telemetry.fanRows))
            return;

        const rows = producer.telemetry.fanRows;
        const next = Object.assign({}, producer.fanStates);
        const warnings = [];
        const recoveries = [];
        const now = Date.now();

        for (let i = 0; i < rows.length; ++i) {
            const fan = rows[i] || {};
            // hwmon source paths are internal-only keys to keep identical
            // model/label names from collapsing. Never publish those paths.
            const key = String(fan.source || fan.id || "").trim();
            if (!key || fan.sensorKind !== "fan")
                continue;
            const result = FanPolicy.transition(next[key], fan, now);
            next[key] = result.state;
            if (!result.event || !result.observation)
                continue;

            const event = {
                name: String(fan.name || fan.label || "FAN").slice(0, 72),
                chip: String(fan.chip || "").slice(0, 40),
                rpm: result.observation.rpm,
                minRpm: result.observation.minRpm,
                pwmPercent: result.observation.pwmPercent
            };
            if (result.event === "warning")
                warnings.push(event);
            else if (result.event === "recovered")
                recoveries.push(event);
        }

        producer.fanStates = next;
        if (warnings.length > 0)
            producer.publish(warnings, false, now);
        if (recoveries.length > 0)
            producer.publish(recoveries, true, now);
    }

    function publish(items, recovered, observedMs) {
        const fan = items[0];
        const displayName = fan.chip
                          ? fan.chip + " // " + fan.name : fan.name;
        const extras = items.length > 1
                     ? " + " + (items.length - 1) + " MORE FAN SENSOR(S)" : "";
        const detail = displayName + extras + " // "
                     + fan.rpm.toFixed(0) + " RPM"
                     + " // HWMON MIN " + fan.minRpm.toFixed(0) + " RPM";
        const demand = fan.pwmPercent === null
                     ? "" : " // PWM " + fan.pwmPercent.toFixed(0) + "%";
        const message = detail + demand
                      + (recovered
                         ? " // RPM returned to the reported minimum or above."
                         : " // Repeated readings warrant inspection; "
                           + "this does not prove a hardware failure.")
                      + " Review CPU++ THERMAL // FANS.";

        NotificationsService.pushRich({
            "source": "CPU++",
            "sourceId": "cpu-plus-fan-health",
            "category": "internal",
            "severity": recovered ? "normal" : "warning",
            "title": recovered ? "CPU++ // FAN RPM RECOVERED"
                               : "CPU++ // FAN RPM BELOW MINIMUM",
            "message": message,
            "tags": ["cpu-plus", "system", "fan-health", "hwmon"],
            "metrics": {
                "rpm": fan.rpm,
                "hwmonMinimumRpm": fan.minRpm,
                "pwmPercent": fan.pwmPercent,
                "affectedCount": items.length
            },
            "context": {
                "eventType": recovered ? "fan-rpm-recovered"
                                       : "fan-rpm-below-hwmon-minimum",
                "origin": "apollo",
                "domain": "system",
                "evidence": "repeated hwmon tachometer and configured minimum",
                "observedAtUtc": new Date(observedMs).toISOString(),
                "sampling": "existing active monitoring only"
            }
        });
    }

    Connections {
        target: producer.telemetry
        function onRefreshed() { producer.observe(); }
    }
}
