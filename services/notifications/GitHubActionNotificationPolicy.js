.pragma library

// Existing gh mutationFinished results, not polls or pending UI state.
// Do not announce an issue or review-thread action as VERIFIED merely
// because its process exited successfully.
function repo(value) {
    const text = String(value || "").trim();
    return /^[^/\s]+\/[^/\s]+$/.test(text) ? text : "";
}
function number(value) {
    const num = Number(value || 0);
    return isFinite(num) && Math.floor(num) === num && num > 0 ? num : 0;
}
function issue(succeeded, verified, operation, evidence, fallbackRepo, fallbackNumber) {
    const action = String(operation || "").toLowerCase().trim();
    if (["create", "edit", "comment", "close", "reopen", "labels", "assignees"].indexOf(action) < 0)
        return null;
    const row = evidence || {};
    const issue = row.issue || {};
    const repository = repo(row.repository || fallbackRepo);
    const id = number(issue.number || fallbackNumber);
    if (!repository)
        return null;
    const state = String(issue.state || "").toUpperCase();
    const expected = action === "close" ? "CLOSED"
                   : action === "create" || action === "reopen" ? "OPEN" : "";
    // IssueService's generic evidence flag proves that the issue exists,
    // not that an edit, comment, label or assignment was applied. Only
    // actions with an independently checked target state may say VERIFIED.
    const confirmed = succeeded === true && verified === true
        && ["create", "close", "reopen"].indexOf(action) >= 0
        && id > 0 && String(issue.url || "").length > 0
        && state === expected;
    const result = succeeded === true
        ? confirmed ? "VERIFIED" : "UNVERIFIED"
        : "FAILED";
    return { repository: repository, number: id, action: action,
             outcome: result, type: "issue" };
}
function review(succeeded, verified, operation, evidence, fallbackRepo, fallbackNumber) {
    const action = String(operation || "").toLowerCase().trim();
    if (["reply", "resolve", "unresolve"].indexOf(action) < 0)
        return null;
    const row = evidence || {};
    const repository = repo(row.repository || fallbackRepo);
    const numberValue = number(fallbackNumber);
    if (!repository || !numberValue)
        return null;
    const thread = row.thread || {};
    const desired = action === "resolve" ? true
                  : action === "unresolve" ? false : null;
    const confirmed = succeeded === true && verified === true
        && String(thread.id || "") !== ""
        && (desired === null
            ? String(row.createdReplyNodeId || "") !== ""
            : thread.isResolved === desired);
    return { repository: repository, number: numberValue, action: action,
             outcome: succeeded === true
                      ? confirmed ? "VERIFIED" : "UNVERIFIED" : "FAILED",
             type: "review" };
}
