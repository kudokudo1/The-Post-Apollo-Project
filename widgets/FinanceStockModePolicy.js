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


// M14: a single, bounded, in-memory return ticket created ONLY when the
// operator explicitly opens a selected RANGE session in DAY. No disk/cache IO.
// Validate every bar before preserving the original provider snapshot.
function rangeReturnTicket(snapshot, index, cik, from, to) {
    const day = daySnapshotFromRange(snapshot, index, cik, from, to);
    if (!day || calendarDay(from) === null || calendarDay(to) === null
            || calendarDay(to) - calendarDay(from) > 180
            || snapshot.bars.length > 132
            || (snapshot.changePct !== null
                && (typeof snapshot.changePct !== "number"
                    || !Number.isFinite(snapshot.changePct)))
            || !snapshot.first || !snapshot.last
            || snapshot.first.date !== snapshot.bars[0].date
            || snapshot.last.date !== snapshot.bars[snapshot.bars.length - 1].date
            || snapshot.first.price !== snapshot.bars[0].price
            || snapshot.last.price !== snapshot.bars[snapshot.bars.length - 1].price)
        return null;
    let previous = "";
    for (let i = 0; i < snapshot.bars.length; i++) {
        const row = snapshot.bars[i];
        if (!row || calendarDay(row.date) === null
                || row.date < from || row.date > to || row.date <= previous
                || typeof row.price !== "number"
                || !Number.isFinite(row.price) || row.price <= 0)
            return null;
        previous = row.date;
    }
    // The source was normalized and accepted by the Market reader. Keep a
    // separate data copy so changing the derived DAY view cannot edit RANGE.
    const original = JSON.parse(JSON.stringify(snapshot));
    return {
        cik:cik, from:from, to:to, index:index,
        openedDay:day.from, openedPrice:day.bars[0].price,
        snapshot:original
    };
}

// Valid only for the same issuer, original period, selected DAY, provider
// basis and original source provenance. Never borrow a ticket across edits.
function rangeFromReturnTicket(ticket, daySnapshot, cik, from, to) {
    if (!ticket || ticket.cik !== cik || ticket.from !== from
            || ticket.to !== to || !ticket.snapshot || !daySnapshot
            || daySnapshot.derivedFromRange !== true
            || daySnapshot.schemaVersion !== 1
            || daySnapshot.source !== "eodhd-eod" || daySnapshot.readOnly !== true
            || !daySnapshot.originRange
            || daySnapshot.originRange.from !== from
            || daySnapshot.originRange.to !== to
            || daySnapshot.cik !== cik
            || daySnapshot.from !== ticket.openedDay
            || daySnapshot.to !== ticket.openedDay
            || daySnapshot.symbol !== ticket.snapshot.symbol
            || daySnapshot.priceBasis !== ticket.snapshot.priceBasis
            || daySnapshot.retrievedAt !== ticket.snapshot.retrievedAt
            || !Array.isArray(daySnapshot.bars) || daySnapshot.bars.length !== 1
            || daySnapshot.bars[0].date !== ticket.openedDay
            || daySnapshot.bars[0].price !== ticket.openedPrice
            || !daySnapshot.delivery || !ticket.snapshot.delivery
            || daySnapshot.delivery.via !== ticket.snapshot.delivery.via
            || daySnapshot.delivery.state !== ticket.snapshot.delivery.state
            || daySnapshot.delivery.servedAt !== ticket.snapshot.delivery.servedAt
            || daySnapshot.delivery.cachedAt !== ticket.snapshot.delivery.cachedAt
            || daySnapshot.delivery.expiresAt !== ticket.snapshot.delivery.expiresAt
            || daySnapshot.delivery.ageSeconds !== ticket.snapshot.delivery.ageSeconds)
        return null;
    const rechecked = rangeReturnTicket(
        ticket.snapshot, ticket.index, cik, from, to);
    if (!rechecked || rechecked.openedDay !== ticket.openedDay
            || rechecked.openedPrice !== ticket.openedPrice)
        return null;
    const restored = rechecked.snapshot;
    restored.restoredFromDay = true;
    restored.returnedFromDay = ticket.openedDay;
    return restored;
}
