// HOSPITAL // inline Surgery workforce management preflight.
// These checks are UI affordances, not substitute for atomic PX authority.
const BASIC_ROLES = ["INT", "NRS", "DOC"];
const PERMISSIONS = ["READ", "EDIT", "TEST", "COMMIT", "PUSH", "OPEN_PR", "INTEGRATE"];
function v(s) { return String(s === null || s === undefined ? "" : s).trim(); }
function rows(r) { return Array.isArray(r) ? r : []; }
function roleCode(s) { return v(s).toUpperCase(); }
function validName(s) { return !!v(s) && v(s).length <= 96 && !/[\x00-\x1f\x7f]/.test(v(s)); }
function base(a) {
    const source = a || {}, blockers = [];
    if (source.doctorsLoaded !== true) blockers.push("Doctor directory has not loaded");
    if (source.roomsLoaded !== true || source.sessionsLoaded !== true)
        blockers.push("Room / Session registry not verified");
    if (v(source.registryError)) blockers.push("PX registry returned an error");
    return blockers;
}
function worker(a) {
    const source = a || {}, blockers = base(source);
    const name = v(source.name), role = roleCode(source.role);
    const id = v(source.id);
    if (!validName(name)) blockers.push("Worker name is required (maximum 96 characters)");
    if (BASIC_ROLES.indexOf(role) < 0) blockers.push("Choose INTERN, NURSE or DOCTOR");
    if (!/^worker-[a-z0-9-]{8,90}$/.test(id)) blockers.push("Missing generated worker ID");
    if (rows(source.doctors).some(d => v(d.id) === id))
        blockers.push("Worker ID already exists. Nothing may be overwritten");
    return {ready: blockers.length === 0, blockers, id, name, role,
        mutationAuthorized: false, createsSession: false, launchesProvider: false};
}
function room(a) {
    const source = a || {}, blockers = base(source);
    const id = v(source.id), name = v(source.name);
    const repository = v(source.repository);
    if (!/^room-[a-z0-9-]{8,90}$/.test(id)) blockers.push("Missing generated Room ID");
    if (!validName(name)) blockers.push("Room name is required (maximum 96 characters)");
    if (!/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(repository))
        blockers.push("Repository must be owner/name");
    if (rows(source.rooms).some(r => v(r.id || r.roomId) === id))
        blockers.push("Room ID already exists. Nothing may be overwritten");
    const existingPatients = rows(source.rooms).filter(function(r) {
        return v(r.repository).toLowerCase() === repository.toLowerCase()
            && v(r.patientId);
    });
    const patientIds = existingPatients.map(r => v(r.patientId))
        .filter((id, i, values) => values.indexOf(id) === i);
    if (patientIds.length > 1)
        blockers.push("Patient ID ambiguous for this repository");
    const patientId = patientIds.length === 1 ? patientIds[0] : repository;
    const existingLabel = existingPatients.filter(r => v(r.patientId) === patientId
        && v(r.patientLabel))[0];
    const patientLabel = existingLabel ? v(existingLabel.patientLabel) : repository;
    if (!validName(patientLabel))
        blockers.push("Patient display label too long for this Room creation");
    return {ready: blockers.length === 0, blockers, id, name, repository,
        patientId, patientLabel,
        mutationAuthorized: false, createsSession: false, assignsDoctor: false,
        branch: "", bedPath: ""};
}
function retirement(a) {
    const source = a || {}, blockers = base(source), id = v(source.doctorId);
    const doctor = rows(source.doctors).filter(d => v(d.id) === id)[0];
    if (!doctor) blockers.push("Select a registered worker");
    else if (roleCode(doctor.status) === "RELEASED")
        blockers.push("Worker is already released");
    if (rows(source.rooms).some(r => v(r.doctorId) === id))
        blockers.push("Worker still owns a Room. Recover or release staffing first");
    if (rows(source.sessions).some(function(s) {
        if (v(s.doctorId) !== id) return false;
        const pid = Number(s.activePid || 0);
        return !v(s.endedAt)
            || ["COMPLETE","FAILED","ENDED"].indexOf(roleCode(s.status)) < 0
            || !Number.isFinite(pid) || pid !== 0;
    }))
        blockers.push("Worker has unreleased Session or recorded active process");
    return {ready: blockers.length === 0, blockers, id,
        mutationAuthorized: false, deletesHistory: false};
}
function assignment(a) {
    const source = a || {}, blockers = base(source), roomId = v(source.roomId);
    if (!roomId || !rows(source.rooms).some(r => v(r.id || r.roomId) === roomId))
        blockers.push("Choose a registered Room");
    if (!validName(source.title)) blockers.push("Assignment title is required");
    if (!v(source.goal)) blockers.push("Assignment goal is required");
    const raw = v(source.permissions).toUpperCase().split(/[,\s]+/).filter(Boolean);
    const unknown = raw.filter(p => PERMISSIONS.indexOf(p) < 0);
    if (unknown.length > 0) blockers.push("Unknown permission: " + unknown.join(", "));
    const permissions = ["READ"];
    raw.forEach(function(p) {
        if (p !== "READ" && PERMISSIONS.indexOf(p) >= 0
                && permissions.indexOf(p) < 0)
            permissions.push(p);
    });
    return {ready: blockers.length === 0, blockers, roomId, permissions,
        mutationAuthorized: false, activatesAssignment: false};
}
