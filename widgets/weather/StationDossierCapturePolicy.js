.pragma library

// M23: no-write admission contract for an M22 volatile dossier.
// Nothing in this file persists, schedules, fetches or requests a snapshot.
// Storage format, quota, retention and write owner remain unapproved.

var CANDIDATE_FORMAT = "post-apollo.weather-dossier-candidate.v0";
var PREVIEW_FORMAT = "post-apollo.weather-dossier-preview.v0";
var MAX_REVIEW_AGE_MS = 15 * 60 * 1000;
var MAX_CHARACTERS = 24000;
var LIMITS = {nearby:6, operational:3, timeline:8, relationships:8};

function fail(reason) {
    return {ok:false, reason:reason, candidate:null, characterCount:0};
}

function string(value, max) {
    if (typeof value !== "string")
        return "";
    return value.replace(/[\x00-\x1f\x7f]/g, " ")
        .replace(/\s+/g, " ").trim().slice(0, max);
}

function validTime(value, unknownAllowed) {
    if (typeof value !== "number" || !isFinite(value)
            || Math.floor(value) !== value)
        return false;
    return value > 0 || (unknownAllowed && value === -1);
}

function numeric(value, low, high) {
    return typeof value === "number" && isFinite(value)
        && value >= low && value <= high;
}

function validPoint(value) {
    return value === null
        || (value && typeof value === "object"
            && numeric(value.latitude, -90, 90)
            && numeric(value.longitude, -180, 180));
}

function sourceKnown(source) {
    return ["gdacs","usgs","eonet","firms"].indexOf(source) >= 0;
}

function exactArray(value, expected, maximum) {
    return Array.isArray(value) && value.length === expected
        && value.length <= maximum;
}

function copyPoint(value) {
    return value === null ? null
        : {latitude:value.latitude, longitude:value.longitude};
}

function validate(preview, nowMs) {
    if (!preview || preview.ok !== true || !preview.dossier)
        return fail("PREVIEW_UNAVAILABLE");
    const d = preview.dossier;
    if (d.format !== PREVIEW_FORMAT || d.state !== "VOLATILE_PREVIEW_ONLY")
        return fail("PREVIEW_FORMAT_UNSUPPORTED");
    if (!d.semantics || d.semantics.persistence !== "NONE"
            || d.semantics.incidentMerge !== false
            || d.semantics.sourceEventIdentity
               !== "EXACT_PROVIDER_AND_PROVIDER_NATIVE_ID")
        return fail("PREVIEW_SEMANTICS_UNTRUSTED");
    if (!validTime(nowMs, false) || !validTime(d.assembledAtMs, false)
            || nowMs < d.assembledAtMs
            || nowMs - d.assembledAtMs > MAX_REVIEW_AGE_MS)
        return fail("PREVIEW_TOO_OLD_OR_CLOCK_INVALID");

    const anchor = d.selectedEvent;
    if (!anchor || !sourceKnown(anchor.sourceId)
            || !string(anchor.eventId, 180)
            || !validPoint(anchor.point)
            || !validTime(anchor.sourceTimeMs, true))
        return fail("INVALID_PROVIDER_NATIVE_IDENTITY");

    if (!d.counts || !exactArray(d.nearbyEvents, d.counts.nearby, LIMITS.nearby)
            || !exactArray(d.operationalEvidence, d.counts.operational, LIMITS.operational)
            || !exactArray(d.evidenceTimeline, d.counts.timeline, LIMITS.timeline)
            || !exactArray(d.relationships, d.counts.relationships, LIMITS.relationships))
        return fail("EVIDENCE_BOUNDS_OR_COUNTS_INVALID");

    const nearby = [];
    const seen = [];
    for (let i = 0; i < d.nearbyEvents.length; i++) {
        const r = d.nearbyEvents[i];
        if (!r || !sourceKnown(r.sourceId)
                || r.sourceId === anchor.sourceId
                || !string(r.eventId, 180)
                || !validPoint(r.point) || r.point === null
                || !numeric(r.distanceKm, 0, 250)
                || !validTime(r.sourceTimeMs, true)
                || r.relation !== "CROSS_SOURCE_PROXIMITY_ONLY"
                || r.sameIncidentClaim !== false)
            return fail("NEARBY_PROVENANCE_INVALID");
        const key = r.sourceId + "|" + r.eventId;
        if (seen.indexOf(key) >= 0)
            return fail("NEARBY_IDENTITY_DUPLICATED");
        seen.push(key);
        nearby.push({
            sourceId:r.sourceId, eventId:string(r.eventId, 180),
            sourceLabel:string(r.sourceLabel, 48),
            title:string(r.title, 180), typeLabel:string(r.typeLabel, 80),
            sourceTimeMs:r.sourceTimeMs, point:copyPoint(r.point),
            distanceKm:r.distanceKm,
            relation:r.relation, sameIncidentClaim:false
        });
    }

    const expectedOperational = {
        RADAR_FRAME_COVERAGE:"NOAA MRMS",
        LIGHTNING_FRAME_COVERAGE:"NOAA NOWCOAST",
        FLOOD_GATED_GAUGE_OBSERVATION:"NOAA NWPS"
    };
    const operational = [];
    const seenKinds = [];
    for (let i = 0; i < d.operationalEvidence.length; i++) {
        const r = d.operationalEvidence[i];
        if (!r || !expectedOperational[r.kind]
                || r.provider !== expectedOperational[r.kind]
                || seenKinds.indexOf(r.kind) >= 0
                || r.sameIncidentClaim !== false
                || !validTime(r.sourceTimeMs, true)
                || !validTime(r.receivedAtMs, true)
                || !string(r.limitation, 180))
            return fail("OPERATIONAL_PROVENANCE_INVALID");
        if (r.kind === "FLOOD_GATED_GAUGE_OBSERVATION"
                && (!string(r.gaugeId, 40)
                    || !numeric(r.eventGaugeDistanceKm, 0, 100)))
            return fail("GAUGE_IDENTITY_OR_DISTANCE_INVALID");
        seenKinds.push(r.kind);
        operational.push({
            provider:r.provider, kind:r.kind,
            sourceTimeMs:r.sourceTimeMs, receivedAtMs:r.receivedAtMs,
            frameLabel:string(r.frameLabel, 32),
            windowMinutes:numeric(r.windowMinutes, 0, 1440) ? r.windowMinutes : null,
            usingCache:r.usingCache === true,
            gaugeId:string(r.gaugeId, 40),
            gaugeName:string(r.gaugeName, 160),
            eventGaugeDistanceKm:numeric(r.eventGaugeDistanceKm, 0, 100)
                ? r.eventGaugeDistanceKm : null,
            observedValue:numeric(r.observedValue, 0, 100000000)
                ? r.observedValue : null,
            observedUnits:string(r.observedUnits, 32),
            observedCategory:string(r.observedCategory, 48),
            thresholdSupported:r.thresholdSupported === true,
            thresholdReason:string(r.thresholdReason, 120),
            interpretation:string(r.interpretation, 120),
            limitation:string(r.limitation, 180),
            sameIncidentClaim:false
        });
    }

    const timeline = [];
    for (let i = 0; i < d.evidenceTimeline.length; i++) {
        const r = d.evidenceTimeline[i];
        if (!r || !validTime(r.sourceTimeMs, false)
                || !validTime(r.receivedAtMs, true)
                || !string(r.provider, 48)
                || !string(r.provenance, 120)
                || ["AGE_ONLY","SNAPSHOT","PROVIDER_CONTRACT","UNKNOWN"]
                   .indexOf(r.freshnessMode) < 0
                || r.sameIncidentClaim !== false)
            return fail("TIMELINE_PROVENANCE_INVALID");
        timeline.push({
            provider:string(r.provider, 48),
            provenanceGroup:string(r.provenanceGroup, 48),
            kind:string(r.kind, 48),
            label:string(r.label, 180),
            sourceTimeMs:r.sourceTimeMs,
            receivedAtMs:r.receivedAtMs,
            provenance:string(r.provenance, 120),
            freshnessMode:r.freshnessMode,
            runtimeSourceId:string(r.runtimeSourceId, 48),
            sameIncidentClaim:false
        });
    }

    const relationships = [];
    for (let i = 0; i < d.relationships.length; i++) {
        const r = d.relationships[i];
        if (!r || !string(r.provider, 48)
                || !string(r.relationClass, 48)
                || !string(r.reason, 180)
                || !string(r.limitation, 180)
                || r.sameIncidentClaim !== false
                || (r.distanceKm !== null
                    && !numeric(r.distanceKm, 0, 2000))
                || (r.timeDeltaMinutes !== null
                    && !numeric(r.timeDeltaMinutes, 0, 100000000)))
            return fail("RELATIONSHIP_LIMITATION_INVALID");
        relationships.push({
            provider:string(r.provider, 48),
            evidenceClass:string(r.evidenceClass, 48),
            relationClass:string(r.relationClass, 48),
            spatialLabel:string(r.spatialLabel, 120),
            temporalLabel:string(r.temporalLabel, 120),
            timeBand:string(r.timeBand, 40),
            timeDeltaMinutes:r.timeDeltaMinutes,
            distanceKm:r.distanceKm,
            reason:string(r.reason, 180),
            limitation:string(r.limitation, 180),
            sameIncidentClaim:false
        });
    }

    const candidate = {
        format:CANDIDATE_FORMAT,
        state:"UNSAVED_REVIEW_ONLY",
        selectedEvent:{
            sourceId:anchor.sourceId,
            eventId:string(anchor.eventId, 180),
            sourceLabel:string(anchor.sourceLabel, 48),
            title:string(anchor.title, 180),
            typeLabel:string(anchor.typeLabel, 80),
            sourceTimeMs:anchor.sourceTimeMs,
            point:copyPoint(anchor.point)
        },
        assembledAtMs:d.assembledAtMs,
        reviewedAtMs:nowMs,
        nearbyEvents:nearby,
        operationalEvidence:operational,
        evidenceTimeline:timeline,
        relationships:relationships,
        counts:{
            nearby:nearby.length, operational:operational.length,
            timeline:timeline.length, relationships:relationships.length
        },
        semantics:{
            incidentMerge:false,
            persistence:"NONE",
            relationshipMeaning:"CONTEXT_NOT_CAUSALITY",
            radarMeaning:"FRAME_COVERAGE_NOT_PIXEL_INTERPRETATION",
            gaugeMeaning:"PROXIMITY_NOT_CATCHMENT",
            rawFrameBytes:"NOT_INCLUDED"
        }
    };
    const characterCount = JSON.stringify(candidate).length;
    if (characterCount > MAX_CHARACTERS)
        return fail("REVIEW_SIZE_LIMIT_EXCEEDED");
    return {
        ok:true, reason:"REVIEWABLE_NOT_SAVED",
        candidate:candidate, characterCount:characterCount
    };
}

// Read-only status for the current MAP inspector. No file or process access.
function review(preview, nowMs) {
    const result = validate(preview, nowMs);
    return {
        ready:result.ok,
        reason:result.reason,
        characterCount:result.characterCount,
        saved:false
    };
}

// A future explicit operator action would call this *before* a separately
// authorized storage implementation. This function still never writes.
function stage(preview, nowMs, explicitRequest) {
    if (explicitRequest !== true)
        return fail("EXPLICIT_OPERATOR_REQUEST_REQUIRED");
    return validate(preview, nowMs);
}
