.pragma library

// TASKS M4: local task v3, read-compatible with established v1/v2 checklists.
// Pure policy. Only ApolloHubTodoStore owns disk writes and saves after a
// deliberate action. Never turn malformed/unknown data into an empty file.
var MAX_TASKS = 200;
var MAX_TITLE = 160;
var MAX_DESCRIPTION = 2000;
var MAX_FILE_LENGTH = 1048576;
var MAX_NEXT_ID = 1000000000;
var MAX_PROJECTS = 30;
var MAX_PROJECT_NAME = 64;
var PRIORITIES = ["none", "low", "medium", "high", "urgent"];

function emptyDocument() {
    return {version: 3, nextId: 1, nextProjectId: 1, projects: [], tasks: []};
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
function validProjectName(value) {
    return typeof value === "string" && value === value.trim()
           && value.length > 0 && value.length <= MAX_PROJECT_NAME
           && !/[\x00-\x1f\x7f]/.test(value);
}
function validProject(p) {
    return p && typeof p === "object" && !Array.isArray(p)
           && typeof p.id === "string" && /^p[1-9][0-9]*$/.test(p.id)
           && isInteger(Number(p.id.slice(1)), 1, MAX_NEXT_ID)
           && validProjectName(p.name)
           && isInteger(p.createdAtMs, 1, Number.MAX_SAFE_INTEGER)
           && isInteger(p.updatedAtMs, p.createdAtMs, Number.MAX_SAFE_INTEGER);
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
               && validDueDate(task.dueDate)
               && (version !== 3 || task.projectId === null
                   || typeof task.projectId === "string"
                   && /^p[1-9][0-9]*$/.test(task.projectId))));
}
function validate(doc) {
    if (!doc || typeof doc !== "object" || Array.isArray(doc))
        return {ok:false, reason:"INVALID_DOCUMENT"};
    if (doc.version !== 1 && doc.version !== 2 && doc.version !== 3)
        return {ok:false, reason:"UNSUPPORTED_VERSION"};
    if (!isInteger(doc.nextId, 1, MAX_NEXT_ID))
        return {ok:false, reason:"INVALID_SEQUENCE"};
    if (!Array.isArray(doc.tasks) || doc.tasks.length > MAX_TASKS)
        return {ok:false, reason:"INVALID_TASK_LIST"};
    var projectIds = {};
    if (doc.version === 3) {
        if (!isInteger(doc.nextProjectId, 1, MAX_NEXT_ID))
            return {ok:false, reason:"INVALID_PROJECT_SEQUENCE"};
        if (!Array.isArray(doc.projects) || doc.projects.length > MAX_PROJECTS)
            return {ok:false, reason:"INVALID_PROJECT_LIST"};
        var seenNames = {};
        var maxPid = 0;
        for (var j = 0; j < doc.projects.length; j++) {
            var project = doc.projects[j];
            if (!validProject(project))
                return {ok:false, reason:"INVALID_PROJECT"};
            if (Object.prototype.hasOwnProperty.call(projectIds, project.id))
                return {ok:false, reason:"DUPLICATE_PROJECT_ID"};
            var key = project.name.toLowerCase();
            if (Object.prototype.hasOwnProperty.call(seenNames, key))
                return {ok:false, reason:"DUPLICATE_PROJECT_NAME"};
            projectIds[project.id] = true;
            seenNames[key] = true;
            maxPid = Math.max(maxPid, Number(project.id.slice(1)));
        }
        if (maxPid >= doc.nextProjectId)
            return {ok:false, reason:"PROJECT_SEQUENCE_REWIND"};
    }
    var ids = {};
    var maxId = 0;
    for (var i = 0; i < doc.tasks.length; ++i) {
        var task = doc.tasks[i];
        if (!validTask(task, doc.version))
            return {ok:false, reason:"INVALID_TASK"};
        if (doc.version === 3 && task.projectId !== null
                && !Object.prototype.hasOwnProperty.call(projectIds, task.projectId))
            return {ok:false, reason:"UNKNOWN_PROJECT_REFERENCE"};
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
    return {version:3, nextId:doc.nextId,
            nextProjectId:doc.version === 3 ? doc.nextProjectId : 1,
            projects:doc.version === 3 ? doc.projects.map(function(project) {
                return {id:project.id, name:project.name,
                        createdAtMs:project.createdAtMs,
                        updatedAtMs:project.updatedAtMs};
            }) : [],
            tasks:doc.tasks.map(function(task) {
                return {id:task.id, title:task.title, done:task.done,
                        createdAtMs:task.createdAtMs, updatedAtMs:task.updatedAtMs,
                        priority:doc.version === 1 ? "none" : task.priority,
                        description:doc.version === 1 ? "" : task.description,
                        dueDate:doc.version === 1 ? null : task.dueDate,
                        projectId:doc.version === 3 ? task.projectId : null};
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
                     priority:"none", description:"", dueDate:null, projectId:null});
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

function createProject(doc, name, nowMs) {
    var valid = validate(doc);
    if (!valid.ok) return {ok:false, reason:valid.reason};
    if (typeof name !== "string" || !validProjectName(name.trim()))
        return {ok:false, reason:"INVALID_PROJECT_NAME"};
    name = name.trim();
    if (!isInteger(nowMs, 1, Number.MAX_SAFE_INTEGER))
        return {ok:false, reason:"INVALID_TIME"};
    var next = clone(doc);
    if (next.projects.length >= MAX_PROJECTS)
        return {ok:false, reason:"PROJECT_CAPACITY"};
    if (next.nextProjectId >= MAX_NEXT_ID)
        return {ok:false, reason:"PROJECT_ID_EXHAUSTED"};
    for (var i=0;i<next.projects.length;i++)
        if (next.projects[i].name.toLowerCase() === name.toLowerCase())
            return {ok:false, reason:"DUPLICATE_PROJECT_NAME"};
    next.projects.push({id:"p"+next.nextProjectId, name:name,
                        createdAtMs:nowMs, updatedAtMs:nowMs});
    next.nextProjectId++;
    return {ok:true, reason:"", document:next};
}

function assignProject(doc, taskId, projectId, nowMs) {
    var valid = validate(doc);
    if (!valid.ok) return {ok:false, reason:valid.reason};
    if (typeof taskId !== "string")
        return {ok:false, reason:"UNKNOWN_ID"};
    var index = doc.tasks.findIndex(function(t) { return t.id === taskId; });
    if (index < 0) return {ok:false, reason:"UNKNOWN_ID"};
    if (projectId !== null
            && (typeof projectId !== "string" || doc.version !== 3
                || !doc.projects.some(function(p) { return p.id === projectId; })))
        return {ok:false, reason:"UNKNOWN_PROJECT"};
    var next = clone(doc);
    if (next.tasks[index].projectId === projectId)
        return {ok:false, reason:"NO_CHANGE"};
    if (!isInteger(nowMs, next.tasks[index].updatedAtMs, Number.MAX_SAFE_INTEGER))
        return {ok:false, reason:"INVALID_TIME"};
    next.tasks[index].projectId = projectId;
    next.tasks[index].updatedAtMs = nowMs;
    return {ok:true, reason:"", document:next};
}

// Project identities never change on rename; task assignments remain linked.
function renameProject(doc, projectId, name, nowMs) {
    var check = validate(doc);
    if (!check.ok) return {ok:false, reason:check.reason};
    if (doc.version !== 3 || typeof projectId !== "string")
        return {ok:false, reason:"UNKNOWN_PROJECT"};
    var index = doc.projects.findIndex(function(p) { return p.id === projectId; });
    if (index < 0) return {ok:false, reason:"UNKNOWN_PROJECT"};
    if (typeof name !== "string" || !validProjectName(name.trim()))
        return {ok:false, reason:"INVALID_PROJECT_NAME"};
    var cleanName = name.trim();
    if (doc.projects[index].name === cleanName)
        return {ok:false, reason:"NO_CHANGE"};
    if (doc.projects.some(function(p) {
        return p.id !== projectId && p.name.toLowerCase() === cleanName.toLowerCase();
    })) return {ok:false, reason:"DUPLICATE_PROJECT_NAME"};
    if (!isInteger(nowMs, doc.projects[index].updatedAtMs, Number.MAX_SAFE_INTEGER))
        return {ok:false, reason:"INVALID_TIME"};
    var next = clone(doc);
    next.projects[index].name = cleanName;
    next.projects[index].updatedAtMs = nowMs;
    return {ok:true, reason:"", document:next};
}

// Delete ONLY the project after a direct YES confirmation.
// Existing tasks are not deleted: each affected task becomes unassigned,
// preserving its ID, status, title, description, priority and due date.
function deleteProject(doc, projectId, nowMs, confirmed) {
    var check = validate(doc);
    if (!check.ok) return {ok:false, reason:check.reason};
    if (doc.version !== 3 || typeof projectId !== "string")
        return {ok:false, reason:"UNKNOWN_PROJECT"};
    var index = doc.projects.findIndex(function(p) { return p.id === projectId; });
    if (index < 0) return {ok:false, reason:"UNKNOWN_PROJECT"};
    if (confirmed !== true)
        return {ok:false, reason:"CONFIRM_REQUIRED"};
    if (!isInteger(nowMs, doc.projects[index].updatedAtMs, Number.MAX_SAFE_INTEGER))
        return {ok:false, reason:"INVALID_TIME"};
    for (var i=0; i<doc.tasks.length; ++i) {
        if (doc.tasks[i].projectId === projectId
                && nowMs < doc.tasks[i].updatedAtMs)
            return {ok:false, reason:"INVALID_TIME"};
    }
    var next = clone(doc);
    next.projects.splice(index, 1);
    for (var j=0; j<next.tasks.length; ++j) {
        if (next.tasks[j].projectId === projectId) {
            next.tasks[j].projectId = null;
            next.tasks[j].updatedAtMs = nowMs;
        }
    }
    // nextProjectId remains monotonically increasing, never reused.
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
                dueDate:task.dueDate, projectId:task.projectId};
    });
    return {
        state:state, writable:state === "ready" || state === "empty",
        error:state === "error" || state === "unsupported"
              ? String(issue || "STORAGE_UNAVAILABLE").slice(0,80) : "",
        total:rows.length, remaining:outstanding.length,
        completed:completed.length, items:rows,
        projects:safe.projects.map(function(p) {
            var members = safe.tasks.filter(function(t) { return t.projectId === p.id; });
            return {id:p.id, name:p.name, total:members.length,
                    remaining:members.filter(function(t) { return !t.done; }).length,
                    completed:members.filter(function(t) { return t.done; }).length};
        })
    };
}
