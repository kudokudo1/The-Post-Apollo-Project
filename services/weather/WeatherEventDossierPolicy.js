.pragma library

var VERSION = 1;
var MAX_DOSSIERS = 128;
var MAX_RELATIONS = 16;
var DUPLICATE_WINDOW_MS = 300000;

function text(value, limit) {
    const clean = String(value === undefined || value === null ? "" : value)
        .replace(/[\u0000-\u001f\u007f]/g, " ")
        .replace(/\s+/g, " ")
        .trim();
    return clean.slice(0, Math.max(0, Number(limit) || 0));
}

function finite(value, fallback) {
    if (value === undefined || value === null || value === "")
        return fallback;
    const number = Number(value);
    return isFinite(number) ? number : fallback;
}

function validPoint(latValue, lonValue) {
    const lat = finite(latValue, NaN);
    const lon = finite(lonValue, NaN);
    return isFinite(lat) && isFinite(lon)
        && Math.abs(lat) <= 90 && Math.abs(lon) <= 180;
}

function initialDocument() {
    return {
        version: VERSION,
        revision: 0,
        dossiers: []
    };
}

function sanitizeAnchor(raw) {
    if (!raw || !validPoint(raw.latitude, raw.longitude))
        return null;
    const source = text(raw.source, 48);
    const id = text(raw.id, 120);
    if (!source)
        return null;
    return {
        source: source,
        id: id,
        title: text(raw.title, 180) || "UNTITLED EVENT",
        hazard: text(raw.hazard, 32) || "unknown",
        latitude: finite(raw.latitude, 0),
        longitude: finite(raw.longitude, 0),
        observedMs: Math.max(-1, Math.floor(finite(raw.observedMs, -1)))
    };
}

function sanitizeRelation(raw) {
    if (!raw || !validPoint(raw.latitude, raw.longitude))
        return null;
    const source = text(raw.source, 48);
    if (!source)
        return null;
    return {
        source: source,
        id: text(raw.id, 120),
        title: text(raw.title, 180) || "UNTITLED RECORD",
        hazard: text(raw.hazard, 32) || "unknown",
        latitude: finite(raw.latitude, 0),
        longitude: finite(raw.longitude, 0),
        distanceKm: Math.max(0, finite(raw.distanceKm, 0)),
        deltaHours: finite(raw.deltaHours, -1),
        relationKind: text(raw.relationKind, 32),
        mentionOnly: raw.mentionOnly === true,
        semantics: text(raw.semantics, 180)
    };
}

function sanitizeDossier(raw) {
    if (!raw)
        return null;
    const savedAtMs = Math.floor(finite(raw.savedAtMs, -1));
    const anchor = sanitizeAnchor(raw.anchor);
    if (savedAtMs <= 0 || !anchor)
        return null;
    const relationsRaw = Array.isArray(raw.relations) ? raw.relations : [];
    const relations = [];
    for (let i = 0; i < relationsRaw.length && relations.length < MAX_RELATIONS; i++) {
        const relation = sanitizeRelation(relationsRaw[i]);
        if (relation)
            relations.push(relation);
    }
    return {
        id: text(raw.id, 220)
            || (String(savedAtMs) + "|" + anchor.source + "|" + anchor.id),
        savedAtMs: savedAtMs,
        anchor: anchor,
        relations: relations
    };
}

function parse(raw) {
    const source = String(raw || "").trim();
    if (!source)
        return {ok:true, empty:true, document:initialDocument()};
    let root;
    try {
        root = JSON.parse(source);
    } catch (error) {
        return {ok:false, reason:"INVALID_JSON", document:initialDocument()};
    }
    if (!root || Number(root.version) !== VERSION)
        return {ok:false, reason:"UNSUPPORTED_VERSION", document:initialDocument()};

    const input = Array.isArray(root.dossiers) ? root.dossiers : [];
    const dossiers = [];
    for (let i = 0; i < input.length && dossiers.length < MAX_DOSSIERS; i++) {
        const dossier = sanitizeDossier(input[i]);
        if (dossier)
            dossiers.push(dossier);
    }
    dossiers.sort(function(a, b) { return b.savedAtMs - a.savedAtMs; });
    return {
        ok: true,
        empty: dossiers.length === 0,
        document: {
            version: VERSION,
            revision: Math.max(0, Math.floor(finite(root.revision, 0))),
            dossiers: dossiers
        }
    };
}

function sameAnchor(a, b) {
    if (!a || !b)
        return false;
    return String(a.source || "") === String(b.source || "")
        && String(a.id || "") === String(b.id || "")
        && Math.abs(Number(a.latitude) - Number(b.latitude)) < 1e-6
        && Math.abs(Number(a.longitude) - Number(b.longitude)) < 1e-6;
}

function addDossier(document, anchorRaw, relationRows, nowValue) {
    const parsed = parse(JSON.stringify(document || initialDocument()));
    if (!parsed.ok)
        return {ok:false, reason:parsed.reason, document:parsed.document};

    const anchor = sanitizeAnchor(anchorRaw);
    const savedAtMs = Math.floor(finite(nowValue, -1));
    if (!anchor)
        return {ok:false, reason:"INVALID_ANCHOR", document:parsed.document};
    if (savedAtMs <= 0)
        return {ok:false, reason:"INVALID_TIME", document:parsed.document};

    const current = parsed.document.dossiers;
    if (current.length > 0
            && sameAnchor(current[0].anchor, anchor)
            && savedAtMs - current[0].savedAtMs >= 0
            && savedAtMs - current[0].savedAtMs < DUPLICATE_WINDOW_MS) {
        return {ok:false, reason:"RECENT_DUPLICATE", document:parsed.document};
    }

    const inputRelations = Array.isArray(relationRows) ? relationRows : [];
    const relations = [];
    for (let i = 0; i < inputRelations.length
            && relations.length < MAX_RELATIONS; i++) {
        const relation = sanitizeRelation(inputRelations[i]);
        if (relation)
            relations.push(relation);
    }

    const nextRevision = parsed.document.revision + 1;
    const id = String(savedAtMs) + "|" + anchor.source + "|" + anchor.id
             + "|r" + nextRevision;
    const dossier = {
        id: id,
        savedAtMs: savedAtMs,
        anchor: anchor,
        relations: relations
    };
    const dossiers = [dossier].concat(current).slice(0, MAX_DOSSIERS);
    return {
        ok: true,
        reason: "",
        dossier: dossier,
        document: {
            version: VERSION,
            revision: nextRevision,
            dossiers: dossiers
        }
    };
}

function clearDocument(document) {
    const parsed = parse(JSON.stringify(document || initialDocument()));
    if (!parsed.ok)
        return {ok:false, reason:parsed.reason, document:parsed.document};
    return {
        ok: true,
        reason: "",
        document: {
            version: VERSION,
            revision: parsed.document.revision + 1,
            dossiers: []
        }
    };
}

function recent(document, limit) {
    const parsed = parse(JSON.stringify(document || initialDocument()));
    if (!parsed.ok)
        return [];
    const requested = Number(limit);
    const size = isFinite(requested) && requested > 0
               ? Math.min(MAX_DOSSIERS, Math.floor(requested)) : 5;
    return parsed.document.dossiers.slice(0, size);
}

function summary(document) {
    const parsed = parse(JSON.stringify(document || initialDocument()));
    if (!parsed.ok)
        return {count:0, revision:0, sources:0, latestMs:-1};
    const sourceSet = {};
    let latestMs = -1;
    for (let i = 0; i < parsed.document.dossiers.length; i++) {
        const row = parsed.document.dossiers[i];
        sourceSet[row.anchor.source] = true;
        latestMs = Math.max(latestMs, row.savedAtMs);
    }
    return {
        count: parsed.document.dossiers.length,
        revision: parsed.document.revision,
        sources: Object.keys(sourceSet).length,
        latestMs: latestMs
    };
}

function formatSavedAt(value) {
    const ms = Math.floor(finite(value, -1));
    if (ms <= 0)
        return "--";
    const date = new Date(ms);
    if (isNaN(date.getTime()))
        return "--";
    return date.toISOString().slice(0, 16).replace("T", " ") + " UTC";
}
