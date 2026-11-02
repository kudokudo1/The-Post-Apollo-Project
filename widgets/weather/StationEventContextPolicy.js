.pragma library

// Weather MAP M13 selected-event spatial context.
//
// This policy joins already-loaded MAP records. It never fetches, persists,
// interprets radar pixels, or asserts that nearby records describe one event.

function finite(value, fallback) {
    if (value === undefined || value === null || value === "")
        return fallback;
    const number = Number(value);
    return isFinite(number) ? number : fallback;
}

function safeText(value, limit) {
    return String(value === undefined || value === null ? "" : value)
        .trim().replace(/\s+/g, " ")
        .slice(0, Math.max(1, Number(limit) || 120));
}

function validPoint(latitude, longitude) {
    const lat = finite(latitude, null);
    const lon = finite(longitude, null);
    return lat !== null && lon !== null
        && Math.abs(lat) <= 90 && Math.abs(lon) <= 180;
}

function distanceKm(latA, lonA, latB, lonB) {
    if (!validPoint(latA, lonA) || !validPoint(latB, lonB))
        return -1;
    const a = Number(latA);
    const b = Number(lonA);
    const c = Number(latB);
    const d = Number(lonB);
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

function sourceLabel(sourceId) {
    switch (String(sourceId || "")) {
    case "gdacs": return "GDACS";
    case "usgs": return "USGS";
    case "eonet": return "NASA EONET";
    case "firms": return "NASA FIRMS";
    default: return "MAP SOURCE";
    }
}

function parseMillis(value) {
    if (value === undefined || value === null || value === "")
        return -1;
    const direct = Number(value);
    if (isFinite(direct) && direct > 0)
        return direct;
    const parsed = Date.parse(String(value));
    return isFinite(parsed) && parsed > 0 ? parsed : -1;
}

function utcLabel(value) {
    const ms = parseMillis(value);
    if (ms <= 0)
        return "-- UTC";
    const date = new Date(ms);
    return isNaN(date.getTime())
        ? "-- UTC"
        : date.toISOString().slice(0, 16).replace("T", " ") + " UTC";
}

function normalizeSelected(sourceId, row) {
    const source = String(sourceId || "");
    if (!row || typeof row !== "object")
        return null;

    let id = "";
    let title = "";
    let typeLabel = "";
    let latitude = null;
    let longitude = null;
    let timeMs = -1;
    let timeLabel = "-- UTC";

    if (source === "gdacs") {
        id = safeText(row.id, 100);
        title = safeText(row.name, 180);
        typeLabel = safeText(row.eventTypeLabel, 80);
        latitude = finite(row.latitude, null);
        longitude = finite(row.longitude, null);
        timeMs = parseMillis(row.timeMs);
        timeLabel = safeText(row.toUtc || row.fromUtc, 48) || utcLabel(timeMs);
    } else if (source === "usgs") {
        id = safeText(row.id, 100);
        title = "M" + (
            finite(row.magnitude, null) === null
            ? "--" : Number(row.magnitude).toFixed(1)
        ) + " // " + safeText(row.place, 150);
        typeLabel = "EARTHQUAKE";
        latitude = finite(row.latitude, null);
        longitude = finite(row.longitude, null);
        timeMs = parseMillis(row.time);
        timeLabel = utcLabel(timeMs);
    } else if (source === "eonet") {
        id = safeText(row.id, 100);
        title = safeText(row.title, 180);
        typeLabel = safeText(row.category, 80) || "NATURAL EVENT";
        latitude = finite(row.latitude, null);
        longitude = finite(row.longitude, null);
        timeMs = parseMillis(row.rawTime || row.time);
        timeLabel = safeText(row.time, 48) || utcLabel(timeMs);
    } else if (source === "firms") {
        id = safeText(row.id, 160);
        title = safeText(row.title, 120) || "VIIRS HOTSPOT";
        typeLabel = "THERMAL HOTSPOT";
        latitude = finite(row.latitude, null);
        longitude = finite(row.longitude, null);
        timeMs = parseMillis(row.acquiredUtc);
        timeLabel = safeText(row.acquiredUtc, 48) || utcLabel(timeMs);
    } else {
        return null;
    }

    return {
        sourceId: source,
        sourceLabel: sourceLabel(source),
        id: id,
        title: title || sourceLabel(source) + " EVENT",
        typeLabel: typeLabel || "EVENT",
        latitude: latitude,
        longitude: longitude,
        hasPoint: validPoint(latitude, longitude),
        coordinates: validPoint(latitude, longitude)
            ? Number(latitude).toFixed(3) + ", "
              + Number(longitude).toFixed(3)
            : "POINT LOCATION UNAVAILABLE",
        timeMs: timeMs,
        timeLabel: timeLabel
    };
}

function pointInBounds(latitude, longitude, bounds) {
    if (!validPoint(latitude, longitude)
            || !plainBoundsAvailable(bounds))
        return false;
    const west = finite(bounds.west, null);
    const south = finite(bounds.south, null);
    const east = finite(bounds.east, null);
    const north = finite(bounds.north, null);
    if (west === null || south === null
            || east === null || north === null
            || !(west < east) || !(south < north))
        return false;
    const lat = Number(latitude);
    const lon = Number(longitude);
    return lon >= west && lon <= east
        && lat >= south && lat <= north;
}

function radarCoverage(
    selected, bounds, loadedHistoryMinutes,
    requestedTimeMs, usingCache
) {
    const hasFrame = !!bounds && bounds.valid === true;
    const hasPoint = !!selected && selected.hasPoint === true;
    const covered = hasFrame && hasPoint
        && pointInBounds(selected.latitude, selected.longitude, bounds);
    const minutes = Math.max(
        0,
        Math.round(Number(loadedHistoryMinutes) || 0)
    );
    const frameLabel = minutes > 0 ? "-" + minutes + "M" : "NOW";
    const requested = Number(requestedTimeMs);
    return {
        available: hasFrame,
        covered: covered,
        frameLabel: frameLabel,
        timeLabel: isFinite(requested) && requested > 0
            ? utcLabel(requested) : "LATEST FRAME",
        usingCache: usingCache === true,
        timeMs: isFinite(requested) && requested > 0 ? requested : -1,
        status: !hasFrame
            ? "NO LOADED MRMS FRAME"
            : !hasPoint
              ? "EVENT HAS NO POINT COORDINATE"
              : covered
                ? "FRAME COVERS EVENT COORDINATE"
                : "EVENT OUTSIDE LOADED FRAME"
    };
}

function plainBoundsAvailable(bounds) {
    if (!bounds || typeof bounds !== "object" || bounds.valid === false)
        return false;
    const west = finite(bounds.west, null);
    const south = finite(bounds.south, null);
    const east = finite(bounds.east, null);
    const north = finite(bounds.north, null);
    return west !== null && south !== null
        && east !== null && north !== null
        && west < east && south < north;
}

function lightningCoverage(
    selected, bounds, ready, latestTime,
    windowMinutes, resolutionKm, radiusKm, usingCache
) {
    const hasFrame = ready === true && plainBoundsAvailable(bounds);
    const hasPoint = !!selected && selected.hasPoint === true;
    const covered = hasFrame && hasPoint
        && pointInBounds(selected.latitude, selected.longitude, bounds);
    const window = Math.max(
        0,
        Math.round(Number(windowMinutes) || 0)
    );
    const resolution = Math.max(
        0,
        Math.round(Number(resolutionKm) || 0)
    );
    const radius = Math.max(
        0,
        Math.round(Number(radiusKm) || 0)
    );
    return {
        available: hasFrame,
        covered: covered,
        timeLabel: safeText(latestTime, 48) || "LATEST",
        windowMinutes: window,
        resolutionKm: resolution,
        radiusKm: radius,
        usingCache: usingCache === true,
        timeMs: parseMillis(latestTime),
        status: !hasFrame
            ? "NO LOADED LIGHTNING FRAME"
            : !hasPoint
              ? "EVENT HAS NO POINT COORDINATE"
              : covered
                ? "FRAME COVERS EVENT COORDINATE"
                : "EVENT OUTSIDE LIGHTNING FRAME"
    };
}

function isFloodLike(selected) {
    if (!selected)
        return false;
    return safeText(selected.typeLabel, 80)
        .toUpperCase().indexOf("FLOOD") >= 0;
}

function compactReading(value, units) {
    const number = finite(value, null);
    if (number === null)
        return "--";
    const suffix = safeText(units, 16);
    return number.toFixed(2) + (suffix ? " " + suffix : "");
}

function latestObservedStage(stageflow) {
    const observed = stageflow
        && stageflow.observed
        && stageflow.observed.available
        && Array.isArray(stageflow.observed.data)
        ? stageflow.observed : null;
    if (!observed || observed.data.length === 0)
        return null;
    const row = observed.data[observed.data.length - 1];
    const previous = observed.data.length > 1
        ? observed.data[observed.data.length - 2] : null;
    const timeMs = finite(row.validMillis, -1);
    const previousTimeMs = previous
        ? finite(previous.validMillis, -1) : -1;
    return {
        value: finite(row.primary, null),
        units: safeText(observed.primaryUnits, 24),
        measurementName: safeText(observed.primaryName, 36),
        timeMs: timeMs,
        timeLabel: safeText(row.validLabel, 48) || utcLabel(timeMs),
        previousValue: previous ? finite(previous.primary, null) : null,
        previousTimeMs: previousTimeMs,
        previousTimeLabel: previous
            ? (safeText(previous.validLabel, 48)
               || utcLabel(previousTimeMs))
            : "--"
    };
}

function thresholdMeasurementKind(name) {
    const compact = safeText(name, 36).toUpperCase();
    if (compact.indexOf("STAGE") >= 0 || compact.indexOf("HEIGHT") >= 0)
        return "stage";
    if (compact.indexOf("FLOW") >= 0
            || compact.indexOf("DISCHARGE") >= 0)
        return "flow";
    return "";
}

function normalizedUnit(value) {
    return safeText(value, 24).toLowerCase();
}

function categoryRank(id) {
    switch (safeText(id, 24).toLowerCase()) {
    case "major": return 4;
    case "moderate": return 3;
    case "minor": return 2;
    case "action": return 1;
    case "none": return 0;
    default: return -1;
    }
}

function observedThresholdContext(gauge, gaugeContext, stageflow) {
    const unavailable = {
        available: false,
        supported: false,
        crossedInSeries: false,
        reason: "THRESHOLD CONTEXT UNAVAILABLE",
        measurementKind: "",
        measurementName: "",
        units: "",
        observedValue: null,
        categoryId: "",
        categoryLabel: "NOT DEFINED",
        categoryRank: -1,
        thresholdId: "",
        thresholdLabel: "",
        thresholdValue: null,
        aboveBy: null,
        nextThresholdLabel: "",
        nextThresholdValue: null,
        nextGap: null,
        crossingFromTimeMs: -1,
        crossingFromTimeLabel: "--",
        crossingToTimeMs: -1,
        crossingToTimeLabel: "--"
    };
    if (!gauge || !gaugeContext || gaugeContext.available !== true)
        return unavailable;

    const latest = latestObservedStage(stageflow);
    if (!latest || latest.value === null) {
        unavailable.reason = "NO OBSERVED NWPS READING";
        return unavailable;
    }

    const kind = thresholdMeasurementKind(latest.measurementName);
    if (!kind) {
        unavailable.reason = "OBSERVED MEASUREMENT TYPE NOT IDENTIFIED";
        return unavailable;
    }

    const expectedUnits = kind === "stage"
        ? safeText(gaugeContext.stageUnits, 24)
        : safeText(gaugeContext.flowUnits, 24);
    if (!expectedUnits
            || normalizedUnit(expectedUnits)
               !== normalizedUnit(latest.units)) {
        unavailable.reason = "OBSERVED UNITS DO NOT MATCH THRESHOLD UNITS";
        return unavailable;
    }

    const rawThresholds = Array.isArray(gaugeContext.thresholds)
        ? gaugeContext.thresholds : [];
    const thresholds = [];
    for (let i = 0; i < rawThresholds.length; i++) {
        const row = rawThresholds[i] || {};
        const value = finite(
            kind === "stage" ? row.stage : row.flow,
            null
        );
        if (value === null)
            continue;
        thresholds.push({
            id: safeText(row.id, 24).toLowerCase(),
            label: safeText(row.label, 36),
            value: value,
            rank: categoryRank(row.id)
        });
    }
    thresholds.sort(function(a, b) {
        if (a.value !== b.value)
            return a.value - b.value;
        return a.rank - b.rank;
    });
    if (thresholds.length === 0) {
        unavailable.reason = "NO MATCHING OFFICIAL THRESHOLDS";
        return unavailable;
    }

    const category = gauge.observedCategory || {};
    const observedCategoryId = safeText(category.id, 24).toLowerCase();
    const observedCategoryLabel = safeText(category.label, 40)
        || "NOT DEFINED";
    const observedCategoryRank = finite(
        category.rank,
        categoryRank(observedCategoryId)
    );

    let met = null;
    let next = null;
    for (let i = 0; i < thresholds.length; i++) {
        if (latest.value >= thresholds[i].value)
            met = thresholds[i];
        else {
            next = thresholds[i];
            break;
        }
    }

    const result = {
        available: true,
        supported: false,
        crossedInSeries: false,
        reason: "",
        measurementKind: kind,
        measurementName: latest.measurementName,
        units: latest.units,
        observedValue: latest.value,
        categoryId: observedCategoryId,
        categoryLabel: observedCategoryLabel,
        categoryRank: observedCategoryRank,
        thresholdId: met ? met.id : "",
        thresholdLabel: met ? met.label : "",
        thresholdValue: met ? met.value : null,
        aboveBy: met ? latest.value - met.value : null,
        nextThresholdLabel: next ? next.label : "",
        nextThresholdValue: next ? next.value : null,
        nextGap: next ? next.value - latest.value : null,
        crossingFromTimeMs: -1,
        crossingFromTimeLabel: "--",
        crossingToTimeMs: latest.timeMs,
        crossingToTimeLabel: latest.timeLabel
    };

    if (!met) {
        result.supported = observedCategoryRank === 0;
        result.reason = result.supported
            ? "BELOW ACTION // OBSERVED CATEGORY ALIGNED"
            : "CATEGORY/READING NOT ALIGNED // CLAIM WITHHELD";
        return result;
    }

    result.supported = observedCategoryId === met.id
        && observedCategoryRank === met.rank;
    if (!result.supported) {
        result.reason =
            "CATEGORY/READING NOT ALIGNED // CLAIM WITHHELD";
        return result;
    }

    const previousValue = finite(latest.previousValue, null);
    if (previousValue !== null
            && previousValue < met.value
            && latest.value >= met.value) {
        result.crossedInSeries = true;
        result.crossingFromTimeMs = latest.previousTimeMs;
        result.crossingFromTimeLabel = latest.previousTimeLabel;
        result.reason = "THRESHOLD CROSSED IN LOADED OBSERVED SERIES";
    } else {
        result.reason = "THRESHOLD MET // CATEGORY ALIGNED";
    }
    return result;
}

function floodGaugeContext(
    selected, gauge, gaugeContext, stageflow, maximumDistanceKm
) {
    const relevant = isFloodLike(selected);
    const limit = Math.max(
        10,
        Math.min(250, Number(maximumDistanceKm) || 100)
    );
    const base = {
        relevant: relevant,
        available: false,
        reason: "",
        maximumDistanceKm: limit,
        gaugeName: "",
        gaugeId: "",
        eventGaugeDistanceKm: -1,
        weatherFixGaugeDistanceKm: -1,
        observedCategory: "NOT DEFINED",
        forecastCategory: "NOT DEFINED",
        observedReading: "--",
        latestObserved: null,
        thresholdContext: {
            available: false,
            supported: false,
            crossedInSeries: false,
            reason: "THRESHOLD CONTEXT UNAVAILABLE"
        },
        thresholds: [],
        impacts: [],
        contextAvailable: false
    };

    if (!relevant) {
        base.reason = "SELECTED EVENT IS NOT AN EXPLICIT FLOOD";
        return base;
    }
    if (!selected || selected.hasPoint !== true) {
        base.reason = "FLOOD EVENT HAS NO POINT COORDINATE";
        return base;
    }
    if (!gauge || !validPoint(gauge.latitude, gauge.longitude)) {
        base.reason = "NWPS GAUGE CONTEXT UNAVAILABLE";
        return base;
    }

    const distance = distanceKm(
        selected.latitude, selected.longitude,
        gauge.latitude, gauge.longitude
    );
    base.gaugeName = safeText(gauge.name, 160);
    base.gaugeId = safeText(gauge.lid, 40);
    base.eventGaugeDistanceKm = distance;
    base.weatherFixGaugeDistanceKm = finite(gauge.distanceKm, -1);
    base.observedCategory = gauge.observedCategory
        ? safeText(gauge.observedCategory.label, 40) : "NOT DEFINED";
    base.forecastCategory = gauge.forecastCategory
        ? safeText(gauge.forecastCategory.label, 40) : "NOT DEFINED";
    base.observedReading = compactReading(
        gauge.observedPrimary,
        gauge.primaryUnits
    );

    const latest = latestObservedStage(stageflow);
    base.latestObserved = latest;

    const context = gaugeContext
        && typeof gaugeContext === "object"
        && gaugeContext.available === true
        ? gaugeContext : null;
    if (context) {
        base.contextAvailable = true;
        base.thresholds = Array.isArray(context.thresholds)
            ? context.thresholds.slice(0, 4) : [];
        base.impacts = Array.isArray(context.impacts)
            ? context.impacts.slice(0, 2) : [];
        base.thresholdContext = observedThresholdContext(
            gauge,
            context,
            stageflow
        );
    }

    if (distance < 0 || distance > limit) {
        base.reason = "NEAREST WEATHER-FIX GAUGE IS OUTSIDE "
            + Math.round(limit) + " KM EVENT GATE";
        return base;
    }

    base.available = true;
    base.reason = context
        ? "NEARBY NWPS GAUGE + OFFICIAL FLOOD METADATA"
        : "NEARBY NWPS GAUGE // METADATA NOT LOADED";
    return base;
}

function timelineRow(
    sourceLabel, provenanceGroup, kind,
    label, timeMs, provenance
) {
    const time = finite(timeMs, -1);
    if (time <= 0)
        return null;
    return {
        sourceLabel: safeText(sourceLabel, 40),
        provenanceGroup: safeText(provenanceGroup, 40),
        kind: safeText(kind, 40),
        label: safeText(label, 180),
        timeMs: time,
        timeLabel: utcLabel(time),
        provenance: safeText(provenance, 80)
    };
}

function evidenceTimeline(
    selected, companions, radarContext,
    lightningContext, floodContext, maximum
) {
    const rows = [];
    function add(row) {
        if (row)
            rows.push(row);
    }

    if (selected) {
        add(timelineRow(
            selected.sourceLabel,
            "EVENT RECORD",
            "SELECTED EVENT",
            selected.typeLabel + " // " + selected.title,
            selected.timeMs,
            "SOURCE EVENT TIME"
        ));
    }

    const nearby = Array.isArray(companions) ? companions : [];
    for (let i = 0; i < nearby.length; i++) {
        const row = nearby[i] || {};
        add(timelineRow(
            row.sourceLabel,
            "EVENT RECORD",
            "NEARBY RECORD",
            row.typeLabel + " // " + row.title,
            row.timeMs,
            "INDEPENDENT SOURCE RECORD"
        ));
    }

    if (radarContext && radarContext.available) {
        add(timelineRow(
            "NOAA MRMS",
            "REMOTE SENSING",
            "RADAR FRAME",
            radarContext.frameLabel || "FRAME",
            radarContext.timeMs,
            "LOADED FRAME TIME"
        ));
    }

    if (lightningContext && lightningContext.available) {
        add(timelineRow(
            "NOAA NOWCOAST",
            "REMOTE SENSING",
            "LIGHTNING FRAME",
            String(lightningContext.windowMinutes || 15)
                + "M DENSITY",
            lightningContext.timeMs,
            "LOADED FRAME TIME"
        ));
    }

    if (floodContext && floodContext.available
            && floodContext.latestObserved) {
        add(timelineRow(
            "NOAA NWPS",
            "GAUGE OBSERVATION",
            "OBSERVED STAGE",
            floodContext.gaugeId + " // "
                + compactReading(
                    floodContext.latestObserved.value,
                    floodContext.latestObserved.units
                  ),
            floodContext.latestObserved.timeMs,
            "GAUGE OBSERVATION TIME"
        ));
    }

    rows.sort(function(a, b) {
        if (a.timeMs !== b.timeMs)
            return b.timeMs - a.timeMs;
        return a.sourceLabel.localeCompare(b.sourceLabel);
    });

    const limit = Math.max(
        1,
        Math.min(12, Math.floor(Number(maximum) || 8))
    );
    return rows.slice(0, limit);
}

function compactOffsetMinutes(minutes) {
    const value = Math.abs(Number(minutes));
    if (!isFinite(value))
        return "--";
    if (value < 1)
        return "<1M";
    if (value < 60)
        return Math.round(value) + "M";
    const hours = value / 60;
    if (hours < 24)
        return hours.toFixed(hours < 10 ? 1 : 0) + "H";
    return Math.round(hours / 24) + "D";
}

function timeRelationship(anchorTimeMs, evidenceTimeMs) {
    const anchor = parseMillis(anchorTimeMs);
    const evidence = parseMillis(evidenceTimeMs);
    if (anchor <= 0 || evidence <= 0) {
        return {
            available: false,
            deltaMinutes: -1,
            direction: "UNKNOWN",
            band: "UNKNOWN",
            label: "TIME OFFSET UNAVAILABLE"
        };
    }

    const signedMinutes = (evidence - anchor) / 60000;
    const absoluteMinutes = Math.abs(signedMinutes);
    const direction = absoluteMinutes < 0.5
        ? "SAME SELECTED SOURCE TIME"
        : signedMinutes < 0
          ? "BEFORE SELECTED SOURCE TIME"
          : "AFTER SELECTED SOURCE TIME";
    const band = absoluteMinutes <= 15
        ? "WITHIN 15M"
        : absoluteMinutes <= 60
          ? "WITHIN 1H"
          : absoluteMinutes <= 360
            ? "WITHIN 6H"
            : absoluteMinutes <= 1440
              ? "WITHIN 24H"
              : "OVER 24H";

    return {
        available: true,
        deltaMinutes: absoluteMinutes,
        direction: direction,
        band: band,
        label: compactOffsetMinutes(absoluteMinutes)
            + " " + direction + " // " + band
    };
}

function spatialRelationship(distance) {
    const km = finite(distance, -1);
    if (km < 0) {
        return {
            available: false,
            distanceKm: -1,
            band: "UNKNOWN",
            label: "DISTANCE UNAVAILABLE"
        };
    }
    const band = km <= 25
        ? "LOCAL"
        : km <= 100
          ? "NEAR"
          : km <= 250
            ? "REGIONAL"
            : "DISTANT";
    return {
        available: true,
        distanceKm: km,
        band: band,
        label: Math.round(km) + " KM // " + band
    };
}

function relationshipRow(
    sourceLabelValue, evidenceClass, relationClass,
    spatialLabel, temporal, reason, limitation, distanceKm
) {
    return {
        sourceLabel: safeText(sourceLabelValue, 48),
        evidenceClass: safeText(evidenceClass, 48),
        relationClass: safeText(relationClass, 48),
        spatialLabel: safeText(spatialLabel, 120),
        temporalLabel: temporal && temporal.label
            ? safeText(temporal.label, 120)
            : "TIME OFFSET UNAVAILABLE",
        timeBand: temporal && temporal.band
            ? safeText(temporal.band, 40) : "UNKNOWN",
        timeDeltaMinutes: temporal && temporal.available
            ? finite(temporal.deltaMinutes, -1) : -1,
        reason: safeText(reason, 180),
        limitation: safeText(limitation, 180),
        distanceKm: finite(distanceKm, -1)
    };
}

function evidenceRelationships(
    selected, companions, radarContext,
    lightningContext, floodContext, maximum
) {
    if (!selected)
        return [];

    const rows = [];
    const nearby = Array.isArray(companions) ? companions : [];

    for (let i = 0; i < nearby.length && i < 4; i++) {
        const row = nearby[i] || {};
        const spatial = spatialRelationship(row.distanceKm);
        rows.push(relationshipRow(
            row.sourceLabel,
            "EVENT RECORD",
            "CROSS-SOURCE PROXIMITY",
            spatial.label,
            timeRelationship(selected.timeMs, row.timeMs),
            "CROSS-SOURCE RECORD ADMITTED BY 250 KM PROXIMITY RULE",
            "PROXIMITY + TIME OFFSET DO NOT ESTABLISH SAME INCIDENT",
            spatial.distanceKm
        ));
    }

    if (radarContext && radarContext.available
            && radarContext.covered === true) {
        rows.push(relationshipRow(
            "NOAA MRMS",
            "REMOTE SENSING",
            "FRAME COVERAGE",
            "EVENT POINT INSIDE LOADED MRMS FRAME",
            timeRelationship(selected.timeMs, radarContext.timeMs),
            "LOADED MRMS FRAME COVERS SELECTED EVENT POINT",
            "FRAME COVERAGE + TIME OFFSET DO NOT INTERPRET RADAR PIXELS",
            -1
        ));
    }

    if (lightningContext && lightningContext.available
            && lightningContext.covered === true) {
        rows.push(relationshipRow(
            "NOAA NOWCOAST",
            "REMOTE SENSING",
            "FRAME COVERAGE",
            "EVENT POINT INSIDE LOADED LIGHTNING FRAME",
            timeRelationship(selected.timeMs, lightningContext.timeMs),
            "LOADED LIGHTNING FRAME COVERS SELECTED EVENT POINT",
            "FRAME COVERAGE + TIME OFFSET DO NOT PROVE LIGHTNING AT EVENT",
            -1
        ));
    }

    if (floodContext && floodContext.available === true
            && floodContext.relevant === true) {
        const spatial = spatialRelationship(
            floodContext.eventGaugeDistanceKm
        );
        const observationTime = floodContext.latestObserved
            ? floodContext.latestObserved.timeMs : -1;
        rows.push(relationshipRow(
            "NOAA NWPS",
            "GAUGE OBSERVATION",
            "FLOOD-GATED PROXIMITY",
            spatial.label + " // EVENT TO GAUGE",
            timeRelationship(selected.timeMs, observationTime),
            "EXPLICIT FLOOD SELECTION + NWPS GAUGE WITHIN 100 KM EVENT GATE",
            "NEARBY GAUGE ≠ EVENT CATCHMENT OR INCIDENT IDENTITY",
            spatial.distanceKm
        ));
    }

    const limit = Math.max(
        1,
        Math.min(10, Math.floor(Number(maximum) || 8))
    );
    return rows.slice(0, limit);
}

function weatherFixDistance(selected, latitude, longitude) {
    if (!selected || selected.hasPoint !== true
            || !validPoint(latitude, longitude))
        return -1;
    return distanceKm(
        selected.latitude, selected.longitude,
        latitude, longitude
    );
}

function normalizeCompanion(sourceId, row) {
    return normalizeSelected(sourceId, row);
}

function nearbyEvidence(selected, bundles, radiusKm, maximum) {
    if (!selected || selected.hasPoint !== true)
        return [];

    const radius = Math.max(
        1,
        Math.min(2000, Number(radiusKm) || 250)
    );
    const limit = Math.max(
        1,
        Math.min(12, Math.floor(Number(maximum) || 6))
    );
    const sourceBundles = Array.isArray(bundles) ? bundles : [];
    const out = [];

    for (let i = 0; i < sourceBundles.length; i++) {
        const bundle = sourceBundles[i] || {};
        const sourceId = String(bundle.sourceId || "");
        if (!sourceId || sourceId === selected.sourceId)
            continue;
        const rows = Array.isArray(bundle.rows) ? bundle.rows : [];
        for (let j = 0; j < rows.length; j++) {
            const event = normalizeCompanion(sourceId, rows[j]);
            if (!event || event.hasPoint !== true)
                continue;
            const distance = distanceKm(
                selected.latitude, selected.longitude,
                event.latitude, event.longitude
            );
            if (distance < 0 || distance > radius)
                continue;
            out.push({
                sourceId: event.sourceId,
                sourceLabel: event.sourceLabel,
                id: event.id,
                title: event.title,
                typeLabel: event.typeLabel,
                latitude: event.latitude,
                longitude: event.longitude,
                coordinates: event.coordinates,
                timeMs: event.timeMs,
                timeLabel: event.timeLabel,
                distanceKm: distance
            });
        }
    }

    out.sort(function(a, b) {
        if (a.distanceKm !== b.distanceKm)
            return a.distanceKm - b.distanceKm;
        return Number(b.timeMs || -1) - Number(a.timeMs || -1);
    });

    return out.slice(0, limit);
}
