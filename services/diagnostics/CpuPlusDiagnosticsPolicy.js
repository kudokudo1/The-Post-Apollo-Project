// Fixed, read-only diagnostic catalog. No caller-supplied arguments.
function argumentsFor(kind, resolvePath) {
    const prefix = ["/usr/bin/timeout", "--kill-after=3s", "145s",
                    "/usr/bin/python3", "-B"];
    if (kind === "memory")
        return prefix.concat([resolvePath("scripts/cpuplus_quickshell_memory_observer.py"),
                             "--duration", "120", "--interval", "10"]);
    if (kind === "inventory")
        return prefix.concat([resolvePath("scripts/cpuplus_qml_workload_inventory.py")]);
    if (kind === "census")
        return prefix.concat([resolvePath("scripts/cpuplus_process_census.py"),
                             "--duration", "30", "--interval", "10"]);
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
        if (kind === "census") {
            const records = text.trim().split("\n").map(line => JSON.parse(line));
            const final = records.pop();
            if (!final || final.schema !== "post-apollo-process-census-v1"
                    || final.event !== "complete" || final.samples !== records.length
                    || records.length < 1 || records.length > 6) return null;
            const nullable = value => value === null || numeric(value);
            if (records.some((sample, index) =>
                    sample.schema !== final.schema || sample.event !== "census"
                    || sample.scope !== "same-user" || sample.sequence !== index + 1
                    || !Number.isSafeInteger(sample.observed) || sample.observed <= 0
                    || !Number.isSafeInteger(sample.cpuMeasured) || sample.cpuMeasured < 0
                    || sample.cpuMeasured > sample.observed
                    || !Number.isSafeInteger(sample.ioMeasured) || sample.ioMeasured < 0
                    || sample.ioMeasured > sample.observed
                    || !sample.coverage || !sample.previousCoverage
                    || typeof sample.coverage.truncated !== "boolean"
                    || typeof sample.previousCoverage.truncated !== "boolean"
                    || !Array.isArray(sample.rows) || !sample.rows.length
                    || sample.rows.length > Math.min(32, sample.observed)
                    || sample.rows.some(row => !Number.isSafeInteger(row.pid) || row.pid <= 0
                        || typeof row.name !== "string" || !numeric(row.rssKiB)
                        || !nullable(row.cpuPct) || !nullable(row.readBps)
                        || !nullable(row.writeBps)))) return null;
            const last = records[records.length - 1];
            const top = key => last.rows.filter(row => row[key] !== null)
                .sort((a, b) => b[key] - a[key] || a.pid - b.pid)[0];
            const cpu = top("cpuPct"), ram = top("rssKiB"), write = top("writeBps");
            const label = row => row.name.replace(/[\x00-\x1f\x7f]/g, "?") + " #" + row.pid;
            const limited = records.some(row => row.coverage.truncated || row.previousCoverage.truncated);
            return "SAME-USER // " + last.observed + " observed / " + records.length + " samples"
                + (limited ? " // SCAN LIMIT REACHED" : "")
                + "\nCPU / I-O COVERAGE // " + last.cpuMeasured + " / " + last.ioMeasured
                + "\nTOP CPU // " + (cpu ? label(cpu) + " " + cpu.cpuPct.toFixed(1) + "%" : "UNAVAILABLE")
                + "\nTOP RSS // " + (ram ? label(ram) + " " + (ram.rssKiB / 1048576).toFixed(2) + " GiB" : "UNAVAILABLE")
                + "\nTOP WRITE // " + (write ? label(write) + " " + (write.writeBps / 1024).toFixed(1) + " KiB/s" : "UNAVAILABLE")
                + "\nLAST INTERVAL // RSS IS NOT UNIQUE RAM";
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
