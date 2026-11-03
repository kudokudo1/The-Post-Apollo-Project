"use strict";

const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const nav=read("widgets/weather/StationSubjectNavigationPolicy.js");
const preview=read("widgets/weather/StationSubjectNavigationPreviewPolicy.js");
const toolPolicy=read("widgets/weather/StationToolsSubjectPanelPolicy.js");
const healthPolicy=read("widgets/weather/StationSourceHealthPolicy.js");
const toolPane=read("widgets/weather/StationToolsSubjectPane.qml");
const home=read("widgets/weather/StationHome.qml");
const space=read("widgets/weather/StationSpace.qml");
const navigator=read("widgets/weather/StationSubjectNavigator.qml");
const station=read("widgets/weather/WeatherStationW.qml");
const env=vm.createContext({}),policy=vm.createContext({}),health=vm.createContext({});
vm.runInContext(nav.replace(/^\.pragma library\s*$/m,""),env);
vm.runInContext(preview.replace(/^\.pragma library\s*$/m,""),env);
vm.runInContext(toolPolicy.replace(/^\.pragma library\s*$/m,""),policy);
vm.runInContext(healthPolicy.replace(/^\.pragma library\s*$/m,""),health);
const plain=x=>JSON.parse(JSON.stringify(x));
const reviewed=[
  ["home-source-health","tools/sources/health"],
  ["space-field-times","tools/sources/provenance"],
  ["station-frame-cache","tools/storage/frames"],
  ["station-persistent-cache","tools/storage/cache"],
  ["station-live-history","tools/storage/history"],
  ["station-event-store","tools/storage/events"]
];

test("exact six M28-I source controls have existing native TOOLS owners",()=>{
  assert.equal(reviewed.length,6);
  const actual=Object.keys(env.WIRED_IN_SUBJECTS).filter(id=>env.WIRED_IN_SUBJECTS[id]==="M28-I");
  assert.deepEqual(actual.sort(),reviewed.map(x=>x[0]).sort());
  for(const [id,route] of reviewed){
    assert.equal(env.PANELS[id],route,id+" preserves original destination");
    const leaf=env.findRoute(route);
    assert.ok(leaf && leaf.subject==="tools" && !leaf.group,id+" known leaf");
    assert.ok(policy.routeInfo(route),id+" actual native panel");
  }
  assert.equal(Object.keys(env.PANELS).length,103);
  assert.equal(Object.keys(env.WIRED_IN_SUBJECTS).length,89);
  assert.equal(103-89,14);
  assert.deepEqual(plain(env.remainingSourcePagesForPath("tools/storage",env.PANELS)),[]);
  assert.deepEqual(plain(env.remainingSourcePagesForPath("tools/sources/provenance",env.PANELS)),[]);
  assert.deepEqual(plain(env.nativeDestinationsForPath("tools/storage",env.PANELS).map(x=>x.path)),
    ["tools/storage/cache","tools/storage/events","tools/storage/frames","tools/storage/history"]);
});

test("NOAA four original SPACE clocks are real sample timestamps, not source-catalog descriptions",()=>{
  const now=Date.parse("2026-11-03T12:00:00Z");
  const receipt=new Date(now-60000);
  const spaceData={
    kpReady:true,kpTime:"2026-11-03T04:00:00Z",kpLastUpdated:receipt,
    solarWindReady:true,solarWindTime:"2026-11-03T11:55:00Z",solarWindLastUpdated:receipt,
    magneticFieldReady:true,magneticFieldTime:"2026-11-03T11:48:00Z",magneticFieldLastUpdated:receipt,
    solarFluxReady:true,solarFluxTime:"2026-11-03T03:00:00Z",solarFluxLastUpdated:receipt
  };
  const data=plain(policy.fieldTimeRows(spaceData,now));
  assert.deepEqual(data.map(x=>x.id),["kp","solar-wind","imf","solar-flux"]);
  assert.deepEqual(data.map(x=>x.title),["KP SAMPLE","WIND SAMPLE","IMF SAMPLE","FLUX SAMPLE"]);
  assert.deepEqual(data.map(x=>x.status),["STALE","CURRENT","CURRENT","CURRENT"]);
  assert.deepEqual(data.map(x=>x.sampleAgeMinutes),[480,5,12,540]);
  assert.deepEqual(data.map(x=>x.staleAfterMinutes),[360,45,45,2160]);
  for(const row of data){
    assert.equal(row.receiptClock,"2026-11-03T11:59:00.000Z",
      "recent receipt never repairs an older NOAA sample");
    assert.ok(row.sampleClock.startsWith("2026-11-03T"),row.id);
  }
  assert.match(space,/text: "KP SAMPLE"/);
  assert.match(space,/text: "WIND SAMPLE"/);
  assert.match(space,/text: "IMF SAMPLE"/);
  assert.match(space,/text: "FLUX SAMPLE"/);
  assert.match(toolPane,/ToolsPolicy\.fieldTimeRows\(spaceService,runtimeNowMs\)/);
  assert.match(toolPane,/model: toolsPane\.fieldTimeRows/);
  assert.match(toolPane,/title: "NOAA \/\/ FIELD SAMPLE CLOCKS"/);
  assert.match(toolPane,/LAST RECEIPT \/\/ /);
  assert.match(toolPane,/PROVIDER SAMPLE \/\/ /);
});

test("missing, malformed, future or not-ready sample clocks never fake CURRENT",()=>{
  const now=Date.parse("2026-11-03T12:00:00Z");
  const empty=plain(policy.fieldTimeRows(null,now));
  assert.equal(empty.length,4);
  assert.ok(empty.every(x=>x.status==="NOT READY"));
  assert.ok(empty.every(x=>x.sampleClock==="UNAVAILABLE"&&x.receiptClock==="UNAVAILABLE"));
  const future=plain(policy.fieldTimeRows({
    kpReady:true,kpTime:"2026-11-04T12:00:00Z",
    solarWindReady:true,solarWindTime:"garbage",
    magneticFieldReady:true,magneticFieldTime:"",
    solarFluxReady:false,solarFluxTime:"2026-11-03T10:00:00Z"
  },now));
  assert.deepEqual(future.map(x=>x.status),
    ["TIME UNVERIFIED","TIME UNVERIFIED","NO SAMPLE","NOT READY"]);
  assert.ok(future.every(x=>x.sampleAgeMinutes<0 || x.status!=="TIME UNVERIFIED"));
});

test("HOME source health reuses original six-source policy and shared live readers",()=>{
  assert.match(home,/SourceHealth\.buildCoreSources\(/);
  assert.match(toolPane,/SourceHealth\.buildCoreSources\(/);
  assert.match(toolPane,/ToolsPolicy\.sourceInput\(weatherService,spaceService,runtimeNowMs\)/);
  assert.match(toolPane,/model: toolsPane\.healthRows/);
  assert.equal(policy.shows("tools/sources/health","health"),true);
  assert.equal(policy.shows("tools/sources/provenance","provenance"),true);
  assert.equal(policy.shows("tools/sources/health","provenance"),false);
  const input=policy.sourceInput(null,null,Date.parse("2026-11-03T12:00:00Z"));
  const sources=plain(health.buildCoreSources(input));
  assert.deepEqual(sources.map(x=>x.id),
    ["weather","aqi","kp","solar-wind","imf","solar-flux"]);
  assert.ok(sources.every(x=>x.state==="OFFLINE"));
});

test("cache, history, event, dossier and FRAME CONTRACT stay read-only with original owners",()=>{
  const cache={storageState:"ready",revision:2,document:{records:{a:{},b:{}}}},
        history={storageState:"ready",revision:3,document:{series:{k:{}}}},
        events={storageState:"empty",revision:4,eventCount:()=>1},
        dossiers={storageState:"ready",revision:5};
  const rows=plain(policy.storageRows(cache,history,events,dossiers,42));
  assert.deepEqual(rows.map(r=>r.id),["cache","history","events","dossiers"]);
  assert.deepEqual(rows.map(r=>r.revision),[2,3,4,5]);
  assert.deepEqual(rows.map(r=>r.count),[2,1,1,-1]);
  assert.deepEqual(plain(policy.storageRowsFor("tools/storage/events",rows).map(x=>x.id)),
    ["events","dossiers"]);
  assert.deepEqual(plain(policy.storageRowsFor("tools/storage/frames",rows)),[],
    "FRAME is a retention catalogue, not actual persistent frame records");
  assert.match(toolPane,/ToolsPolicy\.frameSources\(sourceCatalog\)/);
  assert.match(toolPane,/NO SEPARATE PERSISTENT FRAME ARCHIVE STORE IS CONNECTED/);
  assert.match(toolPane,/eventArchiveStore: null/);
  assert.match(toolPane,/dossierArchiveStore: null/);
  assert.match(station,/eventArchiveStore: weatherStation\.eventArchiveStore/);
  assert.match(station,/dossierArchiveStore: weatherStation\.dossierArchiveStore/);
  for(const forbidden of ["Process {","FileView {","XMLHttpRequest","WeatherServices.","StationTerminal {"])
    assert.ok(!toolPane.includes(forbidden),"no second fetcher, writer or Kitty actor: "+forbidden);
  for(const forbidden of ["Process {","FileView {","XMLHttpRequest"])
    assert.ok(!toolPolicy.includes(forbidden),"TOOLS policy has no effects: "+forbidden);
});

test("still-pending source racks, HOME semantics and WATCH hosting remain visibly unresolved",()=>{
  for(const id of [
    "home-quick-conditions","home-aqi-humidity","home-aqi-wind",
    "home-space-weather","ground-source","map-source-rack",
    "station-source-badge","home-aqi-humidity","home-aqi-wind"
  ])assert.equal(env.WIRED_IN_SUBJECTS[id],undefined,id+" not silently accepted");
  assert.ok(env.sourcePagesForPath("media/watch",env.PANELS).length>0,
    "original NEWS catalog source provenance remains");
  assert.deepEqual(plain(env.remainingSourcePagesForPath("media/watch",env.PANELS)),[],
    "M28-J classifies the catalog, not video playback");
  assert.match(navigator,/model: browser\.nativeDestinations/);
  assert.match(navigator,/model: browser\.classicSources/);
  assert.deepEqual(plain(env.nativeDestinationsForPath("../tools",env.PANELS)),[]);
});
