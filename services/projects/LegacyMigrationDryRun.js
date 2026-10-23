.pragma library

// PROXY 1 / M10d: pure, fail-closed, non-persisting migration DRY RUN.
// Requires caller-supplied existing TodoPolicy and M10b journal policy.
// No FileView, disk mutation, GitHub call, backup, or live schema upgrade.
// The candidate version is the M10b prototype envelope, NOT live Todo v4.

var TOP_V12 = ["version", "nextId", "tasks"];
var TOP_V3 = ["version", "nextId", "nextProjectId", "projects", "tasks"];
var PROJECT_KEYS = ["id", "name", "createdAtMs", "updatedAtMs"];
var TASK_V1 = ["id", "title", "done", "createdAtMs", "updatedAtMs"];
var TASK_V2 = TASK_V1.concat(["priority", "description", "dueDate"]);
var TASK_V3 = TASK_V2.concat(["projectId"]);

function failure(reason) { return {ok:false, reason:reason}; }
function object(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
}
function exactKeys(value, allowed) {
    if (!object(value)) return false;
    var actual=Object.keys(value);
    if (actual.length !== allowed.length) return false;
    for (var i=0;i<actual.length;i++)
        if (allowed.indexOf(actual[i]) === -1) return false;
    return true;
}
function strictLegacy(source) {
    if (!object(source)) return failure("INVALID_LEGACY_OBJECT");
    var v=source.version;
    if (v!==1 && v!==2 && v!==3)
        return failure("UNSUPPORTED_LEGACY_VERSION");
    if (!exactKeys(source,v===3?TOP_V3:TOP_V12))
        return failure("UNRECOGNIZED_LEGACY_FIELDS");
    if (!Array.isArray(source.tasks)
            || v===3 && !Array.isArray(source.projects))
        return failure("INVALID_LEGACY_COLLECTIONS");
    for (var i=0;i<source.tasks.length;i++)
        if (!exactKeys(source.tasks[i],
                       v===1?TASK_V1:v===2?TASK_V2:TASK_V3))
            return failure("UNRECOGNIZED_TASK_FIELDS");
    if (v===3) for (var j=0;j<source.projects.length;j++)
        if (!exactKeys(source.projects[j],PROJECT_KEYS))
            return failure("UNRECOGNIZED_PROJECT_FIELDS");
    return {ok:true,reason:""};
}
function taskCopy(t) {
    return {id:t.id,title:t.title,done:t.done,
        createdAtMs:t.createdAtMs,updatedAtMs:t.updatedAtMs,
        priority:t.priority,description:t.description,
        dueDate:t.dueDate,projectId:t.projectId};
}
function projectCopy(p) {
    return {id:p.id,name:p.name,
        createdAtMs:p.createdAtMs,updatedAtMs:p.updatedAtMs};
}
// NORMAL projects are the only valid migration target for the existing v3
// records; there is NO attempt to infer GitHub project/item identity.
function projectCandidate(p) {
    var out=projectCopy(p);
    out.family="normal";
    out.remote=null;
    return out;
}
function deriveCandidate(normalized) {
    return {version:1,revision:0,
        nextId:normalized.nextId,
        nextProjectId:normalized.nextProjectId,
        projects:normalized.projects.map(projectCandidate),
        tasks:normalized.tasks.map(taskCopy),
        operations:[]};
}
function restoreCompatibleV3(candidate,legacyPolicy,journalPolicy) {
    if (!object(candidate) || !journalPolicy
            || typeof journalPolicy.verify!=="function"
            || !legacyPolicy || typeof legacyPolicy.validate!=="function")
        return failure("INVALID_DEPENDENCY_OR_CANDIDATE");
    var check=journalPolicy.verify(candidate);
    if (!check.ok) return failure("INVALID_PROTOTYPE_"+check.reason);
    if (candidate.revision!==0 || candidate.operations.length!==0)
        return failure("ACTIVE_JOURNAL_NOT_ROLLBACKABLE");
    if (!Number.isInteger(candidate.nextId)
            || !Number.isInteger(candidate.nextProjectId))
        return failure("MISSING_SEQUENCE_COUNTERS");
    for (var i=0;i<candidate.projects.length;i++) {
        var p=candidate.projects[i];
        if (!exactKeys(p,PROJECT_KEYS.concat(["family","remote"]))
                || p.family!=="normal" || p.remote!==null)
            return failure("GIT_OR_EXTRA_PROJECT_DATA");
    }
    for (var j=0;j<candidate.tasks.length;j++)
        if (!exactKeys(candidate.tasks[j],TASK_V3))
            return failure("EXTRA_TASK_DATA");
    if (!exactKeys(candidate,[
        "version","revision","nextId","nextProjectId",
        "projects","tasks","operations"]))
        return failure("EXTRA_ENVELOPE_DATA");
    var doc={version:3,nextId:candidate.nextId,
        nextProjectId:candidate.nextProjectId,
        projects:candidate.projects.map(projectCopy),
        tasks:candidate.tasks.map(taskCopy)};
    var legacyChecked=legacyPolicy.validate(doc);
    if (!legacyChecked.ok) return failure("INVALID_V3_"+legacyChecked.reason);
    return {ok:true,reason:"",document:doc};
}

// Raw source is validated by the EXISTING parser first. Then a stricter
// allowlist refuses fields that the legacy v3 clone would silently discard.
// No attempt is made to repair unsupported/malformed documents.
function plan(raw,legacyPolicy,journalPolicy) {
    if (!legacyPolicy || typeof legacyPolicy.parse!=="function"
            || typeof legacyPolicy.validate!=="function"
            || !journalPolicy || typeof journalPolicy.verify!=="function"
            || typeof journalPolicy.encode!=="function")
        return failure("MISSING_POLICIES");
    var parsed=legacyPolicy.parse(raw);
    if (!parsed.ok) return failure("LEGACY_"+parsed.reason);
    var source;
    try { source=JSON.parse(raw); }
    catch (e) { return failure("INVALID_JSON"); }
    var strict=strictLegacy(source);
    if (!strict.ok) return strict;
    var normalized=parsed.document;
    if (!legacyPolicy.validate(normalized).ok)
        return failure("INVALID_NORMALIZED_V3");
    var candidate=deriveCandidate(normalized);
    var checked=journalPolicy.verify(candidate);
    if (!checked.ok) return failure("CANDIDATE_"+checked.reason);
    var encoded=journalPolicy.encode(candidate);
    if (!encoded.ok) return failure("CANDIDATE_"+encoded.reason);
    var roundtrip=journalPolicy.decode
        ? journalPolicy.decode(encoded.raw)
        : failure("MISSING_DECODER");
    if (!roundtrip.ok) return failure("CANDIDATE_ROUNDTRIP_FAILED");
    var restored=restoreCompatibleV3(roundtrip.document,legacyPolicy,journalPolicy);
    if (!restored.ok) return restored;
    if (JSON.stringify(restored.document)!==JSON.stringify(normalized))
        return failure("LOSSY_COMPATIBILITY_ROUNDTRIP");
    return {ok:true,reason:"",
        sourceVersion:source.version,
        counts:{projects:normalized.projects.length,tasks:normalized.tasks.length},
        candidate:roundtrip.document,
        compatibilityV3:restored.document,
        // Pure dry run only: never claim a durable backup or disk migration.
        writeReady:false, migrationPerformed:false};
}
