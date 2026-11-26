function archiveResponse(doc, submitted) {
    if (!doc || doc.schema !== "post-apollo-diagnostic-archive-v1"
            || !Array.isArray(doc.rows) || doc.rows.length > 8 || !submitted) return null;
    const ids = [];
    for (const row of doc.rows) {
        if (!row || !validKind(row.kind) || !validReportId(row.id) || ids.indexOf(row.id) >= 0
                || ["COMPLETE", "CANCELLED", "NOT VERIFIED"].indexOf(row.status) < 0
                || typeof row.summary !== "string" || row.summary.length > 4096
                || typeof row.text !== "string" || row.text.length > reportLimit(row.kind)
                || (row.kind === "workflow" && /[^\x00-\x7f]/.test(row.text))
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
    return ["memory", "inventory", "threads", "census", "storage", "appcontrol", "workflow", "stall"].indexOf(kind) >= 0;
}

function reportLimit(kind) { return kind === "workflow" ? 300000 : 65536; }

function validReportId(id) {
    return typeof id === "string" && /^[a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[1-9][0-9]*$/.test(id)
        && id.length <= 128;
}

function noticeFor(job, report) {
    if (!validKind(job) || !report || !validReportId(report.id)
            || ["COMPLETE", "CANCELLED", "NOT VERIFIED"].indexOf(report.status) < 0)
        return null;
    const labels = {memory: "MEMORY OBSERVE", inventory: "SOURCE WORKLOAD SCAN",
                    threads: "THREAD SAMPLE", census: "PROCESS CENSUS", storage: "STORAGE OBSERVE", appcontrol: "APPCONTROL TEST", workflow: "DIAGNOSTIC WORKFLOW", stall: "UI STALL OBSERVE"};
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
    if (kind === "appcontrol")
        return prefix.concat([resolvePath("scripts/syntagma_quickshell_thread_sampler.py"),
                             "--parent-quickshell", "--duration", "30", "--interval", "1", "--top", "4"]);
    if (kind === "threads")
        return prefix.concat([resolvePath("scripts/syntagma_quickshell_thread_sampler.py"),
                             "--duration", "30", "--interval", "1", "--top", "4"]);
    return null;
}

// Configured evidence remains JSONL, retaining existing archive and copy paths.
function configuredThreadEvidence(text, expected) {
    try {
        if (typeof text !== "string" || text.length > 65536) return null;
        const rows = text.trim().split("\n").map(line=>JSON.parse(line));
        const start = rows.shift(), end = rows.pop();
        const tag = "post-apollo-thread-calibration-v1";
        const int = (v,min,max)=>Number.isSafeInteger(v)&&v>=min&&v<=max;
        if (!start || !end || start.event !== "start" || end.event !== "complete"
                || start.workshopSchema !== tag || end.workshopSchema !== tag
                || !int(start.pid,1,Number.MAX_SAFE_INTEGER)
                || !int(start.startTicks,1,Number.MAX_SAFE_INTEGER)
                || !int(start.durationSeconds,1,120)
                || [100,250,500,1000,2000,5000].indexOf(start.intervalMs)<0
                || start.intervalMs>start.durationSeconds*1000
                || !int(start.topCount,1,12)
                || end.pid!==start.pid || end.startTicks!==start.startTicks
                || end.samples!==rows.length || !int(end.observedMs,start.durationSeconds*1000,145000))
            return null;
        const limit=Math.ceil(start.durationSeconds*1000/start.intervalMs);
        if (limit>30 || limit*(start.topCount+1)>150 || !rows.length || rows.length>limit)
            return null;
        if (expected && (expected.kind!=="threads" || expected.durationSeconds!==start.durationSeconds
                || expected.intervalMs!==start.intervalMs || expected.topCount!==start.topCount)) return null;
        let elapsed=0;
        for (const row of rows) {
            if (!row || row.event!=="threads" || row.pid!==start.pid || row.startTicks!==start.startTicks
                    || !int(row.sampleIntervalMs,1,145000) || !numeric(row.totalCpuPct)
                    || !int(row.threadCount,1,Number.MAX_SAFE_INTEGER)
                    || !Array.isArray(row.top) || row.top.length>Math.min(row.threadCount,start.topCount+1)
                    || !row.top.length || !row.main || row.main.tid!==start.pid || !numeric(row.main.cpuPct)
                    || row.top.some(t=>!t || !int(t.tid,1,Number.MAX_SAFE_INTEGER)||!numeric(t.cpuPct))
                    || new Set(row.top.map(t=>t.tid)).size!==row.top.length
                    || !row.top.some(t=>t.tid===start.pid && t.cpuPct===row.main.cpuPct)) return null;
            elapsed+=row.sampleIntervalMs;
        }
        if (Math.abs(elapsed-end.observedMs)>rows.length+1) return null;
        return {kind:"threads",durationSeconds:start.durationSeconds,intervalMs:start.intervalMs,topCount:start.topCount};
    } catch (_) { return null; }
}

// Observer receipts extend the terminal record rather than prepend a row,
// keeping existing memory, census and storage projections compatible.
function configuredEvidence(kind,text,expected) {
    if (kind==="threads") return configuredThreadEvidence(text,expected);
    try {
        if (!["memory","census","storage"].includes(kind) || typeof text!=="string" || text.length>65536) return null;
        const rows=text.trim().split("\n").map(line=>JSON.parse(line)), end=rows.pop();
        const c=end && end.calibration;
        const integer=(x,min,max)=>Number.isSafeInteger(x)&&x>=min&&x<=max;
        if (!end || end.event!=="complete" || end.workshopSchema!=="post-apollo-observer-calibration-v1"
                || !c || c.kind!==kind || !integer(c.durationSeconds,1,120)
                || !integer(end.observedMs,c.durationSeconds*1000,145000)
                || end.samples!==rows.length || !rows.length
                || rows.some(r=>!r || r.event!==kind)) return null;
        const keys=kind==="storage"?["kind","durationSeconds"]:["kind","durationSeconds","intervalMs"];
        if (Object.keys(c).length!==keys.length || keys.some(k=>!Object.prototype.hasOwnProperty.call(c,k))
                || (expected && keys.some(k=>expected[k]!==c[k]))) return null;
        if (kind==="storage") {
            if (c.durationSeconds>30 || rows.length!==Math.ceil(c.durationSeconds/10)
                    || rows.some((r,i)=>r.intervals!==Math.min((i+1)*10,c.durationSeconds))
                    || rows[rows.length-1].elapsedMs!==end.observedMs) return null;
        } else {
            const min=kind==="memory"?5000:1000;
            if (!integer(c.intervalMs,min,Math.min(60000,c.durationSeconds*1000)) || c.intervalMs%1000!==0) return null;
            const n=Math.ceil(c.durationSeconds*1000/c.intervalMs);
            if (kind==="census") {
                if (c.durationSeconds>60 || n>3 || rows.length>n
                        || rows.some((r,i)=>r.sequence!==i+1 || r.scope!=="same-user")) return null;
            } else {
                if (n>12 || rows.length<2 || rows.length>n+1 || !integer(end.pid,1,Number.MAX_SAFE_INTEGER)
                        || !integer(end.startTicks,1,Number.MAX_SAFE_INTEGER)
                        || rows.some(r=>r.pid!==end.pid || r.startTicks!==end.startTicks)
                        || rows[0].sampleIntervalMs!==null || rows[0].cpuPct!==null) return null;
                let elapsed=0;
                for (let i=1;i<rows.length;i++) {
                    if (!integer(rows[i].sampleIntervalMs,1,145000)||!numeric(rows[i].cpuPct)) return null;
                    elapsed+=rows[i].sampleIntervalMs;
                }
                if (Math.abs(elapsed-end.observedMs)>rows.length+1) return null;
            }
        }
        return c;
    } catch (_) { return null; }
}

function observerCalibrationSuffix(kind,text) {
    const lines=text.trim().split("\n");
    const final=JSON.parse(lines[lines.length-1]);
    if (!Object.prototype.hasOwnProperty.call(final,"workshopSchema")
            && !Object.prototype.hasOwnProperty.call(final,"calibration")) return "";
    const c=configuredEvidence(kind,text,null);
    if (!c) return null;
    return "\nCALIBRATION // "+c.durationSeconds+" s"
        +(kind==="storage"?" / 1000 ms metadata cadence":" / "+c.intervalMs+" ms");
}

function numeric(value) {
    return typeof value === "number" && Number.isFinite(value) && value >= 0;
}

// Optional host context. Never turn missing data into zero, sum overlapping
// memory counters, or infer a causal relation from a coincident PSS change.
function hostMemorySummary(rows) {
    if (!rows.some(row=>Object.prototype.hasOwnProperty.call(row,"hostObservation"))) return "";
    const keys=["MemTotal","MemAvailable","MemFree","AnonPages","Cached","Shmem",
        "SReclaimable","SUnreclaim","SwapTotal","SwapFree"];
    const count=value=>Number.isSafeInteger(value) && value>=0;
    const valid=value=>value && keys.every(key=>count(value[key]))
        && value.MemTotal>0 && value.MemAvailable<=value.MemTotal
        && value.MemFree<=value.MemTotal && value.SwapFree<=value.SwapTotal;
    const pairs=rows.map(row=>{
        const h=row.hostObservation;
        return h && numeric(h.spanMs) && valid(h.beforeKiB) && valid(h.afterKiB)
            && h.beforeKiB.MemTotal===h.afterKiB.MemTotal
            ? h : null;
    });
    const available=pairs.filter(Boolean);
    const mib=value=>(value/1024).toFixed(1);
    const signed=value=>(value>0?"+":"")+mib(value);
    let summary="\nHOST CONTEXT // "+available.length+"/"+rows.length+" paired samples";
    if (!available.length) return summary+" // UNAVAILABLE";
    const samples=available.flatMap(pair=>[pair.beforeKiB,pair.afterKiB]);
    const minimum=Math.min(...samples.map(value=>value.MemAvailable));
    const span=Math.max(...available.map(pair=>pair.spanMs));
    summary+="\nHOST AVAILABLE MIN (OBSERVED) // "+mib(minimum)+" MiB";
    summary+="\nHOST SAMPLE BRACKET MAX // "+span.toFixed(1)+" ms";
    const first=pairs[0], last=pairs[pairs.length-1];
    const complete=available.length===rows.length
        && samples.every(value=>value.MemTotal===samples[0].MemTotal);
    if (!complete) return summary+"\nHOST TREND // INCOMPLETE OR CHANGED CAPACITY";
    summary+="\nHOST AVAILABLE START / FINAL // "+mib(first.beforeKiB.MemAvailable)
        +" / "+mib(last.afterKiB.MemAvailable)+" MiB";
    if (rows.length>1) {
        summary+="\nHOST AVAILABLE CHANGE // "+signed(last.afterKiB.MemAvailable-first.beforeKiB.MemAvailable)+" MiB";
        summary+="\nQS PSS CHANGE // "+signed(rows[rows.length-1].memoryKiB.Pss-rows[0].memoryKiB.Pss)+" MiB";
    }
    return summary+"\nCORRELATION ONLY // CAUSE NOT ESTABLISHED";
}

// Bounded numeric opening markers plus the existing external thread sampler.
function combineAppControl(raw, modes, openings, overflow, killWork, work) {
    if (overflow || typeof raw !== "string" || raw.length > 65536) return null;
    try {
        const rows = raw.trim().split("\n").map(line => JSON.parse(line));
        const start = rows.shift(), end = rows.pop();
        if (!start || !end || start.event !== "start" || end.event !== "complete"
                || start.pid !== end.pid || start.durationSeconds !== 30
                || rows.some(row => row.event !== "threads" || row.pid !== start.pid
                    || !row.main || row.main.tid !== start.pid)) return null;
        const doc = {schema:"post-apollo-appcontrol-diagnostic-v1",pid:start.pid,
            startMs:start.tsMs,endMs:end.tsMs,modes:modes,openings:openings,
            samples:rows.map(row=>({tsMs:row.tsMs,intervalMs:row.sampleIntervalMs,
                total:row.totalCpuPct,main:row.main.cpuPct}))};
        if (killWork !== undefined) doc.killWork = killWork;
        if (work !== undefined) doc.work = work;
        const text = JSON.stringify(doc);
        return text.length <= 65536 && appControlMetrics(text) ? text : null;
    } catch (error) { return null; }
}
function appControlMetrics(text) {
    try {
        const d = JSON.parse(text);
        const stamp = n => Number.isSafeInteger(n) && n >= 0;
        const stages = ["graph-invalidation","mode-restore","selection","probe-schedule",
            "refresh-dispatch","focus","handler-total"];
        const selectionStages = ["selection-state","selection-row","selection-detail"];
        const detailedStages = stages.slice(0,2).concat(selectionStages,stages.slice(2));
        const workStages = ["cpu-history","hunter-history","history-revisions","task-order",
            "task-rows","metric-alerts","snapshot-selection","mini-cpu-history",
            "mini-hunter-history","mini-history-revisions"];
        if (!d || d.schema !== "post-apollo-appcontrol-diagnostic-v1"
                || !Number.isSafeInteger(d.pid) || d.pid <= 1
                || !stamp(d.startMs) || !stamp(d.endMs) || d.endMs < d.startMs
                || !Array.isArray(d.samples) || d.samples.length < 1 || d.samples.length > 32
                || !Array.isArray(d.modes) || !d.modes.length || d.modes.length > 128
                || !Array.isArray(d.openings) || d.openings.length > 140
                || d.modes.some((m,i)=>!m || !stamp(m.tsMs)
                    || ["closed","app","kill","other","unavailable"].indexOf(m.mode)<0
                    || (i>0 && m.tsMs<d.modes[i-1].tsMs))
                || d.modes[0].tsMs > d.startMs
                || d.samples.some((s,i)=>!s || !stamp(s.tsMs) || !stamp(s.intervalMs)
                    || s.intervalMs<=0 || s.tsMs<d.startMs || s.tsMs>d.endMs
                    || (i>0 && s.tsMs<=d.samples[i-1].tsMs)
                    || !numeric(s.total) || !numeric(s.main) || s.main>s.total+0.1)
                || d.openings.some(o=>!o || detailedStages.indexOf(o.stage)<0
                    || !Number.isSafeInteger(o.sequence) || o.sequence<1
                    || !stamp(o.tsMs) || !numeric(o.elapsedMs))) return null;
        const groups = {};
        for (const o of d.openings) {
            if (!groups[o.sequence]) groups[o.sequence]=[];
            groups[o.sequence].push(o);
        }
        const totals = [];
        const selection = {};
        for (const stage of selectionStages) selection[stage]=[];
        for (const group of Object.values(groups)) {
            const expected = group.some(o=>selectionStages.indexOf(o.stage)>=0) ? detailedStages : stages;
            if (group.length>expected.length
                    || group.some((o,i)=>o.stage!==expected[i] || (i && o.tsMs<group[i-1].tsMs))) return null;
            if (group.length !== expected.length) continue;
            const total=group[group.length-1];
            if (total.tsMs-total.elapsedMs>=d.startMs && total.tsMs<=d.endMs) {
                totals.push(total.elapsedMs);
                for (const o of group)
                    if (selectionStages.indexOf(o.stage)>=0) selection[o.stage].push(o.elapsedMs);
            }
        }
        const killWork = {};
        if (d.killWork !== undefined) {
            if (!Array.isArray(d.killWork) || d.killWork.length>512
                    || d.killWork.some((o,i)=>!o || workStages.indexOf(o.stage)<0
                        || !stamp(o.tsMs) || !numeric(o.elapsedMs)
                        || (i>0 && o.tsMs<d.killWork[i-1].tsMs))) return null;
            for (const o of d.killWork) {
                if (o.tsMs-o.elapsedMs<d.startMs || o.tsMs>d.endMs) continue;
                const v=killWork[o.stage] || {count:0,totalMs:0,maxMs:0};
                v.count++; v.totalMs+=o.elapsedMs; v.maxMs=Math.max(v.maxMs,o.elapsedMs);
                killWork[o.stage]=v;
            }
        }
        const observedWork = {};
        if (d.work !== undefined) {
            const moreStages = workStages.concat(["app-model-read","app-key-scan","app-index-write",
                "app-position-view","resource-reconcile","event-loop-gap"]);
            if (!Array.isArray(d.work) || d.work.length>256
                    || d.work.some((o,i)=>!o || moreStages.indexOf(o.stage)<0
                        || ["closed","app","kill","other","unavailable"].indexOf(o.mode)<0
                        || !stamp(o.tsMs) || !numeric(o.elapsedMs)
                        || (i>0 && o.tsMs<d.work[i-1].tsMs))) return null;
            for (const o of d.work) {
                if (o.tsMs-o.elapsedMs<d.startMs || o.tsMs>d.endMs) continue;
                const key=o.mode+" / "+o.stage;
                const v=observedWork[key] || {count:0,totalMs:0,maxMs:0};
                v.count++; v.totalMs+=o.elapsedMs; v.maxMs=Math.max(v.maxMs,o.elapsedMs);
                observedWork[key]=v;
            }
        }
        const weighted = rows => {
            const ms=rows.reduce((n,s)=>n+s.intervalMs,0);
            return {count:rows.length,ms:ms,
                total:ms?rows.reduce((n,s)=>n+s.total*s.intervalMs,0)/ms:null,
                main:ms?rows.reduce((n,s)=>n+s.main*s.intervalMs,0)/ms:null};
        };
        const buckets={app:[],kill:[]};
        for (const s of d.samples) {
            const from=s.tsMs-s.intervalMs;
            if (from<d.startMs) continue;
            const previous=d.modes.filter(m=>m.tsMs<=from).pop();
            if (!previous || !buckets[previous.mode]
                    || d.modes.some(m=>m.tsMs>from && m.tsMs<=s.tsMs)) continue;
            buckets[previous.mode].push(s);
        }
        return {pid:d.pid,durationMs:d.endMs-d.startMs,all:weighted(d.samples),
            app:weighted(buckets.app),kill:weighted(buckets.kill),
            selection:selection,killWork:killWork,work:observedWork,
            openings:totals.length,openingMean:totals.length?totals.reduce((a,b)=>a+b,0)/totals.length:null,
            openingMax:totals.length?Math.max(...totals):null};
    } catch (error) { return null; }
}
function summarize(kind, text) {
    if (kind === "stall") {
        const d=stallEvidence(text,null);
        return d ? "UI HEARTBEAT // "+d.coverageMs+" ms observed / "+d.durationSeconds+" s requested"
            +"\nTHRESHOLD // "+d.thresholdMs+" ms   GAPS // "+d.gaps.length+"   MAX // "+d.maxGapMs+" ms"
            +"\n100 ms nominal cadence; wall-clock callback intervals, not CPU attribution or proof of responsiveness." : null;
    }
    if (kind === "workflow") {
        const evidence=workflowEvidence(text,null);
        return evidence && evidence.status==="COLLECTED" ? evidence.summary : null;
    }
    try {
        if (kind === "appcontrol") {
            const d=appControlMetrics(text);
            if (!d) return null;
            const line=(name,x)=>name+" // "+(x.count?x.total.toFixed(1)+"% total / "+x.main.toFixed(1)+"% main ("+x.count+" samples)":"N/A");
            return "PID // "+d.pid+"\n"+line("MIXED / WHOLE CAPTURE",d.all)+"\n"+line("APP",d.app)+"\n"+line("KILL",d.kill)
                +"\nOPENINGS // "+d.openings+(d.openings?" / mean "+d.openingMean.toFixed(1)+" ms / max "+d.openingMax+" ms":" / N/A")
                +Object.keys(d.selection).filter(k=>d.selection[k].length).map(k=>"\n"+k.toUpperCase()+" // mean "+(d.selection[k].reduce((a,b)=>a+b,0)/d.selection[k].length).toFixed(1)+" ms").join("")
                +Object.keys(d.killWork).sort((a,b)=>d.killWork[b].totalMs-d.killWork[a].totalMs).map(k=>"\nKILL "+k.toUpperCase()+" // "+d.killWork[k].count+" calls / "+d.killWork[k].totalMs+" ms summed / "+d.killWork[k].maxMs+" ms max").join("")
                +Object.keys(d.work).sort((a,b)=>d.work[b].maxMs-d.work[a].maxMs).map(k=>"\n"+k.toUpperCase()+" // "+d.work[k].count+" calls / "+d.work[k].totalMs+" ms summed / "+d.work[k].maxMs+" ms max").join("")
                +"\nStable-mode CPU intervals only; whole capture includes closed/other. Work mode is observed at completion, not necessarily throughout the call. Event-loop gaps may overlap measured work; do not add them as CPU time. Stage timings are synchronous wall time, not CPU attribution or first paint. 100% = one core.";
        }
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
            const calibration=observerCalibrationSuffix(kind,text);
            if (calibration===null) return null;
            return "STORAGE METADATA // " + last.intervals + " intervals / " + ids.length + " targets"
                + "\nCHANGED TARGETS // " + changed.length + "   ABSENT AT END // " + absent
                + "\nUNAVAILABLE INTERVALS IN // " + unavailable + " targets"
                + (changed.length ? "\n" + changed.slice(0,5).map(row =>
                    row.id + " // " + row.changedIntervals + " changed intervals").join("\n") : "")
                + "\nNOT WRITE COUNTS OR WRITER IDENTITY" + calibration;
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
            const calibration=observerCalibrationSuffix(kind,text);
            if (calibration===null) return null;
            return "SAME-USER // " + last.observed + " observed / " + records.length + " samples"
                + (limited ? " // SCAN LIMIT REACHED" : "")
                + "\nCPU / I-O COVERAGE // " + last.cpuMeasured + " / " + last.ioMeasured
                + "\nTOP CPU // " + (cpu ? label(cpu) + " " + cpu.cpuPct.toFixed(1) + "%" : "UNAVAILABLE")
                + "\nTOP RSS // " + (ram ? label(ram) + " " + (ram.rssKiB / 1048576).toFixed(2) + " GiB" : "UNAVAILABLE")
                + "\nTOP WRITE // " + (write ? label(write) + " " + (write.writeBps / 1024).toFixed(1) + " KiB/s" : "UNAVAILABLE")
                + "\nLAST INTERVAL // RSS IS NOT UNIQUE RAM" + calibration;
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
            const calibration=observerCalibrationSuffix(kind,text);
            if (calibration===null) return null;
            return "PID // " + final.pid + "   SAMPLES // " + rows.length
                + "\nPSS START / PEAK / FINAL // " + gib(rows[0].memoryKiB.Pss)
                + " / " + gib(peak) + " / " + gib(rows[rows.length - 1].memoryKiB.Pss)
                + " GiB\nSWAP PSS PEAK // " + gib(swap)
                + " GiB   CPU PEAK // " + cpu.toFixed(1) + "%" + hostMemorySummary(rows) + calibration;
        }
        if (rows.some(row => !numeric(row.totalCpuPct))) return null;
        const configured = records.some(row=>Object.prototype.hasOwnProperty.call(row,"workshopSchema"));
        const config = configured ? configuredThreadEvidence(text,null) : null;
        if (configured && !config) return null;
        const peak = Math.max(...rows.map(row => row.totalCpuPct));
        return "PID // " + final.pid + "   SAMPLES // " + rows.length
            + "\nTHREAD CPU PEAK // " + peak.toFixed(1) + "% (ONE CORE = 100%)"
            + (config ? "\nCALIBRATION // "+config.durationSeconds+" s / "+config.intervalMs+" ms / TOP "+config.topCount : "");
    } catch (error) {
        return null;
    }
}


// Validate the transport against the exact submitted calibration, independently
// of the subprocess's exit/status claim. Retain no invalid child metric data.
function workflowEvidence(text, expected) {
    try {
        if (typeof text!=="string" || text.length>reportLimit("workflow") || /[^\x00-\x7f]/.test(text)) return null;
        const d=JSON.parse(text), int=(x,min,max)=>Number.isSafeInteger(x)&&x>=min&&x<=max;
        if (!d || d.schema!=="post-apollo-diagnostic-workflow-transport-v1"
                || !["COLLECTED","NOT VERIFIED","CANCELLED"].includes(d.status)
                || !int(d.durationSeconds,1,120) || !Array.isArray(d.instruments)
                || d.instruments.length<2 || d.instruments.length>5
                || !int(d.startedMonotonicMs,0,Number.MAX_SAFE_INTEGER)
                || !int(d.finishedMonotonicMs,d.startedMonotonicMs,Number.MAX_SAFE_INTEGER)
                || d.finishedMonotonicMs-d.startedMonotonicMs>145000) return null;
        if (expected && (expected.durationSeconds!==d.durationSeconds
                || expected.instruments.length!==d.instruments.length)) return null;
        const order=["threads","memory","census","storage","stall"], seen=[], summaries=[];
        let first=0,last=Number.MAX_SAFE_INTEGER, complete=0;
        const pin=d.pinnedQuickshell;
        for (let i=0;i<d.instruments.length;i++) {
            const item=d.instruments[i], c=item && item.config, kind=c && c.kind;
            if (!c || !order.includes(kind) || seen.includes(kind)
                    || (seen.length && order.indexOf(kind)<=order.indexOf(seen[seen.length-1]))
                    || c.durationSeconds!==d.durationSeconds) return null;
            const keys=kind==="threads"?["kind","durationSeconds","intervalMs","topCount"]:
                kind==="storage"?["kind","durationSeconds"]:kind==="stall"?["kind","durationSeconds","thresholdMs"]:["kind","durationSeconds","intervalMs"];
            if (Object.keys(c).length!==keys.length || keys.some(k=>!Object.prototype.hasOwnProperty.call(c,k))) return null;
            if (expected && keys.some(k=>k!=="durationSeconds" && expected.instruments[i][k]!==c[k])) return null;
            if (kind==="stall") { if (c.durationSeconds<5 || !int(c.thresholdMs,150,2000) || c.thresholdMs%50) return null; }
            else if (kind==="storage") { if (c.durationSeconds>30) return null; }
            else {
                if (!int(c.intervalMs,100,Math.min(60000,c.durationSeconds*1000))) return null;
                const n=Math.ceil(c.durationSeconds*1000/c.intervalMs);
                if (kind==="threads" && (![100,250,500,1000,2000,5000].includes(c.intervalMs)
                        || !int(c.topCount,1,12) || n>30 || n*(c.topCount+1)>150)) return null;
                if (kind==="memory" && (c.intervalMs<5000 || c.intervalMs%1000 || n>12)) return null;
                if (kind==="census" && (c.durationSeconds>60 || c.intervalMs%1000 || n>3)) return null;
            }
            seen.push(kind);
            if (!int(item.payloadBytes,0,65536) || !Array.isArray(item.records)
                    || typeof item.error!=="string" || item.error.length>80
                    || !["COLLECTED","NOT VERIFIED"].includes(item.status)
                    || (item.launchMonotonicMs!==null && !int(item.launchMonotonicMs,d.startedMonotonicMs,d.finishedMonotonicMs))
                    || (item.exitCode!==null && !int(item.exitCode,-255,255))) return null;
            if (kind==="memory" || kind==="threads") {
                if (!pin || !int(pin.pid,1,Number.MAX_SAFE_INTEGER)
                        || !int(pin.startTicks,1,Number.MAX_SAFE_INTEGER)) return null;
            }
            if (item.status!=="COLLECTED") {
                if (item.records.length || !item.error) return null;
                summaries.push(kind.toUpperCase()+" // NOT VERIFIED / "+item.error);
                continue;
            }
            if (item.exitCode!==0 || item.error!=="" || item.launchMonotonicMs===null || !item.payloadBytes
                    || !int(item.firstMonotonicMs,item.launchMonotonicMs,d.finishedMonotonicMs)
                    || !int(item.lastMonotonicMs,item.firstMonotonicMs,d.finishedMonotonicMs)
                    || !item.records.length || item.records.length>32) return null;
            if (kind==="stall") {
                if (item.records.length!==1 || item.payloadBytes>2048) return null;
                const record=item.records[0], evidence=stallEvidence(JSON.stringify(record),c);
                if (!evidence || record.witness.startedMonotonicMs!==item.firstMonotonicMs
                        || record.witness.monotonicMs!==item.lastMonotonicMs
                        || Math.abs(item.lastMonotonicMs-item.firstMonotonicMs-record.witness.elapsedMs)>2
                        || JSON.stringify(record).length>24000) return null;
                // Estimate common observed coverage from the witness endpoints;
                // exclude 250ms at each edge for the accepted clock discrepancy.
                const a=item.firstMonotonicMs+record.ticks[0]-record.witness.startWallMs+250;
                const b=item.lastMonotonicMs-(record.witness.endWallMs-record.ticks[record.ticks.length-1])-250;
                first=Math.max(first,a);
                last=Math.min(last,b);
                complete++;
                summaries.push("STALL // "+evidence.gaps.length+" GAPS / MAX "+evidence.maxGapMs+" ms / THRESHOLD "+evidence.thresholdMs+" ms");
                continue;
            }
            const rows=item.records, end=rows[rows.length-1];
            if (!end || end.monotonicMs!==item.lastMonotonicMs
                    || Math.abs(item.lastMonotonicMs-item.firstMonotonicMs-end.observedMs)>2
                    || (kind==="memory" || kind==="threads" ? rows[0].monotonicMs : end.startedMonotonicMs)!==item.firstMonotonicMs
                    || rows.some((row,j)=>!row || !int(row.monotonicMs,item.firstMonotonicMs,item.lastMonotonicMs)
                        || (j>0 && row.monotonicMs<rows[j-1].monotonicMs)
                        || ((kind==="memory" || kind==="threads") && (row.pid!==pin.pid || row.startTicks!==pin.startTicks)))) return null;
            // Python's ASCII JSONL can expand non-ASCII thread names. Re-encode
            // as ASCII before checking the per-child limit and existing policy.
            const raw=rows.map(row=>JSON.stringify(row).replace(/[^\x00-\x7f]/g,ch=>"\\u"+ch.charCodeAt(0).toString(16).padStart(4,"0"))).join("\n")+"\n";
            if (raw.length>65536 || !configuredEvidence(kind,raw,c)) return null;
            const summary=summarize(kind,raw);
            if (!summary) return null;
            summaries.push(kind.toUpperCase()+" // VERIFIED");
            complete++;
            first=Math.max(first,item.firstMonotonicMs);
            last=Math.min(last,item.lastMonotonicMs);
        }
        if (!seen.some(k=>k==="threads"||k==="memory") && pin!==null) return null;
        const overlap=complete===seen.length?Math.max(0,last-first):null;
        if (d.overlapMs!==overlap || (d.status==="COLLECTED" && !(complete===seen.length&&overlap>0))
                || (d.status==="NOT VERIFIED" && complete===seen.length&&overlap>0)) return null;
        return {status:d.status,complete:complete,summary:"WORKFLOW // "+complete+" / "+seen.length+" VERIFIED"
            +"\nDURATION // "+d.durationSeconds+" s   OVERLAP // "+(overlap===null?"N/A":overlap+" ms")
            +"\n"+summaries.join("\n")};
    } catch (_) { return null; }
}


// Standalone shell heartbeat evidence. The external witness establishes an
// independent monotonic duration; QML wall-clock samples are checked only
// inside its wall-time window. Do not invent gaps at the capture boundaries.
function stallEvidence(text,expected) {
    try {
        if (typeof text!=="string" || text.length>65536) return null;
        const d=JSON.parse(text), integer=(x,min,max)=>Number.isSafeInteger(x)&&x>=min&&x<=max;
        if (!d || d.schema!=="post-apollo-ui-stall-v1" || !integer(d.durationSeconds,5,120)
                || !integer(d.thresholdMs,150,2000) || d.thresholdMs%50!==0
                || d.cadenceMs!==100
                || (expected && (expected.kind!=="stall" || expected.durationSeconds!==d.durationSeconds
                    || expected.thresholdMs!==d.thresholdMs))) return null;
        const w=d.witness;
        if (!w || w.schema!=="post-apollo-stall-clock-v1" || w.durationSeconds!==d.durationSeconds
                || !integer(w.startWallMs,1,Number.MAX_SAFE_INTEGER)
                || !integer(w.endWallMs,w.startWallMs,Number.MAX_SAFE_INTEGER)
                || !integer(w.elapsedMs,d.durationSeconds*1000,d.durationSeconds*1000+5000)
                || Math.abs(w.endWallMs-w.startWallMs-w.elapsedMs)>250) return null;
        if (!Array.isArray(d.ticks) || d.ticks.length<2 || d.ticks.length>1500
                || d.ticks.some((t,i)=>!integer(t,w.startWallMs,w.endWallMs)
                    || (i>0 && t<=d.ticks[i-1]))) return null;
        const coverage=d.ticks[d.ticks.length-1]-d.ticks[0];
        // Refuse sparse or missing endpoint coverage, rather than report zero stalls.
        if (d.ticks[0]-w.startWallMs>500 || w.endWallMs-d.ticks[d.ticks.length-1]>500
                || coverage<d.durationSeconds*1000-1000) return null;
        const gaps=[];
        let maxGapMs=0;
        for (let i=1;i<d.ticks.length;i++) {
            const elapsed=d.ticks[i]-d.ticks[i-1];
            maxGapMs=Math.max(maxGapMs,elapsed);
            if (elapsed>=d.thresholdMs) gaps.push({startMs:d.ticks[i-1],endMs:d.ticks[i],elapsedMs:elapsed});
        }
        return {durationSeconds:d.durationSeconds,thresholdMs:d.thresholdMs,coverageMs:coverage,
            maxGapMs:maxGapMs,gaps:gaps};
    } catch (_) { return null; }
}

function combineStall(witnessText,ticks,config) {
    try {
        if (typeof witnessText!=="string" || witnessText.length>2048 || !Array.isArray(ticks)
                || ticks.length>1500 || !config || config.kind!=="stall"
                || ticks.some((t,i)=>!Number.isSafeInteger(t)||t<=0||(i>0&&t<=ticks[i-1]))) return null;
        const witness=JSON.parse(witnessText);
        const text=JSON.stringify({schema:"post-apollo-ui-stall-v1",durationSeconds:config.durationSeconds,
            thresholdMs:config.thresholdMs,cadenceMs:100,witness:witness,
            ticks:ticks.filter(t=>t>=witness.startWallMs&&t<=witness.endWallMs)});
        return stallEvidence(text,config) ? text : null;
    } catch (_) { return null; }
}


// Attach the shell's heartbeat timestamps to the runner's clock witness.
// The transport is not a COMPLETE stall result without this step.
function attachWorkflowStall(text,expected,ticks,overflow) {
    try {
        if (typeof text!=="string" || text.length>300000 || !expected || !Array.isArray(expected.instruments)) return null;
        const cfg=expected.instruments.find(c=>c.kind==="stall");
        if (!cfg) return text;
        const d=JSON.parse(text);
        if (!d || d.schema!=="post-apollo-diagnostic-workflow-transport-v1"
                || !["COLLECTED","NOT VERIFIED","CANCELLED"].includes(d.status)
                || !Array.isArray(d.instruments)) return null;
        const item=d.instruments.find(x=>x && x.config && x.config.kind==="stall");
        if (!item) return null;
        const allTransport=d.instruments.every(x=>x && x.status==="COLLECTED");
        const transportOverlap=allTransport?Math.max(0,Math.min(...d.instruments.map(x=>x.lastMonotonicMs))
            -Math.max(...d.instruments.map(x=>x.firstMonotonicMs))):null;
        if (d.overlapMs!==transportOverlap || (d.status==="COLLECTED" && !(allTransport&&transportOverlap>0))
                || (d.status==="NOT VERIFIED" && allTransport&&transportOverlap>0)) return null;
        if (item.status==="COLLECTED") {
            if (!Array.isArray(item.records) || item.records.length!==1 || item.records[0].schema!=="post-apollo-stall-clock-v1") return null;
            const combined=!overflow && combineStall(JSON.stringify(item.records[0]),ticks,
                Object.assign({},cfg,{durationSeconds:expected.durationSeconds}));
            if (!combined) {
                item.status="NOT VERIFIED";item.error="STALL COVERAGE OR CLOCK NOT VERIFIED";item.records=[];
                delete item.firstMonotonicMs;delete item.lastMonotonicMs;
            } else item.records=[JSON.parse(combined)];
        }
        const complete=d.instruments.every(x=>x.status==="COLLECTED");
        let first=0,last=Number.MAX_SAFE_INTEGER;
        if (complete) for (const x of d.instruments) {
            if (x.config.kind==="stall") {
                const s=x.records[0], w=s.witness;
                first=Math.max(first,x.firstMonotonicMs+s.ticks[0]-w.startWallMs+250);
                last=Math.min(last,x.lastMonotonicMs-(w.endWallMs-s.ticks[s.ticks.length-1])-250);
            } else {first=Math.max(first,x.firstMonotonicMs);last=Math.min(last,x.lastMonotonicMs);}
        }
        d.overlapMs=complete?Math.max(0,last-first):null;
        if (d.status!=="CANCELLED") d.status=complete&&d.overlapMs>0?"COLLECTED":"NOT VERIFIED";
        const result=JSON.stringify(d).replace(/[^\x00-\x7f]/g,ch=>"\\u"+ch.charCodeAt(0).toString(16).padStart(4,"0"));
        return workflowEvidence(result,expected)?result:null;
    } catch (_) {return null;}
}
