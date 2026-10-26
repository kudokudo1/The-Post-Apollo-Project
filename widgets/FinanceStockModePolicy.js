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

// M13: make a read-only single-session DAY view from an already retrieved
// and verified RANGE. This does not claim a separate daily API request.
// Only actual provider-returned bars qualify. Copy rather than mutate.
function daySnapshotFromRange(snapshot, index, cik, rangeFrom, rangeTo) {
    const symbols = {
        "0000320193":"AAPL.US",
        "0000789019":"MSFT.US",
        "0001045810":"NVDA.US"
    };
    if (!snapshot || snapshot.schemaVersion !== 1
            || snapshot.source !== "eodhd-eod" || snapshot.readOnly !== true
            || snapshot.cik !== cik || snapshot.symbol !== symbols[cik]
            || snapshot.from !== rangeFrom || snapshot.to !== rangeTo
            || calendarDay(rangeFrom) === null || calendarDay(rangeTo) === null
            || rangeFrom > rangeTo || !["CLOSE","ADJUSTED CLOSE"].includes(snapshot.priceBasis)
            || typeof snapshot.retrievedAt !== "string"
            || !Number.isFinite(Date.parse(snapshot.retrievedAt))
            || !snapshot.delivery
            || !["DIRECT","HUB"].includes(snapshot.delivery.via)
            || !["DIRECT","FETCHED","CACHED","SHARED"].includes(snapshot.delivery.state)
            || typeof snapshot.delivery.servedAt !== "string"
            || !Number.isFinite(Date.parse(snapshot.delivery.servedAt))
            || !Array.isArray(snapshot.bars) || snapshot.bars.length < 2
            || snapshot.bars.length > 132
            || !Number.isInteger(index) || index < 0 || index >= snapshot.bars.length)
        return null;
    const bar = snapshot.bars[index];
    if (!bar || calendarDay(bar.date) === null
            || bar.date < rangeFrom || bar.date > rangeTo
            || typeof bar.price !== "number" || !Number.isFinite(bar.price)
            || bar.price <= 0)
        return null;
    if (snapshot.delivery.via === "DIRECT"
            && snapshot.delivery.state !== "DIRECT")
        return null;
    if (snapshot.delivery.via === "HUB"
            && (!["FETCHED","CACHED","SHARED"].includes(snapshot.delivery.state)
                || typeof snapshot.delivery.cachedAt !== "string"
                || !Number.isFinite(Date.parse(snapshot.delivery.cachedAt))))
        return null;
    const exact = {date:bar.date, price:bar.price};
    const delivery = snapshot.delivery;
    return {
        schemaVersion:1, source:"eodhd-eod", readOnly:true,
        cik:cik, symbol:snapshot.symbol,
        from:bar.date, to:bar.date, retrievedAt:snapshot.retrievedAt,
        priceBasis:snapshot.priceBasis,
        first:{date:exact.date, price:exact.price},
        last:{date:exact.date, price:exact.price},
        changePct:null, bars:[exact],
        delivery:{
            via:delivery.via, state:delivery.state,
            servedAt:delivery.servedAt,
            cachedAt:delivery.cachedAt || null,
            expiresAt:delivery.expiresAt || null,
            ageSeconds:delivery.ageSeconds === undefined ? null : delivery.ageSeconds
        },
        derivedFromRange:true,
        originRange:{from:rangeFrom,to:rangeTo},
        scope:"Actual closing session selected from loaded RANGE; no new request"
    };
}
