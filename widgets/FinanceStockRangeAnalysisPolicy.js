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

// M28: simple *trailing* averages of actual loaded trading-session closes.
// These are never intraday highs/lows, predictions, or extrapolated quotes.
// M26 validates 1-132 chronological source bars and a single price basis.
function movingAverageSeries(snapshot) {
    const valid = summarizeRange(snapshot);
    if (!valid) return null;
    const rows = snapshot.bars;
    function trail(period) {
        let total = 0;
        const points = [];
        for (let i=0; i<rows.length; i++) {
            total += rows[i].price;
            if (i >= period) total -= rows[i-period].price;
            if (i >= period - 1) {
                const avg = total / period;
                if (!Number.isFinite(avg) || avg <= 0) return null;
                points.push({index:i, date:rows[i].date, price:avg});
            }
        }
        return points;
    }
    const five = trail(5), twenty = trail(20);
    if (!five || !twenty) return null;
    return {
        sma5:five, sma20:twenty,
        latest5:five.length ? five[five.length - 1].price : null,
        latest20:twenty.length ? twenty[twenty.length - 1].price : null,
        sessions:rows.length,
        priceBasis:valid.priceBasis,
        source:"loaded-eodhd-range-only",
        readOnly:true,
        noProviderCalls:true
    };
}

// M29: descriptive relationship between already-loaded SMA5 and SMA20.
// An observed SIDE CHANGE means the first later non-equal average is on the
// opposite side of the earlier non-equal average, potentially across ties.
// Never call this a price crossing, recommendation, or intraday event.
function movingAverageRelationship(snapshot) {
    const moving = movingAverageSeries(snapshot);
    if (!moving) return null;
    if (moving.sessions < 20) {
        return {
            state:"insufficient", sessions:moving.sessions, requiredSessions:20,
            source:"loaded-eodhd-range-only", readOnly:true, noProviderCalls:true
        };
    }
    let previousDefinite = null;
    let aboveChanges = 0, belowChanges = 0, lastChange = null;
    let latestSide = "EQUAL";
    for (let i=19; i<moving.sessions; i++) {
        const five = moving.sma5[i-4], twenty = moving.sma20[i-19];
        if (!five || !twenty || five.index !== i || twenty.index !== i
                || five.date !== twenty.date) return null;
        const spread = five.price - twenty.price;
        const epsilon = Math.max(five.price, twenty.price) * 1e-10;
        const side = Math.abs(spread) <= epsilon ? "EQUAL"
            : spread > 0 ? "ABOVE" : "BELOW";
        latestSide = side;
        if (side !== "EQUAL") {
            if (previousDefinite !== null && side !== previousDefinite) {
                if (side === "ABOVE") aboveChanges++;
                else belowChanges++;
                lastChange = {date:five.date,index:i,direction:side};
            }
            previousDefinite = side;
        }
    }
    const spread = moving.latest5 - moving.latest20;
    const spreadPct = spread / moving.latest20 * 100;
    if (!Number.isFinite(spread) || !Number.isFinite(spreadPct))
        return null;
    return {
        state:"ready",
        sessions:moving.sessions,
        latestDate:snapshot.bars[snapshot.bars.length-1].date,
        latestSide:latestSide,
        spreadPrice:latestSide === "EQUAL" ? 0 : Math.round(spread*100)/100,
        spreadPct:latestSide === "EQUAL" ? 0 : roundPct(spreadPct),
        sideChanges:aboveChanges+belowChanges,
        movedAbove:aboveChanges, movedBelow:belowChanges,
        lastChange:lastChange,
        priceBasis:moving.priceBasis,
        source:"loaded-eodhd-range-only",
        readOnly:true,
        noProviderCalls:true
    };
}

// M30: arbitrary two-point historical comparison inside a single loaded RANGE.
// A/B indices refer ONLY to provider-returned closing sessions. Date order may
// run forward or backward; percentages always use A (pinned) as the baseline.
// No quote requests, portfolio holdings, storage, timers or implicit endpoints.
function comparePinnedRangeSessions(snapshot, firstIndex, secondIndex) {
    const validated = summarizeRange(snapshot);
    if (!validated || !Number.isInteger(firstIndex)
            || !Number.isInteger(secondIndex)
            || firstIndex < 0 || secondIndex < 0
            || firstIndex >= snapshot.bars.length
            || secondIndex >= snapshot.bars.length)
        return null;
    const a = snapshot.bars[firstIndex];
    const b = snapshot.bars[secondIndex];
    const change = b.price - a.price;
    const changePct = (b.price / a.price - 1) * 100;
    if (!Number.isFinite(change) || !Number.isFinite(changePct))
        return null;
    const rounded = Math.round(change * 100) / 100;
    return {
        start:{index:firstIndex,date:a.date,price:a.price},
        end:{index:secondIndex,date:b.date,price:b.price},
        deltaPrice:rounded === 0 ? 0 : rounded,
        deltaPct:roundPct(changePct) || 0,
        observedSteps:Math.abs(secondIndex - firstIndex),
        order:secondIndex > firstIndex ? "FORWARD"
            : secondIndex < firstIndex ? "BACKWARD" : "SAME",
        priceBasis:validated.priceBasis,
        source:"loaded-eodhd-range-only",
        readOnly:true,
        noProviderCalls:true
    };
}
