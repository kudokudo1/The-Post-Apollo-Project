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
const badgePolicy=read("widgets/weather/StationSubjectSourceBadgePolicy.js");
const toolsPane=read("widgets/weather/StationToolsSubjectPane.qml");
const discovery=read("widgets/weather/StationDiscovery.qml");
const earthPane=read("widgets/weather/StationEarthSubjectPane.qml");
const weatherPane=read("widgets/weather/StationWeatherSubjectPane.qml");
const surface=read("widgets/weather/StationWorkspaceSurface.qml");
const navigator=read("widgets/weather/StationSubjectNavigator.qml");
const station=read("widgets/weather/WeatherStationW.qml");
const ground=read("widgets/weather/StationGround.qml");
const env=vm.createContext({}),tools=vm.createContext({}),badge=vm.createContext({});
vm.runInContext(nav.replace(/^\.pragma library\s*$/m,""),env);
vm.runInContext(preview.replace(/^\.pragma library\s*$/m,""),env);
vm.runInContext(toolPolicy.replace(/^\.pragma library\s*$/m,""),tools);
vm.runInContext(badgePolicy.replace(/^\.pragma library\s*$/m,""),badge);
const plain=x=>JSON.parse(JSON.stringify(x));

test("M28-L closes only three exact original SOURCE ids without changing M0 provenance",()=>{
  const three=["ground-source","map-source-rack","station-source-badge"].sort();
  const audited=Object.keys(env.WIRED_IN_SUBJECTS)
    .filter(id=>env.WIRED_IN_SUBJECTS[id]==="M28-L").sort();
  assert.deepEqual(audited,three);
  assert.equal(Object.keys(env.PANELS).length,103);
  assert.equal(Object.keys(env.WIRED_IN_SUBJECTS).length,103);
  assert.deepEqual(Object.keys(env.PANELS).filter(id=>!env.WIRED_IN_SUBJECTS[id]),[]);
  for(const id of three){
    assert.equal(env.PANELS[id],"tools/sources/health",
      "M0 original provenance is preserved");
    assert.ok(env.findRoute(env.PANELS[id]));
  }
  assert.deepEqual(plain(env.remainingSourcePagesForPath("tools/sources/health",env.PANELS)),[]);
  assert.deepEqual(plain(env.sourcePagesForPath("tools/sources/health",env.PANELS)
    .map(x=>x.id)),["home","ground","map"],
    "original pages stay in M0 provenance despite no CLASSIC shortcut");
  const native=plain(env.nativeDestinationsForPath("tools/sources/health",env.PANELS));
  assert.deepEqual(native,[{
    path:"tools/sources/health",panels:4,
    milestones:["M28-I","M28-L"]
  }]);
});

test("the original GROUND source panel now has exact weather-fix and AQI provider time in TOOLS",()=>{
  const rows=plain(tools.groundSourceRows({
    latitude:"38.921832",longitude:"-76.758000",
    aqiReady:true,airQualitySourceTime:"2026-11-03T13:00:00Z"
  }));
  assert.deepEqual(rows.map(r=>r.id),["weather-fix","aqi-sample"]);
  assert.equal(rows[0].value,"LAT 38.921832   LON -76.758000");
  assert.equal(rows[1].value,"2026-11-03T13:00:00Z");
  assert.match(rows[0].detail,/NOT DEVICE GPS/);
  assert.match(rows[1].detail,/NOT NETWORK RECEIPT/);
  assert.deepEqual(plain(tools.groundSourceRows(null).map(r=>r.value)),
    ["LAT --   LON --","--"]);
  assert.deepEqual(plain(tools.groundSourceRows({
    latitude:"95",longitude:"600",aqiReady:false,
    airQualitySourceTime:"2026-11-03T13:00:00Z"
  }).map(r=>r.value)),["LAT --   LON --","--"]);
  assert.match(ground,/title: "ENVIRONMENT \/\/ SOURCE"/);
  assert.match(ground,/text: "LAT " \+ \(weatherService && weatherService\.latitude !== ""/);
  assert.match(ground,/text: ground\.aqiReady && weatherService\.airQualitySourceTime !== ""/);
  assert.match(toolsPane,/ToolsPolicy\.groundSourceRows\(weatherService\)/);
  assert.match(toolsPane,/model: toolsPane\.groundSourceRows/);
  assert.match(toolsPane,/title: "GROUND SOURCE \/\/ PROVIDER FIX \+ AQI SAMPLE"/);
  assert.match(toolsPane,/ToolsPolicy\.shows\(toolsPane\.subjectRoute,"health"\)/);
});

test("MAP source rack is opened in-place into both original provider-owned map views",()=>{
  assert.match(toolsPane,/label: "EARTH \/\/ EVENT SOURCE RACK"/);
  assert.match(toolsPane,/onClicked: toolsPane\.routeRequested\("earth\/maps\/overview"\)/);
  assert.match(toolsPane,/label: "WEATHER \/\/ RADAR SOURCE RACK"/);
  assert.match(toolsPane,/onClicked: toolsPane\.routeRequested\("weather\/maps"\)/);
  assert.match(toolsPane,/signal routeRequested\(string path\)/);
  assert.match(surface,/onRouteRequested: function\(path\) \{\s*surface\.routeRequested\(path\);/);
  assert.match(navigator,/onRouteRequested: function\(path\) \{\s*browser\.chooseRoute\(path\);/);
  assert.equal(env.findRoute("earth/maps/overview").subject,"earth");
  assert.equal(env.findRoute("weather/maps").subject,"weather");
  assert.match(discovery,/title: "SOURCE RACK \/\/ WHAT IS CONNECTED"/);
  assert.match(discovery,/model: stationDiscovery\.plannedSources/);
  assert.match(discovery,/if \(earthMapOnly\)/);
  assert.match(discovery,/if \(weatherMapOnly\)/);
  assert.match(discovery,/title: "SOURCE RACK \/\/ WHAT IS CONNECTED"/);
  assert.match(discovery,/visible: stationDiscovery\.domain === "map"/);
  for(const literal of [
    "NATURAL EARTH // SHARED LOCAL CARTOGRAPHY",
    "USGS // OBSERVED EARTHQUAKES M2.5+",
    "NASA EONET // NATURAL EVENTS",
    "GDACS // DISASTER EARLY WARNING",
    "NASA FIRMS // VIIRS HOTSPOTS",
    "NOAA HMS // SMOKE PLUMES",
    "NOAA MRMS // MANUAL RADAR",
    "RAINVIEWER // PAST RADAR FALLBACK"
  ])assert.ok(discovery.includes(literal),literal);
  assert.match(earthPane,/earthMapOnly: true/);
  assert.match(weatherPane,/weatherMapOnly: true/);
  assert.match(discovery,/NOAA HMS \+ SMOKE PLUMES|NOAA HMS \/\/ SMOKE PLUMES/);
  assert.match(discovery,/KEY REQUIRED/);
});

test("root badge uses real selected SUBJECTS runtimes and preserves original alert precedence",()=>{
  assert.match(station,/import "StationSubjectSourceBadgePolicy\.js" as SubjectSourceBadge/);
  assert.match(station,/SubjectSourceBadge\.badgeFor\(/);
  assert.match(station,/subjectNavigator\.currentPath,subjectNavigator\.indexOpen/);
  assert.match(station,/weatherRuntimeState,spaceRuntimeState,currentPageRuntimeSummary/);
  assert.match(station,/subjectNavigationOpen \? subjectNavigator\.liveMapRuntimeRows/);
  assert.match(station,/if \(subjectNavigationOpen\)\s*return subjectSourceBadge\.text;/);
  assert.match(station,/switch \(subjectSourceBadge\.tone\)/);
  assert.match(station,/if \(officialAlertSummary\.available\)/);
  assert.match(station,/text: weatherStation\.sourceStatusDisplay/);
  assert.match(station,/border\.color: weatherStation\.sourceStatusColor/);
  assert.match(station,/onTriggered: weatherStation\.sourceStatusClock\+\+/);
  assert.match(station,/active: !weatherStation\.subjectNavigationOpen/);
  assert.equal((station.match(/id: sourceStatusIndicator/g)||[]).length,1);
});

test("the subject map status is read from the ONE loaded original map, not a parallel collector",()=>{
  assert.match(earthPane,/readonly property var runtimeRows:/);
  assert.match(earthPane,/earthLoader\.item\.runtimeRows/);
  assert.match(weatherPane,/readonly property var runtimeRows:/);
  assert.match(weatherPane,/panelLoader\.item\.runtimeRows/);
  assert.match(surface,/readonly property var activeMapRuntimeRows:/);
  assert.match(surface,/earthSourcePane\.runtimeRows/);
  assert.match(surface,/weatherSourcePane\.runtimeRows/);
  assert.match(navigator,/readonly property var liveMapRuntimeRows:/);
  assert.match(navigator,/workspaceLoader\.item\.activeMapRuntimeRows/);
  assert.match(discovery,/readonly property var runtimeRows:/);
  assert.match(station,/RuntimePolicy\.summarizeRows\(currentPageRuntimeRows\)/);
  for(const source of [toolsPane,surface,navigator]){
    for(const forbidden of ["WeatherServices.","FileView {","Process {","XMLHttpRequest",
                             "StationTerminal {","swaymsg"])
      assert.ok(!source.includes(forbidden),source.slice(0,40)+" new owner "+forbidden);
  }
});

test("live weather, space, home and map badges distinguish freshness, cache and failures",()=>{
  const s=availability=>({availability});
  const get=(p,w,sp,map)=>plain(badge.badgeFor(p,false,s(w),s(sp),map||{}));
  assert.deepEqual(get("home/overview","LIVE","LIVE"),{text:"HOME // 2 LIVE",tone:"magenta"});
  assert.deepEqual(get("home/quick","LIVE","LIVE_STALE"),{text:"HOME // STALE",tone:"yellow"});
  assert.deepEqual(get("home/quick","LIVE","CACHE_STALE"),{text:"HOME // CACHE",tone:"blue"});
  assert.deepEqual(get("home/quick","LIVE","OFFLINE"),{text:"HOME // PARTIAL",tone:"yellow"});
  assert.deepEqual(get("weather/conditions/current","LIVE","OFFLINE"),{text:"WEATHER // LIVE",tone:"magenta"});
  assert.deepEqual(get("weather/conditions/current","CACHE_EXPIRED","LIVE"),{text:"WEATHER // CACHE EXPIRED",tone:"red"});
  assert.deepEqual(get("cosmos/space-weather/overview","WAITING","LIVE_STALE"),
    {text:"COSMOS // STALE",tone:"yellow"});
  assert.deepEqual(get("earth/maps/overview","LIVE","LIVE",{ready:3,cached:0}),
    {text:"EARTH // 3 READY",tone:"magenta"});
  assert.deepEqual(get("earth/maps/overview","LIVE","LIVE",{ready:1,stale:1}),
    {text:"EARTH // STALE",tone:"yellow"});
  assert.deepEqual(get("earth/maps/overview","LIVE","LIVE",{cached:1,ready:2}),
    {text:"EARTH // CACHE",tone:"blue"});
  assert.deepEqual(get("weather/maps","LIVE","LIVE",{loading:2,ready:0}),
    {text:"WEATHER // READING",tone:"orange"});
  assert.deepEqual(get("weather/maps/radar","LIVE","LIVE",{ready:0,expired:1}),
    {text:"WEATHER // EXPIRED",tone:"red"});
  assert.deepEqual(plain(badge.badgeFor("earth/maps/overview",true,s("LIVE"),s("LIVE"),{ready:5})),
    {text:"INDEX // PREVIEW",tone:"cyan"});
  for(const p of ["media/watch/live","magick/overview","tools/sources/health"])
    assert.notEqual(get(p,"LIVE","LIVE").tone,"magenta",
      "a catalogue / interpretive / settings menu is not automatically a live source");
});

test("100%-mapped source ledger is NOT video, GPS, Sway, or CLASSIC retirement acceptance",()=>{
  assert.deepEqual(plain(env.remainingSourcePagesForPath("tools",env.PANELS)),[]);
  assert.deepEqual(plain(env.remainingSourcePagesForPath("earth",env.PANELS)),[]);
  assert.deepEqual(plain(env.remainingSourcePagesForPath("weather",env.PANELS)),[]);
  assert.match(station,/\? "CLASSIC" : "SUBJECTS"/);
  assert.match(station,/StationTerminal\s*\{/);
  assert.match(station,/onLegacyPageRequested: function\(pageId\)/);
  const viewer=read("widgets/weather/StationChannelScreen.qml");
  assert.match(viewer,/readonly property bool playbackAvailable: false/);
  assert.match(viewer,/WEBENGINE DISABLED \/\/ QUICKSHELL CRASH PROTECTION/);
  assert.deepEqual(plain(env.nativeDestinationsForPath("../tools",env.PANELS)),[]);
});
