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
    "canonicalNewsUrl", "newsTitleKey", "newsTopics",
    "filterNewsRows", "parseNews"
])
    assert.equal(typeof ctx[fn], "function", fn);

// Canonicalization is deliberately narrow: remove fragments/common tracking,
// normalize host/trailing slash, and sort retained query parameters.
assert.equal(
    ctx.canonicalNewsUrl(
        "https://www.Example.com/story/?utm_source=x&id=7&fbclid=abc#top"
    ),
    "https://example.com/story?id=7"
);
assert.equal(
    ctx.canonicalNewsUrl("https://example.com/a?z=2&a=1"),
    "https://example.com/a?a=1&z=2"
);
assert.equal(
    ctx.canonicalNewsUrl("https://example.com/a?ref=homepage"),
    "https://example.com/a?ref=homepage",
    "ordinary publisher parameters are preserved"
);
assert.equal(ctx.canonicalNewsUrl("javascript:alert(1)"), "");

assert.equal(
    ctx.newsTitleKey("  Wildfire: Smoke Spreads!  "),
    ctx.newsTitleKey("wildfire smoke spreads")
);
assert.notEqual(
    ctx.newsTitleKey("Wildfire grows near town"),
    ctx.newsTitleKey("Wildfire contained near town"),
    "similar-but-different headlines are not fuzzy clustered"
);

assert.deepEqual(
    Array.from(ctx.newsTopics("Aurora watch after geomagnetic storm")),
    ["space"]
);
assert.deepEqual(
    Array.from(ctx.newsTopics("Earthquake triggers tsunami warning")),
    ["earth"]
);
assert.deepEqual(
    Array.from(ctx.newsTopics("Wildfire smoke spreads in high winds")),
    ["fire", "weather"]
);
assert.deepEqual(
    Array.from(ctx.newsTopics("Heavy rain forecast this weekend")),
    ["weather"]
);

const payload = {
    articles: [
        {
            title: "Wildfire smoke spreads across region",
            domain: "www.example.com",
            sourcecountry: "US",
            seendate: "20261027T103000Z",
            url: "https://www.example.com/story/?utm_source=x&id=7#top"
        },
        {
            // Same canonical URL, different tracking wrapper.
            title: "Alternate wrapper title",
            domain: "example.com",
            sourcecountry: "US",
            seendate: "20261027T102959Z",
            url: "https://example.com/story?id=7&utm_medium=social"
        },
        {
            // Same normalized headline across another publisher.
            title: "Wildfire smoke spreads across region!",
            domain: "mirror.example",
            sourcecountry: "US",
            seendate: "20261027T102900Z",
            url: "https://mirror.example/copy"
        },
        {
            title: "Aurora watch after geomagnetic storm",
            domain: "space.example",
            sourcecountry: "CA",
            seendate: "20261027T101500Z",
            url: "https://space.example/a?fbclid=abc"
        },
        {
            title: "Earthquake shakes coastal city",
            domain: "quake.example",
            sourcecountry: "JP",
            seendate: "20261027T100000Z",
            url: "https://quake.example/q"
        },
        {
            title: "Heavy rain forecast this weekend",
            domain: "wx.example",
            sourcecountry: "GB",
            seendate: "20261027T093000Z",
            url: "https://wx.example/w"
        },
        {
            title: "General environmental report",
            domain: "other.example",
            sourcecountry: "FR",
            seendate: "20261027T090000Z",
            url: "https://other.example/o"
        }
    ]
};

const rows = Array.from(ctx.parseNews(payload));
assert.equal(rows.length, 5, "one canonical URL duplicate + one headline duplicate removed");
assert.equal(rows[0].canonicalUrl, "https://example.com/story?id=7");
assert.equal(rows[0].domain, "www.example.com");
assert.equal(rows[0].country, "US");
assert.equal(rows[0].primaryTopic, "fire");
assert.equal(rows[1].primaryTopic, "space");
assert.equal(rows[1].topics.includes("weather"), false);
assert.equal(rows[4].primaryTopic, "other");
assert.equal(rows[4].topics.length, 0);

const all = Array.from(ctx.filterNewsRows(rows, "all"));
const weather = Array.from(ctx.filterNewsRows(rows, "weather"));
const earth = Array.from(ctx.filterNewsRows(rows, "earth"));
const fire = Array.from(ctx.filterNewsRows(rows, "fire"));
const space = Array.from(ctx.filterNewsRows(rows, "space"));
assert.equal(all.length, 5);
assert.deepEqual(weather.map(x => x.title), ["Heavy rain forecast this weekend"]);
assert.deepEqual(earth.map(x => x.title), ["Earthquake shakes coastal city"]);
assert.deepEqual(fire.map(x => x.title), ["Wildfire smoke spreads across region"]);
assert.deepEqual(space.map(x => x.title), ["Aurora watch after geomagnetic storm"]);
all.push({title:"local mutation"});
assert.equal(ctx.filterNewsRows(rows, "all").length, 5);
assert.equal(ctx.filterNewsRows(null, "all").length, 0);

const ui = read("widgets/weather/StationDiscovery.qml");
assert.match(
    ui,
    /StationDiscoveryPolicy\.js" as DiscoveryPolicy/
);
assert.match(ui, /property string newsTopic: "all"/);
for (const label of ["ALL", "WEATHER", "EARTH", "FIRE", "SPACE"])
    assert.ok(ui.includes('"label": "' + label + '"'), label);
assert.match(
    ui,
    /DiscoveryPolicy\.filterNewsRows\([\s\S]*?source\.rows[\s\S]*?newsTopic/
);
assert.match(ui, /id: newsTopicRail/);
assert.match(ui, /delegate: ModeButton/);
assert.match(ui, /bordered: false/);
assert.match(ui, /selected: stationDiscovery\.newsTopic === modelData\.id/);
assert.match(ui, /SHOWING /);
assert.match(ui, /\/ " \+ source\.rows\.length[\s\S]*?LOCAL FILTER/);
assert.match(ui, /NO HEADLINES MATCH/);
assert.match(ui, /FILTER IS LOCAL \/\/ SOURCE NOT REFETCHED/);
assert.match(
    ui,
    /model: source\.ready \? stationDiscovery\.visibleRows : \[\]/
);
assert.match(ui, /LOCAL TOPIC FILTER \+ URL\/TITLE DEDUPE/);
assert.match(ui, /EXACT-HEADLINE SOURCE GROUPS \/\/ NOT FUZZY STORY CLUSTERING/);
assert.match(ui, /EXACT-HEADLINE SOURCE GROUPS", state:"CONNECTED"/);
assert.match(ui, /SEMANTIC STORY CLUSTERS \/ DOSSIERS", state:"NOT WIRED"/);
assert.match(ui, /PUBLISHER \/ SOURCE COUNTRY FILTER", state:"CONNECTED"/);
assert.match(ui, /LANGUAGE \+ TIME WINDOW FILTERS", state:"CONNECTED"/);
assert.match(ui, /SOURCE-COUNTRY REGION GROUPS", state:"CONNECTED"/);
assert.match(ui, /EVENT \/ MENTIONED-LOCATION LINKING", state:"NOT WIRED"/);

const selectStart = ui.indexOf("function selectNewsTopic(id)");
const selectEnd = ui.indexOf("function selectMapFilter(id)", selectStart);
assert.ok(selectStart >= 0 && selectEnd > selectStart);
const selectFunction = ui.slice(selectStart, selectEnd);
assert.match(selectFunction, /newsTopic = id/);
assert.match(selectFunction, /discoveryScroll\.contentY = 0/);
assert.doesNotMatch(
    selectFunction,
    /refresh\(|Process\s*\{|curl|endpoint|Qt\.openUrlExternally/
);

const policySource = read("services/weather/StationDiscoveryPolicy.js");
assert.doesNotMatch(
    policySource,
    /Levenshtein|Jaro|embedding|cosine|editDistance|fuzzyMatch/i,
    "dedupe must remain exact/canonical rather than fuzzy story matching"
);

console.log("Weather NEWS conservative dedupe and local topic filters: PASS");
