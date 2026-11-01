#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = rel => fs.readFileSync(path.join(root, rel), "utf8");

const source = read("services/weather/WeatherEventDossierPolicy.js");
const ctx = {
    Date, Math, Number, String, Array, Object, JSON,
    isFinite, isNaN
};
vm.runInNewContext(source.replace(/^\.pragma library\s*/m, ""), ctx);

for (const fn of [
    "initialDocument", "parse", "sanitizeAnchor", "sanitizeRelation",
    "addDossier", "clearDocument", "recent", "summary", "formatSavedAt"
])
    assert.equal(typeof ctx[fn], "function", fn);

const empty = ctx.initialDocument();
assert.equal(empty.version, 1);
assert.equal(empty.revision, 0);
assert.equal(empty.dossiers.length, 0);

let parsed = ctx.parse("");
assert.equal(parsed.ok, true);
assert.equal(parsed.empty, true);
assert.equal(parsed.document.dossiers.length, 0);
assert.equal(ctx.parse("{wat").ok, false);
assert.equal(ctx.parse(JSON.stringify({version:99,dossiers:[]})).reason,
             "UNSUPPORTED_VERSION");

const anchor = {
    source: "GDACS",
    id: "WF:7:1",
    title: "Example Wildfire",
    hazard: "fire",
    latitude: 38.5,
    longitude: -77.2,
    observedMs: Date.parse("2026-10-31T18:00:00Z")
};
const relations = [
    {
        source: "NASA EONET",
        id: "EONET_7",
        title: "Example Fire",
        hazard: "fire",
        latitude: 38.55,
        longitude: -77.15,
        distanceKm: 7.2,
        deltaHours: 1.5,
        relationKind: "TIME + SPACE",
        mentionOnly: false,
        semantics: "RELATED SOURCE CONTEXT, NOT SAME-EVENT IDENTITY"
    },
    {
        source: "GDELT GKG",
        id: "place-7",
        title: "Nearby Place",
        hazard: "unknown",
        latitude: 38.52,
        longitude: -77.18,
        distanceKm: 2.4,
        deltaHours: -1,
        relationKind: "MENTION NEARBY",
        mentionOnly: true,
        semantics: "ARTICLE MENTION NEAR AN EVENT ANCHOR, NOT VERIFIED EVENT LOCATION"
    }
];

const t1 = Date.parse("2026-11-01T00:30:00Z");
let added = ctx.addDossier(empty, anchor, relations, t1);
assert.equal(added.ok, true);
assert.equal(added.document.revision, 1);
assert.equal(added.document.dossiers.length, 1);
assert.equal(added.dossier.anchor.source, "GDACS");
assert.equal(added.dossier.anchor.hazard, "fire");
assert.equal(added.dossier.relations.length, 2);
assert.equal(added.dossier.relations[1].mentionOnly, true);
assert.match(added.dossier.relations[1].semantics, /NOT VERIFIED EVENT LOCATION/);

let duplicate = ctx.addDossier(
    added.document, anchor, relations, t1 + 120000
);
assert.equal(duplicate.ok, false);
assert.equal(duplicate.reason, "RECENT_DUPLICATE");
assert.equal(duplicate.document.dossiers.length, 1);

const t2 = t1 + 301000;
added = ctx.addDossier(added.document, anchor, relations, t2);
assert.equal(added.ok, true);
assert.equal(added.document.revision, 2);
assert.equal(added.document.dossiers.length, 2);
assert.equal(added.document.dossiers[0].savedAtMs, t2);

const summary = ctx.summary(added.document);
assert.equal(summary.count, 2);
assert.equal(summary.revision, 2);
assert.equal(summary.sources, 1);
assert.equal(summary.latestMs, t2);
assert.equal(Array.from(ctx.recent(added.document, 1)).length, 1);
assert.match(ctx.formatSavedAt(t2), /^2026-11-01 00:35 UTC$/);

const cleared = ctx.clearDocument(added.document);
assert.equal(cleared.ok, true);
assert.equal(cleared.document.revision, 3);
assert.equal(cleared.document.dossiers.length, 0);

assert.equal(ctx.addDossier(
    empty,
    {...anchor, latitude:100},
    relations,
    t1
).reason, "INVALID_ANCHOR");
assert.equal(ctx.addDossier(empty, anchor, relations, -1).reason, "INVALID_TIME");

// Parse is fail-closed and bounded: malformed dossiers are ignored.
parsed = ctx.parse(JSON.stringify({
    version:1,
    revision:4,
    dossiers:[
        added.document.dossiers[0],
        {id:"bad",savedAtMs:0,anchor:null,relations:[]}
    ]
}));
assert.equal(parsed.ok, true);
assert.equal(parsed.document.dossiers.length, 1);

const store = read("services/weather/WeatherEventDossierStore.qml");
assert.match(store, /Quickshell\.dataDir \+ "\/weather-event-dossiers-v1\.json"/);
assert.match(store, /WeatherEventDossierPolicy\.js" as DossierPolicy/);
assert.match(store, /atomicWrites: true/);
assert.match(store, /watchChanges: false/);
assert.match(store, /dossierFile\.setText\(JSON\.stringify\(pendingDocument, null, 2\) \+ "\\n"\)/);
assert.match(store, /DossierPolicy\.addDossier\([\s\S]*Date\.now\(\)/);
assert.match(store, /function clearArchive\(\)/);
assert.doesNotMatch(store, /\bTimer\s*\{/);
assert.doesNotMatch(store, /\bProcess\s*\{/);
assert.doesNotMatch(store, /curl|XMLHttpRequest|Qt\.openUrlExternally/);

const ui = read("widgets/weather/StationDiscovery.qml");
assert.match(
    ui,
    /import "\.\.\/\.\.\/services\/weather\/WeatherEventDossierPolicy\.js" as DossierPolicy/
);
assert.match(ui, /WeatherServices\.WeatherEventDossierStore\s*\{/);
assert.match(ui, /name:"EVENT DOSSIER ARCHIVE \/\/ LOCAL"/);
assert.match(ui, /title: "EVENT DOSSIERS \/\/ LOCAL HISTORY"/);
assert.match(ui, /label: "SAVE DOSSIER"/);
assert.match(ui, /dossierStore\.saveDossier\([\s\S]*relationAnchor[\s\S]*relatedSourceRows/);
assert.match(ui, /label: stationDiscovery\.dossierClearArmed[\s\S]*"CONFIRM CLEAR" : "ARM CLEAR"/);
assert.match(ui, /dossierStore\.clearArchive\(\)/);
assert.match(ui, /model: dossierStore\.recentDossiers/);
assert.match(ui, /modelData\.relations\.length/);
assert.match(ui, /MAX 128 DOSSIERS/);
assert.match(ui, /MANUAL SNAPSHOTS ONLY/);
assert.match(ui, /ATOMIC VERSIONED JSON/);

const homeService = read("services/weather/WeatherHistoryService.qml");
assert.match(homeService, /This is not a local database/);
assert.doesNotMatch(homeService, /WeatherEventDossier/);

console.log("Weather MAP operator-saved event dossier archive: PASS");
