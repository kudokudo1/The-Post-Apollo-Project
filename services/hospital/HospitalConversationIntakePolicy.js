// HOSPITAL // local, deterministic starter proposal from an operator brief.
// This is NOT AI inference or a Provider turn. It never grants permissions,
// writes a Room, chooses a Git Bed or authorizes worker execution.
function clean(value) {
    return String(value === undefined || value === null ? "" : value).trim();
}
function compact(value, limit) {
    return clean(value).replace(/\s+/g, " ").slice(0, limit).trim();
}
function proposal(briefValue) {
    const brief = clean(briefValue);
    const blockers = [];
    if (!brief) blockers.push("Describe the work before drafting a setup");
    if (brief.length > 4000) blockers.push("Description exceeds the 4000 character intake limit");
    if (/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/.test(brief))
        blockers.push("Description contains unsupported control characters");
    const match = /(?:\byou(?:'re| are)\b|\bmy\b|\bas an?\b|\brole\s*(?:is|:))[^.!?\n]{0,50}\b(intern|nurse|doctor)\b/i.exec(brief);
    const roleWord = match ? match[1].toLowerCase() : "intern";
    const role = roleWord === "doctor" ? "DOC" : roleWord === "nurse" ? "NRS" : "INT";
    let first = compact(brief.split(/[\n.!?]/)[0], 78);
    if (!first) first = compact(brief, 78);
    const title = first || "New Assignment";
    const nameBase = compact(first.replace(/^(?:hey,?\s+|please\s+|i (?:want|need) (?:you|an? ai) to\s+)/i, ""), 65)
        || "Project Review";
    const roomName = nameBase.slice(0, 96);
    const workerName = compact(roomName + " " + (role === "DOC" ? "Doctor" : role === "NRS" ? "Nurse" : "Intern"), 96);
    return {
        ready: blockers.length === 0,
        blockers: blockers,
        source: "LOCAL STARTER TEMPLATE // NOT AI-GENERATED",
        role: role,
        roomName: roomName,
        workerName: workerName,
        title: title,
        goal: brief,
        constraints: "Start with read-only inspection. Stay inside the chosen Patient, Room and assigned files. Ask before making changes.",
        definitionDone: "Report findings, evidence, blockers and recommended next actions for operator review.",
        checklist: "Inspect current source and Room context\nIdentify findings and evidence\nReport recommendations and open questions",
        permissions: "READ",
        roomSaved: false,
        workerSaved: false,
        jobSaved: false,
        launchesProvider: false,
        activatesAssignment: false,
        writesHospital: false,
        authorityVerified: false
    };
}
