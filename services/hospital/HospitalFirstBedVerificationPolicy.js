// HOSPITAL // non-authoritative first Git Bed selection and fresh evidence.
// The Floor inventory is a candidate list only. No PX room-bind or filesystem
// mutation occurs here; PX must revalidate Git and Room ownership on commit.

function v(x) { return String(x === undefined || x === null ? "" : x).trim(); }
function rows(x) { return Array.isArray(x) ? x : []; }
function repository(origin) {
    let x = v(origin);
    if (!x) return "";
    let m = x.match(/^([A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+)$/);
    if (m) return m[1].toLowerCase();
    m = x.match(/^(?:git@github\.com:|ssh:\/\/git@github\.com\/|https:\/\/github\.com\/)([A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+?)(?:\.git)?\/?$/i);
    return m ? m[1].toLowerCase() : "";
}
function candidateRows(input) {
    const a = input || {}, room = a.room || {};
    const expected = repository(room.repository);
    const expectedBranch = v(room.branch);
    if (!expected || a.roomsLoaded !== true) return [];
    const existing = rows(a.rooms);
    const seen = {};
    return rows(a.beds).filter(function(b) {
        const path = v((b || {}).path);
        if (!path || !path.startsWith("/") || seen[path]) return false;
        seen[path] = true;
        if ((b || {}).isLive === true || v(b.worktree).toUpperCase() !== "CLEAN")
            return false;
        if (repository(b.origin) !== expected
                || !v(b.branch) || v(b.branch) === "DETACHED")
            return false;
        if (expectedBranch && v(b.branch) !== expectedBranch)
            return false;
        if (existing.some(r => v(r.id || r.roomId) !== v(room.id || room.roomId)
                && v(r.bedPath) === path))
            return false;
        return true;
    }).sort(function(a,b) {
        return v(a.path).localeCompare(v(b.path));
    });
}
function assess(input) {
    const a = input || {}, room = a.room || {};
    const selectedPath = v(a.selectedPath), blockers = [];
    function hold(s) { blockers.push(s); }
    const roomId = v(room.id || room.roomId);
    const expectedRepo = repository(room.repository);
    const candidate = candidateRows(a).filter(b => v(b.path) === selectedPath)[0] || null;
    if (a.roomsLoaded !== true) hold("PX Room registry not verified");
    if (!roomId || rows(a.rooms).filter(r =>
            v(r.id || r.roomId) === roomId).length !== 1)
        hold("Select exactly one registered Room");
    if (!expectedRepo) hold("Room GitHub Patient repository not verified");
    if (v(room.bedPath) || v(room.branch))
        hold("Room already has a registered Git Bed or branch");
    if (v(room.doctorId) || v(room.providerId))
        hold("Room is already staffed; first-Bed registration is not eligible");
    if (rows(a.sessions).some(s => v(s.roomId) === roomId))
        hold("Room has Session history; use recovery instead");
    if (a.bedsDiscovering === true)
        hold("Local Git worktree discovery still running");
    if (!candidate)
        hold("Select an unclaimed, non-live, clean Bed from this Patient");
    const evidence = a.evidence || {};
    const inspected = a.evidenceChecked === true
        && a.evidenceBusy !== true
        && v(evidence.path) === selectedPath
        && repository(evidence.origin) === expectedRepo
        && v(evidence.branch) === v((candidate || {}).branch)
        && v(evidence.head).match(/^[0-9a-fA-F]{40,64}$/)
        && evidence.clean === true
        && evidence.topLevel === selectedPath;
    if (!inspected)
        hold("Fresh local Git verification not yet passed for this Bed");
    return {
        candidateSelectable: !!candidate,
        verifiedForReview: blockers.length === 0,
        blockers: blockers,
        roomId: roomId, path: selectedPath,
        branch: v((candidate || {}).branch),
        repository: expectedRepo,
        head: inspected ? v(evidence.head) : "",
        wouldChange: ["Room.branch", "Room.bedPath"],
        authorityVerified: false,
        registrationAuthorized: false,
        providerLaunched: false,
        sessionCreated: false,
        status: blockers.length ? "BED HOLD // VERIFICATION INCOMPLETE"
            : "GIT BED VERIFIED // PX AUTHORIZATION STILL REQUIRED"
    };
}
