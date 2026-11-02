.pragma library

var SCHEMA = "post-apollo.weather-last-known.v1";
var VERSION = 1;
var MAX_RECORDS = 13;
var MAX_TEXT = 160;
var MAX_ARRAY_JSON = 65536;

var _known = {
    "weather-current": true,
    "weather-forecast": true,
    "air-quality": true,
    "space-kp": true,
    "space-wind": true,
    "space-imf": true,
    "space-flux": true,
    "seismic": true,
    "gdacs": true,
    "nws-alerts": true,
    "river": true,
    "marine": true,
    "coastal": true
};

var _scoped = {
    "river": true,
    "marine": true,
    "coastal": true,
    "nws-alerts": true
};

function initialDocument() {
    return {
        schema: SCHEMA,
        version: VERSION,
        revision: 0,
        records: ({})
    };
}

function safeText(value, maxLength) {
    const limit = Math.max(1, Number(maxLength) || MAX_TEXT);
    const text = String(value === undefined || value === null ? "" : value);
    return text.length <= limit ? text : text.slice(0, limit);
}

function finiteNumber(value, fallback) {
    if (value === undefined || value === null || value === "")
        return fallback;
    const number = Number(value);
    return isFinite(number) ? number : fallback;
}

function positiveMillis(value) {
    const number = Number(value);
    return Number.isFinite
        ? (Number.isFinite(number) && number > 0 ? Math.floor(number) : -1)
        : (isFinite(number) && number > 0 ? Math.floor(number) : -1);
}

function boundedJson(value, fallback, maxChars) {
    try {
        const raw = JSON.stringify(value);
        if (typeof raw !== "string"
                || raw.length > Math.max(1, Number(maxChars) || MAX_ARRAY_JSON))
            return fallback;
        return JSON.parse(raw);
    } catch (error) {
        return fallback;
    }
}

function boundedArray(value, limit) {
    if (!Array.isArray(value))
        return [];
    const sliced = value.slice(0, Math.max(0, Number(limit) || 0));
    const copy = boundedJson(sliced, null, MAX_ARRAY_JSON);
    return Array.isArray(copy) ? copy : [];
}

function boundedObject(value) {
    if (!value || typeof value !== "object" || Array.isArray(value))
        return ({});
    const copy = boundedJson(value, null, 16384);
    return copy && typeof copy === "object" && !Array.isArray(copy)
        ? copy : ({});
}


function normalizeNwsPointKey(value) {
    const text = safeText(value, 64).trim();
    if (!/^-?\d{1,2}(?:\.\d{1,4})?\s*,\s*-?\d{1,3}(?:\.\d{1,4})?$/.test(text))
        return "";
    const values = text.split(",").map(function(v) {
        return Number(v.trim());
    });
    if (!isFinite(values[0]) || !isFinite(values[1])
            || Math.abs(values[0]) > 90 || Math.abs(values[1]) > 180)
        return "";
    return String(values[0]) + "," + String(values[1]);
}

function nwsDisplaySeverity(raw) {
    const severity = String(raw || "").toLowerCase();
    return severity === "extreme" || severity === "severe" ? "critical"
        : severity === "moderate" ? "warning" : "normal";
}

function normalizeNwsAlert(value) {
    if (!value || typeof value !== "object" || Array.isArray(value))
        return null;

    const id = safeText(value.id, 512);
    const event = safeText(value.event, 128);
    const revision = safeText(value.revision, 1024);
    const status = safeText(value.status, 24);
    if (!id || !event || !revision || status !== "Actual")
        return null;

    const severity = safeText(value.severity, 24);
    return {
        id:id,
        event:event,
        headline:safeText(value.headline, 300),
        area:safeText(value.area, 240),
        issuer:safeText(value.issuer, 120),
        severity:severity,
        urgency:safeText(value.urgency, 24),
        certainty:safeText(value.certainty, 24),
        status:status,
        messageType:safeText(value.messageType, 24),
        category:safeText(value.category, 48),
        response:safeText(value.response, 48),
        displaySeverity:nwsDisplaySeverity(severity),
        description:safeText(value.description, 640),
        instruction:safeText(value.instruction, 320),
        sent:safeText(value.sent, 45),
        updated:safeText(value.updated, 45),
        effective:safeText(value.effective, 45),
        onset:safeText(value.onset, 45),
        expires:safeText(value.expires, 45),
        ends:safeText(value.ends, 45),
        revision:revision
    };
}

function normalizeNwsEntries(value) {
    const source = Array.isArray(value) ? value : [];
    const out = [];
    const seen = ({});

    for (let i = 0; i < source.length && out.length < 64; i++) {
        const row = source[i] || {};
        const alert = normalizeNwsAlert(row.alert);
        if (!alert || seen[alert.id])
            continue;

        const id = safeText(row.id, 512);
        const revision = safeText(row.revision, 1024);
        if (id !== alert.id || revision !== alert.revision)
            continue;

        seen[id] = true;
        out.push({
            id:id,
            revision:revision,
            absent:Math.min(
                1,
                Math.max(0, Math.floor(finiteNumber(row.absent, 0)))
            ),
            alert:alert
        });
    }

    out.sort(function(a, b) {
        return String(a.id).localeCompare(String(b.id));
    });
    return out;
}

function normalizeSeismicEvents(value) {
    if (!Array.isArray(value))
        return [];

    const out = [];
    for (let i = 0; i < value.length && out.length < 50; i++) {
        const row = value[i] || {};
        const magnitude = finiteNumber(row.magnitude, null);
        const time = positiveMillis(row.time);
        const latitude = finiteNumber(row.latitude, null);
        const longitude = finiteNumber(row.longitude, null);
        if (magnitude === null || magnitude < 2.5
                || time <= 0 || latitude === null || longitude === null
                || Math.abs(latitude) > 90 || Math.abs(longitude) > 180)
            continue;

        out.push({
            id: safeText(row.id, 128),
            magnitude: magnitude,
            place: safeText(row.place, 180),
            time: time,
            updated: positiveMillis(row.updated),
            utc: safeText(row.utc, 32),
            depthKm: finiteNumber(row.depthKm, -1),
            latitude: latitude,
            longitude: longitude,
            significance: finiteNumber(row.significance, -1),
            tsunami: row.tsunami === true,
            status: safeText(row.status, 32),
            alert: safeText(row.alert, 24),
            magType: safeText(row.magType, 24)
        });
    }
    return out;
}

function normalizeGdacsEvents(value) {
    if (!Array.isArray(value))
        return [];

    const out = [];
    for (let i = 0; i < value.length && out.length < 50; i++) {
        const row = value[i] || {};
        const latitude = finiteNumber(row.latitude, null);
        const longitude = finiteNumber(row.longitude, null);
        const timeMs = positiveMillis(row.timeMs);
        if (latitude === null || longitude === null || timeMs <= 0
                || Math.abs(latitude) > 90 || Math.abs(longitude) > 180)
            continue;

        const alert = safeText(row.alertLevel, 16).toUpperCase();
        out.push({
            id: safeText(row.id, 160),
            eventId: safeText(row.eventId, 80),
            episodeId: safeText(row.episodeId, 80),
            eventType: safeText(row.eventType, 16),
            eventTypeLabel: safeText(row.eventTypeLabel, 64),
            name: safeText(row.name, 180),
            alertLevel: alert === "RED" || alert === "ORANGE"
                        || alert === "GREEN" ? alert : "UNKNOWN",
            alertScore: finiteNumber(row.alertScore, -1),
            alertToken: safeText(row.alertToken, 16),
            isCurrent: row.isCurrent === true,
            country: safeText(row.country, 120),
            iso3: safeText(row.iso3, 8),
            source: safeText(row.source, 64),
            latitude: latitude,
            longitude: longitude,
            coordinates: safeText(row.coordinates, 48),
            geometryType: "Point",
            fromUtc: safeText(row.fromUtc, 40),
            toUtc: safeText(row.toUtc, 40),
            timeMs: timeMs,
            severity: finiteNumber(row.severity, -1),
            severityText: safeText(row.severityText, 160),
            severityUnit: safeText(row.severityUnit, 40),
            reportUrl: safeText(row.reportUrl, 512),
            detailsUrl: safeText(row.detailsUrl, 512)
        });
    }
    return out;
}

function normalizeLocationKey(value) {
    const text = safeText(value, 64);
    const parts = text.split("|");
    if (parts.length !== 2)
        return "";
    const lat = finiteNumber(parts[0], null);
    const lon = finiteNumber(parts[1], null);
    if (lat === null || lon === null
            || Math.abs(lat) > 90 || Math.abs(lon) > 180)
        return "";
    return lat.toFixed(3) + "|" + lon.toFixed(3);
}

function normalizeRiverGauge(value) {
    if (!value || typeof value !== "object")
        return null;
    const lid = safeText(value.lid, 40);
    const latitude = finiteNumber(value.latitude, null);
    const longitude = finiteNumber(value.longitude, null);
    if (!lid || latitude === null || longitude === null
            || Math.abs(latitude) > 90 || Math.abs(longitude) > 180)
        return null;
    function category(raw) {
        const source = raw && typeof raw === "object" ? raw : {};
        return {
            id:safeText(source.id, 24),
            label:safeText(source.label, 48),
            rank:finiteNumber(source.rank, -1)
        };
    }
    return {
        lid:lid,
        name:safeText(value.name, 160),
        latitude:latitude,
        longitude:longitude,
        distanceKm:finiteNumber(value.distanceKm, -1),
        state:safeText(value.state, 16),
        wfo:safeText(value.wfo, 16),
        rfc:safeText(value.rfc, 16),
        observedPrimary:finiteNumber(value.observedPrimary, null),
        observedSecondary:finiteNumber(value.observedSecondary, null),
        forecastPrimary:finiteNumber(value.forecastPrimary, null),
        forecastSecondary:finiteNumber(value.forecastSecondary, null),
        primaryUnits:safeText(value.primaryUnits, 24),
        secondaryUnits:safeText(value.secondaryUnits, 24),
        observedCategory:category(value.observedCategory),
        forecastCategory:category(value.forecastCategory)
    };
}

function normalizeRiverProduct(value) {
    const source = value && typeof value === "object" ? value : {};
    const rows = [];
    const data = Array.isArray(source.data) ? source.data : [];
    for (let i = 0; i < data.length && rows.length < 48; i++) {
        const row = data[i] || {};
        const validMillis = positiveMillis(row.validMillis);
        const primary = finiteNumber(row.primary, null);
        const secondary = finiteNumber(row.secondary, null);
        if (validMillis <= 0 || (primary === null && secondary === null))
            continue;
        rows.push({
            validTime:safeText(row.validTime, 40),
            validMillis:validMillis,
            validLabel:safeText(row.validLabel, 40),
            generatedTime:safeText(row.generatedTime, 40),
            primary:primary,
            secondary:secondary
        });
    }
    return {
        available:rows.length > 0,
        pedts:safeText(source.pedts, 24),
        issuedTime:safeText(source.issuedTime, 40),
        issuedLabel:safeText(source.issuedLabel, 40),
        wfo:safeText(source.wfo, 16),
        timeZone:safeText(source.timeZone, 24),
        primaryName:safeText(source.primaryName, 36),
        primaryUnits:safeText(source.primaryUnits, 24),
        secondaryName:safeText(source.secondaryName, 36),
        secondaryUnits:safeText(source.secondaryUnits, 24),
        data:rows
    };
}

function normalizeRiverContext(value) {
    const source = value && typeof value === "object" ? value : {};

    const thresholds = [];
    const thresholdSource = Array.isArray(source.thresholds)
        ? source.thresholds : [];
    for (let i = 0; i < thresholdSource.length && thresholds.length < 4; i++) {
        const row = thresholdSource[i] || {};
        const stage = finiteNumber(row.stage, null);
        const flow = finiteNumber(row.flow, null);
        if (stage === null && flow === null)
            continue;
        thresholds.push({
            id:safeText(row.id, 24),
            label:safeText(row.label, 40),
            stage:stage,
            flow:flow
        });
    }

    const impacts = [];
    const impactSource = Array.isArray(source.impacts) ? source.impacts : [];
    for (let i = 0; i < impactSource.length && impacts.length < 20; i++) {
        const row = impactSource[i] || {};
        const stage = finiteNumber(row.stage, null);
        const statement = safeText(row.statement, 420);
        if (stage === null || !statement)
            continue;
        impacts.push({stage:stage, statement:statement});
    }

    function crests(value) {
        const rows = [];
        const input = Array.isArray(value) ? value : [];
        for (let i = 0; i < input.length && rows.length < 10; i++) {
            const row = input[i] || {};
            const occurredMillis = positiveMillis(row.occurredMillis);
            const stage = finiteNumber(row.stage, null);
            const flow = finiteNumber(row.flow, null);
            if (occurredMillis <= 0 || (stage === null && flow === null))
                continue;
            rows.push({
                occurredTime:safeText(row.occurredTime, 40),
                occurredLabel:safeText(row.occurredLabel, 40),
                occurredMillis:occurredMillis,
                stage:stage,
                flow:flow,
                preliminary:safeText(row.preliminary, 12),
                oldDatum:row.oldDatum === true
            });
        }
        return rows;
    }

    const notes = [];
    const noteSource = Array.isArray(source.notes) ? source.notes : [];
    for (let i = 0; i < noteSource.length && notes.length < 4; i++) {
        const row = noteSource[i] || {};
        const statement = safeText(row.statement, 320);
        if (!statement)
            continue;
        notes.push({
            statement:statement,
            effective:safeText(row.effective, 40),
            expiration:safeText(row.expiration, 40)
        });
    }

    return {
        available:source.available === true,
        lid:safeText(source.lid, 40),
        usgsId:safeText(source.usgsId, 40),
        description:safeText(source.description, 180),
        county:safeText(source.county, 80),
        timeZone:safeText(source.timeZone, 40),
        stageUnits:safeText(source.stageUnits, 24),
        flowUnits:safeText(source.flowUnits, 24),
        thresholds:thresholds,
        impacts:impacts,
        recentCrests:crests(source.recentCrests),
        historicCrests:crests(source.historicCrests),
        inundationAvailable:source.inundationAvailable === true,
        notes:notes
    };
}

function normalizeMarineStation(value) {
    if (!value || typeof value !== "object")
        return null;
    const stationId = safeText(value.stationId, 16);
    const latitude = finiteNumber(value.latitude, null);
    const longitude = finiteNumber(value.longitude, null);
    const sampleMillis = positiveMillis(value.sampleMillis);
    if (!stationId || latitude === null || longitude === null
            || sampleMillis <= 0
            || Math.abs(latitude) > 90 || Math.abs(longitude) > 180)
        return null;
    return {
        stationId:stationId,
        latitude:latitude,
        longitude:longitude,
        sampleMillis:sampleMillis,
        sampleUtc:safeText(value.sampleUtc, 40),
        distanceKm:finiteNumber(value.distanceKm, -1),
        windDirection:finiteNumber(value.windDirection, null),
        windSpeedMs:finiteNumber(value.windSpeedMs, null),
        gustMs:finiteNumber(value.gustMs, null),
        waveHeightM:finiteNumber(value.waveHeightM, null),
        dominantPeriodS:finiteNumber(value.dominantPeriodS, null),
        averagePeriodS:finiteNumber(value.averagePeriodS, null),
        meanWaveDirection:finiteNumber(value.meanWaveDirection, null),
        pressureHpa:finiteNumber(value.pressureHpa, null),
        pressureTendencyHpa:finiteNumber(value.pressureTendencyHpa, null),
        airTempC:finiteNumber(value.airTempC, null),
        waterTempC:finiteNumber(value.waterTempC, null),
        dewpointC:finiteNumber(value.dewpointC, null),
        visibilityNm:finiteNumber(value.visibilityNm, null),
        tideFt:finiteNumber(value.tideFt, null)
    };
}

function normalizeCoastalStation(value) {
    if (!value || typeof value !== "object")
        return null;
    const id = safeText(value.id, 24);
    const latitude = finiteNumber(value.latitude, null);
    const longitude = finiteNumber(value.longitude, null);
    if (!id || latitude === null || longitude === null
            || Math.abs(latitude) > 90 || Math.abs(longitude) > 180)
        return null;
    return {
        id:id,
        name:safeText(value.name, 100),
        latitude:latitude,
        longitude:longitude,
        distanceKm:finiteNumber(value.distanceKm, -1),
        state:safeText(value.state, 24),
        timezone:safeText(value.timezone, 64),
        tidal:value.tidal === true,
        greatLakes:value.greatLakes === true,
        affiliations:safeText(value.affiliations, 80),
        predictionType:safeText(value.predictionType, 8),
        referenceId:safeText(value.referenceId, 24)
    };
}

function normalizeWaterLevel(value) {
    if (!value || typeof value !== "object")
        return null;
    const sampleMillis = positiveMillis(value.sampleMillis);
    const level = finiteNumber(value.value, null);
    if (sampleMillis <= 0 || level === null)
        return null;
    return {
        value:level,
        time:safeText(value.time, 40),
        sampleMillis:sampleMillis,
        sampleUtc:safeText(value.sampleUtc, 40),
        sigma:finiteNumber(value.sigma, null),
        flags:safeText(value.flags, 40),
        quality:safeText(value.quality, 12),
        qualityLabel:safeText(value.qualityLabel, 40)
    };
}

function normalizeTidePredictions(value) {
    if (!Array.isArray(value))
        return [];
    const out = [];
    for (let i = 0; i < value.length && out.length < 12; i++) {
        const row = value[i] || {};
        const sampleMillis = positiveMillis(row.sampleMillis);
        const level = finiteNumber(row.value, null);
        if (sampleMillis <= 0 || level === null)
            continue;
        out.push({
            time:safeText(row.time, 40),
            sampleMillis:sampleMillis,
            sampleUtc:safeText(row.sampleUtc, 40),
            value:level,
            type:safeText(row.type, 8),
            label:safeText(row.label, 32),
            high:row.high === true ? true
                : row.high === false ? false : null
        });
    }
    return out;
}

function normalizePayload(sourceId, payload) {
    const source = payload || {};

    if (sourceId === "weather-current") {
        const result = {
            tempF: safeText(source.tempF, 24),
            feelsLikeF: safeText(source.feelsLikeF, 24),
            condition: safeText(source.condition, 96),
            weatherCode: safeText(source.weatherCode, 24),
            uvIndex: finiteNumber(source.uvIndex, -1),
            humidity: safeText(source.humidity, 24),
            windMph: safeText(source.windMph, 24),
            windDirection: safeText(source.windDirection, 24),
            pressureHpa: finiteNumber(source.pressureHpa, -1),
            visibilityMiles: finiteNumber(source.visibilityMiles, -1),
            cloudCover: finiteNumber(source.cloudCover, -1),
            precipMm: finiteNumber(source.precipMm, -1),
            observationTime: safeText(source.observationTime, 96),
            localObservationDateTime:
                safeText(source.localObservationDateTime, 96),
            latitude: safeText(source.latitude, 32),
            longitude: safeText(source.longitude, 32)
        };
        if (result.tempF === "" && result.condition === "")
            return null;
        return result;
    }

    if (sourceId === "weather-forecast") {
        const hourly = boundedArray(source.hourlyForecast, 12);
        const daily = boundedArray(source.dailyForecast, 10);
        if (hourly.length === 0 && daily.length === 0)
            return null;
        return {
            hourlyForecast: hourly,
            dailyForecast: daily
        };
    }

    if (sourceId === "air-quality") {
        const aqi = finiteNumber(source.aqi, -1);
        if (aqi < 0 || aqi > 500)
            return null;
        return {
            aqi: Math.round(aqi),
            aqiLabel: safeText(source.aqiLabel, 32),
            ozoneAqi: finiteNumber(source.ozoneAqi, -1),
            nitrogenDioxideAqi: finiteNumber(source.nitrogenDioxideAqi, -1),
            carbonMonoxideAqi: finiteNumber(source.carbonMonoxideAqi, -1),
            pm25: finiteNumber(source.pm25, -1),
            pm10: finiteNumber(source.pm10, -1),
            carbonMonoxide: finiteNumber(source.carbonMonoxide, -1),
            nitrogenDioxide: finiteNumber(source.nitrogenDioxide, -1),
            ozone: finiteNumber(source.ozone, -1),
            dust: finiteNumber(source.dust, -1),
            alderPollen: finiteNumber(source.alderPollen, -1),
            birchPollen: finiteNumber(source.birchPollen, -1),
            grassPollen: finiteNumber(source.grassPollen, -1),
            mugwortPollen: finiteNumber(source.mugwortPollen, -1),
            olivePollen: finiteNumber(source.olivePollen, -1),
            ragweedPollen: finiteNumber(source.ragweedPollen, -1),
            pollenAvailable: source.pollenAvailable === true,
            airQualitySourceTime:
                safeText(source.airQualitySourceTime, 64),
            airQualityUtcOffsetMinutes:
                source.airQualityUtcOffsetMinutes === null
                || source.airQualityUtcOffsetMinutes === undefined
                ? null
                : finiteNumber(source.airQualityUtcOffsetMinutes, null),
            airQualityTimezone:
                safeText(source.airQualityTimezone, 80),
            airQualityTimezoneAbbreviation:
                safeText(source.airQualityTimezoneAbbreviation, 24),
            airQualityForecast:
                boundedArray(source.airQualityForecast, 6)
        };
    }

    if (sourceId === "space-kp") {
        const kp = finiteNumber(source.kp, -1);
        if (kp < 0 || kp > 9)
            return null;
        return {
            kp: kp,
            kpTime: safeText(source.kpTime, 64),
            kpHistory: boundedArray(source.kpHistory, 24),
            kpHistorySummary: boundedObject(source.kpHistorySummary)
        };
    }

    if (sourceId === "space-wind") {
        const speed = finiteNumber(source.solarWindSpeed, -1);
        if (speed < 0)
            return null;
        return {
            solarWindSpeed: speed,
            solarWindTime: safeText(source.solarWindTime, 64)
        };
    }

    if (sourceId === "space-imf") {
        const bt = finiteNumber(source.magneticFieldBt, null);
        const bz = finiteNumber(source.magneticFieldBz, null);
        if (bt === null || bz === null)
            return null;
        return {
            magneticFieldBt: bt,
            magneticFieldBz: bz,
            magneticFieldTime: safeText(source.magneticFieldTime, 64)
        };
    }

    if (sourceId === "space-flux") {
        const flux = finiteNumber(source.solarFlux, -1);
        if (flux < 0)
            return null;
        return {
            solarFlux: flux,
            solarFluxTime: safeText(source.solarFluxTime, 64)
        };
    }

    if (sourceId === "nws-alerts") {
        const point = normalizeNwsPointKey(source.point);
        if (!point)
            return null;
        return {
            point:point,
            entries:normalizeNwsEntries(source.entries)
        };
    }

    if (sourceId === "seismic") {
        const events = normalizeSeismicEvents(source.events);
        return events.length > 0 ? {events:events} : null;
    }

    if (sourceId === "gdacs") {
        const events = normalizeGdacsEvents(source.events);
        return events.length > 0 ? {events:events} : null;
    }

    if (sourceId === "river") {
        const locationKey = normalizeLocationKey(source.locationKey);
        const gauge = normalizeRiverGauge(source.gauge);
        if (!locationKey || !gauge)
            return null;
        const nearby = [];
        const sourceNearby = Array.isArray(source.nearbyGauges)
            ? source.nearbyGauges : [];
        for (let i = 0; i < sourceNearby.length && nearby.length < 4; i++) {
            const row = normalizeRiverGauge(sourceNearby[i]);
            if (row)
                nearby.push(row);
        }
        return {
            locationKey:locationKey,
            gauge:gauge,
            nearbyGauges:nearby,
            stageflow:{
                observed:normalizeRiverProduct(
                    source.stageflow ? source.stageflow.observed : null
                ),
                forecast:normalizeRiverProduct(
                    source.stageflow ? source.stageflow.forecast : null
                )
            },
            stageflowGaugeId:safeText(source.stageflowGaugeId, 40),
            gaugeContext:normalizeRiverContext(source.gaugeContext),
            contextGaugeId:safeText(source.contextGaugeId, 40)
        };
    }

    if (sourceId === "marine") {
        const locationKey = normalizeLocationKey(source.locationKey);
        const station = normalizeMarineStation(source.station);
        if (!locationKey || !station)
            return null;
        return {
            locationKey:locationKey,
            station:station,
            reportingStations:Math.max(
                0, Math.floor(finiteNumber(source.reportingStations, 0))
            )
        };
    }

    if (sourceId === "coastal") {
        const locationKey = normalizeLocationKey(source.locationKey);
        const waterStation = normalizeCoastalStation(source.waterStation);
        const tideStation = normalizeCoastalStation(source.tideStation);
        if (!locationKey || !waterStation || !tideStation)
            return null;
        return {
            locationKey:locationKey,
            waterStation:waterStation,
            tideStation:tideStation,
            waterLevel:normalizeWaterLevel(source.waterLevel),
            tidePredictions:normalizeTidePredictions(source.tidePredictions)
        };
    }

    return null;
}

function normalizeRecord(sourceId, record) {
    if (!_known[sourceId] || !record || typeof record !== "object")
        return null;
    const receivedAtMs = positiveMillis(record.receivedAtMs);
    const savedAtMs = positiveMillis(record.savedAtMs);
    const payload = normalizePayload(sourceId, record.payload);
    if (receivedAtMs <= 0 || savedAtMs <= 0 || !payload)
        return null;

    const scopeKey = safeText(record.scopeKey, 96);
    const requestKey = safeText(record.requestKey, 192);

    if (_scoped[sourceId]) {
        if (!scopeKey || !requestKey)
            return null;

        if (sourceId === "nws-alerts") {
            if (normalizeNwsPointKey(scopeKey) !== scopeKey
                    || payload.point !== scopeKey
                    || requestKey !== "nws|" + scopeKey)
                return null;
        } else {
            if (normalizeLocationKey(scopeKey) !== scopeKey
                    || payload.locationKey !== scopeKey)
                return null;

            let expected = "";
            if (sourceId === "river")
                expected = scopeKey + "|" + payload.gauge.lid;
            else if (sourceId === "marine")
                expected = scopeKey + "|" + payload.station.stationId;
            else if (sourceId === "coastal")
                expected = scopeKey + "|" + payload.waterStation.id
                         + "|" + payload.tideStation.id;

            if (!expected || requestKey !== expected)
                return null;
        }
    }

    return {
        sourceId: sourceId,
        receivedAtMs: receivedAtMs,
        savedAtMs: savedAtMs,
        scopeKey: scopeKey,
        requestKey: requestKey,
        payload: payload
    };
}

function normalizeDocument(value) {
    if (!value || typeof value !== "object" || Array.isArray(value))
        return {ok:false, reason:"INVALID_DOCUMENT"};

    if (String(value.schema || "") !== SCHEMA)
        return {ok:false, reason:"INVALID_SCHEMA"};

    if (Number(value.version) !== VERSION)
        return {ok:false, reason:"UNSUPPORTED_VERSION"};

    const revision = Number(value.revision);
    if (!Number.isSafeInteger(revision) || revision < 0)
        return {ok:false, reason:"INVALID_REVISION"};

    const inputRecords = value.records;
    if (!inputRecords || typeof inputRecords !== "object"
            || Array.isArray(inputRecords))
        return {ok:false, reason:"INVALID_RECORDS"};

    const keys = Object.keys(inputRecords);
    if (keys.length > MAX_RECORDS)
        return {ok:false, reason:"TOO_MANY_RECORDS"};

    const records = ({});
    for (let i = 0; i < keys.length; i++) {
        const id = String(keys[i]);
        if (!_known[id])
            return {ok:false, reason:"UNKNOWN_RECORD"};
        const record = normalizeRecord(id, inputRecords[id]);
        if (!record)
            return {ok:false, reason:"INVALID_RECORD"};
        records[id] = record;
    }

    return {
        ok:true,
        document:{
            schema:SCHEMA,
            version:VERSION,
            revision:revision,
            records:records
        }
    };
}

function parse(raw) {
    let value;
    try {
        value = JSON.parse(String(raw || ""));
    } catch (error) {
        return {ok:false, reason:"INVALID_JSON"};
    }
    return normalizeDocument(value);
}

function upsert(
    document, sourceId, receivedAtMs, payload, savedAtMs,
    scopeKey, requestKey
) {
    const normalized = normalizeDocument(document);
    if (!normalized.ok)
        return normalized;

    const id = String(sourceId || "");
    if (!_known[id])
        return {ok:false, reason:"UNKNOWN_RECORD"};

    const record = normalizeRecord(id, {
        receivedAtMs:receivedAtMs,
        savedAtMs:savedAtMs,
        scopeKey:scopeKey,
        requestKey:requestKey,
        payload:payload
    });
    if (!record)
        return {ok:false, reason:"INVALID_RECORD"};

    const existing = normalized.document.records[id];
    if (existing && record.receivedAtMs < existing.receivedAtMs)
        return {ok:false, reason:"OLDER_RECORD"};

    const records = ({});
    const keys = Object.keys(normalized.document.records);
    for (let i = 0; i < keys.length; i++)
        records[keys[i]] = normalized.document.records[keys[i]];
    records[id] = record;

    return {
        ok:true,
        document:{
            schema:SCHEMA,
            version:VERSION,
            revision:normalized.document.revision + 1,
            records:records
        }
    };
}

function record(document, sourceId) {
    const normalized = normalizeDocument(document);
    if (!normalized.ok)
        return null;
    const id = String(sourceId || "");
    return normalized.document.records[id] || null;
}

function knownSourceIds() {
    return Object.keys(_known);
}
