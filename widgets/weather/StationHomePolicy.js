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

function firstDaily(daily) {
    return Array.isArray(daily) && daily.length > 0
           ? daily[0] : null;
}

function previousSet(previousIds) {
    const set = ({});
    const source = Array.isArray(previousIds) ? previousIds : [];

    for (let i = 0; i < source.length; i++)
        set[String(source[i] || "")] = true;

    return set;
}

function activeAbove(value, enterAt, releaseBelow, wasActive) {
    const number = finiteNumber(value, -Infinity);
    return wasActive ? number >= releaseBelow : number >= enterAt;
}

function activeBelow(value, enterAt, releaseAbove, wasActive) {
    const number = finiteNumber(value, Infinity);
    return wasActive ? number <= releaseAbove : number <= enterAt;
}

function makeCandidate(
    id,
    rank,
    source,
    title,
    value,
    detail,
    meterValue,
    kind,
    footer
) {
    const rawMeter = finiteNumber(meterValue, -1);
    const meterVisible = rawMeter >= 0;

    return {
        id: String(id || ""),
        rank: Number(rank) || 0,
        source: String(source || "weather"),
        title: String(title || ""),
        value: String(value || ""),
        detail: String(detail || ""),
        meterVisible: meterVisible,
        meterValue: meterVisible ? clamp01(rawMeter) : 0,
        kind: String(kind || "priority"),
        footer: String(footer || "")
    };
}

function pushUnique(candidates, candidate) {
    if (!candidate || !candidate.id)
        return;

    for (let i = 0; i < candidates.length; i++) {
        if (candidates[i].id === candidate.id) {
            if (candidate.rank > candidates[i].rank)
                candidates[i] = candidate;
            return;
        }
    }

    candidates.push(candidate);
}

function signedDelta(value, digits, suffix) {
    const number = finiteNumber(value, 0);
    const sign = number > 0 ? "+" : "";
    return sign + number.toFixed(digits) + String(suffix || "");
}

function trendSuffix(value, threshold, digits, suffix) {
    const number = finiteNumber(value, 0);
    if (Math.abs(number) < threshold)
        return "";

    return " // " + signedDelta(number, digits, suffix)
           + " SINCE LAST SAMPLE";
}

function parseClockMinutes(value) {
    const raw = String(value || "").trim().toUpperCase();
    if (!raw)
        return -1;

    const match = raw.match(/^(\d{1,2}):(\d{2})\s*(AM|PM)$/);
    if (!match)
        return -1;

    let hour = Number(match[1]);
    const minute = Number(match[2]);
    const suffix = match[3];

    if (!isFinite(hour) || !isFinite(minute)
            || hour < 1 || hour > 12 || minute < 0 || minute > 59)
        return -1;

    if (hour === 12)
        hour = 0;
    if (suffix === "PM")
        hour += 12;

    return hour * 60 + minute;
}

function minutesUntilClock(clockText, nowMinutes) {
    const target = parseClockMinutes(clockText);
    const now = finiteNumber(nowMinutes, -1);

    if (target < 0 || now < 0)
        return -1;

    return target - now;
}

function chooseRelevant(input) {
    const ranked = rankRelevant(input, [], 1);
    return ranked.length > 0
           ? ranked[0]
           : makeCandidate(
               "current-status",
               0,
               "weather",
               "CURRENT STATUS",
               "WAITING",
               "CONNECTING TO SOURCES",
               -1,
               "baseline",
               "AUTO BASELINE"
           );
}

function rankRelevant(input, previousIds, limit) {
    const state = input || {};
    const previous = previousSet(previousIds);
    const candidates = [];

    const weatherReady = !!state.weatherReady;
    const aqiReady = !!state.aqiReady;
    const spaceReady = !!state.spaceReady;
    const weatherStale = !!state.weatherStale;
    const spacePartial = !!state.spacePartial;
    const spaceStale = !!state.spaceStale;
    const weatherError = String(state.weatherError || "");
    const aqiError = String(state.aqiError || "");
    const spaceError = String(state.spaceError || "");

    const hourly = Array.isArray(state.hourlyForecast)
                   ? state.hourlyForecast : [];
    const daily = Array.isArray(state.dailyForecast)
                  ? state.dailyForecast : [];
    const forecast = firstForecast(hourly);
    const today = firstDaily(daily);

    const temperature = finiteNumber(state.temperatureF, -999);
    const humidity = finiteNumber(state.humidity, -1);
    const wind = finiteNumber(state.windMph, -1);
    const pressure = finiteNumber(state.pressureHpa, -1);
    const visibility = finiteNumber(state.visibilityMiles, -1);
    const cloudCover = finiteNumber(state.cloudCover, -1);
    const uv = finiteNumber(state.uvIndex, -1);
    const aqi = finiteNumber(state.aqi, -1);
    const pm25 = finiteNumber(state.pm25, -1);

    const rainChance = finiteNumber(
        forecast ? forecast.chanceRain : null,
        -1
    );

    const kp = finiteNumber(state.kp, -1);
    const solarWind = finiteNumber(state.solarWindSpeed, -1);
    const bz = finiteNumber(state.bz, 999);
    const bt = finiteNumber(state.bt, -1);
    const solarFlux = finiteNumber(state.solarFlux, -1);

    const temperatureDelta = finiteNumber(
        state.temperatureDelta, 0
    );
    const pressureDelta = finiteNumber(
        state.pressureDelta, 0
    );
    const rainDelta = finiteNumber(
        state.rainChanceDelta, 0
    );
    const aqiDelta = finiteNumber(
        state.aqiDelta, 0
    );
    const kpDelta = finiteNumber(
        state.kpDelta, 0
    );
    const solarWindDelta = finiteNumber(
        state.solarWindDelta, 0
    );
    const bzDelta = finiteNumber(
        state.bzDelta, 0
    );

    // ─────────────────────────────────────────────
    // SOURCE HEALTH
    // ─────────────────────────────────────────────

    if (!weatherReady) {
        pushUnique(candidates, makeCandidate(
            "weather-link",
            100,
            "weather",
            "WEATHER LINK",
            "OFFLINE",
            weatherError
                ? "CURRENT CONDITIONS SOURCE ERROR"
                : "CURRENT CONDITIONS UNAVAILABLE",
            -1,
            "source",
            "AUTO SOURCE HEALTH"
        ));
    } else if (weatherStale) {
        const age = finiteNumber(state.weatherAgeMinutes, -1);
        pushUnique(candidates, makeCandidate(
            "weather-stale",
            88,
            "weather",
            "WEATHER LINK",
            "STALE",
            age >= 0
                ? "LAST WEATHER UPDATE " + Math.round(age) + " MIN AGO"
                : "WEATHER DATA AGE EXCEEDED",
            -1,
            "source",
            "AUTO SOURCE HEALTH"
        ));
    }

    if (weatherReady && !aqiReady && aqiError) {
        pushUnique(candidates, makeCandidate(
            "air-feed",
            52,
            "ground",
            "AIR QUALITY FEED",
            "OFFLINE",
            "WEATHER IS LIVE // AQI SOURCE ERROR",
            -1,
            "source",
            "AUTO SOURCE HEALTH"
        ));
    }

    if (spaceStale) {
        pushUnique(candidates, makeCandidate(
            "space-feed",
            72,
            "space",
            "SPACE FEED",
            "STALE",
            String(
                state.spaceStaleDetail
                || "ONE OR MORE SPACE SOURCES AGED OUT"
            ).toUpperCase(),
            -1,
            "source",
            "AUTO SOURCE HEALTH"
        ));
    }

    if (!spaceReady && (spacePartial || spaceError)) {
        pushUnique(candidates, makeCandidate(
            "space-feed",
            spaceError ? 64 : 50,
            "space",
            "SPACE FEED",
            spacePartial ? "PARTIAL" : "OFFLINE",
            spaceError
                ? "SPACE WEATHER SOURCE ERROR"
                : "WAITING FOR ALL SPACE SOURCES",
            -1,
            "source",
            "AUTO SOURCE HEALTH"
        ));
    }

    // ─────────────────────────────────────────────
    // COMBINED CONDITIONS
    // ─────────────────────────────────────────────

    const hotHumidActive = activeAbove(
        temperature,
        85,
        82,
        !!previous["hot-humid"]
    ) && activeAbove(
        humidity,
        65,
        60,
        !!previous["hot-humid"]
    );

    if (weatherReady && hotHumidActive) {
        let rank = 64;
        if (temperature >= 95 && humidity >= 70)
            rank = 82;
        else if (temperature >= 90 && humidity >= 70)
            rank = 74;

        pushUnique(candidates, makeCandidate(
            "hot-humid",
            rank,
            "sky",
            "HOT // HUMID",
            Math.round(temperature) + "°F",
            Math.round(humidity) + "% HUMIDITY"
            + trendSuffix(temperatureDelta, 5, 0, "°F"),
            temperature / 120,
            "combo",
            "AUTO COMBINATION"
        ));
    }

    const windRainActive = activeAbove(
        rainChance,
        60,
        50,
        !!previous["wind-rain"]
    ) && activeAbove(
        wind,
        20,
        17,
        !!previous["wind-rain"]
    );

    if (weatherReady && windRainActive) {
        let rank = 76;
        if (rainChance >= 80 && wind >= 30)
            rank = 90;

        pushUnique(candidates, makeCandidate(
            "wind-rain",
            rank,
            "sky",
            "WIND + RAIN",
            Math.round(rainChance) + "% RAIN",
            Math.round(wind) + " MPH "
            + String(state.windDirection || "").toUpperCase()
            + trendSuffix(rainDelta, 20, 0, "pp"),
            rainChance / 100,
            "combo",
            "AUTO COMBINATION"
        ));
    }

    const spaceStackActive = activeAbove(
        kp,
        4,
        3.5,
        !!previous["space-stack"]
    ) && activeAbove(
        solarWind,
        500,
        450,
        !!previous["space-stack"]
    ) && activeBelow(
        bz,
        -5,
        -3,
        !!previous["space-stack"]
    );

    if (spaceStackActive) {
        let rank = 95;
        if (kp >= 5 || bz <= -10 || solarWind >= 700)
            rank = 99;

        pushUnique(candidates, makeCandidate(
            "space-stack",
            rank,
            "space",
            "SPACE WEATHER STACK",
            "KP " + kp.toFixed(1),
            Math.round(solarWind) + " KM/S // BZ "
            + bz.toFixed(1) + " nT"
            + (bt >= 0 ? " // BT " + bt.toFixed(1) + " nT" : ""),
            kp / 9,
            "combo",
            "AUTO COMBINATION"
        ));
    }

    // ─────────────────────────────────────────────
    // ABSOLUTE CONDITIONS
    // ─────────────────────────────────────────────

    const aqiActive = activeAbove(
        aqi,
        51,
        45,
        !!previous["air-quality"]
    );

    if (aqiReady && aqiActive) {
        let rank = 58;
        if (aqi > 150)
            rank = 96;
        else if (aqi > 100)
            rank = 78;

        pushUnique(candidates, makeCandidate(
            "air-quality",
            rank,
            "ground",
            "AIR QUALITY",
            "AQI " + Math.round(aqi),
            String(state.aqiLabel || "ELEVATED").toUpperCase()
            + trendSuffix(aqiDelta, 15, 0, ""),
            aqi / 500,
            "priority",
            "AUTO PROMOTED // GROUND"
        ));
    } else if (aqiReady && aqiDelta >= 20) {
        pushUnique(candidates, makeCandidate(
            "air-quality-trend",
            70,
            "ground",
            "AQI TREND",
            signedDelta(aqiDelta, 0, ""),
            "AQI " + Math.round(aqi)
            + " // SINCE LAST SAMPLE",
            aqi / 500,
            "trend",
            "AUTO TREND // GROUND"
        ));
    }

    const uvActive = activeAbove(
        uv,
        3,
        2.5,
        !!previous["uv-index"]
    );

    if (weatherReady && uvActive) {
        let rank = 36;
        if (uv >= 8)
            rank = 92;
        else if (uv >= 6)
            rank = 72;

        pushUnique(candidates, makeCandidate(
            "uv-index",
            rank,
            "sky",
            "UV INDEX",
            String(Math.round(uv)),
            uv >= 8 ? "VERY HIGH"
                    : uv >= 6 ? "HIGH"
                    : "MODERATE",
            uv / 11,
            "priority",
            "AUTO PROMOTED // SKY"
        ));
    }

    const rainActive = activeAbove(
        rainChance,
        30,
        20,
        !!previous["rain-chance"]
    );

    if (!windRainActive && rainActive) {
        pushUnique(candidates, makeCandidate(
            "rain-chance",
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
            ).toUpperCase()
            + trendSuffix(rainDelta, 20, 0, "pp"),
            rainChance / 100,
            "priority",
            "AUTO PROMOTED // SKY"
        ));
    } else if (!windRainActive && rainDelta >= 25) {
        pushUnique(candidates, makeCandidate(
            "rain-trend",
            68,
            "sky",
            "RAIN TREND",
            signedDelta(rainDelta, 0, "pp"),
            "NOW " + Math.round(Math.max(0, rainChance))
            + "% // SINCE LAST SAMPLE",
            Math.max(0, rainChance) / 100,
            "trend",
            "AUTO TREND // SKY"
        ));
    }

    const windActive = activeAbove(
        wind,
        25,
        20,
        !!previous["strong-wind"]
    );

    if (weatherReady && !windRainActive && windActive) {
        pushUnique(candidates, makeCandidate(
            "strong-wind",
            wind >= 40 ? 82 : wind >= 30 ? 64 : 50,
            "sky",
            "STRONG WIND",
            Math.round(wind) + " MPH",
            String(state.windDirection || "--").toUpperCase(),
            wind / 50,
            "priority",
            "AUTO PROMOTED // SKY"
        ));
    }

    const lowVisibilityActive = activeBelow(
        visibility,
        3,
        4,
        !!previous["low-visibility"]
    );

    if (weatherReady && visibility >= 0 && lowVisibilityActive) {
        pushUnique(candidates, makeCandidate(
            "low-visibility",
            visibility <= 1 ? 88 : 70,
            "sky",
            "LOW VISIBILITY",
            visibility.toFixed(1) + " MI",
            String(state.condition || "ATMOSPHERE").toUpperCase(),
            clamp01(1 - visibility / 10),
            "priority",
            "AUTO PROMOTED // SKY"
        ));
    }

    const overcastActive = activeAbove(
        cloudCover,
        90,
        80,
        !!previous["overcast"]
    );

    if (weatherReady && overcastActive && rainChance < 30) {
        pushUnique(candidates, makeCandidate(
            "overcast",
            32,
            "sky",
            "CLOUD COVER",
            Math.round(cloudCover) + "%",
            "OVERCAST CONDITIONS",
            cloudCover / 100,
            "priority",
            "AUTO PROMOTED // SKY"
        ));
    }

    if (Math.abs(temperatureDelta) >= 5 && !hotHumidActive) {
        pushUnique(candidates, makeCandidate(
            "temperature-trend",
            Math.abs(temperatureDelta) >= 10 ? 78 : 58,
            "sky",
            "TEMPERATURE SHIFT",
            signedDelta(temperatureDelta, 0, "°F"),
            "NOW " + Math.round(temperature) + "°F"
            + " // SINCE LAST SAMPLE",
            temperature / 120,
            "trend",
            "AUTO TREND // SKY"
        ));
    }

    if (Math.abs(pressureDelta) >= 3) {
        pushUnique(candidates, makeCandidate(
            "pressure-trend",
            Math.abs(pressureDelta) >= 6 ? 72 : 54,
            "sky",
            "PRESSURE TREND",
            signedDelta(pressureDelta, 1, " hPa"),
            pressure >= 0
                ? "NOW " + pressure.toFixed(0) + " hPa"
                  + " // SINCE LAST SAMPLE"
                : "SINCE LAST SAMPLE",
            -1,
            "trend",
            "AUTO TREND // SKY"
        ));
    }

    const kpActive = activeAbove(
        kp,
        4,
        3.5,
        !!previous["geomagnetic"]
    );

    if (!spaceStackActive && kpActive) {
        let rank = 52;
        if (kp >= 6)
            rank = 91;
        else if (kp >= 5)
            rank = 74;

        pushUnique(candidates, makeCandidate(
            "geomagnetic",
            rank,
            "space",
            "GEOMAGNETIC",
            "KP " + kp.toFixed(1),
            String(state.kpLabel || "ACTIVE").toUpperCase()
            + trendSuffix(kpDelta, 1, 1, ""),
            kp / 9,
            "priority",
            "AUTO PROMOTED // SPACE"
        ));
    } else if (!spaceStackActive && kpDelta >= 1) {
        pushUnique(candidates, makeCandidate(
            "kp-trend",
            72,
            "space",
            "KP TREND",
            signedDelta(kpDelta, 1, ""),
            "NOW KP " + kp.toFixed(1)
            + " // SINCE LAST SAMPLE",
            kp / 9,
            "trend",
            "AUTO TREND // SPACE"
        ));
    }

    const solarWindActive = activeAbove(
        solarWind,
        500,
        450,
        !!previous["solar-wind"]
    );

    if (!spaceStackActive && solarWindActive) {
        let rank = 45;
        if (solarWind >= 800)
            rank = 84;
        else if (solarWind >= 650)
            rank = 64;

        pushUnique(candidates, makeCandidate(
            "solar-wind",
            rank,
            "space",
            "SOLAR WIND",
            Math.round(solarWind) + " KM/S",
            "ELEVATED SOLAR WIND"
            + trendSuffix(solarWindDelta, 75, 0, " KM/S"),
            solarWind / 1000,
            "priority",
            "AUTO PROMOTED // SPACE"
        ));
    } else if (!spaceStackActive && solarWindDelta >= 100) {
        pushUnique(candidates, makeCandidate(
            "solar-wind-trend",
            60,
            "space",
            "SOLAR WIND TREND",
            signedDelta(solarWindDelta, 0, " KM/S"),
            "NOW " + Math.round(solarWind)
            + " KM/S // SINCE LAST SAMPLE",
            solarWind / 1000,
            "trend",
            "AUTO TREND // SPACE"
        ));
    }

    const bzActive = activeBelow(
        bz,
        0,
        1,
        !!previous["imf-bz"]
    );

    if (!spaceStackActive && bzActive) {
        let rank = 34;
        if (bz <= -10)
            rank = 88;
        else if (bz <= -5)
            rank = 68;

        pushUnique(candidates, makeCandidate(
            "imf-bz",
            rank,
            "space",
            "IMF BZ",
            bz.toFixed(1) + " nT",
            (
                bz <= -10 ? "STRONG SOUTH"
                : bz <= -5 ? "SOUTH"
                : "SLIGHT SOUTH"
            ) + trendSuffix(bzDelta, 3, 1, " nT"),
            Math.abs(bz) / 20,
            "priority",
            "AUTO PROMOTED // SPACE"
        ));
    } else if (!spaceStackActive && bzDelta <= -5) {
        pushUnique(candidates, makeCandidate(
            "bz-trend",
            62,
            "space",
            "BZ TREND",
            signedDelta(bzDelta, 1, " nT"),
            "NOW " + bz.toFixed(1)
            + " nT // MOVING SOUTH",
            Math.abs(bz) / 20,
            "trend",
            "AUTO TREND // SPACE"
        ));
    }

    // ─────────────────────────────────────────────
    // TIME-SENSITIVE CONDITIONS
    // ─────────────────────────────────────────────

    if (today) {
        const nowMinutes = finiteNumber(state.nowMinutes, -1);
        const sunriseIn = minutesUntilClock(today.sunrise, nowMinutes);
        const sunsetIn = minutesUntilClock(today.sunset, nowMinutes);

        if (sunriseIn >= 0 && sunriseIn <= 75) {
            pushUnique(candidates, makeCandidate(
                "sunrise-window",
                sunriseIn <= 30 ? 52 : 44,
                "sky",
                "SUNRISE",
                String(today.sunrise || "--"),
                "IN " + Math.round(sunriseIn) + " MIN",
                -1,
                "time",
                "AUTO TIME WINDOW // SKY"
            ));
        }

        if (sunsetIn >= 0 && sunsetIn <= 75) {
            pushUnique(candidates, makeCandidate(
                "sunset-window",
                sunsetIn <= 30 ? 52 : 44,
                "sky",
                "SUNSET",
                String(today.sunset || "--"),
                "IN " + Math.round(sunsetIn) + " MIN",
                -1,
                "time",
                "AUTO TIME WINDOW // SKY"
            ));
        }
    }

    // ─────────────────────────────────────────────
    // LOW-PRIORITY BASELINES
    // ─────────────────────────────────────────────

    if (forecast) {
        pushUnique(candidates, makeCandidate(
            "next-hours",
            0,
            "sky",
            "NEXT HOURS",
            String(forecast.condition || "FORECAST").toUpperCase(),
            String(forecast.timeLabel || "")
            + (
                finiteNumber(forecast.tempF, -999) > -900
                ? " // " + Math.round(Number(forecast.tempF)) + "°F"
                : ""
            )
            + (
                rainChance >= 0
                ? " // RAIN " + Math.round(rainChance) + "%"
                : ""
            ),
            rainChance >= 0 ? rainChance / 100 : -1,
            "baseline",
            "AUTO BASELINE // SKY"
        ));
    }

    if (today) {
        const high = finiteNumber(today.maxTempF, -999);
        const low = finiteNumber(today.minTempF, -999);

        if (high > -900 || low > -900) {
            pushUnique(candidates, makeCandidate(
                "today-range",
                -1,
                "sky",
                "TODAY RANGE",
                (high > -900 ? Math.round(high) : "--")
                + "° / "
                + (low > -900 ? Math.round(low) : "--")
                + "°F",
                String(today.condition || "DAILY FORECAST").toUpperCase(),
                -1,
                "baseline",
                "AUTO BASELINE // SKY"
            ));
        }
    }

    if (pressure >= 0) {
        pushUnique(candidates, makeCandidate(
            "pressure-baseline",
            -2,
            "sky",
            "PRESSURE",
            pressure.toFixed(0) + " hPa",
            visibility >= 0
                ? "VIS " + visibility.toFixed(1) + " MI"
                  + " // CLOUD " + Math.max(0, Math.round(cloudCover)) + "%"
                : "ATMOSPHERE",
            -1,
            "baseline",
            "AUTO BASELINE // SKY"
        ));
    }

    if (spaceReady && (solarFlux >= 0 || kp >= 0)) {
        pushUnique(candidates, makeCandidate(
            "space-baseline",
            -3,
            "space",
            "SPACE BASELINE",
            kp >= 0 ? "KP " + kp.toFixed(1) : "SPACE LIVE",
            (solarWind >= 0
             ? Math.round(solarWind) + " KM/S"
             : "WIND --")
            + (solarFlux >= 0
               ? " // F10.7 " + Math.round(solarFlux) + " SFU"
               : "")
            + (bt >= 0 ? " // BT " + bt.toFixed(1) + " nT" : ""),
            kp >= 0 ? kp / 9 : -1,
            "baseline",
            "AUTO BASELINE // SPACE"
        ));
    }

    if (aqiReady && pm25 >= 0) {
        pushUnique(candidates, makeCandidate(
            "particulate-baseline",
            -4,
            "ground",
            "PARTICULATES",
            "PM2.5 " + pm25.toFixed(1),
            "µg/m³ // AQI " + Math.max(0, Math.round(aqi)),
            aqi >= 0 ? aqi / 500 : -1,
            "baseline",
            "AUTO BASELINE // GROUND"
        ));
    }

    if (candidates.length === 0) {
        pushUnique(candidates, makeCandidate(
            "current-status",
            0,
            "weather",
            "CURRENT STATUS",
            weatherReady ? "NO PRIORITY CONDITION" : "WAITING",
            weatherReady
                ? "LIVE DATA NOMINAL"
                : "CONNECTING TO SOURCES",
            -1,
            "baseline",
            "AUTO BASELINE"
        ));
    }

    candidates.sort(function(a, b) {
        if (b.rank !== a.rank)
            return b.rank - a.rank;
        return a.id.localeCompare(b.id);
    });

    const requested = Math.max(
        1,
        Math.floor(finiteNumber(limit, 3))
    );

    return candidates.slice(0, requested);
}
