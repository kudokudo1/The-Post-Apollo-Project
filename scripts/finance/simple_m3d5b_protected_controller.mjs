// FinanceW Simple M3d5b1 // NON-ACTIVATED protected Save controller.
// This is a pre-dispatch state machine. It DOES NOT run a writer, mutate
// Actual, create a permit, persist a transaction or release a write command.
// Future actuation requires a new, independently reviewed implementation.
// Production financial writes: HARD HOLD.
import {createHash,randomBytes,timingSafeEqual} from "node:crypto";
import {homedir} from "node:os";
import {join} from "node:path";
import {readdir} from "node:fs/promises";
import {openTrustedDirectory,readTrustedPrivateFile,readPrivateEntry}
  from "./categorized_expense_file_trust.mjs";
import {prepareOfflineCategorizedReview,recheckOfflineCategorizedReview}
  from "./simple_m3d2_offline_review.mjs";
import {validateCategorizedExpenseCommand}
  from "./categorized_expense_guard.mjs";

const WRITER_URL="http://127.0.0.1:5006";
const KEY=/^[0-9a-f]{64}$/;
const SYNC=/^[A-Za-z0-9-]{8,80}$/;
const fail=code=>({ok:false,canSave:false,writeAllowed:false,reason:code});
function matchingKey(sourceKey,serverURL,syncId){
  if(!KEY.test(sourceKey) || serverURL!==WRITER_URL || !SYNC.test(syncId))
    return false;
  const computed=createHash("sha256")
    .update(serverURL+"\0"+syncId).digest();
  return timingSafeEqual(computed,Buffer.from(sourceKey,"hex"));
}

// The same trusted config files that the reviewed M3b writer consumes.
// This check establishes source-key CONSISTENCY, not fresh Actual authority.
// No password, transaction, raw sync ID or private path is returned.
export async function inspectM3d5bSourceBinding({
  sourceKey,configDir=join(homedir(),".config","financew")
}={}) {
  let serverURL,syncId;
  try{
    serverURL=await readTrustedPrivateFile(join(configDir,"actual-server-url"));
    syncId=await readTrustedPrivateFile(join(configDir,"actual-sync-id"));
  }catch{return fail("source-files-untrusted-or-unavailable");}
  if(serverURL!==WRITER_URL)
    return fail("read-write-endpoint-not-aligned");
  if(!SYNC.test(syncId))
    return fail("invalid-protected-sync-id");
  if(!matchingKey(sourceKey,serverURL,syncId))
    return fail("read-write-source-mismatch");
  return {ok:true,canSave:false,writeAllowed:false,
    reason:"source-key-matches-protected-writer",sourceLabel:"loopback-5006"};
}

// Best-effort read-only precheck. The M3b writer MUST independently acquire
// the global exclusive lock and re-check journals under that lock immediately
// before Actual mutation. This observation alone NEVER authorizes a write.
export async function inspectM3d5bSharedRecovery({
  journalDir=join(homedir(),".local","state","financew","operations")
}={}) {
  let dir;
  try{dir=await openTrustedDirectory(journalDir,{privateLeaf:true});}
  catch(error){
    if(error?.code==="ENOENT")
      return {ok:true,canSave:false,writeAllowed:false,
        reason:"no-prior-journal-directory"};
    return fail("journal-directory-untrusted");
  }
  try{
    const names=await readdir("/proc/self/fd/"+dir.fd);
    for(const name of names){
      if(name===".write-lock")return fail("write-lock-present");
      if(!name.endsWith(".json"))return fail("unrecognized-journal-entry");
      let entry;
      try{entry=JSON.parse(await readPrivateEntry(dir,name));}
      catch{return fail("untrusted-or-unresolved-journal");}
      if(!entry || entry.status!=="committed")
        return fail("unresolved-finance-operation");
    }
    return {ok:true,canSave:false,writeAllowed:false,
      reason:"no-unresolved-operation-observed"};
  }catch{return fail("journal-read-failed");}
  finally{await dir.close();}
}

function snapshotView(view){
  return {snapshot:view?.snapshot,candidate:view?.candidate,
    proposal:view?.proposal,selectedCategoryId:view?.selectedCategoryId};
}
function guardOffline(view,previous=null){
  const current=prepareOfflineCategorizedReview(snapshotView(view));
  if(!current.ok || current.canSave!==false || current.writeAllowed!==false)
    return fail(current.reason || "offline-review-invalid");
  if(previous){
    const checked=recheckOfflineCategorizedReview({
      previous,...snapshotView(view)});
    if(!checked.ok || checked.canSave!==false || checked.writeAllowed!==false)
      return fail(checked.reason||"review-changed");
  }
  return current;
}

// Each instance has exactly ONE confirmation opportunity. No "retry" or
// "resume" can silently issue another operation identity. A newly started
// process is NOT durable recovery; the M3b journal remains authoritative.
// Inputs are references only until confirmation; we always recompute from
// fresh caller-supplied values, including in-place changes to nested objects.
export function createM3d5bNonActivatedController({
  configDir=join(homedir(),".config","financew"),
  journalDir=join(homedir(),".local","state","financew","operations")
}={}) {
  let phase="idle",prior=null,challenge="",epoch=0;
  const status=()=>({phase,canSave:false,writeAllowed:false,
    productionDispatch:"HARD-HOLD"});
  async function verifyReadiness(view){
    const source=await inspectM3d5bSourceBinding({
      sourceKey:view?.snapshot?.sourceKey,configDir});
    if(!source.ok)return source;
    const recovery=await inspectM3d5bSharedRecovery({journalDir});
    if(!recovery.ok)return recovery;
    return {ok:true};
  }
  async function stage(view){
    if(phase!=="idle")return fail("controller-not-idle");
    phase="checking";
    const ticket=++epoch;
    const checked=guardOffline(view);
    if(!checked.ok){phase="refused";return checked;}
    const ready=await verifyReadiness(view);
    if(ticket!==epoch)return fail("controller-invalidated");
    if(!ready.ok){phase="refused";return ready;}
    const refreshed=guardOffline(view,checked);
    if(!refreshed.ok){phase="refused";return refreshed;}
    prior=checked;
    challenge="CONFIRM CATEGORY "+randomBytes(8).toString("hex");
    phase="awaiting-explicit-confirmation";
    return {ok:true,canSave:false,writeAllowed:false,
      phase,confirmationPrompt:challenge,reason:"reviewed-but-not-authorized"};
  }
  async function confirm({confirmationText,current}={}){
    if(phase!=="awaiting-explicit-confirmation" || !prior)
      return fail("confirmation-not-armed");
    // Consume confirmation before any awaits so concurrent calls cannot
    // mint two operation IDs. Even a wrong/failed attempt cannot be retried.
    phase="checking-confirmation";
    const ticket=++epoch;
    const expected=challenge;
    challenge="";
    if(confirmationText!==expected){
      phase="refused";prior=null;
      return fail("confirmation-mismatch");
    }
    const checked=guardOffline(current,prior);
    if(!checked.ok){phase="refused";prior=null;return checked;}
    const ready=await verifyReadiness(current);
    if(ticket!==epoch)return fail("controller-invalidated");
    if(!ready.ok){phase="refused";prior=null;return ready;}
    const second=guardOffline(current,prior);
    if(!second.ok){phase="refused";prior=null;return second;}
    // Generate the only operation identity using CSPRNG, never QML Math.random.
    // Validate the EXACT M3b schema in memory, then irreversibly discard it.
    // An executable command MUST NOT escape this non-activated controller.
    const requestId=randomBytes(16).toString("hex");
    let command;
    try{command=validateCategorizedExpenseCommand({
      action:"create-categorized-expense",requestId,...second.previewFields
    });}
    catch{phase="refused";prior=null;return fail("invalid-command-shape");}
    const fingerprint=createHash("sha256")
      .update(JSON.stringify(command)).digest("hex");
    prior=null;
    phase="confirmed-but-dispatch-disabled";
    return {ok:true,canSave:false,writeAllowed:false,phase,
      reason:"request-identity-issued-and-discarded",fingerprint};
  }
  function cancel(){
    ++epoch;
    challenge="";prior=null;phase="canceled";
    return {ok:true,canSave:false,writeAllowed:false,phase};
  }
  function dispatch(){
    // Even a fully confirmed fake or real review cannot turn on an Actual
    // writer. This module does not import any Process, spawn, API or permit.
    return fail("production-dispatch-hard-hold");
  }
  return Object.freeze({stage,confirm,cancel,status,dispatch});
}
