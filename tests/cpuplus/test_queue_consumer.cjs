const assert=require("node:assert/strict"),fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const c=vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(__dirname,"../../widgets/cpuplus/CpuPlusQueueConsumer.js"),"utf8"),c);
const A="c23683a9-b2ab-4a2c-87ce-31bdf27a3012",B="c23683a9-b2ab-4a2c-87ce-31bdf27a3013",
    R="c23683a9-b2ab-4a2c-87ce-31bdf27a3014",X="c23683a9-b2ab-4a2c-87ce-31bdf27a3015";
function status(owner,sequence,next,id=null,code=id?"EXTENSION_OCCUPIED":"NO_PENDING_REQUEST"){
    return {version:1,owner_id:owner,sequence,next_action_sequence:next,kind:"STATUS",can_execute:false,
        projection:{version:1,can_execute:false,adjustment_outcome:"UNVERIFIED",
            status:{request_id:id,can_execute:false,code}}};
}
// Stand-in for the separately reviewed #2558 strict R1 projector.
// Real integration must invoke that parser, not this fixture.
function project(p){return {requestId:p.status.request_id,state:p.status.request_id?"WAITING REPORTED":"IDLE REPORTED",
    targetGiB:p.status.request_id?16:null,canExecute:false,outcome:"UNVERIFIED"};}
function reply(owner,sequence,disposition="REPORTED",action=X,seq=1){
    return {version:1,owner_id:owner,sequence,next_action_sequence:seq+1,kind:"ACTION",can_execute:false,
        action_id:action,action_sequence:seq,disposition,code:disposition==="REPORTED"?"READ_STATUS_REQUIRED":
            disposition==="REFUSED"?"STALE_REQUEST":"RECONCILE_REQUIRED",
        result:disposition==="REPORTED"?{version:1,adjustment_outcome:"UNVERIFIED",can_execute:false,
            request:{source:{inode:9007199254740992}}}:null,invalidate:true};
}
let s=c.initial();
assert.equal(c.acceptStatus(s,status(A,1,1),project),s);
s=c.connect(s,A);
s=c.acceptStatus(s,status(A,1,1),project);
assert.equal(s.status.state,"IDLE REPORTED");
assert.equal(c.prepare(s,"CANCEL",null,null),s);
assert.equal(c.prepare(s,"QUEUE",17,200),s);
assert.equal(c.prepare(s,"QUEUE",16,null),s);
assert.equal(c.prepare(s,"QUEUE",16,Number.MAX_SAFE_INTEGER+1),s);
s=c.prepare(s,"QUEUE",16,200);
assert.equal(s.prepared.targetGiB,16);
const prepared=s;
assert.equal(c.cancelPreparation(s).prepared,null);
s=c.acceptStatus(s,status(A,2,1),project);
assert.equal(s.prepared,null);
assert.equal(c.submit(s,X).message,null);
assert.equal(c.acceptStatus(s,status(A,1,1,R),project),s);
assert.equal(c.acceptStatus(s,status(B,999,1,R),project),s);
s=c.disconnect(s);s=c.connect(s,A);
assert.equal(c.acceptStatus(s,status(A,2,1),project),s);
s=c.acceptStatus(s,status(A,3,1),project);
assert.equal(s.status.state,"IDLE REPORTED");
s=c.prepare(s,"QUEUE",16,200);
let sent=c.submit(s,X);s=sent.state;
assert.equal(sent.message.target_gib,16);
assert.equal(sent.message.expected_request_id,null);
assert.equal(sent.message.action_sequence,1);
assert.equal(s.status,null);
assert.equal(c.submit(s,X).message,null);
assert.equal(c.prepare(s,"QUEUE",16,200),s);
s=c.acceptAction(s,reply(A,4));
assert.equal(s.pending,null);
assert.equal(s.status,null);
assert.equal(s.unresolved,null);
assert.equal(JSON.stringify(s).includes("inode"),false);
assert.equal(c.prepare(s,"QUEUE",16,200),s);
s=c.acceptStatus(s,status(A,5,2,R),project);
assert.equal(s.status.requestId,R);
assert.equal(c.prepare(s,"QUEUE",16,200),s);
assert.equal(c.prepare(s,"EXPIRE",null,null),s);
s=c.prepare(s,"CANCEL",null,null);
sent=c.submit(s,B);s=sent.state;
assert.equal(sent.message.expected_request_id,R);
s=c.acceptAction(s,reply(A,6,"UNKNOWN",B,2));
assert.ok(s.unresolved);
assert.equal(c.acknowledgeReconciliation(s),s);
s=c.acceptStatus(s,status(A,7,3,R),project);
assert.equal(c.prepare(s,"CANCEL",null,null),s);
s=c.acknowledgeReconciliation(s);
assert.equal(s.unresolved,null);
s=c.prepare(s,"RECHECK",null,null);s=c.submit(s,X).state;
s=c.disconnect(s);
assert.ok(s.unresolved);
s=c.connect(s,B);
assert.equal(c.acceptAction(s,reply(A,7,"REPORTED",X,3)),s);
s=c.acceptStatus(s,status(B,1,1),project);
assert.ok(s.unresolved);
s=c.acknowledgeReconciliation(s);
s=c.prepare(s,"QUEUE",16,200);s=c.submit(s,X).state;
s=c.acceptStatus(s,status(B,3,2,R),project);
assert.ok(s.pending);assert.equal(s.status,null);
assert.equal(c.acceptAction(s,reply(B,2)),s);
s=c.timeout(s);
assert.ok(s.unresolved);assert.equal(s.pending,null);
s=c.acceptStatus(s,status(B,4,2,R),project);s=c.acknowledgeReconciliation(s);
s=c.prepare(s,"REPLACE",16,201);sent=c.submit(s,A);s=sent.state;
assert.equal(sent.message.expected_request_id,R);
s=c.acceptAction(s,reply(B,5,"REFUSED",A,2));
assert.equal(s.status,null);assert.equal(s.unresolved,null);
s=c.acceptStatus(s,status(B,6,3,R,"EXPIRY_RECONCILIATION_REQUIRED"),project);
s=c.prepare(s,"EXPIRE",null,null);assert.equal(s.prepared.kind,"EXPIRE");
s=c.acceptStatus(s,{...status(B,7,3,R),can_execute:true},project);
assert.equal(s.status,null);assert.equal(s.prepared,null);
assert.equal(c.prepare(s,"RECHECK",null,null),s);
s=c.acceptStatus(s,status(B,8,3,R),()=>({state:"VERIFIED",requestId:R,canExecute:true}));
assert.equal(s.status,null);
s=c.acceptStatus(s,status(B,9,3,R),project);
s=c.prepare(s,"RECHECK",null,null);s=c.submit(s,A).state;
s=c.acceptAction(s,reply(B,10,"REPORTED",X,3));
assert.ok(s.unresolved);assert.equal(s.status,null);
assert.equal(c.acceptStatus(s,status(A,999,1),project),s);
assert.equal(JSON.stringify(s).includes("can_execute\":true"),false);
console.log("CPU++ R2b consumer lifecycle contract PASS (isolated source fixture, no transport)");
