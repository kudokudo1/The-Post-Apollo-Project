// HOSPITAL // read-only Room picker display contract.
//
// Identity stays the exact PX Room ID. A successful room-bind on PX v10
// does NOT persist the user's requested name. Only the current Manager
// instance may display that recently requested label, with an explicit
// "NOT SAVED" marker. No write, Team reuse, or implied worker attachment.
function value(s) {
    return String(s === null || s === undefined ? "" : s).trim();
}
function describe(room, recentId, recentName, recentNameSaved) {
    const r = room || {};
    const id = value(r.id || r.roomId);
    const repository = value(r.repository);
    const persisted = value(r.displayName);
    const sameRecent = !!id && id === value(recentId) && !!value(recentName);
    const recent = sameRecent ? value(recentName) : "";
    let title = "";
    let nameStatus = "";
    if (persisted) {
        title = persisted;
        nameStatus = "SAVED ROOM NAME";
    } else if (recent) {
        title = recent;
        nameStatus = recentNameSaved === true
            ? "NAME SAVED // AWAITING REGISTRY REFRESH"
            : "THIS SESSION ONLY // NAME NOT SAVED IN PX";
    } else {
        // A GitHub repo is useful context, but is NOT a Room's display name.
        const repoProject = repository.indexOf("/") >= 0
            ? repository.substring(repository.indexOf("/") + 1)
            : repository;
        title = repoProject
            ? "ROOM IN // " + repoProject
            : "UNNAMED ROOM";
        nameStatus = "NO SAVED ROOM NAME";
    }
    return {
        id: id,
        title: title,
        idLine: "ID // " + (id || "UNREGISTERED"),
        nameStatus: nameStatus,
        repository: repository || "PATIENT NOT VERIFIED",
        hasSavedName: !!persisted,
        hasSessionName: !persisted && !!recent
    };
}
