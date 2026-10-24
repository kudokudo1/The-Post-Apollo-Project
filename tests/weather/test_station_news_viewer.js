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
assert.match(viewer, /property bool webRequested: false/);
assert.match(viewer, /active: stationViewer\.webRequested && stationViewer\.canReadWeb/);
assert.match(viewer, /source: "StationNewsWebView\.qml"/);
assert.match(viewer, /WEBPAGE LOADS HERE ONLY WHEN REQUESTED/);
assert.match(viewer, /A headline is not the/);

// QtWebEngine is dynamically isolated from the shell, dock and NEWS list.
assert.match(web, /^import QtWebEngine/m);
assert.doesNotMatch(discovery, /import QtWebEngine/);
assert.doesNotMatch(viewer, /import QtWebEngine/);
assert.doesNotMatch(station, /import QtWebEngine/);
assert.match(web, /onNavigationRequested/);
assert.match(web, /ViewerPolicy\.articleHost\(target\)/);
assert.match(web, /request\.reject\(\)/);
assert.match(web, /onNewWindowRequested/);
assert.match(web, /onPermissionRequested/);
assert.match(web, /permission\.deny\(\)/);
assert.match(web, /property bool audioAllowed: false/);
assert.match(web, /audioMuted: !newsWeb.audioAllowed/);
assert.match(viewer, /label: stationViewer.audioAllowed \? "MUTE" : "ENABLE AUDIO"/);

const channel = read("widgets/weather/StationChannelScreen.qml");
// Direct channel view hides the surrounding NEWS rack and occupies the full
// viewing bay. It never silently launches an OS browser or a second terminal.
assert.match(channel, /signal closeRequested\(\)/);
assert.match(channel, /signal muteToggled\(\)/);
assert.match(channel, /label: "×  CLOSE"/);
assert.match(channel, /label: channelScreen\.muted \? "MUTE: ON" : "MUTE: OFF"/);
assert.match(channel, /active: channelScreen\.sourceUrl !== ""/);
assert.match(channel, /source: "StationNewsWebView\.qml"/);
assert.match(channel, /onLoaded:[\s\S]*?item\.articleUrl = channelScreen\.sourceUrl/);
assert.match(channel, /WEB RENDERER NOT AVAILABLE/);
assert.match(channel, /QtWebEngine could not load in this Quickshell runtime/);
assert.match(channel, /PLAYER REDIRECT BLOCKED/);
assert.match(channel, /PUBLISHER PAGE FAILED/);
assert.match(channel, /visible: channelScreen\.noRenderer/);
assert.match(channel, /channelLoader\.status === Loader\.Error/);
assert.match(channel, /channelScreen\.closeRequested\(\)/);
assert.doesNotMatch(channel, /Qt\.openUrlExternally|swaymsg|kitty|\bProcess\s*\{/);
assert.match(web, /property string loadError: ""/);
assert.match(web, /WebEngineView\.LoadFailedStatus/);
assert.match(web, /loadRequest\.errorString/);

// No new radio backend, terminal launcher or compositor control in this stage.
assert.doesNotMatch(viewer, /\bProcess\s*\{/);
assert.doesNotMatch(discovery, /\bProcess\s*\{/);
console.log("Weather Station NEWS internal viewer contracts: PASS");
