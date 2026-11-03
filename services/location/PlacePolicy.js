.pragma library

// Post-Apollo Places M2: user-supplied Home and temporary Explore context.
// A v1 Home-only file remains valid. No IP guessing, geocoding, or network calls.
const SCHEMA = "post-apollo.places.v1";
const MAX_REVISION = 9007199254740990;
const EXPLORE_DURATIONS = {"30M":1800000, "2H":7200000, "1D":86400000,
                           "MANUAL":null};

function initialDocument() {
    return {schema:SCHEMA, revision:0, home:null, explore:null};
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

function normalizeExplore(raw) {
    if (raw === null || raw === undefined)
        return {ok:true, value:null};
    if (!raw || typeof raw !== "object" || Array.isArray(raw)
            || !raw.place || typeof raw.place !== "object"
            || raw.place.source !== "MANUAL")
        return {ok:false, reason:"EXPLORE_INVALID"};

    const normalized = place(raw.place.label,
                             raw.place.latitude, raw.place.longitude);
    if (!normalized.ok)
        return {ok:false, reason:"EXPLORE_INVALID"};

    const duration = String(raw.durationKey || "");
    if (!Object.prototype.hasOwnProperty.call(EXPLORE_DURATIONS, duration))
        return {ok:false, reason:"EXPLORE_DURATION_INVALID"};
    const startedAtMs = raw.startedAtMs;
    if (!Number.isSafeInteger(startedAtMs) || startedAtMs <= 0
            || startedAtMs > MAX_REVISION)
        return {ok:false, reason:"EXPLORE_TIME_INVALID"};
    let expiresAtMs = null;
    if (duration !== "MANUAL") {
        expiresAtMs = startedAtMs + EXPLORE_DURATIONS[duration];
        if (!Number.isSafeInteger(expiresAtMs)
                || expiresAtMs > MAX_REVISION
                || raw.expiresAtMs !== expiresAtMs)
            return {ok:false, reason:"EXPLORE_TIME_INVALID"};
    } else if (raw.expiresAtMs !== null) {
        return {ok:false, reason:"EXPLORE_TIME_INVALID"};
    }

    return {
        ok:true,
        value:{
            place:normalized.value,
            durationKey:duration,
            startedAtMs:startedAtMs,
            expiresAtMs:expiresAtMs
        }
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

    // Files created by M1 omit explore altogether. Both forms are valid.
    const explore = normalizeExplore(documentRaw.explore);
    if (!explore.ok)
        return explore;
    if (explore.value && home === null)
        return {ok:false, reason:"EXPLORE_WITHOUT_HOME"};
    return {ok:true, document:{
        schema:SCHEMA, revision:revision, home:home, explore:explore.value
    }};
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

function nextRevision(document) {
    if (document.revision >= MAX_REVISION)
        return {ok:false, reason:"REVISION_LIMIT"};
    return {ok:true, revision:document.revision + 1};
}

function withHome(documentRaw, label, latitude, longitude) {
    const base = normalize(documentRaw);
    if (!base.ok)
        return base;
    const rev = nextRevision(base.document);
    if (!rev.ok)
        return rev;
    const nextHome = place(label, latitude, longitude);
    if (!nextHome.ok)
        return nextHome;
    return {
        ok:true,
        document:{
            schema:SCHEMA,
            revision:rev.revision,
            home:nextHome.value,
            explore:base.document.explore
        }
    };
}

function withExplore(documentRaw, label, latitude, longitude,
                     durationKey, nowMs) {
    const base = normalize(documentRaw);
    if (!base.ok)
        return base;
    if (!base.document.home)
        return {ok:false, reason:"HOME_NOT_SET"};
    const next = nextRevision(base.document);
    if (!next.ok)
        return next;
    const destination = place(label, latitude, longitude);
    if (!destination.ok)
        return destination;

    const duration = String(durationKey || "");
    if (!Object.prototype.hasOwnProperty.call(EXPLORE_DURATIONS, duration))
        return {ok:false, reason:"EXPLORE_DURATION_INVALID"};
    const started = Number(nowMs);
    if (!Number.isSafeInteger(started) || started <= 0
            || started > MAX_REVISION)
        return {ok:false, reason:"EXPLORE_TIME_INVALID"};
    const expiry = duration === "MANUAL"
        ? null : started + EXPLORE_DURATIONS[duration];
    if (expiry !== null && (!Number.isSafeInteger(expiry)
                            || expiry > MAX_REVISION))
        return {ok:false, reason:"EXPLORE_TIME_INVALID"};
    return {ok:true, document:{
        schema:SCHEMA, revision:next.revision,
        home:base.document.home,
        explore:{
            place:destination.value,
            durationKey:duration,
            startedAtMs:started,
            expiresAtMs:expiry
        }
    }};
}

function withoutExplore(documentRaw) {
    const base = normalize(documentRaw);
    if (!base.ok)
        return base;
    if (!base.document.explore)
        return {ok:false, reason:"NO_EXPLORE_TO_CLEAR"};
    const next = nextRevision(base.document);
    if (!next.ok)
        return next;
    return {ok:true, document:{
        schema:SCHEMA, revision:next.revision,
        home:base.document.home, explore:null
    }};
}

function activeExplore(documentRaw, nowMs) {
    const base = normalize(documentRaw);
    if (!base.ok || !base.document.explore)
        return null;
    const now = Number(nowMs);
    // Invalid clocks fail closed to Home, never activate stale exploration.
    if (!Number.isSafeInteger(now) || now <= 0)
        return null;
    const explore = base.document.explore;
    // A clock that moves behind the original start must not reactivate a
    // temporary destination. Fail closed to the explicitly saved Home.
    if (now < explore.startedAtMs)
        return null;
    return explore.expiresAtMs === null || now < explore.expiresAtMs
           ? explore : null;
}

function effectivePlace(documentRaw, nowMs) {
    const active = activeExplore(documentRaw, nowMs);
    if (active)
        return active.place;
    const base = normalize(documentRaw);
    return base.ok ? base.document.home : null;
}

function contextKind(documentRaw, nowMs) {
    if (activeExplore(documentRaw, nowMs))
        return "EXPLORE";
    const base = normalize(documentRaw);
    return base.ok && base.document.home ? "HOME" : "NONE";
}
