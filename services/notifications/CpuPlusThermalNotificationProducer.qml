import QtQuick
import Quickshell
import qs.services.notifications
import "CpuPlusThermalPolicy.js" as ThermalPolicy

// Display-only consumer of CPU++ / AppControl's ONE shared SystemTelemetry.
// It NEVER starts a monitor process, polls sensors or controls fan speed.
Scope {
    id: producer
    required property var telemetry
    property var perSensorState: ({})

    function observe() {
        if (!telemetry || telemetry.errorText
                || !Array.isArray(telemetry.thermalRows))
            return;

        const rows = telemetry.thermalRows;
        const updated = Object.assign({}, perSensorState);
        const raised = [];

        for (let index = 0; index < rows.length; ++index) {
            const sensor = rows[index] || {};
            // Physical hwmon source paths disambiguate equal chip/label names.
            // Never send that local path or process contributors to history.
            const key = String(sensor.source || sensor.id || "").trim();
            if (!key || sensor.sensorKind !== "temperature")
                continue;

            const result = ThermalPolicy.transition(updated[key], sensor);
            updated[key] = result.state;
            if (result.emit > 0) {
                raised.push({
                    level: result.emit,
                    name: String(sensor.name || sensor.label || "SENSOR")
                          .slice(0, 72),
                    chip: String(sensor.chip || "").slice(0, 40),
                    tempC: result.reading.temp,
                    highC: result.reading.high,
                    critC: result.reading.crit
                });
            }
        }
        perSensorState = updated;

        if (raised.length === 0)
            return;

        raised.sort(function(a, b) {
            return b.level - a.level || b.tempC - a.tempC;
        });
        const highest = raised[0];
        const critical = highest.level === 2;
        const title = critical ? "CPU++ // THERMAL CRITICAL"
                               : "CPU++ // THERMAL WARNING";
        const threshold = critical ? highest.critC : highest.highC;
        const affected = raised.length === 1
            ? highest.name
            : highest.name + " + " + (raised.length - 1)
              + " other sensor" + (raised.length === 2 ? "" : "s");
        const message = affected + " // " + highest.tempC.toFixed(1) + "°C"
                + " reached hardware "
                + (critical ? "critical" : "high")
                + " limit " + threshold.toFixed(1) + "°C."
                + " Review CPU++ Thermal.";

        NotificationsService.pushRich({
            "source": "CPU++",
            "sourceId": "cpu-plus",
            "category": "internal",
            "severity": critical ? "critical" : "warning",
            "title": title,
            "message": message,
            "tags": ["cpu-plus", "thermal", "hardware-limit"],
            "context": {
                "eventType": "hardware-thermal-limit",
                "affectedCount": raised.length,
                "sensorLabels": raised.map(function(s) { return s.name; })
            },
            "metrics": {
                "temperatureC": highest.tempC,
                "hardwareHighC": highest.highC,
                "hardwareCriticalC": highest.critC,
                "alertLevel": highest.level
            }
        });
    }

    Connections {
        target: producer.telemetry
        function onRefreshed() { producer.observe(); }
    }
}
