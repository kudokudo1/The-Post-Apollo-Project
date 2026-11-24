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

// M31: inspect the ACTUAL loaded closes between two selected historical bars.
// The interval is chronological regardless of the order in which A and B were
// pinned. It does not infer intraday extremes, missing sessions or future data.
function summarizePinnedInterval(snapshot, firstIndex, secondIndex) {
    const compared = comparePinnedRangeSessions(snapshot, firstIndex, secondIndex);
    if (!compared) return null;
    const bars = snapshot.bars;
    const startIndex = Math.min(firstIndex, secondIndex);
    const endIndex = Math.max(firstIndex, secondIndex);
    const first = bars[startIndex], last = bars[endIndex];
    let high = first, low = first, runningPeak = first;
    let drawdownPeak = null, drawdownTrough = null, worstDrop = 0;
    let up = 0, down = 0, flat = 0;
    for (let i=startIndex + 1; i<=endIndex; i++) {
        const current = bars[i], previous = bars[i-1];
        if (current.price > high.price) high = current;
        if (current.price < low.price) low = current;
        if (current.price > runningPeak.price) runningPeak = current;
        const drop = (runningPeak.price - current.price)
            / runningPeak.price * 100;
        if (drop > worstDrop) {
            worstDrop = drop;
            drawdownPeak = runningPeak;
            drawdownTrough = current;
        }
        if (current.price > previous.price) up++;
        else if (current.price < previous.price) down++;
        else flat++;
    }
    const point = bar => ({date:bar.date,price:bar.price});
    return {
        from:point(first), to:point(last),
        sessions:endIndex - startIndex + 1,
        observedSteps:endIndex - startIndex,
        high:point(high),low:point(low),
        maxDrawdownPct:roundPct(worstDrop),
        drawdownPeak:drawdownPeak ? point(drawdownPeak) : null,
        drawdownTrough:drawdownTrough ? point(drawdownTrough) : null,
        upSteps:up,downSteps:down,flatSteps:flat,
        priceBasis:compared.priceBasis,
        pathOrder:"CHRONOLOGICAL",
        source:"loaded-eodhd-range-only",
        readOnly:true,noProviderCalls:true
    };
}

// M33: constant compounded close-to-close change equivalent to a loaded
// interval's actual endpoint ratio. Observed transitions are not elapsed
// calendar days; the result is descriptive, never annualized or projected.
function observedStepChangePct(interval) {
    if (!interval || !Number.isInteger(interval.observedSteps)
            || interval.observedSteps < 1
            || !interval.from || !interval.to
            || !Number.isFinite(interval.from.price)
            || !Number.isFinite(interval.to.price)
            || interval.from.price <= 0 || interval.to.price <= 0)
        return null;
    const logChange = (Math.log(interval.to.price)
        - Math.log(interval.from.price)) / interval.observedSteps;
    const result = (Math.exp(logChange) - 1) * 100;
    if (!Number.isFinite(result)) return null;
    // Four decimals preserve ordinary small observed-step changes.
    // Rounding is display-only; keep the full precision for the difference.
    return result === 0 ? 0 : result;
}

// M32: compare two inclusive historical segments in the same loaded RANGE.
// Both segment returns are chronological, irrespective of selection direction.
function compareHistoricalIntervals(snapshot, a, b, c, d) {
    const first = summarizePinnedInterval(snapshot, a, b);
    const second = summarizePinnedInterval(snapshot, c, d);
    if (!first || !second || a === b || c === d) return null;
    const r1 = (first.to.price / first.from.price - 1) * 100;
    const r2 = (second.to.price / second.from.price - 1) * 100;
    const gap = r2 - r1;
    if (![r1, r2, gap].every(Number.isFinite)) return null;
    const firstStepPct = observedStepChangePct(first);
    const secondStepPct = observedStepChangePct(second);
    const stepGapPoints = firstStepPct === null || secondStepPct === null
        ? null : secondStepPct - firstStepPct;
    return {
        first:first, second:second,
        firstReturnPct:roundPct(r1), secondReturnPct:roundPct(r2),
        returnGapPoints:roundPct(gap),
        firstStepPct:firstStepPct,
        secondStepPct:secondStepPct,
        stepGapPoints:Number.isFinite(stepGapPoints) ? stepGapPoints : null,
        sameStepCount:first.observedSteps === second.observedSteps,
        overlaps:Math.max(Math.min(a,b),Math.min(c,d))
            <= Math.min(Math.max(a,b),Math.max(c,d)),
        readOnly:true,noProviderCalls:true
    };
}

// M34: both chronological intervals start at index value 100. The x axis
// is observed close-to-close steps, shared across unequal-length intervals.
// Shorter series stop at their own last actual observation; no padding.
function normalizedIntervalChart(snapshot, a, b, c, d) {
    const comparison = compareHistoricalIntervals(snapshot, a, b, c, d);
    if (!comparison) return null;
    function series(left, right) {
        const lo = Math.min(left, right), hi = Math.max(left, right);
        const base = snapshot.bars[lo].price;
        const points = [];
        for (let i=lo; i<=hi; i++) {
            const bar = snapshot.bars[i];
            const value = i === lo ? 100 : (bar.price / base) * 100;
            if (!Number.isFinite(value) || value <= 0) return null;
            points.push({step:i-lo, date:bar.date, value:value});
        }
        return points;
    }
    const first = series(a,b), second = series(c,d);
    if (!first || !second) return null;
    const values = first.concat(second).map(p => p.value);
    const low = Math.min.apply(null, values);
    const high = Math.max.apply(null, values);
    return {
        first:first, second:second, low:low, high:high,
        maxSteps:Math.max(first.length,second.length)-1,
        priceBasis:comparison.first.priceBasis,
        source:"loaded-eodhd-range-only",
        readOnly:true,noProviderCalls:true
    };
}

// Coordinates shared by the two series and the base-100 reference line.
function normalizedChartPoint(chart, point, width, height) {
    if (!chart || !point || !Number.isFinite(width)
            || !Number.isFinite(height) || width < 5 || height < 5
            || !Number.isInteger(chart.maxSteps) || chart.maxSteps < 1
            || !Number.isInteger(point.step) || point.step < 0
            || point.step > chart.maxSteps
            || !Number.isFinite(chart.low) || !Number.isFinite(chart.high)
            || chart.low <= 0 || chart.high < chart.low
            || !Number.isFinite(point.value)
            || point.value < chart.low || point.value > chart.high)
        return null;
    return {
        x:point.step / chart.maxSteps * (width - 1),
        y:chart.high === chart.low ? (height - 1)/2
            : (1 - (point.value-chart.low)/(chart.high-chart.low))*(height-1)
    };
}

// M35: choose an observed step on the existing common horizontal axis.
// This is an ordinal comparison, not synchronization by calendar date.
function normalizedStepAtX(chart, width, x) {
    if (!chart || !Number.isInteger(chart.maxSteps) || chart.maxSteps < 1
            || chart.maxSteps > 131 || !Number.isFinite(width) || width < 5
            || !Number.isFinite(x) || x < 0 || x > width - 1)
        return -1;
    return Math.round(x / (width - 1) * chart.maxSteps);
}

function inspectNormalizedStep(chart, step) {
    if (!chart || chart.source !== "loaded-eodhd-range-only"
            || chart.readOnly !== true || chart.noProviderCalls !== true
            || !Number.isInteger(chart.maxSteps) || chart.maxSteps < 1
            || chart.maxSteps > 131 || !Number.isInteger(step)
            || step < 0 || step > chart.maxSteps
            || !Array.isArray(chart.first) || !Array.isArray(chart.second)
            || Math.max(chart.first.length,chart.second.length) !== chart.maxSteps+1
            || chart.first.length < 2 || chart.second.length < 2)
        return null;
    function observation(series) {
        if (step >= series.length) return null;
        const p = series[step];
        if (!p || p.step !== step || !calendarDay(p.date)
                || !Number.isFinite(p.value) || p.value <= 0)
            return null;
        return {step:step,date:p.date,value:p.value,changePct:p.value-100};
    }
    const first = observation(chart.first), second = observation(chart.second);
    // A missing in-bounds observation is invalid, not an ended series.
    if ((step < chart.first.length && !first)
            || (step < chart.second.length && !second)
            || (!first && !second)) return null;
    const gap = first && second ? second.value-first.value : null;
    if (gap !== null && !Number.isFinite(gap)) return null;
    return {
        step:step,first:first,second:second,
        gapPoints:gap,sharedObservation:first !== null && second !== null,
        readOnly:true,noProviderCalls:true
    };
}

// M36: capture one detached, bounded closing-price range in memory.
// Caller supplies the exact identity from the existing six-stock catalog.
function captureStockReference(snapshot, cik, symbol) {
    if (!summarizeRange(snapshot) || snapshot.bars.length < 2
            || typeof cik !== "string" || !/^\d{10}$/.test(cik)
            || typeof symbol !== "string" || !/^[A-Z]+\.US$/.test(symbol)
            || snapshot.cik !== cik || snapshot.symbol !== symbol
            || typeof snapshot.retrievedAt !== "string"
            || !Number.isFinite(Date.parse(snapshot.retrievedAt)))
        return null;
    const bars = snapshot.bars.map(p => ({date:p.date,price:p.price}));
    return {
        schemaVersion:1,source:"eodhd-eod",readOnly:true,
        cik:cik,symbol:symbol,priceBasis:snapshot.priceBasis,
        from:snapshot.from,to:snapshot.to,retrievedAt:snapshot.retrievedAt,
        bars:bars,first:{date:bars[0].date,price:bars[0].price},
        last:{date:bars[bars.length-1].date,price:bars[bars.length-1].price}
    };
}

// Cross-stock movement uses common observed calendar dates, not ordinal
// alignment. No missing-price fill or cross-basis comparison.
function compareStockReferences(reference, current, cik, symbol) {
    const a = reference && captureStockReference(reference,reference.cik,reference.symbol);
    const b = captureStockReference(current,cik,symbol);
    if (!a || !b) return {state:"invalid"};
    if (a.cik === b.cik || a.symbol === b.symbol) return {state:"same-stock"};
    if (a.from !== b.from || a.to !== b.to) return {state:"window-mismatch"};
    if (a.priceBasis !== b.priceBasis) return {state:"basis-mismatch"};
    const pairs = [];
    let i=0,j=0;
    while (i<a.bars.length && j<b.bars.length) {
        const left=a.bars[i], right=b.bars[j];
        if (left.date < right.date) i++;
        else if (right.date < left.date) j++;
        else {
            pairs.push({date:left.date,referencePrice:left.price,currentPrice:right.price});
            i++; j++;
        }
    }
    if (pairs.length < 2) return {state:"insufficient",matched:pairs.length};
    const first=pairs[0], last=pairs[pairs.length-1];
    const referencePct=(last.referencePrice/first.referencePrice-1)*100;
    const currentPct=(last.currentPrice/first.currentPrice-1)*100;
    const gap=currentPct-referencePct;
    if (![referencePct,currentPct,gap].every(Number.isFinite)) return {state:"invalid"};
    return {
        state:"ready",referenceSymbol:a.symbol,currentSymbol:b.symbol,
        referenceRetrievedAt:a.retrievedAt,currentRetrievedAt:b.retrievedAt,
        priceBasis:a.priceBasis,from:first.date,to:last.date,
        matched:pairs.length,referenceUnmatched:a.bars.length-pairs.length,
        currentUnmatched:b.bars.length-pairs.length,
        referencePct:referencePct,currentPct:currentPct,gapPoints:gap,
        pairs:pairs,readOnly:true,noProviderCalls:true
    };
}

// M37: rebase both stocks to 100 at their first COMMON observed closing
// date. The x axis is ordinal common-date observations, not calendar time.
// Accept only the ready output of the existing M36 comparison.
function crossStockNormalizedChart(comparison) {
    if (!comparison || comparison.state !== "ready"
            || comparison.readOnly !== true || comparison.noProviderCalls !== true
            || typeof comparison.referenceSymbol !== "string"
            || typeof comparison.currentSymbol !== "string"
            || comparison.referenceSymbol === comparison.currentSymbol
            || !["CLOSE","ADJUSTED CLOSE"].includes(comparison.priceBasis)
            || !Array.isArray(comparison.pairs)
            || comparison.pairs.length < 2 || comparison.pairs.length > 132
            || comparison.matched !== comparison.pairs.length)
        return null;
    const pairs=comparison.pairs;
    let previous="";
    for (const pair of pairs) {
        if (!pair || !calendarDay(pair.date) || pair.date <= previous
                || !Number.isFinite(pair.referencePrice) || pair.referencePrice <= 0
                || !Number.isFinite(pair.currentPrice) || pair.currentPrice <= 0
                || pair.referencePrice >= 10000000 || pair.currentPrice >= 10000000)
            return null;
        previous=pair.date;
    }
    if (pairs[0].date !== comparison.from
            || pairs[pairs.length-1].date !== comparison.to) return null;
    const first=[],second=[];
    for (let i=0;i<pairs.length;i++) {
        const row=pairs[i];
        const a=i===0 ? 100 : row.referencePrice/pairs[0].referencePrice*100;
        const b=i===0 ? 100 : row.currentPrice/pairs[0].currentPrice*100;
        if (!Number.isFinite(a) || !Number.isFinite(b) || a <= 0 || b <= 0)
            return null;
        first.push({step:i,date:row.date,value:a});
        second.push({step:i,date:row.date,value:b});
    }
    const values=first.concat(second).map(p=>p.value);
    return {
        first:first,second:second,
        low:Math.min.apply(null,values),high:Math.max.apply(null,values),
        maxSteps:pairs.length-1,from:comparison.from,to:comparison.to,
        referenceSymbol:comparison.referenceSymbol,currentSymbol:comparison.currentSymbol,
        priceBasis:comparison.priceBasis,source:"loaded-eodhd-common-dates-only",
        readOnly:true,noProviderCalls:true
    };
}
