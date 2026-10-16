.pragma library

// Pure, read-only interpretation of EXISTING hwmon fan snapshots.
// fanN_min is a driver-exposed/configured threshold, NOT proof of an
// equipment safety limit. A stopped fan may be intentional (zero-RPM mode).
function numeric(raw) {
    if (raw === null || raw === undefined || raw === ""
            || typeof raw === "boolean")
        return null;
    const n = Number(raw);
    return isFinite(n) && n >= 0 ? n : null;
}

function reading(sensor) {
    if (!sensor || sensor.sensorKind !== "fan"
            || sensor.rpmAvailable !== true)
        return null; // PWM-only/target-only channels have no tachometer.
    const rpm = numeric(sensor.rpm);
    const min = numeric(sensor.minRpm);
    const pwm = numeric(sensor.pwmPercent);
    if (rpm === null || min === null || min <= 0 || min > 30000
            || rpm > 30000 || (pwm !== null && pwm > 100))
        return null;
    const driveReported = pwm !== null && pwm >= 50;
    // Below positive min while spinning is meaningful. 0 RPM alone isn't.
    // Demand is a heuristic to corroborate a stalled tachometer, not proof
    // of a broken fan or an override of firmware fan-stop policy.
    const concerning = (rpm > 0 && rpm < min)
                    || (rpm === 0 && driveReported);
    return { rpm: rpm, minRpm: min, pwmPercent: pwm,
             driveReported: driveReported, concerning: concerning };
}

function initial() {
    return { active: false, badCount: 0, badSinceMs: 0,
             goodCount: 0, goodSinceMs: 0, lastSampleMs: 0 };
}
function clearCounts(state) {
    state.badCount = 0;
    state.badSinceMs = 0;
    state.goodCount = 0;
    state.goodSinceMs = 0;
}
// Three fresh consecutive readings spanning >=3.5s confirm below-min
// behavior and >=min recovery. An unseen tachometer or firmware fan-stop
// never establishes "recovered". Gaps >15s invalidate pending streaks.
function transition(previous, sensor, observedMs) {
    const old = previous || initial();
    const state = {
        active: old.active === true,
        badCount: Number(old.badCount || 0),
        badSinceMs: Number(old.badSinceMs || 0),
        goodCount: Number(old.goodCount || 0),
        goodSinceMs: Number(old.goodSinceMs || 0),
        lastSampleMs: Number(old.lastSampleMs || 0)
    };
    const obs = reading(sensor);
    if (!obs || !isFinite(observedMs) || observedMs <= 0
            || observedMs <= state.lastSampleMs)
        return { state: state, event: "", observation: obs };

    if (state.lastSampleMs > 0 && observedMs - state.lastSampleMs > 15000)
        clearCounts(state);
    state.lastSampleMs = observedMs;

    if (obs.concerning) {
        state.goodCount = 0;
        state.goodSinceMs = 0;
        if (!state.active) {
            if (state.badCount === 0)
                state.badSinceMs = observedMs;
            state.badCount += 1;
            if (state.badCount >= 3
                    && observedMs - state.badSinceMs >= 3500) {
                state.active = true;
                state.badCount = 0;
                state.badSinceMs = 0;
                return { state: state, event: "warning", observation: obs };
            }
        }
        return { state: state, event: "", observation: obs };
    }

    state.badCount = 0;
    state.badSinceMs = 0;
    // A fan settling intentionally at zero RPM is not a verified recovery.
    const recovered = obs.rpm >= obs.minRpm;
    if (state.active && recovered) {
        if (state.goodCount === 0)
            state.goodSinceMs = observedMs;
        state.goodCount += 1;
        if (state.goodCount >= 3
                && observedMs - state.goodSinceMs >= 3500) {
            state.active = false;
            state.goodCount = 0;
            state.goodSinceMs = 0;
            return { state: state, event: "recovered", observation: obs };
        }
    } else {
        state.goodCount = 0;
        state.goodSinceMs = 0;
    }
    return { state: state, event: "", observation: obs };
}
