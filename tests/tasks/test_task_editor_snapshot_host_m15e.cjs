#!/usr/bin/env node
"use strict";
const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),path=require("node:path");
const crypto=require("node:crypto");
const encryptedModel=require("./fixtures/TaskEncryptedDraftTransactionM13m.cjs");
const M=require("./fixtures/TaskEditorSnapshotHostM15e.cjs");
const root=path.resolve(__dirname,"../..");
let time,source,editors,reads,encrypted,failEncryption,host;
const src=()=>({bytes:Buffer.from(source.bytes),generation:source.generation,
                  ownerEpoch:source.ownerEpoch,committed:source.committed});
function setup(){
 time=1000;reads=[];encrypted=[];failEncryption=false;
 source={bytes:JSON.stringify({kind:"M13M_FAKE_TASKS_JSON",documentVersion:3,marker:"FAKE_M15E_SOURCE"}),generation:7,ownerEpoch:"SyntheticOwner7",committed:true};
 editors={entry:{identity:"new-task-1",editEpoch:2,dirty:true,savePending:false,text:"FAKE_ENTRY_SECRET"},
          details:{identity:"task-007",editEpoch:8,dirty:true,savePending:false,text:"FAKE_DETAILS_SECRET"}};
 host=M.createDisposableHost({marker:M.MARKER,readSource:src,clock:()=>time,
   readEditorState:target=>{const e=editors[target];return e?{target,identity:e.identity,editEpoch:e.editEpoch,dirty:e.dirty,savePending:e.savePending}:null;},
   readEditorSnapshot:target=>{reads.push(target);const e=editors[target];return e?{target,identity:e.identity,editEpoch:e.editEpoch,text:e.text}:null;},
   encryptSnapshot:draft=>{encrypted.push(draft);if(failEncryption)return false;
     // Compose the PREEXISTING M13m source-bound AES-GCM fixture. No new cipher.
     const k=crypto.randomBytes(32);
     const surface=draft.target==="entry"?"HUB":"DETAILS";
     const installationId="M15EInstall001",epoch=7;
     try{
       const prepared=encryptedModel.createSyntheticCheckpoint({
         source:{kind:"M13M_FAKE_SOURCE",generation:draft.source.generation,raw:source.bytes},
         ledger:{kind:"M13M_FAKE_LEDGER",installationId,epoch,
           sourceGeneration:draft.source.generation,
           sourceDigest:draft.source.digest,latestCommittedSeq:0},
         identity:{installationId,epoch,stageId:"m13a-M15EInstall001-7-1",surface},
         draft:{kind:"M13M_FAKE_EDITOR_DRAFT",surface,value:draft.text},
         key:k,optedIn:true,checkpointSeq:1
       });
       assert.equal(prepared.ok,true,prepared.status);
       assert.equal(prepared.persistAuthorized,false);
       assert.ok(!JSON.stringify(prepared.checkpoint).includes(draft.text));
       return prepared.ok;
     }finally{k.fill(0);}
   }});
}
const req=target=>host.client.request({scope:M.CAPTURE,target});
const take=(id,target)=>host.client.capture({requestId:id,scope:M.CAPTURE,target});
const authorize=id=>{host.syntheticOperator.enable();return host.syntheticOperator.approve({requestId:id});};
function noPower(result){for(const k of Object.keys(M.DENIED))assert.equal(result[k],false,k);
 assert.doesNotMatch(JSON.stringify(result),/FAKE_(ENTRY|DETAILS)_SECRET|task-007|new-task-1/);}
test("no registered real host: not mounted or callable from real TASKS",()=>{
  const j=fs.readFileSync(path.join(root,"widgets/TasksW.qml"),"utf8");
  const ui=fs.readFileSync(path.join(root,"widgets/tasks/TaskEncryptedDraftAccessPaneM15c.qml"),"utf8");
  const c=fs.readFileSync(path.join(root,"services/connections/ConnectionsBroker.qml"),"utf8");
  const store=fs.readFileSync(path.join(root,"services/hub/ApolloHubTodoStore.qml"),"utf8");
  const shell=fs.readFileSync(path.join(root,"shell.qml"),"utf8");
  for(const x of [j,ui,store,shell])assert.doesNotMatch(x,/TaskEditorSnapshotHostM15e/);
  assert.match(ui,/readonly property bool canCaptureDraft: false/);
  assert.match(ui,/available: false/);
  assert.match(c,/readonly property bool credentialActionsEnabled: false/);
  assert.equal((store.match(/\bFileView\s*\{/g)||[]).length,1);
  assert.equal((store.match(/\btodoFile\.setText\s*\(/g)||[]).length,1);
  assert.doesNotMatch(j,/readEditorSnapshot|TaskEditorSnapshotHostM15e/);
});
test("refuses wrong scope, no target, no approval without observing text",()=>{
 setup();for(const scope of [M.PREVIEW,M.CLEAR,"tasks.draft.capture","BAD"]){
   noPower(host.client.request({scope,target:"entry"}));}
 const none=host.client.request({scope:M.CAPTURE,target:"none"});assert.equal(none.ok,false);noPower(none);
 const r=req("entry");noPower(r);assert.equal(reads.length,0);
 const x=take(r.requestId,"entry");assert.equal(x.ok,false);noPower(x);
 assert.equal(reads.length,0);assert.equal(encrypted.length,0);
});
test("one operator-chosen editor captured only after test approval; replay and cross-target denied",()=>{
 setup();const r=req("entry");assert.equal(reads.length,0);
 authorize(r.requestId);assert.equal(reads.length,0);
 const wrong=take(r.requestId,"details");assert.equal(wrong.ok,false);noPower(wrong);
 const success=take(r.requestId,"entry");assert.equal(success.ok,true);noPower(success);
 assert.deepEqual(reads,["entry"]);assert.equal(encrypted.length,1);
 assert.equal(encrypted[0].text,"FAKE_ENTRY_SECRET");
 assert.equal(take(r.requestId,"entry").ok,false);
 assert.equal(reads.length,1);
});
test("stale source, editor identity, edit epoch, saved state and pending writes fail before plaintext",()=>{
 for(const mutate of [()=>source.bytes+=' ',()=>source.generation++,()=>source.ownerEpoch='OtherOwner',
  ()=>editors.details.identity='other-task',()=>editors.details.editEpoch++,
  ()=>editors.details.savePending=true,()=>editors.details.dirty=false,
  ()=>source.committed=false]){
   setup();const r=req("details");authorize(r.requestId);mutate();
   const x=take(r.requestId,"details");assert.equal(x.ok,false,x.status);
   noPower(x);assert.equal(reads.length,0);assert.equal(encrypted.length,0);
 }
});
test("revocation, expiry, malformed request and duplicate approval deny",()=>{
 setup();let r=req("entry");authorize(r.requestId);
 host.syntheticOperator.revoke();assert.equal(take(r.requestId,"entry").ok,false);assert.equal(reads.length,0);
 setup();r=req("entry");authorize(r.requestId);time+=30001;
 assert.equal(take(r.requestId,"entry").status,"EXPIRED");assert.equal(reads.length,0);
 setup();r=req("entry");authorize(r.requestId);
 assert.equal(host.syntheticOperator.approve({requestId:r.requestId}).ok,false);
 const bad=host.client.capture({requestId:r.requestId,scope:M.CAPTURE,target:"entry",text:"FAKE_ENTRY_SECRET"});
 assert.equal(bad.ok,false);assert.equal(reads.length,0);noPower(bad);
});
test("mutation during draft read and encryption failure retain draft and report no powers",()=>{
 setup();
 // Recreate to change editor during read, no production import.
 host=M.createDisposableHost({marker:M.MARKER,readSource:src,clock:()=>time,
   readEditorState:target=>({target,identity:editors[target].identity,
     editEpoch:editors[target].editEpoch,dirty:true,savePending:false}),
   readEditorSnapshot:target=>{reads.push(target);editors[target].editEpoch++;
     return {target,identity:"task-007",editEpoch:8,text:"FAKE_DETAILS_SECRET"};},
   encryptSnapshot:()=>{throw Error("MUST_NOT_ENCRYPT_STALE");}});
 const again=req("details");authorize(again.requestId);
 const bad=take(again.requestId,"details");assert.equal(bad.ok,false);noPower(bad);
 assert.equal(bad.status,"SOURCE_OR_EDITOR_CHANGED_DURING_SNAPSHOT");
 assert.equal(encrypted.length,0);
 setup();failEncryption=true;const e=req("entry");authorize(e.requestId);
 const failed=take(e.requestId,"entry");assert.equal(failed.ok,false);noPower(failed);
 assert.equal(failed.status,"ENCRYPTION_NOT_CONFIRMED");
});
test("refuses deployment without disposable marker",()=>{
 assert.throws(()=>M.createDisposableHost({marker:"production"}),/M15E_REFUSED/);
});
