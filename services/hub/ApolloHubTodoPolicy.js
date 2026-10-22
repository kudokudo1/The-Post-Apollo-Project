.pragma library

// TASKS M4: local task v2, read-compatible with the established v1 checklist.
// Pure policy. Only ApolloHubTodoStore owns disk writes and saves after a
// deliberate action. Never turn malformed/unknown data into an empty file.
var MAX_TASKS = 200;
var MAX_TITLE = 160;
var MAX_DESCRIPTION = 2000;
var MAX_FILE_LENGTH = 1048576;
var MAX_NEXT_ID = 1000000000;
var PRIORITIES = ["none", "low", "medium", "high", "urgent"];

function emptyDocument() {
    return {version: 2, nextId: 1, tasks: []};
}

function isInteger(value, min, max) {
    return typeof value === "number" && isFinite(value)
           && Math.floor(value) === value && value >= min && value <= max;
}

function validTitle(value) {
    return typeof value === "string"
           && value === value.trim()
           && value.length > 0 && value.length <= MAX_TITLE
           && !/[\x00-\x1f\x7f]/.test(value);
}
function titleInput(value) {
    if (typeof value !== "string") return "";
    var title = value.trim();
    return validTitle(title) ? title : "";
}
function validPriority(value) {
    return typeof value === "string" && PRIORITIES.indexOf(value) >= 0;
}
function validDescription(value) {
    return typeof value === "string"
           && value.length <= MAX_DESCRIPTION
           && !/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/.test(value);
}
function validDueDate(value) {
    if (value === null) return true;
    if (typeof value !== "string"
            || !/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(value))
        return false;
    var year = Number(value.slice(0, 4));
    var month = Number(value.slice(5, 7));
    var day = Number(value.slice(8, 10));
    if (year < 1 || month < 1 || month > 12 || day < 1)
        return false;
    var leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
    var monthDays = [31, leap ? 29 : 28, 31, 30, 31, 30,
                     31, 31, 30, 31, 30, 31];
    return day <= monthDays[month - 1];
}

function validTask(task, version) {
    return task && typeof task === "object" && !Array.isArray(task)
           && typeof task.id === "string" && /^t[1-9][0-9]*$/.test(task.id)
           && isInteger(Number(task.id.slice(1)), 1, MAX_NEXT_ID)
           && validTitle(task.title)
           && typeof task.done === "boolean"
           && isInteger(task.createdAtMs, 1, Number.MAX_SAFE_INTEGER)
           && isInteger(task.updatedAtMs, task.createdAtMs, Number.MAX_SAFE_INTEGER)
           && (version === 1 || (validPriority(task.priority)
               && validDescription(task.description)
               && validDueDate(task.dueDate)));
}
function validate(doc) {
    if (!doc || typeof doc !== "object" || Array.isArray(doc))
        return {ok:false, reason:"INVALID_DOCUMENT"};
    if (doc.version !== 1 && doc.version !== 2)
        return {ok:false, reason:"UNSUPPORTED_VERSION"};
    if (!isInteger(doc.nextId, 1, MAX_NEXT_ID))
        return {ok:false, reason:"INVALID_SEQUENCE"};
    if (!Array.isArray(doc.tasks) || doc.tasks.length > MAX_TASKS)
        return {ok:false, reason:"INVALID_TASK_LIST"};
    var ids = {};
    var maxId = 0;
    for (var i = 0; i < doc.tasks.length; ++i) {
        var task = doc.tasks[i];
        if (!validTask(task, doc.version))
            return {ok:false, reason:"INVALID_TASK"};
        if (Object.prototype.hasOwnProperty.call(ids, task.id))
            return {ok:false, reason:"DUPLICATE_ID"};
        ids[task.id] = true;
        maxId = Math.max(maxId, Number(task.id.slice(1)));
    }
    if (maxId >= doc.nextId)
        return {ok:false, reason:"SEQUENCE_REWIND"};
    return {ok:true, reason:""};
}

function clone(doc) {
    // In-memory upgrade only. Unrecognized persisted keys are deliberately
    // removed, not copied into the next disk write.
    return {version:2, nextId:doc.nextId,
            tasks:doc.tasks.map(function(task) {
                return {id:task.id, title:task.title, done:task.done,
                        createdAtMs:task.createdAtMs, updatedAtMs:task.updatedAtMs,
                        priority:doc.version === 1 ? "none" : task.priority,
                        description:doc.version === 1 ? "" : task.description,
                        dueDate:doc.version === 1 ? null : task.dueDate};
            })};
}

function parse(raw) {
    if (typeof raw !== "string" || raw.length === 0
            || raw.length > MAX_FILE_LENGTH)
        return {ok:false, reason:"INVALID_FILE"};
    var data;
    try {
        data = JSON.parse(raw);
    } catch (e) {
        return {ok:false, reason:"INVALID_JSON"};
    }
    var validity = validate(data);
    if (!validity.ok) return validity;
    return {ok:true, reason:"", document:clone(data)};
}

function create(doc, value, nowMs) {
    var check = validate(doc);
    var title = titleInput(value);
    if (!check.ok) return {ok:false, reason:check.reason};
    if (!title) return {ok:false, reason:"INVALID_TITLE"};
    if (!isInteger(nowMs, 1, Number.MAX_SAFE_INTEGER))
        return {ok:false, reason:"INVALID_TIME"};
    if (doc.tasks.length >= MAX_TASKS) return {ok:false, reason:"CAPACITY"};
    if (doc.nextId >= MAX_NEXT_ID) return {ok:false, reason:"ID_EXHAUSTED"};
    var next = clone(doc);
    next.tasks.push({id:"t" + next.nextId, title:title, done:false,
                     createdAtMs:nowMs, updatedAtMs:nowMs,
                     priority:"none", description:"", dueDate:null});
    next.nextId++;
    return {ok:true, reason:"", document:next};
}

function update(doc, id, change, value, nowMs, confirmed) {
    var check = validate(doc);
    if (!check.ok) return {ok:false, reason:check.reason};
    if (typeof id !== "string") return {ok:false, reason:"UNKNOWN_ID"};
    var index = doc.tasks.findIndex(function(task) { return task.id === id; });
    if (index < 0) return {ok:false, reason:"UNKNOWN_ID"};
    var previous = doc.tasks[index];
    var next = clone(doc);
    var task = next.tasks[index];
    if (change === "done") {
        if (typeof value !== "boolean") return {ok:false, reason:"INVALID_DONE"};
        if (previous.done === value) return {ok:false, reason:"NO_CHANGE"};
        task.done = value;
    } else if (change === "rename") {
        var title = titleInput(value);
        if (!title) return {ok:false, reason:"INVALID_TITLE"};
        if (title === previous.title) return {ok:false, reason:"NO_CHANGE"};
        task.title = title;
    } else if (change === "delete") {
        if (confirmed !== true) return {ok:false, reason:"CONFIRM_REQUIRED"};
        next.tasks.splice(index, 1);
        return {ok:true, reason:"", document:next};
    } else {
        return {ok:false, reason:"INVALID_ACTION"};
    }
    if (!isInteger(nowMs, previous.updatedAtMs, Number.MAX_SAFE_INTEGER))
        return {ok:false, reason:"INVALID_TIME"};
    task.updatedAtMs = nowMs;
    return {ok:true, reason:"", document:next};
}

function updateDetails(doc, id, priority, description, dueDate, nowMs) {
    var check = validate(doc);
    if (!check.ok) return {ok:false, reason:check.reason};
    if (typeof id !== "string") return {ok:false, reason:"UNKNOWN_ID"};
    var index = doc.tasks.findIndex(function(task) { return task.id === id; });
    if (index < 0) return {ok:false, reason:"UNKNOWN_ID"};
    if (!validPriority(priority)) return {ok:false, reason:"INVALID_PRIORITY"};
    if (!validDescription(description))
        return {ok:false, reason:"INVALID_DESCRIPTION"};
    if (!validDueDate(dueDate)) return {ok:false, reason:"INVALID_DUE_DATE"};
    var next = clone(doc);
    var task = next.tasks[index];
    if (task.priority === priority && task.description === description
            && task.dueDate === dueDate)
        return {ok:false, reason:"NO_CHANGE"};
    if (!isInteger(nowMs, task.updatedAtMs, Number.MAX_SAFE_INTEGER))
        return {ok:false, reason:"INVALID_TIME"};
    task.priority = priority;
    task.description = description;
    task.dueDate = dueDate;
    task.updatedAtMs = nowMs;
    return {ok:true, reason:"", document:next};
}

function view(storageState, doc, issue) {
    var state = storageState === "ready" || storageState === "empty"
        || storageState === "loading" || storageState === "saving"
        || storageState === "error" || storageState === "unsupported"
        ? storageState : "error";
    var available = (state === "ready" || state === "empty"
                     || state === "saving") && validate(doc).ok;
    var safe = available ? clone(doc) : emptyDocument();
    var outstanding = safe.tasks.filter(function(task) { return !task.done; });
    var completed = safe.tasks.filter(function(task) { return task.done; });
    var rows = outstanding.concat(completed).map(function(task) {
        return {id:task.id, title:task.title, done:task.done,
                priority:task.priority, description:task.description,
                dueDate:task.dueDate};
    });
    return {
        state:state, writable:state === "ready" || state === "empty",
        error:state === "error" || state === "unsupported"
              ? String(issue || "STORAGE_UNAVAILABLE").slice(0,80) : "",
        total:rows.length, remaining:outstanding.length,
        completed:completed.length, items:rows
    };
}
