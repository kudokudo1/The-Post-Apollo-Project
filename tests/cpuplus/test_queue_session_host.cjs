const assert=require("node:assert/strict"),fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const root=path.join(__dirname,"../..");
function load(file){const c=vm.createContext({});vm.runInContext(fs.readFileSync(file,"utf8"),c);return c;}
const h=load(path.join(root,"services/memory/MemoryQueueSessionHost.js"));
const c=load(path.join(root,"widgets/cpuplus/CpuPlusQueueConsumer.js"));
const p=load(path.join(root,"widgets/cpuplus/CpuPlusQueuePresentation.js"));
const history=load(process.argv[2]);
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
function feed(s,x){return h.feed(s,typeof x==="string"?x:wire(x),c,p.project,history.project);}
function connect(owner=A){
 let s=h.start(h.initial(c),c);
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
const requested=h.readHistory(s,R);s=requested.state;assert.ok(requested.frame);
assert.equal(h.readHistory(s,R).frame,null);
assert.equal(h.confirm(s,c.prepare(s.session,"CANCEL",null,null).prepared,X,c).frame,null);
const detail={version:1,kind:"DETAIL",owner_id:A,sequence:4,next_action_sequence:2,can_execute:false,
 detail:{version:1,request:{id:R,state:"QUEUED",target_gib:16,original_actual_kib:25165816,
 requested_at:100,expires_at:200,changed_at:100,replaced_by:null},notification_events:[],
 withdrawal_evidence:null,adjustment_outcome:"UNVERIFIED",can_execute:false}};
s=feed(s,detail);assert.equal(s.history.requestId,R);assert.equal(s.sequence,4);
assert.equal(feed(s,detail).phase,"FAILED");
s=feed(s,wire(control("INVALIDATE"))+wire(status(5,2,R)));
assert.equal(s.history,null);
const cancel=h.confirm(s,c.prepare(s.session,"CANCEL",null,null).prepared,B,c);
assert.ok(cancel.frame);
s=h.stop(cancel.state,c,"TIMEOUT");
assert.ok(s.session.unresolved);assert.equal(s.projection,null);
s=h.start(s,c);
s=feed(s,wire(control("HELLO",B))+wire(control("INVALIDATE",B))+wire(status(1,1,R,B)));
assert.ok(s.session.unresolved && s.startupLocked);
assert.equal(h.confirm(s,intent,X,c).frame,null);
for(const bad of ["x".repeat(16384),"\u0100","{}\n",wire(control("HELLO",B)),wire({...status(2,1),can_execute:true}),wire(control("INVALIDATE",B))]){
 assert.equal(feed(connect(),bad).phase,"FAILED");
}
let t=connect();t=feed(t,"{");
assert.equal(t.buffer,"{");assert.equal(h.stop(t,c,"PARTIAL_TIMEOUT").buffer,"");
console.log("R3c host controller PASS: startup lock, framing, pending, history, timeout, reconnect");
