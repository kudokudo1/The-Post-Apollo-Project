.pragma library

// PROXY 1 / M10g: read-only integration seam, NOT a deployed storage adapter.
// Converts a verified M10b *prototype* envelope into the existing v3 snapshot
// shape for Hub/TASKS/TODAY/PLANNER. Never creates a writer or grants sync.
// Existing ApolloHubTodoStore remains the sole live writer until a separately
// reviewed, operator-approved cutover with proper durability guarantees.

var REQUIRED_GATES = [
    "originalByteBackupVerified",
    "originalSourceFrozen",
    "legacyWriterQuiesced",
    "candidateValidated",
    "exclusiveNewWriterProven",
    "crashRecoveryProven",
    "snapshotParityProven",
    "rollbackProcedureVerified",
    "operatorCutoverApproved"
];
function fail(reason) {
    return {ok:false,reason:reason,writeReady:false};
}
function isObject(value) {
    return value!==null && typeof value==="object" && !Array.isArray(value);
}
function validCounter(n) {
    return Number.isInteger(n) && n>=1 && n<=1000000000;
}
function exactTypeAndFields(record,fields) {
    if (!isObject(record)) return false;
    var keys=Object.keys(record);
    if (keys.length!==fields.length) return false;
    for(var i=0;i<fields.length;i++)
        if(!Object.prototype.hasOwnProperty.call(record,fields[i]))
            return false;
    return true;
}
var TASK_FIELDS=[
    "id","title","done","createdAtMs","updatedAtMs",
    "priority","description","dueDate","projectId"
];
// Extra envelope metadata stays in the original envelope and is *not*
// written back into a legacy store. Only project/task compatibility fields
// are copied. Invalid or unsupported source documents fail closed.
function preview(envelope,journalPolicy,legacyPolicy) {
    if (!journalPolicy || typeof journalPolicy.verify!=="function"
            || !legacyPolicy || typeof legacyPolicy.validate!=="function"
            || typeof legacyPolicy.view!=="function")
        return fail("MISSING_DEPENDENCY");
    var check=journalPolicy.verify(envelope);
    if (!check.ok) return fail("INVALID_CANDIDATE_"+check.reason);
    if (!validCounter(envelope.nextId) || !validCounter(envelope.nextProjectId))
        return fail("MISSING_OR_INVALID_SEQUENCE_COUNTERS");
    var projects=[];
    for(var i=0;i<envelope.projects.length;i++) {
        var p=envelope.projects[i];
        if (!isObject(p) || !Number.isSafeInteger(p.createdAtMs)
                || !Number.isSafeInteger(p.updatedAtMs))
            return fail("MISSING_PROJECT_TIMESTAMPS");
        if(p.family!=="normal" && p.family!=="git")
            return fail("INVALID_PROJECT_FAMILY");
        projects.push({id:p.id,name:p.name,
            createdAtMs:p.createdAtMs,updatedAtMs:p.updatedAtMs});
    }
    var tasks=[];
    for(var j=0;j<envelope.tasks.length;j++) {
        var t=envelope.tasks[j];
        if(!isObject(t)) return fail("INVALID_TASK");
        for(var k=0;k<TASK_FIELDS.length;k++)
            if(!Object.prototype.hasOwnProperty.call(t,TASK_FIELDS[k]))
                return fail("MISSING_TASK_COMPATIBILITY_FIELD");
        tasks.push({id:t.id,title:t.title,done:t.done,
            createdAtMs:t.createdAtMs,updatedAtMs:t.updatedAtMs,
            priority:t.priority,description:t.description,
            dueDate:t.dueDate,projectId:t.projectId});
    }
    var document={
        version:3,nextId:envelope.nextId,
        nextProjectId:envelope.nextProjectId,
        projects:projects,tasks:tasks
    };
    var valid=legacyPolicy.validate(document);
    if(!valid.ok) return fail("INVALID_COMPATIBILITY_V3_"+valid.reason);
    var state=tasks.length===0?"empty":"ready";
    var snapshot=legacyPolicy.view(state,document,"");
    // This bridge is for rendering only. A live UI must not mount it as its
    // editing store. Snapshot.writable from v3 is forced false.
    snapshot.writable=false;
    return {ok:true,reason:"",writeReady:false,
        source:"M10G_READ_ONLY_PROTOTYPE",
        candidateRevision:envelope.revision,
        queuedOperations:envelope.operations.filter(function(op) {
            return op.state!=="ACKNOWLEDGED";
        }).length,
        snapshot:snapshot,
        // Returned v3 document is for verified projection comparison only.
        // NEVER persist it back over the enriched prototype.
        compatibilityDocument:document};
}
// Declarative readiness review only: self-reported flags are not verified
// evidence. Even with all positive, this policy CANNOT authorize activation.
function cutoverReview(facts) {
    if(!isObject(facts))
        return {reviewReady:false,writeReady:false,activate:false,
            blockedBy:REQUIRED_GATES.slice(),reason:"MISSING_EVIDENCE"};
    var blocked=REQUIRED_GATES.filter(function(name) {
        return facts[name]!==true;
    });
    // Operator authority is an external permission; "true" here is a
    // planning assertion, not an approval record or token.
    return {reviewReady:blocked.length===0,writeReady:false,activate:false,
        blockedBy:blocked,
        reason:blocked.length?"REVIEW_GATES_OPEN":"EXTERNAL_ACTIVATION_REQUIRED"};
}
