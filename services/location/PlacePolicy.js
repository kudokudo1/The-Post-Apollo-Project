.pragma library

// Post-Apollo Places M1: one explicitly supplied Home point.
// No IP geolocation, external lookup, time-zone guessing or automatic fallback.
const SCHEMA = "post-apollo.places.v1";
const MAX_REVISION = 9007199254740990;

function initialDocument() {
    return {schema:SCHEMA, revision:0, home:null};
}

function coordinate(value, maxAbs) {
    if (value === undefined || value === null)
        return null;
    const text = String(value).trim();
    if (!/^[-+]?(?:[0-9]{1,3}(?:\.[0-9]{1,6})?|\.[0-9]{1,6})$/.test(text))
        return null;
    const number = Number(text);
    if (!isFinite(number) || Math.abs(number) > maxAbs)
        return null;
    return Number(number.toFixed(6));
}

function place(labelRaw, latitudeRaw, longitudeRaw) {
    const label = String(labelRaw === undefined || labelRaw === null
                         ? "" : labelRaw).trim();
    if (!label || label.length > 64 || /[\u0000-\u001f\u007f]/.test(label))
        return {ok:false, reason:"HOME_LABEL_INVALID"};
    const latitude = coordinate(latitudeRaw, 90);
    if (latitude === null)
        return {ok:false, reason:"LATITUDE_INVALID"};
    const longitude = coordinate(longitudeRaw, 180);
    if (longitude === null)
        return {ok:false, reason:"LONGITUDE_INVALID"};
    return {
        ok:true,
        value:{label:label, latitude:latitude, longitude:longitude,
               source:"MANUAL"}
    };
}

function normalize(documentRaw) {
    if (!documentRaw || typeof documentRaw !== "object"
            || Array.isArray(documentRaw))
        return {ok:false, reason:"DOCUMENT_INVALID"};
    if (documentRaw.schema !== SCHEMA)
        return {ok:false, reason:"UNSUPPORTED_VERSION"};
    const revision = documentRaw.revision;
    if (!Number.isSafeInteger(revision) || revision < 0
            || revision > MAX_REVISION)
        return {ok:false, reason:"REVISION_INVALID"};
    let home = null;
    if (documentRaw.home !== null) {
        if (!documentRaw.home || typeof documentRaw.home !== "object"
                || Array.isArray(documentRaw.home)
                || documentRaw.home.source !== "MANUAL")
            return {ok:false, reason:"HOME_INVALID"};
        const normalized = place(documentRaw.home.label,
                                 documentRaw.home.latitude,
                                 documentRaw.home.longitude);
        if (!normalized.ok)
            return {ok:false, reason:"HOME_INVALID"};
        home = normalized.value;
    }
    return {ok:true, document:{schema:SCHEMA, revision:revision, home:home}};
}

function parse(textRaw) {
    const raw = String(textRaw === undefined || textRaw === null ? "" : textRaw);
    if (!raw.trim() || raw.length > 4096)
        return {ok:false, reason:"DOCUMENT_INVALID"};
    let input;
    try {
        input = JSON.parse(raw);
    } catch (e) {
        return {ok:false, reason:"JSON_INVALID"};
    }
    return normalize(input);
}

function withHome(documentRaw, label, latitude, longitude) {
    const base = normalize(documentRaw);
    if (!base.ok)
        return base;
    if (base.document.revision >= MAX_REVISION)
        return {ok:false, reason:"REVISION_LIMIT"};
    const nextHome = place(label, latitude, longitude);
    if (!nextHome.ok)
        return nextHome;
    return {
        ok:true,
        document:{
            schema:SCHEMA,
            revision:base.document.revision + 1,
            home:nextHome.value
        }
    };
}
