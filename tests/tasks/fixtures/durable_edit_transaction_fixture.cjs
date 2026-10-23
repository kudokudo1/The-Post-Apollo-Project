"use strict";

// PROXY 1 M10i: throwaway, Node-only transaction composition fixture.
// NEVER point it at live Quickshell data or use it as a production adapter.
// Uses existing M10f cooperative lock and M10h in-memory model; it does
// not perform GitHub transport, issue permissions, or authorize migration.
const gate=require("./single_writer_gate_fixture.cjs");
const crypto=require("node:crypto");

const digest=raw=>crypto.createHash("sha256").update(raw,"utf8").digest("hex");
const fail=reason=>({ok:false,reason,localSaved:false,remoteSent:false});
function edit(document,command,model) {
    if(!command || typeof command!=="object")
        return fail("INVALID_COMMAND");
    if(command.kind==="task")
        return model.editTask(document,command.request);
    if(command.kind==="custom")
        return model.editCustomValue(document,command.request);
    if(command.kind==="project-rename")
        return model.renameProject(document,command.request);
    if(command.kind==="field-create")
        return model.addLocalField(document,command.request);
    return fail("UNKNOWN_COMMAND");
}
// Callers first acquire() a valid M10f lease for a throwaway envelope.
// expected revision + complete source fingerprint MUST come from a previously
// inspected committed document. The fixture retains the lease after a
// commit exception; caller must reconcile before any retry/release decision.
function transact(lease,expected,command,model,stopAt) {
    const before=gate.inspect(lease,model);
    if(!before.ok) return fail("UNREADABLE_SOURCE_"+before.reason);
    if(!expected || !Number.isSafeInteger(expected.revision)
        || typeof expected.sha256!=="string"
        || !/^[a-f0-9]{64}$/.test(expected.sha256))
        return fail("EXPECTED_BASELINE_REQUIRED");
    if(before.revision!==expected.revision)
        return fail("STALE_REVISION");
    if(before.sha256!==expected.sha256)
        return fail("STALE_SOURCE_HASH");
    const proposed=edit(before.document,command,model);
    if(!proposed.ok) return fail("EDIT_"+proposed.reason);
    const encoded=model.encode(proposed.document);
    if(!encoded.ok) return fail("ENCODING_"+encoded.reason);
    const intent={
        baselineRevision:before.revision,
        baselineHash:before.sha256,
        candidateRevision:proposed.document.revision,
        candidateHash:digest(encoded.raw),
        commandKind:command.kind,
        remoteIntentCreated:proposed.remoteIntentCreated===true
    };
    // No remote worker may observe intent for dispatch until local commit
    // is acknowledged and the remote side has its separate authorization.
    try {
        const committed=gate.commit(lease,before.revision,before.sha256,
            proposed.document,model,stopAt);
        if(!committed.ok) return fail("COMMIT_"+committed.reason);
        if(committed.revision!==intent.candidateRevision
            || committed.sha256!==intent.candidateHash)
            return {ok:false,reason:"COMMIT_READBACK_MISMATCH",
                localSaved:false,remoteSent:false,intent};
        return {ok:true,reason:"",status:"LOCAL_COMMITTED",
            localSaved:true,remoteSent:false,
            remoteWriteAuthorized:false,remoteIntentCreated:intent.remoteIntentCreated,
            revision:committed.revision,sha256:committed.sha256};
    } catch(e) {
        // An interrupted rename may already have committed. Do NOT claim
        // failure/rollback or automatically replay this edit.
        return {ok:false,reason:"COMMIT_UNCERTAIN",localSaved:false,
            remoteSent:false,remoteWriteAuthorized:false,intent};
    }
}
// Only compares exact bytes/revisions of the committed test envelope.
// An observed candidate is NOT a GitHub acknowledgement.
function reconcile(lease,intent,model) {
    if(!intent || !Number.isSafeInteger(intent.baselineRevision)
        || !Number.isSafeInteger(intent.candidateRevision)
        || !/^[a-f0-9]{64}$/.test(intent.baselineHash||"")
        || !/^[a-f0-9]{64}$/.test(intent.candidateHash||"")
        || intent.candidateRevision!==intent.baselineRevision+1)
        return fail("INVALID_INTENT");
    const observed=gate.inspect(lease,model);
    if(!observed.ok) return fail("RECONCILIATION_BLOCKED_"+observed.reason);
    if(observed.revision===intent.candidateRevision
        && observed.sha256===intent.candidateHash)
        return {ok:true,reason:"",status:"LOCAL_COMMIT_OBSERVED",
            localSaved:true,remoteSent:false,remoteWriteAuthorized:false};
    if(observed.revision===intent.baselineRevision
        && observed.sha256===intent.baselineHash)
        return {ok:true,reason:"",status:"LOCAL_COMMIT_NOT_APPLIED",
            localSaved:false,remoteSent:false,remoteWriteAuthorized:false};
    return fail("UNKNOWN_OR_CONFLICTING_LOCAL_STATE");
}
module.exports={transact,reconcile,inspect:gate.inspect,
    acquire:gate.acquire,release:gate.release};
