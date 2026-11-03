.pragma library

// M6c: read-only diagnostics derived from the existing one WeatherService.
// No request, timer, disk write or location mutation belongs to this policy.
function millis(value) {
    if (value === undefined || value === null || value === "")
        return -1;
    const ms = typeof value === "number" ? value : new Date(value).getTime();
    return isFinite(ms) && ms > 0 ? ms : -1;
}

function ageText(value, nowRaw) {
    const received = millis(value);
    const now = millis(nowRaw);
    if (received <= 0 || now <= 0 || received > now)
        return "--";
    const minutes = Math.floor((now - received) / 60000);
    if (minutes < 1)
        return "<1m";
    if (minutes < 60)
        return minutes + "m";
    if (minutes < 1440)
        return Math.floor(minutes / 60) + "h " + (minutes % 60) + "m";
    return Math.floor(minutes / 1440) + "d";
}

function providerName(key) {
    switch (String(key || "").toUpperCase()) {
    case "WTTR": return "WTTR.IN";
    case "OPEN_METEO": return "OPEN-METEO";
    case "OPEN_METEO_AQI": return "OPEN-METEO AQI";
    case "CACHE": return "CACHE";
    default: return "NONE";
    }
}

function stateFor(raw) {
    switch (String(raw || "").toUpperCase()) {
    case "READY": return "LIVE";
    case "FETCHING": return "READING";
    case "REQUEST_FAILED": return "REQUEST FAILED";
    case "PARSE_FAILED": return "DATA INVALID";
    case "NO_MANUAL_PLACE": return "NO SELECTED PLACE";
    case "IDLE": return "IDLE";
    default: return "UNKNOWN";
    }
}

function snapshot(input, nowMs) {
    const s = input || {};
    const ready = s.ready === true;
    const cached = ready && (s.usingCache === true
                              || String(s.activeProvider) === "CACHE");
    const provider = String(s.activeProvider || "NONE");
    const original = cached ? providerName(s.cachedProvider)
                            : providerName(provider);
    const primary = stateFor(s.primaryStatus);
    const fallback = stateFor(s.fallbackStatus);
    const aqiCached = s.aqiReady === true && s.aqiUsingCache === true;
    const aqi = aqiCached ? "CACHE"
               : s.aqiLoading === true ? "READING"
               : s.aqiReady === true ? "LIVE"
               : String(s.aqiError || "").trim() ? "FAILED"
               : "WAITING";

    let currentState = "WAITING";
    if (cached)
        currentState = "CACHE";
    else if (ready && provider === "OPEN_METEO")
        currentState = "FALLBACK";
    else if (ready && provider === "WTTR")
        currentState = "LIVE";
    else if (s.loading)
        currentState = "READING";
    else if (String(s.error || "").trim()
             || primary === "REQUEST FAILED" || primary === "DATA INVALID")
        currentState = "OFFLINE";

    let header = "WEATHER // WAIT";
    if (currentState === "CACHE")
        header = "CACHE // " + (original === "NONE" ? "UNKNOWN"
                                                      : original === "OPEN-METEO"
                                                      ? "METEO" : "WTTR");
    else if (currentState === "FALLBACK")
        header = "FALLBACK // METEO";
    else if (currentState === "LIVE")
        header = "LIVE // WTTR";
    else if (currentState === "READING")
        header = "WEATHER // READING";
    else if (currentState === "OFFLINE")
        header = "WEATHER // OFFLINE";

    const primaryFailure =
        primary === "REQUEST FAILED" || primary === "DATA INVALID";
    let reason = "NO FAILURE REPORTED";
    if (currentState === "FALLBACK")
        reason = primaryFailure ? "PRIMARY " + primary
                                : "PRIMARY UNAVAILABLE";
    else if (currentState === "CACHE")
        reason = "LAST-KNOWN SNAPSHOT // NOT A LIVE READING";
    else if (currentState === "OFFLINE")
        reason = String(s.fallbackError || s.error || "PROVIDERS UNAVAILABLE");
    else if (primaryFailure)
        reason = "PRIMARY " + primary;
    else if (s.loading)
        reason = "PROVIDER REQUEST IN PROGRESS";

    const selected = s.selectedPlace && typeof s.selectedPlace === "object"
                     ? s.selectedPlace : null;
    const location = selected && String(selected.label || "").trim()
                     ? String(selected.label).slice(0, 64)
                     : "UNSPECIFIED // LEGACY LOCATION";

    return {
        currentState:currentState,
        header:header,
        origin:original,
        reason:reason,
        location:location,
        currentAge:ageText(s.lastUpdated, nowMs),
        currentAt:millis(s.lastUpdated),
        primary:{
            label:"WTTR.IN",
            state:primary,
            age:ageText(s.primaryLastSuccessAt,nowMs)
        },
        fallback:{
            label:"OPEN-METEO",
            state:fallback,
            age:ageText(s.fallbackLastSuccessAt,nowMs),
            error:String(s.fallbackError || "").slice(0,120)
        },
        aqi:{
            label:"AIR QUALITY / OPEN-METEO",
            state:aqi,
            age:ageText(s.aqiLastUpdated,nowMs),
            error:String(s.aqiError || "").slice(0,120)
        },
        providerLabel:cached ? "CACHE // " + original
                             : currentState === "FALLBACK"
                             ? "OPEN-METEO // FALLBACK"
                             : original
    };
}
