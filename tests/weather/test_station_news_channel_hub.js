#!/usr/bin/env node
"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const c={};
vm.runInNewContext(read("widgets/weather/StationNewsCatalogPolicy.js")
    .replace(/^\.pragma library\s*/m,""),c);
const plain=x=>JSON.parse(JSON.stringify(x));
assert.deepEqual(plain(c.sections),[
    "LIVE","CONGRESS","REPORTS","COMPARE","CREATORS","SATIRE"]);
// The Python preflight must never acquire an unrelated/mismatched URL.
// Enforce exact source-ID, section and URL parity with the QML catalog.
const allowlist=JSON.parse(read("scripts/weather/news_viewer_allowlist.json"));
assert.equal(allowlist.schema,1);
assert.equal(allowlist.sources.length,c.channels.length);
const byId=new Map(allowlist.sources.map(x=>[x.id,x]));
for(const item of c.channels){
    const registered=byId.get(item.id);
    assert.ok(registered, "preflight missing "+item.id);
    assert.equal(registered.url,item.url);
    assert.equal(registered.section,item.section);
}
const ids=new Set(c.channels.map(v=>v.id));
assert.equal(ids.size,c.channels.length);
for(const item of c.channels){
    assert.ok(item.title && item.source && item.access && item.detail);
    assert.ok(c.sections.includes(item.section));
    assert.match(item.url,/^https:\/\/[a-z0-9.-]+\//i);
    assert.equal(c.find(item.id).id,item.id);
    const record=c.toViewerRecord(item);
    assert.equal(record.title,item.title);
    assert.equal(record.kind,"channel");
    assert.equal(record.source,item.source);
    assert.equal(record.time,item.access);
    assert.equal(record.url,item.url);
}
assert.equal(c.itemsFor("LIVE").length>=6,true);
assert.equal(c.find("cnn").access,"SUBSCRIPTION / TV LOGIN");
assert.equal(c.find("foxnews").access,"SUBSCRIPTION / TV LOGIN");
assert.match(c.find("livenow").detail,/not pay-TV FOX News/);
assert.equal(c.find("house").section,"CONGRESS");
assert.equal(c.find("senate").section,"CONGRESS");
assert.equal(c.find("cspan").section,"CONGRESS");
assert.equal(c.find("groundnews").section,"COMPARE");
assert.equal(c.find("jubilee").section,"CREATORS");
assert.equal(c.find("theonion").section,"SATIRE");
assert.match(c.find("theonion").detail,/Fictional satirical/);
const id="UC"+"a".repeat(22);
assert.equal(c.safeChannelId(id),id);
assert.equal(c.safeChannelId("https://www.youtube.com/channel/"+id),id);
assert.equal(c.safeChannelId("https://m.youtube.com/channel/"+id+"/"),id);
for(const bad of [
    "https://youtube.com/@jubilee",
    "https://www.youtube.com/watch?v=abcdefghijk",
    "https://bad.example/channel/"+id,
    id+";touch /tmp/z",
    "javascript:alert(1)",
    "../"+id,
    "UCinvalid",
    ""
]) assert.equal(c.safeChannelId(bad),"",bad);
assert.equal(c.normalizeCreator("  News | Fan  ",id).title,"News   Fan");
assert.equal(c.normalizeCreator("  ",id),null);
assert.equal(c.normalizeCreator("Name","/tmp/passwd"),null);
assert.equal(c.creatorRecord("My History",id).url,
    "https://www.youtube.com/channel/"+id);
assert.equal(c.creatorRecord("My History",id).channelId,id);
const hub=read("widgets/weather/StationNewsHub.qml");
const station=read("widgets/weather/WeatherStationW.qml");
const viewer=read("widgets/weather/StationViewerHost.qml");
const web=read("widgets/weather/StationNewsWebView.qml");
assert.match(hub,/FileView\s*\{/);
assert.match(hub,/JsonAdapter\s*\{/);
assert.match(hub,/Quickshell\.dataDir \+ "\/weather-news-creators\.json"/);
assert.match(hub,/creatorAdapter\.creatorEntries = current/);
assert.match(hub,/visibleItems/);
assert.match(hub,/function removeCreator\(channelId\)/);
assert.match(hub,/label: "ADD CREATOR"/);
assert.match(hub,/label: "UPLOADS"/);
assert.match(hub,/function checkUploads\(item\)/);
assert.match(hub,/station_youtube_feed\.py/);
assert.match(hub,/stationNewsHub\.inflightCreatorId/);
assert.match(hub,/active: stationNewsHub\.isReports && stationNewsHub\.stationOpen/);
assert.match(hub,/StationDiscovery\s*\{[\s\S]*?domain: "news"/);
assert.match(hub,/StationChannelScreen/);
assert.match(hub,/label: "WATCH IN STATION"/);
assert.match(hub,/label: "MUTE: ON"/);
assert.match(hub,/available: false/);
assert.match(hub,/VIDEO SAFE MODE/);
assert.doesNotMatch(hub,/onMuteToggled:/);
assert.match(hub,/onCloseRequested: stationNewsHub\.closeViewer\(\)/);
assert.match(hub,/muted: stationNewsHub\.channelMuted/);
assert.match(hub,/viewerOpen = false;[\s\S]*?channelMuted = true;/);
assert.doesNotMatch(hub,/label: "VIEW HERE"/);
assert.match(station,/id: newsViewComponent[\s\S]*?StationNewsHub/);
// The NEWS launch paths now deliberately cannot create QtWebEngine inside
// the host. The optional web file remains unreferenced, not "available".
assert.match(viewer,/READER DISABLED/);
assert.doesNotMatch(viewer,/StationNewsWebView\.qml|\bLoader\s*\{/);
assert.match(web,/audioMuted: !newsWeb\.audioAllowed/);
assert.match(web,/onNewWindowRequested/);
assert.match(web,/permission\.deny\(\)/);
assert.doesNotMatch(hub,/Qt\.openUrlExternally/);
assert.doesNotMatch(hub,/Process\s*\{[\s\S]*?curl/);
assert.doesNotMatch(station,/import QtWebEngine/);
console.log("Weather NEWS channel catalog / subscriptions: PASS");
