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
        events:[],lastMs:now,fault:""};
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
        events:run.events.map(e=>({id:e.id,open:e.open,atMs:e.atMs})),stats};
}
