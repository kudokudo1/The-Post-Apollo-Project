"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.resolve(__dirname,"../..");
const read = p => fs.readFileSync(path.join(root,p),"utf8");
const policySource = read("widgets/weather/StationEarthOverviewPolicy.js");
const context = vm.createContext({Array,Number,Math,String,Object,isFinite});
vm.runInContext(policySource.replace(/^\.pragma library\s*$/m,""),context);
const subject = read("widgets/weather/StationEarthOverviewPane.qml");
const earth = read("widgets/weather/StationEarthSubjectPane.qml");
const discovery = read("widgets/weather/StationDiscovery.qml");
const cosmos = read("widgets/weather/StationCosmosOverviewPane.qml");
const fixture = read("tests/weather/fixtures/E6EarthOverviewNativeShell.qml");
const plain = value => JSON.parse(JSON.stringify(value));

test("E7 replaces only the single full-menu button with three C44-sized direct controls",()=>{
    assert.equal(subject.includes("OPEN FULL MENU"),false);
    assert.equal(subject.includes('id: fullMenu'),false);
    assert.ok(subject.includes('objectName: "earth-e7-overview-main-rail"'));
    assert.ok(subject.includes('objectName: "earth-e7-overview-divider"'));
    assert.ok(subject.includes('objectName: "earth-e7-main-" + modelData.id'));
    assert.ok(subject.includes("height: HeaderGeometry.tabHeight"));
    assert.ok(subject.includes("spacing: HeaderGeometry.tabSpacing"));
    assert.ok(subject.includes("HeaderGeometry.buttonWidth(overviewMainRail.width,3)"));
    assert.ok(subject.includes("anchors.topMargin: HeaderGeometry.tabsToRule"));
    assert.ok(subject.includes("height: overview.embeddedHeader ? 0 : HeaderGeometry.ruleHeight"));
    assert.ok(earth.includes("embeddedHeader: true"));
    assert.ok(subject.includes("onClicked: overview.openTopicRequested(modelData.id)"));
    assert.ok(cosmos.includes('objectName: "cosmos-c44-overview-mode-rail"'));
    for(const topic of context.TOPICS) {
        assert.ok(["water","pollen","environment"].includes(topic.id));
        assert.ok(earth.includes('if (topicId === "water")'));
        assert.ok(earth.includes('else if (topicId === "pollen" || topicId === "environment")'));
    }
    assert.ok(subject.includes('objectName: "earth-e6-prev"'));
    assert.ok(subject.includes('objectName: "earth-e6-next"'));
});

test("E7 no fabricated trends: NWPS stage comparisons are measured, unknown source stays empty",()=>{
    const empty=context.microcharts(0,null,null,null,null,null,[]);
    assert.equal(empty.length,4);
    for(const v of empty) assert.deepEqual(plain(v.values),[]);
    const r={ready:true,gauge:{observedPrimary:2,forecastPrimary:4,
        observedCategory:{label:"MINOR",rank:2}}};
    const x=context.microcharts(0,r,null,null,null,null,[]);
    assert.deepEqual(plain(x[0].values),[0.5,1]);
    assert.deepEqual(plain(x[1].values),[0.5]);
    assert.deepEqual(plain(x[2].values),[1]);
    assert.deepEqual(plain(x[3].values),[1,1,0,0]);
    assert.equal(x[3].caption,"NWPS CLASS");
    assert.equal(context.relative(null,20),null);
});

test("E7 AQI mini-graph uses actual hourly forecast; pollen uses six measured species",()=>{
    const source={aqiReady:true,aqi:26,pm25:4,pm10:10,
        pollenAvailable:true,alderPollen:0,birchPollen:3,
        grassPollen:6,mugwortPollen:1,olivePollen:2,ragweedPollen:4,
        airQualityForecast:[{aqi:21},{aqi:24},{aqi:26},{aqi:20},
                            {aqi:23},{aqi:25}]};
    const chart=context.microcharts(1,null,source,null,null,null,[]);
    assert.equal(chart[0].type,"bars");
    assert.equal(chart[0].caption,"AQI / 6H");
    assert.equal(chart[0].values.length,6);
    assert.ok(chart[0].values.every(x=>x>=0 && x<=1));
    assert.deepEqual(plain(chart[1].values),[0.4]);
    assert.deepEqual(plain(chart[2].values),[1]);
    assert.deepEqual(plain(chart[3].values),[0,0.5,1,1/6,1/3,2/3]);
    const noForecast=context.microcharts(1,null,{...source,airQualityForecast:[]},null,null,null,[]);
    assert.equal(noForecast[0].type,"marks");
    assert.deepEqual(plain(noForecast[0].values),[1,0,0,0,0,0]);
    const noData=context.microcharts(1,null,{aqiReady:false,pollenAvailable:false},
                                    null,null,null,[]);
    for(const v of noData) assert.deepEqual(plain(v.values),[]);
});

test("E7 emergency and heat charts are explicitly categorical, not inferred history",()=>{
    const unknown=context.microcharts(2,null,null,{ready:false,configured:false},
        {ready:false},null,[]);
    for(const v of unknown) assert.deepEqual(plain(v.values),[]);
    const x=context.microcharts(2,null,null,
        {ready:true,configured:true,alertList:[{},{}]},
        {ready:true,events:[{}, {}, {}]},
        {available:true,band:{id:"extreme-caution"}},
        [{event:"Red Flag Warning"}]);
    assert.deepEqual(plain(x[0].values),[1,1,0,0,0]);
    assert.deepEqual(plain(x[1].values),[1,0,0,0,0]);
    assert.deepEqual(plain(x[2].values),[1,1,1,0,0]);
    assert.deepEqual(plain(x[3].values),[1,1,0,0]);
});

test("E7 fixed summary card fit retains the single E2 map and hides only overview scrollbar",()=>{
    assert.equal((discovery.match(/id: mapPlot\b/g)||[]).length,1);
    assert.equal((earth.match(/StationDiscovery\s*\{/g)||[]).length,1);
    assert.ok(subject.includes('objectName: "earth-e6-summary-cards"'));
    assert.ok(subject.includes('objectName: "earth-e7-microchart"'));
    assert.ok(subject.includes('objectName: "earth-e7-bar-strip"'));
    assert.ok(subject.includes('objectName: "earth-e7-meter-track"'));
    assert.ok(subject.includes("anchors.bottom: sourceFooter.top"));
    assert.ok(subject.includes("anchors.top: topicCaption.bottom"));
    assert.ok(discovery.includes('objectName: "earth-e7-overview-hide-event-scrollbar"'));
    assert.ok(discovery.includes("visible: !stationDiscovery.earthOverviewMode"));
    assert.ok(discovery.includes("&& !stationDiscovery.viewerOpen && scrollable"));
    assert.ok(fixture.includes("E7_NATIVE_PASS"));
    assert.ok(fixture.includes("visibleBar.visible"));
    assert.ok(fixture.includes('count(summary,"earth-e7-microchart")!==4'));
    assert.ok(!subject.includes("WeatherServices."));
    assert.ok(!subject.includes("Process {"));
});
