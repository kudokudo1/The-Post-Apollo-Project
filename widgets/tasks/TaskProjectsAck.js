.pragma library

// Use ONE received snapshot when reconciling a PROJECTS write.
// QML's derived storeState/projects/tasks properties can be reevaluated
// in separate turns and must not be mixed in a single acknowledgement.
function status(snapshot, kind, projectId, projectName, taskId,
                targetProjectId, expectedTaskCount) {
    if (!snapshot || typeof snapshot.state !== "string")
        return "waiting";
    if (snapshot.state === "error" || snapshot.state === "unsupported")
        return "failed";
    if (snapshot.state === "saving" || snapshot.state === "loading")
        return "waiting";
    if (snapshot.state !== "ready" && snapshot.state !== "empty")
        return "failed";
    if (!Array.isArray(snapshot.projects) || !Array.isArray(snapshot.items))
        return "unconfirmed";

    var projects = snapshot.projects;
    var tasks = snapshot.items;
    var i, project, task;
    if (kind === "create") {
        for (i = 0; i < projects.length; i++) {
            project = projects[i];
            if (project && project.name === projectName)
                return "confirmed";
        }
    } else if (kind === "rename") {
        for (i = 0; i < projects.length; i++) {
            project = projects[i];
            if (project && project.id === projectId
                    && project.name === projectName)
                return "confirmed";
        }
    } else if (kind === "assign") {
        for (i = 0; i < tasks.length; i++) {
            task = tasks[i];
            if (task && task.id === taskId
                    && task.projectId === targetProjectId)
                return "confirmed";
        }
    } else if (kind === "delete") {
        if (tasks.length !== expectedTaskCount)
            return "unconfirmed";
        for (i = 0; i < projects.length; i++)
            if (projects[i] && projects[i].id === projectId)
                return "unconfirmed";
        for (i = 0; i < tasks.length; i++)
            if (tasks[i] && tasks[i].projectId === projectId)
                return "unconfirmed";
        return "confirmed";
    }
    // The store is no longer saving but the expected result was not
    // demonstrated by the snapshot. Unlock the UI without claiming SAVED.
    return "unconfirmed";
}
