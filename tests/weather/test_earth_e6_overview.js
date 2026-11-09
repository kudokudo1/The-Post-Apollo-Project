"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const vm = require("node:vm");
const fs = require("node:fs");
const path = require("node:path");
const root = path.resolve(__dirname,"../..");
const read = file => fs.readFileSync(path.join(root,file),"utf8");
function load(file) {
    const ctx = vm.createContext({Number,Math,String,Object,Array,isFinite});
    vm.runInContext(read(file).replace(/^\.pragma library\s*$/m,""),ctx);
    return ctx;
}
const pure = load("widgets/weather/StationEarthOverviewPolicy.js");
const earth = load("widgets/weather/StationEarthSubjectPanelPolicy.js");
const pane = read("widgets/weather/StationEarthSubjectPane.qml");
const discovery = read("widgets/weather/StationDiscovery.qml");
const card = read("widgets/weather/StationEarthOverviewPane.qml");
const surface = read("widgets/weather/StationWorkspaceNavigationPolicy.js");
const fixture = read("tests/weather/fixtures/E6EarthOverviewNativeShell.qml");
const json = x => JSON.parse(JSON.stringify(x));

test("E6 arrow topic carousel wraps safely and routes only to the original menus",()=>{
    assert.deepEqual(json(pure.TOPICS).map(x=>[x.id,x.route]),[
        ["water","earth/water/rivers"],
        ["pollen","earth/ground/full"],
        ["environment","earth/ground/full"]
    ]);
    for(const [from,expected] of [[-1,2],[0,0],[1,1],[2,2],[3,0],[4,1],[-4,2]])
        assert.equal(pure.wrap(from),expected);
    assert.equal(pure.wrap(NaN),0);
    assert.equal(pure.topic(2).label,"ENVIRONMENT");
    assert.equal(pure.topic(3).id,"water");
    assert.match(card,/onClicked: overview\.topicIndex = Overview\.wrap\(overview\.topicIndex-1\)/);
    assert.match(card,/onClicked: overview\.topicIndex = Overview\.wrap\(overview\.topicIndex\+1\)/);
    assert.match(pane,/onOpenTopicRequested: function\(topicId\)/);
    assert.match(pane,/earthPane\.groundViewMode = topicId === "pollen"/);
    assert.match(pane,/earthPane\.routeRequested\("earth\/water\/rivers"\)/);
    assert.match(pane,/earthPane\.routeRequested\("earth\/ground\/full"\)/);
    assert.match(surface,/\{label:"OVERVIEW",path:"earth\/overview"/);
});

test("E6 WATER uses only existing NWPS gauge readings and never claims no flooding on missing data",()=>{
    const empty=pure.summarize(0,null,null,null,null,null,[]);
    assert.equal(empty.cards.length,4);
    assert.equal(empty.cards[1].value,"--");
    assert.match(empty.footer,/GAUGE DATA IS NOT AN ALERT/);
    const source={ready:true,configured:true,usingPersistentCache:true,
        gauge:{lid:"ABCD1",name:"Original Local Gauge",observedPrimary:1.21,
            forecastPrimary:1.39,primaryUnits:"ft",distanceKm:12.5,
            observedCategory:{label:"NO FLOODING"}}};
    const full=pure.summarize(0,source,null,null,null,null,[]);
    assert.equal(full.cards[0].value,"ABCD1");
    assert.equal(full.cards[1].value,"1.21 ft");
    assert.equal(full.cards[2].value,"1.39 ft");
    assert.equal(full.cards[3].value,"NO FLOODING");
    assert.match(full.footer,/CACHE/);
});

test("E6 AIR and pollen summarize only actual Open-Meteo values",()=>{
    const missing=pure.summarize(1,null,{aqiReady:false,pollenAvailable:false},null,null,null,[]);
    assert.equal(missing.cards[0].value,"--");
    assert.equal(missing.cards[3].value,"--");
    const air={aqiReady:true,aqi:26,aqiLabel:"GOOD",pm25:4.8,pm10:7.4,
        pollenAvailable:true,alderPollen:1,birchPollen:3,grassPollen:6,
        mugwortPollen:2,olivePollen:0,ragweedPollen:4,
        usingPersistentAqiCache:false};
    const a=pure.summarize(1,null,air,null,null,null,[]);
    assert.equal(a.cards[0].value,"26");
    assert.equal(a.cards[1].value,"4.8 µg/m³");
    assert.equal(a.cards[3].detail,"GRASS");
    assert.equal(a.cards[3].value,"6.0 gr/m³");
    assert.equal(pure.pollenPeak({pollenAvailable:true,grassPollen:-1}).value,null);
});

test("E6 ENVIRONMENT keeps NWS pinned-point semantics separate from USGS and weather heat",()=>{
    const heat={available:true,valueF:99.5,band:{label:"EXTREME CAUTION"}};
    const noPoint=pure.summarize(2,null,null,{configured:false,ready:false},
        {ready:false},heat,[]);
    assert.equal(noPoint.cards[0].value,"--");
    assert.match(noPoint.cards[0].detail,/NOT CONFIGURED/);
    const nws={configured:true,ready:true,alertList:[{event:"Red Flag Warning"}],
        usingPersistentCache:false};
    const quake={ready:true,events:[{magnitude:4.2},{magnitude:3.1}]};
    const actual=pure.summarize(2,null,null,nws,quake,heat,[{event:"Red Flag Warning"}]);
    assert.deepEqual(json(actual.cards).map(x=>x.value),["1","1","2","99.5 °F"]);
    assert.match(actual.footer,/NWS PINNED POINT/);
});

test("E6 retains one original map canvas in a half-height viewport and no extra providers",()=>{
    assert.equal((pane.match(/StationDiscovery\s*\{/g)||[]).length,1);
    assert.equal((discovery.match(/id: mapPlot\b/g)||[]).length,1);
    assert.match(pane,/height: earthPane\.overviewMode\s+\? Math\.floor\(\(earthPane\.height-HeaderGeometry\.contentTop\(\)\)\/2\)/);
    assert.match(pane,/anchors\.top: earthLoader\.bottom/);
    assert.match(pane,/earthOverviewMode: earthPane\.overviewMode/);
    assert.match(discovery,/property bool earthOverviewMode: false/);
    assert.match(discovery,/stationDiscovery\.earthOverviewMode[\s\S]*?Math\.max\(0,stationDiscovery\.height-6\)/);
    assert.match(discovery,/visible: pinnedMapHost\.visible && !stationDiscovery\.earthOverviewMode/);
    assert.match(discovery,/!stationDiscovery\.earthOverviewMode\s+clip: true/);
    assert.equal(earth.needsSource("earth/overview","river"),true);
    assert.equal(earth.needsSource("earth/overview","lightning"),false);
    for(const source of ["eonet","gdacs","seismic"])
        assert.equal(earth.needsSource("earth/overview",source),true,source);
    assert.doesNotMatch(card,/WeatherServices\.|FileView\s*\{|Process\s*\{|XMLHttpRequest|openUrlExternally/);
    assert.doesNotMatch(pane,/WeatherServices\.|FileView\s*\{|Process\s*\{/);
    assert.match(fixture,/E6_NATIVE_PASS/);
    assert.match(fixture,/earth-e6-summary-cards/);
});
