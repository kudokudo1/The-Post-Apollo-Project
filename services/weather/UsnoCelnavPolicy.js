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

function requestInfo(nowMs, latitudeRaw, longitudeRaw) {
    const millis = Number(nowMs);
    const latitude = finite(latitudeRaw);
    const longitude = finite(longitudeRaw);
    if (!isFinite(millis) || millis <= 0
            || latitude === null || Math.abs(latitude) > 90
            || longitude === null || Math.abs(longitude) > 180) {
        return {
            valid:false, key:"", endpoint:"",
            date:"", time:"", latitude:latitude, longitude:longitude
        };
    }

    const date = new Date(millis);
    const year = date.getUTCFullYear();
    if (year < 1800 || year > 2050) {
        return {
            valid:false, key:"", endpoint:"",
            date:"", time:"", latitude:latitude, longitude:longitude
        };
    }

    const dateText = year + "-"
        + twoDigit(date.getUTCMonth() + 1) + "-"
        + twoDigit(date.getUTCDate());
    const timeText = twoDigit(date.getUTCHours()) + ":"
        + twoDigit(date.getUTCMinutes());
    const latText = latitude.toFixed(4);
    const lonText = longitude.toFixed(4);
    const key = dateText + "|" + timeText + "|" + latText + "|" + lonText;

    return {
        valid:true,
        key:key,
        date:dateText,
        time:timeText,
        latitude:latitude,
        longitude:longitude,
        endpoint:
            "https://aa.usno.navy.mil/api/celnav"
            + "?date=" + encodeURIComponent(dateText)
            + "&time=" + encodeURIComponent(timeText)
            + "&coords=" + encodeURIComponent(latText + "," + lonText)
            + "&id=PostApW"
    };
}

function compassDirection(azimuthRaw) {
    const azimuth = finite(azimuthRaw);
    if (azimuth === null)
        return "--";
    const directions = [
        "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
        "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"
    ];
    let angle = azimuth % 360;
    if (angle < 0)
        angle += 360;
    return directions[Math.round(angle / 22.5) % 16];
}

function constellationForNavStar(numberRaw, nameRaw) {
    const number = Number(numberRaw);
    const byNumber = {
        1:"ANDROMEDA", 2:"PHOENIX", 3:"CASSIOPEIA", 4:"CETUS",
        5:"ERIDANUS", 6:"ARIES", 7:"ERIDANUS", 8:"CETUS",
        9:"PERSEUS", 10:"TAURUS", 11:"ORION", 12:"AURIGA",
        13:"ORION", 14:"TAURUS", 15:"ORION", 16:"ORION",
        17:"CARINA", 18:"CANIS MAJOR", 19:"CANIS MAJOR",
        20:"CANIS MINOR", 21:"GEMINI", 22:"CARINA", 23:"VELA",
        24:"CARINA", 25:"HYDRA", 26:"LEO", 27:"URSA MAJOR",
        28:"LEO", 29:"CORVUS", 30:"CRUX", 31:"CRUX",
        32:"URSA MAJOR", 33:"VIRGO", 34:"URSA MAJOR",
        35:"CENTAURUS", 36:"CENTAURUS", 37:"BOOTES",
        38:"CENTAURUS", 39:"LIBRA", 40:"URSA MINOR",
        41:"CORONA BOREALIS", 42:"SCORPIUS",
        43:"TRIANGULUM AUSTRALE", 44:"OPHIUCHUS",
        45:"SCORPIUS", 46:"OPHIUCHUS", 47:"DRACO",
        48:"SAGITTARIUS", 49:"LYRA", 50:"SAGITTARIUS",
        51:"AQUILA", 52:"PAVO", 53:"CYGNUS", 54:"PEGASUS",
        55:"GRUS", 56:"PISCIS AUSTRINUS", 57:"PEGASUS"
    };
    if (isFinite(number) && byNumber[number])
        return byNumber[number];

    const byName = {
        "POLARIS":"URSA MINOR",
        "ALPHERATZ":"ANDROMEDA",
        "SIRIUS":"CANIS MAJOR",
        "VEGA":"LYRA",
        "DENEB":"CYGNUS",
        "ALTAIR":"AQUILA",
        "ARCTURUS":"BOOTES",
        "SPICA":"VIRGO",
        "REGULUS":"LEO",
        "ANTARES":"SCORPIUS",
        "BETELGEUSE":"ORION",
        "RIGEL":"ORION"
    };
    return byName[String(nameRaw || "").trim().toUpperCase()] || "";
}

function almanacData(row) {
    if (!row || typeof row !== "object")
        return null;
    const source = row.almanac_data;
    if (source && typeof source === "object" && !Array.isArray(source))
        return source;
    if (Array.isArray(source) && source.length > 0
            && source[0] && typeof source[0] === "object")
        return source[0];
    return null;
}

function normalizeObject(row) {
    if (!row || typeof row !== "object")
        return null;
    const data = almanacData(row);
    if (!data)
        return null;

    const name = shortText(row.object, 64);
    const altitude = finite(data.hc);
    const azimuth = finite(data.zn);
    if (!name || altitude === null || azimuth === null
            || altitude < -90 || altitude > 90)
        return null;

    let normalizedAzimuth = azimuth % 360;
    if (normalizedAzimuth < 0)
        normalizedAzimuth += 360;

    const navNumber = finite(row.nav_star_number);
    return {
        name:name.toUpperCase(),
        altitude:altitude,
        azimuth:normalizedAzimuth,
        direction:compassDirection(normalizedAzimuth),
        navStarNumber:navNumber,
        constellation:constellationForNavStar(navNumber, name)
    };
}

function emptyResult() {
    return {
        available:false,
        date:"",
        time:"",
        moon:null,
        sun:null,
        planets:[],
        stars:[]
    };
}

function parse(root) {
    if (!root || typeof root !== "object" || root.error)
        throw new Error("Invalid USNO CelNav response");

    const properties = root.properties && typeof root.properties === "object"
        ? root.properties : {};
    const data = Array.isArray(properties.data)
        ? properties.data
        : Array.isArray(root.data) ? root.data : null;
    if (!data)
        throw new Error("USNO CelNav data missing");

    const result = emptyResult();
    const year = finite(properties.year);
    const month = finite(properties.month);
    const day = finite(properties.day);
    result.date = year !== null && month !== null && day !== null
        ? String(Math.floor(year)) + "-"
          + twoDigit(month) + "-" + twoDigit(day)
        : "";
    result.time = shortText(properties.time, 16);

    const planets = [];
    const stars = [];
    const planetNames = {
        "MERCURY":true, "VENUS":true, "MARS":true,
        "JUPITER":true, "SATURN":true, "URANUS":true, "NEPTUNE":true
    };

    for (let i = 0; i < data.length; i++) {
        const item = normalizeObject(data[i]);
        if (!item)
            continue;

        if (item.name === "MOON")
            result.moon = item;
        else if (item.name === "SUN")
            result.sun = item;
        else if (planetNames[item.name])
            planets.push(item);
        else if (item.navStarNumber !== null
                || item.constellation !== "")
            stars.push(item);
    }

    planets.sort(function(a, b) {
        return b.altitude - a.altitude;
    });
    stars.sort(function(a, b) {
        return b.altitude - a.altitude;
    });

    result.planets = planets.slice(0, 8);
    result.stars = stars.slice(0, 8);
    result.available = result.moon !== null
        || result.sun !== null
        || result.planets.length > 0
        || result.stars.length > 0;
    if (!result.available)
        throw new Error("USNO CelNav returned no usable objects");
    return result;
}
