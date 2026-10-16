.pragma library

// Use only actual hardware-reported high/critical thresholds. Missing
// thresholds (the SystemTelemetry zero sentinel) must never become alerts.
function numeric(value) {
    if (value === null || value === undefined || value === ""
            || typeof value === "boolean")
        return null;
    const n = Number(value);
    return isFinite(n) ? n : null;
}

function limits(sensor) {
    if (!sensor || sensor.sensorKind !== "temperature")
        return null;
    const temp = numeric(sensor.tempC);
    const high = numeric(sensor.highC);
    const crit = numeric(sensor.critC);
    if (temp === null || temp < -60 || temp > 200)
        return null;
    const validHigh = high !== null && high > 0 && high <= 200 ? high : null;
    const validCrit = crit !== null && crit > 0 && crit <= 200 ? crit : null;
    if (validHigh === null && validCrit === null)
        return null;
    return { temp: temp, high: validHigh, crit: validCrit };
}

function level(reading) {
    if (!reading)
        return 0;
    if (reading.crit !== null && reading.temp >= reading.crit)
        return 2;
    if (reading.high !== null && reading.temp >= reading.high)
        return 1;
    return 0;
}

function coolBelowHysteresis(reading) {
    if (!reading)
        return false;
    const start = reading.high !== null ? reading.high : reading.crit;
    return reading.temp <= start - 3;
}

function initial() {
    return { sent: 0, candidate: 0, candidateCount: 0, clearCount: 0 };
}

// Two consecutive above-threshold samples are needed for the initial
// warning or escalation. Recovery requires two cool readings at least
// 3°C below the applicable threshold. Invalid samples do not reset state.
function transition(previous, sensor) {
    const state = previous ? {
        sent: Number(previous.sent) || 0,
        candidate: Number(previous.candidate) || 0,
        candidateCount: Number(previous.candidateCount) || 0,
        clearCount: Number(previous.clearCount) || 0
    } : initial();
    const reading = limits(sensor);
    if (!reading)
        return { state: state, emit: 0, reading: null };

    const current = level(reading);
    let emit = 0;
    if (current > state.sent) {
        state.clearCount = 0;
        state.candidateCount = state.candidate === current
                               ? state.candidateCount + 1 : 1;
        state.candidate = current;
        if (state.candidateCount >= 2) {
            state.sent = current;
            state.candidate = 0;
            state.candidateCount = 0;
            emit = current;
        }
    } else {
        state.candidate = 0;
        state.candidateCount = 0;
        if (state.sent > 0 && current === 0
                && coolBelowHysteresis(reading)) {
            state.clearCount += 1;
            if (state.clearCount >= 2) {
                state.sent = 0;
                state.clearCount = 0;
            }
        } else {
            state.clearCount = 0;
        }
    }

    return { state: state, emit: emit, reading: reading };
}
