// Universal diagnostic lifecycle contract. No launch, storage or QObject access.
const lifecycleSchema="post-apollo-widget-lifecycle-v1";
const lifecycleMaxEvents=512;
const lifecycleMaxDuration=120000;
function lifecycleTargets() {
    return [
        ["appcontrol","AppControl"],["camera","Camera"],["hospital","Hospital"],
        ["finance","Finance"],["git","Git"],["company-network","Company Network"],
        ["tasks","Tasks"],["forest","Forest"],["apollo-hub","Apollo Hub"],
        ["cpuplus","CPU++"],["weather","Weather Station"],["social","Social / Messaging"],
        ["time","Clock / Time Machine"],["notifications","Notifications"],["media","Media Deck"]
    ].map(([id,label])=>({id,label}));
}
function lifecycleIds(){return lifecycleTargets().map(t=>t.id);}
function validSelection(ids) {
    const known=lifecycleIds();
    if(!Array.isArray(ids)||ids.length<1||ids.length>known.length||
        Reflect.ownKeys(ids).length!==ids.length+1)return false;
    for(let i=0;i<ids.length;i++){
        const d=Object.getOwnPropertyDescriptor(ids,String(i));
        if(!d||!Object.prototype.hasOwnProperty.call(d,"value")||!known.includes(d.value))return false;
    }
    return new Set(ids).size===ids.length;
}
function exactLifecycleFields(o,fields) {
    return !!o && Object.getPrototypeOf(o)===Object.prototype &&
        Reflect.ownKeys(o).length===fields.length && fields.every(k=>{
            const d=Object.getOwnPropertyDescriptor(o,k);
            return d && Object.prototype.hasOwnProperty.call(d,"value");
        });
}
function validTime(t){return Number.isSafeInteger(t)&&t>=0;}
function lifecycleStart(ids,states,now,durationMs) {
    if(!validSelection(ids)||!validTime(now)||!Number.isSafeInteger(durationMs)||
        durationMs<1000||durationMs>lifecycleMaxDuration||!Number.isSafeInteger(now+durationMs)||
        !exactLifecycleFields(states,ids)||!ids.every(id=>typeof states[id]==="boolean"))return null;
    // Snapshot selected flags only; no titles, payload, paths, account or process data.
    return {schema:lifecycleSchema,ids:ids.slice(),startedMs:now,deadlineMs:now+durationMs,
        initial:JSON.parse(JSON.stringify(states)),current:JSON.parse(JSON.stringify(states)),
        events:[],lastMs:now,fault:"",timings:[],timingRejected:0,loop:{ticks:0,maxIntervalMs:0,firstOffsetMs:null,lastOffsetMs:null,gapCount:0,gaps:[],omittedGaps:0,rejected:0}};
}
function lifecycleFault(run,reason){if(run&&!run.fault)run.fault=reason;return false;}
function lifecycleObserve(run,id,open,now) {
    if(!run||run.fault||!run.ids.includes(id))return false;
    if(typeof open!=="boolean"||!validTime(now)||now<run.lastMs)
        return lifecycleFault(run,"INVALID OBSERVATION");
    if(now>run.deadlineMs)return lifecycleFault(run,"CAPTURE DEADLINE EXCEEDED");
    if(run.current[id]===open)return true;
    if(run.events.length>=lifecycleMaxEvents)return lifecycleFault(run,"EVENT LIMIT EXCEEDED");
    run.events.push({id,open,atMs:now-run.startedMs});
    run.current[id]=open;
    run.lastMs=now;
    return true;
}
function lifecycleFinish(run,now,outcome) {
    if(!run||!["COMPLETE","CANCELLED"].includes(outcome)||!validTime(now)||now<run.lastMs)return null;
    if(run.fault)return {schema:lifecycleSchema,status:"FAILED",reason:run.fault};
    // Do not claim observations beyond the declared interval, or silently
    // convert an early stop into a successful full-duration capture.
    if(now>run.deadlineMs|| (outcome==="COMPLETE"&&now!==run.deadlineMs))
        return {schema:lifecycleSchema,status:"FAILED",reason:"CAPTURE TIMING MISMATCH"};
    const elapsedMs=now-run.startedMs;
    const stats=run.ids.map(id=>{
        let open=run.initial[id],since=0,openMs=0,opens=0,closes=0;
        for(const e of run.events){
            if(e.id!==id)continue;
            if(open)openMs+=e.atMs-since;
            since=e.atMs;
            open=e.open;
            if(open)opens++;else closes++;
        }
        if(open)openMs+=elapsedMs-since;
        return {id,initialOpen:run.initial[id],finalOpen:open,opens,closes,openMs};
    });
    return {schema:lifecycleSchema,status:outcome,elapsedMs,targets:run.ids.slice(),
        events:run.events.map(e=>({id:e.id,open:e.open,atMs:e.atMs})),stats,
        timings:run.timings.map(t=>Object.assign({},t)),timingRejected:run.timingRejected,
        eventLoop:JSON.parse(JSON.stringify(run.loop))};
}

// The cutoff is the requested observation window, not the timer callback.
// Record actual callback delay; refuse a delayed or backwards clock witness.
function lifecycleFinishObserved(run,now) {
    if(!run||!validTime(now)||now<run.deadlineMs||now<run.lastMs)return null;
    const delay=now-run.deadlineMs;
    if(delay>250)return {schema:lifecycleSchema,status:"FAILED",reason:"COMPLETION CALLBACK LATE",completionDelayMs:delay};
    const report=lifecycleFinish(run,run.deadlineMs,"COMPLETE");
    if(report)report.completionDelayMs=delay;
    return report;
}

// These are elapsed handler/stage timings, not exclusive CPU time.
// Aggregate fixed labels only, with separate mode context for AppControl.
function lifecycleTimingAllowed(id,channel,stage,mode) {
    const opening=["graph-invalidation","mode-restore","selection","selection-state","selection-row","selection-detail","probe-schedule","refresh-dispatch","focus","handler-total"];
    const work=["cpu-history","hunter-history","history-revisions","task-order","task-rows","metric-alerts","snapshot-selection","mini-cpu-history","mini-hunter-history","mini-history-revisions"];
    if(id==="appcontrol"){
        if(!["closed","app","kill","cpu-kill","mixed","other","unavailable"].includes(mode))return false;
        return channel==="opening"?opening.includes(stage):channel==="kill-work"?work.includes(stage):
            channel==="work"&&work.concat(["app-model-read","app-key-scan","app-index-write","app-position-view","resource-reconcile"]).includes(stage);
    }
    return mode===""&&((["git","hospital"].includes(id)&&channel==="dock"&&stage==="toggle")||
        (id==="media"&&channel==="frame"&&stage==="cava-apply"));
}
function lifecycleTiming(run,id,channel,stage,mode,elapsed,now) {
    if(!run||run.fault||!run.ids.includes(id))return false;
    if(!lifecycleTimingAllowed(id,channel,stage,mode)||!validTime(now)||!Number.isFinite(elapsed)||elapsed<0||
        elapsed>lifecycleMaxDuration||now>run.deadlineMs||now-elapsed<run.startedMs||now<run.lastMs){
        run.timingRejected=Math.min(1000000,run.timingRejected+1);return false;
    }
    let row=run.timings.find(t=>t.id===id&&t.channel===channel&&t.stage===stage&&t.mode===mode);
    if(!row){
        if(run.timings.length>=256){run.timingRejected=Math.min(1000000,run.timingRejected+1);return false;}
        row={id,channel,stage,mode,count:0,totalMs:0,maxMs:0};run.timings.push(row);
    }
    if(row.count>=1000000){run.timingRejected=Math.min(1000000,run.timingRejected+1);return false;}
    row.count++;row.totalMs+=elapsed;row.maxMs=Math.max(row.maxMs,elapsed);
    run.lastMs=now;
    return true;
}

// Reuse the existing 100ms shell timer. Full intervals only, bounded gap list.
// Timer delivery delay is not a CPU profile or widget attribution.
function lifecycleLoopTick(run,elapsed,now) {
    if(!run||run.fault)return false;
    const l=run.loop;
    if(!validTime(now)||!Number.isSafeInteger(elapsed)||elapsed<=0||now>run.deadlineMs||
        now-elapsed<run.startedMs||now<run.lastMs||
        (l.lastOffsetMs!==null&&now-run.startedMs<=l.lastOffsetMs)||l.ticks>=2048){
        l.rejected=Math.min(1000000,l.rejected+1);return false;
    }
    const offset=now-run.startedMs;
    if(l.firstOffsetMs===null)l.firstOffsetMs=offset-elapsed;
    l.lastOffsetMs=offset;l.ticks++;l.maxIntervalMs=Math.max(l.maxIntervalMs,elapsed);
    if(elapsed>=350){
        l.gapCount++;
        if(l.gaps.length<128)l.gaps.push({fromMs:offset-elapsed,atMs:offset,intervalMs:elapsed});
        else l.omittedGaps++;
    }
    run.lastMs=now;
    return true;
}
function lifecycleCombined(lifecycle,resource,requested,stopped) {
    if(!lifecycle)return null;
    const result=JSON.parse(JSON.stringify(lifecycle));
    if(!requested)return result;
    result.lifecycleStatus=lifecycle.status;
    result.resource=resource?JSON.parse(JSON.stringify(resource)):{status:"NOT VERIFIED",evidence:null};
    if(lifecycle.status==="FAILED")return result;
    if(stopped||lifecycle.status==="CANCELLED"){result.status="CANCELLED";return result;}
    if(lifecycle.status!=="COMPLETE"||result.resource.status!=="COMPLETE"||!result.resource.evidence||
       !result.eventLoop||!result.eventLoop.ticks||result.eventLoop.omittedGaps)result.status="PARTIAL";
    return result;
}
