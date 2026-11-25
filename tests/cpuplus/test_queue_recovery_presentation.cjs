const assert=require("node:assert/strict"),fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const dir=path.join(__dirname,"../../widgets/cpuplus"),c=vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(dir,"CpuPlusQueueRecovery.js"),"utf8"),c);
const O="c23683a9-b2ab-4a2c-87ce-31bdf27a3012",A="c23683a9-b2ab-4a2c-87ce-31bdf27a3013",R="c23683a9-b2ab-4a2c-87ce-31bdf27a3014",B="c23683a9-b2ab-4a2c-87ce-31bdf27a3015";
const m={version:1,owner_id:O,action_id:A,action_sequence:1,kind:"QUEUE",expected_request_id:null,target_gib:16,expires_at:200};
const committed={version:1,ordinal:1,message:m,state:"COMMITTED",prepared_at:100,result_request_id:R,committed_at:101,adjustment_outcome:"UNVERIFIED",can_execute:false};
const prepared={...committed,ordinal:2,message:{...m,kind:"CANCEL",action_id:B,action_sequence:2,expected_request_id:R,target_gib:null,expires_at:null},state:"PREPARED",prepared_at:110,result_request_id:null,committed_at:null};
const packet={version:1,recent:[prepared,committed],truncated:false,prepared,pending_request_id:R,startup_unlock:false,adjustment_outcome:"UNVERIFIED",can_execute:false};
const p=c.project(packet);
assert.equal(p.startupLocked,true);assert.equal(p.prepared.actionId,B);assert.equal(p.recent[1].resultId,R);
assert.equal(c.project({...packet,recent:[committed],prepared:null}).prepared,null);
assert.equal(c.project({...packet,recent:[],prepared:null,pending_request_id:null}).startupLocked,true);
for(const bad of [
 {...packet,startup_unlock:true},{...packet,can_execute:true},{...packet,adjustment_outcome:"VERIFIED"},
 {...packet,recent:[committed,prepared]},{...packet,recent:[prepared,prepared]},
 {...packet,prepared:null},{...packet,recent:[committed],prepared},
 {...packet,recent:[{...prepared,result_request_id:R},committed]},
 {...packet,recent:[prepared,{...committed,message:{...m,source:{inode:42}}}]},
 {...packet,recent:[prepared,{...committed,committed_at:99}]},
 {...packet,recent:[prepared,{...committed,message:{...m,target_gib:17}}]}
]) assert.equal(c.project(bad),null);
const host={phase:"CONNECTED",startupLocked:true,historyPending:false,actionPending:false,unresolved:false};
assert.match(c.gate(host),/STARTUP RECONCILIATION REQUIRED/);
assert.match(c.gate({...host,unresolved:true}),/OUTCOME UNKNOWN/);
assert.match(c.gate(null),/LOCKED/);
assert.match(c.gate({...host,phase:"FAILED"}),/FAILED/);
const ui=fs.readFileSync(path.join(dir,"CpuPlusQueueRecoveryPane.qml"),"utf8");
assert.doesNotMatch(ui,/\b(?:Process|Timer|MemoryOperation|execDetached)\b/);
assert.match(ui,/ADJUSTMENT OUTCOME \/\/ UNVERIFIED/);
console.log("CPU++ recovery presentation contract PASS");

const ctx={hostStatus:host,inventory:packet,localAction:null,recoveryPending:false};
assert.equal(c.context(ctx).inventory.recent.length,2);
assert.equal(c.canRead(ctx,true),true); // reads while startup locked
assert.equal(c.canRead(ctx,false),false);
const unknown={...host,unresolved:true};
const local={actionId:A,record:committed,outcome:"UNVERIFIED",canExecute:false};
const lookup={hostStatus:unknown,inventory:null,localAction:local,recoveryPending:false};
assert.equal(c.context(lookup).localAction.record.resultId,R);
assert.equal(c.canRead(lookup,true),true);
assert.equal(c.context({...lookup,localAction:{...local,record:null}}).localAction.missing,true);
for(const bad of [
    {...lookup,inventory:packet},
    {...lookup,localAction:{...local,actionId:B}},
    {...lookup,localAction:{...local,canExecute:true}},
    {...lookup,hostStatus:{...unknown,phase:"FAILED"}},
    {...lookup,hostStatus:{...unknown,actionPending:true}},
    {...lookup,recoveryPending:true}
]) assert.equal(c.context(bad),null);
const pending={hostStatus:{...unknown,historyPending:true},inventory:null,localAction:null,recoveryPending:true};
assert.equal(c.context(pending).readPending,true);
assert.equal(c.canRead(pending,true),false);
assert.equal(c.context({...pending,inventory:packet}),null);
const stopped={hostStatus:{...unknown,phase:"STOPPED"},inventory:null,localAction:null,recoveryPending:false};
assert.equal(c.context(stopped).localAction,null);
assert.equal(c.canRead(stopped,true),false);
assert.equal(c.context(null),null);
assert.match(ui,/atomicMode \? \(snapshot \? snapshot.inventory : null\) : Recovery.project\(inventory\)/);
assert.match(ui,/recoveryReadRequested\(kind,value\)/);
assert.match(ui,/NO RECORD REPORTED \/\/ NOT PROOF OF NONCOMMIT/);
console.log("CPU++ canonical recovery context presentation PASS");
