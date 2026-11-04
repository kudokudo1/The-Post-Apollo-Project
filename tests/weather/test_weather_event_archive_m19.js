#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = rel => fs.readFileSync(path.join(root, rel), "utf8");

const ctx = {
    Date, Math, Number, String, Array, Object, JSON, RegExp,
    isFinite, isNaN
};
vm.runInNewContext(
    read("services/weather/WeatherEventArchivePolicy.js")
        .replace(/^\.pragma library\s*/m, ""),
    ctx,
    {filename:"services/weather/WeatherEventArchivePolicy.js"}
);

assert.equal(ctx.SCHEMA, "post-apollo.weather-event-archive.v1");
assert.equal(ctx.VERSION, 1);
assert.equal(ctx.MAX_EVENTS, 256);
assert.equal(ctx.MAX_SNAPSHOTS_PER_EVENT, 32);
assert.equal(ctx.MAX_AGE_MS, 180 * 24 * 60 * 60 * 1000);
assert.deepEqual(
    Array.from(ctx.knownSourceIds()),
    ["eonet", "firms", "gdacs", "usgs"]
);

const day = 24 * 60 * 60 * 1000;
const minute = 60000;
const now = Date.UTC(2026, 10, 2, 18, 0, 0);

const gdacs = {
    id:"FL:123:9",
    eventId:"123",
    episodeId:"9",
    eventType:"FL",
    eventTypeLabel:"FLOOD",
    name:"Example Flood",
    alertLevel:"ORANGE",
    alertScore:2,
    isCurrent:true,
    country:"United States",
    iso3:"USA",
    latitude:38.9,
    longitude:-77.0,
    fromUtc:"2026-11-02 12:00 UTC",
    toUtc:"2026-11-02 17:00 UTC",
    timeMs:now - 60 * minute,
    severity:3.2,
    severityText:"Flood severity text",
    severityUnit:"m",
    reportUrl:"https://example.invalid/report",
    detailsUrl:"https://example.invalid/details"
};

const usgs = {
    id:"same-id",
    magnitude:4.2,
    place:"Test Place",
    time:now - 50 * minute,
    updated:now - 45 * minute,
    depthKm:8.2,
    latitude:38.8,
    longitude:-77.1,
    significance:310,
    tsunami:false,
    status:"reviewed",
    alert:"green",
    magType:"ml"
};

const eonet = {
    id:"EONET_1",
    title:"Example Wildfire",
    description:"Provider description",
    category:"Wildfires",
    categoryId:"wildfires",
    rawTime:"2026-11-02T16:30:00Z",
    time:"2026-11-02 16:30 UTC",
    geometryType:"Point",
    latitude:39.0,
    longitude:-77.2,
    sourceNames:"NASA",
    magnitude:"NOT REPORTED",
    url:"https://example.invalid/eonet"
};

const firms = {
    id:"38.90000|-77.00000|2026-11-02 17:45Z|N20",
    title:"VIIRS HOTSPOT",
    latitude:38.9,
    longitude:-77.0,
    acquiredUtc:"2026-11-02 17:45Z",
    brightnessK:331.2,
    frpMw:12.5,
    confidenceCode:"h",
    confidenceLabel:"HIGH",
    satellite:"N20",
    instrument:"VIIRS",
    dayNight:"D",
    version:"2.0"
};

for (const [source,row] of [
    ["gdacs", gdacs],
    ["usgs", usgs],
    ["eonet", eonet],
    ["firms", firms]
]) {
    const identity = ctx.eventIdentity(source, row);
    assert.ok(identity, source);
    assert.equal(identity.sourceId, source);
    assert.equal(identity.eventId, row.id);
    assert.equal(identity.eventKey, source + "|" + row.id);

    const snapshot = ctx.normalizeSnapshot(source, row, now);
    assert.ok(snapshot, source + " snapshot");
    assert.equal(snapshot.sourceId, source);
    assert.equal(snapshot.eventId, row.id);
    assert.equal(snapshot.capturedAtMs, now);
    assert.ok(snapshot.title.length > 0);
    assert.ok(snapshot.typeLabel.length > 0);
    assert.equal(typeof snapshot.payload, "object");
}

assert.equal(ctx.eventIdentity("unknown", gdacs), null);
assert.equal(ctx.normalizeSnapshot("unknown", gdacs, now), null);
assert.equal(ctx.positiveMillis(-1), -1);
assert.equal(ctx.positiveMillis("0"), -1);
assert.equal(ctx.positiveMillis(new Date(now)), now);

let doc = ctx.initialDocument();
let result = ctx.append(doc, "gdacs", gdacs, now);
assert.equal(result.ok, true);
assert.equal(result.changed, true);
assert.equal(result.duplicate, false);
assert.equal(result.eventKey, "gdacs|FL:123:9");
assert.equal(result.count, 1);
doc = result.document;
assert.equal(doc.revision, 1);
assert.equal(ctx.eventCount(doc, now), 1);
assert.equal(ctx.snapshotCount(doc, "gdacs", gdacs.id, now), 1);

result = ctx.append(doc, "gdacs", gdacs, now + minute);
assert.equal(result.ok, true);
assert.equal(result.changed, false);
assert.equal(result.duplicate, true);
assert.equal(result.count, 1);
assert.equal(result.document.revision, 1);

const gdacsChanged = {...gdacs, alertLevel:"RED", alertScore:3};
result = ctx.append(doc, "gdacs", gdacsChanged, now + 2 * minute);
assert.equal(result.ok, true);
assert.equal(result.changed, true);
assert.equal(result.count, 2);
doc = result.document;
assert.equal(doc.revision, 2);
assert.equal(
    ctx.latest(doc, "gdacs", gdacs.id, now + 2 * minute)
        .payload.alertLevel,
    "RED"
);

// Same provider-native id under a different provider remains a different key.
const usgsSameId = {...usgs, id:gdacs.id};
result = ctx.append(doc, "usgs", usgsSameId, now + 3 * minute);
assert.equal(result.ok, true);
doc = result.document;
assert.equal(ctx.eventCount(doc, now + 3 * minute), 2);
assert.equal(
    ctx.snapshotCount(doc, "gdacs", gdacs.id, now + 3 * minute),
    2
);
assert.equal(
    ctx.snapshotCount(doc, "usgs", gdacs.id, now + 3 * minute),
    1
);

// Other supported payloads round-trip as their own source identities.
for (const [source,row] of [["eonet",eonet],["firms",firms]]) {
    result = ctx.append(doc, source, row, now + 4 * minute);
    assert.equal(result.ok, true);
    doc = result.document;
    assert.equal(
        ctx.snapshotCount(doc, source, row.id, now + 4 * minute),
        1
    );
}

// Revision cap: changed provider fields keep the newest 32 snapshots.
let capped = ctx.initialDocument();
for (let i = 0; i < 40; i++) {
    const row = {
        ...gdacs,
        alertScore:i,
        severity:i / 10
    };
    const appended = ctx.append(
        capped, "gdacs", row, now + i * minute
    );
    assert.equal(appended.ok, true);
    capped = appended.document;
}
assert.equal(
    ctx.snapshotCount(capped, "gdacs", gdacs.id, now + 40 * minute),
    32
);
const cappedRows = Array.from(
    ctx.snapshots(capped, "gdacs", gdacs.id, now + 40 * minute)
);
assert.equal(cappedRows[0].payload.alertScore, 8);
assert.equal(cappedRows[cappedRows.length - 1].payload.alertScore, 39);

// 180-day retention is based on archive capture time, not source event time.
let aging = ctx.initialDocument();
result = ctx.append(
    aging, "gdacs", gdacs, now - 181 * day
);
assert.equal(result.ok, true);
aging = result.document;
assert.equal(
    ctx.snapshotCount(aging, "gdacs", gdacs.id, now),
    0
);

// Event cap: only the most recently captured 256 provider identities remain.
let many = ctx.initialDocument();
for (let i = 0; i < 270; i++) {
    const row = {
        ...usgs,
        id:"usgs-" + i,
        time:now - i * minute,
        updated:now - i * minute
    };
    const appended = ctx.append(
        many, "usgs", row, now + i * minute
    );
    assert.equal(appended.ok, true);
    many = appended.document;
}
assert.equal(ctx.eventCount(many, now + 270 * minute), 256);
assert.equal(
    ctx.snapshotCount(many, "usgs", "usgs-0", now + 270 * minute),
    0
);
assert.equal(
    ctx.snapshotCount(many, "usgs", "usgs-269", now + 270 * minute),
    1
);

// Invalid writes fail closed.
result = ctx.append(doc, "weather-current", gdacs, now);
assert.equal(result.ok, false);
assert.equal(result.reason, "INVALID_SNAPSHOT");

const roundTrip = ctx.parse(JSON.stringify(doc), now + 5 * minute);
assert.equal(roundTrip.ok, true);
assert.equal(roundTrip.document.schema, ctx.SCHEMA);
assert.equal(roundTrip.document.version, 1);
assert.equal(
    ctx.snapshotCount(
        roundTrip.document, "gdacs", gdacs.id, now + 5 * minute
    ),
    2
);

const store = read("services/weather/WeatherEventArchiveStore.qml");
assert.match(store, /weather-event-archive-v1\.json/);
assert.equal((store.match(/\bFileView\s*\{/g) || []).length, 1);
assert.equal((store.match(/\bTimer\s*\{/g) || []).length, 0);
assert.equal((store.match(/\bProcess\s*\{/g) || []).length, 0);
assert.match(store, /atomicWrites:\s*true/);
assert.match(store, /function archiveEvent\(sourceId, row\)/);
assert.match(store, /deferredRequests/);
assert.match(store, /ArchivePolicy\.append/);
assert.match(store, /lastResultCode = "UNCHANGED"/);

const shell = read("shell.qml");
assert.equal(
    (shell.match(/WeatherEventArchiveStore\s*\{/g) || []).length,
    1
);
assert.match(shell, /id: weatherEventArchive/);
assert.match(
    shell,
    /WeatherStationW\s*\{[\s\S]*?eventArchiveStore: weatherEventArchive/
);

const station = read("widgets/weather/WeatherStationW.qml");
assert.match(station, /property var eventArchiveStore: null/);
const navigator = read("widgets/weather/StationSubjectNavigator.qml");
const earthPane = read("widgets/weather/StationEarthSubjectPane.qml");
assert.match(station,/eventArchiveStore: weatherStation\.eventArchiveStore/);
assert.match(navigator,/eventArchiveStore: browser\.eventArchiveStore/);
assert.match(earthPane,/eventArchiveStore: earthPane\.eventArchiveStore/);
assert.match(earthPane,/StationDiscovery\s*\{/);
assert.ok(!station.includes("id: mapViewComponent"));

const map = read("widgets/weather/StationDiscovery.qml");
assert.match(map, /property var eventArchiveStore: null/);
assert.match(map, /readonly property int selectedArchiveCount:/);
assert.match(map, /function archiveSelectedEvent\(\)/);
assert.match(
    map,
    /return eventArchiveStore\.archiveEvent\(\s*selectedContextSourceId,\s*selectedContextRow\s*\)/
);
assert.equal(
    (map.match(/eventArchiveStore\.archiveEvent\(/g) || []).length,
    1
);
assert.doesNotMatch(map, /onSelectedContextRowChanged[\s\S]*?archiveEvent/);
assert.doesNotMatch(map, /onSelectedEventContextChanged[\s\S]*?archiveEvent/);
assert.match(
    map,
    /onArchiveRequested:\s*stationDiscovery\.archiveSelectedEvent\(\)/
);

const card = read("widgets/weather/StationEventContextCard.qml");
assert.match(card, /signal archiveRequested\(\)/);
assert.match(card, /label: "ARCHIVE"/);
assert.match(card, /available: card\.archiveAvailable/);
assert.match(card, /onClicked: card\.archiveRequested\(\)/);
assert.ok(card.includes("OPERATOR SNAPSHOT // SOURCE IDENTITY PRESERVED"));
assert.equal((card.match(/\bTimer\s*\{/g) || []).length, 0);
assert.equal((card.match(/\bProcess\s*\{/g) || []).length, 0);
assert.equal((card.match(/\bFileView\s*\{/g) || []).length, 0);

console.log("Weather M19 operator event archive: PASS");
