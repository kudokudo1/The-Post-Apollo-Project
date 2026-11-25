import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {spawnSync} from "node:child_process";
import {pathToFileURL,fileURLToPath} from "node:url";
import {run,Refusal} from "../../scripts/finance/research_investigation_store.mjs";
import {inspectResearchRecovery} from "../../scripts/finance/research_investigation_recovery_probe.mjs";
import {
  prepareWriteIntent,encodeWriteIntent,parseWriteIntent,
  compareObservedWriteIntent,documentFingerprint,MAX_INTENT_BYTES
} from "../../scripts/finance/research_investigation_write_intent.mjs";

// This native test creates only randomized private disposable stores.
const root=fs.mkdtempSync(path.join(os.tmpdir(),"finance-research-m10c-"));
fs.chmodSync(root,0o700);
const timestamp="2026-11-25T14:00:00.000Z";
const cmd=(revision,id)=>({action:"create",expectedRevision:revision,
  id,title:"TEST PRIVATE "+id,
  question:"This private field must not appear in diagnostic output",timestamp});
const refusal=code=>e=>e instanceof Refusal && e.message===code;
const withPatched=(name,fn,body)=>{
  const prev=fs[name];
  fs[name]=(...args)=>fn(prev,args);
  try{return body();}finally{fs[name]=prev;}
};
const locked=(dir)=>{
  const name=path.join(dir,"investigations.lock");
  assert.ok(fs.existsSync(name),"lost crash recovery lock");
  assert.equal(fs.lstatSync(name).mode&0o077,0);
  assert.throws(()=>run(cmd(1,"not-retried"),dir),refusal("WRITE_BUSY"));
};
const privateReport=report=>{
  const raw=JSON.stringify(report);
  for(const needle of ["TEST PRIVATE","This private field",root])
    assert.ok(!raw.includes(needle),"private Research data leaked");
  assert.equal(report.readOnly,true);
  assert.equal(report.canRetry,false);
  assert.equal(report.canUnlock,false);
  assert.equal(report.changesMade,false);
};
try {
  const before={schemaVersion:1,revision:0,investigations:[]};
  const after={schemaVersion:1,revision:1,investigations:[{
    schemaVersion:1,id:"case-1",title:"TEST PRIVATE one",
    question:"This private field must not appear in diagnostic output",
    createdAt:timestamp,updatedAt:timestamp,evidence:[]
  }]};
  const proposal=prepareWriteIntent(cmd(0,"case-1"),before,after,
    ()=> "00000000-0000-4000-8000-000000000001");
  assert.equal(proposal.action,"create");
  assert.equal(proposal.priorRevision,0);
  assert.equal(proposal.proposedRevision,1);
  assert.equal(proposal.priorFingerprint,documentFingerprint(before));
  assert.equal(proposal.proposedFingerprint,documentFingerprint(after));
  const frame=encodeWriteIntent(proposal);
  assert.ok(Buffer.byteLength(frame,"utf8")<=MAX_INTENT_BYTES);
  assert.deepEqual(parseWriteIntent(frame),proposal);
  assert.equal(compareObservedWriteIntent(proposal,before),
    "PRIOR_MATCH_OBSERVED");
  assert.equal(compareObservedWriteIntent(proposal,after),
    "PROPOSED_MATCH_OBSERVED");
  assert.throws(()=>parseWriteIntent(frame+"\n"),/INVALID_RESEARCH_INTENT/);
  assert.throws(()=>parseWriteIntent(frame.replace("\n","\r\n")),/INVALID_RESEARCH_INTENT/);
  assert.throws(()=>parseWriteIntent(JSON.stringify({...proposal,extra:"x"})+"\n"),
    /INVALID_RESEARCH_INTENT/);
  assert.throws(()=>parseWriteIntent(frame.slice(0,-2)),/INVALID_RESEARCH_INTENT/);
  assert.throws(()=>prepareWriteIntent(cmd(1,"case-1"),before,after),
    /INVALID_RESEARCH_INTENT/);
  assert.ok(!frame.includes("TEST PRIVATE"));
  console.log("M10C_CHECK // PURE_INTENT_UUID_HASHES_AND_STRICT_FRAME");

  // Normal write has no recovery lock after a durable commit. The intent
  // is internal to the transaction, not an audit log of successful saves.
  const normal=path.join(root,"normal");
  assert.equal(run(cmd(0,"normal"),normal).revision,1);
  const accepted=inspectResearchRecovery(normal);
  privateReport(accepted);
  assert.equal(accepted.status,"NO_RECOVERY_LOCK");
  assert.equal(accepted.lock.state,"ABSENT");
  assert.equal(accepted.intent.state,"NONE");
  assert.equal(fs.existsSync(path.join(normal,"investigations.lock")),false);
  console.log("M10C_CHECK // SUCCESS_RELEASES_LOCK_NO_FAKE_RECEIPT");

  // A failed directory fsync after rename leaves a readable new snapshot
  // AND a durable record of exactly what the writer proposed. Comparison
  // is evidence only, never authorization to release the recovery lock.
  const post=path.join(root,"after-rename");
  let directoriesSynced=0;
  assert.throws(()=>withPatched("fsyncSync",(real,args)=>{
    if(fs.fstatSync(args[0]).isDirectory()
        && ++directoriesSynced===2)
      throw new Error("SYNTHETIC_DIR_FSYNC_FAILURE");
    return real.apply(fs,args);
  },()=>run(cmd(0,"after"),post)),refusal("COMMIT_OUTCOME_UNKNOWN"));
  locked(post);
  const observedPost=inspectResearchRecovery(post);
  privateReport(observedPost);
  assert.equal(observedPost.status,"REVIEW_REQUIRED");
  assert.equal(observedPost.reason,"LOCK_PRESENT_OUTCOME_UNKNOWN");
  assert.equal(observedPost.intent.state,"VALID");
  assert.equal(observedPost.intent.action,"create");
  assert.equal(observedPost.intent.priorRevision,0);
  assert.equal(observedPost.intent.proposedRevision,1);
  assert.equal(observedPost.intent.comparison,"PROPOSED_MATCH_OBSERVED");
  assert.match(observedPost.intent.operationId,
    /^[a-f0-9]{8}-[a-f0-9]{4}-[1-8][a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/i);
  assert.equal(observedPost.store.fingerprint,
    observedPost.intent.proposedFingerprint);
  assert.equal(run({action:"list"},post).revision,1);
  console.log("M10C_CHECK // POST_RENAME_INTENT_MATCH_STILL_HOLDS");

  // In a failed rename, the old snapshot may still be present. It must
  // be represented as an observation, not a proved failed transaction.
  const pre=path.join(root,"failed-rename");
  assert.throws(()=>withPatched("renameSync",()=> {
    throw new Error("SYNTHETIC_UNKNOWN_RENAME");
  },()=>run(cmd(0,"before"),pre)),refusal("COMMIT_OUTCOME_UNKNOWN"));
  assert.equal(run({action:"list"},pre).revision,0);
  const observedPre=inspectResearchRecovery(pre);
  privateReport(observedPre);
  assert.equal(observedPre.status,"REVIEW_REQUIRED");
  assert.equal(observedPre.intent.state,"VALID");
  assert.equal(observedPre.intent.comparison,"PRIOR_MATCH_OBSERVED");
  assert.equal(observedPre.intent.priorRevision,0);
  assert.ok(fs.existsSync(path.join(pre,"investigations.lock")));
  assert.throws(()=>run(cmd(0,"again"),pre),refusal("WRITE_BUSY"));
  console.log("M10C_CHECK // FAILED_RENAME_INTENT_PRIOR_MATCH_STILL_HOLDS");

  // If a lock was damaged by a crash or another process, the diagnostic
  // must refuse to validate it and must not delete it.
  const damaged=path.join(root,"damaged");
  fs.mkdirSync(damaged,{mode:0o700});
  fs.writeFileSync(path.join(damaged,"investigations.lock"),'{"invalid":',
    {mode:0o600});
  const malformed=inspectResearchRecovery(damaged);
  privateReport(malformed);
  assert.equal(malformed.status,"UNAVAILABLE");
  assert.equal(malformed.reason,"INVALID_INTENT");
  assert.equal(malformed.intent.state,"INVALID");
  assert.equal(fs.readFileSync(path.join(damaged,"investigations.lock"),"utf8"),
    '{"invalid":');
  assert.throws(()=>run(cmd(0,"blocked"),damaged),refusal("WRITE_BUSY"));
  console.log("M10C_CHECK // MALFORMED_INTENT_REJECTED_PRESERVED");

  // A different observed snapshot can never be mistaken for the expected
  // pre or post state, and it cannot grant retry or unlock.
  const mismatch=path.join(root,"mismatch");
  assert.throws(()=>withPatched("renameSync",()=>{
    throw new Error("SYNTHETIC_UNKNOWN_RENAME");
  },()=>run(cmd(0,"recovery"),mismatch)),
  refusal("COMMIT_OUTCOME_UNKNOWN"));
  const replaced={schemaVersion:1,revision:1,investigations:[{
    schemaVersion:1,id:"other",title:"TEST PRIVATE changed",
    question:"This private field must not appear in diagnostic output",
    createdAt:timestamp,updatedAt:timestamp,evidence:[]
  }]};
  fs.writeFileSync(path.join(mismatch,"investigations.json"),
    JSON.stringify(replaced)+"\n",{mode:0o600});
  const wrong=inspectResearchRecovery(mismatch);
  privateReport(wrong);
  assert.equal(wrong.status,"REVIEW_REQUIRED");
  assert.equal(wrong.intent.state,"VALID");
  assert.equal(wrong.intent.comparison,"DIFFERENT_DOCUMENT");
  assert.equal(wrong.canUnlock,false);
  assert.equal(wrong.canRetry,false);
  console.log("M10C_CHECK // WRONG_DOCUMENT_CANNOT_BE_CLEARED");

  // Native crash at the exact writer replacement boundary:
  // the intent survives process death both before and after rename.
  const script=fileURLToPath(new URL(
    "../../scripts/finance/research_investigation_store.mjs",import.meta.url));
  const source=[
    'import fs from "node:fs";',
    'import {run} from '+JSON.stringify(pathToFileURL(script).href)+';',
    'const rename=fs.renameSync.bind(fs);',
    'fs.renameSync=(...args)=>{',
    '  if(process.env.FAIL_AT==="before") process.kill(process.pid,"SIGKILL");',
    '  const result=rename(...args);',
    '  if(process.env.FAIL_AT==="after") process.kill(process.pid,"SIGKILL");',
    '  return result;',
    '};',
    'run({action:"create",expectedRevision:0,id:"killed",',
    'title:"TEST PRIVATE killed",question:"This private field must not appear in diagnostic output",',
    'timestamp:"2026-11-25T14:00:00.000Z"},process.env.TARGET);'
  ].join("\n");
  for(const step of ["before","after"]) {
    const dir=path.join(root,"killed-"+step);
    const child=spawnSync(process.execPath,["--input-type=module","-e",source],{
      env:{...process.env,FAIL_AT:step,TARGET:dir},
      encoding:"utf8",timeout:5000
    });
    assert.equal(child.signal,"SIGKILL",child.stderr);
    assert.equal(child.stdout,"");
    const inspected=inspectResearchRecovery(dir);
    privateReport(inspected);
    assert.equal(inspected.status,"REVIEW_REQUIRED");
    assert.equal(inspected.intent.state,"VALID");
    assert.equal(inspected.intent.comparison,step==="before"
      ? "PRIOR_MATCH_OBSERVED" : "PROPOSED_MATCH_OBSERVED");
    assert.equal(inspected.lock.state,"PRESENT");
    assert.throws(()=>run(cmd(step==="before"?0:1,"duplicate"),dir),
      refusal("WRITE_BUSY"));
    console.log("M10C_CHECK // SIGKILL_"+step.toUpperCase()
      +"_INTENT_PRESERVED");
  }

  console.log("Finance Research M10c durable intent and no-authority comparison: PASS");
} finally {
  fs.rmSync(root,{recursive:true,force:true});
}
