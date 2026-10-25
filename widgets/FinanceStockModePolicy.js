// Finance Market M11: pure DAY vs RANGE selection policy.
// No network, filesystem, dates inferred from market sessions, or side effects.
function calendarDay(value) {
    if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value))
        return null;
    const ms = Date.parse(value + "T00:00:00Z");
    if (!Number.isFinite(ms) || new Date(ms).toISOString().slice(0,10) !== value)
        return null;
    return ms / 86400000;
}
function selectWindow(mode, dayDate, startDate, endDate, today) {
    const upper = calendarDay(today);
    const minimum = calendarDay("2000-01-01");
    if (upper === null) return null;
    if (mode === "day") {
        const day = calendarDay(dayDate);
        return day !== null && day >= minimum && day <= upper
            ? {from:dayDate, to:dayDate, kind:"day"} : null;
    }
    if (mode === "range") {
        const a = calendarDay(startDate), b = calendarDay(endDate);
        return a !== null && b !== null && a >= minimum && b <= upper
            && a <= b && b - a <= 180
            ? {from:startDate, to:endDate, kind:"range"} : null;
    }
    return null;
}
function daySession(snapshot, requestedDay) {
    if (!snapshot || snapshot.from !== requestedDay || snapshot.to !== requestedDay
            || !Array.isArray(snapshot.bars) || snapshot.bars.length > 1)
        return {state:"invalid",date:requestedDay,close:null};
    if (snapshot.bars.length === 0)
        return {state:"no-session",date:requestedDay,close:null};
    const bar = snapshot.bars[0];
    if (!bar || bar.date !== requestedDay || typeof bar.price !== "number"
            || !Number.isFinite(bar.price) || bar.price <= 0)
        return {state:"invalid",date:requestedDay,close:null};
    return {state:"session",date:requestedDay,close:bar.price};
}
