// HOSPITAL // Surgery first-open snapshot decisions.
// Timestamp alone is not valid evidence that a Floor audit succeeded.
// Keep the lag-protection window while refusing to reuse missing/failed data.
function canReuseAudit(lastAt, nowAt, windowMs, available, lastError) {
    const last = Number(lastAt || 0);
    const now = Number(nowAt || 0);
    const window = Number(windowMs || 0);
    if (!available || String(lastError || "").trim()
            || last <= 0 || now < last || window <= 0)
        return false;
    return now - last < window;
}

function canReuseFloor(lastAt, nowAt, windowMs, floorCount) {
    const last = Number(lastAt || 0);
    const now = Number(nowAt || 0);
    const window = Number(windowMs || 0);
    return Number(floorCount || 0) > 0
        && last > 0 && now >= last && window > 0
        && now - last < window;
}
