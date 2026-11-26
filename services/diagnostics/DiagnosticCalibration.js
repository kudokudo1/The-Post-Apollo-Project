// D1a: pure calibration preview, NOT a launch or authority API.
// Limits are conservative envelopes for the existing fixed-report runner;
// actual byte bounds, identity, cancellation and output validation still apply.
function defaultsFor(kind) {
    switch (kind) {
    case "threads": return {kind:kind,durationSeconds:30,intervalMs:1000,topCount:4};
    case "memory": return {kind:kind,durationSeconds:120,intervalMs:10000};
    case "census": return {kind:kind,durationSeconds:30,intervalMs:10000};
    case "storage": return {kind:kind,durationSeconds:30};
    case "inventory": return {kind:kind};
    case "stall": return {kind:kind,durationSeconds:30,thresholdMs:350};
    case "appcontrol": return {kind:kind,durationSeconds:30,intervalMs:1000,topCount:4};
    default: return null;
    }
}

function previewCalibration(input) {
    const refuse = reason => ({ok:false,reason:reason});
    if (!input || Object.getPrototypeOf(input)!==Object.prototype)
        return refuse("INVALID CONFIGURATION");
    const keys = Reflect.ownKeys(input);
    if (keys.some(k=>typeof k!=="string"
        || !Object.prototype.hasOwnProperty.call(Object.getOwnPropertyDescriptor(input,k),"value")))
        return refuse("INVALID CONFIGURATION");
    if (!Object.prototype.hasOwnProperty.call(input,"kind"))
        return refuse("SELECT INSTRUMENT");
    const d = defaultsFor(input.kind);
    if (!d || keys.length!==Object.keys(d).length
        || keys.some(k=>!Object.prototype.hasOwnProperty.call(d,k)))
        return refuse("UNSUPPORTED CONFIGURATION");
    const kind=d.kind;
    const integer=(v,min,max)=>Number.isSafeInteger(v)&&v>=min&&v<=max;
    if (kind==="inventory") return {ok:true,config:d,intervals:null,observations:null,
        scope:"tracked-source",fixed:true};
    const duration=input.durationSeconds;
    if (!integer(duration,1,120)) return refuse("DURATION OUTSIDE PREVIEW LIMIT");
    d.durationSeconds=duration;
    if (kind==="stall") {
        if (duration<5 || !integer(input.thresholdMs,150,2000) || input.thresholdMs%50!==0)
            return refuse("STALL LIMIT // 5–120 SEC / 150–2000 MS");
        d.thresholdMs=input.thresholdMs;
        return {ok:true,config:d,intervals:duration*10,observations:duration*10,
            scope:"launching-quickshell-event-loop",fixed:false};
    }
    if (kind==="storage") {
        if (duration>30) return refuse("STORAGE LIMIT 30 SECONDS");
        return {ok:true,config:d,intervals:duration,observations:Math.ceil(duration/10),
            scope:"configured-file-metadata",fixed:false};
    }
    const interval=input.intervalMs;
    if (!integer(interval,100,60000)||interval>duration*1000)
        return refuse("INVALID INTERVAL");
    d.intervalMs=interval;
    const intervals=Math.ceil(duration*1000/interval);
    let scope, observations=intervals, fixed=false;
    if (kind==="threads"||kind==="appcontrol") {
        if ([100,250,500,1000,2000,5000].indexOf(interval)<0
            || !integer(input.topCount,1,12))
            return refuse("UNSUPPORTED THREAD CALIBRATION");
        d.topCount=input.topCount;
        // Keep approximate record count and ranked-entry budget no larger than
        // the current 30 x (4 + main) run. Not a byte-size guarantee.
        if (intervals>30 || intervals*(d.topCount+1)>150)
            return refuse("THREAD REPORT BUDGET");
        scope=kind==="appcontrol"?"launching-quickshell":"same-user-quickshell";
        if (kind==="appcontrol") {
            // v1 combineAppControl still requires exact 30s / <=32 samples.
            if (duration!==30||interval!==1000||d.topCount!==4)
                return refuse("APPCONTROL V1 FIXED");
            fixed=true;
        }
    } else if (kind==="memory") {
        if (!integer(interval,5000,60000)||interval%1000!==0||intervals>12)
            return refuse("MEMORY REPORT BUDGET");
        observations=intervals+1;
        scope="same-user-quickshell";
    } else if (kind==="census") {
        if (duration>60||interval%1000!==0||intervals>3)
            return refuse("CENSUS REPORT BUDGET");
        scope="same-user-processes";
    } else return refuse("UNKNOWN INSTRUMENT");
    return {ok:true,config:d,intervals:intervals,observations:observations,
        scope:scope,fixed:fixed};
}

// First qualified configurable instrument. Executable and target are fixed.
function threadLaunchPlan(input, resolvePath) {
    const preview = previewCalibration(input);
    if (!preview.ok || preview.config.kind !== "threads") return null;
    const config = preview.config;
    return {config:config, args:["/usr/bin/timeout","--kill-after=3s","145s",
        "/usr/bin/python3","-B",resolvePath("scripts/syntagma_quickshell_thread_sampler.py"),
        "--workshop","--duration",String(config.durationSeconds),
        "--interval",String(config.intervalMs/1000),"--top",String(config.topCount)]};
}

// D1c: existing observers only. No arbitrary executable, target or path.
function observerLaunchPlan(input, resolvePath, dataDir) {
    const preview=previewCalibration(input);
    if (!preview.ok) return null;
    const config=preview.config;
    if (config.kind==="threads") return threadLaunchPlan(config,resolvePath);
    if (config.kind==="stall")
        return {config:config,args:["/usr/bin/timeout","--kill-after=3s","145s",
            "/usr/bin/python3","-B",resolvePath("scripts/cpuplus_stall_clock_witness.py"),
            "--duration",String(config.durationSeconds)]};
    const scripts={memory:"cpuplus_quickshell_memory_observer.py",
        census:"cpuplus_process_census.py",storage:"cpuplus_storage_observer.py"};
    if (!Object.prototype.hasOwnProperty.call(scripts,config.kind)) return null;
    const args=["/usr/bin/timeout","--kill-after=3s","145s","/usr/bin/python3","-B",
        resolvePath("scripts/"+scripts[config.kind]),"--workshop","--duration",String(config.durationSeconds)];
    if (config.kind==="storage") {
        if (typeof dataDir!=="string" || !dataDir.startsWith("/")) return null;
        args.push("--data-dir",dataDir,"--shell-dir",resolvePath("."));
    } else args.push("--interval",String(config.intervalMs/1000));
    return {config:config,args:args};
}


// D2a: one shared calibration, independent per-instrument cadences.
// This pure preview never starts collectors or reserves an execution slot.
function previewWorkflow(input) {
    const refuse=reason=>({ok:false,reason:reason});
    const fields=(object,expected)=>{
        if (!object || Object.getPrototypeOf(object)!==Object.prototype) return false;
        const keys=Reflect.ownKeys(object);
        return keys.length===expected.length && keys.every(k=>expected.includes(k)
            && Object.prototype.hasOwnProperty.call(Object.getOwnPropertyDescriptor(object,k),"value"));
    };
    if (!fields(input,["durationSeconds","instruments"])) return refuse("INVALID WORKFLOW");
    const duration=input.durationSeconds, instruments=input.instruments;
    if (!Number.isSafeInteger(duration)||duration<1||duration>120)
        return refuse("INVALID SHARED DURATION");
    if (!Array.isArray(instruments)||instruments.length<2||instruments.length>5
            || Reflect.ownKeys(instruments).length!==instruments.length+1)
        return refuse("SELECT TWO TO FIVE DISTINCT INSTRUMENTS");
    const seen=[], entries=[];
    for (let i=0;i<instruments.length;i++) {
        const descriptor=Object.getOwnPropertyDescriptor(instruments,String(i));
        if (!descriptor || !Object.prototype.hasOwnProperty.call(descriptor,"value"))
            return refuse("INVALID INSTRUMENT");
        const item=descriptor.value;
        if (!item || Object.getPrototypeOf(item)!==Object.prototype) return refuse("INVALID INSTRUMENT");
        const kd=Object.getOwnPropertyDescriptor(item,"kind");
        if (!kd || !Object.prototype.hasOwnProperty.call(kd,"value")) return refuse("INVALID INSTRUMENT");
        const kind=kd.value;
        if (!["threads","memory","census","storage","stall"].includes(kind)||seen.includes(kind))
            return refuse("UNSUPPORTED OR DUPLICATE INSTRUMENT");
        const keys=kind==="threads"?["kind","intervalMs","topCount"]:
            kind==="storage"?["kind"]:kind==="stall"?["kind","thresholdMs"]:["kind","intervalMs"];
        if (!fields(item,keys)) return refuse("UNSUPPORTED INSTRUMENT FIELDS");
        const preview=previewCalibration(Object.assign({},item,{durationSeconds:duration}));
        if (!preview.ok) return refuse(kind.toUpperCase()+" // "+preview.reason);
        seen.push(kind);
        entries.push({config:preview.config,scope:preview.scope,estimatedIntervals:preview.intervals,
            estimatedObservations:preview.observations,maximumReportBytes:kind==="stall"?24000:65536});
    }
    // Canonical ordering is stable across UI selection order and saved presets.
    const order=["threads","memory","census","storage","stall"];
    entries.sort((a,b)=>order.indexOf(a.config.kind)-order.indexOf(b.config.kind));
    return {ok:true,schema:"post-apollo-diagnostic-workflow-plan-v1",durationSeconds:duration,
        instruments:entries,estimatedObservations:entries.reduce((sum,e)=>sum+e.estimatedObservations,0),
        maximumCombinedPayloadBytes:entries.reduce((sum,e)=>sum+e.maximumReportBytes,0),
        sharedQuickshellIdentityRequired:seen.includes("threads")&&seen.includes("memory"),
        launchReady:false};
}


// D2b transport command only. D2c must mount the session owner and qualify
// the returned envelope before any UI success/archive publication.
function workflowLaunchPlan(input,resolvePath,dataDir) {
    const preview=previewWorkflow(input);
    if (!preview.ok || typeof dataDir!=="string" || !dataDir.startsWith("/")) return null;
    const plan={durationSeconds:preview.durationSeconds,instruments:preview.instruments.map(entry=>{
        const item=Object.assign({},entry.config);
        delete item.durationSeconds;
        return item;
    })};
    return {plan:plan,args:["/usr/bin/timeout","--kill-after=3s","145s","/usr/bin/python3","-B",
        resolvePath("scripts/cpuplus_diagnostic_workflow.py"),"--plan",JSON.stringify(plan),"--data-dir",dataDir]};
}


// Shared draft projection for Controls and Workflows. A preset is calibration
// only, never a stored launch command, readiness token, target PID or consent.
function workshopPlanFromDraft(d) {
    const instruments=[];
    for (const kind of ["threads","memory","census","storage","stall"]) {
        if (!d.selected.includes(kind)) continue;
        if (kind==="threads") instruments.push({kind:kind,intervalMs:d.threadIntervalMs,topCount:d.topCount});
        else if (kind==="memory") instruments.push({kind:kind,intervalMs:d.memoryIntervalMs});
        else if (kind==="census") instruments.push({kind:kind,intervalMs:d.censusIntervalMs});
        else if (kind==="stall") instruments.push({kind:kind,thresholdMs:d.stallThresholdMs});
        else instruments.push({kind:kind});
    }
    return {durationSeconds:d.durationSeconds,instruments:instruments};
}

function workshopDraftFromPlan(plan) {
    try {
        if (!plan || Object.getPrototypeOf(plan)!==Object.prototype
                || Reflect.ownKeys(plan).length!==2 || !["durationSeconds","instruments"].every(k=>{
                    const d=Object.getOwnPropertyDescriptor(plan,k);return d && Object.prototype.hasOwnProperty.call(d,"value");
                }) || !Array.isArray(plan.instruments)
                || !plan.instruments.length || plan.instruments.length>5) return null;
        const kinds=["threads","memory","census","storage","stall"];
        const items=plan.instruments;
        if (Reflect.ownKeys(items).length!==items.length+1 || items.some(c=>!c || Object.getPrototypeOf(c)!==Object.prototype
                || Reflect.ownKeys(c).some(k=>typeof k!=="string" || !Object.prototype.hasOwnProperty.call(Object.getOwnPropertyDescriptor(c,k),"value"))
                || !kinds.includes(c.kind))) return null;
        if (!Object.prototype.hasOwnProperty.call(items,0)) return null;
        if (items.length===1) {
            if (!previewCalibration(Object.assign({},items[0],{durationSeconds:plan.durationSeconds})).ok
                    || Object.prototype.hasOwnProperty.call(items[0],"durationSeconds")) return null;
        } else if (!previewWorkflow(plan).ok) return null;
        const draft={durationSeconds:plan.durationSeconds,selected:[],
            threadIntervalMs:1000,memoryIntervalMs:10000,censusIntervalMs:10000,
            topCount:4,stallThresholdMs:350};
        for (const c of items) {
            draft.selected.push(c.kind);
            if (c.kind==="threads") {draft.threadIntervalMs=c.intervalMs;draft.topCount=c.topCount;}
            else if (c.kind==="memory") draft.memoryIntervalMs=c.intervalMs;
            else if (c.kind==="census") draft.censusIntervalMs=c.intervalMs;
            else if (c.kind==="stall") draft.stallThresholdMs=c.thresholdMs;
        }
        return draft;
    } catch (_) {return null;}
}
