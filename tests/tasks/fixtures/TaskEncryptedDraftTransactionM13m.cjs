"use strict";
/*
 * TASKS M13m // NEVER-MOUNTED FAKE-ONLY transaction policy prototype.
 *
 * This module performs no OS I/O, authentication, trust establishment,
 * keyring calls, TASKS mutation, UI rendering or durable transactions.
 * It uses the M13f AES-256-GCM fixture to test encrypted source binding.
 *
 * It accepts only explicitly marked fake task/source/editor data.
 * All returned authority flags remain false, INCLUDING success results.
 * A caller-supplied "optedIn", "ledger" or "unlocked" value is UNTRUSTED.
 */
const crypto=require("node:crypto");
const cipher=require("./TaskEncryptedRecoveryM13f.cjs");
const NO_POWER=Object.freeze({
    productionActivation:false,
    userConsentAuthenticated:false,
    keyReleaseAuthorized:false,
    sourceTrusted:false,
    persistAuthorized:false,
    decryptAuthorized:false,
    previewAuthorized:false,
    restoreAuthorized:false,
    writeAuthorized:false,
    replayAuthorized:false,
    deleteAuthorized:false,
    clearDraftAuthorized:false,
    exportAuthorized:false,
    syncAuthorized:false
});
const exact=(value,keys)=>value&&typeof value==="object"
    &&!Array.isArray(value)
    &&Object.keys(value).sort().join(",")===keys.slice().sort().join(",");
const token=x=>typeof x==="string"&&/^[A-Za-z0-9_-]{8,80}$/.test(x);
const digest=x=>typeof x==="string"&&/^[0-9a-f]{64}$/.test(x);
const positive=x=>Number.isSafeInteger(x)&&x>0;
const nonnegative=x=>Number.isSafeInteger(x)&&x>=0;
const fail=status=>({ok:false,status,...NO_POWER});
const ok=(status,data)=>({ok:true,status,...data,...NO_POWER});
const sourceKeys=["kind","generation","raw"];
const ledgerKeys=["kind","installationId","epoch","sourceGeneration",
    "sourceDigest","latestCommittedSeq"];
const checkpointKeys=["format","kind","installationId","epoch","stageId",
    "surface","sourceGeneration","sourceDigest","checkpointSeq","envelopeRaw"];
function sourceInfo(source) {
    if(!exact(source,sourceKeys)||source.kind!=="M13M_FAKE_SOURCE"||
        !positive(source.generation)||typeof source.raw!=="string"||
        Buffer.byteLength(source.raw,"utf8")>4096)return null;
    let v;
    try{v=JSON.parse(source.raw);}catch(e){return null;}
    if(!exact(v,["kind","documentVersion","marker"])
        ||v.kind!=="M13M_FAKE_TASKS_JSON"
        ||v.documentVersion!==3
        ||typeof v.marker!=="string" || !/^FAKE_[A-Z0-9_]{1,100}$/.test(v.marker))
        return null;
    return {generation:source.generation,
        digest:crypto.createHash("sha256").update(source.raw,"utf8").digest("hex")};
}
function ledgerValid(x) {
    return exact(x,ledgerKeys)&&x.kind==="M13M_FAKE_LEDGER"
        &&token(x.installationId)&&positive(x.epoch)
        &&positive(x.sourceGeneration)&&digest(x.sourceDigest)
        &&nonnegative(x.latestCommittedSeq);
}
function checkpointValid(x) {
    return exact(x,checkpointKeys)&&x.format===1
        &&x.kind==="M13M_FAKE_CHECKPOINT"&&token(x.installationId)
        &&positive(x.epoch)&&positive(x.sourceGeneration)
        &&digest(x.sourceDigest)&&positive(x.checkpointSeq)
        &&typeof x.stageId==="string"
        &&/^m13a-[A-Za-z0-9_-]{8,80}-[1-9][0-9]*-[1-9][0-9]*$/.test(x.stageId)
        &&["HUB","DETAILS","PLANNER","PROJECTS"].includes(x.surface)
        &&typeof x.envelopeRaw==="string"&&
        Buffer.byteLength(x.envelopeRaw,"utf8")<=70000;
}
function matchesSourceLedger(src,ledger) {
    return src.generation===ledger.sourceGeneration
        &&src.digest===ledger.sourceDigest;
}
function createSyntheticCheckpoint({source,ledger,identity,draft,key,optedIn,
                                    checkpointSeq}={}) {
    if(optedIn!==true)return fail("SIMULATED_OPT_IN_REQUIRED");
    const src=sourceInfo(source);
    if(!src)return fail("INVALID_FAKE_SOURCE");
    if(!ledgerValid(ledger))return fail("INVALID_FAKE_LEDGER");
    if(!matchesSourceLedger(src,ledger))
        return fail("SOURCE_NOT_LAST_CONFIRMED");
    if(!identity||identity.installationId!==ledger.installationId
        ||identity.epoch!==ledger.epoch)
        return fail("INSTALLATION_OR_EPOCH_MISMATCH");
    if(!positive(checkpointSeq) ||
        checkpointSeq!==ledger.latestCommittedSeq+1)
        return fail("CHECKPOINT_SEQUENCE_NOT_NEXT");
    if(!exact(draft,["kind","surface","value"])
        ||draft.kind!=="M13M_FAKE_EDITOR_DRAFT"
        ||draft.surface!==identity.surface
        ||typeof draft.value!=="string"
        ||!/^FAKE_[A-Z0-9_]{1,500}$/.test(draft.value))
        return fail("FAKE_EDITOR_DRAFT_REQUIRED");
    const inner={kind:"M13M_FAKE_BOUND_DRAFT",
        installationId:ledger.installationId,epoch:ledger.epoch,
        sourceGeneration:src.generation,sourceDigest:src.digest,
        checkpointSeq,marker:draft.value};
    const sealed=cipher.seal({identity,key,optedIn:true,
        draft:{kind:"M13F_FAKE_DRAFT",surface:identity.surface,value:inner}});
    if(!sealed.ok)return fail("ENCRYPTION_NOT_VERIFIED");
    const checkpoint={
        format:1,kind:"M13M_FAKE_CHECKPOINT",
        installationId:ledger.installationId,epoch:ledger.epoch,
        stageId:identity.stageId,surface:identity.surface,
        sourceGeneration:src.generation,sourceDigest:src.digest,
        checkpointSeq,envelopeRaw:sealed.envelopeRaw
    };
    // This is a MODEL, not a committed ledger. No filesystem operation
    // or durable/verified checkpoint state is established here.
    const proposedLedger={...ledger,latestCommittedSeq:checkpointSeq};
    return ok("SYNTHETIC_CIPHERTEXT_PREPARED_NOT_DURABLE",
              {checkpoint,proposedLedger});
}
function simulateReadback({checkpoint,proposedLedger,readbackEnvelopeRaw}={}) {
    if(!checkpointValid(checkpoint)||!ledgerValid(proposedLedger))
        return fail("INVALID_SIMULATED_READBACK");
    if(proposedLedger.installationId!==checkpoint.installationId
        ||proposedLedger.epoch!==checkpoint.epoch
        ||proposedLedger.sourceGeneration!==checkpoint.sourceGeneration
        ||proposedLedger.sourceDigest!==checkpoint.sourceDigest
        ||proposedLedger.latestCommittedSeq!==checkpoint.checkpointSeq)
        return fail("READBACK_LEDGER_MISMATCH");
    if(typeof readbackEnvelopeRaw!=="string"
        ||readbackEnvelopeRaw!==checkpoint.envelopeRaw)
        return fail("CIPHERTEXT_READBACK_MISMATCH");
    return ok("SYNTHETIC_BYTES_MATCH_NOT_DURABLE",{
        simulatedReadbackMatched:true
    });
}
function inspectLocked({checkpoint}={}) {
    if(!checkpointValid(checkpoint))
        return fail("INVALID_FAKE_CHECKPOINT");
    const outcome=cipher.inspectLocked({envelopeRaw:checkpoint.envelopeRaw});
    if(!outcome.ok)return fail("INVALID_ENCRYPTED_ENVELOPE");
    return ok("LOCKED_INDICATOR_ONLY",{
        locked:true,simulatedRecoveryCandidate:true
    });
}
function evaluateSyntheticRecovery({checkpoint,source,ledger,identity,key,
                                    unlocked,reviewRequested,activeDraftPresent}={}) {
    if(!checkpointValid(checkpoint))return fail("INVALID_FAKE_CHECKPOINT");
    const src=sourceInfo(source);
    if(!src)return fail("INVALID_FAKE_SOURCE");
    if(!ledgerValid(ledger))return fail("TRUSTED_LEDGER_UNAVAILABLE");
    if(checkpoint.installationId!==ledger.installationId
        ||checkpoint.epoch!==ledger.epoch
        ||!identity||identity.installationId!==checkpoint.installationId
        ||identity.epoch!==checkpoint.epoch
        ||identity.stageId!==checkpoint.stageId
        ||identity.surface!==checkpoint.surface)
        return fail("IDENTITY_OR_CONTEXT_MISMATCH");
    if(checkpoint.checkpointSeq!==ledger.latestCommittedSeq)
        return fail("STALE_OR_UNCOMMITTED_CHECKPOINT");
    if(!matchesSourceLedger(src,ledger)
        ||checkpoint.sourceDigest!==src.digest
        ||checkpoint.sourceGeneration!==src.generation)
        return fail("SOURCE_CHANGED_REVIEW_REQUIRED");
    if(activeDraftPresent!==false)
        return fail("ACTIVE_EDITOR_DRAFT_REVIEW_REQUIRED");
    if(reviewRequested!==true)
        return fail("SEPARATE_USER_REVIEW_REQUIRED");
    if(unlocked!==true)
        return fail("SEPARATE_UNLOCK_REQUIRED");
    const opened=cipher.openAfterUnlock({
        envelopeRaw:checkpoint.envelopeRaw,identity,key,unlocked:true});
    if(!opened.ok)return fail("CIPHERTEXT_AUTH_OR_KEY_REFUSED");
    const inner=opened.draft&&opened.draft.value;
    if(opened.draft.surface!==checkpoint.surface
        ||!exact(inner,["kind","installationId","epoch","sourceGeneration",
                       "sourceDigest","checkpointSeq","marker"])
        ||inner.kind!=="M13M_FAKE_BOUND_DRAFT"
        ||inner.installationId!==checkpoint.installationId
        ||inner.epoch!==checkpoint.epoch
        ||inner.sourceGeneration!==checkpoint.sourceGeneration
        ||inner.sourceDigest!==checkpoint.sourceDigest
        ||inner.checkpointSeq!==checkpoint.checkpointSeq
        ||typeof inner.marker!=="string"
        ||!/^FAKE_[A-Z0-9_]{1,500}$/.test(inner.marker))
        return fail("AUTHENTICATED_BINDING_MISMATCH");
    // "Preview" is synthetic data in an isolated model. NEVER a production
    // draft reveal, UI restore, source mutation or authorization.
    return ok("SYNTHETIC_PREVIEW_CANDIDATE_REQUIRES_REAL_AUTHORITY",{
        fakePreviewMarker:inner.marker,
        disposition:"PREVIEW_ONLY_NO_APPLY"
    });
}
module.exports={createSyntheticCheckpoint,simulateReadback,inspectLocked,
    evaluateSyntheticRecovery,NO_POWER};
