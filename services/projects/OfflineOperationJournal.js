.pragma library

// PROXY 1 / M10b: Pure, versioned model + offline-intent journal prototype.
// Returns new envelopes. It NEVER persists files, uses gh, starts a process,
// verifies GitHub identities, authorizes sync or executes remote changes.
// Persistence and remote read-back must be separate reviewed integrations.

var MAX_PROJECTS = 30;
var MAX_TASKS = 200;
var MAX_OPERATIONS = 1000;
var MAX_REVISION = 1000000000;
var MAX_SERIALIZED = 1048576;
var FIELDS = ["title", "done", "priority", "description", "dueDate"];
var STATES = ["PENDING", "SENDING", "UNCERTAIN", "ACKNOWLEDGED", "CONFLICT"];
var PRIORITIES = ["none", "low", "medium", "high", "urgent"];

function plain(value) {
    return value !== null && typeof value === "object"
           && !Array.isArray(value);
}
function id(value, prefix) {
    return typeof value === "string"
           && new RegExp("^" + prefix + "[1-9][0-9]*$").test(value)
           && value.length <= 32;
}
function goodText(value, maximum, nonempty) {
    return typeof value === "string" && value.length <= maximum
           && (!nonempty || (value.length > 0 && value === value.trim()))
           && !/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/.test(value);
}
function validDate(value) {
    if (value === null) return true;
    if (typeof value !== "string"
            || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
    var y = Number(value.slice(0,4)), m = Number(value.slice(5,7));
    var d = Number(value.slice(8,10));
    if (y < 1 || m < 1 || m > 12 || d < 1) return false;
    var leap = y % 4 === 0 && (y % 100 !== 0 || y % 400 === 0);
    var days = [31,leap?29:28,31,30,31,30,31,31,30,31,30,31];
    return d <= days[m-1];
}
function validValue(field, value) {
    if (field === "title") return goodText(value,160,true);
    if (field === "done") return typeof value === "boolean";
    if (field === "priority") return PRIORITIES.indexOf(value) >= 0;
    if (field === "description") return goodText(value,2000,false);
    if (field === "dueDate") return validDate(value);
    return false;
}
function validProject(p) {
    return plain(p) && id(p.id,"p") && goodText(p.name,64,true)
        && (p.family === "normal" || p.family === "git");
}
function validTask(t, projectIds) {
    if (!plain(t) || !id(t.id,"t")
            || !(t.projectId === null
                 || typeof t.projectId === "string" && projectIds[t.projectId]))
        return false;
    for (var i=0;i<FIELDS.length;i++)
        if (!validValue(FIELDS[i],t[FIELDS[i]])) return false;
    return true;
}
function fail(reason) { return {ok:false,reason:reason}; }
function copy(value) { return JSON.parse(JSON.stringify(value)); }
function verify(document) {
    if (!plain(document)) return fail("INVALID_ENVELOPE");
    if (document.version !== 1) return fail("UNSUPPORTED_ENVELOPE_VERSION");
    if (!Number.isInteger(document.revision) || document.revision < 0
            || document.revision > MAX_REVISION) return fail("INVALID_REVISION");
    if (!Array.isArray(document.projects) || document.projects.length > MAX_PROJECTS)
        return fail("INVALID_PROJECT_LIST");
    if (!Array.isArray(document.tasks) || document.tasks.length > MAX_TASKS)
        return fail("INVALID_TASK_LIST");
    if (!Array.isArray(document.operations)
            || document.operations.length > MAX_OPERATIONS)
        return fail("INVALID_OPERATION_LIST");

    var projects = Object.create(null), tasks = Object.create(null);
    for (var i=0;i<document.projects.length;i++) {
        var p=document.projects[i];
        if (!validProject(p) || projects[p.id]) return fail("INVALID_PROJECT");
        projects[p.id]=p;
    }
    for (var j=0;j<document.tasks.length;j++) {
        var t=document.tasks[j];
        if (!validTask(t,projects) || tasks[t.id]) return fail("INVALID_TASK");
        tasks[t.id]=t;
    }

    var seen=Object.create(null), previousRevision=0;
    for (var k=0;k<document.operations.length;k++) {
        var op=document.operations[k];
        if (!plain(op) || !id(op.id,"op") || seen[op.id]
                || !id(op.taskId,"t") || !id(op.projectId,"p")
                || !tasks[op.taskId] || tasks[op.taskId].projectId !== op.projectId
                || !projects[op.projectId] || projects[op.projectId].family !== "git"
                || FIELDS.indexOf(op.field) < 0
                || !validValue(op.field,op.before)
                || !validValue(op.field,op.after)
                || !Number.isInteger(op.createdRevision)
                || op.createdRevision <= previousRevision
                || op.createdRevision > document.revision
                || STATES.indexOf(op.state) < 0
                || !(op.ackToken === null
                    || goodText(op.ackToken,256,true))
                || (op.state === "ACKNOWLEDGED") !== (op.ackToken !== null))
            return fail("INVALID_OPERATION");
        seen[op.id]=true;
        previousRevision=op.createdRevision;
    }
    return {ok:true,reason:""};
}
function create(projects,tasks) {
    var doc={version:1,revision:0,projects:projects,tasks:tasks,operations:[]};
    var result=verify(doc);
    if (!result.ok) return result;
    return {ok:true,reason:"",document:copy(doc)};
}
function encode(document) {
    var checked=verify(document);
    if (!checked.ok) return checked;
    var raw=JSON.stringify(document);
    if (raw.length > MAX_SERIALIZED) return fail("ENVELOPE_TOO_LARGE");
    return {ok:true,reason:"",raw:raw};
}
function decode(raw) {
    if (typeof raw !== "string" || raw.length === 0
            || raw.length > MAX_SERIALIZED) return fail("INVALID_SERIALIZED_ENVELOPE");
    var doc;
    try { doc=JSON.parse(raw); }
    catch (e) { return fail("INVALID_JSON"); }
    var checked=verify(doc);
    if (!checked.ok) return checked;
    return {ok:true,reason:"",document:doc};
}

// For both families, update locally first. GIT edits ALSO append a pending
// intent in the SAME envelope; NORMAL edits generate no remote intent.
// Caller must persist the complete returned envelope before treating the
// edit as saved or allowing a separate transport to perform remote work.
function localEdit(document,request) {
    var check=verify(document);
    if (!check.ok) return check;
    if (!plain(request) || !id(request.taskId,"t")
            || FIELDS.indexOf(request.field) < 0
            || !validValue(request.field,request.value))
        return fail("INVALID_EDIT");
    if (document.revision >= MAX_REVISION)
        return fail("REVISION_EXHAUSTED");
    var next=copy(document), task=null;
    for (var i=0;i<next.tasks.length;i++)
        if (next.tasks[i].id === request.taskId) task=next.tasks[i];
    if (!task) return fail("UNKNOWN_TASK");
    if (task[request.field] === request.value) return fail("NO_CHANGE");
    var project=null;
    for (var p=0;p<next.projects.length;p++)
        if (next.projects[p].id === task.projectId) project=next.projects[p];
    var isGit=project !== null && project.family === "git";
    if (isGit) {
        if (!id(request.operationId,"op")) return fail("OPERATION_ID_REQUIRED");
        for (var n=0;n<next.operations.length;n++)
            if (next.operations[n].id === request.operationId)
                return fail("DUPLICATE_OPERATION_ID");
        if (next.operations.length >= MAX_OPERATIONS)
            return fail("OPERATION_QUEUE_FULL");
    }
    var before=task[request.field];
    next.revision++;
    task[request.field]=request.value;
    if (isGit) next.operations.push({
        id:request.operationId,taskId:task.id,projectId:task.projectId,
        field:request.field,before:before,after:request.value,
        createdRevision:next.revision,state:"PENDING",ackToken:null
    });
    return {ok:true,reason:"",document:next,
            remoteIntentCreated:isGit};
}

// Serial dispatch gate: unresolved UNCERTAIN, CONFLICT, or SENDING work
// blocks later operations. Conservatively use global ordering for M10b.
// A real adapter must do fresh identity, permission, baseline and connectivity
// verification BEFORE any remote write; this function never authorizes one.
function nextIntent(document) {
    var checked=verify(document);
    if (!checked.ok) return checked;
    for (var i=0;i<document.operations.length;i++) {
        var op=document.operations[i];
        if (op.state === "ACKNOWLEDGED") continue;
        if (op.state !== "PENDING")
            return {ok:true,ready:false,reason:op.state+"_BLOCKED",id:op.id};
        return {ok:true,ready:true,reason:"",id:op.id};
    }
    return {ok:true,ready:false,reason:"QUEUE_EMPTY"};
}
function transition(document,operationId,action,ackToken) {
    var checked=verify(document);
    if (!checked.ok) return checked;
    if (document.revision >= MAX_REVISION) return fail("REVISION_EXHAUSTED");
    var next=copy(document), op=null;
    for (var i=0;i<next.operations.length;i++)
        if (next.operations[i].id===operationId) op=next.operations[i];
    if (!op) return fail("UNKNOWN_OPERATION");

    if (action === "begin") {
        var first=nextIntent(document);
        if (!first.ok || !first.ready || first.id!==operationId)
            return fail("DISPATCH_ORDER_BLOCKED");
        if (op.state!=="PENDING") return fail("INVALID_TRANSITION");
        op.state="SENDING";
    } else if (action === "uncertain") {
        if (op.state!=="SENDING") return fail("INVALID_TRANSITION");
        op.state="UNCERTAIN";
    } else if (action === "conflict") {
        if (op.state!=="SENDING" && op.state!=="UNCERTAIN")
            return fail("INVALID_TRANSITION");
        op.state="CONFLICT";
    } else if (action === "acknowledge") {
        if (op.state!=="SENDING" && op.state!=="UNCERTAIN"
                || !goodText(ackToken,256,true))
            return fail("ACK_EVIDENCE_REQUIRED");
        // Only an external verified read-back can legitimately supply this.
        // A string here is an illustrative receipt, NOT verification itself.
        op.state="ACKNOWLEDGED";
        op.ackToken=ackToken;
    } else return fail("INVALID_TRANSITION");
    next.revision++;
    return {ok:true,reason:"",document:next};
}
// After reading a committed envelope from disk, old SENDING states must
// not be retried. Save the recovered envelope before evaluating new work.
function recover(document) {
    var checked=verify(document);
    if (!checked.ok) return checked;
    var next=copy(document), count=0;
    for (var i=0;i<next.operations.length;i++)
        if (next.operations[i].state==="SENDING") {
            next.operations[i].state="UNCERTAIN";
            count++;
        }
    if (count && next.revision>=MAX_REVISION) return fail("REVISION_EXHAUSTED");
    if (count) next.revision++;
    return {ok:true,reason:"",document:next,uncertainCount:count};
}
