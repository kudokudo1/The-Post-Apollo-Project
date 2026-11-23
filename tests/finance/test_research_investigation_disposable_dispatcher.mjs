import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { ResearchWriteAttempt } from "../../scripts/finance/research_investigation_write_attempt.mjs";
import { DisposableResearchDispatcher } from "../../scripts/finance/research_investigation_disposable_dispatcher.mjs";

const clock=()=> "2026-11-23T15:00:00.000Z";
const ids=[
  "12345678-1234-4234-8234-123456789abc",
  "12345678-1234-4234-8234-123456789abd",
  "12345678-1234-4234-8234-123456789abe",
  "12345678-1234-4234-8234-123456789abf"
];
let next=0;
const options={clock,newId:()=>ids[next++]};
const probe=fs.mkdtempSync(path.join(os.tmpdir(),"finance-research-m4b-t2-sentinel-"));
const priorHome=process.env.XDG_DATA_HOME;
process.env.XDG_DATA_HOME=path.join(probe,"must-remain-absent");
const test=new DisposableResearchDispatcher();
try {
  assert.equal(test.mode,"DISPOSABLE_TEST_ONLY");
  assert.equal(test.closed,false);
  assert.throws(()=>new DisposableResearchDispatcher(path.join(probe,"live")),
    /TARGET_OVERRIDE_FORBIDDEN/);
  let snapshot=test.readTestSnapshot();
  assert.equal(snapshot.revision,0);
  assert.equal(fs.existsSync(process.env.XDG_DATA_HOME),false);

  const create=new ResearchWriteAttempt(
    {action:"create",title:"Disposable investigation",question:"What is documented?"},
    snapshot,options);
  const result=await create.dispatchOnce(async frame=>test.dispatch(frame));
  assert.equal(result.state,"acknowledged");
  assert.equal(result.revision,1);
  assert.equal(test.dispatchCount,1);
  assert.equal(create.getDraft(),null);
  snapshot=test.readTestSnapshot();
  assert.equal(snapshot.investigations.length,1);
  const caseId=snapshot.investigations[0].id;

  const attach=new ResearchWriteAttempt(
    {action:"attach",investigationId:caseId,title:"Manual public source",
      summary:"Unverified and explicitly entered",
      url:"https://www.sec.gov/Archives/edgar/data/320193/example.htm"},
    snapshot,options);
  assert.equal((await attach.dispatchOnce(async f=>test.dispatch(f))).state,"acknowledged");
  snapshot=test.readTestSnapshot();
  assert.equal(snapshot.revision,2);
  assert.equal(snapshot.investigations[0].evidence[0].source,"manual");
  assert.equal(snapshot.investigations[0].evidence[0].reviewed,false);

  const stale=new ResearchWriteAttempt(
    {action:"create",title:"Stale case",question:"Should this save?"},
    {schemaVersion:1,revision:0,investigations:[]},options);
  assert.equal((await stale.dispatchOnce(async f=>test.dispatch(f))).state,"reviewRequired");
  assert.equal(stale.getDraft().title,"Stale case");
  assert.equal(test.readTestSnapshot().revision,2);
  await assert.rejects(stale.dispatchOnce(async f=>test.dispatch(f)),/WRITE_ALREADY_ATTEMPTED/);

  const remove=new ResearchWriteAttempt(
    {action:"remove",investigationId:caseId,
      evidenceId:snapshot.investigations[0].evidence[0].id},
    snapshot,options);
  assert.equal((await remove.dispatchOnce(async f=>test.dispatch(f))).state,"acknowledged");
  assert.equal(test.readTestSnapshot().revision,3);
  assert.equal(test.readTestSnapshot().investigations[0].evidence.length,0);

  // A committed record with a lost reply is still uncertain to the caller.
  const uncertain=new ResearchWriteAttempt(
    {action:"create",title:"Committed but unconfirmed",question:"Will it duplicate?"},
    test.readTestSnapshot(),
    {clock,newId:()=>"12345678-1234-4234-8234-123456789ac0"});
  const unknown=await uncertain.dispatchOnce(async frame=>{
    const reply=test.dispatch(frame);
    assert.equal(reply.exitCode,0);
    throw new Error("lost acknowledgement after committed rename");
  });
  assert.equal(unknown.state,"reviewRequired");
  assert.equal(unknown.autoRetry,false);
  assert.equal(uncertain.getDraft().title,"Committed but unconfirmed");
  assert.equal(test.readTestSnapshot().revision,4);
  await assert.rejects(uncertain.dispatchOnce(async f=>test.dispatch(f)),
    /WRITE_ALREADY_ATTEMPTED/);
  assert.equal(test.readTestSnapshot().revision,4);

  const before=test.dispatchCount;
  for(const frame of [
    "",'{"action":"list"}\n','{"action":"delete","id":"case"}\n',
    '{"action":"create"}\n{"action":"create"}\n',
    '{"action":"attach","fake":true}\n',
    '{"action":"create","injection":true}\n',
    "x".repeat(9000)+"\n"
  ]) {
    const reply=test.dispatch(frame);
    assert.equal(reply.exitCode,1);
    assert.equal(reply.stdout,"");
    assert.equal(reply.stderr,"DISPOSABLE_TEST_REFUSAL");
  }
  assert.equal(test.dispatchCount,before);
  assert.equal(test.readTestSnapshot().revision,4);
  assert.equal(fs.existsSync(process.env.XDG_DATA_HOME),false,
    "The disposable dispatcher must not create XDG user storage");
  console.log("Finance Research M4b-T2 disposable dispatcher: PASS");
} finally {
  test.destroy();
  assert.equal(test.closed,true);
  assert.equal(test.dispatch('{"action":"list"}\n').exitCode,1);
  if(priorHome===undefined) delete process.env.XDG_DATA_HOME;
  else process.env.XDG_DATA_HOME=priorHome;
  fs.rmSync(probe,{recursive:true,force:true});
}
