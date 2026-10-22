.pragma library

// B8: compact, local-only personal notes. Not The Study, Forest, Hospital,
// or an app-wide knowledge database. Only explicit UI actions mutate notes.
var MAX_NOTES = 100;
var MAX_TITLE_LENGTH = 120;
var MAX_BODY_LENGTH = 8192;
var MAX_FILE_LENGTH = 1048576;
var MAX_NEXT_ID = 1000000000;
var MAX_REVISION = 1000000000;
var MAX_PREVIEW_LENGTH = 160;

function emptyDocument() {
    return {version:1, nextId:1, notes:[]};
}

function integerInRange(value, low, high) {
    return typeof value === "number" && isFinite(value)
           && Math.floor(value) === value && value >= low && value <= high;
}

function validTitle(value) {
    return typeof value === "string" && value.length > 0
           && value.length <= MAX_TITLE_LENGTH && value.trim() === value
           && !/[\x00-\x1f\x7f]/.test(value);
}

function inputTitle(value) {
    if (typeof value !== "string") return "";
    var result = value.trim();
    return validTitle(result) ? result : "";
}

function validBody(value) {
    // Multiline notes permit LF and tabs, not embedded control characters.
    return typeof value === "string" && value.length <= MAX_BODY_LENGTH
           && !/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/.test(value);
}

function inputBody(value) {
    if (typeof value !== "string") return null;
    var normalized = value.replace(/\r\n?/g, "\n");
    return validBody(normalized) ? normalized : null;
}

function validNote(note) {
    return !!note && typeof note === "object" && !Array.isArray(note)
        && typeof note.id === "string" && /^n[1-9][0-9]*$/.test(note.id)
        && integerInRange(Number(note.id.slice(1)),1,MAX_NEXT_ID)
        && validTitle(note.title) && validBody(note.body)
        && integerInRange(note.revision,1,MAX_REVISION)
        && integerInRange(note.createdAtMs,1,Number.MAX_SAFE_INTEGER)
        && integerInRange(note.updatedAtMs,note.createdAtMs,Number.MAX_SAFE_INTEGER);
}

function validate(doc) {
    if (!doc || typeof doc !== "object" || Array.isArray(doc))
        return {ok:false,reason:"INVALID_DOCUMENT"};
    if (doc.version !== 1)
        return {ok:false,reason:"UNSUPPORTED_VERSION"};
    if (!integerInRange(doc.nextId,1,MAX_NEXT_ID))
        return {ok:false,reason:"INVALID_SEQUENCE"};
    if (!Array.isArray(doc.notes) || doc.notes.length > MAX_NOTES)
        return {ok:false,reason:"INVALID_NOTES"};
    var seen = {};
    var maxId = 0;
    for (var i=0;i<doc.notes.length;++i) {
        var note = doc.notes[i];
        if (!validNote(note))
            return {ok:false,reason:"INVALID_NOTE"};
        if (Object.prototype.hasOwnProperty.call(seen,note.id))
            return {ok:false,reason:"DUPLICATE_ID"};
        seen[note.id] = true;
        maxId = Math.max(maxId,Number(note.id.slice(1)));
    }
    if (maxId >= doc.nextId)
        return {ok:false,reason:"SEQUENCE_REWIND"};
    return {ok:true,reason:""};
}

function clone(doc) {
    return {version:1,nextId:doc.nextId,notes:doc.notes.map(function(n) {
        return {id:n.id,title:n.title,body:n.body,revision:n.revision,
                createdAtMs:n.createdAtMs,updatedAtMs:n.updatedAtMs};
    })};
}

function parse(raw) {
    if (typeof raw !== "string" || raw.length === 0
            || raw.length > MAX_FILE_LENGTH)
        return {ok:false,reason:"INVALID_FILE"};
    var doc;
    try { doc = JSON.parse(raw); }
    catch (e) { return {ok:false,reason:"INVALID_JSON"}; }
    var check=validate(doc);
    return check.ok ? {ok:true,reason:"",document:clone(doc)} : check;
}

function create(doc,titleValue,bodyValue,nowMs) {
    var check=validate(doc);
    if (!check.ok) return check;
    var title=inputTitle(titleValue);
    var body=inputBody(bodyValue);
    if (!title) return {ok:false,reason:"INVALID_TITLE"};
    if (body === null) return {ok:false,reason:"INVALID_BODY"};
    if (!integerInRange(nowMs,1,Number.MAX_SAFE_INTEGER))
        return {ok:false,reason:"INVALID_TIME"};
    if (doc.notes.length>=MAX_NOTES) return {ok:false,reason:"CAPACITY"};
    if (doc.nextId>=MAX_NEXT_ID) return {ok:false,reason:"ID_EXHAUSTED"};
    var next=clone(doc);
    next.notes.push({id:"n"+next.nextId,title:title,body:body,revision:1,
                     createdAtMs:nowMs,updatedAtMs:nowMs});
    next.nextId++;
    return {ok:true,reason:"",document:next};
}

function update(doc,id,expectedRevision,titleValue,bodyValue,nowMs) {
    var check=validate(doc);
    if (!check.ok) return check;
    if (typeof id !== "string") return {ok:false,reason:"UNKNOWN_ID"};
    var index=doc.notes.findIndex(function(n) { return n.id===id; });
    if (index<0) return {ok:false,reason:"UNKNOWN_ID"};
    var current=doc.notes[index];
    if (!integerInRange(expectedRevision,1,MAX_REVISION)
            || current.revision !== expectedRevision)
        return {ok:false,reason:"STALE_REVISION"};
    var title=inputTitle(titleValue);
    var body=inputBody(bodyValue);
    if (!title) return {ok:false,reason:"INVALID_TITLE"};
    if (body===null) return {ok:false,reason:"INVALID_BODY"};
    if (current.title===title && current.body===body)
        return {ok:false,reason:"NO_CHANGE"};
    if (!integerInRange(nowMs,current.updatedAtMs,Number.MAX_SAFE_INTEGER))
        return {ok:false,reason:"INVALID_TIME"};
    if (current.revision>=MAX_REVISION)
        return {ok:false,reason:"REVISION_EXHAUSTED"};
    var next=clone(doc);
    next.notes[index]={id:current.id,title:title,body:body,
                       revision:current.revision+1,
                       createdAtMs:current.createdAtMs,updatedAtMs:nowMs};
    return {ok:true,reason:"",document:next};
}

function remove(doc,id,expectedRevision,confirmed) {
    var check=validate(doc);
    if (!check.ok) return check;
    if (typeof id !== "string") return {ok:false,reason:"UNKNOWN_ID"};
    var index=doc.notes.findIndex(function(n) { return n.id===id; });
    if (index<0) return {ok:false,reason:"UNKNOWN_ID"};
    if (!integerInRange(expectedRevision,1,MAX_REVISION)
            || doc.notes[index].revision!==expectedRevision)
        return {ok:false,reason:"STALE_REVISION"};
    if (confirmed!==true)
        return {ok:false,reason:"CONFIRM_REQUIRED"};
    var next=clone(doc);
    next.notes.splice(index,1);
    return {ok:true,reason:"",document:next};
}

function displayList(storageState,doc,issue) {
    var allowed=["ready","empty","loading","saving","error","unsupported"];
    var state=allowed.indexOf(storageState)>=0 ? storageState : "error";
    var usable=(state==="ready" || state==="empty" || state==="saving")
               && validate(doc).ok;
    var items=usable ? doc.notes.map(function(n) {
        var preview=n.body.replace(/\s+/g," ").trim().slice(0,MAX_PREVIEW_LENGTH);
        return {id:n.id,title:n.title,preview:preview,revision:n.revision,
                updatedAtMs:n.updatedAtMs};
    }) : [];
    items.sort(function(a,b) {
        return b.updatedAtMs-a.updatedAtMs || b.revision-a.revision
               || a.id.localeCompare(b.id);
    });
    return {
        state:state,
        writable:state==="ready" || state==="empty",
        error:state==="error" || state==="unsupported"
              ? String(issue || "STORAGE_UNAVAILABLE").slice(0,80) : "",
        total:items.length,
        items:items
    };
}

function detail(storageState,doc,id) {
    if ((storageState!=="ready" && storageState!=="empty")
            || !validate(doc).ok || typeof id!=="string")
        return null;
    var note=doc.notes.find(function(n) { return n.id===id; });
    return note ? {id:note.id,title:note.title,body:note.body,
                   revision:note.revision,updatedAtMs:note.updatedAtMs} : null;
}
