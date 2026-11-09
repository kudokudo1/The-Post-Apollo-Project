"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
function policy(p){const ctx=vm.createContext({Array,Object,Number,Math,String,isFinite});
 vm.runInContext(read("widgets/weather/"+p).replace(/^\.pragma library\s*$/m,""),ctx);return ctx;}
const workspace=policy("StationWorkspaceNavigationPolicy.js");
const tree=policy("StationSubjectNavigationPolicy.js");
const earth=policy("StationEarthSubjectPanelPolicy.js");
const ground=policy("StationWeatherSubjectPanelPolicy.js");
const discovery=read("widgets/weather/StationDiscovery.qml");
const earthPane=read("widgets/weather/StationEarthSubjectPane.qml");
const groundPane=read("widgets/weather/StationGround.qml");
const waterPane=read("widgets/weather/StationEarthWaterPane.qml");
const servicePane=read("widgets/weather/StationEarthServicesPane.qml");
const rootStation=read("widgets/weather/WeatherStationW.qml");
const stationSurface=read("widgets/weather/StationWorkspaceSurface.qml");
const browser=read("widgets/weather/StationSubjectNavigator.qml");
const plain=v=>JSON.parse(JSON.stringify(v));

test("E2 bottom tabs separate one overview, one map, WATER, GROUND and final SERVICES",()=>{
 assert.deepEqual(plain(workspace.GROUPS.earth.map(x=>[x.key,x.path])),[
   ["overview","earth/overview"],
   ["map","earth/maps/events"],
   ["water","earth/water/rivers"],
   ["ground","earth/ground/full"],
   ["services","earth/services/health"]]);
 assert.deepEqual(plain(workspace.GROUPS.weather.map(x=>x.key)),[
   "overview","conditions","forecasts","hazards","history"]);
 for(const x of workspace.GROUPS.earth)
   assert.equal(tree.findRoute(x.path).subject,"earth");
 for(const name of ["geology","geography","events","fires","maps","investigations"])
   assert.equal(workspace.selectedGroup("earth/"+name+"/test"),"map");
 assert.equal(workspace.selectedGroup("earth/water/rivers/hydrograph"),"water");
 assert.equal(tree.panelLanding("map-mrms-radar"),"earth/maps/events");
 assert.equal(tree.panelLanding("ground-coast-coops"),"earth/water/coast");
 assert.match(browser,/chooseRoute\("earth\/maps\/events"\)/);
});

test("E2 old EARTH event and investigation routes remain valid without another map engine",()=>{
 assert.equal(earth.isPinnedMap("earth/maps/events"),true);
 assert.equal(earth.isFullMap("earth/maps/full"),true);
 for(const layer of ["quakes","eonet","gdacs","firms","smoke"])
   assert.equal(earth.showsLayer("earth/maps/events",layer),true);
 for(const name of ["earth/geology/earthquakes","earth/events/eonet",
                    "earth/events/gdacs","earth/fires/hotspots",
                    "earth/investigations/dossiers","earth/investigations/archive",
                    "earth/maps/full"]){
   assert.ok(tree.findRoute(name),name);
   assert.equal(earth.kindForRoute(name),"map");
 }
 for(const x of ["earth/water/rivers","earth/water/marine",
                 "earth/water/coast","earth/ground/full"])
   assert.equal(earth.kindForRoute(x),"ground");
 assert.equal(earth.kindForRoute("earth/services/health"),"services");
 assert.equal((earthPane.match(/StationDiscovery\s*\{/g)||[]).length,1);
 assert.match(earthPane,/active: earthPane\.visible && earthPane\.kind !== ""/);
 assert.match(earthPane,/earthPinnedMap: EarthPanelPolicy\.isPinnedMap\(earthPane\.subjectRoute\)/);
 for(const property of ["eventArchiveStore","dossierArchiveStore","persistentCacheStore",
                        "seismicSource","lightningSource","riverSource"])
   assert.ok(earthPane.includes(property+": earthPane."+property),property);
 assert.doesNotMatch(earthPane,/WeatherServices\.|Process\s*\{|FileView\s*\{/);
});

test("E2 the actual original mapPlot is reparented into a fixed viewport, not duplicated",()=>{
 assert.equal((discovery.match(/id: mapPlot\b/g)||[]).length,1);
 assert.match(discovery,/property bool earthPinnedMap: false/);
 assert.match(discovery,/id: pinnedEarthFilters/);
 assert.match(discovery,/id: pinnedMapHost/);
 assert.match(discovery,/objectName: "earth-e2-pinned-map-host"/);
 assert.match(discovery,/parent: mapCanvasSection/);
 assert.match(discovery,/states: State\s*\{[\s\S]*?when: stationDiscovery\.earthPinnedMap[\s\S]*?ParentChange\s*\{[\s\S]*?target: mapPlot[\s\S]*?parent: pinnedMapHost[\s\S]*?x: 0[\s\S]*?y: 0/);
 assert.match(discovery,/anchors\.top: pinnedMapControls\.visible\s*\? pinnedMapControls\.bottom : parent\.top/);
 assert.match(discovery,/anchors\.top: pinnedMapHost\.bottom/);
 assert.match(discovery,/id: discoveryScroll/);
 assert.match(discovery,/contentHeight: Math\.max\(height, content\.y \+ content\.implicitHeight \+ 12\)/);
 assert.match(discovery,/height: stationDiscovery\.earthPinnedMap\s*\? pinnedMapHost\.height : 270/);
 assert.match(discovery,/visible: !stationDiscovery\.viewerOpen && !stationDiscovery\.earthServicesOnly/);
 assert.match(earthPane,/earthServicesOnly: earthPane\.kind === "services"/);
});

test("E2 map filters correspond to real USGS EONET GDACS FIRMS without new providers",()=>{
 for(const key of ["all","quakes","eonet","gdacs","firms"])
   assert.ok(discovery.includes('key:"'+key+'"'),key);
 for(const layer of ["quakes","eonet","gdacs","firms"])
   assert.ok(discovery.includes('earthLayerSelected("'+layer+'")'),layer);
 for(const name of ["mapEarthquakeRows","mapGdacsRows","mapPointRows","firmsService.hotspots"])
   assert.ok(discovery.includes(name),name);
 assert.match(discovery,/function inspectPinnedEvent\(kind,row\)/);
 assert.match(discovery,/onClicked: stationDiscovery\.inspectPinnedEvent\(/);
 assert.match(discovery,/objectName: "earth-e2-event-scroll"/);
 assert.match(discovery,/stationDiscovery\.fetchVisibleHotspots\(\)/);
 assert.match(discovery,/mapVisibleBounds/);
 assert.match(discovery,/DossierCapturePolicy\.review\(/);
 assert.match(discovery,/eventArchiveStore\.archiveEvent\(/);
 assert.equal((rootStation.match(/WeatherServices\.SeismicService\s*\{/g)||[]).length,1);
 assert.equal((rootStation.match(/WeatherServices\.NwpsRiverService\s*\{/g)||[]).length,1);
 assert.equal((discovery.match(/WeatherServices\.GdacsService\s*\{/g)||[]).length,1);
 assert.equal((discovery.match(/WeatherServices\.FirmsHotspotService\s*\{/g)||[]).length,1);
 assert.equal((discovery.match(/WeatherServices\.MrmsRadarService\s*\{/g)||[]).length,1);
});

test("E2 WATER uses the existing ground engine for three isolated bodies, GROUND excludes WATER",()=>{
 assert.equal(ground.visibleFor("ground","earth/water/rivers","rivers"),true);
 assert.equal(ground.visibleFor("ground","earth/water/marine","marine"),true);
 assert.equal(ground.visibleFor("ground","earth/water/coast","coast"),true);
 assert.equal(ground.visibleFor("ground","earth/water/rivers","seismic"),false);
 assert.equal(ground.visibleFor("ground","earth/ground/full","seismic"),true);
 assert.equal(ground.visibleFor("ground","earth/ground/full","lightning"),false);
 for(const x of ["rivers","marine","coast"])
   assert.equal(ground.visibleFor("ground","earth/ground/full",x),false);
 for(const source of ["river","marine","coastal","lightning","seismic"]){
   const paths={river:"earth/water/rivers",marine:"earth/water/marine",
      coastal:"earth/water/coast",lightning:"earth/ground/full",
      seismic:"earth/ground/full"};
   assert.equal(ground.needsSource(paths[source],source),
     source!=="lightning",source);
 }
 assert.equal((waterPane.match(/StationGround\s*\{/g)||[]).length,1);
 assert.equal((earthPane.match(/StationGround\s*\{/g)||[]).length,1);
 for(const path of ["earth/water/rivers","earth/water/marine","earth/water/coast"])
   assert.ok(waterPane.includes(path),path);
 assert.match(groundPane,/earth\/water\/rivers/);
 assert.match(groundPane,/onTriggered: ground\.routeRequested\(modelData\.path\)/);
 assert.match(stationSurface,/nwsAlertSource: surface\.nwsAlertSource/);
 assert.match(stationSurface,/liveHistoryStore: surface\.liveHistoryStore/);
});

test("E2 final SERVICES observes same runtimeRows, RX OBS and provider states, not a duplicate",()=>{
 assert.match(earthPane,/StationEarthServicesPane\s*\{/);
 assert.match(earthPane,/runtimeRows: earthLoader\.item \? earthLoader\.item\.runtimeRows : \[\]/);
 assert.match(earthPane,/sourceRows: earthLoader\.item \? earthLoader\.item\.plannedSources : \[\]/);
 assert.match(servicePane,/RuntimePolicy\.rowAgeLabel\(/);
 assert.match(servicePane,/RuntimePolicy\.rowStateLabel\(/);
 assert.match(servicePane,/RuntimePolicy\.cadenceLabel\(/);
 assert.match(servicePane,/SOURCE DIRECTORY/);
 assert.match(servicePane,/RX = LOCAL RECEIPT \/\/ OBS = PROVIDER SAMPLE/);
 assert.match(servicePane,/id: rowScroll/);
 assert.doesNotMatch(servicePane,/WeatherServices\.|Process\s*\{|FileView\s*\{|XMLHttpRequest/);
 assert.match(discovery,/readonly property var runtimeRows/);
 assert.match(discovery,/readonly property var plannedSources/);
});

test("E2 the original overview is not rewritten and historical compatibility is read-only",()=>{
 assert.match(earthPane,/earthMapRoute: earthPane\.kind === "services"/);
 assert.ok(tree.findRoute("earth/overview"));
 assert.ok(tree.findRoute("weather/water/rivers"));
 assert.ok(tree.findRoute("weather/ground/full"));
 assert.ok(tree.findRoute("weather/maps/radar"));
 assert.equal(ground.kindForRoute("weather/ground/full"),"ground");
 assert.equal(earth.needsSource("earth/maps/events","seismic"),true);
 assert.equal(earth.needsSource("earth/maps/events","river"),true);
 assert.equal(earth.needsSource("earth/maps/events","lightning"),true);
 for(const source of ["firms","smoke"])
   assert.equal(earth.needsSource("earth/maps/events",source),false);
});
