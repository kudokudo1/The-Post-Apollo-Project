.pragma library

function finite(value, fallback) {
    if (value === undefined || value === null || value === "")
        return fallback;
    const number = Number(value);
    return isFinite(number) ? number : fallback;
}

function pad2(value) {
    return String(value).padStart(2, "0");
}

function parseAnchor(raw) {
    const text = String(raw || "").trim();
    const match = text.match(
        /^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{1,2}):(\d{2})(?::\d{2})?\s*(AM|PM)?)?/i
    );
    if (!match)
        return null;

    let hour = match[4] === undefined ? 12 : Number(match[4]);
    const suffix = String(match[6] || "").toUpperCase();
    if (suffix === "AM" && hour === 12)
        hour = 0;
    else if (suffix === "PM" && hour < 12)
        hour += 12;

    if (!isFinite(hour) || hour < 0 || hour > 23)
        return null;

    return {
        date: match[1] + "-" + match[2] + "-" + match[3],
        hour: hour
    };
}

function shiftDate(dateText, deltaDays) {
    const match = String(dateText || "").match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (!match)
        return "";
    const stamp = new Date(Date.UTC(
        Number(match[1]), Number(match[2]) - 1,
        Number(match[3]) + Number(deltaDays || 0)
    ));
    if (isNaN(stamp.getTime()))
        return "";
    return stamp.toISOString().slice(0, 10);
}

function requestSpec(latitudeValue, longitudeValue, anchorValue) {
    const latitude = finite(latitudeValue, NaN);
    const longitude = finite(longitudeValue, NaN);
    const anchor = parseAnchor(anchorValue);
    if (!isFinite(latitude) || !isFinite(longitude)
            || Math.abs(latitude) > 90 || Math.abs(longitude) > 180
            || !anchor) {
        return {
            valid: false, key: "", startDate: "", endDate: "",
            localHour: -1, latitude: 0, longitude: 0
        };
    }

    const endDate = shiftDate(anchor.date, -1);
    const startDate = shiftDate(endDate, -6);
    if (!startDate || !endDate)
        return {valid: false, key: "", startDate: "", endDate: "", localHour: -1};

    return {
        valid: true,
        latitude: latitude,
        longitude: longitude,
        startDate: startDate,
        endDate: endDate,
        localHour: anchor.hour,
        key: latitude.toFixed(4) + "," + longitude.toFixed(4)
             + "|" + startDate + "|" + endDate + "|" + anchor.hour
    };
}

function arrayValue(source, key, index, fallback) {
    const values = source && Array.isArray(source[key]) ? source[key] : [];
    return index >= 0 && index < values.length
           ? finite(values[index], fallback) : fallback;
}

function parseDaily(root) {
    const daily = root && root.daily ? root.daily : {};
    const times = Array.isArray(daily.time) ? daily.time : [];
    const rows = [];

    for (let i = 0; i < times.length; i++) {
        const date = String(times[i] || "");
        if (!/^\d{4}-\d{2}-\d{2}$/.test(date))
            continue;
        rows.push({
            date: date,
            maxTempF: arrayValue(daily, "temperature_2m_max", i, -999),
            minTempF: arrayValue(daily, "temperature_2m_min", i, -999),
            precipitationIn: arrayValue(daily, "precipitation_sum", i, -1),
            maxWindMph: arrayValue(daily, "wind_speed_10m_max", i, -1)
        });
    }
    return rows;
}

function parseSameHour(root, endDate, hour) {
    const hourly = root && root.hourly ? root.hourly : {};
    const times = Array.isArray(hourly.time) ? hourly.time : [];
    const target = String(endDate || "") + "T" + pad2(hour) + ":";
    let bestIndex = -1;

    for (let i = 0; i < times.length; i++) {
        if (String(times[i] || "").indexOf(target) === 0) {
            bestIndex = i;
            break;
        }
    }
    if (bestIndex < 0)
        return null;

    return {
        time: String(times[bestIndex] || ""),
        tempF: arrayValue(hourly, "temperature_2m", bestIndex, -999),
        humidity: arrayValue(hourly, "relative_humidity_2m", bestIndex, -1),
        feelsLikeF: arrayValue(hourly, "apparent_temperature", bestIndex, -999),
        pressureHpa: arrayValue(hourly, "pressure_msl", bestIndex, -1),
        windMph: arrayValue(hourly, "wind_speed_10m", bestIndex, -1)
    };
}

function summarizeDaily(rows) {
    const source = Array.isArray(rows) ? rows : [];
    let maxHigh = -Infinity;
    let minLow = Infinity;
    let highSum = 0;
    let lowSum = 0;
    let highCount = 0;
    let lowCount = 0;
    let precipTotal = 0;
    let maxPrecip = -1;
    let maxPrecipDate = "";
    let wetDays = 0;

    for (let i = 0; i < source.length; i++) {
        const row = source[i] || {};
        const high = finite(row.maxTempF, -999);
        const low = finite(row.minTempF, -999);
        const precip = finite(row.precipitationIn, -1);

        if (high > -900) {
            maxHigh = Math.max(maxHigh, high);
            highSum += high;
            highCount++;
        }
        if (low > -900) {
            minLow = Math.min(minLow, low);
            lowSum += low;
            lowCount++;
        }
        if (precip >= 0) {
            precipTotal += precip;
            if (precip > 0.001)
                wetDays++;
            if (precip > maxPrecip) {
                maxPrecip = precip;
                maxPrecipDate = String(row.date || "");
            }
        }
    }

    return {
        days: source.length,
        maxHighF: isFinite(maxHigh) ? maxHigh : -999,
        minLowF: isFinite(minLow) ? minLow : -999,
        avgHighF: highCount > 0 ? highSum / highCount : -999,
        avgLowF: lowCount > 0 ? lowSum / lowCount : -999,
        precipitationIn: precipTotal,
        wetDays: wetDays,
        maxPrecipIn: maxPrecip,
        maxPrecipDate: maxPrecipDate
    };
}

function parseResponse(root, spec) {
    if (!root || !spec || !spec.valid)
        throw new Error("Invalid historical response");
    const daily = parseDaily(root);
    if (daily.length === 0)
        throw new Error("No historical daily rows");
    return {
        daily: daily,
        sameHour: parseSameHour(root, spec.endDate, spec.localHour),
        summary: summarizeDaily(daily),
        timezone: String(root.timezone || ""),
        timezoneAbbreviation: String(root.timezone_abbreviation || "")
    };
}

function signedDelta(currentValue, pastValue, digits) {
    const current = finite(currentValue, NaN);
    const past = finite(pastValue, NaN);
    if (!isFinite(current) || !isFinite(past))
        return "--";
    const delta = current - past;
    const places = Math.max(0, Number(digits) || 0);
    return (delta > 0 ? "+" : "") + delta.toFixed(places);
}
