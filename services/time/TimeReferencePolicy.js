.pragma library

// Only read-only time reference evidence lives here. Persist a completed
// measurement separately from attempts, failures, display calibration and
// privileged RESYNC. Estimation never changes the host clock.
var VERSION = 1;
var MAX_AGE_MS = 15 * 60 * 1000;
var MAX_STORED_AGE_MS = 7 * 24 * 60 * 60 * 1000;
var MAX_OFFSET_MS = 24 * 60 * 60 * 1000;
var MAX_ERROR_LENGTH = 180;

function timestamp(value) {
    return typeof value === "number" && isFinite(value)
           && Math.floor(value) === value && value >= 0
           && value <= 8640000000000000;
}

function bootId(value) {
    return typeof value === "string"
           && /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/.test(value);
}

function validSample(sample) {
    return !!sample && typeof sample === "object" && !Array.isArray(sample)
           && timestamp(sample.checkedAtMs) && sample.checkedAtMs > 0
           && bootId(sample.bootId)
           && (sample.source === "CHRONY_TRACKING"
               || sample.source === "CHRONYD_ONESHOT")
           && typeof sample.offsetMs === "number" && isFinite(sample.offsetMs)
           && Math.abs(sample.offsetMs) <= MAX_OFFSET_MS
           && typeof sample.uncertaintyMs === "number"
           && isFinite(sample.uncertaintyMs)
           && sample.uncertaintyMs >= 0
           && sample.uncertaintyMs <= MAX_OFFSET_MS
           && typeof sample.trendPpm === "number"
           && isFinite(sample.trendPpm) && Math.abs(sample.trendPpm) <= 100
           && typeof sample.trendKnown === "boolean";
}

function initialDocument() {
    return { version: VERSION, sample: null,
             lastAttemptAtMs: 0, lastFailureAtMs: 0, lastError: "" };
}

function parse(raw) {
    var value;
    try { value = JSON.parse(String(raw)); }
    catch (error) { return { ok: false, reason: "INVALID_JSON" }; }
    if (!value || typeof value !== "object" || Array.isArray(value)
            || value.version !== VERSION)
        return { ok: false, reason: "INVALID_DOCUMENT" };
    if ((value.sample !== null && !validSample(value.sample))
            || !timestamp(value.lastAttemptAtMs)
            || !timestamp(value.lastFailureAtMs)
            || typeof value.lastError !== "string"
            || value.lastError.length > MAX_ERROR_LENGTH
            || value.lastFailureAtMs > value.lastAttemptAtMs)
        return { ok: false, reason: "INVALID_EVIDENCE" };
    return { ok: true, document: {
        version: VERSION,
        sample: value.sample === null ? null : {
            checkedAtMs: value.sample.checkedAtMs,
            bootId: value.sample.bootId, source: value.sample.source,
            offsetMs: value.sample.offsetMs,
            uncertaintyMs: value.sample.uncertaintyMs,
            trendPpm: value.sample.trendPpm,
            trendKnown: value.sample.trendKnown
        },
        lastAttemptAtMs: value.lastAttemptAtMs,
        lastFailureAtMs: value.lastFailureAtMs,
        lastError: value.lastError
    }};
}

function withMeasurement(doc, reading, checkedAtMs, currentBootId) {
    if (!doc || !timestamp(checkedAtMs) || checkedAtMs === 0
            || !bootId(currentBootId) || !reading
            || (reading.source !== "CHRONY_TRACKING"
                && reading.source !== "CHRONYD_ONESHOT")
            || typeof reading.offsetMs !== "number"
            || !isFinite(reading.offsetMs)
            || Math.abs(reading.offsetMs) > MAX_OFFSET_MS
            || typeof reading.uncertaintyMs !== "number"
            || !isFinite(reading.uncertaintyMs)
            || reading.uncertaintyMs < 0
            || reading.uncertaintyMs > MAX_OFFSET_MS)
        return { ok: false, reason: "INVALID_MEASUREMENT" };

    // Never extrapolate Chrony's live correction from its uncorrected
    // oscillator frequency. For an inactive daemon, two comparable
    // measurements can establish a bounded, provisional observed trend.
    var trendPpm = 0;
    var trendKnown = false;
    var prior = doc.sample;
    if (reading.source === "CHRONYD_ONESHOT" && validSample(prior)
            && prior.source === "CHRONYD_ONESHOT"
            && prior.bootId === currentBootId) {
        var elapsed = checkedAtMs - prior.checkedAtMs;
        if (elapsed >= 60 * 1000 && elapsed <= 6 * 60 * 60 * 1000) {
            var observed = (reading.offsetMs - prior.offsetMs)
                           * 1000000 / elapsed;
            if (isFinite(observed) && Math.abs(observed) <= 100) {
                trendPpm = observed;
                trendKnown = true;
            }
        }
    }
    return { ok: true, document: {
        version: VERSION,
        sample: { checkedAtMs: checkedAtMs, bootId: currentBootId,
                  source: reading.source, offsetMs: reading.offsetMs,
                  uncertaintyMs: reading.uncertaintyMs,
                  trendPpm: trendPpm, trendKnown: trendKnown },
        lastAttemptAtMs: checkedAtMs,
        lastFailureAtMs: 0, lastError: ""
    }};
}

function withFailure(doc, atMs, message) {
    if (!doc || !timestamp(atMs) || atMs === 0)
        return { ok: false, reason: "INVALID_FAILURE" };
    return { ok: true, document: {
        version: VERSION,
        sample: validSample(doc.sample) ? doc.sample : null,
        lastAttemptAtMs: atMs, lastFailureAtMs: atMs,
        lastError: String(message || "REFERENCE UNAVAILABLE")
                   .slice(0, MAX_ERROR_LENGTH)
    }};
}

function estimate(doc, nowMs, currentBootId) {
    var empty = { available: false, fresh: false, ageMs: 0,
                  offsetMs: 0, uncertaintyMs: 0, predicted: false };
    if (!doc || !validSample(doc.sample) || !bootId(currentBootId)
            || doc.sample.bootId !== currentBootId || !timestamp(nowMs))
        return empty;
    var sample = doc.sample;
    var age = nowMs - sample.checkedAtMs;
    // A reboot or backwards wall-clock step invalidates the old reference.
    if (age < 0 || age > MAX_STORED_AGE_MS)
        return empty;
    var predicted = sample.source === "CHRONYD_ONESHOT" && sample.trendKnown;
    // Chrony's live slew is NOT modeled by its oscillator frequency.
    var offset = sample.offsetMs
                 + (predicted ? age * sample.trendPpm / 1000000 : 0);
    // Unknown oscillator drift and intervening Chrony corrections widen the
    // bound over time. This is conservative local arithmetic, not a new poll.
    var ppmBound = sample.source === "CHRONY_TRACKING" ? 1000
                 : predicted ? Math.max(100, Math.abs(sample.trendPpm) * 2)
                 : 100;
    var uncertainty = sample.uncertaintyMs + age * ppmBound / 1000000;
    return { available: true, fresh: age <= MAX_AGE_MS, ageMs: age,
             offsetMs: offset, uncertaintyMs: uncertainty,
             predicted: predicted };
}
