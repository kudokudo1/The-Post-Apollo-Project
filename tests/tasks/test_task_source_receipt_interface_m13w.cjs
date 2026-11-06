#!/usr/bin/env node
"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const ROOT=path.resolve(__dirname,"../..");
function load(file) {
  const code=fs.readFileSync(path.join(ROOT,file),"utf8").replace(/^\.pragma library\s*/,"");
  const sandbox=vm.createContext({});
  vm.runInContext(code,sandbox,{filename:file,timeout:1000});
  return sandbox;
}
const contract=load("services/hub/TaskSaveTicketContractM12o.js");
const policy=load("services/hub/TaskSourceReceiptReviewPolicyM13w.js");
const clone=x=>JSON.parse(JSON.stringify(x));
const makeView=name=>({state:"ready",writable:true,
  items:[{id:"FAKE_ITEM",title:name}],projects:[],total:1,remaining:1});
const baseline=makeView("BEFORE"),expected=makeView("AFTER");
function sample(surface="HUB",method="renameTask") {
  const ticket=contract.begin(surface,method,"m12o-ticket-000001",
                              baseline,expected,{dirty:true,present:true});
  assert.ok(ticket);
  const pin={ticketId:ticket.ticketId,stageId:"m13v-stage-000001",
    ownerEpoch:0,baselineRevision:0,expectedSourceSha256:"a".repeat(64)};
  const evidence={status:"SYNTHETIC_RECEIPT_OBSERVED_UI_UNACKNOWLEDGED",
    fixtureOnly:true,receipt:{revision:1,stageId:pin.stageId,
    ownerEpoch:0,sourceSha256:pin.expectedSourceSha256},independentlyReadBack:true};
  for(const flag of policy.MUST_REMAIN_FALSE)evidence[flag]=false;
  return {ticket,pin,evidence,snapshot:clone(expected)};
}
function safe(x) {
  assert.equal(x.draftDisposition,"KEEP_DRAFT");
  assert.equal(x.lastConfirmedVisible,true);
  for(const flag of ["autoReplay","localSaved","sourceReceiptAuthenticated",
    "userSaveAcknowledged","keyReleaseAuthorized","realGrantActive",
    "canWriteTasks","canCapture","canPreview","canClear","canRestore",
    "draftPresentInResult"])assert.equal(x[flag],false,flag);
  assert.doesNotMatch(JSON.stringify(x),/FAKE_ITEM|BEFORE|AFTER|aaaaaaaaaa/);
  for(const key of ["receipt","ticket","pin","draft","baseline","expected",
    "sourceSha256","content"])assert.equal(Object.hasOwn(x,key),false,key);
}
test("all M12o consumer methods yield review-only, never saved",()=>{
  for(const [surface,methods] of Object.entries(clone(policy.ROUTES))) {
    for(const method of methods) {
      const s=sample(surface,method);
      const out=policy.inspectSynthetic(s.ticket,s.pin,s.evidence,s.snapshot);
      assert.equal(out.status,"SOURCE_MATCHED_SYNTHETIC_ONLY",surface+"."+method);
      assert.equal(out.state,"NEEDS_TRUSTED_OWNER");
      safe(out);
    }
  }
});
test("no receipt, native callback, or alleged CONFIRMED can authorize saving",()=>{
  const s=sample();
  const absent=policy.inspectSynthetic(s.ticket,s.pin,null,s.snapshot);
  assert.equal(absent.status,"WAITING_FOR_SOURCE_EVIDENCE");safe(absent);
  for(const evidence of [
    {status:"NATIVE_HINT_ONLY_NOT_A_RECEIPT"},
    {status:"SYNTHETIC_STAGE_RESERVED_NO_SOURCE_WRITE"},
    {status:"CONFIRMED",evidence:"SYNTHETIC_READBACK_RECEIPT"},
    {...s.evidence,fixtureOnly:false}
  ]) {
    const result=policy.inspectSynthetic(s.ticket,s.pin,evidence,s.snapshot);
    assert.equal(result.status,"UNTRUSTED_SOURCE_EVIDENCE");
    safe(result);
  }
});
test("production grants and forged review fields are rejected",()=>{
  const s=sample();
  for(const flag of policy.MUST_REMAIN_FALSE) {
    const out=policy.inspectSynthetic(s.ticket,s.pin,
      {...s.evidence,[flag]:true},s.snapshot);
    assert.equal(out.status,"UNTRUSTED_SOURCE_EVIDENCE",flag);safe(out);
  }
  const incomplete={...s.evidence};delete incomplete.durableUserSaveAcknowledged;
  assert.equal(policy.inspectSynthetic(s.ticket,s.pin,incomplete,s.snapshot).status,
    "UNTRUSTED_SOURCE_EVIDENCE");
  assert.equal(policy.inspectSynthetic(s.ticket,s.pin,
    {...s.evidence,approvedByUser:true},s.snapshot).status,
    "UNTRUSTED_SOURCE_EVIDENCE");
});
test("scope, stage, epoch, revision, digest and ticket mismatch refuse",()=>{
  const s=sample();
  for(const pin of [
    {...s.pin,ticketId:"m12o-other-000001"},
    {...s.pin,stageId:"m13v-stage-000002"},
    {...s.pin,ownerEpoch:1},
    {...s.pin,baselineRevision:1},
    {...s.pin,baselineRevision:true},
    {...s.pin,expectedSourceSha256:"b".repeat(64)},
    {...s.pin,sourceTrusted:true},
  ]) {
    const out=policy.inspectSynthetic(s.ticket,pin,s.evidence,s.snapshot);
    assert.notEqual(out.status,"SOURCE_MATCHED_SYNTHETIC_ONLY");safe(out);
  }
  for(const receipt of [
    {...s.evidence.receipt,sourceSha256:"b".repeat(64)},
    {...s.evidence.receipt,revision:2},
    {...s.evidence.receipt,ownerEpoch:1},
    {...s.evidence.receipt,stageId:"m13v-stage-000099"},
    {...s.evidence.receipt,scope:"tasks.draft.capture.encrypted"},
  ]) {
    const out=policy.inspectSynthetic(s.ticket,s.pin,
      {...s.evidence,receipt},s.snapshot);
    assert.equal(out.status,"STALE_OR_MISMATCHED_SOURCE_REVISION");safe(out);
  }
});
test("snapshot conflict and terminal tickets never clear the user's draft",()=>{
  const s=sample();
  for(const snapshot of [clone(baseline),{...s.snapshot,state:"saving"},
                         {...s.snapshot,items:[]},null]) {
    const out=policy.inspectSynthetic(s.ticket,s.pin,s.evidence,snapshot);
    assert.equal(out.status,"SAVED_SNAPSHOT_MISMATCH");safe(out);
  }
  for(const state of ["CONFIRMED","REVIEW_REQUIRED","REJECTED"]) {
    const out=policy.inspectSynthetic(
      {...s.ticket,state},s.pin,s.evidence,s.snapshot);
    assert.equal(out.status,"TICKET_NOT_VERIFIED");safe(out);
  }
});
test("disabled QML facade never imports into the actual single source writer",()=>{
  const qml=fs.readFileSync(path.join(ROOT,
    "services/hub/TaskSourceReceiptFacadeM13w.qml"),"utf8");
  const js=fs.readFileSync(path.join(ROOT,
    "services/hub/TaskSourceReceiptReviewPolicyM13w.js"),"utf8");
  const store=fs.readFileSync(path.join(ROOT,
    "services/hub/ApolloHubTodoStore.qml"),"utf8");
  const shell=fs.readFileSync(path.join(ROOT,"shell.qml"),"utf8");
  const broker=fs.readFileSync(path.join(ROOT,
    "services/connections/ConnectionsBroker.qml"),"utf8");
  assert.match(qml,/TaskSaveTicketContractM12o\.js/);
  assert.match(qml,/readonly property bool enabled: false/);
  for(const name of ["productionWriterAuthorized","sourceOwnerAuthenticated",
    "nativeCallbackAuthenticated","durableReceiptAuthenticated",
    "consentAuthenticated","draftRecoveryEnabled"])assert.match(
      qml,new RegExp("readonly property bool "+name+": false"));
  assert.match(qml,/reason:"M13W_DISABLED_NO_WRITER"/);
  assert.doesNotMatch(store+shell,
    /TaskSourceReceiptFacadeM13w|TaskSourceReceiptReviewPolicyM13w/);
  assert.equal((store.match(/\bFileView\s*\{/g)||[]).length,1);
  assert.equal((store.match(/todoFile\.setText\(/g)||[]).length,1);
  assert.match(store,/readonly property bool ticketProducerEnabled: false/);
  assert.match(store,/readonly property bool encryptedRecoveryEnabled: false/);
  assert.match(broker,/readonly property bool credentialActionsEnabled: false/);
  for(const text of [qml,js])assert.doesNotMatch(text,
    /\bFileView\s*\{|\bProcess\s*\{|Quickshell\.dataDir|\.setText\(|secret-tool|gnome-keyring|\.exec\(|fetch\(/);
});
