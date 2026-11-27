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
    return ["memory", "inventory", "threads", "census", "storage", "appcontrol", "workflow", "stall", "hostcpu", "gpu", "diskio", "swapio", "netio"].indexOf(kind) >= 0;
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
                    threads: "THREAD SAMPLE", census: "PROCESS CENSUS", storage: "STORAGE OBSERVE", appcontrol: "APPCONTROL TEST", workflow: "DIAGNOSTIC WORKFLOW", stall: "UI STALL OBSERVE", hostcpu: "HOST CPU OBSERVE", gpu: "GPU OBSERVE", diskio: "DISK I/O OBSERVE", swapio: "SWAP OBSERVE", netio: "NETWORK OBSERVE"};
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

// Legacy configured storage receipts retain their original exact shape.
function storageCadence(c) {
    if (!c || c.kind!=="storage" || !Number.isSafeInteger(c.durationSeconds)
            || c.durationSeconds<1 || c.durationSeconds>30) return null;
    const explicit=Object.prototype.hasOwnProperty.call(c,"sampleSeconds")
        || Object.prototype.hasOwnProperty.call(c,"reportSeconds");
    const keys=explicit?["kind","durationSeconds","sampleSeconds","reportSeconds"]:["kind","durationSeconds"];
    if (Object.keys(c).length!==keys.length || keys.some(k=>!Object.prototype.hasOwnProperty.call(c,k))) return null;
    const sample=explicit?c.sampleSeconds:1, report=explicit?c.reportSeconds:10;
    if (!Number.isSafeInteger(sample)||sample<1||sample>Math.min(5,c.durationSeconds)
            || !Number.isSafeInteger(report)||report<sample||report>30||report%sample
            || Math.ceil(c.durationSeconds/report)>6) return null;
    return {keys:keys,sample:sample,report:report,explicit:explicit};
}

// Observer receipts extend the terminal record rather than prepend a row,
// keeping existing memory, census and storage projections compatible.
function configuredEvidence(kind,text,expected) {
    if (kind==="netio") { const d=netIoEvidence(text,expected); return d ? d.calibration : null; }
    if (kind==="swapio") { const d=swapIoEvidence(text,expected); return d ? d.calibration : null; }
    if (kind==="diskio") { const d=diskIoEvidence(text,expected); return d ? d.calibration : null; }
    if (kind==="gpu") { const d=gpuEvidence(text,expected); return d ? d.calibration : null; }
    if (kind==="hostcpu") { const d=hostCpuEvidence(text,expected); return d ? d.calibration : null; }
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
        const cadence=kind==="storage"?storageCadence(c):null;
        if (kind==="storage" && !cadence) return null;
        const keys=cadence?cadence.keys:["kind","durationSeconds","intervalMs"];
        if (Object.keys(c).length!==keys.length || keys.some(k=>!Object.prototype.hasOwnProperty.call(c,k))
                || (expected && (Object.keys(expected).length!==keys.length || keys.some(k=>expected[k]!==c[k])))) return null;
        if (kind==="storage") {
            if (rows.length!==Math.ceil(c.durationSeconds/cadence.report)
                    || rows.some((r,i)=>{
                        const scheduled=Math.min((i+1)*cadence.report,c.durationSeconds);
                        return r.intervals!==Math.ceil(scheduled/cadence.sample)
                            || !integer(r.elapsedMs,cadence.explicit?scheduled*1000:0,end.observedMs);
                    }) || rows[rows.length-1].elapsedMs!==end.observedMs) return null;
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
        +(kind==="storage"?(c.sampleSeconds===undefined?" / 1000 ms metadata cadence":
            " / "+c.sampleSeconds+" s metadata cadence / "+c.reportSeconds+" s reports"):" / "+c.intervalMs+" ms");
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
    if (kind==="netio") return netIoSummary(text);
    if (kind==="swapio") return swapIoSummary(text);
    if (kind==="diskio") return diskIoSummary(text);
    if (kind==="gpu") return gpuSummary(text);
    if (kind==="hostcpu") return hostCpuSummary(text);
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
                    || records.length < 1 || records.length > (final.calibration && storageCadence(final.calibration)
                        && storageCadence(final.calibration).explicit ? 6 : 3)) return null;
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
                || d.instruments.length<2 || d.instruments.length>10
                || !int(d.startedMonotonicMs,0,Number.MAX_SAFE_INTEGER)
                || !int(d.finishedMonotonicMs,d.startedMonotonicMs,Number.MAX_SAFE_INTEGER)
                || d.finishedMonotonicMs-d.startedMonotonicMs>145000) return null;
        if (expected && (expected.durationSeconds!==d.durationSeconds
                || expected.instruments.length!==d.instruments.length)) return null;
        const hardware=["hostcpu","gpu","diskio","swapio","netio"];
        const order=["threads","memory","census","storage","stall",...hardware], seen=[], summaries=[];
        let first=0,last=Number.MAX_SAFE_INTEGER, complete=0;
        const pin=d.pinnedQuickshell;
        for (let i=0;i<d.instruments.length;i++) {
            const item=d.instruments[i], c=item && item.config, kind=c && c.kind;
            if (!c || !order.includes(kind) || seen.includes(kind)
                    || (seen.length && order.indexOf(kind)<=order.indexOf(seen[seen.length-1]))
                    || c.durationSeconds!==d.durationSeconds) return null;
            const cadence=kind==="storage"?storageCadence(c):null;
            if (kind==="storage" && !cadence) return null;
            const keys=kind==="threads"?["kind","durationSeconds","intervalMs","topCount"]:
                cadence?cadence.keys:kind==="stall"?["kind","durationSeconds","thresholdMs"]:["kind","durationSeconds","intervalMs"];
            if (Object.keys(c).length!==keys.length || keys.some(k=>!Object.prototype.hasOwnProperty.call(c,k))) return null;
            if (expected && (Object.keys(expected.instruments[i]).length!==keys.length-1
                    || keys.some(k=>k!=="durationSeconds" && expected.instruments[i][k]!==c[k]))) return null;
            if (kind==="stall") { if (c.durationSeconds<5 || !int(c.thresholdMs,150,2000) || c.thresholdMs%50) return null; }
            else if (kind==="storage") { if (c.durationSeconds>30) return null; }
            else {
                if (!int(c.intervalMs,100,Math.min(60000,c.durationSeconds*1000))) return null;
                const n=Math.ceil(c.durationSeconds*1000/c.intervalMs);
                if (kind==="threads" && (![100,250,500,1000,2000,5000].includes(c.intervalMs)
                        || !int(c.topCount,1,12) || n>30 || n*(c.topCount+1)>150)) return null;
                if (kind==="memory" && (c.intervalMs<5000 || c.intervalMs%1000 || n>12)) return null;
                if (kind==="census" && (c.durationSeconds>60 || c.intervalMs%1000 || n>3)) return null;
                if (hardware.includes(kind) && (c.durationSeconds>30 || c.intervalMs<1000 || c.intervalMs>5000 || c.intervalMs%1000 || n>12)) return null;
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
            if (hardware.includes(kind)) {
                if (!end || end.startedMonotonicMs!==item.firstMonotonicMs
                        || end.monotonicMs!==item.lastMonotonicMs
                        || !int(end.observedMs,c.durationSeconds*1000,45000)
                        || end.monotonicMs-end.startedMonotonicMs!==end.observedMs) return null;
                // Standalone validators retain their exact legacy schema.
                // The two workflow-only clock fields were checked above.
                const terminal=Object.assign({},end);
                delete terminal.startedMonotonicMs;
                delete terminal.monotonicMs;
                const raw=rows.slice(0,-1).concat([terminal]).map(row=>JSON.stringify(row)).join("\n")+"\n";
                if (raw.length>65536 || !configuredEvidence(kind,raw,c) || !summarize(kind,raw)) return null;
                summaries.push(kind.toUpperCase()+" // VERIFIED");
                complete++;
                first=Math.max(first,item.firstMonotonicMs);
                last=Math.min(last,item.lastMonotonicMs);
                continue;
            }
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

/* D5c-a live presentation side channel, never completion authority. */
function storageLiveProgress(line, config, previous, requestWallMs, receiveWallMs) {
    try {
        if (typeof line!=="string"||line.length>512||!line.startsWith("STORAGE_PROGRESS ")) return null;
        const c=storageCadence(config), p=JSON.parse(line.slice(17));
        const keys=["tick","reports","elapsedMs","startWallMs","wallMs","durationSeconds","sampleSeconds","reportSeconds"];
        const int=(n,min,max)=>Number.isSafeInteger(n)&&n>=min&&n<=max;
        if (!c||!p||Object.keys(p).length!==keys.length||keys.some(k=>!Object.prototype.hasOwnProperty.call(p,k))
                ||p.durationSeconds!==config.durationSeconds||p.sampleSeconds!==c.sample||p.reportSeconds!==c.report
                ||!int(p.tick,0,Math.ceil(config.durationSeconds/c.sample))
                ||!int(p.reports,0,6)||!int(p.elapsedMs,0,145000)
                ||!int(p.startWallMs,requestWallMs,receiveWallMs+250)
                ||!int(p.wallMs,p.startWallMs,receiveWallMs+250)
                ||Math.abs(p.wallMs-p.startWallMs-p.elapsedMs)>250) return null;
        const scheduled=Math.min(p.tick*c.sample,config.durationSeconds);
        const reports=scheduled===config.durationSeconds?Math.ceil(scheduled/c.report):Math.floor(scheduled/c.report);
        if (p.reports!==reports||p.elapsedMs<scheduled*1000
                ||(!previous&&(p.tick!==0||p.elapsedMs!==0))
                ||(previous&&(p.tick!==previous.tick+1||p.startWallMs!==previous.startWallMs
                    ||p.elapsedMs<previous.elapsedMs||p.wallMs<previous.wallMs))) return null;
        return Object.assign({},p,{receivedWallMs:receiveWallMs,
            reportReceivedWallMs:!previous||p.reports>previous.reports?receiveWallMs:previous.reportReceivedWallMs});
    } catch (_) {return null;}
}
function storageCountdown(p,field,now) {
    if (!p||!["sample","report"].includes(field)||!Number.isFinite(now)||now<p.receivedWallMs) return null;
    const period=field==="sample"?p.sampleSeconds:p.reportSeconds;
    const count=field==="sample"?p.tick:p.reports;
    const target=Math.min(p.durationSeconds,(count+1)*period);
    const finished=field==="sample"?p.tick>=Math.ceil(p.durationSeconds/p.sampleSeconds)
        :p.reports>=Math.ceil(p.durationSeconds/p.reportSeconds);
    const previous=Math.min(p.durationSeconds,count*period);
    const remaining=finished?0:Math.max(0,target*1000-(now-p.startWallMs));
    const span=Math.max(1,(target-previous)*1000);
    return {remainingMs:remaining,fraction:Math.min(1,remaining/span),finished:finished,
        waiting:!finished&&remaining===0,flash:count>0&&now-(field==="sample"?p.receivedWallMs:p.reportReceivedWallMs)<350};
}


// Host counters have a distinct scope and unit from process CPU percentages.
function hostCpuEvidence(text,expected) {
    try {
        if (typeof text!=="string" || text.length>65536 || /[^\x00-\x7f]/.test(text)) return null;
        const records=text.trim().split("\n").map(line=>JSON.parse(line)), end=records.pop();
        const schema="post-apollo-host-cpu-v1", integer=(x,min,max)=>Number.isSafeInteger(x)&&x>=min&&x<=max;
        const c=end&&end.calibration;
        const keys=(o,k)=>!!o&&Object.keys(o).length===k.length&&k.every(x=>Object.prototype.hasOwnProperty.call(o,x));
        if (!keys(end,["schema","event","samples","observedMs","calibration"])
                || end.schema!==schema||end.event!=="complete"||!keys(c,["kind","durationSeconds","intervalMs"])
                || c.kind!=="hostcpu"||!integer(c.durationSeconds,1,30)
                ||!integer(c.intervalMs,1000,Math.min(5000,c.durationSeconds*1000))||c.intervalMs%1000
                || (expected&&(!keys(expected,Object.keys(c))||Object.keys(c).some(k=>c[k]!==expected[k])))) return null;
        const n=Math.ceil(c.durationSeconds*1000/c.intervalMs);
        if (n>12||records.length!==n||end.samples!==n||!integer(end.observedMs,c.durationSeconds*1000,45000))return null;
        const validTicks=a=>Array.isArray(a)&&a.length===3&&integer(a[0],1,1000000000)
            &&integer(a[1],0,a[0])&&integer(a[2],0,a[0]-a[1]);
        let elapsed=0, ids=null;
        for (let i=0;i<n;i++) {
            const row=records[i];
            if (!keys(row,["schema","event","sequence","elapsedMs","intervalMs","aggregate","cores","psiSomeAvg10"])
                    ||row.schema!==schema||row.event!=="hostcpu"||row.sequence!==i+1
                    ||!integer(row.elapsedMs,Math.min((i+1)*c.intervalMs,c.durationSeconds*1000),end.observedMs)
                    ||!integer(row.intervalMs,1,45000)||row.elapsedMs!==elapsed+row.intervalMs
                    ||!validTicks(row.aggregate)||!Array.isArray(row.cores)||row.cores.length<1||row.cores.length>128
                    ||(row.psiSomeAvg10!==null&&(!numeric(row.psiSomeAvg10)||row.psiSomeAvg10>100)))return null;
            if(row.cores.some((a,j)=>!Array.isArray(a)||a.length!==5||!integer(a[0],0,1048575)
                ||(j>0&&a[0]<=row.cores[j-1][0])||!validTicks(a.slice(1,4))
                ||(a[4]!==null&&!integer(a[4],1,100000000))))return null;
            const current=row.cores.map(a=>a[0]).join(",");
            if(ids!==null&&ids!==current)return null;
            ids=current;elapsed=row.elapsedMs;
        }
        if(elapsed!==end.observedMs)return null;
        return {calibration:c,records:records,observedMs:elapsed};
    }catch(_){return null;}
}
function hostCpuSummary(text) {
    const d=hostCpuEvidence(text,null);
    if(!d)return null;
    const rows=d.records, last=rows[rows.length-1], pct=(a,b)=>100*a/b,
        sum=(r,i)=>r.reduce((a,b)=>a+b.aggregate[i],0);
    const frequency=last.cores.filter(a=>a[4]!==null).map(a=>a[4]/1000);
    const coreStats=last.cores.map((a,i)=>{
        let ticks=0,busy=0;
        for(const r of rows){ticks+=r.cores[i][1];busy+=r.cores[i][2];}
        return {id:a[0],busy:pct(busy,ticks)};
    }).sort((a,b)=>b.busy-a.busy||a.id-b.id);
    return "HOST CPU // "+rows.length+" intervals / "+last.cores.length+" logical CPUs / "+d.observedMs+" ms"
        +"\nBUSY // mean "+pct(sum(rows,1),sum(rows,0)).toFixed(1)+"% / peak "+Math.max(...rows.map(r=>pct(r.aggregate[1],r.aggregate[0]))).toFixed(1)+"%"
        +"\nIOWAIT // "+pct(sum(rows,2),sum(rows,0)).toFixed(1)+"% weighted"
        +"\nCPU PSI SOME AVG10 // "+(last.psiSomeAvg10===null?"N/A":last.psiSomeAvg10.toFixed(2)+"% (last reading)")
        +"\nSCALING FREQUENCY // "+(frequency.length?Math.min(...frequency).toFixed(0)+"–"+Math.max(...frequency).toFixed(0)+" MHz / "+frequency.length+"/"+last.cores.length+" CPUs":"N/A")
        +"\nTOP LOGICAL CPUs // "+coreStats.slice(0,8).map(a=>"CPU"+a.id+" "+a.busy.toFixed(1)+"%").join(" / ")
        +"\nHost busy excludes idle and iowait, includes steal; 100% = aggregate capacity. PSI is a rolling kernel reading, not capture-local stall time. Scaling frequency is driver-reported, not measured clock. Raw report retains every covered logical CPU.";
}


// Each DRM device has its own identity and coverage. Never add GPU percentages
// or convert unsupported readings into zero.
function gpuEvidence(text,expected) {
    try {
        if (typeof text!=="string"||text.length>65536||/[^\x00-\x7f]/.test(text)) return null;
        const records=text.trim().split("\n").map(line=>JSON.parse(line)), end=records.pop();
        const schema="post-apollo-gpu-observation-v1", integer=(x,min,max)=>Number.isSafeInteger(x)&&x>=min&&x<=max;
        const c=end&&end.calibration;
        const keys=(o,k)=>!!o&&Object.keys(o).length===k.length&&k.every(x=>Object.prototype.hasOwnProperty.call(o,x));
        if (!keys(end,["schema","event","samples","observedMs","calibration"])
                ||end.schema!==schema||end.event!=="complete"||!keys(c,["kind","durationSeconds","intervalMs"])
                ||c.kind!=="gpu"||!integer(c.durationSeconds,1,30)
                ||!integer(c.intervalMs,1000,Math.min(5000,c.durationSeconds*1000))||c.intervalMs%1000
                ||(expected&&(!keys(expected,Object.keys(c))||Object.keys(c).some(k=>c[k]!==expected[k]))))return null;
        const n=Math.ceil(c.durationSeconds*1000/c.intervalMs);
        if(n>12||records.length!==n||end.samples!==n||!integer(end.observedMs,c.durationSeconds*1000,45000))return null;
        let elapsed=0, identity=null, observed=false;
        const validDevice=(d,j,all)=>Array.isArray(d)&&d.length===6
            &&typeof d[0]==="string"&&/^card(?:0|[1-9][0-9]{0,5})$/.test(d[0])
            &&(j===0||d[0]>all[j-1][0])&&typeof d[1]==="string"&&d[1].length<=256
            &&/^[A-Za-z0-9_./:+-]+$/.test(d[1])&&!d[1].startsWith("/")
            &&d[1].split("/").every(p=>p!==""&&p!=="."&&p!=="..")
            &&(d[2]===null||integer(d[2],0,100))
            &&((d[3]===null&&d[4]===null)||(integer(d[4],1,Number.MAX_SAFE_INTEGER)&&integer(d[3],0,d[4])))
            &&(d[5]===null||integer(d[5],-40000,200000));
        for(let i=0;i<n;i++){
            const row=records[i];
            if(!keys(row,["schema","event","sequence","elapsedMs","intervalMs","devices"])
                    ||row.schema!==schema||row.event!=="gpu"||row.sequence!==i+1
                    ||!integer(row.elapsedMs,Math.min((i+1)*c.intervalMs,c.durationSeconds*1000),end.observedMs)
                    ||!integer(row.intervalMs,1,45000)||row.elapsedMs!==elapsed+row.intervalMs
                    ||!Array.isArray(row.devices)||row.devices.length<1||row.devices.length>8
                    ||!row.devices.every(validDevice)
                    ||new Set(row.devices.map(d=>d[1])).size!==row.devices.length)return null;
            const next=JSON.stringify(row.devices.map(d=>d.slice(0,2)));
            if(identity!==null&&identity!==next)return null;
            identity=next;elapsed=row.elapsedMs;
            observed=observed||row.devices.some(d=>d.slice(2).some(v=>v!==null));
        }
        if(!observed||elapsed!==end.observedMs)return null;
        return {calibration:c,records:records,observedMs:elapsed};
    }catch(_){return null;}
}
function gpuSummary(text) {
    const d=gpuEvidence(text,null);
    if(!d)return null;
    const rows=d.records,last=rows[rows.length-1], n=rows.length;
    const mib=x=>(x/1048576).toFixed(1);
    const lines=last.devices.map((dev,i)=>{
        const samples=rows.map(r=>r.devices[i]), busy=samples.filter(a=>a[2]!==null).map(a=>a[2]),
            vram=samples.filter(a=>a[3]!==null), temp=samples.filter(a=>a[5]!==null).map(a=>a[5]/1000);
        const coverage=a=>" ("+a.length+"/"+n+")";
        return dev[0].toUpperCase()+" // "+dev[1].split("/").pop()
            +"\nBUSY // "+(busy.length?"mean "+(busy.reduce((a,b)=>a+b,0)/busy.length).toFixed(1)+"% / peak "+Math.max(...busy)+"%"+coverage(busy):"N/A")
            +"\nVRAM // "+(dev[3]===null?"last N/A":mib(dev[3])+" / "+mib(dev[4])+" MiB last")
            +(vram.length?" / peak used "+mib(Math.max(...vram.map(a=>a[3])))+" MiB"+coverage(vram):"")
            +"\nTEMP1 // "+(temp.length?"peak "+Math.max(...temp).toFixed(1)+" C"+coverage(temp):"N/A");
    });
    return "GPU // "+n+" observations / "+last.devices.length+" DRM devices / "+d.observedMs+" ms\n"
        +lines.join("\n\n")+"\nDriver-exposed point readings, not interval utilization or per-process attribution. TEMP1 is a uniquely associated hwmon sensor, not necessarily junction. Unsupported fields are N/A.";
}


// D8c-b: strictly admit only the bounded whole-device counter receipt.
function diskIoEvidence(text,expected) {
    try {
        if(typeof text!=="string"||text.length>65536||/[^\x00-\x7f]/.test(text))return null;
        const records=text.trim().split("\n").map(line=>JSON.parse(line)), end=records.pop();
        const schema="post-apollo-disk-io-v1", integer=(x,min,max)=>Number.isSafeInteger(x)&&x>=min&&x<=max;
        const keys=(o,k)=>!!o&&Object.keys(o).length===k.length&&k.every(x=>Object.prototype.hasOwnProperty.call(o,x));
        const c=end&&end.calibration;
        if(!keys(end,["schema","event","samples","observedMs","calibration"])
            ||end.schema!==schema||end.event!=="complete"||!keys(c,["kind","durationSeconds","intervalMs"])
            ||c.kind!=="diskio"||!integer(c.durationSeconds,1,30)
            ||!integer(c.intervalMs,1000,Math.min(5000,c.durationSeconds*1000))||c.intervalMs%1000
            ||(expected&&(!keys(expected,Object.keys(c))||Object.keys(c).some(k=>c[k]!==expected[k]))))return null;
        const n=Math.ceil(c.durationSeconds*1000/c.intervalMs);
        if(n>12||records.length!==n||end.samples!==n||!integer(end.observedMs,c.durationSeconds*1000,45000))return null;
        let elapsed=0, identity=null, totals=null;
        for(let i=0;i<n;i++){
            const row=records[i];
            if(!keys(row,["schema","event","sequence","elapsedMs","intervalMs","devices"])
                ||row.schema!==schema||row.event!=="diskio"||row.sequence!==i+1
                ||!integer(row.elapsedMs,Math.min((i+1)*c.intervalMs,c.durationSeconds*1000),end.observedMs)
                ||!integer(row.intervalMs,1,45000)||row.elapsedMs!==elapsed+row.intervalMs
                ||!Array.isArray(row.devices)||row.devices.length<1||row.devices.length>32)return null;
            const devs=row.devices;
            if(!devs.every((d,j)=>Array.isArray(d)&&d.length===13
                &&typeof d[0]==="string"&&/^[A-Za-z0-9_.!+\-]{1,64}$/.test(d[0])
                &&(j===0||d[0]>devs[j-1][0])
                &&integer(d[1],0,1048575)&&integer(d[2],0,1048575)
                &&(d[3]===null||integer(d[3],0,Number.MAX_SAFE_INTEGER))
                &&d.slice(4).every(v=>integer(v,0,Number.MAX_SAFE_INTEGER))
                &&d[5]%512===0&&d[8]%512===0)
                ||new Set(devs.map(d=>d[1]+":"+d[2])).size!==devs.length)return null;
            const next=JSON.stringify(devs.map(d=>d.slice(0,4)));
            if(identity!==null&&identity!==next)return null;
            if(totals===null)totals=devs.map(()=>Array(8).fill(0));
            for(let j=0;j<devs.length;j++)for(let k=0;k<8;k++){
                totals[j][k]+=devs[j][k+4];
                if(!Number.isSafeInteger(totals[j][k]))return null;
            }
            identity=next;elapsed=row.elapsedMs;
        }
        if(elapsed!==end.observedMs)return null;
        return {calibration:c,records:records,observedMs:elapsed,totals:totals};
    }catch(_){return null;}
}
function diskIoSummary(text) {
    const d=diskIoEvidence(text,null);
    if(!d)return null;
    const rows=d.records,last=rows[rows.length-1],sec=d.observedMs/1000;
    const mib=x=>(x/1048576/sec).toFixed(2);
    // Limit projection size without dropping any raw evidence.
    const ranked=last.devices.map((dev,i)=>({dev:dev,i:i,total:d.totals[i]}))
        .sort((a,b)=>(b.total[1]+b.total[4])-(a.total[1]+a.total[4])||a.i-b.i);
    const lines=ranked.slice(0,8).map(o=>{
        const a=o.total, inflight=Math.max(...rows.map(r=>r.devices[o.i][12]));
        return o.dev[0]+" ["+o.dev[1]+":"+o.dev[2]+"]"
            +"\nREAD / WRITE // "+mib(a[1])+" / "+mib(a[4])+" MiB/s"
            +" | "+(a[0]/sec).toFixed(1)+" / "+(a[3]/sec).toFixed(1)+" IOPS"
            +"\nIO MS / WEIGHTED MS // "+a[6]+" / "+a[7]+" | sampled peak in-flight "+inflight;
    });
    return "DISK I/O // "+rows.length+" intervals / "+last.devices.length+" devices / "+d.observedMs+" ms\n"
        +lines.join("\n\n")+"\nTop "+Math.min(8,last.devices.length)+" by bytes; raw report retains all devices."
        +" Device-backed whole block counters only; excludes virtual layers, partitions, discard and flush. Kernel time counters are not latency or saturation guarantees.";
}


// D9a-b: VM swap traffic, not disk traffic; optional pressure and zram
// data retain their availability and interval coverage.
function swapIoEvidence(text,expected) {
    try {
        if(typeof text!=="string"||text.length>65536||/[^\x00-\x7f]/.test(text))return null;
        const records=text.trim().split("\n").map(line=>JSON.parse(line)),end=records.pop();
        const schema="post-apollo-swap-io-v1",max=Number.MAX_SAFE_INTEGER;
        const integer=(x,min,max)=>Number.isSafeInteger(x)&&x>=min&&x<=max;
        const keys=(o,k)=>!!o&&Object.keys(o).length===k.length&&k.every(x=>Object.prototype.hasOwnProperty.call(o,x));
        const c=end&&end.calibration,page=end&&end.pageSize;
        if(!keys(end,["schema","event","samples","observedMs","pageSize","calibration"])
            ||end.schema!==schema||end.event!=="complete"||!keys(c,["kind","durationSeconds","intervalMs"])
            ||c.kind!=="swapio"||!integer(c.durationSeconds,1,30)
            ||!integer(c.intervalMs,1000,Math.min(5000,c.durationSeconds*1000))||c.intervalMs%1000
            ||!integer(page,1024,1048576)||(page&(page-1))!==0
            ||(expected&&(!keys(expected,Object.keys(c))||Object.keys(c).some(k=>c[k]!==expected[k]))))return null;
        const n=Math.ceil(c.durationSeconds*1000/c.intervalMs);
        if(n>12||records.length!==n||end.samples!==n||!integer(end.observedMs,c.durationSeconds*1000,45000))return null;
        let elapsed=0,identity=null,capacity=null,bytes=[0,0],pressureTotals=[0,0],pressureMs=0;
        const pct=v=>typeof v==="number"&&Number.isFinite(v)&&v>=0&&v<=100;
        for(let i=0;i<n;i++){
            const row=records[i],m=row&&row.memoryKiB,p=row&&row.pressure;
            if(!keys(row,["schema","event","sequence","elapsedMs","intervalMs","memoryKiB","swapBytes","pressure","zram"])
                ||row.schema!==schema||row.event!=="swapio"||row.sequence!==i+1
                ||!integer(row.elapsedMs,Math.min((i+1)*c.intervalMs,c.durationSeconds*1000),end.observedMs)
                ||!integer(row.intervalMs,1,45000)||row.elapsedMs!==elapsed+row.intervalMs
                ||!Array.isArray(m)||m.length!==4||!m.every(v=>integer(v,0,max))
                ||m[0]===0||m[1]>m[0]||m[3]>m[2]
                ||!Array.isArray(row.swapBytes)||row.swapBytes.length!==2
                ||!row.swapBytes.every(v=>integer(v,0,max)&&v%page===0)
                ||(p!==null&&(!Array.isArray(p)||p.length!==4||!pct(p[0])||!pct(p[1])
                    ||!integer(p[2],0,max)||!integer(p[3],0,max)))
                ||!Array.isArray(row.zram)||row.zram.length>16)return null;
            if(!row.zram.every((z,j)=>Array.isArray(z)&&z.length===4
                &&typeof z[0]==="string"&&/^zram(?:0|[1-9][0-9]{0,5})$/.test(z[0])
                &&(j===0||z[0]>row.zram[j-1][0])
                &&(z.slice(1).every(v=>v===null)||z.slice(1).every(v=>integer(v,0,max)))))return null;
            const next=JSON.stringify(row.zram.map(z=>z[0])),cap=JSON.stringify([m[0],m[2]]);
            if(identity!==null&&identity!==next||capacity!==null&&capacity!==cap)return null;
            identity=next;capacity=cap;
            for(let k=0;k<2;k++){
                bytes[k]+=row.swapBytes[k];
                if(!Number.isSafeInteger(bytes[k]))return null;
                if(p!==null){
                    pressureTotals[k]+=p[k+2];
                    if(!Number.isSafeInteger(pressureTotals[k]))return null;
                }
            }
            if(p!==null)pressureMs+=row.intervalMs;
            elapsed=row.elapsedMs;
        }
        if(elapsed!==end.observedMs)return null;
        return {calibration:c,records:records,observedMs:elapsed,pageSize:page,bytes:bytes,pressureTotals:pressureTotals,pressureMs:pressureMs};
    }catch(_){return null;}
}
function swapIoSummary(text) {
    const d=swapIoEvidence(text,null);
    if(!d)return null;
    const rows=d.records,last=rows[rows.length-1],sec=d.observedMs/1000;
    const mib=b=>(b/1048576).toFixed(2),gib=k=>(k/1048576).toFixed(2);
    const zram=last.zram.map(z=>z[0]+" // "+(z[1]===null?"N/A":
        mib(z[1])+" / "+mib(z[2])+" / "+mib(z[3])+" MiB (original / compressed / allocated)"));
    return "SWAP // "+rows.length+" intervals / "+d.observedMs+" ms / page "+d.pageSize+" B"
        +"\nRAM AVAILABLE // "+gib(last.memoryKiB[1])+" / "+gib(last.memoryKiB[0])+" GiB last"
        +" / minimum "+gib(Math.min(...rows.map(r=>r.memoryKiB[1])))+" GiB"
        +"\nSWAP USED // "+gib(last.memoryKiB[3])+" / "+gib(last.memoryKiB[2])+" GiB last"
        +"\nSWAP IN / OUT // "+mib(d.bytes[0])+" / "+mib(d.bytes[1])+" MiB total"
        +" | "+mib(d.bytes[0]/sec)+" / "+mib(d.bytes[1]/sec)+" MiB/s mean"
        +"\nMEMORY PSI SOME / FULL AVG10 // "+(last.pressure===null?"N/A":last.pressure[0].toFixed(2)+" / "+last.pressure[1].toFixed(2)+"% last")
        +"\nPSI STALL SOME / FULL // "+(d.pressureMs===0?"N/A":
            (d.pressureTotals[0]/1000).toFixed(1)+" / "+(d.pressureTotals[1]/1000).toFixed(1)+" ms over "+d.pressureMs+" ms observed")
        +"\nACTIVE ZRAM // "+(zram.length?"\n"+zram.join("\n"):"NONE")
        +"\nVM swap counters are not disk throughput. PSI covers all host memory pressure, not just swap. ZRAM allocation consumes RAM. Snapshots are non-atomic; no process attribution.";
}


// D10a-b: per-interface counters, no aggregate across stacked links.
function netIoEvidence(text,expected) {
    try {
        if(typeof text!=="string"||text.length>65536||/[^\x00-\x7f]/.test(text))return null;
        const records=text.trim().split("\n").map(line=>JSON.parse(line)),end=records.pop();
        const schema="post-apollo-network-io-v1",max=Number.MAX_SAFE_INTEGER;
        const integer=(x,min,max)=>Number.isSafeInteger(x)&&x>=min&&x<=max;
        const keys=(o,k)=>!!o&&Object.keys(o).length===k.length&&k.every(x=>Object.prototype.hasOwnProperty.call(o,x));
        const c=end&&end.calibration;
        if(!keys(end,["schema","event","samples","observedMs","calibration"])
            ||end.schema!==schema||end.event!=="complete"||!keys(c,["kind","durationSeconds","intervalMs"])
            ||c.kind!=="netio"||!integer(c.durationSeconds,1,30)
            ||!integer(c.intervalMs,1000,Math.min(5000,c.durationSeconds*1000))||c.intervalMs%1000
            ||(expected&&(!keys(expected,Object.keys(c))||Object.keys(c).some(k=>c[k]!==expected[k]))))return null;
        const n=Math.ceil(c.durationSeconds*1000/c.intervalMs);
        if(n>12||records.length!==n||end.samples!==n||!integer(end.observedMs,c.durationSeconds*1000,45000))return null;
        let elapsed=0,identity=null,totals=null;
        const states=["unknown","notpresent","down","lowerlayerdown","testing","dormant","up"];
        for(let i=0;i<n;i++){
            const row=records[i],devs=row&&row.interfaces;
            if(!keys(row,["schema","event","sequence","elapsedMs","intervalMs","interfaces"])
                ||row.schema!==schema||row.event!=="netio"||row.sequence!==i+1
                ||!integer(row.elapsedMs,Math.min((i+1)*c.intervalMs,c.durationSeconds*1000),end.observedMs)
                ||!integer(row.intervalMs,1,45000)||row.elapsedMs!==elapsed+row.intervalMs
                ||!Array.isArray(devs)||devs.length<1||devs.length>32)return null;
            if(!devs.every((d,j)=>Array.isArray(d)&&d.length===13
                &&typeof d[0]==="string"&&/^[A-Za-z0-9_.+@-]{1,15}$/.test(d[0])
                &&(j===0||d[0]>devs[j-1][0])
                &&integer(d[1],1,2147483647)&&integer(d[2],1,2147483647)
                &&integer(d[3],0,65535)&&(d[4]===null||states.includes(d[4]))
                &&d.slice(5).every(v=>integer(v,0,max)))
                ||new Set(devs.map(d=>d[1])).size!==devs.length)return null;
            const next=JSON.stringify(devs.map(d=>d.slice(0,4)));
            if(identity!==null&&identity!==next)return null;
            if(totals===null)totals=devs.map(()=>Array(8).fill(0));
            for(let j=0;j<devs.length;j++)for(let k=0;k<8;k++){
                totals[j][k]+=devs[j][k+5];
                if(!Number.isSafeInteger(totals[j][k]))return null;
            }
            identity=next;elapsed=row.elapsedMs;
        }
        if(elapsed!==end.observedMs)return null;
        return {calibration:c,records:records,observedMs:elapsed,totals:totals};
    }catch(_){return null;}
}
function netIoSummary(text) {
    const d=netIoEvidence(text,null);
    if(!d)return null;
    const rows=d.records,last=rows[rows.length-1],sec=d.observedMs/1000;
    const mbps=x=>(x/sec*8/1000000).toFixed(3);
    const ranked=last.interfaces.map((dev,i)=>({dev:dev,i:i,total:d.totals[i]}))
        .sort((a,b)=>(b.total[0]+b.total[4])-(a.total[0]+a.total[4])||a.i-b.i);
    const lines=ranked.slice(0,8).map(o=>{
        const a=o.total;
        return o.dev[0]+" ["+o.dev[1]+"] // "+(o.dev[4]===null?"N/A":o.dev[4].toUpperCase())+" last"
            +"\nRX / TX // "+mbps(a[0])+" / "+mbps(a[4])+" Mb/s mean"
            +" | "+(a[1]/sec).toFixed(1)+" / "+(a[5]/sec).toFixed(1)+" pkt/s"
            +"\nERRORS RX / TX // "+a[2]+" / "+a[6]+" | DROPS "+a[3]+" / "+a[7];
    });
    return "NETWORK // "+rows.length+" intervals / "+last.interfaces.length+" interfaces / "+d.observedMs+" ms\n"
        +lines.join("\n\n")+"\nTop "+Math.min(8,last.interfaces.length)+" by bytes; raw report retains all interfaces."
        +" No stacked-interface aggregate. Interface errors and drops are not end-to-end packet loss. No latency test or application attribution.";
}
