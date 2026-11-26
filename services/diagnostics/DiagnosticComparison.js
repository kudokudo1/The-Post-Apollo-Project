// Bounded, presentation-only comparisons of exact archived capture pairs.
// No source inspection, subprocesses, IO or automatic performance verdicts.
function nonnegative(value) {
    return typeof value === "number" && Number.isFinite(value) && value >= 0;
}

function metric(label, value, unit, digits) {
    return {label: label, value: value, unit: unit, digits: digits};
}

function memoryMetrics(rows, final) {
    if (rows.length < 2 || rows.length > 361
            || !Number.isSafeInteger(final.pid) || final.pid <= 0
            || !Number.isSafeInteger(final.startTicks)
            || rows.some(r => r.event !== "memory" || r.pid !== final.pid
                || r.startTicks !== final.startTicks || !r.memoryKiB
                || !nonnegative(r.memoryKiB.Pss) || !nonnegative(r.memoryKiB.SwapPss)))
        return null;
    if (rows[0].sampleIntervalMs !== null || rows[0].cpuPct !== null) return null;
    // Legacy captures have neither additive field. Never substitute zero.
    const privateValues = rows.map(r => {
        const m = r.memoryKiB;
        const hasClean = Object.prototype.hasOwnProperty.call(m, "Private_Clean");
        const hasTotal = Object.prototype.hasOwnProperty.call(r, "privateResidentKiB");
        if (!hasClean && !hasTotal) return null;
        const count = v => Number.isSafeInteger(v) && v >= 0;
        if (!hasClean || !hasTotal || !count(m.Private_Clean) || !count(m.Private_Dirty)
                || !count(m.Rss) || !count(r.privateResidentKiB)
                || r.privateResidentKiB !== m.Private_Clean + m.Private_Dirty
                || r.privateResidentKiB > m.Rss) throw Error("private resident evidence");
        return r.privateResidentKiB;
    });
    const hasPrivate = privateValues.every(v => v !== null);
    const footprint = rows.map(r => r.memoryKiB.Pss + r.memoryKiB.SwapPss);
    let duration = 0, cpu = 0, memory = 0, cpuPeak = 0;
    for (let i = 1; i < rows.length; ++i) {
        const r = rows[i], previous = rows[i - 1], ms = r.sampleIntervalMs;
        if (!nonnegative(ms) || ms <= 0 || !nonnegative(r.cpuPct)) return null;
        duration += ms;
        cpu += ms * r.cpuPct;
        cpuPeak = Math.max(cpuPeak, r.cpuPct);
        memory += ms * (previous.memoryKiB.Pss + r.memoryKiB.Pss) / 2;
    }
    const gib = value => value / 1048576;
    const last = rows[rows.length - 1];
    return [
        metric("SAMPLES", rows.length, "", 0),
        metric("OBSERVED TIME", duration / 1000, "s", 1),
        metric("PSS START", gib(rows[0].memoryKiB.Pss), "GiB", 3),
        metric("PSS PEAK", gib(Math.max(...rows.map(r => r.memoryKiB.Pss))), "GiB", 3),
        metric("PSS MEAN (EST.)", gib(memory / duration), "GiB", 3),
        metric("PSS FINAL", gib(last.memoryKiB.Pss), "GiB", 3),
        metric("PSS NET CHANGE", (last.memoryKiB.Pss - rows[0].memoryKiB.Pss) / 1024, "MiB", 1),
        metric("SWAP PSS PEAK", Math.max(...rows.map(r => r.memoryKiB.SwapPss)) / 1024, "MiB", 1),
        metric("PSS + SWAP PSS START", gib(footprint[0]), "GiB", 3),
        metric("PSS + SWAP PSS FINAL", gib(footprint[footprint.length-1]), "GiB", 3),
        metric("PSS + SWAP PSS NET CHANGE", (footprint[footprint.length-1]-footprint[0])/1024, "MiB", 1),
        metric("PRIVATE RESIDENT START", hasPrivate ? gib(privateValues[0]) : null, "GiB", 3),
        metric("PRIVATE RESIDENT FINAL", hasPrivate ? gib(privateValues[privateValues.length-1]) : null, "GiB", 3),
        metric("PRIVATE RESIDENT NET CHANGE", hasPrivate ? (privateValues[privateValues.length-1]-privateValues[0])/1024 : null, "MiB", 1),
        metric("CPU MEAN", cpu / duration, "%", 1),
        metric("CPU PEAK", cpuPeak, "%", 1)
    ];
}

function threadMetrics(rows, final) {
    const start = rows.shift();
    if (!start || start.event !== "start" || start.pid !== final.pid
            || !Number.isSafeInteger(final.pid) || final.pid <= 0
            || !rows.length || rows.length > 1800) return null;
    let duration = 0, cpu = 0, main = 0, mainAvailable = true;
    for (const r of rows) {
        if (r.event !== "threads" || r.pid !== final.pid
                || !nonnegative(r.sampleIntervalMs) || r.sampleIntervalMs <= 0
                || !nonnegative(r.totalCpuPct) || !nonnegative(r.threadCount)) return null;
        duration += r.sampleIntervalMs;
        cpu += r.sampleIntervalMs * r.totalCpuPct;
        if (!r.main || r.main.tid !== final.pid || !nonnegative(r.main.cpuPct))
            mainAvailable = false;
        else main += r.sampleIntervalMs * r.main.cpuPct;
    }
    return [
        metric("SAMPLES", rows.length, "", 0),
        metric("OBSERVED TIME", duration / 1000, "s", 1),
        metric("THREAD CPU MEAN", cpu / duration, "%", 1),
        metric("THREAD CPU PEAK", Math.max(...rows.map(r => r.totalCpuPct)), "%", 1),
        metric("MAIN CPU MEAN", mainAvailable ? main / duration : null, "%", 1),
        metric("THREAD COUNT PEAK", Math.max(...rows.map(r => r.threadCount)), "", 0)
    ];
}

function censusMetrics(rows) {
    const last = rows[rows.length - 1];
    const focus = last.rows.filter(r => r.name === "quickshell");
    // No aggregation over a top-N sample; ambiguous or missing shell -> unavailable.
    const shell = focus.length === 1 ? focus[0] : null;
    const get = (key, divisor) => shell && nonnegative(shell[key]) ? shell[key] / divisor : null;
    const limited = rows.some(r => r.coverage.truncated || r.previousCoverage.truncated);
    if (limited) return null;
    return [
        metric("SAMPLES", rows.length, "", 0),
        metric("OBSERVED PROCESSES (FINAL)", last.observed, "", 0),
        metric("CPU COVERAGE (FINAL)", 100 * last.cpuMeasured / last.observed, "%", 1),
        metric("I/O COVERAGE (FINAL)", 100 * last.ioMeasured / last.observed, "%", 1),
        metric("QS RSS (FINAL)", get("rssKiB", 1048576), "GiB", 3),
        metric("QS CPU (FINAL)", get("cpuPct", 1), "%", 1),
        metric("QS READ (FINAL)", get("readBps", 1024), "KiB/s", 1),
        metric("QS WRITE (FINAL)", get("writeBps", 1024), "KiB/s", 1)
    ];
}

function extract(report, validate, appMetrics) {
    if (!report || report.status !== "COMPLETE" || typeof report.text !== "string"
            || report.text.length > 65536 || !validate(report.kind, report.text)) return null;
    if (report.kind === "appcontrol") {
        const d = typeof appMetrics === "function" ? appMetrics(report.text) : null;
        if (!d) return null;
        return [metric("OBSERVED TIME",d.durationMs/1000,"s",1),
            ...["all","app","kill"].flatMap(key=>[metric(key.toUpperCase()+" TOTAL CPU",d[key].total,"%",1),
                metric(key.toUpperCase()+" MAIN CPU",d[key].main,"%",1),metric(key.toUpperCase()+" SAMPLES",d[key].count,"",0)]),
            metric("OPENINGS",d.openings,"",0),metric("OPEN MEAN",d.openingMean,"ms",1),metric("OPEN MAX",d.openingMax,"ms",1)];
    }
    if (report.kind === "inventory") {
        const d = JSON.parse(report.text);
        return [metric("QML FILES", d.scannedQml, "", 0),
                metric("TIMER MARKERS", d.totals.Timer, "", 0),
                metric("PROCESS MARKERS", d.totals.Process, "", 0),
                metric("REPEATER MARKERS", d.totals.Repeater, "", 0)];
    }
    const rows = report.text.trim().split("\n").map(line => JSON.parse(line));
    const final = rows.pop();
    if (!final || final.event !== "complete") return null;
    if (report.kind === "memory") return memoryMetrics(rows, final);
    if (report.kind === "threads") return threadMetrics(rows, final);
    if (report.kind === "census") return censusMetrics(rows);
    if (report.kind === "storage") {
        const last = rows[rows.length - 1];
        return [metric("OBSERVED TIME", last.elapsedMs / 1000, "s", 1),
                metric("SAMPLED INTERVALS", last.intervals, "", 0),
                ...last.rows.map(row => metric(row.id + " CHANGED INTERVALS",
                    row.unavailableIntervals === 0 && row.initialState === "present"
                        && row.finalState === "present" ? row.changedIntervals : null, "", 0))];
    }
    return null;
}

function compare(before, after, validate, appMetrics) {
    const fail = error => ({error: error, rows: [], note: ""});
    if (!before || !after) return fail("SELECT TWO RETAINED CAPTURES");
    if (before.id === after.id) return fail("SELECT DIFFERENT CAPTURES");
    if (before.kind !== after.kind) return fail("CAPTURE TYPES MUST MATCH");
    if (before.status !== "COMPLETE" || after.status !== "COMPLETE")
        return fail("COMPLETED CAPTURES ONLY");
    const firstTime = Date.parse(before.finishedAt), secondTime = Date.parse(after.finishedAt);
    if (!Number.isFinite(firstTime) || !Number.isFinite(secondTime) || secondTime <= firstTime)
        return fail("AFTER MUST BE NEWER THAN BEFORE");
    try {
        if (["memory","census","storage"].includes(before.kind)) {
            const terminal=report=>JSON.parse(report.text.trim().split("\n").pop());
            const x=terminal(before), y=terminal(after);
            if (x.workshopSchema || y.workshopSchema || x.calibration || y.calibration) {
                if (x.workshopSchema!==y.workshopSchema || !x.calibration || !y.calibration
                        || x.calibration.kind!==y.calibration.kind
                        || x.calibration.durationSeconds!==y.calibration.durationSeconds
                        || x.calibration.intervalMs!==y.calibration.intervalMs
                        || x.calibration.sampleSeconds!==y.calibration.sampleSeconds
                        || x.calibration.reportSeconds!==y.calibration.reportSeconds)
                    return fail("OBSERVER CALIBRATION MUST MATCH");
            }
        }
        if (before.kind==="threads") {
            const first=JSON.parse(before.text.trim().split("\n",1)[0]);
            const second=JSON.parse(after.text.trim().split("\n",1)[0]);
            if (first.workshopSchema || second.workshopSchema) {
                if (first.workshopSchema!==second.workshopSchema
                        || first.durationSeconds!==second.durationSeconds
                        || first.intervalMs!==second.intervalMs || first.topCount!==second.topCount)
                    return fail("THREAD CALIBRATION MUST MATCH");
            }
        }
        const a = extract(before, validate, appMetrics), b = extract(after, validate, appMetrics);
        if (!a || !b || a.length !== b.length) return fail("INCOMPLETE OR UNSUPPORTED EVIDENCE");
        const rows = a.map((left, i) => {
            const right = b[i], x = left.value, y = right.value;
            if (left.label !== right.label || left.unit !== right.unit
                    || [x,y].some(v => v !== null && !Number.isFinite(v))) throw Error("metrics");
            return {label:left.label, unit:left.unit, digits:left.digits,
                    before:x, after:y, delta:x === null || y === null ? null : y - x};
        });
        let note = "Observed differences only. Match hardware, workload, duration and deployed revision manually; archive does not attest those conditions.";
        if (before.kind === "inventory") note = "Source declaration counts only; not running objects or performance. " + note;
        if (before.kind === "memory") {
            const first = JSON.parse(before.text.trim().split("\n", 1)[0]);
            const second = JSON.parse(after.text.trim().split("\n", 1)[0]);
            const changed = first.pid !== second.pid || first.startTicks !== second.startTicks;
            note = (changed ? "PROCESS IDENTITY CHANGED // separate process observations, not continuous growth. "
                : "PID/start ticks match; boot identity and continuity between captures are unverified. ")
                + "PSS + SwapPss is a proportional footprint estimate, not physical swap cost. Private resident excludes separately accounted hugetlb; legacy or partial private readings are N/A. No component attribution. PSS mean is a time-weighted trapezoid estimate; CPU mean is interval-weighted. " + note;
        }
        if (before.kind === "appcontrol") note = "Whole capture includes closed/other; APP/KILL include only stable-mode intervals. Opening is synchronous, not first paint. Thread sums may omit exiting threads. " + note;
        if (before.kind === "threads") note = "Thread sums may omit exiting threads. " + note;
        if (before.kind === "storage") note = "Sampled metadata changes only; not writes, transactions or writer identity. Missing/unavailable endpoints are N/A. " + note;
        if (before.kind === "census") note = "Final intervals only; RSS is not PSS. Top-N rows are not totals. QS requires one returned exact-name match; identity and absence of omitted matches are not proven. " + note;
        const duration = rows.find(r => r.label === "OBSERVED TIME");
        if (duration && Math.abs(duration.delta) > Math.max(2, duration.before * 0.1))
            note = "UNEQUAL DURATIONS // peak and mean comparisons need caution. " + note;
        return {error:"", rows:rows, note:note};
    } catch (error) {
        return fail("INCOMPLETE OR UNSUPPORTED EVIDENCE");
    }
}
