import QtQuick
import Quickshell

QtObject {
    id: graphHistory

    // Pure graph/history presentation helpers shared by AppControl and CPU++.
    // This object deliberately owns no telemetry source and no selection state.

    // Opt-in aggregate-only diagnostics. The counters are plain JS object fields,
    // not QML-bound per-sample properties. No extra timer or data collector.
    readonly property bool arrayCopyProbeEnabled:
        String(Quickshell.env("POST_APOLLO_ARRAY_COPY_PROBE") || "").trim() === "1"
    property var arrayCopyProbeBuckets: ({})
    property double arrayCopyProbeLastReportMs: 0

    function recordArrayCopy(kind, inputCount, copyMs, startMs) {
        if (!arrayCopyProbeEnabled)
            return;
        const now = Date.now();
        const buckets = arrayCopyProbeBuckets;
        let bucket = buckets[kind];
        if (!bucket) {
            bucket = { count: 0, maxInput: 0, copyTotalMs: 0,
                       workTotalMs: 0, maxWorkMs: 0 };
            buckets[kind] = bucket;
        }
        const workMs = Math.max(0, now - startMs);
        bucket.count += 1;
        bucket.maxInput = Math.max(bucket.maxInput, inputCount);
        bucket.copyTotalMs += copyMs;
        bucket.workTotalMs += workMs;
        bucket.maxWorkMs = Math.max(bucket.maxWorkMs, workMs);
        if (!arrayCopyProbeLastReportMs) {
            arrayCopyProbeLastReportMs = now;
            return;
        }
        if (now - arrayCopyProbeLastReportMs < 5000)
            return;
        for (const name in buckets) {
            const b = buckets[name];
            console.warn("SYNTAGMA_ARRAY_PROBE // graph=" + name
                         + " calls=" + b.count + " maxInput=" + b.maxInput
                         + " copyTotalMs=" + b.copyTotalMs
                         + " workTotalMs=" + b.workTotalMs
                         + " maxWorkMs=" + b.maxWorkMs + " tsMs=" + now);
        }
        arrayCopyProbeBuckets = ({});
        arrayCopyProbeLastReportMs = now;
    }

    function linePoints(values, graphWidth, graphHeight, requiredRange,
                        slotCount, topInset, bottomInset) {
        const probeStartMs = arrayCopyProbeEnabled ? Date.now() : 0;
        const source = Array.isArray(values) ? values.slice() : [];
        const copyMs = probeStartMs ? Date.now() - probeStartMs : 0;

        if (source.length === 0) {
            if (probeStartMs)
                recordArrayCopy("linePoints", 0, copyMs, probeStartMs);
            return [];
        }

        if (source.length === 1)
            source.unshift(source[0]);

        let minimum = Number(source[0] || 0);
        let maximum = minimum;

        for (let i = 1; i < source.length; i++) {
            const value = Number(source[i] || 0);
            minimum = Math.min(minimum, value);
            maximum = Math.max(maximum, value);
        }

        const wantedRange = Math.max(0.0001, Number(requiredRange || 1));
        let range = Math.max(wantedRange, maximum - minimum);
        let lower = Math.max(0, minimum - range * 0.24);
        let upper = maximum + range * 0.24;

        if (upper - lower < wantedRange) {
            const center = (upper + lower) / 2;
            lower = Math.max(0, center - wantedRange / 2);
            upper = lower + wantedRange;
        }

        const width = Math.max(1, Number(graphWidth || 1));
        const height = Math.max(1, Number(graphHeight || 1));
        const top = Math.max(
            0,
            Number(topInset === undefined ? 2 : topInset)
        );
        const bottom = Math.max(
            top + 1,
            height - Math.max(
                0,
                Number(bottomInset === undefined ? 2 : bottomInset)
            )
        );
        const slots = Math.max(2, Number(slotCount || source.length));
        const step = width / Math.max(1, slots - 1);
        const startX = width - step * (source.length - 1);
        const points = [];

        for (let i = 0; i < source.length; i++) {
            const normalized = Math.max(
                0,
                Math.min(
                    1,
                    (Number(source[i] || 0) - lower)
                    / Math.max(0.0001, upper - lower)
                )
            );
            const rawX = startX + i * step;
            const rawY =
                bottom - normalized * Math.max(1, bottom - top);
            points.push(Qt.point(rawX, rawY));
        }

        if (probeStartMs)
            recordArrayCopy("linePoints", source.length, copyMs, probeStartMs);
        return points;
    }

    function downsampleHistory(values, maximumPoints) {
        const probeStartMs = arrayCopyProbeEnabled ? Date.now() : 0;
        const source = Array.isArray(values) ? values : [];
        const limit = Math.max(
            2,
            Math.floor(Number(maximumPoints || source.length))
        );

        const sampled = source.length <= limit
            ? source.slice()
            : source.slice(Math.max(0, source.length - limit));
        if (probeStartMs)
            recordArrayCopy("downsampleHistory", source.length,
                            Date.now() - probeStartMs, probeStartMs);
        return sampled;
    }

    function linePointsInBand(values, graphWidth, graphHeight, requiredRange,
                              slotCount, bandIndex, bandCount) {
        const bands = Math.max(1, Number(bandCount || 1));
        const index = Math.max(
            0,
            Math.min(bands - 1, Number(bandIndex || 0))
        );
        const bandHeight = Math.max(
            4,
            Number(graphHeight || 1) / bands
        );
        const local = linePoints(
            values,
            graphWidth,
            bandHeight,
            requiredRange,
            slotCount,
            2,
            2
        );
        const offsetY = index * bandHeight;
        const points = [];

        for (let i = 0; i < local.length; i++)
            points.push(Qt.point(local[i].x, local[i].y + offsetY));

        return points;
    }

    function cssColor(colorValue, alphaMultiplier) {
        const alpha = Math.max(
            0,
            Math.min(
                1,
                Number(colorValue.a)
                * (
                    alphaMultiplier === undefined
                    ? 1.0
                    : Number(alphaMultiplier)
                )
            )
        );

        return "rgba("
               + String(Math.round(Number(colorValue.r) * 255)) + ","
               + String(Math.round(Number(colorValue.g) * 255)) + ","
               + String(Math.round(Number(colorValue.b) * 255)) + ","
               + String(alpha) + ")";
    }

    function appendBounded(values, value, maximumPoints) {
        const probeStartMs = arrayCopyProbeEnabled ? Date.now() : 0;
        const next = Array.isArray(values) ? values.slice() : [];
        const copyMs = probeStartMs ? Date.now() - probeStartMs : 0;
        const inputCount = next.length;
        const limit = Math.max(1, Math.floor(Number(maximumPoints || 1)));

        next.push(Number(value || 0));

        while (next.length > limit)
            next.shift();

        if (probeStartMs)
            recordArrayCopy("appendBounded", inputCount, copyMs, probeStartMs);
        return next;
    }
}
