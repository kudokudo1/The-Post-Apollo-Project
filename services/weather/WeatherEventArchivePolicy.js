.pragma library

// Weather event evidence archive M19.
//
// Durable operator-requested source snapshots. This is intentionally separate
// from operational last-known cache, M10 scalar live history and frame cache.
//
// Identity contract:
// - exact provider source + provider-native event id;
// - never merge GDACS/USGS/EONET/FIRMS into one incident id;
// - archive only explicit operator requests;
// - identical snapshots dedupe instead of inventing revisions.

var SCHEMA = "post-apollo.weather-event-archive.v1";
var VERSION = 1;
var MAX_EVENTS = 256;
var MAX_SNAPSHOTS_PER_EVENT = 32;
var MAX_AGE_MS = 180 * 24 * 60 * 60 * 1000;

function knownSourceIds() {
    return ["eonet", "firms", "gdacs", "usgs"];
}

function sourceKnown(sourceId) {
    return knownSourceIds().indexOf(String(sourceId || "")) >= 0;
}

function sourceLabel(sourceId) {
    switch (String(sourceId || "")) {
    case "gdacs": return "GDACS";
    case "usgs": return "USGS";
    case "eonet": return "NASA EONET";
    case "firms": return "NASA FIRMS";
    default: return "UNKNOWN";
    }
}

function safeText(value, maximum) {
    const text = String(
        value === undefined || value === null ? "" : value
    ).trim();
    const limit = Math.max(1, Math.floor(Number(maximum) || 128));
    let out = "";
    for (let i = 0; i < text.length && out.length < limit; i++) {
        const code = text.charCodeAt(i);
        if (code >= 32 && code !== 127)
            out += text[i];
    }
    return out;
}

function finite(value, fallback) {
    if (value === undefined || value === null || value === "")
        return fallback;
    const number = Number(value);
    return isFinite(number) ? number : fallback;
}

function positiveMillis(value) {
    if (value === undefined || value === null || value === "")
        return -1;
    if (typeof value === "number")
        return isFinite(value) && value > 0 ? Math.floor(value) : -1;
    if (typeof value.getTime === "function") {
        const ms = value.getTime();
        return isFinite(ms) && ms > 0 ? Math.floor(ms) : -1;
    }
    const raw = String(value).trim();
    if (!raw)
        return -1;
    const direct = Number(raw);
    if (isFinite(direct))
        return direct > 0 ? Math.floor(direct) : -1;
    const parsed = Date.parse(raw);
    return isFinite(parsed) && parsed > 0 ? Math.floor(parsed) : -1;
}

function boundedLatitude(value) {
    const number = finite(value, null);
    return number !== null && Math.abs(number) <= 90 ? number : null;
}

function boundedLongitude(value) {
    const number = finite(value, null);
    return number !== null && Math.abs(number) <= 180 ? number : null;
}

function initialDocument() {
    return {
        schema: SCHEMA,
        version: VERSION,
        revision: 0,
        events: {}
    };
}

function eventIdentity(sourceId, row) {
    const source = String(sourceId || "");
    if (!sourceKnown(source) || !row || typeof row !== "object")
        return null;
    const eventId = safeText(row.id, 180);
    if (!eventId)
        return null;
    return {
        sourceId: source,
        sourceLabel: sourceLabel(source),
        eventId: eventId,
        eventKey: source + "|" + eventId
    };
}

function normalizedPayload(sourceId, row) {
    const source = row && typeof row === "object" ? row : {};

    if (sourceId === "gdacs") {
        return {
            eventId: safeText(source.eventId, 80),
            episodeId: safeText(source.episodeId, 80),
            eventType: safeText(source.eventType, 24),
            alertLevel: safeText(source.alertLevel, 24),
            alertScore: finite(source.alertScore, -1),
            isCurrent: source.isCurrent === true,
            country: safeText(source.country, 100),
            iso3: safeText(source.iso3, 12),
            severity: finite(source.severity, -1),
            severityText: safeText(source.severityText, 180),
            severityUnit: safeText(source.severityUnit, 40),
            fromUtc: safeText(source.fromUtc, 64),
            toUtc: safeText(source.toUtc, 64),
            reportUrl: safeText(source.reportUrl, 400),
            detailsUrl: safeText(source.detailsUrl, 400)
        };
    }

    if (sourceId === "usgs") {
        return {
            magnitude: finite(source.magnitude, -1),
            place: safeText(source.place, 180),
            time: positiveMillis(source.time),
            updated: positiveMillis(source.updated),
            depthKm: finite(source.depthKm, -1),
            significance: finite(source.significance, -1),
            tsunami: source.tsunami === true,
            status: safeText(source.status, 40),
            alert: safeText(source.alert, 40),
            magType: safeText(source.magType, 24)
        };
    }

    if (sourceId === "eonet") {
        return {
            description: safeText(source.description, 480),
            category: safeText(source.category, 80),
            categoryId: safeText(source.categoryId, 48),
            rawTime: safeText(source.rawTime, 64),
            geometryType: safeText(source.geometryType, 40),
            sourceNames: safeText(source.sourceNames, 240),
            magnitude: safeText(source.magnitude, 120),
            url: safeText(source.url, 400)
        };
    }

    if (sourceId === "firms") {
        return {
            acquiredUtc: safeText(source.acquiredUtc, 64),
            brightnessK: finite(source.brightnessK, -1),
            frpMw: finite(source.frpMw, -1),
            confidenceCode: safeText(source.confidenceCode, 24),
            confidenceLabel: safeText(source.confidenceLabel, 32),
            satellite: safeText(source.satellite, 32),
            instrument: safeText(source.instrument, 32),
            dayNight: safeText(source.dayNight, 16),
            version: safeText(source.version, 48)
        };
    }

    return null;
}

function sourceTimeMs(sourceId, row) {
    const source = row && typeof row === "object" ? row : {};
    if (sourceId === "gdacs")
        return positiveMillis(source.timeMs);
    if (sourceId === "usgs")
        return positiveMillis(source.time);
    if (sourceId === "eonet")
        return positiveMillis(source.rawTime || source.time);
    if (sourceId === "firms")
        return positiveMillis(source.acquiredUtc);
    return -1;
}

function commonTitle(sourceId, row) {
    const source = row && typeof row === "object" ? row : {};
    if (sourceId === "gdacs")
        return safeText(source.name, 180) || "GDACS EVENT";
    if (sourceId === "usgs") {
        const magnitude = finite(source.magnitude, null);
        const mag = magnitude === null ? "M--" : "M" + magnitude.toFixed(1);
        return mag + " // " + (
            safeText(source.place, 160) || "LOCATION UNAVAILABLE"
        );
    }
    if (sourceId === "eonet")
        return safeText(source.title, 180) || "NASA EONET EVENT";
    if (sourceId === "firms")
        return safeText(source.title, 120) || "VIIRS HOTSPOT";
    return "EVENT";
}

function commonType(sourceId, row) {
    const source = row && typeof row === "object" ? row : {};
    if (sourceId === "gdacs")
        return safeText(source.eventTypeLabel, 80)
            || safeText(source.eventType, 40)
            || "DISASTER";
    if (sourceId === "usgs")
        return "EARTHQUAKE";
    if (sourceId === "eonet")
        return safeText(source.category, 80) || "NATURAL EVENT";
    if (sourceId === "firms")
        return "THERMAL HOTSPOT";
    return "EVENT";
}

function normalizeSnapshot(sourceId, row, capturedAtMs) {
    const identity = eventIdentity(sourceId, row);
    const captured = positiveMillis(capturedAtMs);
    if (!identity || captured <= 0)
        return null;

    const payload = normalizedPayload(identity.sourceId, row);
    if (!payload)
        return null;

    return {
        sourceId: identity.sourceId,
        sourceLabel: identity.sourceLabel,
        eventId: identity.eventId,
        eventKey: identity.eventKey,
        capturedAtMs: captured,
        sourceTimeMs: sourceTimeMs(identity.sourceId, row),
        title: commonTitle(identity.sourceId, row),
        typeLabel: commonType(identity.sourceId, row),
        latitude: boundedLatitude(row.latitude),
        longitude: boundedLongitude(row.longitude),
        payload: payload
    };
}

function normalizeStoredSnapshot(value, sourceId, eventId) {
    if (!value || typeof value !== "object")
        return null;
    const source = String(sourceId || "");
    const id = safeText(eventId, 180);
    if (!sourceKnown(source) || !id
            || String(value.sourceId || "") !== source
            || safeText(value.eventId, 180) !== id)
        return null;

    const captured = positiveMillis(value.capturedAtMs);
    if (captured <= 0)
        return null;
    const payload = normalizedPayload(source, value.payload);
    if (!payload)
        return null;

    return {
        sourceId: source,
        sourceLabel: sourceLabel(source),
        eventId: id,
        eventKey: source + "|" + id,
        capturedAtMs: captured,
        sourceTimeMs: positiveMillis(value.sourceTimeMs),
        title: safeText(value.title, 180) || sourceLabel(source) + " EVENT",
        typeLabel: safeText(value.typeLabel, 80) || "EVENT",
        latitude: boundedLatitude(value.latitude),
        longitude: boundedLongitude(value.longitude),
        payload: payload
    };
}

function snapshotFingerprint(snapshot) {
    if (!snapshot)
        return "";
    return JSON.stringify({
        sourceId: snapshot.sourceId,
        eventId: snapshot.eventId,
        sourceTimeMs: snapshot.sourceTimeMs,
        title: snapshot.title,
        typeLabel: snapshot.typeLabel,
        latitude: snapshot.latitude,
        longitude: snapshot.longitude,
        payload: snapshot.payload
    });
}

function normalizeEvent(value, nowMs) {
    if (!value || typeof value !== "object")
        return null;
    const source = String(value.sourceId || "");
    const eventId = safeText(value.eventId, 180);
    if (!sourceKnown(source) || !eventId)
        return null;

    const sourceRows = Array.isArray(value.snapshots) ? value.snapshots : [];
    const cutoff = positiveMillis(nowMs) > 0
        ? positiveMillis(nowMs) - MAX_AGE_MS : -1;
    const snapshots = [];
    for (let i = 0; i < sourceRows.length; i++) {
        const row = normalizeStoredSnapshot(sourceRows[i], source, eventId);
        if (!row)
            continue;
        if (cutoff > 0 && row.capturedAtMs < cutoff)
            continue;
        snapshots.push(row);
    }
    snapshots.sort(function(a, b) {
        return a.capturedAtMs - b.capturedAtMs;
    });
    if (snapshots.length > MAX_SNAPSHOTS_PER_EVENT)
        snapshots.splice(0, snapshots.length - MAX_SNAPSHOTS_PER_EVENT);
    if (snapshots.length === 0)
        return null;

    const first = snapshots[0];
    const last = snapshots[snapshots.length - 1];
    return {
        sourceId: source,
        sourceLabel: sourceLabel(source),
        eventId: eventId,
        eventKey: source + "|" + eventId,
        title: last.title,
        typeLabel: last.typeLabel,
        firstCapturedAtMs: first.capturedAtMs,
        lastCapturedAtMs: last.capturedAtMs,
        snapshots: snapshots
    };
}

function normalizeDocument(value, nowMs) {
    if (!value || typeof value !== "object" || Array.isArray(value))
        return null;
    if (value.schema !== SCHEMA || Number(value.version) !== VERSION)
        return null;

    const sourceEvents = value.events
        && typeof value.events === "object"
        && !Array.isArray(value.events)
        ? value.events : {};
    const events = {};
    const keys = Object.keys(sourceEvents);
    for (let i = 0; i < keys.length; i++) {
        const event = normalizeEvent(sourceEvents[keys[i]], nowMs);
        if (event)
            events[event.eventKey] = event;
    }

    const sorted = Object.keys(events).sort(function(a, b) {
        return events[b].lastCapturedAtMs - events[a].lastCapturedAtMs;
    });
    for (let i = MAX_EVENTS; i < sorted.length; i++)
        delete events[sorted[i]];

    return {
        schema: SCHEMA,
        version: VERSION,
        revision: Math.max(0, Math.floor(Number(value.revision) || 0)),
        events: events
    };
}

function parse(raw, nowMs) {
    const text = String(raw || "").trim();
    if (!text)
        return {ok:true, document:initialDocument(), reason:"EMPTY"};
    try {
        const parsed = JSON.parse(text);
        if (!parsed || parsed.schema !== SCHEMA)
            return {
                ok:false,
                document:initialDocument(),
                reason:"INVALID_SCHEMA"
            };
        if (Number(parsed.version) !== VERSION)
            return {
                ok:false,
                document:initialDocument(),
                reason:"UNSUPPORTED_VERSION"
            };
        const document = normalizeDocument(parsed, nowMs);
        return document
            ? {ok:true, document:document, reason:""}
            : {
                ok:false,
                document:initialDocument(),
                reason:"INVALID_DOCUMENT"
            };
    } catch (error) {
        return {
            ok:false,
            document:initialDocument(),
            reason:"INVALID_JSON"
        };
    }
}

function copyDocument(document, nowMs) {
    const normalized = normalizeDocument(document, nowMs);
    return normalized || initialDocument();
}

function append(document, sourceId, row, capturedAtMs) {
    const captured = positiveMillis(capturedAtMs);
    const snapshot = normalizeSnapshot(sourceId, row, captured);
    if (!snapshot)
        return {
            ok:false,
            changed:false,
            duplicate:false,
            document:copyDocument(document, captured),
            reason:"INVALID_SNAPSHOT",
            eventKey:"",
            count:0
        };

    const next = copyDocument(document, captured);
    const existing = next.events[snapshot.eventKey];
    const snapshots = existing && Array.isArray(existing.snapshots)
        ? existing.snapshots.slice() : [];

    if (snapshots.length > 0
            && snapshotFingerprint(snapshots[snapshots.length - 1])
               === snapshotFingerprint(snapshot)) {
        return {
            ok:true,
            changed:false,
            duplicate:true,
            document:next,
            reason:"DUPLICATE",
            eventKey:snapshot.eventKey,
            count:snapshots.length
        };
    }

    snapshots.push(snapshot);
    if (snapshots.length > MAX_SNAPSHOTS_PER_EVENT)
        snapshots.splice(0, snapshots.length - MAX_SNAPSHOTS_PER_EVENT);

    const first = snapshots[0];
    const last = snapshots[snapshots.length - 1];
    next.events[snapshot.eventKey] = {
        sourceId: snapshot.sourceId,
        sourceLabel: snapshot.sourceLabel,
        eventId: snapshot.eventId,
        eventKey: snapshot.eventKey,
        title: snapshot.title,
        typeLabel: snapshot.typeLabel,
        firstCapturedAtMs: first.capturedAtMs,
        lastCapturedAtMs: last.capturedAtMs,
        snapshots: snapshots
    };

    const normalized = normalizeDocument(next, captured) || initialDocument();
    normalized.revision = next.revision + 1;
    return {
        ok:true,
        changed:true,
        duplicate:false,
        document:normalized,
        reason:"",
        eventKey:snapshot.eventKey,
        count:normalized.events[snapshot.eventKey]
            ? normalized.events[snapshot.eventKey].snapshots.length : 0
    };
}

function snapshots(document, sourceId, eventId, nowMs) {
    const source = String(sourceId || "");
    const id = safeText(eventId, 180);
    if (!sourceKnown(source) || !id)
        return [];
    const normalized = copyDocument(document, nowMs);
    const event = normalized.events[source + "|" + id];
    return event && Array.isArray(event.snapshots)
        ? event.snapshots.slice() : [];
}

function snapshotCount(document, sourceId, eventId, nowMs) {
    return snapshots(document, sourceId, eventId, nowMs).length;
}

function latest(document, sourceId, eventId, nowMs) {
    const rows = snapshots(document, sourceId, eventId, nowMs);
    return rows.length > 0 ? rows[rows.length - 1] : null;
}

function eventCount(document, nowMs) {
    return Object.keys(copyDocument(document, nowMs).events).length;
}
