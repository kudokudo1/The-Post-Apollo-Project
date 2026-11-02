.pragma library

// Weather M11 relationship helpers.
//
// These functions compare already-captured observations. They do not fetch,
// interpolate provider data, or imply causation. Time alignment is explicit
// and one-to-one so one slow observation cannot be counted repeatedly against
// several faster samples.

function finiteNumber(value, fallback) {
    if (value === undefined || value === null || value === "")
        return fallback;
    const number = Number(value);
    return isFinite(number) ? number : fallback;
}

function positiveMillis(value) {
    const number = Number(value);
    return isFinite(number) && number > 0 ? Math.floor(number) : -1;
}

function numericSeries(samples, field, maximumPoints) {
    const source = Array.isArray(samples) ? samples : [];
    const rows = [];
    for (let i = 0; i < source.length; i++) {
        const sample = source[i] || {};
        const time = positiveMillis(sample.observedAtMs);
        const payload = sample.payload && typeof sample.payload === "object"
            ? sample.payload : {};
        const value = finiteNumber(payload[field], null);
        if (time <= 0 || value === null)
            continue;
        rows.push({
            timeMs: time,
            value: value,
            receivedAtMs: positiveMillis(sample.receivedAtMs)
        });
    }

    rows.sort(function(a, b) {
        return a.timeMs - b.timeMs;
    });

    const limit = Math.max(
        2,
        Math.floor(Number(maximumPoints || rows.length || 2))
    );
    return rows.length > limit
        ? rows.slice(rows.length - limit)
        : rows;
}

function nearestPairs(
    leftSamples, leftField,
    rightSamples, rightField,
    toleranceMs, maximumPairs
) {
    const left = numericSeries(leftSamples, leftField, 100000);
    const right = numericSeries(rightSamples, rightField, 100000);
    const tolerance = Math.max(
        0,
        Math.floor(Number(toleranceMs) || 0)
    );
    const used = {};
    const pairs = [];

    for (let i = 0; i < left.length; i++) {
        const row = left[i];
        let bestIndex = -1;
        let bestDistance = tolerance + 1;

        for (let j = 0; j < right.length; j++) {
            if (used[j])
                continue;
            const distance = Math.abs(right[j].timeMs - row.timeMs);
            if (distance > tolerance)
                continue;
            if (distance < bestDistance) {
                bestDistance = distance;
                bestIndex = j;
            }
        }

        if (bestIndex < 0)
            continue;

        used[bestIndex] = true;
        const other = right[bestIndex];
        pairs.push({
            timeMs: Math.max(row.timeMs, other.timeMs),
            leftTimeMs: row.timeMs,
            rightTimeMs: other.timeMs,
            distanceMs: bestDistance,
            left: row.value,
            right: other.value
        });
    }

    pairs.sort(function(a, b) {
        return a.timeMs - b.timeMs;
    });

    const limit = Math.max(
        2,
        Math.floor(Number(maximumPairs || pairs.length || 2))
    );
    return pairs.length > limit
        ? pairs.slice(pairs.length - limit)
        : pairs;
}

function pearson(pairs) {
    const source = Array.isArray(pairs) ? pairs : [];
    // Four aligned observations is a minimum display gate, not a claim of
    // statistical significance.
    if (source.length < 4)
        return null;

    let leftMean = 0;
    let rightMean = 0;
    for (let i = 0; i < source.length; i++) {
        leftMean += Number(source[i].left);
        rightMean += Number(source[i].right);
    }
    leftMean /= source.length;
    rightMean /= source.length;

    let numerator = 0;
    let leftSquares = 0;
    let rightSquares = 0;
    for (let i = 0; i < source.length; i++) {
        const dl = Number(source[i].left) - leftMean;
        const dr = Number(source[i].right) - rightMean;
        numerator += dl * dr;
        leftSquares += dl * dl;
        rightSquares += dr * dr;
    }

    const denominator = Math.sqrt(leftSquares * rightSquares);
    if (!isFinite(denominator) || denominator <= 0)
        return null;

    const value = numerator / denominator;
    return Math.max(-1, Math.min(1, value));
}

function correlationLabel(value) {
    if (value === null || value === undefined || !isFinite(Number(value)))
        return "NEED ≥4 PAIRS";

    const number = Number(value);
    const magnitude = Math.abs(number);
    const direction = number > 0.05 ? "POSITIVE"
        : number < -0.05 ? "NEGATIVE" : "FLAT";

    if (magnitude >= 0.7)
        return "STRONG " + direction;
    if (magnitude >= 0.4)
        return "MODERATE " + direction;
    if (magnitude >= 0.2)
        return "WEAK " + direction;
    return "LITTLE LINEAR ASSOCIATION";
}

function trendFromPairs(pairs, side) {
    const source = Array.isArray(pairs) ? pairs : [];
    const key = side === "right" ? "right" : "left";
    if (source.length === 0) {
        return {
            count:0, first:null, latest:null, delta:null,
            minimum:null, maximum:null, spanMs:0
        };
    }

    let minimum = Number(source[0][key]);
    let maximum = minimum;
    for (let i = 1; i < source.length; i++) {
        const value = Number(source[i][key]);
        minimum = Math.min(minimum, value);
        maximum = Math.max(maximum, value);
    }

    const first = Number(source[0][key]);
    const latest = Number(source[source.length - 1][key]);
    return {
        count: source.length,
        first: first,
        latest: latest,
        delta: latest - first,
        minimum: minimum,
        maximum: maximum,
        spanMs: Math.max(
            0,
            Number(source[source.length - 1].timeMs)
            - Number(source[0].timeMs)
        )
    };
}

function summarizePairs(pairs) {
    const source = Array.isArray(pairs) ? pairs : [];
    const correlation = pearson(source);
    return {
        pairs: source,
        count: source.length,
        correlation: correlation,
        correlationLabel: correlationLabel(correlation),
        leftTrend: trendFromPairs(source, "left"),
        rightTrend: trendFromPairs(source, "right"),
        leftValues: source.map(function(row) { return row.left; }),
        rightValues: source.map(function(row) { return row.right; }),
        spanMs: source.length >= 2
            ? Math.max(
                0,
                Number(source[source.length - 1].timeMs)
                - Number(source[0].timeMs)
              )
            : 0,
        maxAlignmentMs: source.reduce(function(best, row) {
            return Math.max(best, Number(row.distanceMs) || 0);
        }, 0)
    };
}

function relationship(
    leftSamples, leftField,
    rightSamples, rightField,
    toleranceMs, maximumPairs
) {
    return summarizePairs(nearestPairs(
        leftSamples, leftField,
        rightSamples, rightField,
        toleranceMs, maximumPairs
    ));
}

function formatCorrelation(value) {
    return value === null || value === undefined || !isFinite(Number(value))
        ? "--"
        : Number(value).toFixed(2);
}

function formatDelta(value, decimals) {
    if (value === null || value === undefined || !isFinite(Number(value)))
        return "--";
    const digits = Math.max(0, Math.floor(Number(decimals) || 0));
    const number = Number(value);
    return (number > 0 ? "+" : "") + number.toFixed(digits);
}

function spanLabel(milliseconds) {
    const ms = Math.max(0, Number(milliseconds) || 0);
    const minutes = Math.floor(ms / 60000);
    if (minutes < 60)
        return minutes + "m";
    const hours = Math.floor(minutes / 60);
    const remainder = minutes % 60;
    if (hours < 48)
        return hours + "h " + remainder + "m";
    return Math.floor(hours / 24) + "d " + (hours % 24) + "h";
}

function normalized(values) {
    const source = Array.isArray(values) ? values : [];
    if (source.length === 0)
        return [];
    let minimum = Number(source[0]);
    let maximum = minimum;
    for (let i = 1; i < source.length; i++) {
        minimum = Math.min(minimum, Number(source[i]));
        maximum = Math.max(maximum, Number(source[i]));
    }
    const spread = maximum - minimum;
    if (!isFinite(spread) || Math.abs(spread) < 0.0000001)
        return source.map(function() { return 0.5; });
    return source.map(function(value) {
        return (Number(value) - minimum) / spread;
    });
}
