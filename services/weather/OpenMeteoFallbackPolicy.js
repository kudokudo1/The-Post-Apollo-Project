.pragma library

// Weather M6: deterministic Open-Meteo forecast fallback for explicit
// Place Registry coordinates. Normalizes to WeatherDataPolicy's widget
// shapes and never guesses unreported weather observations.
const BASE = "https://api.open-meteo.com/v1/forecast";

function number(value, fallback) {
    if (typeof value !== "number" || !isFinite(value))
        return fallback;
    return value;
}

function point(latitude, longitude) {
    if (latitude === undefined || longitude === undefined
            || latitude === null || longitude === null
            || String(latitude).trim() === ""
            || String(longitude).trim() === "")
        return null;
    const latText = String(latitude).trim();
    const lonText = String(longitude).trim();
    if (!/^[-+]?\d+(?:\.\d{1,6})?$/.test(latText)
            || !/^[-+]?\d+(?:\.\d{1,6})?$/.test(lonText))
        return null;
    const lat = Number(latText);
    const lon = Number(lonText);
    if (!isFinite(lat) || !isFinite(lon)
            || lat < -90 || lat > 90 || lon < -180 || lon > 180)
        return null;
    return {latitude:lat, longitude:lon};
}

function endpoint(latitude, longitude) {
    const location = point(latitude, longitude);
    if (!location)
        return "";
    return BASE + "?latitude=" + location.latitude
         + "&longitude=" + location.longitude
         + "&current=temperature_2m,apparent_temperature,relative_humidity_2m,"
         + "precipitation,weather_code,cloud_cover,pressure_msl,"
         + "wind_speed_10m,wind_direction_10m"
         + "&hourly=temperature_2m,apparent_temperature,relative_humidity_2m,"
         + "dew_point_2m,precipitation_probability,precipitation,pressure_msl,"
         + "cloud_cover,wind_speed_10m,wind_direction_10m,weather_code"
         + "&daily=weather_code,temperature_2m_max,temperature_2m_min,"
         + "precipitation_probability_max,sunrise,sunset"
         + "&temperature_unit=fahrenheit&wind_speed_unit=mph"
         + "&timezone=auto&forecast_days=3";
}

function wmo(code) {
    if (!Number.isInteger(code) || code < 0 || code > 99)
        return {description:"UNKNOWN", weatherCode:""};
    if (code === 0)
        return {description:"Clear sky", weatherCode:"113"};
    if (code === 1 || code === 2)
        return {description:"Partly cloudy", weatherCode:"116"};
    if (code === 3)
        return {description:"Overcast", weatherCode:"122"};
    if (code === 45 || code === 48)
        return {description:"Fog", weatherCode:"143"};
    if (code >= 51 && code <= 57)
        return {description:"Drizzle", weatherCode:"266"};
    if (code === 61 || code === 63)
        return {description:"Rain", weatherCode:"296"};
    if (code === 65)
        return {description:"Heavy rain", weatherCode:"308"};
    if (code >= 71 && code <= 73)
        return {description:"Snow", weatherCode:"227"};
    if (code === 75 || code === 77)
        return {description:"Heavy snow", weatherCode:"230"};
    if (code === 80 || code === 81)
        return {description:"Rain showers", weatherCode:"296"};
    if (code === 82)
        return {description:"Heavy rain showers", weatherCode:"308"};
    if (code === 85 || code === 86)
        return {description:"Snow showers", weatherCode:"227"};
    if (code === 95 || code === 96 || code === 99)
        return {description:"Thunderstorm", weatherCode:"200"};
    return {description:"UNKNOWN", weatherCode:""};
}

function compass(degrees) {
    if (typeof degrees !== "number" || !isFinite(degrees)
            || degrees < 0 || degrees > 360)
        return "--";
    const names = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S",
                   "SSW","SW","WSW","W","WNW","NW","NNW"];
    return names[Math.floor(((degrees % 360) + 11.25) / 22.5) % 16];
}

function fixed(value, fallback) {
    return typeof value === "number" && isFinite(value)
        ? String(Math.round(value * 10) / 10) : fallback;
}

function clock(value) {
    const text = String(value || "");
    return /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?$/.test(text)
           ? text : "";
}

function timeLabel(time) {
    const source = clock(time);
    if (!source)
        return "--";
    const hour = Number(source.slice(11,13));
    const minutes = Number(source.slice(14,16));
    if (hour > 23 || minutes > 59)
        return "--";
    const output = hour % 12 || 12;
    return output + (minutes ? ":" + String(minutes).padStart(2,"0") : "")
           + " " + (hour >= 12 ? "PM" : "AM");
}

function at(values, index) {
    return Array.isArray(values) && index >= 0 && index < values.length
           ? values[index] : null;
}

function normalizedCurrent(current) {
    if (!current || typeof current !== "object"
            || Array.isArray(current))
        return null;
    const when = clock(current.time);
    const temp = number(current.temperature_2m, null);
    if (!when || temp === null)
        return null;
    const info = wmo(number(current.weather_code, -1));
    return {
        tempF:fixed(temp,"--"),
        feelsLikeF:fixed(current.apparent_temperature,"--"),
        humidity:fixed(current.relative_humidity_2m,"--"),
        windMph:fixed(current.wind_speed_10m,"--"),
        windDirection:compass(current.wind_direction_10m),
        pressureHpa:number(current.pressure_msl,-1),
        visibilityMiles:-1,
        cloudCover:number(current.cloud_cover,-1),
        precipMm:number(current.precipitation,-1),
        observationTime:timeLabel(when),
        localObservationDateTime:when.replace("T"," ") + (when.length === 16 ? ":00" : ""),
        weatherCode:info.weatherCode,
        condition:info.description,
        uvIndex:-1
    };
}

function normalizedHourly(hourly, now) {
    if (!hourly || !Array.isArray(hourly.time))
        return [];
    const output = [];
    const currentHour = now.slice(0,13);
    for (let i = 0; i < hourly.time.length && output.length < 6; i++) {
        const when = clock(at(hourly.time,i));
        if (!when || when.slice(0,13) < currentHour)
            continue;
        const info = wmo(number(at(hourly.weather_code,i),-1));
        output.push({
            date:when.slice(0,10),
            time:when.slice(11,16).replace(":","") ,
            timeLabel:timeLabel(when),
            tempF:number(at(hourly.temperature_2m,i),-999),
            feelsLikeF:number(at(hourly.apparent_temperature,i),-999),
            dewPointF:number(at(hourly.dew_point_2m,i),-999),
            humidity:number(at(hourly.relative_humidity_2m,i),-1),
            chanceRain:number(at(hourly.precipitation_probability,i),-1),
            chanceSnow:-1,
            precipMm:number(at(hourly.precipitation,i),-1),
            pressureHpa:number(at(hourly.pressure_msl,i),-1),
            visibilityMiles:-1,
            cloudCover:number(at(hourly.cloud_cover,i),-1),
            uvIndex:-1,
            windMph:number(at(hourly.wind_speed_10m,i),-1),
            windDirection:compass(at(hourly.wind_direction_10m,i)),
            weatherCode:info.weatherCode,
            condition:info.description
        });
    }
    return output;
}

function normalizedDaily(daily) {
    if (!daily || !Array.isArray(daily.time))
        return [];
    const output = [];
    for (let i = 0; i < daily.time.length && output.length < 3; i++) {
        const date = String(at(daily.time,i) || "");
        if (!/^\d{4}-\d{2}-\d{2}$/.test(date))
            continue;
        const info = wmo(number(at(daily.weather_code,i),-1));
        output.push({
            date:date,
            maxTempF:number(at(daily.temperature_2m_max,i),-999),
            minTempF:number(at(daily.temperature_2m_min,i),-999),
            avgTempF:-999,
            condition:info.description,
            weatherCode:info.weatherCode,
            chanceRain:number(at(daily.precipitation_probability_max,i),-1),
            chanceSnow:-1,
            uvIndex:-1,
            sunrise:timeLabel(at(daily.sunrise,i)),
            sunset:timeLabel(at(daily.sunset,i)),
            moonPhase:"--",
            moonIllumination:-1
        });
    }
    return output;
}

function parse(rawText) {
    const text = String(rawText === null || rawText === undefined
                        ? "" : rawText);
    if (!text || text.length > 262144)
        return {ok:false, reason:"RESPONSE_INVALID"};
    let data;
    try { data = JSON.parse(text); }
    catch (error) { return {ok:false, reason:"JSON_INVALID"}; }
    if (!data || typeof data !== "object" || Array.isArray(data)
            || data.error === true)
        return {ok:false, reason:"PROVIDER_ERROR"};
    const current = normalizedCurrent(data.current);
    if (!current)
        return {ok:false, reason:"CURRENT_INVALID"};
    return {ok:true, current:current,
            hourly:normalizedHourly(data.hourly, data.current.time),
            daily:normalizedDaily(data.daily)};
}
