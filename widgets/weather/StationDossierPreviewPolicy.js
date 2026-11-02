.pragma library

// M22-A: volatile, read-only candidate for a future cross-domain dossier.
// No FileView, Process, Timer, network, writer, schema migration or archive API.
// This is not evidence that nearby records describe one incident.

var FORMAT = "post-apollo.weather-dossier-preview.v0";
var MAX_COMPANIONS = 6;
var MAX_OBSERVATIONS = 3;
var MAX_TIMELINE = 8;
var MAX_RELATIONSHIPS = 8;

function text(value, limit) {
    if (value === undefined || value === null
            || (typeof value !== "string" && typeof value !== "number"))
        return "";
    return String(value).replace(/[\x00-\x1f\x7f]/g, " ")
        .replace(/\s+/g, " ").trim().slice(0, limit || 120);
}

function sourceKnown(sourceId) {
    return ["gdacs", "usgs", "eonet", "firms"].indexOf(sourceId) >= 0;
}

function millis(value) {
    if (value === undefined || value === null || value === "")
        return -1;
    const number = Number(value);
    return isFinite(number) && number > 0 ? Math.floor(number) : -1;
}

function numberOrNull(value, lower, upper) {
    if (value === null || value === undefined || value === "")
        return null;
    const number = Number(value);
    return isFinite(number) && number >= lower && number <= upper
        ? number : null;
}

function distance(value, maximum) {
    return numberOrNull(value, 0, maximum);
}

function point(latitude, longitude) {
    const lat = numberOrNull(latitude, -90, 90);
    const lon = numberOrNull(longitude, -180, 180);
    return lat === null || lon === null
        ? null : {latitude:lat, longitude:lon};
}

function list(value) {
    return Array.isArray(value) ? value : [];
}

function selectedRecord(selected) {
    if (!selected || typeof selected !== "object")
        return null;
    const sourceId = text(selected.sourceId, 12);
    const eventId = text(selected.id, 180);
    if (!sourceKnown(sourceId) || !eventId)
        return null;
    return {
        sourceId:sourceId,
        eventId:eventId,
        sourceLabel:text(selected.sourceLabel, 48),
        title:text(selected.title, 180),
        typeLabel:text(selected.typeLabel, 80),
        sourceTimeMs:millis(selected.timeMs),
        point:point(selected.latitude, selected.longitude)
    };
}

function companionRecord(row, anchor) {
    if (!row || typeof row !== "object")
        return null;
    const sourceId = text(row.sourceId, 12);
    const eventId = text(row.id, 180);
    const at = point(row.latitude, row.longitude);
    const km = distance(row.distanceKm, 250);
    // Existing M13 proximity rule admits independent *other-source* records.
    if (!sourceKnown(sourceId) || sourceId === anchor.sourceId
            || !eventId || !at || !anchor.point || km === null)
        return null;
    return {
        sourceId:sourceId,
        eventId:eventId,
        sourceLabel:text(row.sourceLabel, 48),
        title:text(row.title, 180),
        typeLabel:text(row.typeLabel, 80),
        sourceTimeMs:millis(row.timeMs),
        point:at,
        distanceKm:km,
        relation:"CROSS_SOURCE_PROXIMITY_ONLY",
        sameIncidentClaim:false
    };
}

function operationalEvidence(radar, lightning, flood, anchor) {
    const out = [];
    if (!anchor.point)
        return out;
    if (radar && radar.available === true && radar.covered === true) {
        out.push({
            provider:"NOAA MRMS",
            kind:"RADAR_FRAME_COVERAGE",
            sourceTimeMs:millis(radar.timeMs),
            receivedAtMs:millis(radar.receivedAtMs),
            frameLabel:text(radar.frameLabel, 32),
            usingCache:radar.usingCache === true,
            interpretation:"LOADED_FRAME_COVERS_EVENT_POINT",
            limitation:"FRAME COVERAGE DOES NOT INTERPRET RADAR PIXELS",
            sameIncidentClaim:false
        });
    }
    if (lightning && lightning.available === true
            && lightning.covered === true) {
        out.push({
            provider:"NOAA NOWCOAST",
            kind:"LIGHTNING_FRAME_COVERAGE",
            sourceTimeMs:millis(lightning.timeMs),
            receivedAtMs:millis(lightning.receivedAtMs),
            windowMinutes:numberOrNull(lightning.windowMinutes, 0, 1440),
            usingCache:lightning.usingCache === true,
            interpretation:"LOADED_FRAME_COVERS_EVENT_POINT",
            limitation:"FRAME COVERAGE DOES NOT PROVE LIGHTNING AT EVENT",
            sameIncidentClaim:false
        });
    }
    const km = flood ? distance(flood.eventGaugeDistanceKm, 100) : null;
    const gaugeId = flood ? text(flood.gaugeId, 40) : "";
    if (flood && flood.relevant === true && flood.available === true
            && km !== null && gaugeId) {
        const reading = flood.latestObserved || {};
        const threshold = flood.thresholdContext || {};
        out.push({
            provider:"NOAA NWPS",
            kind:"FLOOD_GATED_GAUGE_OBSERVATION",
            gaugeId:gaugeId,
            gaugeName:text(flood.gaugeName, 160),
            eventGaugeDistanceKm:km,
            sourceTimeMs:millis(reading.timeMs),
            receivedAtMs:millis(flood.receivedAtMs),
            observedValue:numberOrNull(reading.value, 0, 100000000),
            observedUnits:text(reading.units, 32),
            observedCategory:text(flood.observedCategory, 48),
            thresholdSupported:threshold.supported === true,
            thresholdReason:text(threshold.reason, 120),
            interpretation:"EXPLICIT_FLOOD_EVENT_AND_NEARBY_GAUGE",
            limitation:"DISTANCE DOES NOT ESTABLISH SAME CATCHMENT OR INCIDENT",
            sameIncidentClaim:false
        });
    }
    return out.slice(0, MAX_OBSERVATIONS);
}

function timelineRecord(row) {
    if (!row || typeof row !== "object")
        return null;
    const sourceTimeMs = millis(row.timeMs);
    if (sourceTimeMs < 0)
        return null;
    const mode = text(row.freshnessMode, 32);
    return {
        provider:text(row.sourceLabel, 48),
        provenanceGroup:text(row.provenanceGroup, 48),
        kind:text(row.kind, 48),
        label:text(row.label, 180),
        sourceTimeMs:sourceTimeMs,
        receivedAtMs:millis(row.receivedAtMs),
        provenance:text(row.provenance, 120),
        freshnessMode:["AGE_ONLY","SNAPSHOT","PROVIDER_CONTRACT"].indexOf(mode) >= 0
            ? mode : "UNKNOWN",
        runtimeSourceId:text(row.runtimeSourceId, 48),
        // Timeline is chronology/context, not an independent provider record ID.
        sameIncidentClaim:false
    };
}

function relationshipRecord(row) {
    if (!row || typeof row !== "object")
        return null;
    const relationClass = text(row.relationClass, 48);
    if (!relationClass)
        return null;
    return {
        provider:text(row.sourceLabel, 48),
        evidenceClass:text(row.evidenceClass, 48),
        relationClass:relationClass,
        spatialLabel:text(row.spatialLabel, 120),
        temporalLabel:text(row.temporalLabel, 120),
        timeBand:text(row.timeBand, 40),
        timeDeltaMinutes:numberOrNull(row.timeDeltaMinutes, 0, 100000000),
        distanceKm:distance(row.distanceKm, 2000),
        reason:text(row.reason, 180),
        limitation:text(row.limitation, 180),
        sameIncidentClaim:false
    };
}

function boundedRecords(rows, limit, convert) {
    const result = [];
    const input = list(rows);
    for (let i = 0; i < input.length && result.length < limit; i++) {
        const record = convert(input[i]);
        if (record)
            result.push(record);
    }
    return result;
}

// Input objects are the *already-loaded* M13–M18 derived contexts.
// This function never stores, mutates, fetches or archives any provider data.
function preview(selected, companions, radar, lightning, flood,
                 timeline, relationships, assembledAtMs) {
    const anchor = selectedRecord(selected);
    const assembled = millis(assembledAtMs);
    if (!anchor)
        return {ok:false, reason:"INVALID_SOURCE_EVENT_IDENTITY", dossier:null};
    if (assembled < 0)
        return {ok:false, reason:"INVALID_ASSEMBLY_TIME", dossier:null};

    const nearby = boundedRecords(companions, MAX_COMPANIONS,
        function(row) { return companionRecord(row, anchor); });
    const observed = operationalEvidence(radar, lightning, flood, anchor);
    const chronological = boundedRecords(timeline, MAX_TIMELINE, timelineRecord);
    const related = boundedRecords(relationships, MAX_RELATIONSHIPS,
        relationshipRecord);

    return {
        ok:true,
        reason:"",
        dossier:{
            format:FORMAT,
            state:"VOLATILE_PREVIEW_ONLY",
            assembledAtMs:assembled,
            selectedEvent:anchor,
            nearbyEvents:nearby,
            operationalEvidence:observed,
            evidenceTimeline:chronological,
            relationships:related,
            counts:{
                nearby:nearby.length,
                operational:observed.length,
                timeline:chronological.length,
                relationships:related.length
            },
            limits:{
                nearby:MAX_COMPANIONS,
                operational:MAX_OBSERVATIONS,
                timeline:MAX_TIMELINE,
                relationships:MAX_RELATIONSHIPS
            },
            semantics:{
                sourceEventIdentity:"EXACT_PROVIDER_AND_PROVIDER_NATIVE_ID",
                relationshipMeaning:"CONTEXT_NOT_CAUSALITY",
                radarMeaning:"FRAME_COVERAGE_NOT_PIXEL_INTERPRETATION",
                gaugeMeaning:"PROXIMITY_NOT_CATCHMENT",
                temporalMeaning:"SOURCE_AND_RECEIVE_TIMES_SEPARATE",
                persistence:"NONE",
                rawFrameBytes:"NOT_INCLUDED",
                incidentMerge:false
            }
        }
    };
}
