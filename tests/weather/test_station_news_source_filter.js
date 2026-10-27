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

const rows = [
    {
        title:"Rain forecast for Maryland",
        domain:"weather.example.com",
        country:"United States",
        topics:["weather"]
    },
    {
        title:"Aurora activity increases",
        domain:"space.example.ca",
        country:"Canada",
        topics:["space"]
    },
    {
        title:"Wildfire smoke update",
        domain:"regional.example.org",
        country:"United States",
        topics:["fire"]
    },
    {
        title:"Earthquake report",
        domain:"news.example.jp",
        country:"Japan",
        topics:["earth"]
    }
];

function titles(topic, query) {
    return Array.from(ctx.filterNewsRows(rows, topic, query), row => row.title);
}

assert.deepEqual(titles("all", ""), [
    "Rain forecast for Maryland",
    "Aurora activity increases",
    "Wildfire smoke update",
    "Earthquake report"
]);
assert.deepEqual(titles("all", "canada"), ["Aurora activity increases"]);
assert.deepEqual(titles("all", "EXAMPLE.JP"), ["Earthquake report"]);
assert.deepEqual(titles("weather", "united states"), ["Rain forecast for Maryland"]);
assert.deepEqual(titles("fire", "UNITED"), ["Wildfire smoke update"]);
assert.deepEqual(titles("space", "canada"), ["Aurora activity increases"]);
assert.deepEqual(titles("space", "japan"), []);
assert.deepEqual(titles("earth", "news.example"), ["Earthquake report"]);
assert.deepEqual(titles("all", "  Canada  "), ["Aurora activity increases"]);
assert.deepEqual(titles("all", "does-not-exist"), []);

// Filtering returns a new list and never mutates cached source rows.
const copy = ctx.filterNewsRows(rows, "all", "");
copy.pop();
assert.equal(rows.length, 4);
assert.equal(ctx.filterNewsRows(rows, "all", "").length, 4);

const ui = read("widgets/weather/StationDiscovery.qml");
assert.match(ui, /property string newsSourceQuery: ""/);
assert.match(
    ui,
    /DiscoveryPolicy\.filterNewsRows\([\s\S]*?newsTopic,[\s\S]*?newsSourceQuery/
);
assert.match(ui, /id: newsSourceFilter/);
assert.match(ui, /id: newsSourceInput/);
assert.match(ui, /PUBLISHER DOMAIN \/ SOURCE COUNTRY/);
assert.match(ui, /onTextEdited:[\s\S]*?newsSourceQuery = text/);
assert.match(ui, /Keys\.onEscapePressed:/);
assert.match(ui, /newsSourceQuery = ""/);
assert.match(ui, /label: "CLEAR"/);
assert.match(ui, /LOCAL \/\/ MATCHES GDELT DOMAIN OR SOURCE COUNTRY/);
assert.match(ui, /SOURCE MATCH/);
assert.match(ui, /PUBLISHER \/ SOURCE COUNTRY FILTER", state:"CONNECTED"/);
assert.match(ui, /REGION \/ LANGUAGE FILTERS", state:"NOT WIRED"/);
assert.match(ui, /FILTER IS LOCAL \/\/ SOURCE NOT REFETCHED/);

const inputStart = ui.indexOf("id: newsSourceInput");
const inputEnd = ui.indexOf("ActionButton {", inputStart);
assert.ok(inputStart >= 0 && inputEnd > inputStart);
const inputArea = ui.slice(inputStart, inputEnd);
assert.doesNotMatch(
    inputArea,
    /refresh\(|Process\s*\{|curl|endpoint|Qt\.openUrlExternally/
);

const filterSource = read("services/weather/StationDiscoveryPolicy.js");
const filterStart = filterSource.indexOf("function filterNewsRows");
const filterEnd = filterSource.indexOf("function parseEvents", filterStart);
assert.ok(filterStart >= 0 && filterEnd > filterStart);
const filterFunction = filterSource.slice(filterStart, filterEnd);
assert.match(filterFunction, /row\.domain/);
assert.match(filterFunction, /row\.country/);
assert.doesNotMatch(
    filterFunction,
    /fetch|curl|XMLHttpRequest|Qt\.openUrlExternally/
);

console.log("Weather NEWS publisher-domain and source-country filter: PASS");
