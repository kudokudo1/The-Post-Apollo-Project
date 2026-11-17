// HOSPITAL // Read-only PX assignment visibility groups.
// A saved ACTIVE Assignment is work on record, never a live AI heartbeat.
// Unclosed WAITING sessions, Doctors and Git branches alone never qualify.
function rosterText(value) {
    return String(value === undefined || value === null ? "" : value).trim();
}

function category(roomValue) {
    const room = roomValue || {};
    const assignment = rosterText(room.assignmentId);
    const status = rosterText(room.assignmentStatus).toUpperCase();
    if (assignment && status === "ACTIVE")
        return "ACTIVE";
    if (assignment && status !== "COMPLETE" && status !== "CANCELLED")
        return "STAGED";
    return "HISTORY";
}

function counts(rows) {
    const out = {ACTIVE: 0, STAGED: 0, HISTORY: 0, ALL: 0};
    const list = Array.isArray(rows) ? rows : [];
    for (let i = 0; i < list.length; ++i) {
        out[category(list[i])] += 1;
        out.ALL += 1;
    }
    return out;
}

function filter(rows, viewValue) {
    const list = Array.isArray(rows) ? rows : [];
    const view = rosterText(viewValue).toUpperCase();
    if (view === "ALL")
        return list.slice();
    const selected = view === "STAGED" || view === "HISTORY" ? view : "ACTIVE";
    return list.filter(function(row) {
        return category(row) === selected;
    });
}
