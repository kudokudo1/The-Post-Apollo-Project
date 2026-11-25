// FinanceW Simple M3d5b4 // DISPOSABLE CONFIRMED-ID CUSTODY, NON-ACTIVATED.
// Not imported by FinanceW, M3b or M3d5b1. No Actual API, writer process,
// production permit, financial command transport or automatic retry.
// Only a private TEST HOME may contain the confirmed held receipts.
import {open,readdir,rm} from "node:fs/promises";
import {createHash,randomBytes} from "node:crypto";
import {tmpdir} from "node:os";
import {basename,dirname,resolve,join} from "node:path";
import {openTrustedDirectory,dirEntryPath,readPrivateEntry}
  from "./categorized_expense_file_trust.mjs";
import {prepareOfflineCategorizedReview,recheckOfflineCategorizedReview}
  from "./simple_m3d2_offline_review.mjs";
import {inspectM3d5b3SourceCompatibility}
  from "./simple_m3d5b3_bridge_contract.mjs";
import {validateCategorizedExpenseCommand}
  from "./categorized_expense_guard.mjs";

const receiptPattern=/^[0-9a-f]{32}$/;
const digestPattern=/^[0-9a-f]{64}$/;
const testRootPattern=/^financew-m3d5b4-fixture-[A-Za-z0-9_-]{6,64}$/;
const refused=reason=>Object.freeze({
  ok:false,canSave:false,writeAllowed:false,dispatched:false,
  canRetry:false,reason
});
const held=(receiptId,reason)=>Object.freeze({
  ok:true,canSave:false,writeAllowed:false,dispatched:false,
  canRetry:false,state:"confirmed-held-no-dispatch",receiptId,reason
});
const viewFields=v=>({
  snapshot:v?.snapshot,candidate:v?.candidate,proposal:v?.proposal,
  selectedCategoryId:v?.selectedCategoryId
});
const hash=command=>createHash("sha256")
  .update(JSON.stringify(command)).digest("hex");
function allowedFixture(sandboxRoot){
  return process.env.FINANCEW_DISPOSABLE_TEST==="yes"
    && typeof sandboxRoot==="string" && resolve(sandboxRoot)===sandboxRoot
    && dirname(sandboxRoot)===resolve(tmpdir())
    && testRootPattern.test(basename(sandboxRoot))
    && process.env.HOME===sandboxRoot;
}
function checkSource(view,{readerEndpoint,writerEndpoint,writerSourceKey}={}){
  return inspectM3d5b3SourceCompatibility({
    readerEndpoint,writerEndpoint,writerSourceKey,
    readerSourceKey:view?.snapshot?.sourceKey
  });
}
function checkReview(view,previousReview){
  if(!previousReview)return refused("prior-review-required");
  const review=prepareOfflineCategorizedReview(viewFields(view));
  if(!review.ok || review.canSave!==false
      ||review.writeAllowed!==false
      ||review.requiresFreshActualPreflight!==true)
    return refused(review.reason||"review-invalid");
  const rechecked=recheckOfflineCategorizedReview({
    previous:previousReview,...viewFields(view)
  });
  if(!rechecked.ok || rechecked.canSave!==false
      ||rechecked.writeAllowed!==false)
    return refused(rechecked.reason||"review-changed");
  return {ok:true,fields:review.previewFields};
}
function commandFor(requestId,fields){
  // Writer schema check is local and in-memory only. Never serialize command
  // to the UI, process stdin, a journal, logs, or a financial writer.
  return validateCategorizedExpenseCommand({
    action:"create-categorized-expense",requestId,...fields
  });
}
function receiptFilename(receiptId){return "hold-"+receiptId+".json";}
function validRecord(rec,name){
  return !!rec && typeof rec==="object" && !Array.isArray(rec)
    && Object.keys(rec).sort().join(",")===
       "digest,receiptId,requestId,state,version"
    && rec.version===1 && rec.state==="confirmed-held-no-dispatch"
    && typeof rec.receiptId==="string" && receiptPattern.test(rec.receiptId)
    && typeof rec.requestId==="string" && receiptPattern.test(rec.requestId)
    && typeof rec.digest==="string" && digestPattern.test(rec.digest)
    && receiptFilename(rec.receiptId)===name;
}
async function openFixture(sandboxRoot,{create=false}={}){
  if(!allowedFixture(sandboxRoot))return {refusal:"disposable-fixture-required"};
  let root;
  try{root=await openTrustedDirectory(sandboxRoot,{privateLeaf:true});}
  catch{return {refusal:"untrusted-disposable-root"};}
  await root.close();
  try{
    const dir=await openTrustedDirectory(join(sandboxRoot,"holds"),{
      create,privateLeaf:true
    });
    return {dir};
  }catch{return {refusal:"untrusted-disposable-custody"};}
}
async function listTrustedRecords(dir,{skipLock=false}={}){
  const names=await readdir("/proc/self/fd/"+dir.fd);
  if(names.includes(".confirmation-lock") && !skipLock)
    return {refusal:"confirmation-in-progress-or-recovery-required"};
  const records=[];
  for(const name of names){
    if(name===".confirmation-lock" && skipLock)continue;
    if(!/^hold-[0-9a-f]{32}\.json$/.test(name))
      return {refusal:"unexpected-custody-entry"};
    let rec;
    try{rec=JSON.parse(await readPrivateEntry(dir,name));}
    catch{return {refusal:"untrusted-custody-record"};}
    if(!validRecord(rec,name))return {refusal:"invalid-custody-record"};
    records.push(rec);
  }
  return {records};
}
async function sealConfirmedIntent(sandboxRoot,receiptId,requestId,digest){
  const opened=await openFixture(sandboxRoot,{create:true});
  if(opened.refusal)return refused(opened.refusal);
  const dir=opened.dir,lockPath=dirEntryPath(dir,".confirmation-lock");
  let lock=null,cleanLock=false;
  try{
    try{
      lock=await open(lockPath,"wx",0o600);
      await lock.sync();
      await dir.sync();
    }catch{return refused("confirmation-in-progress-or-recovery-required");}
    const prior=await listTrustedRecords(dir,{skipLock:true});
    if(prior.refusal)return refused(prior.refusal);
    if(prior.records.some(x=>x.receiptId===receiptId ||
                               x.requestId===requestId))
      return refused("confirmed-intent-replayed");
    // Identical financial details are not a global collision. Different
    // independently confirmed request IDs can represent real repeat buys.
    let handle=null;
    try{handle=await open(dirEntryPath(dir,receiptFilename(receiptId)),
      "wx",0o600);}
    catch{return refused("custody-collision-recovery-required");}
    try{
      await handle.writeFile(JSON.stringify({
        version:1,state:"confirmed-held-no-dispatch",
        receiptId,requestId,digest
      })+"\n");
      await handle.sync();
      await dir.sync();
    }catch{return refused("custody-durability-uncertain");}
    finally{await handle.close();}
    cleanLock=true;
    return held(receiptId,"confirmed-id-durably-held-disposable-only");
  }catch{return refused("custody-operation-uncertain");}
  finally{
    if(lock)await lock.close();
    // If the record was only partially written, preserve the lock and refuse
    // every later operation. Do not silently clean up unknown outcomes.
    if(lock && cleanLock){
      try{await rm(lockPath);await dir.sync();}
      catch{/* unreadable lock is a safe persistent recovery stop */ }
    }
    await dir.close();
  }
}

// New fixture-only controller, NOT a modification of reviewed M3d5b1.
// The receipt handle is not the internal requestId and carries no permission.
export function createM3d5b4DisposableCustodian({
  sandboxRoot,readerEndpoint,writerEndpoint,writerSourceKey
}={}){
  let phase="idle",previous=null,challenge="",receiptId="",requestId="";
  const status=()=>Object.freeze({
    phase,canSave:false,writeAllowed:false,dispatched:false,
    productionDispatch:"HARD-HOLD"
  });
  function stage({view,previousReview}={}){
    if(phase!=="idle")return refused("not-idle");
    if(!allowedFixture(sandboxRoot))return refused("disposable-fixture-required");
    const checked=checkReview(view,previousReview);
    if(!checked.ok)return checked;
    const source=checkSource(view,{readerEndpoint,writerEndpoint,writerSourceKey});
    if(!source.ok)return refused(source.reason);
    // Generate both identities BEFORE confirmation. UI sees ONLY the
    // independent receipt handle, allowing read-only recovery after ACK loss.
    receiptId=randomBytes(16).toString("hex");
    requestId=randomBytes(16).toString("hex");
    challenge="CONFIRM CATEGORY "+randomBytes(8).toString("hex");
    previous=previousReview;
    phase="awaiting-explicit-confirmation";
    return Object.freeze({
      ok:true,canSave:false,writeAllowed:false,dispatched:false,
      receiptId,confirmationPrompt:challenge,
      phase,reason:"reviewed-but-not-authorized"
    });
  }
  async function confirm({confirmationText,current}={}){
    if(phase!=="awaiting-explicit-confirmation")
      return refused("confirmation-not-armed");
    // Consume synchronously. A second concurrent confirm cannot seal twice.
    phase="sealing";
    const phrase=challenge;
    challenge="";
    if(confirmationText!==phrase){
      phase="refused";previous=null;requestId="";
      return refused("confirmation-mismatch");
    }
    const checked=checkReview(current,previous);
    if(!checked.ok){phase="refused";return checked;}
    const source=checkSource(current,{
      readerEndpoint,writerEndpoint,writerSourceKey
    });
    if(!source.ok){phase="refused";return refused(source.reason);}
    let digest;
    try{digest=hash(commandFor(requestId,checked.fields));}
    catch{phase="refused";return refused("invalid-command-shape");}
    const outcome=await sealConfirmedIntent(
      sandboxRoot,receiptId,requestId,digest);
    phase=outcome.ok?"confirmed-held-no-dispatch":"custody-uncertain";
    // Private requestId is never returned, even on a successful confirmation.
    requestId="";previous=null;
    return outcome;
  }
  function cancel(){
    if(phase==="sealing")return refused("in-flight-custody-recovery-required");
    if(phase!=="idle" && phase!=="awaiting-explicit-confirmation")
      return refused("already-consumed");
    phase="canceled";previous=null;requestId="";challenge="";
    return Object.freeze({ok:true,canSave:false,writeAllowed:false,
      dispatched:false,canRetry:false,phase});
  }
  function dispatch(){return refused("production-dispatch-hard-hold");}
  return Object.freeze({stage,confirm,cancel,status,dispatch});
}

// Read-only recovery lookup in a freshly launched process. It internally
// retrieves the private request ID, rebuilds the candidate *in memory* and
// compares the sealed digest, but NEVER releases the command or request ID.
export async function inspectM3d5b4DisposableReceipt({
  sandboxRoot,receiptId,view,readerEndpoint,writerEndpoint,writerSourceKey
}={}){
  if(typeof receiptId!=="string" || !receiptPattern.test(receiptId))
    return refused("invalid-receipt-handle");
  const source=checkSource(view,{readerEndpoint,writerEndpoint,writerSourceKey});
  if(!source.ok)return refused(source.reason);
  const checked=prepareOfflineCategorizedReview(viewFields(view));
  if(!checked.ok || checked.canSave!==false || checked.writeAllowed!==false)
    return refused(checked.reason||"review-invalid");
  const opened=await openFixture(sandboxRoot);
  if(opened.refusal)return refused(opened.refusal);
  const dir=opened.dir;
  try{
    const prior=await listTrustedRecords(dir);
    if(prior.refusal)return refused(prior.refusal);
    const record=prior.records.find(x=>x.receiptId===receiptId);
    if(!record)return refused("receipt-not-found");
    let digest;
    try{digest=hash(commandFor(record.requestId,checked.previewFields));}
    catch{return refused("invalid-command-shape");}
    if(digest!==record.digest)return refused("receipt-financial-details-changed");
    return held(receiptId,"durable-receipt-observed-no-dispatch");
  }catch{return refused("receipt-recovery-uncertain");}
  finally{await dir.close();}
}
