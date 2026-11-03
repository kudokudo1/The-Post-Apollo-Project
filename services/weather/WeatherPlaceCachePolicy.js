.pragma library

// M6b user-selected weather cache. Independent of the legacy unscoped cache.
// Every record belongs to an exact, validated MANUAL|latitude|longitude key.
var SCHEMA = "post-apollo.weather-place-cache.v1";
var VERSION = 1;
var MAX_RECORDS = 30;
var MAX_DOCUMENT_BYTES = 262144;
var MAX_PAYLOAD_BYTES = 24576;
var MAX_REVISION = 9007199254740990;
var TTL = {
    "weather-current": 5400000,    // 90 minutes
    "weather-forecast": 43200000,  // 12 hours
    "air-quality": 10800000        // 3 hours
};

function initialDocument() {
    return {schema:SCHEMA, version:VERSION, revision:0, records:[]};
}

function key(value) {
    const text = typeof value === "string" ? value : "";
    const m = /^MANUAL\|(-?\d{1,2}(?:\.\d{1,6})?)\|(-?\d{1,3}(?:\.\d{1,6})?)$/.exec(text);
    if (!m)
        return "";
    const latitude = Number(m[1]);
    const longitude = Number(m[2]);
    if (!isFinite(latitude) || !isFinite(longitude)
            || Math.abs(latitude) > 90 || Math.abs(longitude) > 180
            || String(latitude) !== m[1] || String(longitude) !== m[2])
        return "";
    return "MANUAL|" + latitude + "|" + longitude;
}

function safeText(input, max) {
    if (input === null || input === undefined)
        return "";
    const text = String(input);
    return text.length <= max && !/[\u0000-\u001f\u007f]/.test(text) ? text : "";
}

function num(input, fallback) {
    return typeof input === "number" && isFinite(input) ? input : fallback;
}

function boundedArray(input, limit) {
    if (!Array.isArray(input) || input.length > limit)
        return null;
    let raw = "";
    try { raw = JSON.stringify(input); } catch (e) { return null; }
    if (typeof raw !== "string" || raw.length > MAX_PAYLOAD_BYTES)
        return null;
    const items = JSON.parse(raw);
    for (let i = 0; i < items.length; i++) {
        if (!items[i] || typeof items[i] !== "object"
                || Array.isArray(items[i]))
            return null;
    }
    return items;
}

function payload(kind, raw) {
    if (!raw || typeof raw !== "object" || Array.isArray(raw))
        return null;
    if (kind === "weather-current") {
        const tempF = safeText(raw.tempF, 24);
        if (!tempF || tempF === "--")
            return null;
        return {
            tempF:tempF,
            feelsLikeF:safeText(raw.feelsLikeF,24),
            condition:safeText(raw.condition,96),
            weatherCode:safeText(raw.weatherCode,24),
            uvIndex:num(raw.uvIndex,-1),
            humidity:safeText(raw.humidity,24),
            windMph:safeText(raw.windMph,24),
            windDirection:safeText(raw.windDirection,24),
            pressureHpa:num(raw.pressureHpa,-1),
            visibilityMiles:num(raw.visibilityMiles,-1),
            cloudCover:num(raw.cloudCover,-1),
            precipMm:num(raw.precipMm,-1),
            observationTime:safeText(raw.observationTime,96),
            localObservationDateTime:safeText(raw.localObservationDateTime,96)
        };
    }
    if (kind === "weather-forecast") {
        const hourly = boundedArray(raw.hourlyForecast,12);
        const daily = boundedArray(raw.dailyForecast,10);
        if (!hourly || !daily || (!hourly.length && !daily.length))
            return null;
        return {hourlyForecast:hourly,dailyForecast:daily};
    }
    if (kind === "air-quality") {
        const aqi = num(raw.aqi,-1);
        if (aqi < 0 || aqi > 500)
            return null;
        const forecast = boundedArray(raw.airQualityForecast,12);
        if (!forecast)
            return null;
        return {
            aqi:Math.round(aqi), aqiLabel:safeText(raw.aqiLabel,32),
            ozoneAqi:num(raw.ozoneAqi,-1),
            nitrogenDioxideAqi:num(raw.nitrogenDioxideAqi,-1),
            carbonMonoxideAqi:num(raw.carbonMonoxideAqi,-1),
            pm25:num(raw.pm25,-1),pm10:num(raw.pm10,-1),
            carbonMonoxide:num(raw.carbonMonoxide,-1),
            nitrogenDioxide:num(raw.nitrogenDioxide,-1),
            ozone:num(raw.ozone,-1),dust:num(raw.dust,-1),
            alderPollen:num(raw.alderPollen,-1),
            birchPollen:num(raw.birchPollen,-1),
            grassPollen:num(raw.grassPollen,-1),
            mugwortPollen:num(raw.mugwortPollen,-1),
            olivePollen:num(raw.olivePollen,-1),
            ragweedPollen:num(raw.ragweedPollen,-1),
            pollenAvailable:raw.pollenAvailable === true,
            airQualitySourceTime:safeText(raw.airQualitySourceTime,64),
            airQualityUtcOffsetMinutes:
                raw.airQualityUtcOffsetMinutes === null
                || raw.airQualityUtcOffsetMinutes === undefined
                ? null : num(raw.airQualityUtcOffsetMinutes,null),
            airQualityTimezone:safeText(raw.airQualityTimezone,80),
            airQualityTimezoneAbbreviation:
                safeText(raw.airQualityTimezoneAbbreviation,24),
            airQualityForecast:forecast
        };
    }
    return null;
}

function normalizeRecord(raw) {
    if (!raw || typeof raw !== "object" || Array.isArray(raw))
        return null;
    const kind = String(raw.kind || "");
    const scopeKey = key(raw.scopeKey);
    const timestamp = raw.receivedAtMs;
    const provider = String(raw.provider || "");
    if (!Object.prototype.hasOwnProperty.call(TTL,kind) || !scopeKey
            || !Number.isSafeInteger(timestamp) || timestamp <= 0
            || timestamp > MAX_REVISION)
        return null;
    if (kind === "air-quality"
            ? provider !== "OPEN_METEO_AQI"
            : provider !== "WTTR" && provider !== "OPEN_METEO")
        return null;
    const cleanPayload = payload(kind,raw.payload);
    if (!cleanPayload)
        return null;
    return {kind:kind,scopeKey:scopeKey,provider:provider,
            receivedAtMs:timestamp,payload:cleanPayload};
}

function normalizeDocument(raw) {
    if (!raw || typeof raw !== "object" || Array.isArray(raw))
        return {ok:false,reason:"INVALID_DOCUMENT"};
    if (raw.schema !== SCHEMA || raw.version !== VERSION)
        return {ok:false,reason:"UNSUPPORTED_VERSION"};
    if (!Number.isSafeInteger(raw.revision) || raw.revision < 0
            || raw.revision > MAX_REVISION)
        return {ok:false,reason:"INVALID_REVISION"};
    if (!Array.isArray(raw.records) || raw.records.length > MAX_RECORDS)
        return {ok:false,reason:"INVALID_RECORDS"};
    const seen = new Set();
    const records = [];
    for (let i = 0; i < raw.records.length; ++i) {
        const record = normalizeRecord(raw.records[i]);
        if (!record)
            return {ok:false,reason:"INVALID_RECORD"};
        const id = record.scopeKey + "|" + record.kind;
        if (seen.has(id))
            return {ok:false,reason:"DUPLICATE_RECORD"};
        seen.add(id);
        records.push(record);
    }
    return {ok:true, document:{
        schema:SCHEMA,version:VERSION,revision:raw.revision,records:records
    }};
}

function parse(textRaw) {
    const text = typeof textRaw === "string" ? textRaw : "";
    if (!text || text.length > MAX_DOCUMENT_BYTES)
        return {ok:false,reason:"DOCUMENT_TOO_LARGE_OR_EMPTY"};
    let decoded;
    try { decoded = JSON.parse(text); }
    catch (error) { return {ok:false,reason:"INVALID_JSON"}; }
    return normalizeDocument(decoded);
}

function upsert(documentRaw, kind, scopeKey, receivedAtMs, provider, data) {
    const normalized = normalizeDocument(documentRaw);
    if (!normalized.ok)
        return normalized;
    if (normalized.document.revision >= MAX_REVISION)
        return {ok:false,reason:"REVISION_LIMIT"};
    const nextRecord = normalizeRecord({
        kind:kind,scopeKey:scopeKey,receivedAtMs:receivedAtMs,
        provider:provider,payload:data
    });
    if (!nextRecord)
        return {ok:false,reason:"INVALID_RECORD"};
    const prior = normalized.document.records.find(function(r) {
        return r.kind === nextRecord.kind && r.scopeKey === nextRecord.scopeKey;
    });
    if (prior && prior.receivedAtMs > receivedAtMs)
        return {ok:false,reason:"OLDER_RECORD"};
    let records = normalized.document.records.filter(function(r) {
        return r.kind !== nextRecord.kind || r.scopeKey !== nextRecord.scopeKey;
    });
    records.push(nextRecord);
    records.sort(function(a,b) {
        return a.receivedAtMs - b.receivedAtMs
               || a.scopeKey.localeCompare(b.scopeKey)
               || a.kind.localeCompare(b.kind);
    });
    if (records.length > MAX_RECORDS)
        records = records.slice(records.length - MAX_RECORDS);
    const candidate = {
        schema:SCHEMA,version:VERSION,
        revision:normalized.document.revision+1,records:records
    };
    if (JSON.stringify(candidate).length > MAX_DOCUMENT_BYTES)
        return {ok:false,reason:"DOCUMENT_FULL"};
    return {ok:true,document:candidate};
}

function record(documentRaw, kind, scopeKey, nowMs) {
    const normalized = normalizeDocument(documentRaw);
    const canonical = key(scopeKey);
    if (!normalized.ok || !canonical
            || !Object.prototype.hasOwnProperty.call(TTL,kind)
            || !Number.isSafeInteger(nowMs) || nowMs <= 0)
        return null;
    const found = normalized.document.records.find(function(r) {
        return r.kind === kind && r.scopeKey === canonical;
    });
    if (!found)
        return null;
    const age = nowMs - found.receivedAtMs;
    // Never trust a future snapshot or an expired snapshot as current.
    if (age < 0 || age > TTL[kind])
        return null;
    return found;
}
