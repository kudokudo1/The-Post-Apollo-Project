// HOSPITAL // Room GitHub owner selection from the existing Git account and
// registered Patients. This is display suggestion only, not authorization.
function part(value) {
    const s = String(value === null || value === undefined ? "" : value).trim();
    return /^[A-Za-z0-9_.-]+$/.test(s) ? s : "";
}
function splitRepository(value) {
    const s = String(value === null || value === undefined ? "" : value).trim();
    const match = /^([A-Za-z0-9_.-]+)\/([A-Za-z0-9_.-]+)$/.exec(s);
    return match ? {owner: match[1], repository: match[2]} :
        {owner: "", repository: ""};
}
function compose(owner, repository) {
    return String(owner || "").trim() + "/" + String(repository || "").trim();
}
function suggestion(currentPatient, githubLogin) {
    const patient = splitRepository(currentPatient);
    const own = part(githubLogin);
    // Reuse the exact Patient when one is selected; do NOT construct a
    // nonexistent own-login + foreign repository combination.
    if (patient.owner) return {owner: patient.owner, repository: patient.repository,
                               source: "CURRENT PATIENT"};
    if (own) return {owner: own, repository: "", source: "SIGNED-IN GITHUB"};
    return {owner: "", repository: "", source: "MANUAL ENTRY"};
}
function ownerOptions(rooms, currentPatient, githubLogin) {
    const out = [], seen = {};
    function add(owner, label) {
        const clean = part(owner);
        if (!clean || seen[clean.toLowerCase()]) return;
        seen[clean.toLowerCase()] = true;
        out.push({owner: clean, label: label});
    }
    const own = part(githubLogin);
    if (own) add(own, "MY GITHUB");
    const current = splitRepository(currentPatient);
    if (current.owner) add(current.owner, "CURRENT PATIENT");
    (Array.isArray(rooms) ? rooms : []).forEach(function(room) {
        const p = splitRepository((room || {}).repository);
        if (p.owner) add(p.owner, "USED IN HOSPITAL");
    });
    return out.slice(0, 5);
}
