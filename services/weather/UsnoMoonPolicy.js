.pragma library

function finite(value) {
    if (value === undefined || value === null || value === "")
        return null;
    const number = Number(value);
    return isFinite(number) ? number : null;
}

function shortText(value, limit) {
    return String(value === undefined || value === null ? "" : value)
        .replace(/[\u0000-\u001f\u007f]/g, " ")
        .trim()
        .replace(/\s+/g, " ")
        .slice(0, limit);
}

function twoDigit(value) {
    const number = Math.max(0, Math.floor(Number(value) || 0));
    return number < 10 ? "0" + number : String(number);
}

function validDate(value) {
    const match = String(value || "").match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (!match)
        return false;
    const year = Number(match[1]);
    const month = Number(match[2]);
    const day = Number(match[3]);
    if (year < 1700 || year > 2100 || month < 1 || month > 12
            || day < 1 || day > 31)
        return false;
    const check = new Date(Date.UTC(year, month - 1, day));
    return check.getUTCFullYear() === year
        && check.getUTCMonth() === month - 1
        && check.getUTCDate() === day;
}

function snappedOffsetMinutes(value) {
    const raw = finite(value);
    if (raw === null)
        return null;
    const snapped = Math.round(raw / 15) * 15;
    if (snapped < -720 || snapped > 840)
        return null;
    // The sunrise calibration is an astronomical estimate of a civil clock
    // offset. Refuse to reinterpret a large mismatch as a time zone.
    if (Math.abs(snapped - raw) > 8)
        return null;
    return snapped;
}

function offsetHoursText(offsetMinutes) {
    const snapped = snappedOffsetMinutes(offsetMinutes);
    if (snapped === null)
        return "";
    const hours = snapped / 60;
    if (Math.abs(hours - Math.round(hours)) < 1e-9)
        return String(Math.round(hours));
    if (Math.abs(hours * 2 - Math.round(hours * 2)) < 1e-9)
        return hours.toFixed(1);
    return hours.toFixed(2);
}

function requestInfo(dateValue, latitudeValue, longitudeValue, offsetMinutes) {
    const date = String(dateValue || "");
    const latitude = finite(latitudeValue);
    const longitude = finite(longitudeValue);
    const tz = offsetHoursText(offsetMinutes);
    const dateValid = validDate(date);
    const coordinatesValid =
        latitude !== null && Math.abs(latitude) <= 90
        && longitude !== null && Math.abs(longitude) <= 180;
    const offsetValid = tz !== "";

    if (!dateValid || !coordinatesValid || !offsetValid) {
        return {
            valid:false, key:"", endpoint:"", tzHours:"",
            date:date, latitude:latitude, longitude:longitude,
            dateValid:dateValid,
            coordinatesValid:coordinatesValid,
            offsetValid:offsetValid
        };
    }

    const latText = latitude.toFixed(4);
    const lonText = longitude.toFixed(4);
    const key = date + "|" + latText + "|" + lonText + "|" + tz;
    return {
        valid:true,
        key:key,
        date:date,
        latitude:latitude,
        longitude:longitude,
        tzHours:tz,
        dateValid:true,
        coordinatesValid:true,
        offsetValid:true,
        endpoint:
            "https://aa.usno.navy.mil/api/rstt/oneday"
            + "?date=" + encodeURIComponent(date)
            + "&coords=" + encodeURIComponent(latText + "," + lonText)
            + "&tz=" + encodeURIComponent(tz)
    };
}

function clockLabel(value) {
    const raw = String(value === undefined || value === null ? "" : value).trim();
    const match = raw.match(/^(\d{1,2}):(\d{2})$/);
    if (!match)
        return "--";
    const hour = Number(match[1]);
    const minute = Number(match[2]);
    if (hour < 0 || hour > 23 || minute < 0 || minute > 59)
        return "--";
    const suffix = hour >= 12 ? "PM" : "AM";
    const hour12 = hour % 12 === 0 ? 12 : hour % 12;
    return hour12 + ":" + twoDigit(minute) + " " + suffix;
}

function illuminationPercent(value) {
    if (value === undefined || value === null || value === "")
        return -1;
    const text = String(value).trim();
    const match = text.match(/-?\d+(?:\.\d+)?/);
    if (!match)
        return -1;
    let number = Number(match[0]);
    if (!isFinite(number) || number < 0)
        return -1;
    if (text.indexOf("%") < 0 && number <= 1)
        number *= 100;
    if (number > 100)
        return -1;
    return number;
}

function dataObject(root) {
    if (!root || typeof root !== "object")
        throw new Error("Invalid USNO response");
    if (root.error)
        throw new Error("USNO returned an error");

    const properties = root.properties && typeof root.properties === "object"
        ? root.properties : {};
    const data = properties.data !== undefined ? properties.data : properties;

    if (Array.isArray(data)) {
        for (let i = 0; i < data.length; i++) {
            const row = data[i];
            if (row && typeof row === "object"
                    && (Array.isArray(row.moondata)
                        || row.curphase !== undefined
                        || row.fracillum !== undefined))
                return row;
        }
        throw new Error("USNO moon data missing");
    }

    if (data && typeof data === "object")
        return data;

    throw new Error("USNO moon data missing");
}

function phenomenonKey(value) {
    const text = String(value || "").toLowerCase();
    if (text.indexOf("rise") >= 0)
        return "rise";
    if (text.indexOf("set") >= 0)
        return "set";
    if (text.indexOf("transit") >= 0)
        return "transit";
    return "";
}

function emptyResult() {
    return {
        available:false,
        rise:"--",
        transit:"--",
        set:"--",
        phase:"--",
        illumination:-1,
        noRiseSet:false,
        timezoneHours:"",
        sourceDate:""
    };
}

function parse(root) {
    const data = dataObject(root);
    const result = emptyResult();
    const moondata = Array.isArray(data.moondata) ? data.moondata : [];

    let rawRise = "";
    let rawTransit = "";
    let rawSet = "";

    for (let i = 0; i < moondata.length; i++) {
        const row = moondata[i];
        if (!row || typeof row !== "object")
            continue;
        const key = phenomenonKey(row.phen);
        const time = row.time === null || row.time === undefined
            ? "" : String(row.time).trim();
        if (!time)
            continue;
        if (key === "rise" && !rawRise)
            rawRise = time;
        else if (key === "transit" && !rawTransit)
            rawTransit = time;
        else if (key === "set" && !rawSet)
            rawSet = time;
    }

    const phase = shortText(data.curphase, 64);
    const illumination = illuminationPercent(data.fracillum);
    const year = Number(data.year);
    const month = Number(data.month);
    const day = Number(data.day);
    const sourceDate = isFinite(year) && isFinite(month) && isFinite(day)
        ? String(year) + "-" + twoDigit(month) + "-" + twoDigit(day)
        : "";
    const timezone = finite(data.tz);

    result.rise = clockLabel(rawRise);
    result.transit = clockLabel(rawTransit);
    result.set = clockLabel(rawSet);
    result.phase = phase ? phase.toUpperCase() : "--";
    result.illumination = illumination;
    result.noRiseSet = result.rise === "--" && result.set === "--";
    result.timezoneHours = timezone === null ? "" : String(timezone);
    result.sourceDate = sourceDate;
    result.available = moondata.length > 0 || phase !== "" || illumination >= 0;
    return result;
}
