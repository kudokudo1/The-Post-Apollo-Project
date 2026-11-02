.pragma library

// Weather live history M10.
//
// This document is a bounded chronology of successful live observations.
// It is deliberately separate from weather-last-known-v1.json:
// - last-known cache answers "what can still be shown after failure/restart?"
// - live history answers "how has this value changed over time?"
// No provider fetcher, timer, forecast archive or frame cache lives here.

var SCHEMA = "post-apollo.weather-live-history.v1";
var VERSION = 1;
var MAX_SERIES = 6;

var _rules = {
    "weather-current": {maxSamples:192, maxAgeMs:172800000},
    "air-quality": {maxSamples:192, maxAgeMs:172800000},
    "marine": {maxSamples:96, maxAgeMs:172800000},
    "coastal-water": {maxSamples:192, maxAgeMs:172800000},
    "space-wind": {maxSamples:576, maxAgeMs:172800000},
    "space-imf": {maxSamples:576, maxAgeMs:172800000}
};

function knownSourceIds() {
    return Object.keys(_rules).sort();
}

function initialDocument() {
    return {
        schema: SCHEMA,
        version: VERSION,
        revision: 0,
        series: {}
    };
}

function finiteNumber(value, fallback) {
    if (value === undefined || value === null || value === "")
        return fallback;
    const number = Number(value);
    return isFinite(number) ? number : fallback;
}

function positiveMillis(value, allowZero) {
    const number = Number(value);
    if (!isFinite(number))
        return -1;
    const integer = Math.floor(number);
    if (integer < 0 || (!allowZero && integer === 0))
        return -1;
    return integer;
}

function safeText(value, maximum) {
    const text = String(value === undefined || value === null ? "" : value);
    const limit = Math.max(1, Math.floor(Number(maximum) || 128));
    let out = "";
    for (let i = 0; i < text.length && out.length < limit; i++) {
        const code = text.charCodeAt(i);
        if (code >= 32 && code !== 127)
            out += text[i];
    }
    return out;
}

function sourceRule(sourceId) {
    const key = String(sourceId || "");
    return _rules[key] || null;
}

function normalizedScope(sourceId, raw) {
    if (!sourceRule(sourceId))
        return "";
    if (sourceId === "space-wind" || sourceId === "space-imf")
        return "global";
    const scope = safeText(raw, 96);
    return scope.length > 0 ? scope : "";
}

function normalizedPayload(sourceId, value) {
    const source = value && typeof value === "object" ? value : {};

    if (sourceId === "weather-current") {
        const tempF = finiteNumber(source.tempF, null);
        const feelsLikeF = finiteNumber(source.feelsLikeF, null);
        const humidity = finiteNumber(source.humidity, null);
        const windMph = finiteNumber(source.windMph, null);
        const pressureHpa = finiteNumber(source.pressureHpa, null);
        if (tempF === null || humidity === null)
            return null;
        return {
            tempF: tempF,
            feelsLikeF: feelsLikeF,
            humidity: humidity,
            windMph: windMph,
            pressureHpa: pressureHpa,
            visibilityMiles: finiteNumber(source.visibilityMiles, null),
            cloudCover: finiteNumber(source.cloudCover, null),
            precipMm: finiteNumber(source.precipMm, null),
            uvIndex: finiteNumber(source.uvIndex, null),
            condition: safeText(source.condition, 80)
        };
    }

    if (sourceId === "air-quality") {
        const aqi = finiteNumber(source.aqi, null);
        if (aqi === null || aqi < 0 || aqi > 500)
            return null;
        return {
            aqi: Math.round(aqi),
            pm25: finiteNumber(source.pm25, null),
            pm10: finiteNumber(source.pm10, null),
            ozoneAqi: finiteNumber(source.ozoneAqi, null),
            nitrogenDioxideAqi:
                finiteNumber(source.nitrogenDioxideAqi, null),
            carbonMonoxideAqi:
                finiteNumber(source.carbonMonoxideAqi, null),
            ozone: finiteNumber(source.ozone, null),
            nitrogenDioxide: finiteNumber(source.nitrogenDioxide, null),
            carbonMonoxide: finiteNumber(source.carbonMonoxide, null),
            dust: finiteNumber(source.dust, null)
        };
    }

    if (sourceId === "marine") {
        const stationId = safeText(source.stationId, 24);
        const sampleMillis = positiveMillis(source.sampleMillis, false);
        if (!stationId || sampleMillis <= 0)
            return null;
        return {
            stationId: stationId,
            sampleMillis: sampleMillis,
            windDirection: finiteNumber(source.windDirection, null),
            windSpeedMs: finiteNumber(source.windSpeedMs, null),
            gustMs: finiteNumber(source.gustMs, null),
            waveHeightM: finiteNumber(source.waveHeightM, null),
            pressureHpa: finiteNumber(source.pressureHpa, null),
            airTempC: finiteNumber(source.airTempC, null),
            waterTempC: finiteNumber(source.waterTempC, null),
            visibilityNm: finiteNumber(source.visibilityNm, null),
            tideFt: finiteNumber(source.tideFt, null)
        };
    }

    if (sourceId === "coastal-water") {
        const stationId = safeText(source.stationId, 24);
        const sampleMillis = positiveMillis(source.sampleMillis, false);
        const waterLevel = finiteNumber(source.waterLevel, null);
        if (!stationId || sampleMillis <= 0 || waterLevel === null)
            return null;
        return {
            stationId: stationId,
            sampleMillis: sampleMillis,
            waterLevel: waterLevel,
            sigma: finiteNumber(source.sigma, null),
            quality: safeText(source.quality, 24)
        };
    }

    if (sourceId === "space-wind") {
        const speed = finiteNumber(source.solarWindSpeed, null);
        if (speed === null || speed < 0)
            return null;
        return {
            solarWindSpeed: speed,
            sourceTime: safeText(source.sourceTime, 64)
        };
    }

    if (sourceId === "space-imf") {
        const bt = finiteNumber(source.bt, null);
        const bz = finiteNumber(source.bz, null);
        if (bt === null || bz === null)
            return null;
        return {
            bt: bt,
            bz: bz,
            sourceTime: safeText(source.sourceTime, 64)
        };
    }

    return null;
}

function normalizeSample(sourceId, value) {
    const source = value && typeof value === "object" ? value : {};
    const observedAtMs = positiveMillis(source.observedAtMs, false);
    const receivedAtMs = positiveMillis(source.receivedAtMs, false);
    const payload = normalizedPayload(sourceId, source.payload);
    if (observedAtMs <= 0 || receivedAtMs <= 0 || !payload)
        return null;
    return {
        observedAtMs: observedAtMs,
        receivedAtMs: receivedAtMs,
        payload: payload
    };
}

function dedupeAndBound(sourceId, samples, nowMs) {
    const rule = sourceRule(sourceId);
    if (!rule)
        return [];

    const source = Array.isArray(samples) ? samples : [];
    const byObserved = {};
    for (let i = 0; i < source.length; i++) {
        const sample = normalizeSample(sourceId, source[i]);
        if (!sample)
            continue;
        const key = String(sample.observedAtMs);
        const existing = byObserved[key];
        if (!existing || sample.receivedAtMs >= existing.receivedAtMs)
            byObserved[key] = sample;
    }

    let rows = Object.keys(byObserved).map(function(key) {
        return byObserved[key];
    });
    rows.sort(function(a, b) {
        return a.observedAtMs - b.observedAtMs;
    });

    const now = positiveMillis(nowMs, false);
    if (now > 0) {
        const floor = now - Number(rule.maxAgeMs);
        rows = rows.filter(function(row) {
            return row.receivedAtMs >= floor;
        });
    }

    const limit = Number(rule.maxSamples) || 1;
    if (rows.length > limit)
        rows = rows.slice(rows.length - limit);
    return rows;
}

function normalizeSeries(sourceId, value, nowMs) {
    const source = value && typeof value === "object" ? value : {};
    const scopeKey = normalizedScope(sourceId, source.scopeKey);
    if (!scopeKey)
        return null;
    const samples = dedupeAndBound(sourceId, source.samples, nowMs);
    return {
        sourceId: sourceId,
        scopeKey: scopeKey,
        samples: samples
    };
}

function normalizeDocument(value, nowMs) {
    if (!value || typeof value !== "object" || Array.isArray(value))
        return null;
    if (value.schema !== SCHEMA || Number(value.version) !== VERSION)
        return null;

    const sourceSeries = value.series
        && typeof value.series === "object"
        && !Array.isArray(value.series)
        ? value.series : {};
    const series = {};
    const ids = knownSourceIds();
    for (let i = 0; i < ids.length; i++) {
        const id = ids[i];
        if (!sourceSeries[id])
            continue;
        const normalized = normalizeSeries(id, sourceSeries[id], nowMs);
        if (normalized)
            series[id] = normalized;
    }

    return {
        schema: SCHEMA,
        version: VERSION,
        revision: Math.max(0, Math.floor(Number(value.revision) || 0)),
        series: series
    };
}

function parse(raw, nowMs) {
    const text = String(raw || "").trim();
    if (!text)
        return {ok:true, document:initialDocument(), reason:"EMPTY"};
    try {
        const parsed = JSON.parse(text);
        if (!parsed || parsed.schema !== SCHEMA)
            return {ok:false, document:initialDocument(), reason:"INVALID_SCHEMA"};
        if (Number(parsed.version) !== VERSION)
            return {
                ok:false,
                document:initialDocument(),
                reason:"UNSUPPORTED_VERSION"
            };
        const document = normalizeDocument(parsed, nowMs);
        return document
            ? {ok:true, document:document, reason:""}
            : {ok:false, document:initialDocument(), reason:"INVALID_DOCUMENT"};
    } catch (error) {
        return {ok:false, document:initialDocument(), reason:"INVALID_JSON"};
    }
}

function copyDocument(document, nowMs) {
    const normalized = normalizeDocument(document, nowMs);
    return normalized || initialDocument();
}

function append(
    document, sourceId, scopeKey,
    observedAtMs, receivedAtMs, payload, savedAtMs
) {
    const id = String(sourceId || "");
    if (!sourceRule(id))
        return {ok:false, document:copyDocument(document), reason:"UNKNOWN_SOURCE"};

    const scope = normalizedScope(id, scopeKey);
    if (!scope)
        return {ok:false, document:copyDocument(document), reason:"SCOPE_REQUIRED"};

    const observed = positiveMillis(observedAtMs, false);
    const received = positiveMillis(receivedAtMs, false);
    const saved = positiveMillis(savedAtMs, false);
    const payloadValue = normalizedPayload(id, payload);
    if (observed <= 0 || received <= 0 || saved <= 0 || !payloadValue)
        return {ok:false, document:copyDocument(document), reason:"INVALID_SAMPLE"};

    const next = copyDocument(document, saved);
    const existing = next.series[id];
    let samples = [];
    if (existing && existing.scopeKey === scope)
        samples = existing.samples.slice();

    samples.push({
        observedAtMs: observed,
        receivedAtMs: received,
        payload: payloadValue
    });
    samples = dedupeAndBound(id, samples, saved);

    next.series[id] = {
        sourceId: id,
        scopeKey: scope,
        samples: samples
    };
    next.revision += 1;
    return {ok:true, document:next, reason:""};
}

function samples(document, sourceId, scopeKey, nowMs) {
    const id = String(sourceId || "");
    const scope = normalizedScope(id, scopeKey);
    if (!scope)
        return [];
    const normalized = copyDocument(document, nowMs);
    const series = normalized.series[id];
    if (!series || series.scopeKey !== scope)
        return [];
    return dedupeAndBound(id, series.samples, nowMs);
}

function count(document, sourceId, scopeKey, nowMs) {
    return samples(document, sourceId, scopeKey, nowMs).length;
}

function latest(document, sourceId, scopeKey, nowMs) {
    const rows = samples(document, sourceId, scopeKey, nowMs);
    return rows.length > 0 ? rows[rows.length - 1] : null;
}

function numericTrend(document, sourceId, scopeKey, field, nowMs) {
    const rows = samples(document, sourceId, scopeKey, nowMs);
    const values = [];
    for (let i = 0; i < rows.length; i++) {
        const value = finiteNumber(rows[i].payload[field], null);
        if (value !== null)
            values.push({
                value:value,
                observedAtMs:rows[i].observedAtMs
            });
    }
    if (values.length === 0) {
        return {
            count:0, first:null, latest:null, delta:null,
            minimum:null, maximum:null, spanMs:0
        };
    }

    let minimum = values[0].value;
    let maximum = values[0].value;
    for (let i = 1; i < values.length; i++) {
        minimum = Math.min(minimum, values[i].value);
        maximum = Math.max(maximum, values[i].value);
    }

    const first = values[0];
    const last = values[values.length - 1];
    return {
        count:values.length,
        first:first.value,
        latest:last.value,
        delta:last.value - first.value,
        minimum:minimum,
        maximum:maximum,
        spanMs:Math.max(0, last.observedAtMs - first.observedAtMs)
    };
}
