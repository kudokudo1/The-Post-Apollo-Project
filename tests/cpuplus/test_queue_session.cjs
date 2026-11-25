const assert=require("node:assert/strict"),fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const load=p=>{const c=vm.createContext({});vm.runInContext(fs.readFileSync(path.join(root,p),"utf8"),c);return c;};
const C=load("widgets/cpuplus/CpuPlusQueueConsumer.js");
const Q=load("widgets/cpuplus/CpuPlusQueuePresentation.js");
const H=load("candidate-history/widgets/cpuplus/CpuPlusQueueHistory.js");
const S=load("widgets/cpuplus/CpuPlusQueueSession.js");
const O="c23683a9-b2ab-4a2c-87ce-31bdf27a3012",N="c23683a9-b2ab-4a2c-87ce-31bdf27a3013",R="c23683a9-b2ab-4a2c-87ce-31bdf27a3014",A="c23683a9-b2ab-4a2c-87ce-31bdf27a3015";
const control=(kind,owner=O)=>({version:1,kind,owner_id:owner,can_execute:false});
const status=(seq,id=null,next=1,owner=O)=>({...control("STATUS",owner),sequence:seq,next_action_sequence:next,projection:{
    version:1,can_execute:false,adjustment_outcome:"UNVERIFIED",notification_candidate:null,notification_error:null,
    status:{version:1,request_id:id,target_gib:id?16:null,original_actual_kib:id?25165816:null,
        expires_at:id?200:null,state:id?"WAITING":"IDLE",code:id?"EXTENSION_OCCUPIED":"NO_PENDING_REQUEST",
        can_execute:false,last_checked_at:id?100:null,next_check_monotonic_ms:id?11000:null,
        ready_valid_before_monotonic_ms:null,transition:true}}});
const detail=(seq,owner=O)=>({...control("DETAIL",owner),sequence:seq,next_action_sequence:2,detail:{
    version:1,can_execute:false,adjustment_outcome:"UNVERIFIED",notification_events:[],withdrawal_evidence:null,
    request:{id:R,state:"QUEUED",target_gib:16,original_actual_kib:25165816,requested_at:100,expires_at:200,changed_at:100,replaced_by:null}}});
const reply=(seq,action=A)=>({...control("ACTION"),sequence:seq,next_action_sequence:2,action_id:action,
    action_sequence:1,disposition:"REPORTED",code:"READ_STATUS_REQUIRED",result:{version:1,can_execute:false,adjustment_outcome:"UNVERIFIED"},invalidate:true});
let s=S.begin(S.initial(C,true),1);
const recv=(p,g=1)=>{const out=S.receive(s,g,JSON.stringify(p),C,Q.project,H.project);s=out.state;return out;};
recv(control("HELLO"));recv(control("INVALIDATE"));recv(status(1));
assert.equal(s.session.status.state,"IDLE REPORTED");
const frozen=C.prepare(s.session,"QUEUE",16,200).prepared;
assert.equal(S.submitIntent(s,{...frozen,statusSequence:0},A,C).frame,null);
const sent=S.submitIntent(s,frozen,A,C);s=sent.state;
assert.equal(JSON.parse(sent.frame).message.action_id,A);
assert.ok(S.context(s).state.pending);assert.equal(S.context(s).projection,null);
assert.equal(S.submitIntent(s,frozen,A,C).frame,null);
recv(control("INVALIDATE"));recv(status(2)); // owner publication races pending
assert.ok(s.session.pending);assert.equal(s.projection,null);
recv(reply(3));recv(control("INVALIDATE"));recv(status(4,R,2));
assert.equal(s.session.status.requestId,R);
let history=S.requestHistory(s,R);s=history.state;
assert.equal(JSON.parse(history.frame).kind,"HISTORY");
assert.equal(S.requestHistory(s,R).frame,null);
assert.equal(S.context(s).state.status,null);
recv(detail(5));
assert.equal(s.history.view.requestId,R);assert.equal(s.session.sequence,5);
assert.equal(S.context(s).state.status.requestId,R);
const p=C.prepare(s.session,"CANCEL",null,null).prepared;
s=S.submitIntent(s,p,N,C).state;
const disconnected=S.disconnect(s,1,C,"TIMEOUT");s=disconnected.state;
assert.ok(s.session.unresolved);assert.equal(s.active,false);assert.equal(s.history,null);
assert.equal(S.begin(s,1),s);
s=S.begin(s,2);
assert.equal(recv(reply(6),1).state,s); // late callback from old child ignored
recv(control("HELLO",N),2);recv(control("INVALIDATE",N),2);recv(status(1,R,1,N),2);
assert.ok(s.session.unresolved);
assert.equal(S.submitIntent(s,p,A,C).frame,null);
assert.equal(S.requestHistory(s,R).frame!==null,true);
const malformed=S.receive(s,2,'{"version":1,"version":1,"can_execute":false}',C,Q.project,H.project);
assert.equal(malformed.stop,true);assert.ok(malformed.state.session.unresolved);
let boot=S.begin(S.initial(C),1);
for(const p of [control("HELLO"),control("INVALIDATE"),status(1)]) boot=S.receive(boot,1,JSON.stringify(p),C,Q.project,H.project).state;
assert.equal(S.context(boot).state.status,null);
assert.equal(S.submitIntent(boot,C.prepare(boot.session,"QUEUE",16,200).prepared,A,C).frame,null);
for(const bad of ["x".repeat(16384),'{"version":1,"can_execute":false,"x":9007199254740993}',
    '{"version":1,"can_execute":false,"x":1.0}','{"version":1,"can_execute":true}']) assert.equal(S.decode(bad),null);
console.log("CPU++ R3d session coordinator contract PASS");
