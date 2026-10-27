#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = rel => fs.readFileSync(path.join(root, rel), "utf8");

const ctx = {};
vm.runInNewContext(
    read("widgets/weather/StationRadioMemoryPolicy.js")
        .replace(/^\.pragma library\s*/m, ""),
    ctx
);

for (const fn of [
    "normalize", "encode", "decode", "decodeList",
    "isFavorite", "addFavorite", "removeFavorite", "touchRecent"
])
    assert.equal(typeof ctx[fn], "function", fn);

function station(n, title = "Station " + n) {
    const suffix = String(n).padStart(12, "0");
    return {
        ref: {
            source: "radio-browser",
            kind: "station",
            id: "123e4567-e89b-42d3-a456-" + suffix
        },
        title,
        artist: "US",
        genre: "news,talk",
        album: "news,talk",
        codec: "MP3",
        bitrate: 128,
        streamHost: "must-not-persist.example",
        playback: {available:true, reason:"runtime only"}
    };
}

const first = station(1, "Public News One");
const normalized = ctx.normalize(first);
assert.equal(normalized.ref.source, "radio-browser");
assert.equal(normalized.ref.kind, "station");
assert.equal(normalized.ref.id, first.ref.id);
assert.equal(normalized.title, "Public News One");
assert.equal(normalized.artist, "US");
assert.equal(normalized.genre, "news,talk");
assert.equal(normalized.codec, "MP3");
assert.equal(normalized.bitrate, 128);
assert.equal(normalized.streamHost, undefined);
assert.equal(normalized.playback, undefined);

assert.equal(ctx.normalize({
    ref:{source:"direct-stream", kind:"stream", id:first.ref.id},
    title:"wrong source"
}), null);
assert.equal(ctx.normalize({
    ref:{source:"radio-browser", kind:"station", id:"not-a-uuid"},
    title:"bad uuid"
}), null);
assert.equal(ctx.normalize({
    ref:{source:"radio-browser", kind:"station", id:first.ref.id},
    title:""
}), null);

const encoded = ctx.encode(first);
assert.ok(encoded.length > 0);
assert.doesNotMatch(encoded, /must-not-persist|streamHost|playback|https?:/i);
assert.equal(ctx.decode(encoded).ref.id, first.ref.id);
assert.equal(ctx.decode("{bad json"), null);

let favorites = [];
favorites = ctx.addFavorite(favorites, first, 10);
assert.equal(favorites.length, 1);
assert.equal(ctx.isFavorite(favorites, first), true);

// Re-adding the same UUID moves/keeps one canonical entry rather than
// creating duplicates.
favorites = ctx.addFavorite(favorites, first, 10);
assert.equal(favorites.length, 1);

for (let i = 2; i <= 12; i++)
    favorites = ctx.addFavorite(favorites, station(i), 10);
assert.equal(favorites.length, 10);
assert.equal(ctx.decode(favorites[0]).title, "Station 12");
assert.equal(ctx.isFavorite(favorites, first), false,
             "oldest favorite falls off the explicit 10-entry cap");

favorites = ctx.removeFavorite(favorites, station(12));
assert.equal(favorites.length, 9);
assert.equal(ctx.isFavorite(favorites, station(12)), false);

let recent = [];
recent = ctx.touchRecent(recent, station(2), 8);
recent = ctx.touchRecent(recent, station(3), 8);
recent = ctx.touchRecent(recent, station(2, "Station Two Renamed"), 8);
assert.equal(recent.length, 2);
assert.equal(ctx.decode(recent[0]).ref.id, station(2).ref.id);
assert.equal(ctx.decode(recent[0]).title, "Station Two Renamed");

const mixed = [
    ctx.encode(station(4)),
    "not-json",
    ctx.encode(station(4)),
    ctx.encode(station(5))
];
const decoded = Array.from(ctx.decodeList(mixed, 8));
assert.deepEqual(decoded.map(x => x.ref.id), [
    station(4).ref.id,
    station(5).ref.id
]);

const ui = read("widgets/weather/StationRadio.qml");
assert.match(ui, /import Quickshell/);
assert.match(ui, /StationRadioMemoryPolicy\.js" as RadioMemory/);
assert.match(ui, /FileView\s*\{/);
assert.match(ui, /Quickshell\.dataDir \+ "\/weather-radio-memory\.json"/);
assert.match(ui, /JsonAdapter\s*\{/);
assert.match(ui, /property list<string> favoriteEntries: \[\]/);
assert.match(ui, /property list<string> recentEntries: \[\]/);
assert.match(ui, /RadioMemory\.decodeList\(radioMemoryAdapter\.favoriteEntries, 10\)/);
assert.match(ui, /RadioMemory\.decodeList\(radioMemoryAdapter\.recentEntries, 8\)/);
assert.match(ui, /function toggleHighlightedFavorite\(\)/);
assert.match(ui, /function recallSaved\(item\)/);
assert.match(ui, /function resolveRecall\(\)/);
assert.match(ui, /"name:" \+ row\.title/);
assert.match(ui, /item\.ref\.id === recallTargetId/);
assert.match(ui, /controller\.selectMedia\(item\.ref\)/);
assert.match(ui, /SAVED UUID NOT IN CURRENT DIRECTORY RESULTS/);
assert.match(ui, /id: recallDelay/);
assert.match(ui, /interval: 120/);
assert.match(ui, /repeat: false/);
assert.match(ui, /onBrowseItemsChanged:/);
assert.match(ui, /onLoadedMediaChanged:/);
assert.match(ui, /id !== lastLoadRequestedId/);
assert.match(ui, /RadioMemory\.touchRecent/);
assert.match(ui, /title: "SAVED \/\/ FAVORITES \+ RECENTLY LOADED"/);
assert.match(ui, /label: "RECALL"/);
assert.match(ui, /label: "X"/);
assert.match(ui, /UNFAVORITE/);
assert.match(ui, /NO STORED STREAM URL \/\/ NO AUTOPLAY/);

// Recall must only re-enter the existing directory + select path. It may not
// directly load/play a persisted ref or manufacture a direct stream URL.
const recallStart = ui.indexOf("function recallSaved(item)");
const resolveEnd = ui.indexOf("function selectHighlighted()", recallStart);
assert.ok(recallStart >= 0 && resolveEnd > recallStart);
const recallArea = ui.slice(recallStart, resolveEnd);
assert.match(recallArea, /search\(query, null\)/);
assert.match(recallArea, /controller\.selectMedia\(item\.ref\)/);
assert.doesNotMatch(
    recallArea,
    /loadMedia\(|loadSelectedMedia\(|transport\(|direct-stream|https?:\/\//
);

// Memory policy itself never handles stream origins, playback, processes or
// network access.
const policy = read("widgets/weather/StationRadioMemoryPolicy.js");
assert.doesNotMatch(
    policy,
    /streamHost|url_resolved|direct-stream|https?:\/\/|Process\s*\{|Timer\s*\{|curl|XMLHttpRequest/
);

console.log("Weather RADIO favorites, recents and safe recall contracts: PASS");
