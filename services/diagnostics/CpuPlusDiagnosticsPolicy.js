// Fixed, read-only diagnostic catalog. No caller-supplied arguments.
function argumentsFor(kind, resolvePath) {
    const prefix = ["/usr/bin/timeout", "--kill-after=3s", "145s",
                    "/usr/bin/python3", "-B"];
    if (kind === "memory")
        return prefix.concat([resolvePath("scripts/cpuplus_quickshell_memory_observer.py"),
                             "--duration", "120", "--interval", "10"]);
    if (kind === "inventory")
        return prefix.concat([resolvePath("scripts/cpuplus_qml_workload_inventory.py")]);
    if (kind === "threads")
        return prefix.concat([resolvePath("scripts/syntagma_quickshell_thread_sampler.py"),
                             "--duration", "30", "--interval", "1", "--top", "4"]);
    return null;
}

function numeric(value) {
    return typeof value === "number" && Number.isFinite(value) && value >= 0;
}

function summarize(kind, text) {
    try {
        if (kind === "inventory") {
            const data = JSON.parse(text);
            if (data.schema !== "post-apollo-qml-workload-inventory-v1"
                    || !numeric(data.scannedQml) || data.scannedQml !== data.trackedQml
                    || !Array.isArray(data.skipped) || data.skipped.length
                    || !data.totals || !numeric(data.totals.Timer)
                    || !numeric(data.totals.Process) || !numeric(data.totals.Repeater))
                return null;
            return "QML // " + data.scannedQml + " files\nSOURCE MARKERS // "
                + data.totals.Timer + " timers / " + data.totals.Process
                + " processes / " + data.totals.Repeater + " repeaters";
        }
        if (kind !== "memory" && kind !== "threads") return null;
        const records = text.trim().split("\n").map(line => JSON.parse(line));
        const final = records[records.length - 1];
        if (!final || final.event !== "complete" || !numeric(final.pid)) return null;
        const rows = records.filter(row => row.event === kind);
        if (!rows.length || records.some(row => row.event === "stopped")
                || rows.some(row => row.pid !== final.pid)) return null;
        if (kind === "memory") {
            if (rows.some(row => row.startTicks !== final.startTicks || !row.memoryKiB
                    || !numeric(row.memoryKiB.Pss) || !numeric(row.memoryKiB.SwapPss)
                    || (row.cpuPct !== null && !numeric(row.cpuPct)))) return null;
            const gib = value => (value / 1048576).toFixed(2);
            const peak = Math.max(...rows.map(row => row.memoryKiB.Pss));
            const swap = Math.max(...rows.map(row => row.memoryKiB.SwapPss));
            const cpu = Math.max(0, ...rows.map(row => row.cpuPct || 0));
            return "PID // " + final.pid + "   SAMPLES // " + rows.length
                + "\nPSS START / PEAK / FINAL // " + gib(rows[0].memoryKiB.Pss)
                + " / " + gib(peak) + " / " + gib(rows[rows.length - 1].memoryKiB.Pss)
                + " GiB\nSWAP PSS PEAK // " + gib(swap)
                + " GiB   CPU PEAK // " + cpu.toFixed(1) + "%";
        }
        if (rows.some(row => !numeric(row.totalCpuPct))) return null;
        const peak = Math.max(...rows.map(row => row.totalCpuPct));
        return "PID // " + final.pid + "   SAMPLES // " + rows.length
            + "\nTHREAD CPU PEAK // " + peak.toFixed(1) + "% (ONE CORE = 100%)";
    } catch (error) {
        return null;
    }
}
