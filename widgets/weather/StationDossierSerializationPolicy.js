.pragma library

// M24-A // PROVISIONAL, MEMORY-ONLY dossier serialization probe.
// This policy has no FileView, Process, Timer, path, capture action or writer.
// Its v0 format is NOT a durable storage schema or a retention decision.

var FORMAT = "post-apollo.weather-dossier-serialization-probe.v0";
var VERSION = 0;
var STATE = "UNSAVED_TRANSPORT_PROBE_ONLY";
var CANDIDATE_FORMAT = "post-apollo.weather-dossier-candidate.v0";
var MAX_CANDIDATE_CHARS = 24000;
var MAX_ENVELOPE_CHARS = 27000;

function refuse(reason) {
    return {ok:false, reason:reason, text:"", envelope:null, characters:0};
}
function record(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
}
function exactKeys(value, names) {
    if (!record(value))
        return false;
    const actual = Object.keys(value);
    return actual.length === names.length
        && names.every(function(name) {
            return Object.prototype.hasOwnProperty.call(value, name);
        });
}
function t(value, max, required) {
    return typeof value === "string" && value.length <= max
        && (!required || value.length > 0)
        && !/[\x00-\x1f\x7f]/.test(value);
}
function validMs(value, allowUnknown) {
    return typeof value === "number" && isFinite(value)
        && Math.floor(value) === value
        && (value > 0 || (allowUnknown && value === -1));
}
function n(value, a, b) {
    return typeof value === "number" && isFinite(value)
        && value >= a && value <= b;
}
function nullableNumber(value, a, b) {
    return value === null || n(value, a, b);
}
function point(value, optional) {
    if (value === null)
        return optional;
    return exactKeys(value, ["latitude","longitude"])
        && n(value.latitude, -90, 90)
        && n(value.longitude, -180, 180);
}
function sourceKnown(source) {
    return ["gdacs","usgs","eonet","firms"].indexOf(source) >= 0;
}
function arrayCount(rows, count, maximum) {
    return Array.isArray(rows)
        && Number.isInteger(count)
        && count >= 0 && count <= maximum
        && rows.length === count;
}
function validSelected(r) {
    return exactKeys(r, [
        "sourceId","eventId","sourceLabel","title","typeLabel",
        "sourceTimeMs","point"
    ])
        && sourceKnown(r.sourceId)
        && t(r.eventId, 180, true)
        && t(r.sourceLabel, 48, false)
        && t(r.title, 180, false)
        && t(r.typeLabel, 80, false)
        && validMs(r.sourceTimeMs, true)
        && point(r.point, true);
}
function validNearby(r, sourceId) {
    return exactKeys(r, [
        "sourceId","eventId","sourceLabel","title","typeLabel",
        "sourceTimeMs","point","distanceKm","relation","sameIncidentClaim"
    ])
        && sourceKnown(r.sourceId) && r.sourceId !== sourceId
        && t(r.eventId, 180, true)
        && t(r.sourceLabel, 48, false)
        && t(r.title, 180, false)
        && t(r.typeLabel, 80, false)
        && validMs(r.sourceTimeMs, true)
        && point(r.point, false)
        && n(r.distanceKm, 0, 250)
        && r.relation === "CROSS_SOURCE_PROXIMITY_ONLY"
        && r.sameIncidentClaim === false;
}
function validOperational(r) {
    if (!exactKeys(r, [
        "provider","kind","sourceTimeMs","receivedAtMs","frameLabel",
        "windowMinutes","usingCache","gaugeId","gaugeName",
        "eventGaugeDistanceKm","observedValue","observedUnits",
        "observedCategory","thresholdSupported","thresholdReason",
        "interpretation","limitation","sameIncidentClaim"
    ]))
        return false;
    const providers = {
        RADAR_FRAME_COVERAGE:"NOAA MRMS",
        LIGHTNING_FRAME_COVERAGE:"NOAA NOWCOAST",
        FLOOD_GATED_GAUGE_OBSERVATION:"NOAA NWPS"
    };
    const interpretation = {
        RADAR_FRAME_COVERAGE:"LOADED_FRAME_COVERS_EVENT_POINT",
        LIGHTNING_FRAME_COVERAGE:"LOADED_FRAME_COVERS_EVENT_POINT",
        FLOOD_GATED_GAUGE_OBSERVATION:"EXPLICIT_FLOOD_EVENT_AND_NEARBY_GAUGE"
    };
    const limitation = {
        RADAR_FRAME_COVERAGE:"FRAME COVERAGE DOES NOT INTERPRET RADAR PIXELS",
        LIGHTNING_FRAME_COVERAGE:"FRAME COVERAGE DOES NOT PROVE LIGHTNING AT EVENT",
        FLOOD_GATED_GAUGE_OBSERVATION:"DISTANCE DOES NOT ESTABLISH SAME CATCHMENT OR INCIDENT"
    };
    return Object.prototype.hasOwnProperty.call(providers, r.kind)
        && r.provider === providers[r.kind]
        && r.interpretation === interpretation[r.kind]
        && r.limitation === limitation[r.kind]
        && validMs(r.sourceTimeMs, true) && validMs(r.receivedAtMs, true)
        && t(r.frameLabel, 32, false)
        && nullableNumber(r.windowMinutes, 0, 1440)
        && typeof r.usingCache === "boolean"
        && t(r.gaugeId, 40, r.kind === "FLOOD_GATED_GAUGE_OBSERVATION")
        && t(r.gaugeName, 160, false)
        && nullableNumber(r.eventGaugeDistanceKm, 0, 100)
        && (r.kind !== "FLOOD_GATED_GAUGE_OBSERVATION"
            || r.eventGaugeDistanceKm !== null)
        && nullableNumber(r.observedValue, 0, 100000000)
        && t(r.observedUnits, 32, false)
        && t(r.observedCategory, 48, false)
        && typeof r.thresholdSupported === "boolean"
        && t(r.thresholdReason, 120, false)
        && r.sameIncidentClaim === false;
}
function validTimeline(r) {
    return exactKeys(r, [
        "provider","provenanceGroup","kind","label","sourceTimeMs",
        "receivedAtMs","provenance","freshnessMode","runtimeSourceId",
        "sameIncidentClaim"
    ])
        && t(r.provider, 48, true)
        && t(r.provenanceGroup, 48, false)
        && t(r.kind, 48, false)
        && t(r.label, 180, false)
        && validMs(r.sourceTimeMs, false)
        && validMs(r.receivedAtMs, true)
        && t(r.provenance, 120, true)
        && ["AGE_ONLY","SNAPSHOT","PROVIDER_CONTRACT","UNKNOWN"]
            .indexOf(r.freshnessMode) >= 0
        && t(r.runtimeSourceId, 48, false)
        && r.sameIncidentClaim === false;
}
function validRelationship(r) {
    return exactKeys(r, [
        "provider","evidenceClass","relationClass","spatialLabel",
        "temporalLabel","timeBand","timeDeltaMinutes","distanceKm",
        "reason","limitation","sameIncidentClaim"
    ])
        && t(r.provider, 48, true)
        && t(r.evidenceClass, 48, false)
        && t(r.relationClass, 48, true)
        && t(r.spatialLabel, 120, false)
        && t(r.temporalLabel, 120, false)
        && t(r.timeBand, 40, false)
        && nullableNumber(r.timeDeltaMinutes, 0, 100000000)
        && nullableNumber(r.distanceKm, 0, 2000)
        && t(r.reason, 180, true)
        && t(r.limitation, 180, true)
        && r.sameIncidentClaim === false;
}
function validCandidate(c) {
    if (!exactKeys(c, [
        "format","state","selectedEvent","assembledAtMs","reviewedAtMs",
        "nearbyEvents","operationalEvidence","evidenceTimeline",
        "relationships","counts","semantics"
    ]) || c.format !== CANDIDATE_FORMAT
        || c.state !== "UNSAVED_REVIEW_ONLY"
        || !validSelected(c.selectedEvent)
        || !validMs(c.assembledAtMs, false)
        || !validMs(c.reviewedAtMs, false)
        || c.reviewedAtMs < c.assembledAtMs
        || !exactKeys(c.counts, ["nearby","operational","timeline","relationships"])
        || !arrayCount(c.nearbyEvents, c.counts.nearby, 6)
        || !arrayCount(c.operationalEvidence, c.counts.operational, 3)
        || !arrayCount(c.evidenceTimeline, c.counts.timeline, 8)
        || !arrayCount(c.relationships, c.counts.relationships, 8)
        || !exactKeys(c.semantics, [
            "incidentMerge","persistence","relationshipMeaning","radarMeaning",
            "gaugeMeaning","rawFrameBytes"
        ])
        || c.semantics.incidentMerge !== false
        || c.semantics.persistence !== "NONE"
        || c.semantics.relationshipMeaning !== "CONTEXT_NOT_CAUSALITY"
        || c.semantics.radarMeaning !== "FRAME_COVERAGE_NOT_PIXEL_INTERPRETATION"
        || c.semantics.gaugeMeaning !== "PROXIMITY_NOT_CATCHMENT"
        || c.semantics.rawFrameBytes !== "NOT_INCLUDED")
        return false;

    const seenEvents = [];
    for (let i = 0; i < c.nearbyEvents.length; i++) {
        const r = c.nearbyEvents[i];
        if (!validNearby(r, c.selectedEvent.sourceId))
            return false;
        const key = r.sourceId + "|" + r.eventId;
        if (seenEvents.indexOf(key) >= 0)
            return false;
        seenEvents.push(key);
    }
    const seenKinds = [];
    for (let i = 0; i < c.operationalEvidence.length; i++) {
        const r = c.operationalEvidence[i];
        if (!validOperational(r) || seenKinds.indexOf(r.kind) >= 0)
            return false;
        seenKinds.push(r.kind);
    }
    return c.evidenceTimeline.every(validTimeline)
        && c.relationships.every(validRelationship);
}
function validEnvelope(envelope) {
    return exactKeys(envelope, ["format","version","state","candidate"])
        && envelope.format === FORMAT
        && envelope.version === VERSION
        && envelope.state === STATE
        && validCandidate(envelope.candidate);
}
// This is an in-memory *transport* string, not a file write.
function serialize(staged) {
    if (!staged || staged.ok !== true
            || staged.reason !== "REVIEWABLE_NOT_SAVED"
            || !validCandidate(staged.candidate))
        return refuse("UNTRUSTED_OR_UNSTAGED_CANDIDATE");
    let candidateText;
    try { candidateText = JSON.stringify(staged.candidate); }
    catch (error) { return refuse("CANDIDATE_SERIALIZATION_FAILED"); }
    if (candidateText.length > MAX_CANDIDATE_CHARS)
        return refuse("CANDIDATE_SIZE_LIMIT_EXCEEDED");

    // JSON roundtrip drops prototypes/links and rejects unrecognized fields.
    const envelope = {
        format:FORMAT, version:VERSION, state:STATE,
        candidate:JSON.parse(candidateText)
    };
    const raw = JSON.stringify(envelope);
    if (raw.length > MAX_ENVELOPE_CHARS)
        return refuse("ENVELOPE_SIZE_LIMIT_EXCEEDED");
    return {
        ok:true, reason:"SERIALIZED_IN_MEMORY_ONLY",
        text:raw, envelope:envelope, characters:raw.length
    };
}
// Pure parse probe; no migration, repair, deletion, fallback, or readback claim.
function inspect(raw) {
    if (typeof raw !== "string" || raw.length === 0
            || raw.length > MAX_ENVELOPE_CHARS)
        return refuse("INPUT_SIZE_OR_TYPE_INVALID");
    let parsed;
    try { parsed = JSON.parse(raw); }
    catch (error) { return refuse("INVALID_JSON"); }
    if (!record(parsed) || parsed.format !== FORMAT)
        return refuse("UNKNOWN_FORMAT");
    if (parsed.version !== VERSION)
        return refuse("UNSUPPORTED_VERSION");
    if (!validEnvelope(parsed))
        return refuse("INVALID_ENVELOPE_OR_EVIDENCE");
    if (JSON.stringify(parsed.candidate).length > MAX_CANDIDATE_CHARS)
        return refuse("CANDIDATE_SIZE_LIMIT_EXCEEDED");
    return {
        ok:true, reason:"PARSED_IN_MEMORY_ONLY",
        text:"", envelope:parsed, characters:raw.length
    };
}
function probe(staged) {
    const encoded = serialize(staged);
    if (!encoded.ok)
        return {ok:false, reason:encoded.reason, equal:false, characters:0};
    const decoded = inspect(encoded.text);
    return {
        ok:decoded.ok,
        reason:decoded.reason,
        equal:decoded.ok
            && JSON.stringify(decoded.envelope) === encoded.text,
        characters:encoded.characters
    };
}
