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
    "newsTitleKey", "newsExactSourceGroups", "parseNews"
])
    assert.equal(typeof ctx[fn], "function", fn);

const articles = [
    {
        title:"River flooding threatens downtown",
        domain:"alpha.example",
        sourcecountry:"US",
        language:"English",
        seendate:"20261031T100000Z",
        url:"https://alpha.example/flood?id=1"
    },
    {
        title:"River flooding threatens downtown!",
        domain:"beta.example",
        sourcecountry:"Canada",
        language:"French",
        seendate:"20261031T100500Z",
        url:"https://beta.example/story"
    },
    {
        title:"RIVER FLOODING THREATENS DOWNTOWN",
        domain:"gamma.example",
        sourcecountry:"US",
        language:"English",
        seendate:"20261031T101000Z",
        url:"https://gamma.example/report"
    },
    {
        // Same exact title key but same publisher. This is another article
        // record, not another independent source.
        title:"River flooding threatens downtown",
        domain:"alpha.example",
        sourcecountry:"US",
        language:"English",
        seendate:"20261031T101500Z",
        url:"https://alpha.example/flood?id=2"
    },
    {
        // Similar words are deliberately NOT grouped.
        title:"River flooding threatens nearby suburb",
        domain:"delta.example",
        sourcecountry:"US",
        language:"English",
        seendate:"20261031T102000Z",
        url:"https://delta.example/suburb"
    },
    {
        // Same URL after tracking cleanup is not counted twice.
        title:"Separate wrapper title",
        domain:"alpha.example",
        sourcecountry:"US",
        language:"English",
        seendate:"20261031T102500Z",
        url:"https://alpha.example/flood?id=1&utm_source=social"
    }
];

const key = ctx.newsTitleKey("River flooding threatens downtown");
const groups = ctx.newsExactSourceGroups(articles);
assert.ok(groups[key]);
assert.equal(groups[key].articleCount, 4);
assert.equal(groups[key].sourceCount, 3);
assert.equal(groups[key].multiSource, true);
assert.deepEqual(
    Array.from(groups[key].domains),
    ["alpha.example", "beta.example", "gamma.example"]
);
assert.deepEqual(
    Array.from(groups[key].countries),
    ["US", "Canada"]
);
assert.deepEqual(
    Array.from(groups[key].languages),
    ["English", "French"]
);

const similarKey = ctx.newsTitleKey(
    "River flooding threatens nearby suburb"
);
assert.notEqual(key, similarKey);
assert.equal(groups[similarKey].sourceCount, 1);
assert.equal(groups[similarKey].multiSource, false);

const rows = Array.from(ctx.parseNews({articles}));
assert.equal(
    rows.filter(x => x.title.toLowerCase().includes("downtown")).length,
    1,
    "existing exact-title dedupe remains one visible representative"
);
const grouped = rows.find(
    x => x.sourceGroup && x.sourceGroup.multiSource
);
assert.ok(grouped);
assert.equal(grouped.sourceGroup.articleCount, 4);
assert.equal(grouped.sourceGroup.sourceCount, 3);
assert.deepEqual(
    Array.from(grouped.sourceGroup.domains),
    ["alpha.example", "beta.example", "gamma.example"]
);
assert.equal(
    rows.some(x => x.title === "River flooding threatens nearby suburb"),
    true,
    "similar headline remains separate"
);

// A repeated title on one publisher is not presented as multi-source.
const onePublisher = Array.from(ctx.parseNews({
    articles:[
        {
            title:"Heat wave continues",
            domain:"solo.example",
            sourcecountry:"US",
            language:"English",
            seendate:"20261031T110000Z",
            url:"https://solo.example/1"
        },
        {
            title:"Heat wave continues!",
            domain:"solo.example",
            sourcecountry:"US",
            language:"English",
            seendate:"20261031T111000Z",
            url:"https://solo.example/2"
        }
    ]
}));
assert.equal(onePublisher.length, 1);
assert.equal(onePublisher[0].sourceGroup.sourceCount, 1);
assert.equal(onePublisher[0].sourceGroup.multiSource, false);

const ui = read("widgets/weather/StationDiscovery.qml");
assert.match(ui, /EXACT HEADLINE GROUP \/\/ /);
assert.match(ui, /modelData\.sourceGroup\.sourceCount/);
assert.match(ui, /modelData\.sourceGroup\.domains\.join\("\ \/ "\)/);
assert.match(ui, /modelData\.sourceGroup\.countries\.join\("\ \/ "\)/);
assert.match(ui, /EXACT-HEADLINE SOURCE GROUPS", state:"CONNECTED"/);
assert.match(ui, /CONSERVATIVE STORY FAMILIES", state:"CONNECTED"/);
assert.match(ui, /SEMANTIC \/ EMBEDDING DOSSIERS", state:"NOT WIRED"/);
assert.match(ui, /NOT FUZZY STORY CLUSTERING/);

const source = read("services/weather/StationDiscoveryPolicy.js");
assert.doesNotMatch(
    source,
    /Levenshtein|Jaro|embedding|cosine|editDistance|fuzzyMatch/i
);
assert.match(
    source,
    /key\.length < 12/
);
assert.match(
    source,
    /group\.sourceCount = group\.domains\.length/
);

console.log("Weather NEWS exact-headline multi-source comparison: PASS");
