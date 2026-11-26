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
