const assert=require("node:assert/strict"),fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const c=vm.createContext({});
const dir=path.join(__dirname,"../../widgets/cpuplus");
vm.runInContext(fs.readFileSync(path.join(dir,"CpuPlusQueueHistory.js"),"utf8"),c);
const O="c23683a9-b2ab-4a2c-87ce-31bdf27a3012",R="c23683a9-b2ab-4a2c-87ce-31bdf27a3013",N="c23683a9-b2ab-4a2c-87ce-31bdf27a3014";
const p={version:1,kind:"DETAIL",owner_id:O,sequence:8,next_action_sequence:3,can_execute:false,
    detail:{version:1,can_execute:false,adjustment_outcome:"UNVERIFIED",request:{
        id:R,state:"REPLACED",target_gib:16,original_actual_kib:25165816,requested_at:100,
        expires_at:200,changed_at:150,replaced_by:N},
        notification_events:[{event_id:"apollo-cpu-memory-"+R+"-ready-advisory",kind:"READY_ADVISORY",
            code:"FRESH_AUTH_AND_ROOT_CHECK_REQUIRED",observed_at:120,attempt_reserved_at_ms:121000,delivery_outcome:"UNKNOWN"}],
        withdrawal_evidence:{state:"UNBOUND_EVIDENCE",observed_at:145,kernel_verified_for_request:false,can_execute:false}}};
const read=v=>c.project(v,O,R,7);
const v=read(p);
assert.equal(v.state,"REPLACED");assert.equal(v.replacedBy,N);assert.equal(v.outcome,"UNVERIFIED");
assert.equal(v.events[0].kind,"READINESS REPORTED (HISTORICAL)");
assert.equal(v.events[0].delivery,"ATTEMPT RESERVED // DELIVERY UNKNOWN");
assert.equal(c.project(p,N,R,7),null);
assert.equal(c.project(p,O,N,7),null);
assert.equal(c.project(p,O,R,8),null);
assert.equal(c.project(p,O,R,null),null);
assert.equal(read({...p,can_execute:true}),null);
assert.equal(read({...p,sequence:Number.MAX_SAFE_INTEGER+1}),null);
const mutate=(fn)=>{const n=JSON.parse(JSON.stringify(p));fn(n.detail);return n;};
for(const change of [
    d=>d.adjustment_outcome="VERIFIED",d=>d.request.source={inode:42},
    d=>d.request.replaced_by=R,d=>d.request.changed_at=99,d=>d.request.original_actual_kib=-1,
    d=>d.notification_events[0].delivery_outcome="DELIVERED",d=>d.notification_events[0].attempt_reserved_at_ms=1,
    d=>d.notification_events[0].event_id="wrong",d=>d.notification_events.push(d.notification_events[0]),
    d=>d.notification_events[0].observed_at=200,d=>d.withdrawal_evidence.receipt={state:"VERIFIED"},
    d=>d.withdrawal_evidence.kernel_verified_for_request=true
]) assert.equal(read(mutate(change)),null);
assert.equal(read(mutate(d=>{d.notification_events[0].attempt_reserved_at_ms=null;d.notification_events[0].delivery_outcome="NOT_RECORDED";})).events[0].delivery,"NO ATTEMPT RECORDED");
assert.equal(read(mutate(d=>{d.notification_events=[];d.withdrawal_evidence=null;})).evidenceAt,null);
assert.equal(read(mutate(d=>{d.request.state="EXPIRED";d.request.changed_at=199;d.request.replaced_by=null;})),null);
const ui=fs.readFileSync(path.join(dir,"CpuPlusQueueHistoryPane.qml"),"utf8");
assert.doesNotMatch(ui,/\b(?:Process|Timer|ActionButton|MemoryOperation|execDetached|Consumer)\b/);
assert.match(ui,/ADJUSTMENT OUTCOME \/\/ UNVERIFIED/);
console.log("CPU++ R3c reduced DETAIL presentation contract PASS");
