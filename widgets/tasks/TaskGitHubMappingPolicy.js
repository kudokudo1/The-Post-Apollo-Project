.pragma library

// TASKS -> GitHub Projects: local-only compatibility / identity preview.
// This policy does not link by title, project number, or matching field name.
// Remote ProjectV2, Item, Field and Option IDs must be verified separately
// through the Git-owned GitHubProjectsService before any future writes.

var FIELD_CONTRACT = [
    {local:"priority", remoteKind:"SINGLE_SELECT", remoteCandidate:"PRIORITY",
     readiness:"NEEDS_FIELD_AND_OPTION_IDS"},
    {local:"dueDate", remoteKind:"DATE", remoteCandidate:"TARGET DATE",
     readiness:"NEEDS_DATE_FIELD_ID"},
    {local:"done", remoteKind:"SINGLE_SELECT", remoteCandidate:"STATUS",
     readiness:"NEEDS_EXPLICIT_STATUS_SEMANTICS"},
    {local:"description", remoteKind:"DRAFT_BODY", remoteCandidate:"DRAFT BODY",
     readiness:"NEEDS_CONTENT_TYPE_AND_ID"}
];

function preview(snapshot) {
    var state = snapshot && typeof snapshot.state === "string"
              ? snapshot.state : "unavailable";
    var available = state === "ready" || state === "empty"
                    || state === "saving";
    if (!available || !snapshot
            || !Array.isArray(snapshot.projects)
            || !Array.isArray(snapshot.items)) {
        return {available:false, state:state, localProjects:0,
                localTasks:0, tasksWithPriority:0, tasksWithDate:0,
                tasksWithDescription:0, tasksDone:0, writeReady:0,
                projectRows:[], taskRows:[], fieldRows:FIELD_CONTRACT};
    }

    var projectRows = [];
    var taskRows = [];
    var withPriority = 0, withDate = 0, withDescription = 0, doneCount = 0;
    snapshot.projects.forEach(function(p) {
        if (!p || typeof p.id !== "string" || typeof p.name !== "string")
            return;
        projectRows.push({id:p.id, title:p.name,
                          total:typeof p.total === "number" ? p.total : 0,
                          linkage:"NEEDS_VERIFIED_REMOTE_PROJECT_ID"});
    });
    snapshot.items.forEach(function(t) {
        if (!t || typeof t.id !== "string" || typeof t.title !== "string")
            return;
        var priority = typeof t.priority === "string" ? t.priority : "none";
        var due = typeof t.dueDate === "string" ? t.dueDate : "";
        var hasDescription = typeof t.description === "string"
                             && t.description.length > 0;
        if (priority !== "none") withPriority++;
        if (due.length > 0) withDate++;
        if (hasDescription) withDescription++;
        if (t.done === true) doneCount++;
        // Do not leak local description/body text or fabricate remote IDs.
        taskRows.push({id:t.id, title:t.title, priority:priority,
                       dueDate:due, projectId:t.projectId || null,
                       linkage:"NEEDS_VERIFIED_REMOTE_ITEM_ID"});
    });

    return {available:true, state:state,
            localProjects:projectRows.length, localTasks:taskRows.length,
            tasksWithPriority:withPriority, tasksWithDate:withDate,
            tasksWithDescription:withDescription, tasksDone:doneCount,
            writeReady:0, projectRows:projectRows,
            taskRows:taskRows, fieldRows:FIELD_CONTRACT};
}
