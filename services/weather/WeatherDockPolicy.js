.pragma library

// Pure presentation policy for the 50px Weather dock module.
// No network requests, geolocation, or inference of official warnings.
function fresh(timestampMs, nowMs) {
    const timestamp = Number(timestampMs);
    const now = Number(nowMs);
    return isFinite(timestamp) && timestamp > 0 && isFinite(now)
           && now >= timestamp - 300000 && now - timestamp <= 3600000;
}

// The service reports Fahrenheit. Convert only for presentation, so the
// alternate dock mode does not introduce another network fetch.
function formatTemperature(fahrenheit, isFresh, useCelsius) {
    const unit = useCelsius ? "°C" : "°F";
    if (!isFresh || fahrenheit === null || fahrenheit === undefined
            || String(fahrenheit).trim() === "")
        return "--" + unit;

    const value = Number(fahrenheit);
    if (!isFinite(value) || value < -150 || value > 150)
        return "--" + unit;

    const displayed = useCelsius ? (value - 32) * 5 / 9 : value;
    const rounded = Math.round(displayed);
    return (rounded === 0 ? 0 : rounded) + unit;
}

// The thermometer reports absolute air temperature, never relative comfort,
// wind chill, heat index, UV exposure, or weather-alert severity.
function temperatureState(fahrenheit, isFresh) {
    if (!isFresh || fahrenheit === null || fahrenheit === undefined ||
            String(fahrenheit).trim() === "")
        return { "valid": false, "color": "white", "level": 0 };

    const value = Number(fahrenheit);
    if (!isFinite(value) || value < -150 || value > 150)
        return { "valid": false, "color": "white", "level": 0 };

    const color = value <= 15 ? "white"
                : value <= 32 ? "cyan"
                : value <= 49 ? "blue"
                : value <= 59 ? "magenta"
                : value <= 75 ? "yellow"
                : value <= 89 ? "orange"
                : "red";

    // -20°F to 110°F gives a legible gauge across normal outdoor readings.
    // Outside that range, clamp the column; the bulb stays filled if valid.
    const level = Math.max(0, Math.min(1, (value + 20) / 130));
    return { "valid": true, "color": color, "level": level };
}

function state(color, icon, label) {
    return { "color": color, "icon": icon, "label": label };
}

function includesCode(code, codes) {
    return codes.indexOf(code) !== -1;
}

function classify(reading) {
    const weatherFresh = reading.ready === true && !reading.errorText
                         && fresh(reading.weatherTimeMs, reading.nowMs);
    const aqiFresh = reading.aqiReady === true && !reading.aqiErrorText
                     && fresh(reading.aqiTimeMs, reading.nowMs);

    const uv = Number(reading.uvIndex);
    const aqi = Number(reading.aqi);
    if (weatherFresh && isFinite(uv) && uv >= 8 && uv <= 20)
        return state("red", "⚠︎", "VERY HIGH UV " + uv);
    if (aqiFresh && isFinite(aqi) && aqi >= 151 && aqi <= 500)
        return state("red", "⚠︎", "UNHEALTHY AIR // AQI " + Math.round(aqi));

    // Missing or stale weather is UNKNOWN, never sunny or an all-clear.
    if (!weatherFresh)
        return state("white", "?", "WEATHER UNAVAILABLE");

    const code = Number(reading.weatherCode);
    const desc = String(reading.condition || "").toLowerCase();
    const wind = Number(reading.windMph);

    if (includesCode(code, [200, 386, 389, 392, 395]) || /thunder|lightning/.test(desc))
        return state("magenta", "⛈︎", "THUNDERSTORM");
    if (includesCode(code, [350, 374, 377]) || /hail|ice pellets/.test(desc))
        return state("white", "🌨︎", "HAIL / ICE PELLETS");
    if (includesCode(code, [179, 182, 227, 230, 317, 320, 323, 326, 329, 332,
                            335, 338, 362, 365, 368, 371]) ||
        /snow|blizzard|sleet/.test(desc))
        return state("cyan", "❆", "SNOW / SLEET");
    if (isFinite(wind) && wind >= 25 && wind <= 250)
        return state("omnitrix", "༄", "HIGH WIND // " + Math.round(wind) + " MPH");
    if (includesCode(code, [176, 185, 263, 266, 281, 284, 293, 296, 299, 302,
                            305, 308, 311, 314, 353, 356, 359]) ||
        /rain|drizzle|shower/.test(desc))
        return state("blue", "☂︎", "RAIN");
    if (code === 116 || /partly sunny|partly cloudy/.test(desc))
        return state("orange", "🌤︎", "PARTLY SUNNY");
    if (includesCode(code, [119, 122, 143, 248, 260]) ||
        /cloud|overcast|fog|mist|haze/.test(desc))
        return state("yellow", "☁︎", "CLOUDS / FOG");
    if (code === 113 || /sunny|clear/.test(desc))
        return state("orange", "☀︎", "SUNNY / CLEAR");

    return state("white", "?", "UNKNOWN CONDITION");
}
