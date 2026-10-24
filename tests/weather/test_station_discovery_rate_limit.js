#!/usr/bin/env node
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.resolve(__dirname, "../..");
const read = rel => fs.readFileSync(path.join(root, rel), "utf8");
const ctx = {};
vm.runInNewContext(read("services/weather/StationDiscoveryPolicy.js")
    .replace(/^\.pragma library\s*/m, ""), ctx);

// The operator's real provider response: HTTP429 body is plain text,
// not a JSON article list, and the former curl -f discarded it.
const throttle = ctx.splitHttpResponse(
    "Please limit requests to one every 5 seconds.\n__POST_APOLLO_HTTP__:429");
assert.equal(throttle.status, 429);
assert.match(throttle.body, /one every 5 seconds/);
const ok = ctx.splitHttpResponse(
    '{"articles":[{"title":"Test"}]}\n__POST_APOLLO_HTTP__:200');
assert.equal(ok.status, 200);
assert.deepEqual(JSON.parse(ok.body), {articles:[{title:"Test"}]});
assert.equal(ctx.splitHttpResponse("<html>oops</html>").status, 0);
assert.equal(ctx.splitHttpResponse("x\n__POST_APOLLO_HTTP__:wat").status, 0);

// One shared request gate survives unmount/remount of the NEWS QML component
// while pragma-library state remains in this Quickshell engine.
const t = 1780000000000;
assert.equal(ctx.reserveNewsRequest(t), true);
assert.equal(ctx.reserveNewsRequest(t + 1000), false);
assert.equal(ctx.newsWaitMs(t + 1000), 29000);
assert.equal(ctx.reserveNewsRequest(t + 30000), true);
assert.equal(ctx.recordNewsThrottle(t + 31000), 300000);
assert.equal(ctx.newsManualRetryRequired(), true);
assert.equal(ctx.newsThrottleCount(), 1);
assert.equal(ctx.newsThrottled(t + 32000), true);
assert.equal(ctx.reserveNewsRequest(t + 32000), false);
assert.equal(ctx.newsWaitMs(t + 32000), 299000);
assert.equal(ctx.reserveNewsRequest(t + 330000), false);
assert.equal(ctx.reserveNewsRequest(t + 331000), true);
assert.equal(ctx.newsThrottled(t + 331000), false);
// A second 429 grows the delay to 15m; further failures do not hammer
// the provider. All retries remain explicit and button-driven.
assert.equal(ctx.recordNewsThrottle(t + 332000), 900000);
assert.equal(ctx.newsThrottleCount(), 2);
assert.equal(ctx.newsWaitMs(t + 333000), 899000);
assert.equal(ctx.reserveNewsRequest(t + 1231000), false);
assert.equal(ctx.reserveNewsRequest(t + 1232000), true);
assert.equal(ctx.newsThrottled(t + 1232000), false);

// The last successful headlines persist across page recreation but never
// pretend to include article text, and are not stored on disk.
const records=[{title:"Provider headline",url:"https://example.org/a"}];
ctx.storeNewsRows(records,t+1233000);
const snapshot=ctx.cachedNewsRows();
assert.equal(snapshot.updatedAtMs,t+1233000);
assert.equal(ctx.newsManualRetryRequired(), false);
assert.equal(ctx.newsThrottleCount(), 0);
assert.equal(ctx.newsWaitMs(t+1233001), 899999);
assert.equal(ctx.reserveNewsRequest(t+1263000), false);
assert.equal(ctx.reserveNewsRequest(t+2133000), true);
assert.equal(snapshot.rows.length,1);
assert.equal(snapshot.rows[0].title,"Provider headline");
assert.equal(snapshot.rows[0].body,undefined);
snapshot.rows.push({title:"local change"});
assert.equal(ctx.cachedNewsRows().rows.length,1);

const service=read("services/weather/StationDiscoveryService.qml");
const ui=read("widgets/weather/StationDiscovery.qml");
const shell=read("widgets/weather/WeatherStationW.qml");
const workflow=read(".github/workflows/weather-teardown-contracts.yml");
assert.match(service,/DiscoveryPolicy\.reserveNewsRequest\(now\)/);
assert.match(service,/DiscoveryPolicy\.recordNewsThrottle\(now\)/);
assert.match(service,/DiscoveryPolicy\.cachedNewsRows\(\)/);
assert.match(service,/DiscoveryPolicy\.storeNewsRows\(parsed, now\)/);
assert.match(service,/property bool usingCache: false/);
assert.match(service,/received\.status === 429/);
assert.match(service,/received\.status < 200 \|\| received\.status >= 300/);
assert.match(service,/sourceClockMs = now/);
assert.match(service,/sourceClockMs = Date\.now\(\)/);
assert.match(service,/interval: 1000/);
assert.match(service,/running: discovery\.active && discovery\.domain === "news"/);
assert.doesNotMatch(service,/running: discovery\.active && discovery\.domain === "news"\s*&& discovery\.retryWaitSeconds/);
assert.match(service,/!manual && DiscoveryPolicy\.newsManualRetryRequired\(\)/);
assert.match(service,/domain === "news" && DiscoveryPolicy\.newsManualRetryRequired\(\)/);
assert.match(service,/interval: 900000/);
assert.match(service,/onTriggered: discovery\.refresh\(\)/);
assert.doesNotMatch(service,/["']-fsSL["']/);
assert.match(service,/__POST_APOLLO_HTTP__/);
assert.match(ui,/label: "RETRY NEWS"/);
assert.match(ui,/onClicked: source\.refresh\(true\)/);
assert.match(ui,/function retryClock\(value\)/);
assert.match(ui,/EARLIEST RETRY IN/);
assert.match(ui,/RETRY MAY STILL BE THROTTLED/);
assert.match(ui,/available: source\.canRetry/);
assert.match(ui,/state:"ENDPOINT CONFIGURED"/);
assert.match(ui,/NEWS CACHED/);
assert.match(ui,/NEWS RECEIVED/);
assert.match(shell,/id: weatherContentLoader/);
assert.match(shell,/newsSourceItem\.feedBadge/);
assert.match(shell,/newsSourceItem\.feedBadgeColor/);
assert.match(workflow,/node tests\/weather\/test_station_discovery_rate_limit\.js/);
console.log("Weather NEWS GDELT 429 and cache contracts: PASS");
