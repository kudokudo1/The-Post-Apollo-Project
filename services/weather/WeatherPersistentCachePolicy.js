.pragma library

var SCHEMA = "post-apollo.weather-last-known.v1";
var VERSION = 1;
var MAX_RECORDS = 9;
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
    "gdacs": true
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

    if (sourceId === "seismic") {
        const events = normalizeSeismicEvents(source.events);
        return events.length > 0 ? {events:events} : null;
    }

    if (sourceId === "gdacs") {
        const events = normalizeGdacsEvents(source.events);
        return events.length > 0 ? {events:events} : null;
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
    return {
        sourceId: sourceId,
        receivedAtMs: receivedAtMs,
        savedAtMs: savedAtMs,
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

function upsert(document, sourceId, receivedAtMs, payload, savedAtMs) {
    const normalized = normalizeDocument(document);
    if (!normalized.ok)
        return normalized;

    const id = String(sourceId || "");
    if (!_known[id])
        return {ok:false, reason:"UNKNOWN_RECORD"};

    const record = normalizeRecord(id, {
        receivedAtMs:receivedAtMs,
        savedAtMs:savedAtMs,
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
