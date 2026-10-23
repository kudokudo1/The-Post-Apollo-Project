.pragma library

// Proxy 1 M10h: strict, in-memory *candidate* schema v2 for NORMAL/GIT
// projects and typed LOCAL-ONLY fields. This is not Todo v4, not a writer,
// not a GitHub identity verifier, and not a network/sync executor.
var VERSION=2;
var MAX_BYTES=1048576;
var MAX_REVISION=1000000000;
var PROJECT_FIELDS=["id","name","createdAtMs","updatedAtMs","family","remote","fields"];
var TASK_FIELDS=["id","title","done","createdAtMs","updatedAtMs","priority",
                 "description","dueDate","projectId","remote","values"];
var ENVELOPE_FIELDS=["version","revision","nextId","nextProjectId","nextOperationId",
                     "projects","tasks","operations"];
var OP_FIELDS=["id","taskId","projectId","field","before","after",
               "createdRevision","state","ackToken"];
var REMOTE_PROJECT_FIELDS=["provider","owner","projectNodeId","projectNumber"];
var REMOTE_ITEM_FIELDS=["projectItemNodeId","contentKind","contentNodeId"];
var CUSTOM_FIELD_FIELDS=["id","label","kind","scope"];
var PRIORITIES=["none","low","medium","high","urgent"];
var TASK_EDIT_FIELDS=["title","done","priority","description","dueDate"];
var OP_STATES=["PENDING","SENDING","UNCERTAIN","CONFLICT","ACKNOWLEDGED"];
var FIELD_KINDS=["text","number","boolean","date"];

function fail(reason) { return {ok:false,reason:reason,writeReady:false}; }
function obj(x) { return x!==null && typeof x==="object" && !Array.isArray(x); }
function keys(x,expected) {
    if(!obj(x) || Object.keys(x).length!==expected.length) return false;
    for(var i=0;i<expected.length;i++)
        if(!Object.prototype.hasOwnProperty.call(x,expected[i])) return false;
    return true;
}
function integer(x,low,high) {
    return Number.isSafeInteger(x) && x>=low && x<=high;
}
function identifier(x,prefix) {
    return typeof x==="string"
        && new RegExp("^"+prefix+"([1-9][0-9]*)$").test(x)
        && x.length<=15 && integer(Number(x.slice(prefix.length)),1,MAX_REVISION);
}
function text(x,max,required) {
    return typeof x==="string" && x.length<=max
        && (!required || (x.length>0 && x===x.trim()))
        && !/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/.test(x);
}
function date(x) {
    if(x===null) return true;
    if(typeof x!=="string" || !/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(x))
        return false;
    var y=Number(x.slice(0,4)),m=Number(x.slice(5,7)),d=Number(x.slice(8,10));
    if(y<1 || m<1 || m>12 || d<1) return false;
    var leap=y%4===0 && (y%100!==0 || y%400===0);
    var days=[31,leap?29:28,31,30,31,30,31,31,30,31,30,31];
    return d<=days[m-1];
}
function value(kind,v) {
    if(v===null) return true;
    if(kind==="text") return text(v,2000,false);
    if(kind==="number") return typeof v==="number" && Number.isFinite(v)
         && Math.abs(v)<=1000000000000;
    if(kind==="boolean") return typeof v==="boolean";
    if(kind==="date") return date(v);
    return false;
}
function taskValue(field,v) {
    if(field==="title") return text(v,160,true);
    if(field==="done") return typeof v==="boolean";
    if(field==="priority") return PRIORITIES.indexOf(v)!==-1;
    if(field==="description") return text(v,2000,false);
    if(field==="dueDate") return date(v);
    return false;
}
function validRemoteProject(x) {
    return keys(x,REMOTE_PROJECT_FIELDS)
        && x.provider==="github" && text(x.owner,39,true)
        && /^[A-Za-z0-9][A-Za-z0-9-]*$/.test(x.owner)
        && text(x.projectNodeId,200,true) && !/\s/.test(x.projectNodeId)
        && integer(x.projectNumber,1,MAX_REVISION);
}
function validRemoteItem(x) {
    return keys(x,REMOTE_ITEM_FIELDS)
        && text(x.projectItemNodeId,200,true)
        && !/\s/.test(x.projectItemNodeId)
        && ["ISSUE","PULL_REQUEST","DRAFT_ISSUE"].indexOf(x.contentKind)!==-1
        && (x.contentNodeId===null || (text(x.contentNodeId,200,true)
                                       && !/\s/.test(x.contentNodeId)))
        && (x.contentKind==="DRAFT_ISSUE" || x.contentNodeId!==null);
}
function verify(document) {
    if(!obj(document)) return fail("INVALID_ENVELOPE");
    if(document.version!==VERSION) return fail("UNSUPPORTED_SCHEMA_VERSION");
    if(!keys(document,ENVELOPE_FIELDS)) return fail("UNKNOWN_ENVELOPE_FIELD");
    if(!integer(document.revision,0,MAX_REVISION)
        || !integer(document.nextId,1,MAX_REVISION)
        || !integer(document.nextProjectId,1,MAX_REVISION)
        || !integer(document.nextOperationId,1,MAX_REVISION))
        return fail("INVALID_COUNTER");
    if(!Array.isArray(document.projects) || document.projects.length>30
        || !Array.isArray(document.tasks) || document.tasks.length>200
        || !Array.isArray(document.operations) || document.operations.length>1000)
        return fail("INVALID_LISTS");

    var projects=Object.create(null), tasks=Object.create(null),
        maxP=0,maxT=0,maxO=0, fieldDefs=Object.create(null), names=Object.create(null);
    for(var i=0;i<document.projects.length;i++) {
        var p=document.projects[i];
        if(!keys(p,PROJECT_FIELDS) || !identifier(p.id,"p")
            || !text(p.name,64,true) || projects[p.id]
            || !(p.family==="normal" || p.family==="git")
            || !integer(p.createdAtMs,1,Number.MAX_SAFE_INTEGER)
            || !integer(p.updatedAtMs,p.createdAtMs,Number.MAX_SAFE_INTEGER))
            return fail("INVALID_PROJECT");
        var lower=p.name.toLowerCase();
        if(names[lower]) return fail("DUPLICATE_PROJECT_NAME");
        names[lower]=true;
        if(p.family==="normal" ? p.remote!==null : !validRemoteProject(p.remote))
            return fail("INVALID_REMOTE_PROJECT_SHAPE");
        if(!Array.isArray(p.fields) || p.fields.length>24)
            return fail("INVALID_FIELD_DEFINITIONS");
        var definitions=Object.create(null), labels=Object.create(null);
        for(var j=0;j<p.fields.length;j++) {
            var f=p.fields[j];
            if(!keys(f,CUSTOM_FIELD_FIELDS) || !identifier(f.id,"f")
                || !text(f.label,64,true) || definitions[f.id]
                || FIELD_KINDS.indexOf(f.kind)<0 || f.scope!=="local")
                return fail("INVALID_FIELD_DEFINITION");
            var label=f.label.toLowerCase();
            if(labels[label]) return fail("DUPLICATE_FIELD_LABEL");
            labels[label]=true;
            definitions[f.id]=f.kind;
        }
        projects[p.id]=p;
        fieldDefs[p.id]=definitions;
        maxP=Math.max(maxP,Number(p.id.slice(1)));
    }
    if(maxP>=document.nextProjectId) return fail("PROJECT_COUNTER_REWIND");
    for(var k=0;k<document.tasks.length;k++) {
        var t=document.tasks[k];
        if(!keys(t,TASK_FIELDS) || !identifier(t.id,"t") || tasks[t.id]
            || !integer(t.createdAtMs,1,Number.MAX_SAFE_INTEGER)
            || !integer(t.updatedAtMs,t.createdAtMs,Number.MAX_SAFE_INTEGER)
            || !(t.projectId===null || typeof t.projectId==="string" && projects[t.projectId]))
            return fail("INVALID_TASK");
        for(var fIndex=0;fIndex<TASK_EDIT_FIELDS.length;fIndex++) {
            var field=TASK_EDIT_FIELDS[fIndex];
            if(!taskValue(field,t[field])) return fail("INVALID_TASK_FIELD");
        }
        if(t.remote!==null && (!t.projectId
            || projects[t.projectId].family!=="git" || !validRemoteItem(t.remote)))
            return fail("INVALID_REMOTE_ITEM_SHAPE");
        if(!obj(t.values) || Object.keys(t.values).length>24)
            return fail("INVALID_CUSTOM_VALUES");
        var entries=Object.keys(t.values), definitionsForTask=t.projectId
            ? fieldDefs[t.projectId]:null;
        for(var e=0;e<entries.length;e++) {
            var fid=entries[e], kind=definitionsForTask && definitionsForTask[fid];
            if(!kind || !value(kind,t.values[fid]))
                return fail("INVALID_CUSTOM_VALUE");
        }
        tasks[t.id]=t;
        maxT=Math.max(maxT,Number(t.id.slice(1)));
    }
    if(maxT>=document.nextId) return fail("TASK_COUNTER_REWIND");
    var seenOps=Object.create(null),previousRevision=0;
    for(var n=0;n<document.operations.length;n++) {
        var op=document.operations[n];
        if(!keys(op,OP_FIELDS) || !identifier(op.id,"op") || seenOps[op.id]
            || !tasks[op.taskId] || !projects[op.projectId]
            || tasks[op.taskId].projectId!==op.projectId
            || projects[op.projectId].family!=="git"
            || TASK_EDIT_FIELDS.indexOf(op.field)<0
            || !taskValue(op.field,op.before) || !taskValue(op.field,op.after)
            || op.before===op.after
            || !integer(op.createdRevision,1,document.revision)
            || op.createdRevision<=previousRevision || OP_STATES.indexOf(op.state)<0
            || !(op.ackToken===null || text(op.ackToken,256,true))
            || ((op.state==="ACKNOWLEDGED")!==(op.ackToken!==null)))
            return fail("INVALID_OPERATION");
        previousRevision=op.createdRevision;
        seenOps[op.id]=true;
        maxO=Math.max(maxO,Number(op.id.slice(2)));
    }
    if(maxO>=document.nextOperationId) return fail("OPERATION_COUNTER_REWIND");
    return {ok:true,reason:"",writeReady:false};
}
function clone(x) { return JSON.parse(JSON.stringify(x)); }
function empty() {
    return {version:VERSION,revision:0,nextId:1,nextProjectId:1,
            nextOperationId:1,projects:[],tasks:[],operations:[]};
}
function encode(document) {
    var check=verify(document);
    if(!check.ok) return check;
    var raw=JSON.stringify(document);
    if(raw.length>MAX_BYTES) return fail("DOCUMENT_TOO_LARGE");
    return {ok:true,reason:"",writeReady:false,raw:raw};
}
// A valid JSON text still may contain two members with the same decoded key.
// Reject duplicates before parsing to prevent silent loss from JSON.parse.
// Parser intentionally bounds nesting. This is only a duplicate-key scanner;
// JSON.parse remains the syntax validator.
function hasDuplicateKeys(raw) {
    var pos=0,deep=0,duplicates=false;
    function whitespace() { while(/\s/.test(raw.charAt(pos)) && pos<raw.length) pos++; }
    function stringToken() {
        var start=pos++;
        while(pos<raw.length) {
            var c=raw.charAt(pos++);
            if(c==="\\") { pos++; continue; }
            if(c==='"') return JSON.parse(raw.slice(start,pos));
        }
        throw Error("UNTERMINATED_STRING");
    }
    function scan() {
        whitespace();
        if(++deep>48) throw Error("EXCESSIVE_NESTING");
        var c=raw.charAt(pos);
        if(c==="{") {
            pos++; whitespace();
            var seen=Object.create(null);
            if(raw.charAt(pos)==="}") pos++;
            else while(pos<raw.length) {
                whitespace();
                var key=stringToken(); whitespace();
                if(seen[key]) duplicates=true;
                seen[key]=true;
                if(raw.charAt(pos++)!==":") throw Error("INVALID_COLON");
                scan(); whitespace();
                var delimiter=raw.charAt(pos++);
                if(delimiter==="}") break;
                if(delimiter!==",") throw Error("INVALID_OBJECT");
            }
        } else if(c==="[") {
            pos++; whitespace();
            if(raw.charAt(pos)==="]") pos++;
            else while(pos<raw.length) {
                scan(); whitespace();
                var next=raw.charAt(pos++);
                if(next==="]") break;
                if(next!==",") throw Error("INVALID_ARRAY");
            }
        } else if(c==='"') {
            stringToken();
        } else {
            // Syntax already validated by JSON.parse. Consume primitives.
            while(pos<raw.length && !/[\s,\]\}]/.test(raw.charAt(pos))) pos++;
        }
        deep--;
    }
    scan(); whitespace();
    if(pos!==raw.length) throw Error("TRAILING_CONTENT");
    return duplicates;
}
function decode(raw) {
    if(typeof raw!=="string" || raw.length===0 || raw.length>MAX_BYTES)
        return fail("INVALID_FILE");
    var doc;
    try { doc=JSON.parse(raw); }
    catch(e) { return fail("INVALID_JSON"); }
    try { if(hasDuplicateKeys(raw)) return fail("DUPLICATE_JSON_KEY"); }
    catch(e) { return fail("INVALID_OR_DEEPLY_NESTED_JSON"); }
    var check=verify(doc);
    if(!check.ok) return check;
    return {ok:true,reason:"",writeReady:false,document:doc};
}
// Explicit baseline-only upgrade. Never infer GIT identity from name.
// Refuses old candidates carrying remote changes or unexpected keys.
// M10b remains separately supported for its own prior tests.
function upgradeBaselineV1(oldDocument,oldPolicy) {
    if(!oldPolicy || typeof oldPolicy.verify!=="function")
        return fail("MISSING_V1_POLICY");
    var original=oldPolicy.verify(oldDocument);
    if(!original.ok) return fail("INVALID_V1_"+original.reason);
    if(oldDocument.revision!==0 || oldDocument.operations.length!==0
        || !keys(oldDocument,["version","revision","nextId","nextProjectId",
                             "projects","tasks","operations"]))
        return fail("NOT_BASELINE_V1");
    var out=empty();
    out.nextId=oldDocument.nextId;
    out.nextProjectId=oldDocument.nextProjectId;
    for(var i=0;i<oldDocument.projects.length;i++) {
        var p=oldDocument.projects[i];
        if(!keys(p,["id","name","createdAtMs","updatedAtMs","family","remote"])
            || p.family!=="normal" || p.remote!==null)
            return fail("UNSUPPORTED_V1_PROJECT");
        out.projects.push({id:p.id,name:p.name,createdAtMs:p.createdAtMs,
            updatedAtMs:p.updatedAtMs,family:"normal",remote:null,fields:[]});
    }
    for(var j=0;j<oldDocument.tasks.length;j++) {
        var t=oldDocument.tasks[j];
        if(!keys(t,["id","title","done","createdAtMs","updatedAtMs","priority",
                    "description","dueDate","projectId"]))
            return fail("UNSUPPORTED_V1_TASK");
        var next=clone(t);
        next.remote=null;
        next.values={};
        out.tasks.push(next);
    }
    var valid=verify(out);
    return valid.ok?{ok:true,reason:"",writeReady:false,document:out}:valid;
}
function editTask(document,request) {
    var valid=verify(document);
    if(!valid.ok) return valid;
    if(!obj(request) || !identifier(request.taskId,"t")
        || TASK_EDIT_FIELDS.indexOf(request.field)<0
        || !taskValue(request.field,request.value)
        || !integer(request.nowMs,1,Number.MAX_SAFE_INTEGER))
        return fail("INVALID_EDIT");
    if(document.revision>=MAX_REVISION) return fail("REVISION_EXHAUSTED");
    var next=clone(document), task=null, project=null;
    for(var i=0;i<next.tasks.length;i++)
        if(next.tasks[i].id===request.taskId) task=next.tasks[i];
    if(!task) return fail("UNKNOWN_TASK");
    if(task[request.field]===request.value) return fail("NO_CHANGE");
    if(request.nowMs<task.updatedAtMs || task.updatedAtMs>=Number.MAX_SAFE_INTEGER)
        return fail("STALE_EDIT_TIME");
    for(var j=0;j<next.projects.length;j++)
        if(next.projects[j].id===task.projectId) project=next.projects[j];
    var isGit=project!==null && project.family==="git";
    // GIT edits queue an intent even when remote task identity is not yet
    // verified, but no transport is ever permitted by this policy.
    if(isGit && (next.operations.length>=1000
        || next.nextOperationId>=MAX_REVISION))
        return fail("OPERATION_QUEUE_FULL");
    var before=task[request.field];
    task[request.field]=request.value;
    task.updatedAtMs=Math.max(request.nowMs,task.updatedAtMs+1);
    next.revision++;
    if(isGit) {
        var id="op"+next.nextOperationId++;
        next.operations.push({id:id,taskId:task.id,projectId:task.projectId,
            field:request.field,before:before,after:request.value,
            createdRevision:next.revision,state:"PENDING",ackToken:null});
    }
    var check=verify(next);
    if(!check.ok) return check;
    return {ok:true,reason:"",writeReady:false,
            remoteIntentCreated:isGit,remoteWriteAuthorized:false,
            document:next};
}
// Custom fields are LOCAL ONLY, even for a GIT project. No remote intent.
function editCustomValue(document,request) {
    var valid=verify(document);
    if(!valid.ok) return valid;
    if(!obj(request) || !identifier(request.taskId,"t")
        || !identifier(request.fieldId,"f")
        || !integer(request.nowMs,1,Number.MAX_SAFE_INTEGER))
        return fail("INVALID_CUSTOM_EDIT");
    if(document.revision>=MAX_REVISION) return fail("REVISION_EXHAUSTED");
    var next=clone(document),task=null,project=null;
    for(var i=0;i<next.tasks.length;i++)
        if(next.tasks[i].id===request.taskId) task=next.tasks[i];
    if(!task) return fail("UNKNOWN_TASK");
    for(var j=0;j<next.projects.length;j++)
        if(next.projects[j].id===task.projectId) project=next.projects[j];
    if(!project) return fail("NO_PROJECT_FOR_CUSTOM_VALUE");
    var def=null;
    for(var k=0;k<project.fields.length;k++)
        if(project.fields[k].id===request.fieldId) def=project.fields[k];
    if(!def) return fail("UNKNOWN_CUSTOM_FIELD");
    if(!value(def.kind,request.value)) return fail("INVALID_CUSTOM_VALUE");
    if(Object.prototype.hasOwnProperty.call(task.values,request.fieldId)
        && task.values[request.fieldId]===request.value) return fail("NO_CHANGE");
    if(request.nowMs<task.updatedAtMs || task.updatedAtMs>=Number.MAX_SAFE_INTEGER)
        return fail("STALE_EDIT_TIME");
    task.values[request.fieldId]=request.value;
    task.updatedAtMs=Math.max(request.nowMs,task.updatedAtMs+1);
    next.revision++;
    var checked=verify(next);
    if(!checked.ok) return checked;
    return {ok:true,reason:"",writeReady:false,
        remoteIntentCreated:false,remoteWriteAuthorized:false,document:next};
}
