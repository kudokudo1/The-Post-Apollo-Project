// Hospital Bed Recovery // Candidate search only.
// The PX provider-launch preflight remains the execution authority.
// Do not use this UI-side metadata filter as a permission or safety grant.

function githubRepository(value) {
    const text = String(value || "").trim();
    if (!text || text === "NO ORIGIN")
        return "";

    let path = "";
    let match = text.match(/^([A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+)(?:\.git)?$/);
    if (match) {
        path = match[1];
    } else {
        match = text.match(/^git@github\.com:([^?#]+)$/i);
        if (match)
            path = match[1];
        else {
            match = text.match(/^(?:https?:\/\/|ssh:\/\/(?:git@)?|git:\/\/)github\.com\/([^?#]+)$/i);
            if (match)
                path = match[1];
        }
    }

    path = path.replace(/\.git$/i, "").replace(/\/$/, "");
    if (!/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(path))
        return "";
    return path.toLowerCase();
}

function isClean(value) {
    return String(value || "").trim().toUpperCase() === "CLEAN";
}

function scanCandidates(knownBeds, repository, branch) {
    const expectedRepository = githubRepository(repository);
    const expectedBranch = String(branch || "").trim();
    if (!expectedRepository || !expectedBranch || expectedBranch === "DETACHED")
        return [];

    const rows = Array.isArray(knownBeds) ? knownBeds : [];
    const seen = {};
    const matches = [];
    for (let i = 0; i < rows.length; ++i) {
        const source = rows[i] || {};
        const path = String(source.path || "").trim();
        const actualBranch = String(source.branch || "").trim();
        const actualRepository = githubRepository(source.origin);
        if (!path || seen[path] || actualBranch !== expectedBranch
                || actualRepository !== expectedRepository)
            continue;
        seen[path] = true;
        matches.push({
            path: path,
            label: String(source.label || "LOCAL BED"),
            branch: actualBranch,
            repository: actualRepository,
            head: String(source.head || ""),
            worktree: String(source.worktree || "UNKNOWN"),
            dirty: !isClean(source.worktree),
            isLive: Boolean(source.isLive),
            // Inventory data is not fresh Git evidence; PX MUST recheck.
            verification: "CANDIDATE_UNVERIFIED"
        });
    }

    // Prefer non-live and clean worktrees, but never auto-select or execute.
    matches.sort(function(a, b) {
        if (a.isLive !== b.isLive)
            return a.isLive ? 1 : -1;
        if (a.dirty !== b.dirty)
            return a.dirty ? 1 : -1;
        return a.path.localeCompare(b.path);
    });
    return matches;
}

function moveEligibility(currentBed, repository, branch, activeOperation) {
    const bed = currentBed || {};
    const path = String(bed.path || "").trim();
    const target = String(branch || "").trim();
    if (!path || !target)
        return { eligible: false, reason: "BED_OR_ROOM_UNRESOLVED" };
    if (Boolean(activeOperation))
        return { eligible: false, reason: "HOSPITAL_OPERATION_ACTIVE" };
    if (githubRepository(bed.origin) !== githubRepository(repository)
            || !githubRepository(repository))
        return { eligible: false, reason: "PATIENT_REPOSITORY_UNVERIFIED" };
    if (String(bed.branch || "").trim() === target)
        return { eligible: false, reason: "BED_ALREADY_ON_BRANCH" };
    if (!isClean(bed.worktree))
        return { eligible: false, reason: "BED_DIRTY" };
    return {
        eligible: true,
        reason: bed.isLive ? "LIVE_BED_REQUIRES_SECOND_CONFIRMATION"
                           : "REQUIRES_FRESH_PREMOVE_VALIDATION"
    };
}
