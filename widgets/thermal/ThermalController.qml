import QtQuick
import "../../components"

QtObject {
    id: thermalController

    required property var telemetry
    required property var fanControl

    readonly property int thermalViewThermal: 0
    readonly property int thermalViewFans: 1
    property int thermalViewMode: thermalViewThermal

    readonly property var thermalRows:
        telemetry && Array.isArray(telemetry.thermalRows)
        ? telemetry.thermalRows : []
    readonly property var fanRows:
        telemetry && Array.isArray(telemetry.fanRows)
        ? telemetry.fanRows : []

    function setThermalViewMode(mode) {
        thermalViewMode =
            mode === thermalViewFans
            ? thermalViewFans
            : thermalViewThermal;
    }

    function rowsForCurrentView() {
        return thermalViewMode === thermalViewFans ? fanRows : thermalRows;
    }

    function reconcileFanRows(rows) {
        if (fanControl)
            fanControl.reconcilePendingPercent(
                Array.isArray(rows) ? rows : fanRows
            );
    }

    function fanControlUnlocked(entry) {
        return fanControl ? fanControl.unlocked(entry) : false;
    }

    function toggleFanControlUnlocked(entry) {
        if (fanControl)
            fanControl.toggleUnlocked(entry);
    }

    function desiredFanPercentFor(entry) {
        return fanControl ? fanControl.desiredPercentFor(entry) : -1;
    }

    function setDesiredFanPercent(entry, percent) {
        if (fanControl)
            fanControl.setDesiredPercent(entry, percent);
    }

    function clearDesiredFanPercent(entry) {
        if (fanControl)
            fanControl.clearDesiredPercent(entry);
    }

    function pendingFanPercentFor(entry) {
        return fanControl ? fanControl.pendingPercentFor(entry) : -1;
    }

    function writeFanControl(entry, action, percent) {
        if (fanControl)
            fanControl.writeControl(entry, action, percent);
    }

    function writeFanPercent(entry, percent) {
        if (fanControl)
            fanControl.writePercent(entry, percent);
    }

    function celsiusToFahrenheit(value) {
        return (Number(value || 0) * 9 / 5) + 32;
    }

    function formatThermalMenuTemp(value) {
        const c = Number(value || 0);
        const f = celsiusToFahrenheit(c);
        return f.toFixed(1) + "°F / " + c.toFixed(1) + "°C";
    }

    function thermalColorForCelsius(value) {
        const temp = Number(value || 0);
        if (temp < 30) return Colors.white;
        if (temp < 40) return Colors.yellow;
        if (temp < 50) return Colors.omnitrix;
        if (temp < 60) return Colors.cyan;
        if (temp < 70) return Colors.orange;
        if (temp < 80) return Colors.magenta;
        return Colors.red;
    }

    function thermalAccent(entry) {
        if (entry && entry.sensorKind === "fan")
            return Colors.omnitrix;
        return thermalColorForCelsius(Number(entry && entry.tempC || 0));
    }

    function thermalSimplePurpose(entry) {
        if (!entry)
            return "";

        const name = String(entry.name || entry.label || "sensor");
        const chip = String(entry.chip || "hardware");
        const lower = (name + " " + chip).toLowerCase();

        if (entry.sensorKind === "fan")
            return "COOLING FAN • Moves heat away from the hardware. This reading shows how fast it is spinning right now; higher RPM means more cooling effort.";
        if (lower.indexOf("nvme") !== -1 || lower.indexOf("ssd") !== -1)
            return "DRIVE TEMPERATURE • Measures how hot this SSD/NVMe device is right now. Use it to see whether storage is heating up under load.";
        if (lower.indexOf("gpu") !== -1 || lower.indexOf("nvidia") !== -1
                || lower.indexOf("nouveau") !== -1 || lower.indexOf("amdgpu") !== -1)
            return "GPU TEMPERATURE • Measures heat from the graphics hardware. It normally rises while rendering, gaming, video work, or other GPU-heavy tasks.";
        if (lower.indexOf("package") !== -1 || lower.indexOf("core") !== -1
                || lower.indexOf("cpu") !== -1 || lower.indexOf("k10temp") !== -1
                || lower.indexOf("coretemp") !== -1)
            return "CPU TEMPERATURE • Measures heat from the processor or one of its cores. It rises when the CPU is doing more work.";
        if (lower.indexOf("pch") !== -1 || lower.indexOf("chipset") !== -1)
            return "CHIPSET TEMPERATURE • Measures heat from the motherboard chipset that helps connect and coordinate system devices.";

        return "TEMPERATURE SENSOR • Measures the heat reported by " + name
               + " on " + chip + ". Use it to see whether that hardware is warming up or cooling down.";
    }
}
