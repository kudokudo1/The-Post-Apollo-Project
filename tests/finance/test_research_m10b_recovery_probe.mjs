import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { run } from "../../scripts/finance/research_investigation_store.mjs";
import {
  inspectResearchRecovery, RESULT_PREFIX, ERROR_PREFIX
} from "../../scripts/finance/research_investigation_recovery_probe.mjs";

// M10b tests use only a random, permission-restricted temporary directory.
const root=fs.mkdtempSync(path.join(os.tmpdir(),"finance-research-m10b-"));
fs.chmodSync(root,0o700);
const stamp="2026-11-25T13:00:00.000Z";
const command=(revision,id)=>({action:"create",expectedRevision:revision,
  id,title:"Private Research "+id,
  question:"Confidential test note must never appear in recovery report",
  timestamp:stamp});
const checkPrivacy=report=>{
  const raw=JSON.stringify(report);
  assert.equal(report.readOnly,true);
  assert.equal(report.canUnlock,false);
  assert.equal(report.canRetry,false);
  assert.equal(report.changesMade,false);
  assert.ok(!raw.includes("Confidential test note"));
  assert.ok(!raw.includes("Private Research"));
  assert.ok(!raw.includes(root));
  assert.equal(Object.hasOwn(report,"unlockToken"),false);
};
function assertUnchanged(dir, before) {
  assert.equal(fs.readFileSync(
    path.join(dir,"investigations.json"),"utf8"),before);
}
try {
  const emptyDir=path.join(root,"does-not-exist");
  const absent=inspectResearchRecovery(emptyDir);
  checkPrivacy(absent);
  assert.equal(absent.status,"NO_STORE");
  assert.equal(absent.reason,"DIRECTORY_ABSENT");
  assert.equal(absent.store.revision,0);
  assert.equal(fs.existsSync(emptyDir),false);
  console.log("M10B_CHECK // ABSENT_STORE_INSPECTED_WITHOUT_CREATING_FILES");

  const dir=path.join(root,"research");
  const doc=run(command(0,"one"),dir);
  assert.equal(doc.revision,1);
  const stored=fs.readFileSync(path.join(dir,"investigations.json"),"utf8");
  const normal=inspectResearchRecovery(dir);
  checkPrivacy(normal);
  assert.equal(normal.status,"NO_RECOVERY_LOCK");
  assert.equal(normal.reason,"NO_LOCK_OBSERVED");
  assert.equal(normal.store.state,"READABLE");
  assert.equal(normal.store.revision,1);
  assert.equal(normal.store.caseCount,1);
  assert.equal(normal.store.evidenceCount,0);
  assert.match(normal.store.fingerprint,/^[0-9a-f]{64}$/);
  assert.equal(normal.lock.state,"ABSENT");
  assert.equal(normal.tempCount,0);
  assert.equal(normal.unexpectedCount,0);
  assert.deepEqual(inspectResearchRecovery(dir),normal);
  assertUnchanged(dir,stored);
  console.log("M10B_CHECK // READ_ONLY_FINGERPRINT_STABLE");

  const lock=path.join(dir,"investigations.lock");
  fs.writeFileSync(lock,"",{flag:"wx",mode:0o600});
  const locked=inspectResearchRecovery(dir);
  checkPrivacy(locked);
  assert.equal(locked.status,"REVIEW_REQUIRED");
  assert.equal(locked.reason,"LOCK_PRESENT_OUTCOME_UNKNOWN");
  assert.equal(locked.store.revision,1);
  assert.equal(locked.store.fingerprint,normal.store.fingerprint);
  assert.equal(locked.lock.state,"PRESENT");
  assert.match(locked.lock.fingerprint,/^[0-9a-f]{64}$/);
  assert.equal(fs.existsSync(lock),true,"Never unlink a recovery lock");
  assertUnchanged(dir,stored);
  console.log("M10B_CHECK // LOCKED_STORE_REQUIRES_REVIEW_NO_RETRY");

  // Corruption is not silently treated as an empty case list. The lock
  // remains preserved while the reader reports the existing problem.
  fs.writeFileSync(path.join(dir,"investigations.json"),"{bad",
    {mode:0o600});
  const corrupt=inspectResearchRecovery(dir);
  checkPrivacy(corrupt);
  assert.equal(corrupt.status,"UNAVAILABLE");
  assert.equal(corrupt.reason,"CORRUPT_STORE");
  assert.equal(corrupt.store.state,"REFUSED");
  assert.equal(corrupt.store.revision,null);
  assert.equal(corrupt.lock.state,"PRESENT");
  assert.equal(fs.existsSync(lock),true);
  assert.equal(fs.readFileSync(path.join(dir,"investigations.json"),"utf8"),"{bad");
  fs.writeFileSync(path.join(dir,"investigations.json"),stored,{mode:0o600});
  console.log("M10B_CHECK // CORRUPTION_NEVER_WIPED");

  fs.unlinkSync(lock); // Test fixture cleanup ONLY, not a recovery operation.
  const temp=path.join(dir,".00000000-0000-4000-8000-000000000001.tmp");
  fs.writeFileSync(temp,"ABANDONED TEST TEMP",{mode:0o600});
  const orphan=inspectResearchRecovery(dir);
  checkPrivacy(orphan);
  assert.equal(orphan.status,"REVIEW_REQUIRED");
  assert.equal(orphan.reason,"UNEXPECTED_RESEARCH_FILES");
  assert.equal(orphan.tempCount,1);
  assert.equal(fs.existsSync(temp),true);
  fs.unlinkSync(temp);
  const unexpected=path.join(dir,"unexpected.txt");
  fs.writeFileSync(unexpected,"DISPOSABLE",{mode:0o600});
  const odd=inspectResearchRecovery(dir);
  assert.equal(odd.status,"REVIEW_REQUIRED");
  assert.equal(odd.unexpectedCount,1);
  assert.equal(fs.existsSync(unexpected),true);
  fs.unlinkSync(unexpected);
  assertUnchanged(dir,stored);
  console.log("M10B_CHECK // ORPHANS_AND_UNEXPECTED_FILES_NEVER_CLEANED");

  const outside=path.join(root,"outside");
  fs.writeFileSync(outside,"OUTSIDE",{mode:0o600});
  fs.symlinkSync(outside,lock);
  const unsafeLock=inspectResearchRecovery(dir);
  checkPrivacy(unsafeLock);
  assert.equal(unsafeLock.status,"UNAVAILABLE");
  assert.equal(unsafeLock.reason,"LOCK_UNSAFE_OR_UNAVAILABLE");
  assert.equal(unsafeLock.lock.state,"UNSAFE");
  assert.equal(fs.readFileSync(outside,"utf8"),"OUTSIDE");
  fs.unlinkSync(lock);
  assertUnchanged(dir,stored);
  console.log("M10B_CHECK // SYMLINKED_LOCK_NOT_FOLLOWED");

  const redirect=path.join(root,"redirect");
  fs.symlinkSync(dir,redirect,"dir");
  const reject=inspectResearchRecovery(path.join(redirect,"research"));
  checkPrivacy(reject);
  assert.equal(reject.status,"UNAVAILABLE");
  assert.equal(reject.reason,"UNSAFE_DIRECTORY");
  assert.equal(reject.lock.state,"UNKNOWN");
  assert.equal(fs.existsSync(path.join(dir,"research")),false);
  console.log("M10B_CHECK // UNSAFE_ANCESTOR_NOT_TRAVERSED");

  const busy=path.join(root,"busy");
  fs.mkdirSync(busy,{mode:0o700});
  for(let i=0;i<130;i++)
    fs.writeFileSync(path.join(busy,"item-"+i),"",{mode:0o600});
  const large=inspectResearchRecovery(busy);
  checkPrivacy(large);
  assert.equal(large.status,"UNAVAILABLE");
  assert.equal(large.reason,"ENTRY_LIMIT");
  assert.equal(large.tempCount,null);
  console.log("M10B_CHECK // DIRECTORY_INVENTORY_BOUNDED");

  // The executable has no unlock flag or writable action. It can only
  // inspect default XDG Research storage and must not emit note text.
  const script=fileURLToPath(new URL(
    "../../scripts/finance/research_investigation_recovery_probe.mjs",import.meta.url));
  const xdg=path.join(root,"xdg");
  const liveDir=path.join(xdg,"post-apollo","finance","research-investigations");
  run(command(0,"cli"),liveDir);
  const env={...process.env,XDG_DATA_HOME:xdg};
  const output=spawnSync(process.execPath,[script],{
    env,encoding:"utf8",timeout:3000
  });
  assert.equal(output.status,0,output.stderr);
  assert.equal(output.stderr,"");
  assert.ok(output.stdout.startsWith(RESULT_PREFIX));
  assert.equal(output.stdout.split("\n").length,2);
  const cli=JSON.parse(output.stdout.slice(RESULT_PREFIX.length));
  checkPrivacy(cli);
  assert.equal(cli.store.revision,1);
  assert.equal(cli.status,"NO_RECOVERY_LOCK");
  const blocked=spawnSync(process.execPath,[script,"--unlock"],{
    env,encoding:"utf8",timeout:3000
  });
  assert.equal(blocked.status,1);
  assert.equal(blocked.stdout,"");
  assert.equal(blocked.stderr,ERROR_PREFIX+"INSPECTION_UNAVAILABLE\n");
  assert.equal(run({action:"list"},liveDir).revision,1);
  console.log("M10B_CHECK // CLI_READ_ONLY_AND_UNLOCK_ARGUMENT_REFUSED");

  console.log("Finance Research M10b recovery inspection, zero writes: PASS");
} finally {
  fs.rmSync(root,{recursive:true,force:true});
}
