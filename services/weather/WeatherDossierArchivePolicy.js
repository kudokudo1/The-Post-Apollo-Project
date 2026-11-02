.pragma library

// M25: persistent dossier archive document policy, with a strict no-prune
// safety capacity. This is independent from the source-native M19 archive.
// All writes are owned by WeatherDossierArchiveStore.qml only.

var SCHEMA = "post-apollo.weather-dossier-archive.v1";
var VERSION = 1;
// Safety ceilings pending final operator retention decision. Never auto-prune.
var MAX_ENTRIES = 64;
var MAX_DOCUMENT_CHARS = 1800000;

function empty() {
    return {schema:SCHEMA, version:VERSION, revision:0, entries:[]};
}
function fail(reason) {
    return {ok:false, reason:reason, document:null, count:0};
}
function validInt(value, minimum) {
    return typeof value === "number" && Number.isSafeInteger(value)
        && value >= minimum;
}
function record(value) {
    return value !== null && typeof value === "object"
        && !Array.isArray(value);
}
function exactKeys(value, keys) {
    return record(value)
        && Object.keys(value).length === keys.length
        && keys.every(function(key) {
            return Object.prototype.hasOwnProperty.call(value, key);
        });
}
function sourceKnown(source) {
    return ["gdacs","usgs","eonet","firms"].indexOf(source) >= 0;
}

// 'codec' is the imported M24 policy in the QML caller, or the pure JS
// test harness. It must supply strict inspect() and serialize().
function validateDocument(value, codec) {
    if (!codec || typeof codec.inspect !== "function"
            || !exactKeys(value, ["schema","version","revision","entries"])
            || value.schema !== SCHEMA || value.version !== VERSION
            || !validInt(value.revision, 0)
            || !Array.isArray(value.entries)
            || value.entries.length > MAX_ENTRIES)
        return fail("INVALID_DOCUMENT_OR_VERSION");

    const entries = [];
    let lastSequence = 0;
    for (let i = 0; i < value.entries.length; i++) {
        const r = value.entries[i];
        if (!exactKeys(r, [
            "sequence","sourceId","eventId","capturedAtMs","transport"
        ]) || !validInt(r.sequence, 1)
            || r.sequence <= lastSequence
            || !sourceKnown(r.sourceId)
            || typeof r.eventId !== "string" || !r.eventId
            || r.eventId.length > 180
            || !validInt(r.capturedAtMs, 1)
            || typeof r.transport !== "string"
            || r.transport.length > 27000)
            return fail("INVALID_ENTRY_OR_ORDER");

        const parsed = codec.inspect(r.transport);
        if (!parsed.ok || !parsed.envelope || !parsed.envelope.candidate)
            return fail("INVALID_NESTED_DOSSIER");
        const candidate = parsed.envelope.candidate;
        if (candidate.selectedEvent.sourceId !== r.sourceId
                || candidate.selectedEvent.eventId !== r.eventId
                || candidate.reviewedAtMs > r.capturedAtMs)
            return fail("ENTRY_PROVENANCE_MISMATCH");
        entries.push({
            sequence:r.sequence,
            sourceId:r.sourceId,
            eventId:r.eventId,
            capturedAtMs:r.capturedAtMs,
            transport:r.transport
        });
        lastSequence = r.sequence;
    }
    if (value.revision < lastSequence)
        return fail("REVISION_BEHIND_ENTRIES");
    const document = {
        schema:SCHEMA, version:VERSION,
        revision:value.revision, entries:entries
    };
    if (JSON.stringify(document).length > MAX_DOCUMENT_CHARS)
        return fail("DOCUMENT_CAPACITY_REACHED");
    return {
        ok:true, reason:"", document:document, count:entries.length
    };
}

function parse(raw, codec) {
    if (typeof raw !== "string" || raw.length > MAX_DOCUMENT_CHARS)
        return fail("INPUT_SIZE_OR_TYPE_INVALID");
    if (!raw.trim())
        return {ok:true,reason:"EMPTY",document:empty(),count:0};
    let value;
    try { value=JSON.parse(raw); }
    catch (error) { return fail("INVALID_JSON"); }
    if (!record(value) || value.schema !== SCHEMA)
        return fail("INVALID_SCHEMA");
    if (value.version !== VERSION)
        return fail("UNSUPPORTED_VERSION");
    return validateDocument(value, codec);
}

// Input must have passed M23 stage, M24 codec, and existing document
// validation. An invalid document is never replaced with empty state.
function append(current, staged, capturedAtMs, codec) {
    if (!validInt(capturedAtMs, 1))
        return fail("INVALID_CAPTURE_TIME");
    const old = validateDocument(current, codec);
    if (!old.ok)
        return old;
    if (old.count >= MAX_ENTRIES)
        return fail("ARCHIVE_AT_CAPACITY");
    if (!codec || typeof codec.serialize !== "function")
        return fail("CODEC_UNAVAILABLE");
    const packet = codec.serialize(staged);
    if (!packet.ok)
        return fail(packet.reason || "DOSSIER_REJECTED");
    const candidate = packet.envelope.candidate;
    if (capturedAtMs < candidate.reviewedAtMs)
        return fail("CAPTURE_BEFORE_REVIEW");
    if (old.document.revision >= Number.MAX_SAFE_INTEGER)
        return fail("REVISION_OVERFLOW");
    const nextRevision = old.document.revision + 1;
    const entries = old.document.entries.concat([{
        sequence:nextRevision,
        sourceId:candidate.selectedEvent.sourceId,
        eventId:candidate.selectedEvent.eventId,
        capturedAtMs:capturedAtMs,
        transport:packet.text
    }]);
    const next = {
        schema:SCHEMA, version:VERSION,
        revision:nextRevision, entries:entries
    };
    const check = validateDocument(next, codec);
    if (!check.ok)
        return check;
    return {
        ok:true,reason:"QUEUED",document:check.document,
        count:check.count,sequence:nextRevision
    };
}
function latest(document, sourceId, eventId, codec) {
    const valid = validateDocument(document, codec);
    if (!valid.ok || !sourceKnown(sourceId)
            || typeof eventId !== "string" || !eventId)
        return null;
    const rows = valid.document.entries;
    for (let i=rows.length-1; i>=0; i--) {
        if (rows[i].sourceId === sourceId && rows[i].eventId === eventId)
            return rows[i];
    }
    return null;
}
function countForEvent(document, sourceId, eventId, codec) {
    const valid = validateDocument(document, codec);
    if (!valid.ok || !sourceKnown(sourceId)
            || typeof eventId !== "string" || !eventId)
        return 0;
    return valid.document.entries.filter(function(row) {
        return row.sourceId === sourceId && row.eventId === eventId;
    }).length;
}
