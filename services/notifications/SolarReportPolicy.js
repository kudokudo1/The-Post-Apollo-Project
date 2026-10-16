.pragma library

// A daily observational digest from SpaceService's NOAA products, not a
// forecast or an official SWPC warning. Time tags are NOAA UTC timestamps.

function observationTimeMs(value) {
    const raw = String(value || "").trim();
    if (!raw)
        return NaN;

    let iso = raw.replace(" ", "T");
    if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?$/.test(iso))
        iso += "Z";

    const parsed = Date.parse(iso);
    return isFinite(parsed) ? parsed : NaN;
}

function freshEnough(timestamp, nowMs, limitMs) {
    const observed = observationTimeMs(timestamp);
    if (!isFinite(observed) || !isFinite(nowMs))
        return false;
    const age = nowMs - observed;
    return age >= -10 * 60 * 1000 && age <= limitMs;
}

function localDayKey(date) {
    const pad = function(value) { return String(value).padStart(2, "0"); };
    return String(date.getFullYear()) + "-" + pad(date.getMonth() + 1)
         + "-" + pad(date.getDate());
}

function snapshot(space, nowMs) {
    if (!space || !space.ready)
        return null;

    const kp = Number(space.kp);
    const wind = Number(space.solarWindSpeed);
    const bt = Number(space.magneticFieldBt);
    const bz = Number(space.magneticFieldBz);
    const flux = Number(space.solarFlux);

    if (!isFinite(kp) || kp < 0 || kp > 9
            || !isFinite(wind) || wind < 0 || wind > 3000
            || !isFinite(bt) || bt < 0 || bt > 500
            || !isFinite(bz) || Math.abs(bz) > 500
            || !isFinite(flux) || flux < 20 || flux > 1000)
        return null;

    // Planetary Kp covers a longer period; radio flux is a daily measure.
    // Wind and magnetic-field summaries should be much more recent.
    if (!freshEnough(space.kpTime, nowMs, 8 * 60 * 60 * 1000)
            || !freshEnough(space.solarWindTime, nowMs, 2 * 60 * 60 * 1000)
            || !freshEnough(space.magneticFieldTime, nowMs, 2 * 60 * 60 * 1000)
            || !freshEnough(space.solarFluxTime, nowMs, 48 * 60 * 60 * 1000))
        return null;

    return {
        kp: kp,
        kpLabel: String(space.kpLabel || "UNKNOWN"),
        solarWindKmS: wind,
        btNt: bt,
        bzNt: bz,
        bzLabel: String(space.bzLabel || "UNKNOWN"),
        solarFluxSfu: flux,
        observed: {
            kp: String(space.kpTime),
            solarWind: String(space.solarWindTime),
            magneticField: String(space.magneticFieldTime),
            solarFlux: String(space.solarFluxTime)
        }
    };
}

function summary(data) {
    return "KP " + data.kp.toFixed(1) + " " + data.kpLabel
           + " // WIND " + Math.round(data.solarWindKmS) + " KM/S\n"
           + "Bz " + data.bzNt.toFixed(1) + " nT " + data.bzLabel
           + " // Bt " + data.btNt.toFixed(1) + " nT\n"
           + "F10.7 SOLAR FLUX " + Math.round(data.solarFluxSfu)
           + " SFU // NOAA observed data";
}
