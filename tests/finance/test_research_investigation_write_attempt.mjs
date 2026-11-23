import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { ResearchWriteAttempt } from "../../scripts/finance/research_investigation_write_attempt.mjs";
import { run } from "../../scripts/finance/research_investigation_store.mjs";

const stamp="2026-11-23T15:00:00.000Z";
const uuid="12345678-1234-4234-8234-123456789abc";
const options={clock:()=>stamp,newId:()=>uuid};
const intent={action:"create",title:"Public research",question:"What changed?"};
const empty={schemaVersion:1,revision:0,investigations:[]};
const root=fs.mkdtempSync(path.join(os.tmpdir(),"research-m4b-once-"));
const dir=path.join(root,"isolated-research");

try {
  let calls=0;
  const attempt=new ResearchWriteAttempt(intent,empty,options);
  assert.equal(attempt.state,"staged");
  assert.equal(attempt.wasDispatched,false);
  assert.equal(attempt.canRetry,false);
  assert.deepEqual(attempt.getDraft(),intent);
  const untrustedDraft=attempt.getDraft();
  untrustedDraft.title="mutated copy";
  assert.equal(attempt.getDraft().title,intent.title);
  assert.equal(attempt.getVerifiedDocument(),null);
  const result=await attempt.dispatchOnce(async frame=>{
    calls++;
    const command=JSON.parse(frame);
    assert.equal(command.action,"create");
    const doc=run(command,dir); // Disposable private directory only.
    return {exitCode:0,stdout:"FINANCE_RESEARCH_STORE_RESULT "+JSON.stringify(doc)+"\n",stderr:""};
  });
  assert.deepEqual(result,{state:"acknowledged",revision:1});
  assert.equal(calls,1);
  assert.equal(attempt.getDraft(),null);
  assert.equal(attempt.getVerifiedDocument().investigations.length,1);
  const mutated=attempt.getVerifiedDocument();
  mutated.investigations[0].title="corrupted";
  assert.equal(attempt.getVerifiedDocument().investigations[0].title,intent.title);
  await assert.rejects(attempt.dispatchOnce(async()=>{calls++;}),/WRITE_ALREADY_ATTEMPTED/);
  assert.equal(calls,1);
  assert.equal(run({action:"list"},dir).revision,1);

  // An unknown exit can mean M2 already committed: require manual recovery,
  // preserve editor text and forbid implicit repetition.
  const uncertain=new ResearchWriteAttempt({action:"create",title:"Second",question:"Was it saved?"},
    run({action:"list"},dir),{clock:()=>stamp,newId:()=>"12345678-1234-4234-8234-123456789abd"});
  const unresolved=await uncertain.dispatchOnce(async frame=>{
    calls++;
    run(JSON.parse(frame),dir);
    throw new Error("worker crashed after atomic rename");
  });
  assert.deepEqual(unresolved,{state:"reviewRequired",requiresReload:true,autoRetry:false});
  assert.equal(uncertain.state,"reviewRequired");
  assert.equal(uncertain.getDraft().title,"Second");
  assert.equal(uncertain.getVerifiedDocument(),null);
  assert.equal(run({action:"list"},dir).revision,2);
  await assert.rejects(uncertain.dispatchOnce(async()=>{calls++;}),/WRITE_ALREADY_ATTEMPTED/);
  assert.equal(calls,2);

  const badAck=new ResearchWriteAttempt({action:"create",title:"Third",question:"Review response"},
    run({action:"list"},dir),{clock:()=>stamp,newId:()=>"12345678-1234-4234-8234-123456789abe"});
  const bad=await badAck.dispatchOnce(async()=>{
    calls++;
    return {exitCode:0,stdout:"FINANCE_RESEARCH_STORE_RESULT {}\n",stderr:""};
  });
  assert.equal(bad.state,"reviewRequired");
  assert.equal(badAck.getDraft().title,"Third");
  assert.equal(run({action:"list"},dir).revision,2);

  for(const reply of [
    {exitCode:1,stdout:"",stderr:"refusal"},
    {exitCode:0,stdout:"",stderr:""},
    {exitCode:0,stdout:"FINANCE_RESEARCH_STORE_RESULT {}\n",stderr:"unexpected log"},
    {exitCode:0,stdout:"",stderr:"",extra:1}
  ]) {
    const staged=new ResearchWriteAttempt(intent,empty,options);
    const response=await staged.dispatchOnce(async()=>reply);
    assert.equal(response.state,"reviewRequired");
    assert.equal(staged.getDraft().title,intent.title);
    assert.equal(staged.canRetry,false);
  }

  // A pending async callback must not allow a second submission.
  let release;
  let waiting=0;
  const hold=new ResearchWriteAttempt(intent,empty,options);
  const pending=hold.dispatchOnce(async()=>{
    waiting++;
    return new Promise(resolve=>{release=resolve;});
  });
  assert.equal(hold.state,"inFlight");
  await assert.rejects(hold.dispatchOnce(async()=>{waiting++;}),/WRITE_ALREADY_ATTEMPTED/);
  assert.equal(waiting,1);
  release({exitCode:1,stdout:"",stderr:"worker unavailable"});
  assert.equal((await pending).state,"reviewRequired");

  const unsent=new ResearchWriteAttempt(intent,empty,options);
  await assert.rejects(unsent.dispatchOnce(null),/DISPATCH_REQUIRED/);
  assert.equal(unsent.state,"staged");
  assert.equal(unsent.wasDispatched,false);
  assert.throws(()=>new ResearchWriteAttempt({action:"delete",id:"x"},empty,options));
  console.log("Finance Research M4b-T1 one-shot transport: PASS");
} finally {
  fs.rmSync(root,{recursive:true,force:true});
}
