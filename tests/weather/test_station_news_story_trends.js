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
    "newsStoryTokens", "newsStoryScore",
    "newsStoryFamilies", "newsReportingTrend"
])
    assert.equal(typeof ctx[fn], "function", fn);

assert.deepEqual(
    Array.from(
        ctx.newsStoryTokens(
            "The latest Hurricane Melissa floods Jamaica after landfall"
        )
    ),
    ["hurricane", "melissa", "floods", "jamaica", "landfall"]
);

const first = {
    title:"Hurricane Melissa floods Jamaica after landfall",
    topics:["weather"]
};
const variant = {
    title:"Hurricane Melissa floods Jamaica following landfall",
    topics:["weather"]
};
const nearbyDifferent = {
    title:"Hurricane Melissa threatens Cuba after Jamaica",
    topics:["weather"]
};
const topicMismatch = {
    title:"Hurricane Melissa floods Jamaica following landfall",
    topics:["space"]
};

const strong = ctx.newsStoryScore(first, variant);
assert.equal(strong.match, true);
assert.ok(strong.common >= 5);
assert.ok(strong.overlap >= 0.75);
assert.ok(strong.jaccard >= 0.62);

const different = ctx.newsStoryScore(first, nearbyDifferent);
assert.equal(
    different.match,
    false,
    "shared hurricane/place words must not merge a different event headline"
);
assert.equal(ctx.newsStoryScore(first, topicMismatch).match, false);

const rows = [
    {
        title:first.title,
        topics:["weather"],
        domain:"alpha.example",
        country:"Jamaica",
        language:"English",
        seenMillis:Date.parse("2026-10-31T11:30:00Z"),
        sourceGroup:{
            articleCount:2,
            domains:["alpha.example", "gamma.example"],
            countries:["Jamaica", "US"],
            languages:["English"]
        }
    },
    {
        title:variant.title,
        topics:["weather"],
        domain:"beta.example",
        country:"UK",
        language:"English",
        seenMillis:Date.parse("2026-10-31T11:20:00Z"),
        sourceGroup:{
            articleCount:1,
            domains:["beta.example"],
            countries:["UK"],
            languages:["English"]
        }
    },
    {
        title:nearbyDifferent.title,
        topics:["weather"],
        domain:"delta.example",
        country:"Cuba",
        language:"Spanish",
        seenMillis:Date.parse("2026-10-31T11:10:00Z"),
        sourceGroup:{
            articleCount:1,
            domains:["delta.example"],
            countries:["Cuba"],
            languages:["Spanish"]
        }
    }
];

const families = Array.from(ctx.newsStoryFamilies(rows));
assert.equal(families.length, 1);
assert.equal(families[0].variantCount, 2);
assert.equal(families[0].articleRecords, 3);
assert.equal(families[0].sourceCount, 3);
assert.deepEqual(
    Array.from(families[0].domains),
    ["alpha.example", "gamma.example", "beta.example"]
);
assert.deepEqual(
    Array.from(families[0].countries),
    ["Jamaica", "US", "UK"]
);
assert.deepEqual(
    Array.from(families[0].languages),
    ["English"]
);
assert.ok(families[0].strongestJaccard >= 0.62);
assert.ok(families[0].strongestJaccard < 1);

const now = Date.parse("2026-10-31T12:00:00Z");
const trendRows = [
    {
        seenMillis:Date.parse("2026-10-31T11:30:00Z"),
        domain:"a.example"
    },
    {
        seenMillis:Date.parse("2026-10-31T10:30:00Z"),
        domain:"b.example"
    },
    {
        seenMillis:Date.parse("2026-10-31T07:00:00Z"),
        domain:"a.example"
    },
    {
        seenMillis:Date.parse("2026-10-31T03:00:00Z"),
        domain:"c.example"
    },
    {
        seenMillis:-1,
        domain:"untimed.example"
    }
];

const trend = ctx.newsReportingTrend(trendRows, now, 4, 6);
assert.equal(trend.buckets.length, 6);
assert.equal(trend.timedRows, 4);
assert.equal(trend.buckets[5].label, "0-4H");
assert.equal(trend.buckets[5].articles, 2);
assert.equal(trend.buckets[5].sources, 2);
assert.equal(trend.buckets[4].articles, 1);
assert.equal(trend.buckets[4].sources, 1);
assert.equal(trend.buckets[3].articles, 1);
assert.equal(trend.maxArticles, 2);
assert.equal(trend.maxSources, 2);
assert.equal(trend.recentArticles, 3);
assert.equal(trend.previousArticles, 1);
assert.equal(trend.direction, "RISING");

const sparse = ctx.newsReportingTrend(
    [{seenMillis:now - 1000, domain:"one.example"}],
    now,
    4,
    6
);
assert.equal(sparse.direction, "SPARSE");

const noTime = ctx.newsReportingTrend(
    [{seenMillis:-1, domain:"none.example"}],
    0,
    4,
    6
);
assert.equal(noTime.direction, "NO TIME DATA");
assert.equal(noTime.buckets.length, 0);

const ui = read("widgets/weather/StationDiscovery.qml");
assert.match(ui, /DiscoveryPolicy\.newsReportingTrend/);
assert.match(ui, /DiscoveryPolicy\.newsStoryFamilies/);
assert.match(ui, /REPORTING TREND \/\/ CURRENT FILTERED BATCH/);
assert.match(ui, /STORY FAMILIES \/\/ CONSERVATIVE TITLE TOKENS/);
assert.match(ui, /ORANGE = ARTICLES \/\/ CYAN = UNIQUE PUBLISHERS/);
assert.match(ui, /modelData\.strongestJaccard/);
assert.match(ui, /modelData\.variantCount/);
assert.match(ui, /modelData\.sourceCount/);
assert.match(ui, /CONSERVATIVE STORY FAMILIES", state:"CONNECTED"/);
assert.match(ui, /REPORTING TREND \/ SOURCE COUNT", state:"CONNECTED"/);
assert.match(ui, /SEMANTIC \/ EMBEDDING DOSSIERS", state:"NOT WIRED"/);
assert.match(ui, /NOT EMBEDDING SEMANTICS OR VERIFIED EVENT IDENTITY/);

const trendStart = ui.indexOf(
    'title: "REPORTING TREND // CURRENT FILTERED BATCH"'
);
const cautionStart = ui.indexOf(
    "text: stationDiscovery.sourceCaution",
    trendStart
);
assert.ok(trendStart >= 0 && cautionStart > trendStart);
const relationshipArea = ui.slice(trendStart, cautionStart);
assert.doesNotMatch(
    relationshipArea,
    /refresh\(|Process\s*\{|curl|endpoint|Qt\.openUrlExternally/
);

const service = read("services/weather/StationDiscoveryService.qml");
assert.equal((service.match(/\bProcess\s*\{/g) || []).length, 1);
assert.equal((service.match(/\bTimer\s*\{/g) || []).length, 2);

const policy = read("services/weather/StationDiscoveryPolicy.js");
assert.doesNotMatch(
    policy,
    /Levenshtein|Jaro|embedding|cosine|editDistance|fuzzyMatch/i
);
assert.match(policy, /jaccard >= 0\.62/);
assert.match(policy, /overlap >= 0\.75/);
assert.match(policy, /common >= 3/);

const workflow = read(".github/workflows/weather-teardown-contracts.yml");
assert.match(
    workflow,
    /node tests\/weather\/test_station_news_story_trends\.js/
);

console.log("Weather NEWS reporting trend and conservative story families: PASS");
