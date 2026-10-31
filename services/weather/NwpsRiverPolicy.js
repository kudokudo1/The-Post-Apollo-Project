.pragma library

function validNumber(value) {
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

function distanceKm(latA, lonA, latB, lonB) {
    const a = validNumber(latA);
    const b = validNumber(lonA);
    const c = validNumber(latB);
    const d = validNumber(lonB);
    if (a === null || b === null || c === null || d === null
            || Math.abs(a) > 90 || Math.abs(c) > 90
            || Math.abs(b) > 180 || Math.abs(d) > 180)
        return -1;

    const rad = Math.PI / 180;
    const dLat = (c - a) * rad;
    const dLon = (d - b) * rad;
    const h = Math.sin(dLat / 2) * Math.sin(dLat / 2)
            + Math.cos(a * rad) * Math.cos(c * rad)
            * Math.sin(dLon / 2) * Math.sin(dLon / 2);
    return 6371 * 2 * Math.atan2(
        Math.sqrt(h),
        Math.sqrt(Math.max(0, 1 - h))
    );
}

function boundedBox(latitudeRaw, longitudeRaw, radiusDegrees) {
    const latitude = validNumber(latitudeRaw);
    const longitude = validNumber(longitudeRaw);
    const radius = validNumber(radiusDegrees);
    if (latitude === null || longitude === null || radius === null
            || Math.abs(latitude) > 90 || Math.abs(longitude) > 180
            || radius <= 0 || radius > 2)
        return null;

    return {
        xmin: Math.max(-180, longitude - radius),
        ymin: Math.max(-90, latitude - radius),
        xmax: Math.min(180, longitude + radius),
        ymax: Math.min(90, latitude + radius)
    };
}

function field(object, names) {
    if (!object)
        return undefined;
    for (let i = 0; i < names.length; i++) {
        const name = names[i];
        if (object[name] !== undefined && object[name] !== null)
            return object[name];
    }
    return undefined;
}

function statusBlock(gauge, kind) {
    const status = gauge && gauge.status && typeof gauge.status === "object"
        ? gauge.status : null;
    const nested = status && status[kind] && typeof status[kind] === "object"
        ? status[kind] : null;
    const direct = gauge && gauge[kind] && typeof gauge[kind] === "object"
        ? gauge[kind] : null;
    return nested || direct || null;
}

function statusValue(gauge, kind, nameCandidates) {
    const block = statusBlock(gauge, kind);
    const nested = field(block, nameCandidates);
    if (nested !== undefined)
        return nested;

    const flattened = [];
    for (let i = 0; i < nameCandidates.length; i++) {
        flattened.push("status_" + kind + "_" + nameCandidates[i]);
        flattened.push(kind + "_" + nameCandidates[i]);
    }
    return field(gauge, flattened);
}

function categoryInfo(raw) {
    const compact = String(raw || "")
        .trim()
        .toLowerCase()
        .replace(/[\s_-]+/g, "");

    if (compact === "major" || compact === "majorflooding")
        return {id:"major", label:"MAJOR", rank:4};
    if (compact === "moderate" || compact === "moderateflooding")
        return {id:"moderate", label:"MODERATE", rank:3};
    if (compact === "minor" || compact === "minorflooding")
        return {id:"minor", label:"MINOR", rank:2};
    if (compact === "action" || compact === "actionstage")
        return {id:"action", label:"ACTION", rank:1};
    if (compact === "noflooding" || compact === "none"
            || compact === "normal" || compact === "belowaction")
        return {id:"none", label:"NO FLOODING", rank:0};
    if (!compact || compact === "notdefined" || compact === "unknown")
        return {id:"unknown", label:"NOT DEFINED", rank:-1};
    return {
        id:"other",
        label:shortText(raw, 36).toUpperCase() || "NOT DEFINED",
        rank:-1
    };
}

function normalizeGauge(gauge, originLat, originLon) {
    if (!gauge || typeof gauge !== "object")
        return null;

    const latitude = validNumber(field(gauge, ["latitude", "lat"]));
    const longitude = validNumber(field(gauge, ["longitude", "lon", "lng"]));
    const lid = shortText(field(gauge, ["lid", "identifier", "id"]), 40);
    const name = shortText(field(gauge, ["name", "locationName"]), 140);
    if (latitude === null || longitude === null
            || Math.abs(latitude) > 90 || Math.abs(longitude) > 180
            || !lid || !name)
        return null;

    const distance = distanceKm(originLat, originLon, latitude, longitude);
    if (distance < 0)
        return null;

    const observedPrimary = validNumber(statusValue(
        gauge, "observed", ["primary", "primaryValue", "value"]
    ));
    const observedSecondary = validNumber(statusValue(
        gauge, "observed", ["secondary", "secondaryValue"]
    ));
    const forecastPrimary = validNumber(statusValue(
        gauge, "forecast", ["primary", "primaryValue", "value"]
    ));
    const forecastSecondary = validNumber(statusValue(
        gauge, "forecast", ["secondary", "secondaryValue"]
    ));

    const observedCategory = categoryInfo(statusValue(
        gauge, "observed",
        ["floodCategory", "flood_category", "category"]
    ));
    const forecastCategory = categoryInfo(statusValue(
        gauge, "forecast",
        ["floodCategory", "flood_category", "category"]
    ));

    const observedBlock = statusBlock(gauge, "observed");
    const forecastBlock = statusBlock(gauge, "forecast");
    const primaryUnits = shortText(
        field(observedBlock, ["primaryUnits", "primaryUnit"])
        || field(forecastBlock, ["primaryUnits", "primaryUnit"])
        || field(gauge, ["primaryUnits", "primaryUnit"]),
        24
    );
    const secondaryUnits = shortText(
        field(observedBlock, ["secondaryUnits", "secondaryUnit"])
        || field(forecastBlock, ["secondaryUnits", "secondaryUnit"])
        || field(gauge, ["secondaryUnits", "secondaryUnit"]),
        24
    );

    return {
        lid: lid,
        name: name,
        latitude: latitude,
        longitude: longitude,
        distanceKm: distance,
        state: shortText(
            gauge.state && gauge.state.abbreviation
                ? gauge.state.abbreviation
                : field(gauge, ["state", "stateAbbreviation"]),
            16
        ),
        wfo: shortText(
            gauge.wfo && gauge.wfo.abbreviation
                ? gauge.wfo.abbreviation
                : field(gauge, ["wfo", "wfoAbbreviation"]),
            16
        ),
        rfc: shortText(
            gauge.rfc && gauge.rfc.abbreviation
                ? gauge.rfc.abbreviation
                : field(gauge, ["rfc", "rfcAbbreviation"]),
            16
        ),
        observedPrimary: observedPrimary,
        observedSecondary: observedSecondary,
        forecastPrimary: forecastPrimary,
        forecastSecondary: forecastSecondary,
        primaryUnits: primaryUnits,
        secondaryUnits: secondaryUnits,
        observedCategory: observedCategory,
        forecastCategory: forecastCategory
    };
}

function gaugeArray(root) {
    if (Array.isArray(root))
        return root;
    if (root && Array.isArray(root.gauges))
        return root.gauges;
    if (root && root.data && Array.isArray(root.data.gauges))
        return root.data.gauges;
    throw new Error("Invalid NWPS gauge response");
}

function nearestGauges(root, originLat, originLon, limit) {
    const originLatitude = validNumber(originLat);
    const originLongitude = validNumber(originLon);
    if (originLatitude === null || originLongitude === null
            || Math.abs(originLatitude) > 90
            || Math.abs(originLongitude) > 180)
        throw new Error("Invalid NWPS origin");

    const requested = Math.max(
        1, Math.min(8, Math.floor(Number(limit) || 4))
    );
    const gauges = gaugeArray(root);
    const rows = [];
    for (let i = 0; i < gauges.length; i++) {
        const row = normalizeGauge(
            gauges[i], originLatitude, originLongitude
        );
        if (row)
            rows.push(row);
    }
    rows.sort(function(a, b) {
        if (a.distanceKm !== b.distanceKm)
            return a.distanceKm - b.distanceKm;
        return a.lid.localeCompare(b.lid);
    });
    return rows.slice(0, requested);
}

function nearestGauge(root, originLat, originLon) {
    const rows = nearestGauges(root, originLat, originLon, 1);
    return rows.length > 0 ? rows[0] : null;
}

function readingText(value, units) {
    const number = validNumber(value);
    if (number === null)
        return "--";
    const suffix = shortText(units, 16);
    return number.toFixed(2) + (suffix ? " " + suffix : "");
}

function isoMillis(value) {
    const raw = String(value || "").trim();
    const millis = Date.parse(raw);
    return isFinite(millis) ? millis : -1;
}

function utcLabel(value) {
    const millis = isoMillis(value);
    if (millis < 0)
        return "--";
    const iso = new Date(millis).toISOString();
    return iso.slice(0, 10) + " " + iso.slice(11, 16) + "Z";
}

function normalizeStageflowProduct(product) {
    if (!product || typeof product !== "object")
        return {
            available:false,
            pedts:"",
            issuedTime:"",
            issuedLabel:"--",
            wfo:"",
            timeZone:"",
            primaryName:"PRIMARY",
            primaryUnits:"",
            secondaryName:"",
            secondaryUnits:"",
            data:[]
        };

    const rawData = Array.isArray(product.data) ? product.data : [];
    const rows = [];
    for (let i = 0; i < rawData.length; i++) {
        const item = rawData[i];
        if (!item || typeof item !== "object")
            continue;
        const validTime = shortText(
            field(item, ["validTime", "valid_time", "time"]), 40
        );
        const validMillis = isoMillis(validTime);
        const primary = validNumber(
            field(item, ["primary", "primaryValue", "stage", "value"])
        );
        const secondary = validNumber(
            field(item, ["secondary", "secondaryValue", "flow"])
        );
        if (validMillis < 0 || (primary === null && secondary === null))
            continue;

        rows.push({
            validTime: validTime,
            validMillis: validMillis,
            validLabel: utcLabel(validTime),
            generatedTime: shortText(
                field(item, ["generatedTime", "generated_time"]), 40
            ),
            primary: primary,
            secondary: secondary
        });
    }
    rows.sort(function(a, b) {
        return a.validMillis - b.validMillis;
    });

    const primaryName = shortText(
        field(product, ["primaryName", "primary_name"]), 36
    ) || "PRIMARY";
    const secondaryName = shortText(
        field(product, ["secondaryName", "secondary_name"]), 36
    );

    return {
        available: rows.length > 0,
        pedts: shortText(field(product, ["pedts", "peds"]), 24),
        issuedTime: shortText(
            field(product, ["issuedTime", "issued_time"]), 40
        ),
        issuedLabel: utcLabel(
            field(product, ["issuedTime", "issued_time"])
        ),
        wfo: shortText(field(product, ["wfo"]), 16),
        timeZone: shortText(
            field(product, ["timeZone", "timezone", "time_zone"]), 24
        ),
        primaryName: primaryName.toUpperCase(),
        primaryUnits: shortText(
            field(product, ["primaryUnits", "primaryUnit"]), 24
        ),
        secondaryName: secondaryName.toUpperCase(),
        secondaryUnits: shortText(
            field(product, ["secondaryUnits", "secondaryUnit"]), 24
        ),
        data: rows
    };
}

function parseStageflow(root) {
    if (!root || typeof root !== "object" || Array.isArray(root))
        throw new Error("Invalid NWPS stageflow response");

    const observed = normalizeStageflowProduct(root.observed);
    const forecast = normalizeStageflowProduct(root.forecast);
    if (!observed.available && !forecast.available
            && !root.observed && !root.forecast)
        throw new Error("NWPS stageflow products missing");

    return {
        observed: observed,
        forecast: forecast
    };
}

function seriesTail(product, count) {
    if (!product || !Array.isArray(product.data))
        return [];
    const size = Math.max(0, Math.min(8, Math.floor(Number(count) || 0)));
    return product.data.slice(Math.max(0, product.data.length - size));
}

function seriesHead(product, count) {
    if (!product || !Array.isArray(product.data))
        return [];
    const size = Math.max(0, Math.min(8, Math.floor(Number(count) || 0)));
    return product.data.slice(0, size);
}

function pointReading(product, point) {
    if (!product || !point)
        return "--";
    const first = readingText(point.primary, product.primaryUnits);
    const secondary = validNumber(point.secondary);
    if (secondary === null || !product.secondaryName)
        return first;
    return first + " // "
         + product.secondaryName + " "
         + readingText(secondary, product.secondaryUnits);
}

function seriesWindow(product, count) {
    if (!product || !Array.isArray(product.data))
        return [];
    const size = Math.max(0, Math.min(24, Math.floor(Number(count) || 0)));
    return product.data.slice(Math.max(0, product.data.length - size));
}

function seriesStats(product, count) {
    const rows = seriesWindow(product, count);
    if (rows.length === 0) {
        return {
            available:false,
            points:0,
            first:null,
            latest:null,
            minimum:null,
            maximum:null,
            delta:null,
            direction:"UNAVAILABLE",
            spanHours:-1
        };
    }

    let minimum = null;
    let maximum = null;
    for (let i = 0; i < rows.length; i++) {
        const value = validNumber(rows[i].primary);
        if (value === null)
            continue;
        if (minimum === null || value < minimum)
            minimum = value;
        if (maximum === null || value > maximum)
            maximum = value;
    }

    const first = validNumber(rows[0].primary);
    const latest = validNumber(rows[rows.length - 1].primary);
    const delta = first !== null && latest !== null ? latest - first : null;
    let direction = "STEADY";
    if (delta === null)
        direction = "UNAVAILABLE";
    else if (delta > 0.01)
        direction = "RISING";
    else if (delta < -0.01)
        direction = "FALLING";

    const firstTime = validNumber(rows[0].validMillis);
    const lastTime = validNumber(rows[rows.length - 1].validMillis);
    const spanHours = firstTime !== null && lastTime !== null
        && lastTime >= firstTime
        ? (lastTime - firstTime) / 3600000 : -1;

    return {
        available:first !== null || latest !== null,
        points:rows.length,
        first:first,
        latest:latest,
        minimum:minimum,
        maximum:maximum,
        delta:delta,
        direction:direction,
        spanHours:spanHours
    };
}

function normalizedSeriesBars(product, count) {
    const rows = seriesWindow(product, count);
    const values = [];
    let minimum = null;
    let maximum = null;
    for (let i = 0; i < rows.length; i++) {
        const value = validNumber(rows[i].primary);
        if (value === null)
            continue;
        values.push(value);
        if (minimum === null || value < minimum)
            minimum = value;
        if (maximum === null || value > maximum)
            maximum = value;
    }
    if (values.length === 0)
        return [];

    const spread = maximum - minimum;
    const output = [];
    for (let i = 0; i < values.length; i++) {
        output.push({
            value:values[i],
            fraction:spread > 0
                ? (values[i] - minimum) / spread
                : 0.5
        });
    }
    return output;
}

