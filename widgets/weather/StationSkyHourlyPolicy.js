.pragma library

// Display-only formatting for wttr.in's already parsed hourly fields.
// Never interpret a missing forecast value as safe/zero. No new provider,
// timer, network request, or historical observation is created here.
function numberInRange(value, minimum, maximum) {
    if (value === undefined || value === null || String(value).trim() === "")
        return null;
    const n = Number(value);
    return isFinite(n) && n >= minimum && n <= maximum ? n : null;
}

function reading(value, minimum, maximum, decimals, unit) {
    const n = numberInRange(value, minimum, maximum);
    return n === null ? "--" : n.toFixed(decimals) + unit;
}

function windText(speed, direction) {
    const mph = reading(speed, 0, 300, 0, " MPH");
    if (mph === "--")
        return mph;
    const compass = String(direction || "").trim().toUpperCase();
    const valid = /^(N|NNE|NE|ENE|E|ESE|SE|SSE|S|SSW|SW|WSW|W|WNW|NW|NNW)$/.test(compass);
    return mph + (valid ? " // " + compass : "");
}

function hourlyMetrics(entry) {
    if (!entry)
        return [];
    return [
        {title: "FEELS LIKE", value: reading(entry.feelsLikeF, -900, 200, 0, "°F")},
        {title: "DEW POINT", value: reading(entry.dewPointF, -900, 200, 0, "°F")},
        {title: "HUMIDITY", value: reading(entry.humidity, 0, 100, 0, "%")},
        {title: "WIND", value: windText(entry.windMph, entry.windDirection)},
        {title: "PRESSURE", value: reading(entry.pressureHpa, 800, 1150, 0, " hPa")},
        {title: "VISIBILITY", value: reading(entry.visibilityMiles, 0, 200, 1, " mi")},
        {title: "CLOUD COVER", value: reading(entry.cloudCover, 0, 100, 0, "%")},
        {title: "PRECIP", value: reading(entry.precipMm, 0, 300, 1, " mm")},
        {title: "RAIN CHANCE", value: reading(entry.chanceRain, 0, 100, 0, "%")},
        {title: "SNOW CHANCE", value: reading(entry.chanceSnow, 0, 100, 0, "%")},
        {title: "UV INDEX", value: reading(entry.uvIndex, 0, 30, 0, "")}
    ];
}

function selectedHour(forecast, index) {
    if (!Array.isArray(forecast) || forecast.length === 0)
        return null;
    const offset = Number(index);
    return forecast[isFinite(offset) && offset >= 0
                    && offset < forecast.length ? Math.floor(offset) : 0];
}

function hourCaption(entry) {
    if (!entry)
        return "NO HOURLY FORECAST AVAILABLE";
    const date = /^\d{4}-\d{2}-\d{2}$/.test(String(entry.date || ""))
                 ? String(entry.date) : "DATE --";
    const time = String(entry.timeLabel || "--").slice(0, 12);
    const condition = String(entry.condition || "UNKNOWN").slice(0, 48).toUpperCase();
    return date + " // " + time + " // " + condition;
}
