const assert=require("node:assert/strict"),fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const root=path.join(__dirname,"../..");
function load(file){const c=vm.createContext({});vm.runInContext(fs.readFileSync(file,"utf8"),c);return c;}
const h=load(path.join(root,"services/memory/MemoryQueueSessionHost.js"));
const c=load(path.join(root,"widgets/cpuplus/CpuPlusQueueConsumer.js"));
const p=load(path.join(root,"widgets/cpuplus/CpuPlusQueuePresentation.js"));
const history=load(path.join(root,"widgets/cpuplus/CpuPlusQueueHistory.js"));
const recovery=load(path.join(root,"widgets/cpuplus/CpuPlusQueueRecovery.js"));
const A="c23683a9-b2ab-4a2c-87ce-31bdf27a3012", B="c23683a9-b2ab-4a2c-87ce-31bdf27a3013",
R="c23683a9-b2ab-4a2c-87ce-31bdf27a3014", X="c23683a9-b2ab-4a2c-87ce-31bdf27a3015";
const wire=x=>JSON.stringify(x)+"\n";
const control=(kind,owner_id=A)=>({version:1,kind,owner_id,can_execute:false});
function status(sequence,next,id=null,owner_id=A){
 return {version:1,kind:"STATUS",owner_id,sequence,next_action_sequence:next,can_execute:false,
 projection:{version:1,notification_candidate:null,notification_error:null,adjustment_outcome:"UNVERIFIED",can_execute:false,
 status:{version:1,request_id:id,target_gib:id?16:null,original_actual_kib:id?25165816:null,expires_at:id?200:null,
 state:id?"WAITING":"IDLE",code:id?"EXTENSION_OCCUPIED":"NO_PENDING_REQUEST",can_execute:false,
 last_checked_at:id?100:null,next_check_monotonic_ms:id?11000:null,ready_valid_before_monotonic_ms:null,transition:true}}};
}
function feed(s,x,generation=s.generation){return h.feed(s,typeof x==="string"?x:wire(x),c,p.project,history.project,generation,recovery.project,recovery.row);}
function connect(owner=A){
 let s=h.start(h.initial(c),c,1);
 const hello=wire(control("HELLO",owner));
 s=feed(s,hello.slice(0,12));
 assert.equal(s.phase,"HELLO");
 s=feed(s,hello.slice(12)+wire(control("INVALIDATE",owner))+wire(status(1,1,null,owner)));
 assert.equal(s.session.status.state,"IDLE REPORTED");
 return s;
}
let s=connect();
const intent=c.prepare(s.session,"QUEUE",16,200).prepared;
assert.ok(s.startupLocked);
assert.equal(h.context(s).startupLocked,true);
assert.equal(h.context(s).phase,"CONNECTED");
assert.equal(h.context(s).state.nextActionSequence,null);
assert.equal(h.confirm(s,intent,X,c).frame,null);
// Only fixture injects the otherwise unavailable startup-review result.
s={...s,startupLocked:false};
const sent=h.confirm(s,intent,X,c);
assert.ok(sent.frame);s=sent.state;
assert.ok(h.context(s).state.pending);assert.equal(h.context(s).projection,null);
assert.equal(h.confirm(s,intent,X,c).frame,null);
const reply={version:1,kind:"ACTION",owner_id:A,sequence:2,next_action_sequence:2,can_execute:false,
 action_id:X,action_sequence:1,disposition:"REPORTED",code:"READ_STATUS_REQUIRED",
 result:{version:1,can_execute:false,adjustment_outcome:"UNVERIFIED"},invalidate:true};
s=feed(s,wire(reply)+wire(control("INVALIDATE"))+wire(status(3,2,R)));
assert.equal(s.session.status.requestId,R);
assert.equal(s.session.pending,null);
const beforeDetail=c.prepare(s.session,"CANCEL",null,null).prepared;
const requested=h.readHistory(s,R);s=requested.state;assert.ok(requested.frame);
assert.equal(h.context(s).historyPending,true);
assert.ok(h.waiting(s).includes("HISTORY"));
assert.equal(h.readHistory(s,R).frame,null);
assert.equal(h.confirm(s,c.prepare(s.session,"CANCEL",null,null).prepared,X,c).frame,null);
const detail={version:1,kind:"DETAIL",owner_id:A,sequence:4,next_action_sequence:2,can_execute:false,
 detail:{version:1,request:{id:R,state:"QUEUED",target_gib:16,original_actual_kib:25165816,
 requested_at:100,expires_at:200,changed_at:100,replaced_by:null},notification_events:[],
 withdrawal_evidence:null,adjustment_outcome:"UNVERIFIED",can_execute:false}};
s=feed(s,detail);assert.equal(s.history.requestId,R);assert.equal(s.sequence,4);
assert.equal(s.session.sequence,4);
assert.equal(h.confirm(s,beforeDetail,X,c).frame,null);
assert.equal(h.context(s).historyPending,false);
assert.equal(feed(s,detail).phase,"FAILED");
s=feed(s,wire(control("INVALIDATE"))+wire(status(5,2,R)));
assert.equal(s.history,null);
const cancel=h.confirm(s,c.prepare(s.session,"CANCEL",null,null).prepared,B,c);
assert.ok(cancel.frame);
s=h.stop(cancel.state,c,"TIMEOUT",1);
assert.ok(s.session.unresolved);assert.equal(s.projection,null);
s=h.start(s,c,2);
s=feed(s,wire(control("HELLO",B))+wire(control("INVALIDATE",B))+wire(status(1,1,R,B)));
assert.ok(s.session.unresolved && s.startupLocked);
assert.equal(feed(s,wire(control("INVALIDATE",A)),1),s);
assert.equal(h.stop(s,c,"OLD_TIMEOUT",1),s);
assert.equal(h.start(s,c,1),s);
assert.equal(h.confirm(s,intent,X,c).frame,null);
for(const bad of ["x".repeat(16384),"\u0100","{}\n",wire(control("HELLO",B)),wire({...status(2,1),can_execute:true}),wire(control("INVALIDATE",B))]){
 assert.equal(feed(connect(),bad).phase,"FAILED");
}
let t=connect();t=feed(t,"{");
assert.equal(t.buffer,"{");assert.equal(h.stop(t,c,"PARTIAL_TIMEOUT",1).buffer,"");
// Reused epoch and late generation callbacks fail closed.
let stale=h.stop(connect(),c,"TEST",1);
stale=h.start(stale,c,2);
assert.equal(feed(stale,control("HELLO",A)).phase,"FAILED");
// Canonical encoding rejects duplicate keys, whitespace, alternate numerics.
for(const line of ['{"version":1,"version":1,"kind":"HELLO","owner_id":"'+A+'","can_execute":false}\n',
    '{"version":1.0,"kind":"HELLO","owner_id":"'+A+'","can_execute":false}\n',
    ' '+wire(control("HELLO"))]) {
    assert.equal(feed(h.start(h.initial(c),c,1),line).phase,"FAILED");
}
// A scheduled publication racing a confirmed action is independently
// validated; pending remains until the matching ACTION reply.
let race=connect();race={...race,startupLocked:false};
race=h.confirm(race,c.prepare(race.session,"QUEUE",16,200).prepared,X,c).state;
assert.ok(h.waiting(race).includes("ACTION"));
race=feed(race,control("INVALIDATE"));
assert.ok(h.waiting(race).includes("PUBLICATION"));
const invalid=status(2,1);
invalid.projection.status.can_execute=true;
assert.equal(feed(race,invalid).phase,"FAILED");
assert.ok(feed(race,invalid).session.unresolved);
assert.equal(feed(race,control("INVALIDATE")).phase,"FAILED");
race=feed(race,status(2,1));
assert.ok(race.session.pending && !race.session.status);
assert.ok(!h.waiting(race).includes("PUBLICATION"));
const correlated={...reply,sequence:3};
race=feed(race,correlated);
assert.ok(!race.session.pending && race.publicationRequired);
assert.equal(feed(race,status(4,2,R)).phase,"FAILED");
race=feed(race,wire(control("INVALIDATE"))+wire(status(4,2,R)));
assert.equal(race.session.status.requestId,R);
console.log("R3c host controller PASS: startup lock, canonical framing, pending race, history watermark, timeout, generation fencing");

let recovering=connect();
const invRead=h.readRecovery(recovering,"INVENTORY",16);
recovering=invRead.state;
assert.ok(invRead.frame && h.waiting(recovering).includes("RECOVERY"));
assert.equal(h.readRecovery(recovering,"INVENTORY",1).frame,null);
assert.equal(h.readHistory(recovering,R).frame,null);
const inv={version:1,owner_id:A,kind:"INVENTORY",sequence:2,next_action_sequence:1,can_execute:false,
 inventory:{version:1,recent:[],truncated:false,prepared:null,pending_request_id:null,
 startup_unlock:false,adjustment_outcome:"UNVERIFIED",can_execute:false}};
assert.equal(feed(recovering,{...inv,inventory:{...inv.inventory,startup_unlock:true}}).phase,"FAILED");
assert.equal(feed(recovering,{...inv,inventory:{...inv.inventory,pending_request_id:R}}).phase,"FAILED");
recovering=feed(recovering,inv);
assert.equal(recovering.session.sequence,2);
assert.ok(h.recoveryContext(recovering).hostStatus.startupLocked);
assert.equal(h.recoveryContext(recovering).inventory.recent.length,0);
assert.equal(h.confirm(recovering,c.prepare(recovering.session,"QUEUE",16,200).prepared,X,c).frame,null);
const lookup=h.readRecovery(recovering,"LOCAL_ACTION",X);
const missing={version:1,owner_id:A,kind:"LOCAL_ACTION",sequence:3,next_action_sequence:1,
 can_execute:false,action_id:X,record:null};
assert.equal(feed(lookup.state,{...missing,action_id:B}).phase,"FAILED");
recovering=feed(lookup.state,missing);
assert.equal(h.recoveryContext(recovering).localAction.record,null);
assert.ok(recovering.startupLocked);
recovering=feed(recovering,control("INVALIDATE"));
assert.equal(h.recoveryContext(recovering).localAction,null);
recovering=feed(recovering,status(4,1));
recovering=h.readRecovery(recovering,"INVENTORY",1).state;
recovering=h.stop(recovering,c,"RECOVERY_TIMEOUT",1);
assert.equal(h.recoveryContext(recovering).inventory,null);
assert.equal(h.recoveryContext(recovering).hostStatus.phase,"FAILED");
console.log("R3e recovery read PASS: correlated inventory/lookup, no unlock, invalidation, timeout");

// R3m: same controller, explicitly configured staged transport. No public
// unlock; only fixture injects a reviewed startup result.
function stagedStart() {
 let s=h.start(h.initial(c),c,1,"STAGED");
 s=feed(s,wire(control("HELLO"))+wire(control("INVALIDATE"))+wire(status(1,1)));
 const i=c.prepare(s.session,"QUEUE",16,200).prepared;
 assert.equal(h.confirm(s,i,X,c).frame,null);
 return h.confirm({...s,startupLocked:false},i,X,c);
}
function stagedReceipt(s) {
 return {version:1,kind:"PREPARED_ACTION",owner_id:A,sequence:2,next_action_sequence:2,can_execute:false,
  record:{version:1,ordinal:1,message:s.session.pending,state:"PREPARED",prepared_at:100,
   result_request_id:null,committed_at:null,adjustment_outcome:"UNVERIFIED",can_execute:false},challenge:B};
}
const prep=stagedStart(), receipt=stagedReceipt(prep.state);
assert.equal(JSON.parse(prep.frame).kind,"PREPARE_ACTION");
assert.equal(h.takeCommit(prep.state,1).frame,null);
assert.equal(h.context(prep.state).actionStage,"WAIT_PREPARED");
assert.equal(feed(prep.state,reply).phase,"FAILED");
for(const bad of [{...receipt,owner_id:B},{...receipt,next_action_sequence:3},
 {...receipt,challenge:"bad"},{...receipt,record:{...receipt.record,state:"COMMITTED"}},
 {...receipt,record:{...receipt.record,message:{...receipt.record.message,target_gib:20}}}]) {
 const f=feed(prep.state,bad);
 assert.equal(f.phase,"FAILED");assert.ok(f.session.unresolved);
 assert.equal(h.takeCommit(f,1).frame,null);
}
let staged=feed(prep.state,wire(receipt).slice(0,12));
assert.equal(h.takeCommit(staged,1).frame,null);
staged=feed(staged,wire(receipt).slice(12));
assert.equal(h.context(staged).actionStage,"RECEIPT_READY");
assert.ok(h.waiting(staged).includes("ACTION"));
assert.equal(h.takeCommit(staged,2).frame,null);
assert.equal(feed(staged,receipt).phase,"FAILED");
assert.equal(h.takeCommit(feed(staged,"{"),1).frame,null);
const commit=h.takeCommit(staged,1);
assert.deepEqual(JSON.parse(commit.frame),{version:1,kind:"COMMIT_ACTION",
 message:JSON.parse(prep.frame).message,prepared_sequence:2,challenge:B});
assert.equal(h.context(commit.state).actionStage,"WAIT_COMMIT");
assert.equal(h.takeCommit(commit.state,1).frame,null);
assert.equal(h.readRecovery(commit.state,"INVENTORY",16).frame,null);
let complete=feed(commit.state,wire({...reply,sequence:3})+wire(control("INVALIDATE"))+wire(status(4,2,R)));
assert.equal(complete.session.status.requestId,R);assert.equal(complete.stage,null);
assert.equal(complete.session.pending,null);
for(const lost of [prep.state,staged,commit.state]) {
 let stopped=h.stop(lost,c,"DISCONNECT",1);
 assert.ok(stopped.session.unresolved);assert.equal(stopped.stage,null);
 stopped=h.start(stopped,c,2,"STAGED");
 stopped=feed(stopped,wire(control("HELLO",B))+wire(control("INVALIDATE",B))+wire(status(1,1,R,B)));
 assert.ok(stopped.startupLocked && stopped.session.unresolved);
 assert.equal(h.takeCommit(stopped,2).frame,null);
 assert.equal(feed(stopped,receipt,1),stopped);
}
console.log("R3m staged host PASS: receipt validation, one-use commit, partial frame, loss and restart refusal");

 // R3o: exact review and explicit acknowledgment; no auto-ACK or release.
const REVIEW="c23683a9-b2ab-4a2c-87ce-31bdf27a3099", DIG="a".repeat(64);
function reviewStart() {
 let s=h.stop(prep.state,c,"LOST",1);
 s=h.start(s,c,2,"STAGED",true);
 return feed(s,wire(control("HELLO",B))+wire(control("INVALIDATE",B))+wire(status(1,1,null,B)));
}
const rv={version:1,review_id:REVIEW,owner_id:B,action_id:X,review_digest:DIG,reviewed_at_ms:100000,
 snapshot:{version:1,record:receipt.record,pending_request_id:null,pending_digest:"b".repeat(64),
 adjustment_outcome:"UNVERIFIED",can_execute:false,startup_unlock:false},can_execute:false,startup_unlock:false};
const rp={version:1,kind:"RECOVERY_REVIEW",owner_id:B,sequence:2,next_action_sequence:1,can_execute:false,review:rv};
const saved={version:1,review:rv,acknowledged_at_ms:100100,disposition:"REVIEW_ACKNOWLEDGED_ONLY",
 adjustment_outcome:"UNVERIFIED",can_execute:false,startup_unlock:false};
const ack={version:1,kind:"RECOVERY_ACK",owner_id:B,sequence:3,next_action_sequence:1,can_execute:false,receipt:saved};
const selection={reviewId:REVIEW,digest:DIG,sequence:2};
assert.equal(h.beginReview(connect(),X).frame,null);
let rs=reviewStart();
let begin=h.beginReview(rs,X);
assert.equal(JSON.parse(begin.frame).kind,"RECOVERY_REVIEW");
assert.equal(h.acknowledgeReview(begin.state,selection,2).frame,null);
assert.equal(h.readRecovery(begin.state,"INVENTORY",16).frame,null);
for(const bad of [{...rv,startup_unlock:true},{...rv,action_id:R},{...rv,owner_id:A},
 {...rv,snapshot:{...rv.snapshot,pending_digest:"bad"}},
 {...rv,snapshot:{...rv.snapshot,record:{...receipt.record,can_execute:true}}}]) {
 assert.equal(feed(begin.state,{...rp,review:bad}).phase,"FAILED");
}
let ready=feed(begin.state,rp);
assert.equal(h.reviewContext(ready).phase,"REVIEW_READY");
assert.equal(h.reviewContext(ready).canAcknowledge,true);
assert.ok(h.waiting(ready).includes("RECOVERY"));
assert.equal(h.acknowledgeReview(ready,selection,1).frame,null);
assert.equal(h.acknowledgeReview(ready,{...selection,digest:"c".repeat(64)},2).frame,null);
let refreshed=feed(ready,control("INVALIDATE",B));
assert.equal(h.reviewContext(refreshed).canAcknowledge,false);
refreshed=feed(refreshed,status(3,1,R,B));
assert.equal(h.reviewContext(refreshed).canAcknowledge,false);
let validRefresh=feed(feed(ready,control("INVALIDATE",B)),status(3,1,null,B));
assert.ok(h.acknowledgeReview(validRefresh,selection,2).frame);
const issued=h.acknowledgeReview(ready,selection,2);
assert.equal(JSON.parse(issued.frame).kind,"RECOVERY_ACK");
assert.equal(h.acknowledgeReview(issued.state,selection,2).frame,null);
assert.equal(feed(issued.state,{...ack,receipt:{...saved,startup_unlock:true}}).phase,"FAILED");
let reviewed=feed(issued.state,ack);
assert.equal(h.reviewContext(reviewed).receipt.disposition,"REVIEW_ACKNOWLEDGED_ONLY");
assert.ok(reviewed.startupLocked && reviewed.session.unresolved);
assert.equal(h.takeCommit(reviewed,2).frame,null);
let lost=h.stop(issued.state,c,"ACK_LOST",2);
assert.equal(h.reviewContext(lost).unknownReviewId,REVIEW);
lost=h.start(lost,c,3,"STAGED",true);
lost=feed(lost,wire(control("HELLO",R))+wire(control("INVALIDATE",R))+wire(status(1,1,null,R)));
assert.equal(h.beginReview(lost,X).frame,null);
assert.equal(h.readReviewReceipt(lost,X).frame,null);
assert.equal(h.acknowledgeReview(lost,selection,3).frame,null);
const request=h.readReviewReceipt(lost,REVIEW);
const hist={version:1,kind:"RECOVERY_REVIEW_HISTORY",owner_id:R,sequence:2,next_action_sequence:1,
 can_execute:false,review_id:REVIEW,receipt:null};
let missingReceipt=feed(request.state,hist);
assert.equal(h.reviewContext(missingReceipt).unknownReviewId,REVIEW);
assert.equal(h.beginReview(missingReceipt,X).frame,null);
const again=h.readReviewReceipt(missingReceipt,REVIEW);
let recovered=feed(again.state,{...hist,sequence:3,receipt:saved});
assert.equal(h.reviewContext(recovered).unknownReviewId,null);
assert.equal(h.reviewContext(recovered).receipt.disposition,"REVIEW_ACKNOWLEDGED_ONLY");
assert.ok(recovered.startupLocked && recovered.session.unresolved);
assert.equal(h.takeCommit(recovered,3).frame,null);
console.log("R3o review host PASS: explicit ack, exact receipt, publication fencing, lost ACK lookup and no unlock");

 // R3q: pre-send checkpoint records contain no live continuation or grant.
const actionCheckpoint=h.checkpointForFrame(prep,recovery.row);
const ackCheckpoint=h.checkpointForFrame(issued,recovery.row);
assert.equal(actionCheckpoint.kind,"ACTION");
assert.equal(ackCheckpoint.kind,"REVIEW_ACK");
assert.equal(h.checkpointForFrame(commit,recovery.row),null);
assert.equal(h.checkpointForFrame({...issued,frame:issued.frame.replace('"review_sequence":2','"review_sequence":9')},recovery.row),null);
const snapshot={version:1,action:actionCheckpoint,acknowledgment:ackCheckpoint,startup_unlock:false,can_execute:false};
let restarted=h.restoreCheckpoint(c,snapshot,recovery.row);
assert.ok(restarted.startupLocked && restarted.session.unresolved && restarted.reviewLost);
assert.equal(restarted.session.pending,null);assert.equal(restarted.stage,null);
assert.equal(restarted.reviewFlow,null);assert.equal(h.takeCommit(restarted,1).frame,null);
assert.equal(h.acknowledgeReview(restarted,selection,1).frame,null);
assert.equal(h.restoreCheckpoint(c,{...snapshot,startup_unlock:true},recovery.row),null);
assert.equal(h.restoreCheckpoint(c,{...snapshot,action:{...actionCheckpoint,message:{...actionCheckpoint.message,target_gib:20}}},recovery.row),null);
let onlyAction=h.restoreCheckpoint(c,{...snapshot,acknowledgment:null},recovery.row);
assert.ok(onlyAction.session.unresolved && !onlyAction.reviewLost);
let onlyAck=h.restoreCheckpoint(c,{...snapshot,action:null},recovery.row);
assert.ok(onlyAck.session.unresolved && onlyAck.reviewLost);
let empty=h.restoreCheckpoint(c,{...snapshot,action:null,acknowledgment:null},recovery.row);
assert.ok(empty.startupLocked && !empty.session.unresolved);
restarted=h.start(restarted,c,1,"STAGED",true);
assert.equal(feed(restarted,control("HELLO",B)).phase,"FAILED");
restarted=feed(restarted,wire(control("HELLO",R))+wire(control("INVALIDATE",R))+wire(status(1,1,null,R)));
assert.equal(h.beginReview(restarted,X).frame,null);
const fullRestartLookup=h.readReviewReceipt(restarted,REVIEW);
assert.ok(fullRestartLookup.frame);
restarted=feed(fullRestartLookup.state,{...hist,receipt:saved});
assert.ok(restarted.startupLocked && restarted.session.unresolved);
assert.equal(restarted.reviewLost,null);
console.log("R3q checkpoint host PASS: pre-send correlation, fresh-shell lookup only, no unlock");

 // R3r: exercise the real one-shot Python adapter from the same controller
// used by QML. This is composed IO evidence, not a native shell wrapper.
{
 const os=require("node:os"),cp=require("node:child_process"),crypto=require("node:crypto");
 const folder=fs.mkdtempSync(path.join(os.tmpdir(),"queue-checkpoint-gate-"));
 const helper=path.join(root,"services/memory/memory_queue_checkpoint_io.py");
 const canonical=x=>x!==null&&typeof x==="object"
     ? Array.isArray(x)?x.map(canonical):Object.fromEntries(Object.keys(x).sort().map(k=>[k,canonical(x[k])])):x;
 const sha=x=>crypto.createHash("sha256").update(JSON.stringify(canonical(x))).digest("hex");
 const io=(command,record,dir=folder)=>cp.spawnSync("python3",["-B",helper,command,dir],{
    input:record===null?"":wire(record),encoding:"utf8",timeout:5000,maxBuffer:32768});
 const result=x=>x.status===0&&!x.error?JSON.parse(x.stdout):null;
 try {
   let s=h.start(h.initial(c),c,1,"STAGED",true,true);
   s=feed(s,wire(control("HELLO"))+wire(control("INVALIDATE"))+wire(status(1,1)));
   const intent=c.prepare(s.session,"QUEUE",16,200).prepared;
   assert.equal(h.confirm(s,intent,X,c).frame,null);
   const gated=h.confirm({...s,startupLocked:false},intent,X,c);
   assert.equal(gated.frame,null);
   assert.equal(gated.checkpoint.kind,"ACTION");
   assert.equal(h.context(gated.state).actionStage,"WAIT_CHECKPOINT");
   assert.ok(h.waiting(gated.state).includes("ACTION"));
   assert.equal(h.takeCommit(gated.state,1).frame,null);
   assert.equal(feed(gated.state,receipt).phase,"FAILED");
   assert.equal(h.finishCheckpoint(gated.state,null,2,c,recovery.row).state,gated.state);
   const savedAction=result(io("SAVE",gated.checkpoint));
   assert.ok(savedAction);
   const released=h.finishCheckpoint(gated.state,savedAction,1,c,recovery.row);
   assert.equal(JSON.parse(released.frame).kind,"PREPARE_ACTION");
   assert.equal(h.finishCheckpoint(released.state,savedAction,1,c,recovery.row).frame,null);
   const wrong=h.finishCheckpoint(gated.state,{...savedAction,record:{...gated.checkpoint,
      message:{...gated.checkpoint.message,target_gib:20}}},1,c,recovery.row);
   assert.equal(wrong.frame,null);assert.equal(wrong.state.phase,"FAILED");
   const failed=h.finishCheckpoint(gated.state,result(io("SAVE",gated.checkpoint)),1,c,recovery.row);
   assert.equal(failed.frame,null);assert.equal(failed.state.phase,"FAILED");
   assert.ok(failed.state.session.unresolved);
   const statusAfter=feed(gated.state,control("INVALIDATE"));
   assert.equal(h.finishCheckpoint(statusAfter,savedAction,1,c,recovery.row).frame,null);
   // The real helper computes the digest; use a correctly hashed snapshot.
   const liveReview={...rv,snapshot:{...rv.snapshot,pending_digest:sha(null)}};
   liveReview.review_digest=sha(liveReview.snapshot);
   let next=h.stop(released.state,c,"LOST",1);
   next=h.start(next,c,2,"STAGED",true,true);
   next=feed(next,wire(control("HELLO",B))+wire(control("INVALIDATE",B))+wire(status(1,1,null,B)));
   next=h.beginReview(next,X).state;
   next=feed(next,{...rp,review:liveReview});
   const select={reviewId:REVIEW,digest:liveReview.review_digest,sequence:2};
   const gatedAck=h.acknowledgeReview(next,select,2,recovery.row);
   assert.equal(gatedAck.frame,null);assert.equal(gatedAck.checkpoint.kind,"REVIEW_ACK");
   assert.equal(h.reviewContext(gatedAck.state).phase,"WAIT_CHECKPOINT");
   assert.ok(h.waiting(gatedAck.state).includes("RECOVERY"));
   const savedAck=result(io("SAVE",gatedAck.checkpoint));
   assert.ok(savedAck);
   const releasedAck=h.finishCheckpoint(gatedAck.state,savedAck,2,c,recovery.row);
   assert.equal(JSON.parse(releasedAck.frame).kind,"RECOVERY_ACK");
   assert.equal(h.finishCheckpoint(releasedAck.state,savedAck,2,c,recovery.row).frame,null);
   const loaded=result(io("LOAD",null));
   assert.equal(loaded.kind,"CHECKPOINT_LOADED");
   const restored=h.restoreCheckpoint(c,loaded.snapshot,recovery.row);
   assert.ok(restored.startupLocked && restored.session.unresolved && restored.reviewLost);
   assert.equal(h.takeCommit(restored,1).frame,null);
   assert.equal(h.finishCheckpoint(restored,savedAck,1,c,recovery.row).frame,null);
   assert.equal(h.acknowledgeReview(restored,select,1,recovery.row).frame,null);
   const corrupted=path.join(folder,"corrupt");
   fs.mkdirSync(corrupted,{mode:0o700});
   fs.writeFileSync(path.join(corrupted,"action-v1.json"),"{",{mode:0o600});
   const rejected=io("SAVE",gated.checkpoint,corrupted);
   assert.notEqual(rejected.status,0);assert.equal(rejected.stdout,"");
   assert.equal(h.finishCheckpoint(gated.state,result(rejected),1,c,recovery.row).frame,null);
   assert.notEqual(io("LOAD",null,corrupted).status,0);
   assert.notEqual(io("SAVE",{...gated.checkpoint,extra:true},corrupted).status,0);
   console.log("R3r checkpoint gate PASS: actual helper save/load, no frame before durable result, duplicate/failed/stale refusal");
 } finally {fs.rmSync(folder,{recursive:true,force:true});}
}
