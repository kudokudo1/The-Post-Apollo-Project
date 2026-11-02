"use strict";
// TASKS M12z // TEST-ONLY, PURE first-create candidate and settlement model.
// The caller supplies synthetic evidence, not a trusted installation identity.
// Never imported by Quickshell, never writes/creates files and NEVER grants
// production write/restore/bootstrap authority. Actual O_EXCL calls live only
// inside disposable CI tests, not in this reusable policy module.
const crypto=require("node:crypto");
const SOURCE="apollo-hub-todo-v1.json";
const sha256=raw=>crypto.createHash("sha256").update(raw).digest("hex");
function denied(reason) {
    return {candidate:false,reason,writeAuthorized:false,
            bootstrapAuthorized:false,restoreAuthorized:false};
}
function prepare({absence,policy,evidence}={}) {
    if(!absence || absence.classification!=="POSSIBLE_FRESH_INSTALL"
            || absence.reason!=="INDEPENDENT_INSTALL_PROVENANCE_REQUIRED"
            || absence.ok!==false || absence.writeAuthorized!==false
            || absence.bootstrapAuthorized!==false
            || absence.restoreAuthorized!==false)
        return denied("ABSENCE_REVIEW_REQUIRED");
    if(!evidence || evidence.kind!=="M12Z_FAKE_INSTALL_EVIDENCE"
            || evidence.firstRun!==true || evidence.generation!==1
            || typeof evidence.instanceId!=="string"
            || !/^[A-Za-z0-9_-]{8,48}$/.test(evidence.instanceId)
            || evidence.sourceName!==SOURCE)
        return denied("SYNTHETIC_INSTALL_EVIDENCE_REQUIRED");
    if(!policy || typeof policy.emptyDocument!=="function"
            || typeof policy.validate!=="function"
            || typeof policy.parse!=="function"
            || typeof policy.view!=="function")
        return denied("VALID_TASKS_POLICY_REQUIRED");
    try {
        const candidate=policy.emptyDocument();
        if(!policy.validate(candidate).ok || candidate.version!==3
                || !Array.isArray(candidate.tasks) || candidate.tasks.length
                || !Array.isArray(candidate.projects) || candidate.projects.length)
            return denied("INVALID_EMPTY_DOCUMENT");
        const raw=JSON.stringify(candidate,null,2)+"\n";
        const parsed=policy.parse(raw);
        if(!parsed.ok || JSON.stringify(parsed.document)!==JSON.stringify(candidate))
            return denied("EMPTY_DOCUMENT_ROUNDTRIP_FAILED");
        const bytes=Buffer.from(raw,"utf8");
        if(!bytes.length || bytes.length>1048576)
            return denied("EMPTY_DOCUMENT_SIZE_INVALID");
        return {
            candidate:true,reason:"SYNTHETIC_EXCLUSIVE_CREATE_CANDIDATE",
            sourceName:SOURCE,instanceId:evidence.instanceId,
            expectedRaw:raw,sha256:sha256(bytes),bytes:bytes.length,
            writeAuthorized:false,bootstrapAuthorized:false,
            restoreAuthorized:false,credentialStatus:"FAKE_ONLY"
        };
    } catch(e) {
        return denied("CANDIDATE_UNAVAILABLE");
    }
}
function observe({plan,exclusiveResult,readback,policy}={}) {
    const blocked=reason=>({
        simulatedConfirmed:false,reason,writeAuthorized:false,
        bootstrapAuthorized:false,restoreAuthorized:false
    });
    if(!plan || plan.candidate!==true
            || plan.reason!=="SYNTHETIC_EXCLUSIVE_CREATE_CANDIDATE"
            || plan.credentialStatus!=="FAKE_ONLY"
            || plan.writeAuthorized!==false
            || plan.bootstrapAuthorized!==false
            || plan.restoreAuthorized!==false
            || plan.sourceName!==SOURCE
            || !Number.isSafeInteger(plan.bytes)
            || typeof plan.expectedRaw!=="string"
            || typeof plan.sha256!=="string"
            || !/^[a-f0-9]{64}$/.test(plan.sha256))
        return blocked("VALID_SYNTHETIC_PLAN_REQUIRED");
    if(!exclusiveResult || exclusiveResult.status!=="EXCLUSIVELY_CREATED"
            || exclusiveResult.noOverwrite!==true
            || exclusiveResult.sourceName!==SOURCE)
        return blocked("EXCLUSIVE_CREATE_NOT_PROVEN");
    if(!Buffer.isBuffer(readback))
        return blocked("INDEPENDENT_READBACK_REQUIRED");
    const expected=Buffer.from(plan.expectedRaw,"utf8");
    if(expected.length!==plan.bytes || sha256(expected)!==plan.sha256)
        return blocked("CANDIDATE_INTEGRITY_MISMATCH");
    if(!readback.equals(expected))
        return blocked("READBACK_BYTES_MISMATCH");
    if(!policy || typeof policy.parse!=="function"
            || typeof policy.validate!=="function")
        return blocked("TASKS_POLICY_REQUIRED");
    try {
        const parsed=policy.parse(readback.toString("utf8"));
        if(!parsed.ok || !policy.validate(parsed.document).ok
                || parsed.document.version!==3
                || parsed.document.tasks.length!==0
                || parsed.document.projects.length!==0)
            return blocked("READBACK_POLICY_INVALID");
    } catch(e) {return blocked("READBACK_POLICY_UNAVAILABLE");}
    // Even a passing test is NEVER a real installation credential, OS
    // authority, durable receipt, or safe production bootstrap decision.
    return {simulatedConfirmed:true,reason:"SYNTHETIC_CREATE_AND_READBACK",
            sourceSha256:sha256(readback),
            writeAuthorized:false,bootstrapAuthorized:false,
            restoreAuthorized:false};
}
module.exports={prepare,observe,SOURCE};
