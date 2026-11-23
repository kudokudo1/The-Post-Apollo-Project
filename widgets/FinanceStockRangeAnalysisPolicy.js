// FinanceW Market M26: pure, read-only descriptive statistics for an already
// loaded EODHD price RANGE. No API, file, cache, system clock or state mutation.
// All prices represent the single snapshot.priceBasis, never intraday highs/lows.
function calendarDay(date) {
    if (typeof date !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(date))
        return false;
    const ms = Date.parse(date + "T00:00:00Z");
    return Number.isFinite(ms)
        && new Date(ms).toISOString().slice(0, 10) === date;
}
function sameBar(reference, bar) {
    return reference && reference.date === bar.date
        && reference.price === bar.price;
}
function roundPct(value) {
    return Math.round(value * 100) / 100;
}
function summarizeRange(snapshot) {
    if (!snapshot || snapshot.schemaVersion !== 1
            || snapshot.readOnly !== true
            || snapshot.source !== "eodhd-eod"
            || !["CLOSE", "ADJUSTED CLOSE"].includes(snapshot.priceBasis)
            || !calendarDay(snapshot.from) || !calendarDay(snapshot.to)
            || snapshot.from > snapshot.to
            || !Array.isArray(snapshot.bars)
            || snapshot.bars.length < 1 || snapshot.bars.length > 132)
        return null;
    const bars = snapshot.bars;
    let previousDate = "";
    for (const bar of bars) {
        if (!bar || !calendarDay(bar.date)
                || bar.date <= previousDate
                || bar.date < snapshot.from || bar.date > snapshot.to
                || typeof bar.price !== "number"
                || !Number.isFinite(bar.price)
                || bar.price <= 0 || bar.price >= 10000000)
            return null;
        previousDate = bar.date;
    }
    if (!sameBar(snapshot.first, bars[0])
            || !sameBar(snapshot.last, bars[bars.length - 1]))
        return null;
    let low = bars[0], high = bars[0];
    let peak = bars[0], deepestPeak = bars[0], deepestTrough = bars[0];
    let deepest = 0, up = 0, down = 0, flat = 0;
    let largestUp = null, largestDown = null;
    for (let i = 1; i < bars.length; i++) {
        const current = bars[i], previous = bars[i - 1];
        if (current.price > high.price) high = current;
        if (current.price < low.price) low = current;
        if (current.price > peak.price) peak = current;
        const drop = (peak.price - current.price) / peak.price * 100;
        if (drop > deepest) {
            deepest = drop;
            deepestPeak = peak;
            deepestTrough = current;
        }
        const change = (current.price / previous.price - 1) * 100;
        if (current.price > previous.price) {
            up++;
            if (largestUp === null || change > largestUp)
                largestUp = change;
        } else if (current.price < previous.price) {
            down++;
            if (largestDown === null || change < largestDown)
                largestDown = change;
        } else flat++;
    }
    // Copy primitive values: never expose a mutable reference to feed bars.
    function point(bar) { return {date:bar.date, price:bar.price}; }
    return {
        sessions:bars.length,
        priceBasis:snapshot.priceBasis,
        high:point(high), low:point(low),
        maxDrawdownPct:roundPct(deepest),
        peak:point(deepestPeak), trough:point(deepestTrough),
        upSteps:up, downSteps:down, flatSteps:flat,
        largestUpPct:largestUp === null ? null : roundPct(largestUp),
        largestDownPct:largestDown === null ? null : roundPct(largestDown),
        source:"loaded-eodhd-range-only",
        noProviderCalls:true, readOnly:true
    };
}

 
// M27: compare the user-selected ACTUAL closing session with the last close
// in the SAME already loaded/validated range. No network, storage or state.
// "Steps" counts observed sessions, not intervening calendar days.
function compareSelectedToLast(snapshot, index) {
    const summary = summarizeRange(snapshot);
    if (!summary || !Number.isInteger(index)
            || index < 0 || index >= snapshot.bars.length)
        return null;
    const a = snapshot.bars[index];
    const b = snapshot.bars[snapshot.bars.length - 1];
    const difference = b.price - a.price;
    const relative = (b.price / a.price - 1) * 100;
    if (!Number.isFinite(difference) || !Number.isFinite(relative))
        return null;
    return {
        selected:{date:a.date,price:a.price},
        last:{date:b.date,price:b.price},
        deltaPrice:Math.round(difference * 100) / 100,
        deltaPct:roundPct(relative),
        sessionSteps:snapshot.bars.length - index - 1,
        priceBasis:summary.priceBasis,
        source:"loaded-eodhd-range-only",
        noProviderCalls:true,
        readOnly:true
    };
}
