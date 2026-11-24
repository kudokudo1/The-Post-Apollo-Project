function archiveResponse(doc, submitted) {
    if (!doc || doc.schema !== "post-apollo-diagnostic-archive-v1"
            || !Array.isArray(doc.rows) || doc.rows.length > 8 || !submitted) return null;
    const ids = [];
    for (const row of doc.rows) {
        if (!row || !validKind(row.kind) || !validReportId(row.id) || ids.indexOf(row.id) >= 0
                || ["COMPLETE", "CANCELLED", "NOT VERIFIED"].indexOf(row.status) < 0
                || typeof row.summary !== "string" || row.summary.length > 4096
                || typeof row.text !== "string" || row.text.length > 65536
                || typeof row.finishedAt !== "string"
                || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(row.finishedAt)) return null;
        ids.push(row.id);
    }
    if (submitted.action === "list") return doc.savedId === null ? doc.rows : null;
    if (submitted.action !== "save" || !submitted.record || doc.savedId !== submitted.record.id) return null;
    const exact = doc.rows.find(row => row.id === doc.savedId);
    if (!exact || ["kind","id","status","summary","text","finishedAt"].some(
            key => exact[key] !== submitted.record[key])) return null;
    return doc.rows;
}

function validKind(kind) {
    return ["memory", "inventory", "threads", "census", "storage"].indexOf(kind) >= 0;
}

function validReportId(id) {
    return typeof id === "string" && /^[a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[1-9][0-9]*$/.test(id)
        && id.length <= 128;
}

function noticeFor(job, report) {
    if (!validKind(job) || !report || !validReportId(report.id)
            || ["COMPLETE", "CANCELLED", "NOT VERIFIED"].indexOf(report.status) < 0)
        return null;
    const labels = {memory: "MEMORY OBSERVE", inventory: "SOURCE WORKLOAD SCAN",
                    threads: "THREAD SAMPLE", census: "PROCESS CENSUS", storage: "STORAGE OBSERVE"};
    return {
        id: "apollo-cpu-diag-" + report.id,
        source: "CPU++",
        sourceId: "cpu-plus-diagnostics",
        category: "internal",
        severity: report.status === "COMPLETE" ? "normal" : "warning",
        title: labels[job] + " // " + report.status,
        message: report.status === "COMPLETE" ? "Capture ready. Open DIAG or copy report."
            : report.status === "CANCELLED" ? "Stopped early. Partial output may be available."
            : "Capture not verified. Open DIAG for status.",
        tags: ["cpu-plus", "system", "diagnostics"],
        context: {origin: "apollo", domain: "system", eventType: "diagnostic-result",
                  reportKind: job, reportId: report.id}
    };
}

function referenceFor(entry) {
    if (!entry || entry.sourceId !== "cpu-plus-diagnostics") return null;
    const ctx = entry.context;
    if (!ctx || ctx.eventType !== "diagnostic-result" || ctx.origin !== "apollo"
            || ctx.domain !== "system" || !validKind(ctx.reportKind)
            || !validReportId(ctx.reportId)
            || entry.id !== "apollo-cpu-diag-" + ctx.reportId) return null;
    return {kind: ctx.reportKind, id: ctx.reportId};
}

// Fixed, read-only diagnostic catalog. No caller-supplied arguments.
function argumentsFor(kind, resolvePath, dataDir) {
    const prefix = ["/usr/bin/timeout", "--kill-after=3s", "145s",
                    "/usr/bin/python3", "-B"];
    if (kind === "memory")
        return prefix.concat([resolvePath("scripts/cpuplus_quickshell_memory_observer.py"),
                             "--duration", "120", "--interval", "10"]);
    if (kind === "inventory")
        return prefix.concat([resolvePath("scripts/cpuplus_qml_workload_inventory.py")]);
    if (kind === "storage") {
        if (typeof dataDir !== "string" || !dataDir.startsWith("/")) return null;
        return prefix.concat([resolvePath("scripts/cpuplus_storage_observer.py"),
                             "--data-dir", dataDir, "--shell-dir", resolvePath("."), "--duration", "30"]);
    }
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
        if (kind === "storage") {
            const records = text.trim().split("\n").map(line => JSON.parse(line));
            const final = records.pop();
            const ids = ["notifications.history", "notifications.favorites", "notifications.policies",
                "notifications.scroll", "weather.cache", "weather.history", "weather.events",
                "weather.places", "weather.dossier", "hub.layout", "hub.notes", "hub.todo",
                "social.identities", "git.journal", "git.delta", "forest.preferences",
                "finance.manual", "company.hubs"];
            const states = ["present", "absent", "unavailable"];
            const count = x => Number.isSafeInteger(x) && x >= 0;
            const size = (state, value) => state === "present" ? count(value) : value === null;
            if (!final || final.schema !== "post-apollo-storage-observation-v1"
                    || final.event !== "complete" || final.samples !== records.length
                    || records.length < 1 || records.length > 3) return null;
            if (records.some((sample, index) =>
                sample.schema !== final.schema || sample.event !== "storage"
                || sample.sequence !== index + 1 || !count(sample.intervals)
                || sample.intervals < 1 || sample.intervals > 30 || !count(sample.elapsedMs)
                || (index > 0 && (sample.intervals <= records[index-1].intervals
                    || sample.elapsedMs < records[index-1].elapsedMs))
                || !Array.isArray(sample.rows) || sample.rows.length !== ids.length
                || sample.rows.some((row, i) => !row || row.id !== ids[i]
                    || states.indexOf(row.initialState) < 0 || states.indexOf(row.finalState) < 0
                    || !size(row.initialState,row.initialBytes) || !size(row.finalState,row.finalBytes)
                    || !count(row.changedIntervals) || !count(row.replacementIntervals)
                    || !count(row.unavailableIntervals) || !count(row.comparableIntervals)
                    || row.comparableIntervals + row.unavailableIntervals !== sample.intervals
                    || row.changedIntervals > row.comparableIntervals
                    || row.replacementIntervals > row.changedIntervals
                    || (index > 0 && (row.initialState !== records[index-1].rows[i].initialState
                        || row.initialBytes !== records[index-1].rows[i].initialBytes
                        || row.changedIntervals < records[index-1].rows[i].changedIntervals
                        || row.replacementIntervals < records[index-1].rows[i].replacementIntervals
                        || row.unavailableIntervals < records[index-1].rows[i].unavailableIntervals
                        || row.comparableIntervals < records[index-1].rows[i].comparableIntervals)))))
                return null;
            const last = records[records.length-1];
            const changed = last.rows.filter(row => row.changedIntervals > 0)
                .sort((a,b) => b.changedIntervals - a.changedIntervals);
            const unavailable = last.rows.filter(row => row.unavailableIntervals > 0).length;
            const absent = last.rows.filter(row => row.finalState === "absent").length;
            return "STORAGE METADATA // " + last.intervals + " intervals / " + ids.length + " targets"
                + "\nCHANGED TARGETS // " + changed.length + "   ABSENT AT END // " + absent
                + "\nUNAVAILABLE INTERVALS IN // " + unavailable + " targets"
                + (changed.length ? "\n" + changed.slice(0,5).map(row =>
                    row.id + " // " + row.changedIntervals + " changed intervals").join("\n") : "")
                + "\nNOT WRITE COUNTS OR WRITER IDENTITY";
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
