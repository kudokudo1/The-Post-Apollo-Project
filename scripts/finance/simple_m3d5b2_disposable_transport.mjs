// FinanceW Simple M3d5b2 // DISPOSABLE-ONLY DURABLE TRANSPORT CUSTODY.
// This is an isolated protocol fixture, NEVER a production transport.
// It never launches the M3b writer, reads Actual, creates a finance permit,
// opens the real FinanceW operations journal, or sends any financial command.
// The private fixture reservation ledger survives separate Node processes.
import {open,readdir,rm} from "node:fs/promises";
import {tmpdir} from "node:os";
import {basename,dirname,join,resolve} from "node:path";
import {createHash} from "node:crypto";
import {openTrustedDirectory,dirEntryPath,readPrivateEntry}
  from "./categorized_expense_file_trust.mjs";
import {validateCategorizedExpenseCommand}
  from "./categorized_expense_guard.mjs";

const namePattern=/^financew-m3d5b2-fixture-[a-zA-Z0-9_-]{6,64}$/;
const requestPattern=/^[0-9a-f]{32}$/;
const shaPattern=/^[0-9a-f]{64}$/;
const fail=reason=>({ok:false,canSave:false,writeAllowed:false,
  dispatched:false,reason});
function digest(obj){
  return createHash("sha256").update(JSON.stringify(obj)).digest("hex");
}
function intentHash(command){
  // No arbitrary object-key order can change the idempotency fingerprint.
  return digest(Object.keys(command).filter(k=>k!=="requestId").sort()
    .map(k=>[k,command[k]]));
}
function allowedFixture(root){
  return process.env.FINANCEW_DISPOSABLE_TEST==="yes"
    && typeof root==="string" && resolve(root)===root
    && dirname(root)===resolve(tmpdir())
    && namePattern.test(basename(root))
    && process.env.HOME===root;
}

// This function verifies M3b's single-bounded-JSON-line stdin transport
// grammar. It NEVER sends the frame and NEVER returns executable fields.
export function inspectM3d5b2StdinFrame(frame) {
  if(typeof frame!=="string" || Buffer.byteLength(frame,"utf8")>4096
      || !frame.endsWith("\n")
      || frame.indexOf("\n")!==frame.length-1 || frame.includes("\r"))
    return fail("invalid-stdin-frame");
  let command;
  try{
    command=validateCategorizedExpenseCommand(
      JSON.parse(frame.slice(0,-1)));
  }catch{return fail("invalid-command-shape");}
  return {ok:true,canSave:false,writeAllowed:false,dispatched:false,
    reason:"frame-compatible-no-dispatch",frameHash:digest(command)};
}

// Parse fixed M3b result grammar without trusting a successful exit status
// alone. Unknown/multiple statuses are UNCERTAIN, never implicit success.
export function inspectM3d5b2WriterOutcome({stdout="",exitCode=null}={}) {
  if(typeof stdout!=="string" || Buffer.byteLength(stdout,"utf8")>2048
      || stdout.includes("\r"))return {state:"uncertain",canRetry:false};
  const lines=stdout.split("\n").filter(Boolean);
  if(lines.length!==1)return {state:"uncertain",canRetry:false};
  const m=/^FINANCEW_CATEGORIZED_EXPENSE_RESULT (committed|uncertain|blocked:[a-z0-9-]+)$/
    .exec(lines[0]);
  if(!m)return {state:"uncertain",canRetry:false};
  if(m[1]==="committed" && exitCode===0)
    return {state:"committed",canRetry:false};
  if(m[1].startsWith("blocked:") && exitCode!==0 && exitCode!==null)
    return {state:"blocked",canRetry:false,reason:m[1].slice(8)};
  return {state:"uncertain",canRetry:false};
}

// Strong, deliberate test-only gate. Root must be a *private* top-level
// /tmp/financew-m3d5b2-fixture-* directory AND exactly the child's HOME.
// A matching environment variable alone is insufficient. Real finance
// journal directories and production worktrees can never be selected.
export async function reserveM3d5b2DisposableIntent({sandboxRoot,command}={}){
  if(!allowedFixture(sandboxRoot))return fail("disposable-fixture-required");
  let approved;
  try{approved=validateCategorizedExpenseCommand(command);}
  catch{return fail("invalid-command-shape");}
  let anchor;
  try{anchor=await openTrustedDirectory(sandboxRoot,{privateLeaf:true});}
  catch{return fail("untrusted-fixture-root");}
  await anchor.close();

  let dir;
  try{dir=await openTrustedDirectory(join(sandboxRoot,"reservations"),{
    create:true,privateLeaf:true
  });}
  catch{return fail("untrusted-reservation-directory");}
  let lock=null,releaseLock=false;
  const lockPath=dirEntryPath(dir,".reservation-lock");
  try {
    try{
      lock=await open(lockPath,"wx",0o600);
      await lock.sync();
      await dir.sync();
    }catch{return fail("reservation-locked-recovery-required");}
    const names=await readdir("/proc/self/fd/"+dir.fd);
    const fingerprint=intentHash(approved);
    for(const name of names){
      if(name===".reservation-lock")continue;
      if(!/^intent-[0-9a-f]{64}\.json$/.test(name))
        return fail("unrecognized-reservation-entry");
      let prior;
      try{prior=JSON.parse(await readPrivateEntry(dir,name));}
      catch{return fail("untrusted-reservation-entry");}
      if(!prior || prior.version!==1 || prior.state!=="sealed-dry-run"
          ||!requestPattern.test(prior.requestId)
          ||!shaPattern.test(prior.fingerprint)
          ||name!=="intent-"+prior.fingerprint+".json")
        return fail("untrusted-reservation-entry");
      if(prior.requestId===approved.requestId || prior.fingerprint===fingerprint){
        releaseLock=true; // Known collision; no new bytes written.
        return fail("replay-or-duplicate-intent");
      }
    }
    // The intent record stores no payee, amount, budget, secret, or
    // executable command. Creation is exclusive and fsynced BEFORE ack.
    const name="intent-"+fingerprint+".json";
    let record;
    try{record=await open(dirEntryPath(dir,name),"wx",0o600);}
    catch{return fail("reservation-collision-recovery-required");}
    try{
      await record.writeFile(JSON.stringify({
        version:1,state:"sealed-dry-run",requestId:approved.requestId,
        fingerprint
      })+"\n");
      await record.sync();
      await dir.sync();
    }catch{return fail("reservation-durability-uncertain");}
    finally{await record.close();}
    releaseLock=true;
    return {ok:true,canSave:false,writeAllowed:false,dispatched:false,
      state:"sealed-dry-run",reason:"durably-reserved-disposable-only",
      fingerprint};
  }finally{
    if(lock)await lock.close();
    // Unknown failure keeps the lock as a recovery marker: no auto cleanup.
    if(lock && releaseLock){
      await rm(lockPath);
      await dir.sync();
    }
    await dir.close();
  }
}
