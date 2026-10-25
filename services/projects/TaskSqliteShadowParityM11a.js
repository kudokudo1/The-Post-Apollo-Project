.pragma library

// M11a: PURE, UNMOUNTED, READ-ONLY JSON v3 vs SQLite-v2 shadow UI parity.
// This is NOT a migration, writer selector, rollback switch or proof that
// either source is quiescent. Only an external reviewed process can establish
// disk baselines, exclusive ownership, backups and on-device runtime safety.
var VERSION = 1;
var PROJECT_FIELDS = ["id","name","createdAtMs","updatedAtMs"];
var TASK_FIELDS = ["id","title","done","createdAtMs","updatedAtMs",
    "priority","description","dueDate","projectId"];
var REPORT_LIMIT = 20;
var RESPONSE_FIELDS = ["protocol","status","available","revision",
    "sourceHash","blockedOperations","document","writeReady",
    "remoteWriteAuthorized"];

function object(v) {
    return v !== null && typeof v === "object" && !Array.isArray(v);
}
function keysExact(o, names) {
    if (!object(o) || Object.keys(o).length !== names.length) return false;
    return names.every(function(k) {
        return Object.prototype.hasOwnProperty.call(o, k);
    });
}
function result(status, reasons, metrics) {
    var r={version:VERSION,status:status,matched:status==="MATCH_FOR_REVIEW_ONLY",
        blockers:reasons, snapshot: null,
        writeReady:false,activate:false,migrate:false,restore:false,
        remoteWriteAuthorized:false,legacyWriterFrozen:false,
        sqliteWriterAuthorized:false};
    if (metrics) {
        r.total=metrics.total;
        r.projects=metrics.projects;
        r.completed=metrics.completed;
        r.remaining=metrics.remaining;
    }
    return r;
}
function compare(legacyDocument, sqliteResponse, todoPolicy) {
    // Even self-asserted user approval cannot authorize a writer here.
    if (!todoPolicy || typeof todoPolicy.validate!=="function"
            || typeof todoPolicy.view!=="function")
        return result("BLOCKED",["MISSING_POLICY"]);
    if (!keysExact(sqliteResponse, RESPONSE_FIELDS)
            || sqliteResponse.protocol !== 1
            || sqliteResponse.available !== true
            || sqliteResponse.writeReady !== false
            || sqliteResponse.remoteWriteAuthorized !== false
            || !Number.isSafeInteger(sqliteResponse.revision)
            || sqliteResponse.revision < 0
            || typeof sqliteResponse.sourceHash !== "string"
            || !/^[0-9a-f]{64}$/.test(sqliteResponse.sourceHash)
            || !Number.isSafeInteger(sqliteResponse.blockedOperations)
            || sqliteResponse.blockedOperations < 0)
        return result("BLOCKED",["INVALID_SQLITE_READ_EVIDENCE"]);
    if (sqliteResponse.status === "RECOVERY_REVIEW"
            || sqliteResponse.blockedOperations !== 0)
        return result("BLOCKED",["SQLITE_RECOVERY_REVIEW"]);
    if (sqliteResponse.status !== "READY"
            && sqliteResponse.status !== "EMPTY")
        return result("BLOCKED",["SQLITE_NOT_READY"]);
    if (!object(legacyDocument) || !todoPolicy.validate(legacyDocument).ok)
        return result("BLOCKED",["INVALID_LEGACY_DOCUMENT"]);
    if (!object(sqliteResponse.document)
            || !todoPolicy.validate(sqliteResponse.document).ok)
        return result("BLOCKED",["INVALID_SQLITE_COMPATIBILITY_DOCUMENT"]);
    var source=sqliteResponse.document;
    if (sqliteResponse.status !== (source.tasks.length ? "READY":"EMPTY"))
        return result("BLOCKED",["INCONSISTENT_SQLITE_STATUS"]);

    // Compare *full compatibility data*, not just UI counts: a single title,
    // due date or assignment mismatch must block acceptance. Differences
    // return field NAMES/positions only, never private title/description.
    var mismatches=[];
    function difference(label, x, y) {
        if (x !== y && mismatches.length < REPORT_LIMIT)
            mismatches.push(label);
    }
    difference("version",legacyDocument.version,source.version);
    difference("nextId",legacyDocument.nextId,source.nextId);
    difference("nextProjectId",legacyDocument.nextProjectId,source.nextProjectId);
    difference("projects.length",legacyDocument.projects.length,source.projects.length);
    difference("tasks.length",legacyDocument.tasks.length,source.tasks.length);

    for (var p=0;p<Math.min(legacyDocument.projects.length,source.projects.length);p++)
        for (var i=0;i<PROJECT_FIELDS.length;i++) {
            var field=PROJECT_FIELDS[i];
            difference("projects["+p+"]."+field,
                legacyDocument.projects[p][field],source.projects[p][field]);
        }
    for (var t=0;t<Math.min(legacyDocument.tasks.length,source.tasks.length);t++)
        for (var j=0;j<TASK_FIELDS.length;j++) {
            var key=TASK_FIELDS[j];
            difference("tasks["+t+"]."+key,
                legacyDocument.tasks[t][key],source.tasks[t][key]);
        }
    if (mismatches.length)
        return result("DIVERGED",mismatches);

    var state=source.tasks.length ? "ready":"empty";
    var legacy=todoPolicy.view(state,legacyDocument,"");
    var sqlite=todoPolicy.view(state,source,"");
    if (!legacy || !sqlite || legacy.total!==sqlite.total
            || legacy.remaining!==sqlite.remaining
            || legacy.completed!==sqlite.completed
            || legacy.items.length!==sqlite.items.length
            || legacy.projects.length!==sqlite.projects.length)
        return result("BLOCKED",["UI_VIEW_PARITY_FAILURE"]);
    for (var q=0;q<sqlite.items.length;q++) {
        if (sqlite.items[q].id!==legacy.items[q].id)
            return result("BLOCKED",["UI_TASK_ORDER_MISMATCH"]);
    }
    for (var r=0;r<sqlite.projects.length;r++) {
        var a=legacy.projects[r],b=sqlite.projects[r];
        if (a.id!==b.id || a.total!==b.total
                || a.remaining!==b.remaining || a.completed!==b.completed)
            return result("BLOCKED",["UI_PROJECT_COUNTER_MISMATCH"]);
    }
    // Exactly the same deployed snapshot data but *not* an editable one.
    sqlite.writable=false;
    var confirmed=result("MATCH_FOR_REVIEW_ONLY",[],
        {total:sqlite.total,projects:sqlite.projects.length,
         completed:sqlite.completed,remaining:sqlite.remaining});
    confirmed.snapshot=sqlite;
    return confirmed;
}
