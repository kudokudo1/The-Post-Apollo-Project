.pragma library

// Read-only astronomical presentation policy. The service's location-local
// observation clock is the anchor: do not silently substitute the PC time
// zone for a remote weather location. No additional network requests.
function observationEpoch(value) {
    const match = String(value || "").trim().match(
        /^(\d{4})-(\d{2})-(\d{2})\s+(\d{1,2}):(\d{2})(?::\d{2})?\s*(AM|PM)?$/i);
    if (!match)
        return NaN;
    const year = Number(match[1]), month = Number(match[2]), day = Number(match[3]);
    let hour = Number(match[4]);
    const minute = Number(match[5]);
    if (match[6]) {
        if (hour < 1 || hour > 12)
            return NaN;
        hour = hour % 12 + (match[6].toUpperCase() === "PM" ? 12 : 0);
    }
    if (hour > 23 || minute > 59 || month < 1 || month > 12 || day < 1 || day > 31)
        return NaN;
    const epoch = Date.UTC(year, month - 1, day, hour, minute);
    const check = new Date(epoch);
    return check.getUTCFullYear() === year && check.getUTCMonth() === month - 1
           && check.getUTCDate() === day ? epoch : NaN;
}

function clockMinute(text) {
    const match = String(text || "").trim().match(/^(\d{1,2}):(\d{2})\s*(AM|PM)$/i);
    if (!match)
        return -1;
    let hour = Number(match[1]);
    const minute = Number(match[2]);
    if (hour < 1 || hour > 12 || minute > 59)
        return -1;
    hour = hour % 12 + (match[3].toUpperCase() === "PM" ? 12 : 0);
    return hour * 60 + minute;
}

function normalizedPhase(value) {
    const name = String(value || "").trim().toLowerCase()
                       .replace(/[\s_-]+/g, " ");
    const names = {
        "new moon": "new", "waxing crescent": "waxing-crescent",
        "first quarter": "first-quarter", "waxing gibbous": "waxing-gibbous",
        "full moon": "full", "waning gibbous": "waning-gibbous",
        "last quarter": "last-quarter", "third quarter": "last-quarter",
        "waning crescent": "waning-crescent"
    };
    return names[name] || "unknown";
}

function dayFor(date, daily) {
    if (!Array.isArray(daily))
        return null;
    for (let i = 0; i < daily.length; i++) {
        if (daily[i] && daily[i].date === date)
            return daily[i];
    }
    return null;
}

function atLocal(date, minute, daily) {
    const day = dayFor(date, daily);
    const phase = day ? normalizedPhase(day.moonPhase) : "unknown";
    const illumination = day ? Number(day.moonIllumination) : -1;
    const light = isFinite(illumination) && illumination >= 0
                  && illumination <= 100 ? illumination : -1;
    const sunrise = day ? clockMinute(day.sunrise) : -1;
    const sunset = day ? clockMinute(day.sunset) : -1;
    let solar = "unknown";
    if (sunrise >= 0 && sunset >= 0 && sunrise < sunset
            && isFinite(minute) && minute >= 0 && minute < 1440) {
        // Presentation windows: the last 30 minutes before sunrise are
        // dawn, and the first 30 minutes after sunset are dusk. These are
        // *not* official astronomical twilight calculations.
        if (minute >= Math.max(0, sunrise - 30) && minute < sunrise)
            solar = "dawn";
        else if (minute >= sunrise && minute < sunset)
            solar = "day";
        else if (minute >= sunset && minute < Math.min(1440, sunset + 30))
            solar = "dusk";
        else
            solar = "night";
    }
    return {solar: solar, moonPhase: phase, moonIllumination: light, date: date};
}

function atObservation(nowMs, observation, anchorMs, daily) {
    const epoch = observationEpoch(observation);
    const now = Number(nowMs), anchor = Number(anchorMs);
    if (!isFinite(epoch) || !isFinite(now) || !isFinite(anchor)
            || anchor <= 0 || now < anchor - 300000 || now - anchor > 3600000)
        return {solar: "unknown", moonPhase: "unknown", moonIllumination: -1, date: ""};
    const local = new Date(epoch + Math.max(0, now - anchor));
    const date = local.getUTCFullYear() + "-"
        + String(local.getUTCMonth() + 1).padStart(2, "0") + "-"
        + String(local.getUTCDate()).padStart(2, "0");
    return atLocal(date, local.getUTCHours() * 60 + local.getUTCMinutes(), daily);
}

function forecast(date, time, daily) {
    // wttr hourly time is HHMM, e.g. 0, 300, 600, 900, 1200, 1500...
    const clock = String(time === null || time === undefined ? "" : time).trim();
    if (!/^\d{1,4}$/.test(clock))
        return atLocal(date, -1, daily);
    const hhmm = Number(clock);
    const hour = Math.floor(hhmm / 100), minute = hhmm % 100;
    return atLocal(date, hour <= 23 && minute <= 59 ? hour * 60 + minute : -1, daily);
}

// Shared night composition selector. It maps the *existing* condition
// classification to foreground artwork; it does not invent new weather
// classifications or override alerts. In particular, wind alone is not a
// cloud, and warning/unknown conditions remain their original icon.
function nightKind(conditionState) {
    const label = conditionState ? String(conditionState.label || "") : "";
    if (label === "SUNNY / CLEAR")
        return "clear";
    if (label === "PARTLY SUNNY" || label === "CLOUDS / FOG")
        return "cloud";
    if (label === "RAIN")
        return "rain";
    if (label === "SNOW / SLEET")
        return "snow";
    if (label === "HAIL / ICE PELLETS")
        return "hail";
    if (label === "THUNDERSTORM")
        return "storm";
    if (label.indexOf("HIGH WIND //") === 0)
        return "wind";
    return "none";
}

function artworkFor(conditionState, cycle) {
    // Alert and unknown precedence is inherited from WeatherDockPolicy.
    // One shared night component composes a back-left moon and any needed
    // cloud/precipitation foreground; day and dawn/dusk icons are untouched.
    const label = conditionState ? conditionState.label : "";
    const phase = cycle ? cycle.solar : "unknown";
    if (phase === "unknown")
        return "weather";
    if (phase === "night")
        return nightKind(conditionState) === "none" ? "weather" : "night-weather";
    if (label === "SUNNY / CLEAR")
        return "sun";
    if (label === "PARTLY SUNNY")
        return "sun-cloud";
    return "weather";
}
