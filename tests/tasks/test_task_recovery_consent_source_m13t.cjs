#!/usr/bin/env node
"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const os=require("node:os");
const path=require("node:path");
const model=require("./fixtures/TaskRecoveryConsentSourceM13t.cjs");
const ROOT=path.resolve(__dirname,"../..");
const CAPTURE=model.SCOPES[0], PREVIEW=model.SCOPES[1], CLEAR=model.SCOPES[2];
function disposable() {
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),"postapollo-m13t-disposable-"));
  fs.chmodSync(dir,0o700);
  const source=path.join(dir,"synthetic-source.json");
  const put=x=>fs.writeFileSync(source,JSON.stringify(x),{mode:0o600});
  put({version:3,tasks:[{id:"FAKE_01",title:"FAKE"}]});
  let instant=1000;
  const h=model.createDisposableModel({marker:model.MARKER,
    readSavedSource:()=>fs.readFileSync(source),clock:()=>instant});
  return {h,put,tick:n=>instant+=n,eraseSource:()=>fs.unlinkSync(source),
          remove:()=>fs.rmSync(dir,{recursive:true,force:true})};
}
function noPower(out){
  for(const [key,value] of Object.entries(model.NO_POWER)){
    assert.equal(value,false,key);
    assert.equal(out[key],false,key);
  }
  assert.doesNotMatch(JSON.stringify(out),/FAKE_01|"title":"FAKE"|keyBytes|secret/i);
}
function ask(h,scope=CAPTURE){return h.client.propose({feature:model.FEATURE,scope});}
function consume(h,req){return h.client.consume({requestId:req.requestId,scope:req.scope});}
test("refuses activation outside disposable test mode",()=>{
  assert.throws(()=>model.createDisposableModel({marker:"NORMAL_SESSION",
    readSavedSource:()=>Buffer.from("{}"),clock:()=>1000}),/M13T_REFUSED/);
});
test("default off, exact scopes, and forged caller metadata refusal",()=>{
  const f=disposable();try{
    const {client,syntheticOperator:operator}=f.h;
    noPower(client.availability());
    assert.equal(client.availability().optInSimulated,false);
    for(const bad of ["*","mail.read","tasks.draft.*",null,{}]){
      const o=ask(f.h,bad);assert.equal(o.ok,false);noPower(o);
    }
    const poison=client.propose({feature:model.FEATURE,scope:CAPTURE,admin:true});
    assert.equal(poison.ok,false);noPower(poison);
    for(const scope of model.SCOPES){
      const q=ask(f.h,scope);
      assert.equal(q.ok,true);noPower(q);
      assert.equal(consume(f.h,q).status,"FEATURE_OPT_IN_OFF");
      assert.equal(operator.approve({requestId:q.requestId}).status,"FEATURE_OPT_IN_OFF");
    }
  }finally{f.remove();}
});
test("synthetic opt-in and independent approval required for each single-use review",()=>{
  const f=disposable();try{
    const h=f.h;
    const q=ask(h,PREVIEW);
    assert.equal(h.syntheticOperator.optIn().ok,true);
    assert.equal(consume(h,q).status,"REVIEW_NOT_ACTIVE_OR_REPLAYED");
    noPower(h.syntheticOperator.approve({requestId:q.requestId}));
    const result=consume(h,q);assert.equal(result.ok,true);noPower(result);
    assert.equal(result.simulatedReviewConsumed,true);
    assert.equal(consume(h,q).status,"REVIEW_NOT_ACTIVE_OR_REPLAYED");
    const other=h.client.consume({requestId:q.requestId,scope:CLEAR});
    assert.equal(other.status,"UNKNOWN_OR_MISMATCHED_REVIEW");noPower(other);
  }finally{f.remove();}
});
test("stale source changed before approval or consumption never passes",()=>{
  const f=disposable();try{
    const h=f.h;h.syntheticOperator.optIn();
    const a=ask(h,CAPTURE);
    f.put({version:3,tasks:[{id:"FAKE_01",title:"EDITED"}]});
    const denied=h.syntheticOperator.approve({requestId:a.requestId});
    assert.equal(denied.status,"SAVED_SOURCE_CHANGED_REVIEW_REQUIRED");noPower(denied);
    const b=ask(h,CAPTURE);
    h.syntheticOperator.approve({requestId:b.requestId});
    f.put({version:3,tasks:[{id:"FAKE_01",title:"AGAIN"}]});
    const refused=consume(h,b);
    assert.equal(refused.status,"SAVED_SOURCE_CHANGED_REVIEW_REQUIRED");noPower(refused);
    assert.equal(consume(h,b).status,"REVIEW_NOT_ACTIVE_OR_REPLAYED");
  }finally{f.remove();}
});
test("expiry, denial, opt-out, and missing source fail closed",()=>{
  const f=disposable();try{
    const h=f.h;h.syntheticOperator.optIn();
    const a=ask(h,CLEAR);noPower(h.syntheticOperator.deny({requestId:a.requestId}));
    assert.equal(consume(h,a).status,"REVIEW_NOT_ACTIVE_OR_REPLAYED");
    const b=ask(h,CLEAR);
    f.tick(300000);
    assert.equal(h.syntheticOperator.approve({requestId:b.requestId}).status,"REVIEW_EXPIRED");
    const c=ask(h,CAPTURE);
    h.syntheticOperator.approve({requestId:c.requestId});
    h.syntheticOperator.optOut();
    assert.equal(consume(h,c).status,"FEATURE_OPT_IN_OFF");
    assert.equal(h.client.availability().optInSimulated,false);
    const d=ask(h,CLEAR);
    h.syntheticOperator.optIn();
    h.syntheticOperator.approve({requestId:d.requestId});
    f.eraseSource();
    assert.equal(consume(h,d).status,"SAVED_SOURCE_CHANGED_REVIEW_REQUIRED");
    assert.equal(ask(h,CAPTURE).status,"SAVED_SOURCE_NOT_OBSERVED");
  }finally{f.remove();}
});
test("no product imports; existing shared broker and source writer remain disabled",()=>{
  const src=fs.readFileSync(path.join(ROOT,"tests/tasks/fixtures/TaskRecoveryConsentSourceM13t.cjs"),"utf8");
  const hub=fs.readFileSync(path.join(ROOT,"services/hub/ApolloHubTodoStore.qml"),"utf8");
  const broker=fs.readFileSync(path.join(ROOT,"services/connections/ConnectionsBroker.qml"),"utf8");
  const task=fs.readFileSync(path.join(ROOT,"widgets/TasksW.qml"),"utf8");
  assert.doesNotMatch(src,/secret-tool|dbus|gnome-keyring|writeFileSync|\.setText\(|\.exec\(/i);
  for(const text of [hub,broker,task])assert.doesNotMatch(text,/TaskRecoveryConsentSourceM13t/);
  assert.equal((hub.match(/\bFileView\s*\{/g)||[]).length,1);
  assert.equal((hub.match(/\btodoFile\.setText\s*\(/g)||[]).length,1);
  assert.match(hub,/readonly property bool encryptedRecoveryEnabled:\s*false/);
  assert.match(broker,/readonly property bool credentialActionsEnabled:\s*false/);
});
