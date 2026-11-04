#!/usr/bin/env node
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname,"../..");
const read = rel => fs.readFileSync(path.join(root,rel),"utf8");
const policySource = read("services/weather/StationPublisherRssPolicy.js");
const ctx = {};
vm.runInNewContext(policySource.replace(/^\.pragma library\s*/m,""),ctx);
assert.equal(ctx.validId("bbc-world"),true);
assert.equal(ctx.validId("al-jazeera-english"),true);
assert.equal(ctx.validId("https://example.org"),false);
assert.equal(ctx.publisher("bbc-world"),"BBC WORLD");
assert.equal(ctx.publisher("al-jazeera-english"),"AL JAZEERA ENGLISH");
const t=1793740000000;
assert.equal(ctx.reserve("bbc-world",t),true);
assert.equal(ctx.waitMs("bbc-world",t+5000),55000);
assert.equal(ctx.reserve("bbc-world",t+1000),false);
assert.equal(ctx.waitMs("al-jazeera-english",t+5000),0,
    "BBC request must not throttle Al Jazeera");
assert.equal(ctx.reserve("al-jazeera-english",t+5000),true);
assert.equal(ctx.waitMs("al-jazeera-english",t+10000),55000);
assert.equal(ctx.store("bbc-world",[{title:"BBC only"}],t+20000),true);
assert.equal(ctx.store("al-jazeera-english",[{title:"Al Jazeera only"}],t+25000),true);
assert.equal(ctx.snapshot("bbc-world").rows[0].title,"BBC only");
assert.equal(ctx.snapshot("al-jazeera-english").rows[0].title,"Al Jazeera only");
const copy=ctx.snapshot("bbc-world");
copy.rows.push({title:"mutated locally"});
assert.equal(ctx.snapshot("bbc-world").rows.length,1);
const backwards=t+25000-3600000;
assert.equal(ctx.waitMs("bbc-world",backwards),35000,
    "backward host-time change should preserve BBC remaining wait");
assert.equal(ctx.waitMs("al-jazeera-english",backwards),40000,
    "Al Jazeera should independently preserve its remaining wait");
assert.equal(ctx.reserve("bbc-world",backwards+34999),false);
assert.equal(ctx.reserve("bbc-world",backwards+35000),true);
assert.equal(ctx.reserve("al-jazeera-english",backwards+39999),false);
assert.equal(ctx.reserve("al-jazeera-english",backwards+40000),true);
assert.equal(ctx.reserve("bad",backwards+40000),false);
assert.equal(ctx.store("bad",[{title:"X"}],backwards+40000),false);

// Integration must not introduce another GDELT owner or browser yank.
const service=read("services/weather/StationPublisherRssService.qml");
const pane=read("widgets/weather/StationPublisherFeeds.qml");
const discovery=read("widgets/weather/StationDiscovery.qml");
const hub=read("widgets/weather/StationNewsHub.qml");
const parser=read("scripts/weather/station_publisher_rss.py");
assert.match(service,/RssPolicy\.reserve\(feedId, now\)/);
assert.match(service,/Quickshell\.configDir \+ "\/scripts\/weather\/station_publisher_rss\.py"/);
assert.match(service,/feedId\s*\]/);
assert.match(service,/onStreamFinished: rss\.acceptResponse/);
assert.match(service,/Component\.onCompleted: restoreLastGood\(\)/);
assert.match(service,/retryWaitSeconds === 0/);
assert.match(service,/rows = RssPolicy\.snapshot\(feedId\)\.rows/);
assert.equal((service.match(/\bProcess\s*\{/g)||[]).length,1);
assert.equal((service.match(/\bTimer\s*\{/g)||[]).length,1);
assert.doesNotMatch(service,/running: true|onTriggered:.*request\(/);
assert.match(pane,/feedId: "bbc-world"/);
assert.match(pane,/feedId: "al-jazeera-english"/);
assert.match(pane,/backend\.request\(\)/);
assert.match(pane,/publisherFeeds\.headlineSelected\(modelData\)/);
assert.match(pane,/SEPARATE FROM GDELT/);
assert.doesNotMatch(pane,/Qt\.openUrlExternally|WebEngine|autoplay/i);
assert.match(discovery,/StationPublisherFeeds\s*\{/);
assert.match(discovery,/onHeadlineSelected: function\(row\)\s*\{\s*stationDiscovery\.openRow\(row\)/);
assert.match(hub,/StationDiscovery\s*\{/);
assert.match(parser,/"bbc-world"/);
assert.match(parser,/"al-jazeera-english"/);
const discoverySource=read("services/weather/StationDiscoveryService.qml");
assert.match(discoverySource,/api\.gdeltproject\.org/);
assert.doesNotMatch(service,/gdeltproject|StationDiscoveryService/);

console.log("Weather M9 publisher cache isolation and in-station source control: PASS");
