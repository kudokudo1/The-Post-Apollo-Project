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
    read("services/weather/StationDiscoveryPolicy.js")
        .replace(/^\.pragma library\s*/m, ""),
    ctx
);

for (const fn of [
    "gdeltSeenMillis", "newsBatchSummary",
    "filterNewsRows", "parseNews"
])
    assert.equal(typeof ctx[fn], "function", fn);

const now = Date.parse("2026-10-31T12:00:00Z");
assert.equal(
    ctx.gdeltSeenMillis("20261031T113000Z"),
    Date.parse("2026-10-31T11:30:00Z")
);
assert.equal(
    ctx.gdeltSeenMillis("2026-10-31T10:15:00Z"),
    Date.parse("2026-10-31T10:15:00Z")
);
assert.equal(ctx.gdeltSeenMillis("not-a-time"), -1);

const payload = {
    articles: [
        {
            title:"Heavy rain reaches Maryland",
            domain:"wx.example",
            sourcecountry:"US",
            language:"English",
            seendate:"20261031T113000Z",
            url:"https://wx.example/a"
        },
        {
            title:"Wildfire update from Spain",
            domain:"fire.example.es",
            sourcecountry:"Spain",
            language:"Spanish",
            seendate:"20261031T093000Z",
            url:"https://fire.example.es/b"
        },
        {
            title:"Earthquake report from Japan",
            domain:"quake.example.jp",
            sourcecountry:"Japan",
            language:"Japanese",
            seendate:"20261031T060000Z",
            url:"https://quake.example.jp/c"
        },
        {
            title:"Aurora forecast from Canada",
            domain:"space.example.ca",
            sourcecountry:"Canada",
            lang:"French",
            seendate:"20261030T140000Z",
            url:"https://space.example.ca/d"
        }
    ]
};

const rows = Array.from(ctx.parseNews(payload));
assert.equal(rows.length, 4);
assert.equal(rows[0].language, "English");
assert.equal(rows[1].language, "Spanish");
assert.equal(rows[3].language, "French");
assert.equal(rows[0].seenMillis, Date.parse("2026-10-31T11:30:00Z"));
assert.match(rows[0].detail, /ENGLISH/);

function filter(topic, source, language, hours) {
    return Array.from(
        ctx.filterNewsRows(rows, topic, source, language, hours, now)
    );
}

assert.deepEqual(
    filter("all", "", "", 1).map(x => x.title),
    ["Heavy rain reaches Maryland"]
);
assert.deepEqual(
    filter("all", "", "", 3).map(x => x.title),
    [
        "Heavy rain reaches Maryland",
        "Wildfire update from Spain"
    ]
);
assert.deepEqual(
    filter("all", "", "", 6).map(x => x.title),
    [
        "Heavy rain reaches Maryland",
        "Wildfire update from Spain",
        "Earthquake report from Japan"
    ]
);
assert.equal(filter("all", "", "", 24).length, 4);
assert.deepEqual(
    filter("all", "", "span", 24).map(x => x.title),
    ["Wildfire update from Spain"]
);
assert.deepEqual(
    filter("weather", "us", "english", 1).map(x => x.title),
    ["Heavy rain reaches Maryland"]
);
assert.deepEqual(
    filter("space", "canada", "french", 24).map(x => x.title),
    ["Aurora forecast from Canada"]
);
assert.equal(filter("earth", "", "english", 24).length, 0);

// Old three-argument callers retain ALL-time/all-language semantics.
assert.equal(ctx.filterNewsRows(rows, "all", "").length, 4);

const summary = ctx.newsBatchSummary(rows);
assert.deepEqual(
    JSON.parse(JSON.stringify(summary)),
    {
        articles:4,
        publishers:4,
        countries:4,
        languages:4,
        timedRows:4
    }
);
const filteredSummary = ctx.newsBatchSummary(
    filter("all", "", "", 3)
);
assert.equal(filteredSummary.articles, 2);
assert.equal(filteredSummary.publishers, 2);
assert.equal(filteredSummary.countries, 2);
assert.equal(filteredSummary.languages, 2);

const untimed = [{
    title:"No provider time",
    domain:"unknown.example",
    country:"US",
    language:"English",
    seenMillis:-1,
    topics:[]
}];
assert.equal(
    ctx.filterNewsRows(untimed, "all", "", "", 1, now).length,
    0,
    "time-window mode must not pretend an untimed record is recent"
);
assert.equal(
    ctx.filterNewsRows(untimed, "all", "", "", 0, now).length,
    1
);

const ui = read("widgets/weather/StationDiscovery.qml");
assert.match(ui, /property string newsLanguageQuery: ""/);
assert.match(ui, /property int newsMaxAgeHours: 0/);
assert.match(ui, /readonly property var newsTimeOptions:/);
for (const label of ["ALL 24H", "1H", "3H", "6H", "12H", "24H"])
    assert.ok(ui.includes('"label": "' + label + '"'), label);

assert.match(
    ui,
    /DiscoveryPolicy\.filterNewsRows\([\s\S]*?newsLanguageQuery,[\s\S]*?newsMaxAgeHours,[\s\S]*?source \? source\.sourceClockMs : 0/
);
assert.match(ui, /DiscoveryPolicy\.newsBatchSummary\(visibleRows\)/);
assert.match(ui, /id: newsTimeRail/);
assert.match(ui, /function selectNewsTime\(hours\)/);
assert.match(ui, /id: newsLanguageFilter/);
assert.match(ui, /id: newsLanguageInput/);
assert.match(ui, /LANGUAGE \/ CODE/);
assert.match(ui, /LOCAL SEENDATE FILTER/);
assert.match(ui, /FULL GDELT 24H BATCH/);
assert.match(ui, /PUBLISHERS \/\/ /);
assert.match(ui, /COUNTRIES \/\/ /);
assert.match(ui, /LANGUAGES/);
assert.match(ui, /LANGUAGE \+ TIME WINDOW FILTERS", state:"CONNECTED"/);
assert.match(ui, /SOURCE-COUNTRY REGION GROUPS", state:"CONNECTED"/);
assert.match(ui, /EVENT \/ MENTIONED-LOCATION LINKING", state:"NOT WIRED"/);

// Reuse the existing NEWS source clock; this feature adds no timer/fetch.
const service = read("services/weather/StationDiscoveryService.qml");
assert.match(service, /interval: 1000/);
assert.match(
    service,
    /running: discovery\.active && discovery\.domain === "news"/
);
assert.equal((service.match(/\bProcess\s*\{/g) || []).length, 1);
assert.equal((service.match(/\bTimer\s*\{/g) || []).length, 2);

const timeStart = ui.indexOf("id: newsTimeRail");
const languageStart = ui.indexOf("id: newsLanguageFilter");
const cautionStart = ui.indexOf(
    "text: stationDiscovery.sourceCaution",
    languageStart
);
assert.ok(timeStart >= 0 && languageStart > timeStart);
assert.ok(cautionStart > languageStart);
const filters = ui.slice(timeStart, cautionStart);
assert.doesNotMatch(
    filters,
    /refresh\(|Process\s*\{|curl|endpoint|Qt\.openUrlExternally/
);

console.log("Weather NEWS language time-window and source batch stats: PASS");
