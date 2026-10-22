.pragma library

function finiteNumber(value, fallback) {
    if (value === undefined || value === null)
        return fallback;

    const text = String(value).trim();
    if (text.length === 0)
        return fallback;

    const number = Number(value);
    return isFinite(number) ? number : fallback;
}

function clamp01(value) {
    const number = finiteNumber(value, 0);
    return Math.max(0, Math.min(1, number));
}

function firstForecast(hourly) {
    return Array.isArray(hourly) && hourly.length > 0
           ? hourly[0] : null;
}

function makeCandidate(rank, source, title, value, detail, meterValue) {
    return {
        rank: Number(rank) || 0,
        source: String(source || "weather"),
        title: String(title || ""),
        value: String(value || ""),
        detail: String(detail || ""),
        meterValue: clamp01(meterValue)
    };
}

function chooseRelevant(input) {
    const state = input || {};
    const candidates = [];

    const weatherReady = !!state.weatherReady;
    const aqiReady = !!state.aqiReady;
    const spaceReady = !!state.spaceReady;

    if (!weatherReady) {
        candidates.push(makeCandidate(
            100,
            "weather",
            "WEATHER LINK",
            "OFFLINE",
            "CURRENT CONDITIONS UNAVAILABLE",
            0
        ));
    }

    const aqi = finiteNumber(state.aqi, -1);
    if (aqiReady && aqi > 50) {
        let rank = 48;
        if (aqi > 150)
            rank = 96;
        else if (aqi > 100)
            rank = 78;
        else if (aqi > 50)
            rank = 58;

        candidates.push(makeCandidate(
            rank,
            "ground",
            "AIR QUALITY",
            "AQI " + Math.round(aqi),
            String(state.aqiLabel || "ELEVATED").toUpperCase(),
            aqi / 500
        ));
    }

    const uv = finiteNumber(state.uvIndex, -1);
    if (weatherReady && uv >= 3) {
        let rank = 36;
        if (uv >= 8)
            rank = 92;
        else if (uv >= 6)
            rank = 72;

        candidates.push(makeCandidate(
            rank,
            "sky",
            "UV INDEX",
            String(Math.round(uv)),
            uv >= 8 ? "VERY HIGH // LIMIT EXPOSURE"
                    : uv >= 6 ? "HIGH"
                    : "MODERATE",
            uv / 11
        ));
    }

    const forecast = firstForecast(state.hourlyForecast);
    const rainChance = finiteNumber(
        forecast ? forecast.chanceRain : null,
        -1
    );

    if (rainChance >= 30) {
        candidates.push(makeCandidate(
            28 + rainChance * 0.42,
            "sky",
            "RAIN CHANCE",
            Math.round(rainChance) + "%",
            String(
                (forecast && forecast.timeLabel) || "NEXT HOURS"
            ).toUpperCase()
            + " // "
            + String(
                (forecast && forecast.condition) || "FORECAST"
            ).toUpperCase(),
            rainChance / 100
        ));
    }

    const kp = finiteNumber(state.kp, -1);
    if (kp >= 4) {
        let rank = 52;
        if (kp >= 6)
            rank = 91;
        else if (kp >= 5)
            rank = 74;

        candidates.push(makeCandidate(
            rank,
            "space",
            "GEOMAGNETIC",
            "KP " + kp.toFixed(1),
            String(state.kpLabel || "ACTIVE").toUpperCase(),
            kp / 9
        ));
    }

    const solarWind = finiteNumber(state.solarWindSpeed, -1);
    if (solarWind >= 500) {
        let rank = 45;
        if (solarWind >= 800)
            rank = 84;
        else if (solarWind >= 650)
            rank = 64;

        candidates.push(makeCandidate(
            rank,
            "space",
            "SOLAR WIND",
            Math.round(solarWind) + " KM/S",
            "ELEVATED SOLAR WIND",
            solarWind / 1000
        ));
    }

    const bz = finiteNumber(state.bz, 999);
    if (bz < 0) {
        let rank = 34;
        if (bz <= -10)
            rank = 88;
        else if (bz <= -5)
            rank = 68;

        candidates.push(makeCandidate(
            rank,
            "space",
            "IMF BZ",
            bz.toFixed(1) + " nT",
            bz <= -10 ? "STRONG SOUTH"
                      : bz <= -5 ? "SOUTH"
                      : "SLIGHT SOUTH",
            Math.abs(bz) / 20
        ));
    }

    if (!spaceReady && String(state.spaceError || "").length > 0) {
        candidates.push(makeCandidate(
            62,
            "space",
            "SPACE FEED",
            "PARTIAL",
            "SPACE WEATHER SOURCE ERROR",
            0
        ));
    }

    if (candidates.length === 0) {
        if (forecast) {
            return makeCandidate(
                0,
                "sky",
                "NEXT HOURS",
                String(forecast.condition || "FORECAST").toUpperCase(),
                String(forecast.timeLabel || "")
                + (
                    finiteNumber(forecast.tempF, -999) > -900
                    ? " // " + Math.round(Number(forecast.tempF)) + "°F"
                    : ""
                ),
                rainChance >= 0 ? rainChance / 100 : 0
            );
        }

        return makeCandidate(
            0,
            "weather",
            "CURRENT STATUS",
            weatherReady ? "NO PRIORITY CONDITION" : "WAITING",
            weatherReady ? "LIVE DATA NOMINAL" : "CONNECTING TO SOURCES",
            0
        );
    }

    candidates.sort(function(a, b) {
        return b.rank - a.rank;
    });

    return candidates[0];
}
