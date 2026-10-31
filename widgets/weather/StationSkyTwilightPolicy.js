.pragma library

function finite(value) {
    if (value === undefined || value === null || value === "")
        return null;
    const number = Number(value);
    return isFinite(number) ? number : null;
}

function radians(degrees) {
    return degrees * Math.PI / 180;
}

function degrees(radiansValue) {
    return radiansValue * 180 / Math.PI;
}

function wrapDegrees(value) {
    let result = Number(value) % 360;
    if (result < 0)
        result += 360;
    return result;
}

function wrapMinutes(value) {
    let result = Number(value) % 1440;
    if (result < 0)
        result += 1440;
    return result;
}

function twoDigit(value) {
    const number = Math.max(0, Math.floor(Number(value) || 0));
    return number < 10 ? "0" + number : String(number);
}

function parseDate(raw) {
    const match = String(raw || "").match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (!match)
        return null;
    const year = Number(match[1]);
    const month = Number(match[2]);
    const day = Number(match[3]);
    if (year < 1901 || year > 2099 || month < 1 || month > 12
            || day < 1 || day > 31)
        return null;
    const check = new Date(Date.UTC(year, month - 1, day));
    if (check.getUTCFullYear() !== year
            || check.getUTCMonth() !== month - 1
            || check.getUTCDate() !== day)
        return null;
    return {year: year, month: month, day: day};
}

function julianDay(date) {
    let year = date.year;
    let month = date.month;
    if (month <= 2) {
        year -= 1;
        month += 12;
    }
    const a = Math.floor(year / 100);
    const b = 2 - a + Math.floor(a / 4);
    return Math.floor(365.25 * (year + 4716))
         + Math.floor(30.6001 * (month + 1))
         + date.day + b - 1524.5;
}

function julianCentury(jd) {
    return (jd - 2451545.0) / 36525.0;
}

function geomMeanLongSun(t) {
    return wrapDegrees(
        280.46646 + t * (36000.76983 + t * 0.0003032)
    );
}

function geomMeanAnomalySun(t) {
    return 357.52911 + t * (35999.05029 - 0.0001537 * t);
}

function eccentricityEarthOrbit(t) {
    return 0.016708634 - t * (0.000042037 + 0.0000001267 * t);
}

function sunEquationOfCenter(t) {
    const m = radians(geomMeanAnomalySun(t));
    return Math.sin(m) * (1.914602 - t * (0.004817 + 0.000014 * t))
         + Math.sin(2 * m) * (0.019993 - 0.000101 * t)
         + Math.sin(3 * m) * 0.000289;
}

function sunApparentLongitude(t) {
    const trueLongitude = geomMeanLongSun(t) + sunEquationOfCenter(t);
    const omega = 125.04 - 1934.136 * t;
    return trueLongitude - 0.00569 - 0.00478 * Math.sin(radians(omega));
}

function meanObliquityOfEcliptic(t) {
    const seconds = 21.448
        - t * (46.815 + t * (0.00059 - t * 0.001813));
    return 23 + (26 + seconds / 60) / 60;
}

function obliquityCorrection(t) {
    const omega = 125.04 - 1934.136 * t;
    return meanObliquityOfEcliptic(t)
         + 0.00256 * Math.cos(radians(omega));
}

function solarDeclination(t) {
    const e = radians(obliquityCorrection(t));
    const lambda = radians(sunApparentLongitude(t));
    return degrees(Math.asin(Math.sin(e) * Math.sin(lambda)));
}

function equationOfTime(t) {
    const epsilon = radians(obliquityCorrection(t));
    const l0 = radians(geomMeanLongSun(t));
    const m = radians(geomMeanAnomalySun(t));
    const e = eccentricityEarthOrbit(t);
    const y = Math.tan(epsilon / 2);
    const y2 = y * y;
    const value =
        y2 * Math.sin(2 * l0)
        - 2 * e * Math.sin(m)
        + 4 * e * y2 * Math.sin(m) * Math.cos(2 * l0)
        - 0.5 * y2 * y2 * Math.sin(4 * l0)
        - 1.25 * e * e * Math.sin(2 * m);
    return 4 * degrees(value);
}

function hourAngle(latitude, declination, zenith) {
    const lat = radians(latitude);
    const dec = radians(declination);
    const denominator = Math.cos(lat) * Math.cos(dec);
    if (Math.abs(denominator) < 1e-12)
        return null;
    const cosine =
        Math.cos(radians(zenith)) / denominator
        - Math.tan(lat) * Math.tan(dec);
    if (!isFinite(cosine) || cosine < -1 || cosine > 1)
        return null;
    return degrees(Math.acos(cosine));
}

function eventUtcMinutes(date, latitude, longitude, zenith, morning) {
    const jd = julianDay(date);
    let t = julianCentury(jd);
    let eq = equationOfTime(t);
    let dec = solarDeclination(t);
    let angle = hourAngle(latitude, dec, zenith);
    if (angle === null)
        return null;

    let signed = morning ? angle : -angle;
    let minutes = 720 - 4 * (longitude + signed) - eq;

    // NOAA's published spreadsheet/calculator method refines the solar
    // geometry at the estimated event time.
    t = julianCentury(jd + minutes / 1440);
    eq = equationOfTime(t);
    dec = solarDeclination(t);
    angle = hourAngle(latitude, dec, zenith);
    if (angle === null)
        return null;
    signed = morning ? angle : -angle;
    minutes = 720 - 4 * (longitude + signed) - eq;
    return isFinite(minutes) ? minutes : null;
}

function solarNoonUtcMinutes(date, longitude) {
    const jd = julianDay(date);
    let t = julianCentury(jd);
    let minutes = 720 - 4 * longitude - equationOfTime(t);
    t = julianCentury(jd + minutes / 1440);
    minutes = 720 - 4 * longitude - equationOfTime(t);
    return isFinite(minutes) ? minutes : null;
}

function clockMinute(raw) {
    const match = String(raw || "").trim().match(
        /^(\d{1,2}):(\d{2})\s*(AM|PM)?$/i
    );
    if (!match)
        return -1;
    let hour = Number(match[1]);
    const minute = Number(match[2]);
    const suffix = String(match[3] || "").toUpperCase();
    if (minute < 0 || minute > 59)
        return -1;
    if (suffix) {
        if (hour < 1 || hour > 12)
            return -1;
        if (hour === 12)
            hour = 0;
        if (suffix === "PM")
            hour += 12;
    } else if (hour < 0 || hour > 23) {
        return -1;
    }
    return hour * 60 + minute;
}

function calibratedClockOffset(localSunriseMinute, sunriseUtcMinute, longitude) {
    if (localSunriseMinute < 0 || sunriseUtcMinute === null)
        return null;

    const utcClock = wrapMinutes(sunriseUtcMinute);
    const base = localSunriseMinute - utcClock;
    const approximate = Number(longitude) * 4;
    let best = null;
    let bestDistance = Infinity;
    for (let k = -1; k <= 1; k++) {
        const candidate = base + k * 1440;
        if (candidate < -720 || candidate > 840)
            continue;
        const distance = Math.abs(candidate - approximate);
        if (distance < bestDistance) {
            best = candidate;
            bestDistance = distance;
        }
    }
    return best;
}

function clockLabelFromMinute(rawMinute) {
    const value = finite(rawMinute);
    if (value === null)
        return "--";
    const minute = Math.round(wrapMinutes(value));
    const hour24 = Math.floor(minute / 60) % 24;
    const mm = minute % 60;
    const suffix = hour24 >= 12 ? "PM" : "AM";
    const hour12 = hour24 % 12 === 0 ? 12 : hour24 % 12;
    return hour12 + ":" + twoDigit(mm) + " " + suffix;
}

function localLabel(utcMinute, offsetMinute) {
    if (utcMinute === null || offsetMinute === null)
        return "--";
    return clockLabelFromMinute(utcMinute + offsetMinute);
}

function observationEpoch(value) {
    const match = String(value || "").trim().match(
        /^(\d{4})-(\d{2})-(\d{2})\s+(\d{1,2}):(\d{2})(?::\d{2})?\s*(AM|PM)?$/i
    );
    if (!match)
        return NaN;
    const year = Number(match[1]);
    const month = Number(match[2]);
    const day = Number(match[3]);
    let hour = Number(match[4]);
    const minute = Number(match[5]);
    if (match[6]) {
        if (hour < 1 || hour > 12)
            return NaN;
        hour = hour % 12
             + (String(match[6]).toUpperCase() === "PM" ? 12 : 0);
    }
    if (hour > 23 || minute > 59 || month < 1 || month > 12
            || day < 1 || day > 31)
        return NaN;
    const epoch = Date.UTC(year, month - 1, day, hour, minute);
    const check = new Date(epoch);
    return check.getUTCFullYear() === year
        && check.getUTCMonth() === month - 1
        && check.getUTCDate() === day ? epoch : NaN;
}

function providerObservationMinute(nowMs, observation, anchorMs) {
    const epoch = observationEpoch(observation);
    const now = Number(nowMs);
    const anchor = Number(anchorMs);
    if (!isFinite(epoch) || !isFinite(now) || !isFinite(anchor)
            || anchor <= 0 || now < anchor - 300000
            || now - anchor > 3600000)
        return -1;
    const local = new Date(epoch + Math.max(0, now - anchor));
    return local.getUTCHours() * 60 + local.getUTCMinutes();
}

function compassLabel(azimuthRaw) {
    const azimuth = finite(azimuthRaw);
    if (azimuth === null)
        return "--";
    const names = [
        "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
        "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"
    ];
    return names[Math.round(wrapDegrees(azimuth) / 22.5) % 16];
}

function solarPosition(dateRaw, localMinuteRaw, latitudeRaw, longitudeRaw,
                       calibrationOffsetRaw) {
    const date = parseDate(dateRaw);
    const localMinute = finite(localMinuteRaw);
    const latitude = finite(latitudeRaw);
    const longitude = finite(longitudeRaw);
    const offset = finite(calibrationOffsetRaw);
    if (!date || localMinute === null || localMinute < 0 || localMinute >= 1440
            || latitude === null || Math.abs(latitude) >= 90
            || longitude === null || Math.abs(longitude) > 180
            || offset === null || offset < -720 || offset > 840) {
        return {
            available: false,
            altitudeDegrees: null,
            azimuthDegrees: null,
            azimuthLabel: "--",
            aboveHorizon: false
        };
    }

    const utcMinute = localMinute - offset;
    const t = julianCentury(julianDay(date) + utcMinute / 1440);
    const declination = solarDeclination(t);
    const eqTime = equationOfTime(t);
    const trueSolarMinute = wrapMinutes(
        utcMinute + eqTime + 4 * longitude
    );
    const hourAngleDegrees = trueSolarMinute / 4 - 180;

    const lat = radians(latitude);
    const dec = radians(declination);
    const hour = radians(hourAngleDegrees);
    const sineElevation =
        Math.sin(lat) * Math.sin(dec)
        + Math.cos(lat) * Math.cos(dec) * Math.cos(hour);
    const elevation = degrees(Math.asin(
        Math.max(-1, Math.min(1, sineElevation))
    ));

    // atan2 form gives azimuth clockwise from north after +180°.
    const azimuth = wrapDegrees(
        degrees(Math.atan2(
            Math.sin(hour),
            Math.cos(hour) * Math.sin(lat)
                - Math.tan(dec) * Math.cos(lat)
        )) + 180
    );

    return {
        available: isFinite(elevation) && isFinite(azimuth),
        altitudeDegrees: elevation,
        azimuthDegrees: azimuth,
        azimuthLabel: compassLabel(azimuth),
        aboveHorizon: elevation >= 0,
        utcMinute: utcMinute,
        hourAngleDegrees: hourAngleDegrees
    };
}

function summary(dateRaw, latitudeRaw, longitudeRaw, providerSunriseRaw) {
    const date = parseDate(dateRaw);
    const latitude = finite(latitudeRaw);
    const longitude = finite(longitudeRaw);
    const providerSunriseMinute = clockMinute(providerSunriseRaw);

    if (!date || latitude === null || longitude === null
            || Math.abs(latitude) >= 90 || Math.abs(longitude) > 180
            || providerSunriseMinute < 0) {
        return {
            available: false,
            astronomicalDawn: "--",
            nauticalDawn: "--",
            civilDawn: "--",
            solarNoon: "--",
            civilDusk: "--",
            nauticalDusk: "--",
            astronomicalDusk: "--",
            blueMorningStart: "--",
            blueMorningEnd: "--",
            goldenMorningStart: "--",
            goldenMorningEnd: "--",
            goldenEveningStart: "--",
            goldenEveningEnd: "--",
            blueEveningStart: "--",
            blueEveningEnd: "--",
            calibrationOffsetMinutes: null
        };
    }

    const sunriseUtc = eventUtcMinutes(
        date, latitude, longitude, 90.833, true
    );
    const offset = calibratedClockOffset(
        providerSunriseMinute, sunriseUtc, longitude
    );
    if (sunriseUtc === null || offset === null) {
        return {
            available: false,
            astronomicalDawn: "--",
            nauticalDawn: "--",
            civilDawn: "--",
            solarNoon: "--",
            civilDusk: "--",
            nauticalDusk: "--",
            astronomicalDusk: "--",
            blueMorningStart: "--",
            blueMorningEnd: "--",
            goldenMorningStart: "--",
            goldenMorningEnd: "--",
            goldenEveningStart: "--",
            goldenEveningEnd: "--",
            blueEveningStart: "--",
            blueEveningEnd: "--",
            calibrationOffsetMinutes: null
        };
    }

    const astronomicalDawnUtc =
        eventUtcMinutes(date, latitude, longitude, 108, true);
    const nauticalDawnUtc =
        eventUtcMinutes(date, latitude, longitude, 102, true);
    const civilDawnUtc =
        eventUtcMinutes(date, latitude, longitude, 96, true);
    const noonUtc = solarNoonUtcMinutes(date, longitude);
    const civilDuskUtc =
        eventUtcMinutes(date, latitude, longitude, 96, false);
    const nauticalDuskUtc =
        eventUtcMinutes(date, latitude, longitude, 102, false);
    const astronomicalDuskUtc =
        eventUtcMinutes(date, latitude, longitude, 108, false);

    // Post-Apollo photographic-light convention. These are solar-center
    // altitude crossings, not official astronomical twilight categories.
    // BLUE: -6° to -4°. GOLDEN: -4° to +6°.
    const blueMorningStartUtc =
        eventUtcMinutes(date, latitude, longitude, 96, true);
    const blueMorningEndUtc =
        eventUtcMinutes(date, latitude, longitude, 94, true);
    const goldenMorningStartUtc = blueMorningEndUtc;
    const goldenMorningEndUtc =
        eventUtcMinutes(date, latitude, longitude, 84, true);
    const goldenEveningStartUtc =
        eventUtcMinutes(date, latitude, longitude, 84, false);
    const goldenEveningEndUtc =
        eventUtcMinutes(date, latitude, longitude, 94, false);
    const blueEveningStartUtc = goldenEveningEndUtc;
    const blueEveningEndUtc =
        eventUtcMinutes(date, latitude, longitude, 96, false);

    return {
        available: true,
        date: String(dateRaw),
        astronomicalDawn: localLabel(astronomicalDawnUtc, offset),
        nauticalDawn: localLabel(nauticalDawnUtc, offset),
        civilDawn: localLabel(civilDawnUtc, offset),
        solarNoon: localLabel(noonUtc, offset),
        civilDusk: localLabel(civilDuskUtc, offset),
        nauticalDusk: localLabel(nauticalDuskUtc, offset),
        astronomicalDusk: localLabel(astronomicalDuskUtc, offset),
        blueMorningStart: localLabel(blueMorningStartUtc, offset),
        blueMorningEnd: localLabel(blueMorningEndUtc, offset),
        goldenMorningStart: localLabel(goldenMorningStartUtc, offset),
        goldenMorningEnd: localLabel(goldenMorningEndUtc, offset),
        goldenEveningStart: localLabel(goldenEveningStartUtc, offset),
        goldenEveningEnd: localLabel(goldenEveningEndUtc, offset),
        blueEveningStart: localLabel(blueEveningStartUtc, offset),
        blueEveningEnd: localLabel(blueEveningEndUtc, offset),
        calibrationOffsetMinutes: offset,
        sunriseAnchor: clockLabelFromMinute(providerSunriseMinute)
    };
}
