"use strict";
/* TASKS M13a // PURE, TEST-ONLY restart review of an immutable fake stage.
 * Consumes only caller-supplied synthetic bytes. There is NO file access,
 * writer, authenticated journal, installer, recovery activation or UI mount.
 * A fresh owner NEVER automatically publishes a candidate or clears a draft.
 */
const crypto=require("node:crypto");
const sha=raw=>crypto.createHash("sha256").update(raw).digest("hex");
const copy=x=>JSON.parse(JSON.stringify(x));
const SOURCE="apollo-hub-todo-v1.json";
const PHASES=new Set(["RESERVED","SETTLED"]);
const token=x=>typeof x==="string" && /^[A-Za-z0-9_-]{8,48}$/.test(x);
const keys=(x,desired)=>x && typeof x==="object" && !Array.isArray(x)
    && Object.keys(x).sort().join(",")===desired.slice().sort().join(",");
const deny=reason=>({ok:false,reason,writable:false,writeAuthorized:false,
    restoreAuthorized:false,replayAuthorized:false,clearDraftAuthorized:false,
    phase:"RECOVERY_REVIEW"});
function parseDoc(policy,raw) {
    if(!policy || typeof policy.parse!=="function"
            || typeof policy.validate!=="function"
            || typeof policy.view!=="function"
            || typeof raw!=="string" || raw.length>1048576 || !raw.length)
        return null;
    const result=policy.parse(raw);
    if(!result || !result.ok || !result.document
            || !policy.validate(result.document).ok
            || result.document.version!==3)
        return null;
    return result.document;
}
function make({policy,confirmed,candidate,draft,sessionId,ownerEpoch,generation,
                sequence,phase}={}) {
    if(!token(sessionId)||!Number.isSafeInteger(ownerEpoch)||ownerEpoch<1
            ||!Number.isSafeInteger(generation)||generation<1
            ||!Number.isSafeInteger(sequence)||sequence<1 ||sequence>9999999
            ||!PHASES.has(phase)
            ||!keys(draft,["surface","method","value"])
            ||!["HUB","DETAILS","PLANNER","PROJECTS"].includes(draft.surface)
            ||typeof draft.method!=="string"
            ||!draft.method || JSON.stringify(draft.value).length>32768)
        return deny("INVALID_SYNTHETIC_IDENTITY_OR_DRAFT");
    try {
        if(!confirmed || !candidate || !policy
                ||typeof policy.validate!=="function"
                ||!policy.validate(confirmed).ok
                ||!policy.validate(candidate).ok)
            return deny("INVALID_TASKS_DOCUMENT");
        const beforeRaw=JSON.stringify(confirmed,null,2)+"\n";
        const expectedRaw=JSON.stringify(candidate,null,2)+"\n";
        if(!parseDoc(policy,beforeRaw)||!parseDoc(policy,expectedRaw)
                ||beforeRaw===expectedRaw)
            return deny("INVALID_OR_UNCHANGED_CANDIDATE");
        const stageId="m13a-"+sessionId+"-"+ownerEpoch+"-"+sequence;
        const record={
            format:1,kind:"M13A_FAKE_RESTART_CHECKPOINT",sourceName:SOURCE,
            sessionId,ownerEpoch,generation,sequence,stageId,phase,
            beforeRaw,expectedRaw,beforeSha:sha(beforeRaw),
            expectedSha:sha(expectedRaw),draft:copy(draft)
        };
        const recordRaw=JSON.stringify(record)+"\n";
        if(Buffer.byteLength(recordRaw,"utf8")>2097152)
            return deny("CHECKPOINT_TOO_LARGE");
        return {ok:true,reason:"SYNTHETIC_CHECKPOINT_CANDIDATE",
            recordRaw,stageId,phase,writeAuthorized:false,
            restoreAuthorized:false,replayAuthorized:false,
            clearDraftAuthorized:false};
    } catch(e) {return deny("CHECKPOINT_CANDIDATE_UNAVAILABLE");}
}
function duplicateKeys(pairs) {
    const out={};
    for(const [k,v] of pairs) {
        if(Object.hasOwn(out,k)) throw Error("DUPLICATE_JSON_KEY");
        out[k]=v;
    }
    return out;
}
function reopen({recordRaw,sourceRaw,policy,freshSessionId,freshEpoch}={}) {
    if(typeof recordRaw!=="string" || Buffer.byteLength(recordRaw,"utf8")>2097152)
        return deny("INVALID_CHECKPOINT_BYTES");
    if(!token(freshSessionId) ||!Number.isSafeInteger(freshEpoch)||freshEpoch<1)
        return deny("INVALID_FRESH_OWNER");
    let r;
    try {r=JSON.parse(recordRaw);} catch(e) {return deny("INVALID_CHECKPOINT_JSON");}
    const fields=["format","kind","sourceName","sessionId","ownerEpoch",
        "generation","sequence","stageId","phase","beforeRaw","expectedRaw",
        "beforeSha","expectedSha","draft"];
    if(!keys(r,fields) ||r.format!==1
            ||r.kind!=="M13A_FAKE_RESTART_CHECKPOINT"
            ||r.sourceName!==SOURCE || !token(r.sessionId)
            ||r.sessionId===freshSessionId ||!Number.isSafeInteger(r.ownerEpoch)
            ||r.ownerEpoch<1 ||!Number.isSafeInteger(r.generation)||r.generation<1
            ||!Number.isSafeInteger(r.sequence)||r.sequence<1||r.sequence>9999999
            ||r.stageId!=="m13a-"+r.sessionId+"-"+r.ownerEpoch+"-"+r.sequence
            ||!PHASES.has(r.phase) ||freshEpoch<=r.ownerEpoch
            ||!keys(r.draft,["surface","method","value"])
            ||!["HUB","DETAILS","PLANNER","PROJECTS"].includes(r.draft.surface)
            ||typeof r.draft.method!=="string"
            ||typeof r.beforeSha!=="string"||typeof r.expectedSha!=="string"
            ||!(/^[a-f0-9]{64}$/.test(r.beforeSha))
            ||!(/^[a-f0-9]{64}$/.test(r.expectedSha)))
        return deny("INVALID_STAGE_IDENTITY_OR_OWNER");
    const confirmed=parseDoc(policy,r.beforeRaw);
    const candidate=parseDoc(policy,r.expectedRaw);
    if(!confirmed ||!candidate ||r.beforeRaw===r.expectedRaw
            ||sha(r.beforeRaw)!==r.beforeSha
            ||sha(r.expectedRaw)!==r.expectedSha)
        return deny("CHECKPOINT_HASH_OR_POLICY_MISMATCH");
    if(typeof sourceRaw!=="string" && sourceRaw!==null)
        return deny("INVALID_SOURCE_OBSERVATION");
    const sourceStatus=sourceRaw===null?"SOURCE_MISSING"
        :sourceRaw===r.beforeRaw?"SOURCE_AT_LAST_CONFIRMED"
        :sourceRaw===r.expectedRaw?"SOURCE_AT_CANDIDATE"
        :"SOURCE_MISMATCH";
    // The persisted checkpoint is NOT trusted source authority, and even a
    // settled marker and exact source bytes NEVER promote candidate on restart.
    const lastView=policy.view(confirmed.tasks.length?"ready":"empty",confirmed,"");
    return {ok:true,reason:"FRESH_OWNER_REVIEW_REQUIRED",phase:"RECOVERY_REVIEW",
        state:"error",writable:false,writeAuthorized:false,
        restoreAuthorized:false,replayAuthorized:false,
        clearDraftAuthorized:false,sourceStatus,
        priorPhase:r.phase,stageId:r.stageId,
        priorSessionId:r.sessionId,priorOwnerEpoch:r.ownerEpoch,
        freshEpoch,confirmedSha:r.beforeSha,
        items:copy(lastView.items),projects:copy(lastView.projects),
        draft:copy(r.draft),disposition:"KEEP_DRAFT"};
}
module.exports={make,reopen,SOURCE};
