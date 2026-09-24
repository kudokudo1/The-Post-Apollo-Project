import QtQuick
import "../../components"

QtObject {
    id: hunterPresentation

    required property var presentationState

    // HUNTER metric mode is intentionally external state: AppControl and CPU++
    // may each choose the active metric while sharing the same interpretation.
    property int metricMode: metricCombined

    readonly property int metricCombined: 0
    readonly property int metricCpu: 1
    readonly property int metricMemory: 2
    readonly property int metricIo: 3
    readonly property int metricAge: 4
    readonly property string combiIcon: "°⋆ꙮ๋࣭⭑."

    function taskHistoryValues(entry) {
        if (!entry)
            return [];

        const pid = Number(entry.pid || 0);
        if (pid <= 0)
            return [];

        const values =
            presentationState.taskMiniCpuHistories["pid:" + String(pid)];

        return Array.isArray(values) ? values : [];
    }

    function taskPeak(entry) {
        const values = taskHistoryValues(entry);
        let peak = Math.max(0, Number(entry && entry.cpuInstant || 0));

        for (let i = 0; i < values.length; i++)
            peak = Math.max(peak, Number(values[i] || 0));

        return peak;
    }

    function taskAverage(entry) {
        const values = taskHistoryValues(entry);

        if (values.length === 0)
            return Math.max(0, Number(entry && entry.cpuInstant || 0));

        let total = 0;
        const start = Math.max(0, values.length - 16);

        for (let i = start; i < values.length; i++)
            total += Number(values[i] || 0);

        return total / Math.max(1, values.length - start);
    }

    function taskMemoryMiB(entry) {
        return Math.max(0, Number(entry && entry.rss || 0)) / 1024.0;
    }

    function taskIoRate(entry) {
        return Math.max(0, Number(entry && entry.ioRate || 0));
    }

    function elapsedSeconds(value) {
        const raw = String(value || "").trim();
        if (!raw)
            return 0;

        let days = 0;
        let clock = raw;
        const dash = raw.indexOf("-");

        if (dash >= 0) {
            days = Number(raw.substring(0, dash) || 0);
            clock = raw.substring(dash + 1);
        }

        const parts = clock.split(":").map(function(part) {
            return Number(part || 0);
        });

        let seconds = days * 86400;

        if (parts.length === 3)
            seconds += parts[0] * 3600 + parts[1] * 60 + parts[2];
        else if (parts.length === 2)
            seconds += parts[0] * 60 + parts[1];
        else if (parts.length === 1)
            seconds += parts[0];

        return seconds;
    }

    function taskMetricScore(entry) {
        if (!entry)
            return 0;

        if (metricMode === metricCpu)
            return taskPeak(entry) + taskAverage(entry) * 0.55;

        if (metricMode === metricMemory)
            return taskMemoryMiB(entry);

        if (metricMode === metricIo)
            return taskIoRate(entry);

        if (metricMode === metricAge)
            return elapsedSeconds(entry.elapsed);

        const ioMiB = taskIoRate(entry) / (1024.0 * 1024.0);

        return taskPeak(entry)
               + taskAverage(entry) * 0.55
               + Math.max(0, Number(entry.mem || 0)) * 0.35
               + Math.log(1 + ioMiB) * 3.0;
    }

    function detailMetricKey() {
        if (metricMode === metricCpu) return "cpu";
        if (metricMode === metricMemory) return "mem";
        if (metricMode === metricIo) return "io";
        if (metricMode === metricAge) return "age";
        return "combined";
    }

    function detailHistory() {
        const key = detailMetricKey();
        const values = presentationState.taskHunterDetailHistories[key];
        return Array.isArray(values) ? values : [];
    }

    function metricAccent() {
        if (metricMode === metricCpu) return Colors.orange;
        if (metricMode === metricMemory) return Colors.magenta;
        if (metricMode === metricIo) return Colors.cyan;
        if (metricMode === metricAge) return Colors.white;
        return Colors.yellow;
    }

    function metricGraphLabel() {
        if (metricMode === metricCpu) return "CPU";
        if (metricMode === metricMemory) return "MEMORY";
        if (metricMode === metricIo) return "I/O";
        if (metricMode === metricAge) return "AGE";
        return combiIcon;
    }

    function metricGraphRange() {
        if (metricMode === metricIo)
            return 0.25;

        if (metricMode === metricAge)
            return 1.0;

        return 5.0;
    }

    function metricRangeForKey(metric) {
        const key = String(metric || "");

        if (key === "io")
            return 0.25;

        if (key === "age")
            return 1.0;

        return 5.0;
    }

    function formatBytesPerSecond(value) {
        let n = Math.max(0, Number(value || 0));
        const units = ["B/s", "KiB/s", "MiB/s", "GiB/s"];
        let i = 0;

        while (n >= 1024 && i < units.length - 1) {
            n /= 1024;
            i++;
        }

        return (i === 0 ? n.toFixed(0) : n.toFixed(1)) + " " + units[i];
    }

    function formatAge(seconds) {
        let value = Math.max(0, Math.floor(Number(seconds || 0)));
        const days = Math.floor(value / 86400);
        value %= 86400;
        const hours = Math.floor(value / 3600);
        value %= 3600;
        const minutes = Math.floor(value / 60);

        if (days > 0)
            return String(days) + "d " + String(hours) + "h";

        if (hours > 0)
            return String(hours) + "h " + String(minutes) + "m";

        return String(minutes) + "m";
    }

    function metricGraphValue(entry) {
        const history = detailHistory();
        const liveValue =
            Array.isArray(history) && history.length > 0
            ? Number(history[history.length - 1] || 0)
            : NaN;

        if (metricMode === metricCpu) {
            return isNaN(liveValue)
                   ? Number(
                         entry && entry.cpuInstant !== undefined
                         ? entry.cpuInstant
                         : entry && entry.cpu || 0
                     ).toFixed(1) + "%"
                   : liveValue.toFixed(1) + "%";
        }

        if (metricMode === metricMemory) {
            return isNaN(liveValue)
                   ? taskMemoryMiB(entry).toFixed(0) + " MiB"
                   : liveValue.toFixed(0) + " MiB";
        }

        if (metricMode === metricIo) {
            return isNaN(liveValue)
                   ? formatBytesPerSecond(taskIoRate(entry))
                   : formatBytesPerSecond(
                         liveValue * 1024.0 * 1024.0
                     );
        }

        if (metricMode === metricAge) {
            return isNaN(liveValue)
                   ? formatAge(elapsedSeconds(entry && entry.elapsed))
                   : formatAge(liveValue * 60.0);
        }

        return isNaN(liveValue)
               ? taskMetricScore(entry).toFixed(1)
               : liveValue.toFixed(1);
    }
}
