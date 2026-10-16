.pragma library

// Report current observed conditions only; WeatherService does not provide
// an hourly/daily forecast. Never replace missing fields with invented values.
function localDayKey(date) {
    const pad = function(n) { return String(n).padStart(2, "0"); };
    return date.getFullYear() + "-" + pad(date.getMonth() + 1)
           + "-" + pad(date.getDate());
}
function numberInRange(value, min, max) {
    if (value === undefined || value === null || String(value).trim() === "")
        return null;
    const n = Number(value);
    return isFinite(n) && n >= min && n <= max ? n : null;
}
function snapshot(weather, nowMs) {
    if (!weather || !weather.ready || !weather.lastUpdated)
        return null;
    const observedMs = new Date(weather.lastUpdated).getTime();
    if (!isFinite(observedMs) || nowMs < observedMs - 10 * 60 * 1000
            || nowMs - observedMs > 45 * 60 * 1000)
        return null;

    const temperatureF = numberInRange(weather.tempF, -120, 140);
    if (temperatureF === null)
        return null;

    const aqi = weather.aqiReady
                ? numberInRange(weather.aqi, 0, 500) : null;
    return {
        temperatureF: temperatureF,
        feelsLikeF: numberInRange(weather.feelsLikeF, -140, 160),
        condition: String(weather.condition || "UNKNOWN").slice(0, 80),
        humidityPercent: numberInRange(weather.humidity, 0, 100),
        windMph: numberInRange(weather.windMph, 0, 300),
        windDirection: String(weather.windDirection || "").slice(0, 12),
        aqi: aqi,
        aqiLabel: aqi === null ? "UNAVAILABLE"
                             : String(weather.aqiLabel || "UNKNOWN"),
        pm25: aqi === null ? null : numberInRange(weather.pm25, 0, 2000),
        pm10: aqi === null ? null : numberInRange(weather.pm10, 0, 3000),
        observedAtUtc: new Date(observedMs).toISOString()
    };
}
function summary(record) {
    let msg = Math.round(record.temperatureF) + "°F";
    if (record.feelsLikeF !== null)
        msg += " // FEELS " + Math.round(record.feelsLikeF) + "°F";
    msg += " // " + record.condition;
    if (record.windMph !== null)
        msg += "\nWIND " + record.windDirection + " "
            + Math.round(record.windMph) + " MPH";
    if (record.humidityPercent !== null)
        msg += " // HUMIDITY " + Math.round(record.humidityPercent) + "%";
    msg += "\nAIR QUALITY " + (record.aqi === null
         ? "UNAVAILABLE" : record.aqi + " " + record.aqiLabel);
    return msg;
}
