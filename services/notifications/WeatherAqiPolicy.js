.pragma library

// US AQI labels already used by WeatherService. The producer never guesses
// a condition from descriptive weather text or a partial fetch.
function bandForAqi(value) {
    const aqi = Number(value);
    if (!isFinite(aqi) || aqi < 0 || aqi > 500)
        return -1;
    if (aqi <= 150)
        return 0;
    if (aqi <= 200)
        return 1;
    if (aqi <= 300)
        return 2;
    return 3;
}

// One notification at the first unhealthy reading or an escalation.
// An unchanged or improving reading never alerts. A return to <=150
// rearms the next episode. This state is scoped to one Quickshell session.
function nextTransition(previousBand, rawAqi) {
    const current = bandForAqi(rawAqi);
    const previous = Math.max(0, Math.min(3, Number(previousBand) || 0));
    if (current < 0)
        return { nextBand: previous, shouldNotify: false };
    if (current === 0)
        return { nextBand: 0, shouldNotify: false };
    return {
        nextBand: Math.max(previous, current),
        shouldNotify: current > previous
    };
}

function labelForBand(band) {
    if (band === 1)
        return "UNHEALTHY";
    if (band === 2)
        return "VERY UNHEALTHY";
    if (band === 3)
        return "HAZARDOUS";
    return "";
}

function severityForBand(band) {
    return band >= 3 ? "critical" : "warning";
}
