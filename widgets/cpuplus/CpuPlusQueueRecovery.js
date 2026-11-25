// DOC 2: local recovery presentation for DOC 4 #2603 inventory.
// No transport, permission, persistence or recovery acknowledgment.
function exact(o,keys) {
    return o !== null && typeof o==="object" && !Array.isArray(o)
        && Object.keys(o).length===keys.length && keys.every(k=>Object.prototype.hasOwnProperty.call(o,k));
}
function uuid(v){return typeof v==="string"&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(v);}
function count(v){return Number.isSafeInteger(v)&&v>=0;}
function utc(v){return count(v)&&v<=8640000000000?new Date(v*1000).toISOString():"UNAVAILABLE";}
function row(r) {
    if(!exact(r,["version","ordinal","message","state","prepared_at","result_request_id","committed_at","adjustment_outcome","can_execute"])
        ||r.version!==1||!count(r.ordinal)||r.ordinal===0||!count(r.prepared_at)
        ||r.adjustment_outcome!=="UNVERIFIED"||r.can_execute!==false) return null;
    const m=r.message;
    if(!exact(m,["version","owner_id","action_id","action_sequence","kind","expected_request_id","target_gib","expires_at"])
        ||m.version!==1||!uuid(m.owner_id)||!uuid(m.action_id)||!count(m.action_sequence)
        ||m.action_sequence===0||m.action_sequence>=Number.MAX_SAFE_INTEGER
        ||!["QUEUE","REPLACE","CANCEL","EXPIRE"].includes(m.kind)
        ||(m.kind==="QUEUE"?m.expected_request_id!==null:!uuid(m.expected_request_id)))return null;
    const changesTarget=m.kind==="QUEUE"||m.kind==="REPLACE";
    if(changesTarget?(!count(m.target_gib)||m.target_gib<4||m.target_gib>64||m.target_gib%4
        ||!count(m.expires_at)||m.expires_at<=r.prepared_at):(m.target_gib!==null||m.expires_at!==null))return null;
    if(r.state==="PREPARED"){
        if(r.result_request_id!==null||r.committed_at!==null)return null;
    }else if(r.state==="COMMITTED"){
        if(!uuid(r.result_request_id)||!count(r.committed_at)||r.committed_at<r.prepared_at
            ||(changesTarget? r.result_request_id===m.expected_request_id:r.result_request_id!==m.expected_request_id))return null;
    }else return null;
    return {ordinal:r.ordinal,actionId:m.action_id,kind:m.kind,state:r.state,
        expectedId:m.expected_request_id,resultId:r.result_request_id,target:m.target_gib,expiry:m.expires_at,
        preparedAt:r.prepared_at,committedAt:r.committed_at};
}
function project(inventory) {
    if(!exact(inventory,["version","recent","truncated","prepared","pending_request_id","startup_unlock","adjustment_outcome","can_execute"])
        ||inventory.version!==1||inventory.startup_unlock!==false||inventory.can_execute!==false
        ||inventory.adjustment_outcome!=="UNVERIFIED"||typeof inventory.truncated!=="boolean"
        ||!Array.isArray(inventory.recent)||inventory.recent.length>16
        ||(inventory.pending_request_id!==null&&!uuid(inventory.pending_request_id)))return null;
    const recent=[],ids=new Set();
    let last=Infinity,prepared=null;
    for(const raw of inventory.recent){
        const item=row(raw);
        if(!item||item.ordinal>=last||ids.has(item.actionId))return null;
        ids.add(item.actionId);last=item.ordinal;
        if(item.state==="PREPARED"){if(prepared)return null;prepared=item;}
        recent.push(item);
    }
    const outstanding=inventory.prepared===null?null:row(inventory.prepared);
    if(inventory.prepared!==null&&(!outstanding||outstanding.state!=="PREPARED"))return null;
    // The separately queried PREPARED may be outside a truncated recent list.
    if(prepared){
        if(!outstanding||JSON.stringify(prepared)!==JSON.stringify(outstanding))return null;
    }else if(outstanding&&(!inventory.truncated||outstanding.ordinal>=last||ids.has(outstanding.actionId)))return null;
    if(inventory.truncated&&recent.length===0)return null;
    return {recent,prepared:outstanding,truncated:inventory.truncated,pendingId:inventory.pending_request_id,
        outcome:"UNVERIFIED",startupLocked:true,canExecute:false};
}
function gate(host) {
    // Explicit proposed presentation metadata supplied by the session owner,
    // not inferred from missing nextActionSequence or a queue's IDLE report.
    if(!host||typeof host.startupLocked!=="boolean"||typeof host.historyPending!=="boolean"
        ||typeof host.actionPending!=="boolean"||typeof host.unresolved!=="boolean"
        ||!["STOPPED","HELLO","CONNECTED","FAILED"].includes(host.phase))
        return "TRANSPORT STATUS UNAVAILABLE // ACTIONS LOCKED";
    if(host.unresolved)return "OUTCOME UNKNOWN // RECONCILIATION REQUIRED";
    if(host.phase==="FAILED")return "CONNECTION FAILED // ACTIONS LOCKED";
    if(host.phase!=="CONNECTED")return "NOT CONNECTED // ACTIONS LOCKED";
    if(host.actionPending)return "ACTION PENDING // WAIT FOR OWNER";
    if(host.startupLocked)return "STARTUP RECONCILIATION REQUIRED // ACTIONS LOCKED";
    if(host.historyPending)return "HISTORY READ PENDING";
    return "HOST REPORTED // SEPARATE REQUEST VALIDATION REQUIRED";
}

// Canonical host #2621 publishes these four fields as one immutable snapshot.
// Correlation, owner identity and sequence are enforced by the host, not here.
function context(value) {
    if(!exact(value,["hostStatus","inventory","localAction","recoveryPending"])
        ||typeof value.recoveryPending!=="boolean")return null;
    const host=value.hostStatus;
    if(!exact(host,["phase","startupLocked","historyPending","actionPending","unresolved"])
        ||!["STOPPED","HELLO","CONNECTED","FAILED"].includes(host.phase)
        ||!["startupLocked","historyPending","actionPending","unresolved"].every(k=>typeof host[k]==="boolean"))
        return null;
    if(value.recoveryPending&&!host.historyPending)return null;
    const busy=host.historyPending||host.actionPending||value.recoveryPending;
    if(host.phase!=="CONNECTED"||busy) {
        if(value.inventory!==null||value.localAction!==null)return null;
        return {host,inventory:null,localAction:null,readPending:value.recoveryPending};
    }
    if(value.inventory!==null&&value.localAction!==null)return null;
    const inventory=value.inventory===null?null:project(value.inventory);
    if(value.inventory!==null&&!inventory)return null;
    let localAction=null;
    if(value.localAction!==null) {
        const raw=value.localAction;
        if(!exact(raw,["actionId","record","outcome","canExecute"])||!uuid(raw.actionId)
            ||raw.outcome!=="UNVERIFIED"||raw.canExecute!==false)return null;
        const record=raw.record===null?null:row(raw.record);
        if(raw.record!==null&&(!record||record.actionId!==raw.actionId))return null;
        localAction={actionId:raw.actionId,record,missing:record===null};
    }
    return {host,inventory,localAction,readPending:false};
}
function canRead(value,hostAvailable) {
    const v=context(value);
    return !!(hostAvailable===true&&v&&v.host.phase==="CONNECTED"
        &&!v.host.historyPending&&!v.host.actionPending&&!v.readPending);
}
