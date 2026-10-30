.pragma library

function finiteNumber(value, fallback) {
    if (value === undefined || value === null)
        return fallback;

    if (typeof value === "string" && value.trim().length === 0)
        return fallback;

    const number = Number(value);
    return isFinite(number) ? number : fallback;
}

function textValue(value, fallback) {
    if (value === undefined || value === null)
        return fallback;
    const text = String(value).trim();
    return text.length > 0 ? text : fallback;
}

function description(node) {
    if (!node || !node.weatherDesc || node.weatherDesc.length === 0)
        return "UNKNOWN";
    return textValue(node.weatherDesc[0].value, "UNKNOWN");
}

function parseClockHour(value) {
    const text = String(value || "");
    const match = text.match(/(\d{1,2}):(\d{2})\s*(AM|PM)?/i);
    if (!match)
        return -1;

    let hour = Number(match[1]);
    const suffix = String(match[3] || "").toUpperCase();

    if (suffix === "AM" && hour === 12)
        hour = 0;
    else if (suffix === "PM" && hour < 12)
        hour += 12;

    return hour >= 0 && hour <= 23 ? hour : -1;
}

function wttrHour(value) {
    const raw = Number(value);
    if (!isFinite(raw))
        return -1;
    return Math.max(0, Math.min(23, Math.floor(raw / 100)));
}

function hourLabel(value) {
    const hour = wttrHour(value);
    if (hour < 0)
        return "--";

    const suffix = hour >= 12 ? "PM" : "AM";
    const display = hour % 12 === 0 ? 12 : hour % 12;
    return display + " " + suffix;
}

function currentAtmosphere(current) {
    const visibilityKm = finiteNumber(current ? current.visibility : null, -1);
    let visibilityMiles = finiteNumber(
        current ? current.visibilityMiles : null,
        -1
    );

    if (visibilityMiles < 0 && visibilityKm >= 0)
        visibilityMiles = visibilityKm * 0.621371;

    return {
        pressureHpa: finiteNumber(current ? current.pressure : null, -1),
        visibilityMiles: visibilityMiles,
        cloudCover: finiteNumber(current ? current.cloudcover : null, -1),
        precipMm: finiteNumber(current ? current.precipMM : null, -1),
        observationTime: textValue(
            current
            ? (current.localObsDateTime || current.observation_time)
            : "",
            ""
        )
    };
}

function maxChance(hourly, key) {
    if (!Array.isArray(hourly))
        return -1;

    let result = -1;
    for (let i = 0; i < hourly.length; i++) {
        const value = finiteNumber(hourly[i] ? hourly[i][key] : null, -1);
        if (value > result)
            result = value;
    }
    return result;
}

function parseDailyForecast(data) {
    const days = data && Array.isArray(data.weather) ? data.weather : [];
    const output = [];

    for (let i = 0; i < days.length; i++) {
        const day = days[i] || {};
        const hourly = Array.isArray(day.hourly) ? day.hourly : [];
        const representative = hourly.length > 0
                               ? hourly[Math.floor(hourly.length / 2)]
                               : null;
        const astronomy = day.astronomy && day.astronomy.length > 0
                          ? day.astronomy[0] : {};

        output.push({
            date: textValue(day.date, "--"),
            maxTempF: finiteNumber(day.maxtempF, -999),
            minTempF: finiteNumber(day.mintempF, -999),
            avgTempF: finiteNumber(day.avgtempF, -999),
            condition: description(representative),
            weatherCode: textValue(
                representative ? representative.weatherCode : "",
                ""
            ),
            chanceRain: maxChance(hourly, "chanceofrain"),
            chanceSnow: maxChance(hourly, "chanceofsnow"),
            uvIndex: finiteNumber(day.uvIndex, -1),
            sunrise: textValue(astronomy.sunrise, "--"),
            sunset: textValue(astronomy.sunset, "--"),
            moonPhase: textValue(astronomy.moon_phase, "--"),
            moonIllumination: finiteNumber(
                astronomy.moon_illumination,
                -1
            )
        });
    }

    return output;
}

function parseHourlyForecast(data, current, limit) {
    const days = data && Array.isArray(data.weather) ? data.weather : [];
    const output = [];
    const requested = Math.max(1, Number(limit) || 6);
    const currentHour = parseClockHour(
        current
        ? (current.localObsDateTime || current.observation_time)
        : ""
    );

    for (let dayIndex = 0;
         dayIndex < days.length && output.length < requested;
         dayIndex++) {
        const day = days[dayIndex] || {};
        const hourly = Array.isArray(day.hourly) ? day.hourly : [];

        for (let i = 0; i < hourly.length && output.length < requested; i++) {
            const entry = hourly[i] || {};
            const hour = wttrHour(entry.time);

            if (dayIndex === 0 && currentHour >= 0 && hour >= 0
                    && hour < currentHour) {
                continue;
            }

            output.push({
                date: textValue(day.date, "--"),
                time: textValue(entry.time, ""),
                timeLabel: hourLabel(entry.time),
                tempF: finiteNumber(entry.tempF, -999),
                feelsLikeF: finiteNumber(entry.FeelsLikeF, -999),
                dewPointF: finiteNumber(entry.DewPointF, -999),
                humidity: finiteNumber(entry.humidity, -1),
                chanceRain: finiteNumber(entry.chanceofrain, -1),
                chanceSnow: finiteNumber(entry.chanceofsnow, -1),
                precipMm: finiteNumber(entry.precipMM, -1),
                pressureHpa: finiteNumber(entry.pressure, -1),
                visibilityMiles: finiteNumber(entry.visibilityMiles, -1),
                cloudCover: finiteNumber(entry.cloudcover, -1),
                uvIndex: finiteNumber(entry.uvIndex, -1),
                windMph: finiteNumber(entry.windspeedMiles, -1),
                windDirection: textValue(entry.winddir16Point, "--"),
                weatherCode: textValue(entry.weatherCode, ""),
                condition: description(entry)
            });
        }
    }

    return output;
}

function parseForecast(data, current, hourlyLimit) {
    return {
        daily: parseDailyForecast(data),
        hourly: parseHourlyForecast(data, current, hourlyLimit)
    };
}

function parseAirQualityContext(root) {
    const source = root || {};
    const seconds = finiteNumber(source.utc_offset_seconds, null);
    const offsetValid = seconds !== null
        && seconds >= -43200 && seconds <= 50400;

    return {
        utcOffsetMinutes: offsetValid ? seconds / 60 : null,
        timezone: textValue(source.timezone, ""),
        timezoneAbbreviation:
            textValue(source.timezone_abbreviation, "")
    };
}

function parseAirQuality(current) {
    const source = current || {};
    const result = {
        usAqi: finiteNumber(source.us_aqi, -1),
        ozoneAqi: finiteNumber(source.us_aqi_ozone, -1),
        nitrogenDioxideAqi:
            finiteNumber(source.us_aqi_nitrogen_dioxide, -1),
        carbonMonoxideAqi:
            finiteNumber(source.us_aqi_carbon_monoxide, -1),
        pm25: finiteNumber(source.pm2_5, -1),
        pm10: finiteNumber(source.pm10, -1),
        carbonMonoxide: finiteNumber(source.carbon_monoxide, -1),
        nitrogenDioxide: finiteNumber(source.nitrogen_dioxide, -1),
        ozone: finiteNumber(source.ozone, -1),
        dust: finiteNumber(source.dust, -1),
        alderPollen: finiteNumber(source.alder_pollen, -1),
        birchPollen: finiteNumber(source.birch_pollen, -1),
        grassPollen: finiteNumber(source.grass_pollen, -1),
        mugwortPollen: finiteNumber(source.mugwort_pollen, -1),
        olivePollen: finiteNumber(source.olive_pollen, -1),
        ragweedPollen: finiteNumber(source.ragweed_pollen, -1),
        time: textValue(source.time, "")
    };

    result.pollenAvailable =
        result.alderPollen >= 0
        || result.birchPollen >= 0
        || result.grassPollen >= 0
        || result.mugwortPollen >= 0
        || result.olivePollen >= 0
        || result.ragweedPollen >= 0;

    return result;
}

// Same Open-Meteo response as current AQI. Use six two-hour samples from
// forecast_hours=12; no current observation is silently used as a forecast.
function parseAirQualityForecast(hourly, hours) {
    const source = hourly || {};
    const times = Array.isArray(source.time) ? source.time : [];
    const aqi = Array.isArray(source.us_aqi) ? source.us_aqi : [];
    const fine = Array.isArray(source.pm2_5) ? source.pm2_5 : [];
    const coarse = Array.isArray(source.pm10) ? source.pm10 : [];
    const requested = Number(hours);
    const length = isFinite(requested) && requested > 0
                   ? Math.min(12, Math.floor(requested)) : 12;
    const output = [];

    for (let i = 0; i < Math.min(length, times.length)
            && output.length < 6; i += 2) {
        const timestamp = textValue(times[i], "");
        if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(timestamp))
            continue;
        const hour = Number(timestamp.slice(11, 13));
        if (!isFinite(hour) || hour < 0 || hour > 23)
            continue;

        const value = finiteNumber(aqi[i], -1);
        const pm25 = finiteNumber(fine[i], -1);
        const pm10 = finiteNumber(coarse[i], -1);
        output.push({
            time: timestamp,
            label: (hour % 12 || 12) + (hour >= 12 ? " PM" : " AM"),
            aqi: value >= 0 && value <= 500 ? value : -1,
            pm25: pm25 >= 0 ? pm25 : -1,
            pm10: pm10 >= 0 ? pm10 : -1
        });
    }
    return output;
}
