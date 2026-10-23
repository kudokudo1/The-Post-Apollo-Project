.pragma library

// PROXY 1 / M10a: read-only compatibility contract for a future unified
// NORMAL/GIT project model. Nothing here writes, migrates, links or syncs.
// A syntactically well-formed GitHub identity is NOT proof of remote existence.

function localId(value, prefix) {
    return typeof value === "string"
        && new RegExp("^" + prefix + "[1-9][0-9]*$").test(value);
}
function cleanName(value) {
    return typeof value === "string"
        && value.length > 0
        && value.length <= 160
        && value === value.trim()
        && !/[\x00-\x1f\x7f]/.test(value);
}
function isGithubProjectReference(value) {
    return value !== null && typeof value === "object"
        && !Array.isArray(value)
        && value.provider === "github"
        && typeof value.owner === "string"
        && /^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$/.test(value.owner)
        && typeof value.projectNodeId === "string"
        && value.projectNodeId.length > 0
        && value.projectNodeId.length <= 200
        && !/\s/.test(value.projectNodeId)
        && Number.isInteger(value.projectNumber)
        && value.projectNumber > 0;
}

// Checks only RECORD SHAPE. The Git-owned service must independently resolve
// each remote ID; titles, project numbers alone, URLs and repo names are NOT
// enough to establish an identity or authorize a write.
function validateProjectCandidate(project) {
    if (!project || typeof project !== "object" || Array.isArray(project)
            || !localId(project.id, "p") || !cleanName(project.name))
        return {ok:false, reason:"INVALID_LOCAL_PROJECT"};
    if (project.family !== "normal" && project.family !== "git")
        return {ok:false, reason:"INVALID_FAMILY"};
    if (project.family === "normal")
        return project.remote === null
            ? {ok:true, reason:"", remoteVerified:false}
            : {ok:false, reason:"NORMAL_CANNOT_HAVE_REMOTE_ID"};
    return isGithubProjectReference(project.remote)
        ? {ok:true, reason:"REMOTE_ID_UNVERIFIED", remoteVerified:false}
        : {ok:false, reason:"MISSING_REMOTE_IDENTITY"};
}

function unavailable(state, reason) {
    return {available:false, state:state, reason:reason, writeReady:false,
            projectCount:0, taskCount:0, projects:[], tasks:[]};
}

// Compatibility projection over the one existing v3 ApolloHubTodoStore
// snapshot. In particular, no title->remote identity matching is attempted.
// Fail closed for unsupported/error/loading states and malformed references.
function previewV3(snapshot) {
    var state = snapshot && typeof snapshot.state === "string"
        ? snapshot.state : "unavailable";
    if (state !== "ready" && state !== "empty" && state !== "saving")
        return unavailable(state, "STORAGE_NOT_READABLE");
    if (!snapshot || !Array.isArray(snapshot.projects)
            || !Array.isArray(snapshot.items))
        return unavailable(state, "INVALID_SNAPSHOT");

    var ids = Object.create(null), taskIds = Object.create(null);
    var projects = [], tasks = [];

    for (var i = 0; i < snapshot.projects.length; i++) {
        var p = snapshot.projects[i];
        if (!p || !localId(p.id, "p") || !cleanName(p.name)
                || ids[p.id])
            return unavailable(state, "INVALID_PROJECTS");
        ids[p.id] = true;
        projects.push({id:p.id, name:p.name, family:"normal",
                       remote:null, linked:false});
    }
    for (var j = 0; j < snapshot.items.length; j++) {
        var t = snapshot.items[j];
        if (!t || !localId(t.id, "t")
                || !cleanName(t.title) || typeof t.done !== "boolean"
                || taskIds[t.id]
                || !(t.projectId === null || t.projectId === undefined
                     || typeof t.projectId === "string" && ids[t.projectId]))
            return unavailable(state, "INVALID_TASKS");
        taskIds[t.id] = true;
        tasks.push({id:t.id, title:t.title, done:t.done,
                    projectId:t.projectId || null});
    }
    return {available:true, state:state, reason:"", writeReady:false,
            projectCount:projects.length, taskCount:tasks.length,
            projects:projects, tasks:tasks};
}
