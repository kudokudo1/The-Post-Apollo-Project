"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const navSource=read("widgets/weather/StationSubjectNavigationPolicy.js");
const policySource=read("widgets/weather/StationToolsSubjectPanelPolicy.js");
const healthSource=read("widgets/weather/StationSourceHealthPolicy.js");
const runtimeSource=read("services/weather/WeatherRuntimePolicy.js");
const pane=read("widgets/weather/StationToolsSubjectPane.qml");
const browser=read("widgets/weather/StationSubjectNavigator.qml");
const station=read("widgets/weather/WeatherStationW.qml");
const terminal=read("widgets/weather/StationTerminal.qml");
const nav=vm.createContext({});
const tools=vm.createContext({});
const health=vm.createContext({});
const runtime=vm.createContext({});
for(const [s,ctx] of [
  [navSource,nav],[policySource,tools],
  [healthSource,health],[runtimeSource,runtime]
]) vm.runInContext(s.replace(/^\.pragma library\s*$/m,""),ctx);
const plain=x=>JSON.parse(JSON.stringify(x));

test("eleven exact TOOLS routes are real descendants of the six-subject tree", () => {
  const routes=Object.keys(tools.ROUTES);
  assert.equal(tools.FORMAT,"post-apollo.weather.tools-panels.t1.v1");
  assert.equal(routes.length,11);
  assert.equal(new Set(routes).size,11);
  const kinds={overview:0,terminal:0,sources:0,storage:0,settings:0};
  for(const route of routes) {
    const match=nav.findRoute(route);
    assert.ok(match,"missing "+route);
    assert.equal(match.subject,"tools",route);
    const kind=tools.kindForRoute(route);
    assert.ok(kind in kinds,route);
    kinds[kind]++;
    assert.ok(tools.titleFor(route).length>=12,route);
  }
  assert.deepEqual(plain(kinds),{overview:1,terminal:2,sources:2,storage:4,settings:2});
  for(const bad of ["tools","tools/terminal","tools/secret",
    "weather/overview","cosmos/overview","earth/overview",
    "media/overview","magick/overview"])
    assert.equal(tools.kindForRoute(bad),"",bad);
});

test("TOOLS terminal routes safely hand off to the original CLASSIC Kitty controller", () => {
  assert.equal(tools.legacyTerminalPage("tools/terminal/star-map"),"terminal");
  assert.equal(tools.legacyTerminalPage("tools/terminal/consoles"),"home");
  assert.equal(tools.legacyTerminalPage("tools/storage/cache"),"");
  assert.match(tools.terminalInstructions("tools/terminal/star-map"),/ORIGINAL HEADER/);
  assert.match(tools.terminalInstructions("tools/terminal/consoles"),/BASH/);
  assert.match(pane,/signal legacyPageRequested\(string pageId\)/);
  assert.match(pane,/onClicked:\s*\{/);
  assert.match(pane,/toolsPane\.legacyPageRequested\(toolsPane\.terminalTarget\)/);
  assert.match(browser,/onLegacyPageRequested: function\(pageId\)/);
  assert.match(station,/weatherStation\.openLegacyFromSubject\(pageId\)/);
  assert.match(station,/function openLegacyFromSubject\(pageId\)/);
  assert.match(station,/function launchContextTerminal\(\)/);
  assert.match(terminal,/sessionMode === "terminal" \? "weather-screen"/);
  assert.match(terminal,/kittyActorConfirmed/);
  assert.match(terminal,/function closeTerminal\(\)/);
  assert.ok(!pane.includes("StationTerminal {"),"no second terminal");
});

test("six shared source-health rows reuse HOME's sample-age conventions", () => {
  const now=Date.parse("2026-11-03T07:00:00Z");
  const date=ms=>new Date(ms);
  const weather={
    ready:true,loading:false,lastUpdated:date(now-120000),errorText:"",
    aqiReady:true,aqiLoading:false,aqiLastUpdated:date(now-180000),
    aqiErrorText:""
  };
  const space={
    kpReady:true,kpLoading:false,kpLastUpdated:date(now-60000),
    kpTime:"2026-11-03T01:00:00Z",kpErrorText:"",
    solarWindReady:true,solarWindLoading:false,
    solarWindLastUpdated:date(now-60000),solarWindTime:"2026-11-03T06:55:00Z",
    solarWindErrorText:"",
    magneticFieldReady:true,magneticFieldLoading:false,
    magneticFieldLastUpdated:date(now-60000),
    magneticFieldTime:"2026-11-03T06:48:00Z",magneticFieldErrorText:"",
    solarFluxReady:true,solarFluxLoading:false,
    solarFluxLastUpdated:date(now-60000),
    solarFluxTime:"2026-11-03T00:00:00Z",solarFluxErrorText:""
  };
  const input=tools.sourceInput(weather,space,now);
  const rows=plain(health.buildCoreSources(input));
  assert.deepEqual(rows.map(r=>r.id),
    ["weather","aqi","kp","solar-wind","imf","solar-flux"]);
  assert.equal(rows[0].state,"LIVE");
  assert.equal(rows[1].state,"LIVE");
  assert.equal(rows[2].state,"STALE","old Kp sample despite new receive");
  assert.equal(rows[3].state,"LIVE");
  assert.equal(rows[4].state,"LIVE");
  assert.equal(rows[5].state,"LIVE");
  assert.equal(input.kp.sampleAgeMinutes,360);
  assert.equal(input.weather.staleAfterMinutes,20);
  assert.equal(input.solarWind.staleAfterMinutes,45);
  assert.equal(input.solarFlux.staleAfterMinutes,2160);
  const none=plain(health.buildCoreSources(tools.sourceInput(null,null,now)));
  assert.equal(none.length,6);
  assert.ok(none.every(x=>x.state==="OFFLINE"));
  assert.match(pane,/SourceHealth\.buildCoreSources\(/);
  assert.match(pane,/ToolsPolicy\.sourceInput\(weatherService,spaceService,runtimeNowMs\)/);
});

test("source provenance reuses all 37 catalogue specs without claiming 37 pollers", () => {
  const catalog=plain(runtime.sourceCatalog());
  assert.equal(catalog.length,37);
  assert.equal(new Set(catalog.map(x=>x.id)).size,37);
  assert.equal(catalog.filter(x=>x.owner==="WeatherService.qml").length>=3,true);
  assert.match(pane,/RuntimePolicy\.sourceCatalog\(\)/);
  assert.match(pane,/RuntimePolicy\.retentionLabel\(modelData\)/);
  assert.match(pane,/RuntimePolicy\.cadenceLabel\(modelData\)/);
  assert.match(pane,/NOT A COUNT OF DISTINCT POLLERS OR LIVE ONLINE FEEDS/);
  assert.equal(tools.shows("tools/sources/health","health"),true);
  assert.equal(tools.shows("tools/sources/provenance","provenance"),true);
  assert.equal(tools.shows("tools/overview","provenance"),false);
  assert.equal(tools.shows("tools/storage/history","provenance"),false);
});

test("cache/history/event/dossier status is actual read-only store data", () => {
  const snapshot={
    storageState:"ready",revision:3,errorCode:"",
    document:{records:{"weather-current":{}, "space-kp":{}}}
  };
  const history={
    storageState:"empty",revision:7,errorCode:"",
    document:{series:{"weather-current|a":{}}}
  };
  let counted=0;
  const archive={
    storageState:"ready",revision:9,errorCode:"",
    eventCount:function(now) {counted++;return now>0?5:0;}
  };
  const dossier={storageState:"ready",revision:4,errorCode:""};
  const rows=plain(tools.storageRows(snapshot,history,archive,dossier,1700000000000));
  assert.equal(rows.length,4);
  assert.deepEqual(rows.map(x=>x.id),["cache","history","events","dossiers"]);
  assert.deepEqual(rows.map(x=>x.revision),[3,7,9,4]);
  assert.deepEqual(rows.map(x=>x.count),[2,1,5,-1]);
  assert.equal(counted,1);
  assert.deepEqual(plain(tools.storageRowsFor("tools/storage/cache",rows).map(x=>x.id)),["cache"]);
  assert.deepEqual(plain(tools.storageRowsFor("tools/storage/history",rows).map(x=>x.id)),["history"]);
  assert.deepEqual(plain(tools.storageRowsFor("tools/storage/events",rows).map(x=>x.id)),["events","dossiers"]);
  assert.deepEqual(plain(tools.storageRowsFor("tools/overview",rows).map(x=>x.id)),
    ["cache","history","events","dossiers"]);
  assert.equal(tools.storageRowsFor("tools/storage/frames",rows).length,0);
  const offline=plain(tools.storageRows(null,null,null,null,1700000000000));
  assert.ok(offline.every(x=>x.state==="NOT CONNECTED"));
  assert.ok(offline.every(x=>x.count===-1));
  assert.match(pane,/persistentCacheStore: null/);
  assert.match(pane,/liveHistoryStore: null/);
  assert.match(pane,/eventArchiveStore: null/);
  assert.match(pane,/dossierArchiveStore: null/);
});

test("frame route is a retention-policy inventory rather than fake frame archive", () => {
  const catalog=plain(runtime.sourceCatalog());
  const frames=plain(tools.frameSources(catalog));
  assert.deepEqual(frames.map(x=>x.id).sort(),
    ["lightning","mrms-radar","rainviewer"]);
  assert.ok(frames.every(x=>x.retention==="FRAME_CACHE"));
  assert.match(pane,/NO SEPARATE PERSISTENT FRAME ARCHIVE STORE IS CONNECTED/);
  assert.match(pane,/toolsPane\.frameRows\.length/);
  assert.equal(tools.shows("tools/storage/frames","frames"),true);
  assert.equal(tools.shows("tools/storage/events","frames"),false);
});

test("location and display are observations/read-only, not settings mutations", () => {
  assert.equal(tools.locationLabel({latitude:"39.12345",longitude:"-76.76543"}),
    "39.123, -76.765 // CURRENT PROVIDER LOCATION");
  assert.equal(tools.locationLabel({latitude:"",longitude:""}),"LOCATION NOT PRESENT IN CURRENT RESPONSE");
  assert.equal(tools.locationLabel({latitude:"91",longitude:"0"}),"LOCATION UNAVAILABLE");
  assert.equal(tools.timezoneLabel({airQualityTimezone:"America/New_York"}),"America/New_York");
  assert.match(pane,/NOT YOUR DEVICE GPS FIX OR A USER-EDITED SAVED LOCATION/);
  assert.match(pane,/NO UNIFIED UNITS, TIMEZONE OR DISPLAY-PREFERENCE WRITER CONNECTED/);
  assert.equal(tools.shows("tools/settings/location","location"),true);
  assert.equal(tools.shows("tools/settings/display","display"),true);
  assert.equal(tools.shows("tools/settings/display","terminal"),false);
});

test("all previous subject panes, CLASSIC, runtime mask and terminal owner remain unchanged", () => {
  for(const name of ["Weather","Cosmos","Earth","Media","Magick","Tools"])
    assert.ok(browser.includes("Station"+name+"SubjectPane {"),name);
  assert.match(browser,/visible: browser\.visible && browser\.liveToolsKind !== ""/);
  assert.match(browser,/onLegacyPageRequested: function\(pageId\)/);
  assert.match(browser,/weatherService: browser\.weatherService/);
  assert.match(browser,/spaceService: browser\.spaceService/);
  assert.match(browser,/runtimeNowMs: browser\.runtimeNowMs/);
  assert.match(station,/subjectNavigator\.liveToolsKind !== ""/);
  assert.match(station,/TOOLS \/\/ SOURCE AND STORAGE STATUS/);
  assert.match(station,/active: !weatherStation\.subjectNavigationOpen/);
  assert.match(station,/terminalHoleActive:/);
  assert.match(station,/StationTerminal\s*\{/);
  assert.match(station,/onNewsMapRequested: function\(payload\)/);
  assert.match(station,/return "INDEX \/\/ PREVIEW"/);
});

test("TOOLS adds no new writer, provider service, network process or session", () => {
  for(const file of [pane,policySource]) {
    for(const forbidden of ["FileView {","Process {","WeatherServices.","XMLHttpRequest",
          "StationTerminal {","StationDiscovery {","append(","capture(","setText(",
          "swaymsg","curl ","openTerminal()","writeAdapter()"])
      assert.ok(!file.includes(forbidden),"unexpected effect in TOOLS "+forbidden);
  }
  assert.match(pane,/READ-ONLY CONTROL PLANE/);
  assert.match(pane,/NO DUPLICATE POLLERS, ARCHIVE WRITERS OR KITTY ACTORS/);
  assert.match(pane,/NeonScrollBar\s*\{/);
});
