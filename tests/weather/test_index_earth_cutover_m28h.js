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
const earthPolicy=read("widgets/weather/StationEarthSubjectPanelPolicy.js");
const earthPane=read("widgets/weather/StationEarthSubjectPane.qml");
const discovery=read("widgets/weather/StationDiscovery.qml");
const navigator=read("widgets/weather/StationSubjectNavigator.qml");
const station=read("widgets/weather/WeatherStationW.qml");
const c=vm.createContext({}),e=vm.createContext({});
vm.runInContext(nav.replace(/^\.pragma library\s*$/m,""),c);
vm.runInContext(preview.replace(/^\.pragma library\s*$/m,""),c);
vm.runInContext(earthPolicy.replace(/^\.pragma library\s*$/m,""),e);
const plain=x=>JSON.parse(JSON.stringify(x));
const controls=[
  ["ground-usgs-seismic","earth/geology/earthquakes","quakes"],
  ["map-natural-earth","earth/geography/basemap",null],
  ["map-spatial-canvas","earth/maps/overview","eonet"],
  ["map-earthquake-layer","earth/geology/earthquakes","quakes"],
  ["map-eonet-layer","earth/events/eonet","eonet"],
  ["map-gdacs-layer","earth/events/gdacs","gdacs"],
  ["map-firms-hotspots","earth/fires/hotspots","firms"],
  ["map-event-context","earth/investigations/context","context"],
  ["map-dossier-preview","earth/investigations/dossiers","dossiers"],
  ["map-event-archive","earth/investigations/archive","archive"],
  ["map-gdacs-inspector","earth/events/gdacs","gdacs"],
  ["map-usgs-inspector","earth/geology/earthquakes","quakes"],
  ["map-eonet-inspector","earth/events/eonet","eonet"],
  ["map-firms-inspector","earth/fires/hotspots","firms"]
];

test("M28-H is exactly fourteen reviewed original EARTH event and dossier source controls",()=>{
  assert.equal(controls.length,14);
  assert.equal(new Set(controls.map(row=>row[0])).size,14);
  const classified=Object.keys(c.WIRED_IN_SUBJECTS)
    .filter(key=>c.WIRED_IN_SUBJECTS[key]==="M28-H").sort();
  assert.deepEqual(classified,controls.map(x=>x[0]).sort());
  for(const [id,route,layer] of controls){
    assert.equal(c.PANELS[id],route,id+" migration target");
    const target=c.findRoute(route);
    assert.ok(target && !target.group && target.subject==="earth",id+" direct leaf");
    assert.equal(e.kindForRoute(route),"map",id+" existing EARTH source");
    if(layer==="context"||layer==="dossiers"||layer==="archive"){
      assert.equal(e.investigationRoute(route),true,id+" investigation");
    }else if(layer!==null){
      assert.equal(e.showsLayer(route,layer),true,id+" event/map layer");
    }else{
      assert.ok(e.routeInfo(route),id+" local basemap route");
      assert.equal(e.showsLayer(route,"quakes"),false,"basemap hides source-specific events");
    }
  }
  assert.equal(Object.keys(c.PANELS).length,103);
  assert.equal(Object.values(c.WIRED_IN_SUBJECTS)
    .filter(milestone=>milestone==="M28-H").length,14,
    "M28-H fourteen event mappings remain an exact proof");
  assert.ok(Object.keys(c.WIRED_IN_SUBJECTS).length>=83,
    "later bounded reviews may add independently audited controls");
});

test("EARTH has one source-scoped map instance, not second event or archive writer",()=>{
  assert.equal((earthPane.match(/StationDiscovery\s*\{/g)||[]).length,1);
  assert.match(earthPane,/Loader\s*\{/);
  assert.match(earthPane,/active: earthPane\.visible && earthPane\.kind === "map"/);
  assert.match(earthPane,/sourceComponent: earthMapComponent/);
  assert.match(earthPane,/earthMapOnly: true/);
  assert.match(earthPane,/earthMapRoute: earthPane\.subjectRoute/);
  assert.match(earthPane,/newsMentionOverlay: earthPane\.newsMentionOverlay/);
  assert.match(earthPane,/eventArchiveStore: earthPane\.eventArchiveStore/);
  assert.match(earthPane,/dossierArchiveStore: earthPane\.dossierArchiveStore/);
  assert.match(navigator,/StationEarthSubjectPane\s*\{/);
  assert.match(station,/active: !weatherStation\.subjectNavigationOpen/);
  for(const bad of ["WeatherServices.","FileView {","Process {","XMLHttpRequest"])
    assert.ok(!earthPane.includes(bad),"no duplicate source or store "+bad);
});

test("EARTH original USGS, EONET, GDACS and FIRMS layers retain provider separation",()=>{
  for(const [route,source] of [
    ["earth/geology/earthquakes","seismic"],
    ["earth/events/eonet","eonet"],
    ["earth/events/gdacs","gdacs"]
  ])assert.equal(e.needsSource(route,source),true,route+" provider gate");
  for(const source of ["seismic","eonet","gdacs"])
    assert.equal(e.needsSource("weather/maps/radar",source),false);
  assert.equal(e.needsSource("earth/fires/hotspots","firms"),false,
    "FIRMS remains manual and must not turn into an unsolicited new fetcher");
  assert.match(discovery,/WeatherServices\.StationDiscoveryService\s*\{/);
  assert.match(discovery,/WeatherServices\.GdacsService\s*\{/);
  assert.match(discovery,/WeatherServices\.FirmsHotspotService\s*\{/);
  assert.match(discovery,/EarthPanelPolicy\.needsSource\(\s*stationDiscovery\.earthMapRoute,"eonet"\)/);
  assert.match(discovery,/EarthPanelPolicy\.needsSource\(\s*stationDiscovery\.earthMapRoute,"gdacs"\)/);
  assert.match(discovery,/function earthLayerEnabled\(layer\)/);
  assert.match(discovery,/mapCompanionEonetRows/);
  assert.match(discovery,/BASEMAP \/\/ NATURAL EARTH 1:110m LAND/);
});

test("original provider event inspector selection and manual dossier/archive admission survive",()=>{
  for(const source of [
    "selectedMapEvent","selectedMapHotspot","selectedMapEarthquake",
    "selectedMapGdacsEvent","selectedEventContext","selectedDossierPreview",
    "selectedDossierCaptureReview","dossierSaveAvailable"
  ])assert.ok(discovery.includes(source),source);
  assert.match(discovery,/function archiveSelectedEvent\(\)/);
  assert.match(discovery,/eventArchiveStore\.archiveEvent\(/);
  assert.match(discovery,/function saveSelectedDossier\(\)/);
  assert.match(discovery,/dossierArchiveStore\.capture\(staged, now\)/);
  assert.match(discovery,/visible: stationDiscovery\.earthInvestigationRoute/);
  assert.match(discovery,/EarthPanelPolicy\.selectionHint\(/);
  assert.ok(e.selectionHint("earth/investigations/archive").includes("MANUAL"));
  assert.equal(e.investigationRoute("earth/maps/overview"),false);
  assert.match(discovery,/selectedMapNewsMention/);
  assert.match(discovery,/newsMentionOverlay/);
});

test("INDEX no longer routes already-reviewed EARTH source groups into CLASSIC",()=>{
  const native=plain(c.nativeDestinationsForPath("earth",c.PANELS));
  assert.equal(native.length,9,"all original EARTH controls coalesce into nine real leaf destinations");
  assert.deepEqual(plain(c.remainingSourcePagesForPath("earth",c.PANELS)),[]);
  assert.deepEqual(plain(c.sourcePagesForPath("earth",c.PANELS).map(z=>z.id)),
    ["ground","map"],"historic M1 source provenance stays available");
  assert.ok(native.every(x=>x.path.startsWith("earth/") && !c.findRoute(x.path).group));
  assert.match(navigator,/model: browser\.nativeDestinations/);
  assert.match(navigator,/onClicked: browser\.chooseRoute\(modelData\.path\)/);
  assert.match(navigator,/model: browser\.classicSources/);
  assert.equal(c.WIRED_IN_SUBJECTS["map-news-mentions"],"M28-A",
    "MEDIA mentioned places must not be promoted as EARTH-native event records");
});

test("unreviewed tools and watch controls are not implicitly certified by EARTH parity",()=>{
  for(const id of [
    "map-source-rack","ground-source","station-source-badge"
  ]) assert.equal(c.WIRED_IN_SUBJECTS[id],undefined,id+" remains pending");
  assert.deepEqual(plain(c.nativeDestinationsForPath("../earth",c.PANELS)),[]);
  assert.deepEqual(plain(c.remainingSourcePagesForPath("earth//map",c.PANELS)),[]);
  assert.equal(e.kindForRoute("weather/maps/radar"),"");
});
