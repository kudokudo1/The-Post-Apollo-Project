#!/usr/bin/env node
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
function read(p) { return fs.readFileSync(path.join(root, p), "utf8"); }
const source = read("widgets/weather/StationViewerPolicy.js")
    .replace(/^\.pragma library\s*/m, "");
const policy = {};
vm.runInNewContext(source, policy);
assert.equal(typeof policy.safeArticleUrl, "function");
assert.equal(typeof policy.normalizeNews, "function");
assert.equal(typeof policy.articleHost, "function");

const article = policy.normalizeNews({
    title: "  Example \n weather report   ",
    detail: "example.org // US",
    time: "10-24 19:12 UTC",
    url: "https://www.example.org/weather/2026"
});
assert.equal(article.title, "Example weather report");
assert.equal(article.source, "example.org // US");
assert.equal(article.time, "10-24 19:12 UTC");
assert.equal(article.kind, "news");
assert.equal(article.url, "https://www.example.org/weather/2026");
assert.equal(policy.articleHost(article.url), "example.org");

assert.equal(policy.normalizeNews({title:"  "}), null);
const noBody = policy.normalizeNews({
    title: "No original article URL",
    detail: "Example",
    url: ""
});
assert.equal(noBody.url, "");
assert.equal(noBody.body, undefined, "a headline is not fetched article text");

// All foreign URLs are data. Never accept JS/file, credentialed host,
// plain HTTP, localhost, raw IP or malformed/unbounded URLs as web sources.
for (const unsafe of [
    "javascript:alert(1)", "file:///etc/passwd",
    "http://example.org/news", "https://localhost/news",
    "https://private.local/news", "https://127.0.0.1/report",
    "https://example.org@evil.org/report",
    "https://user:pass@example.org/report",
    "https://example.org:8080/report",
    "https://example.org\\@evil.org/report",
    "https://example.org/\nmalicious",
    "https://example.org/" + "x".repeat(2100),
    undefined, null
]) {
    assert.equal(policy.safeArticleUrl(unsafe), "", String(unsafe).slice(0, 90));
}
assert.equal(policy.safeArticleUrl(" https://example.org/?q=weather "),
             "https://example.org/?q=weather");
assert.equal(policy.articleHost("https://example.org/post"), "example.org");

const discovery = read("widgets/weather/StationDiscovery.qml");
const viewer = read("widgets/weather/StationViewerHost.qml");
const web = read("widgets/weather/StationNewsWebView.qml");
const station = read("widgets/weather/WeatherStationW.qml");

// NEWS rows route into the internal host, not direct external navigation.
assert.match(discovery, /if \(domain === "news"\)[\s\S]*?ViewerPolicy\.normalizeNews\(row\)[\s\S]*?viewerOpen = true;/);
assert.match(discovery, /onClicked: stationDiscovery\.openRow\(modelData\)/);
assert.match(discovery, /active: stationDiscovery\.viewerOpen/);
assert.match(discovery, /onBackRequested: stationDiscovery\.closeViewer\(\)/);
assert.match(discovery, /onStationOpenChanged: \{ if \(!stationOpen\) closeViewer\(\); \}/);
assert.doesNotMatch(discovery, /onClicked:\s*\{\s*if \(modelData\.url/);
assert.match(discovery, /visible: !stationDiscovery\.viewerOpen/);
assert.match(viewer, /signal backRequested\(\)/);
assert.match(viewer, /label: "◂  BACK"/);
assert.match(viewer, /label: "READER DISABLED"/);
assert.match(viewer, /available: false/);
assert.match(viewer, /INTERNAL ARTICLE RENDERER \/\/ SAFE MODE/);
assert.match(viewer, /WEBENGINE DISABLED \/\/ NO BROWSER PROCESS LAUNCHED/);
assert.match(viewer, /The headline, publisher and time/);
assert.doesNotMatch(viewer, /\bimport\s+QtWebEngine|StationNewsWebView\.qml|webLoader|webRequested/);
assert.doesNotMatch(viewer, /\bLoader\s*\{|\bProcess\s*\{|Qt\.openUrlExternally/);

// Quickshell 0.3.2 crash evidence: SIGABRT in QtWebEngineCore constructor
// after Qt app was initialized with argc=0. NO NEWS-facing QML component
// may instantiate the optional WebEngine implementation until another
// process owns rendering and the operator authorizes its Stage Director path.
const channel = read("widgets/weather/StationChannelScreen.qml");
const hub = read("widgets/weather/StationNewsHub.qml");
assert.match(channel, /signal closeRequested\(\)/);
assert.match(channel, /label: "×  CLOSE"/);
assert.match(channel, /label: "MUTE: ON"/);
assert.match(channel, /available: channelScreen\.playbackAvailable/);
assert.match(channel, /readonly property bool playbackAvailable: false/);
assert.match(channel, /NEWS VIEWER \/\/ SAFE MODE/);
assert.match(channel, /CRASH PROTECTION/);
assert.match(channel, /onClicked: channelScreen\.closeRequested\(\)/);
assert.doesNotMatch(channel, /\bLoader\s*\{|StationNewsWebView\.qml|import QtWebEngine/);
assert.doesNotMatch(channel, /\bProcess\s*\{|Qt\.openUrlExternally|swaymsg|command:[^\n]*kitty/);
assert.match(hub, /StationChannelScreen\s*\{/);
assert.match(hub, /onCloseRequested: stationNewsHub\.closeViewer\(\)/);
assert.match(hub, /label: "WATCH IN STATION"/);
assert.match(hub, /label: "MUTE: ON"/);
assert.match(hub, /available: false/);
assert.doesNotMatch(hub, /Qt\.openUrlExternally|StationNewsWebView\.qml/);
assert.doesNotMatch(station, /import QtWebEngine/);
// Keep the orphaned implementation on disk for a *future* authorized
// host experiment, but ensure it is unreachable from both NEWS pathways.
const web = read("widgets/weather/StationNewsWebView.qml");
assert.match(web, /^import QtWebEngine/m);
const discovery = read("widgets/weather/StationDiscovery.qml");
assert.match(discovery, /StationViewerHost\s*\{/);
assert.match(discovery, /onBackRequested: stationDiscovery\.closeViewer\(\)/);
assert.match(discovery, /viewerOpen = true/);
assert.doesNotMatch(discovery, /StationNewsWebView\.qml|import QtWebEngine/);
assert.match(hub, /StationDiscovery\s*\{[\s\S]*?domain: "news"/);
assert.doesNotMatch(hub, /import QtWebEngine/);
assert.doesNotMatch(channel + hub + viewer + discovery, /source:\s*["']StationNewsWebView\.qml/);

console.log("Weather Station NEWS internal viewer contracts: PASS");
