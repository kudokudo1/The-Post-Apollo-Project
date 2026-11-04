"use strict";

const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const sourceGround=read("widgets/weather/StationGround.qml");
const policyText=read("widgets/weather/StationWeatherSubjectPanelPolicy.js");
const routesText=read("widgets/weather/StationSubjectNavigationPolicy.js");
const tabsText=read("widgets/weather/StationWorkspaceNavigationPolicy.js");
const subjectPane=read("widgets/weather/StationWeatherSubjectPane.qml");
const originalRoot=read("widgets/weather/WeatherStationW.qml");
const originalWorkspace=read("widgets/weather/StationWorkspaceSurface.qml");
const subjectNavigator=read("widgets/weather/StationSubjectNavigator.qml");

function context(src){
    const c=vm.createContext({});
    vm.runInContext(src.replace(/^\.pragma library\s*$/m,""),c);
    return c;
}
const policy=context(policyText),nav=context(routesText),workspace=context(tabsText);
const FULL="weather/ground/full";
const ids=[...new Set([...sourceGround.matchAll(/ground\.sectionVisible\("([^"]+)"\)/g)].map(x=>x[1]))].sort();

test("M28-Q all 16 original GROUND section families survive unchanged in one SUBJECTS full page",()=>{
    assert.deepEqual(ids,[
        "air-forecast","air-gases","air-pm","alerts","coast",
        "coastal-rel","header","heat-fire","lightning","marine",
        "marine-rel","pollen","rivers","runtime","seismic","source"
    ]);
    assert.equal(policy.kindForRoute(FULL),"ground");
    for(const id of ids){
        assert.equal(policy.visibleFor("ground",FULL,id),true,id+" missing");
        assert.equal(policy.visibleFor("sky",FULL,id),false,id+" wrong source page");
        assert.equal(policy.visibleFor("home",FULL,id),false,id+" wrong source page");
        assert.equal(policy.visibleFor("ground","",id),true,
            id+" original CLASSIC default changed");
    }
    assert.equal(policy.visibleFor("ground",FULL,"invented"),true,
        "pass-through full page intentionally delegates section IDs to original GROUND component");
    assert.equal(policy.visibleFor("ground","weather/conditions/air","seismic"),false);
    assert.equal(policy.visibleFor("ground","earth/geology/earthquakes","seismic"),false);
});

test("GROUND full page is a reachable leaf in the seven-family WEATHER workspace and INDEX",()=>{
    const node=nav.findRoute(FULL);
    assert.ok(node);
    assert.equal(node.subject,"weather");
    assert.equal(node.group,false);
    assert.equal(node.label,"GROUND // ALL ORIGINAL INSTRUMENTS");
    assert.equal(nav.findRoute("weather/ground").group,true);
    const tabs=workspace.tabsFor(FULL);
    const ground=tabs.find(x=>x.key==="ground");
    assert.ok(ground,"real WEATHER bottom row button must open complete GROUND");
    assert.equal(ground.label,"GROUND");
    assert.equal(ground.path,FULL);
    assert.equal(workspace.selectedGroup(FULL),"ground");
    assert.equal(workspace.familyFor(FULL),"weather");
    assert.equal(tabs.length,8);
    assert.deepEqual(JSON.parse(JSON.stringify(
        tabs.filter(x=>["water","hazards","conditions","forecasts"].includes(x.key))
            .map(x=>x.path))),[
        "weather/conditions/current","weather/forecasts/hourly",
        "weather/water/rivers","weather/hazards/alerts"
    ]);
    assert.match(originalWorkspace,/model: surface\.activeTabs/);
    assert.match(originalWorkspace,/onTriggered: surface\.routeRequested\(modelData\.path\)/);
    assert.match(subjectNavigator,/function chooseRoute\(path\)/);
    assert.match(subjectNavigator,/browser\.chooseRoute\(modelData\.path\)/);
    assert.equal(Object.keys(nav.PANELS).length,103,
        "do not rewrite historical control provenance merely to add a full visual page");
});

test("full GROUND shares original five provider admission gates, no extra collectors",()=>{
    for(const key of ["river","lightning","marine","coastal","seismic"])
        assert.equal(policy.needsSource(FULL,key),true,"full GROUND missing original "+key);
    for(const key of ["history","astronomy","xray","video","unused"])
        assert.equal(policy.needsSource(FULL,key),false,
            "full GROUND must not poll unrelated provider "+key);
    assert.equal(policy.needsSource("weather/conditions/air","seismic"),false);
    assert.equal(policy.needsSource("earth/geology/earthquakes","seismic"),false);

    assert.equal((originalRoot.match(/WeatherServices\.SeismicService\s*\{/g)||[]).length,1);
    assert.equal((originalRoot.match(/WeatherServices\.NowcoastLightningService\s*\{/g)||[]).length,1);
    assert.equal((originalRoot.match(/WeatherServices\.NwpsRiverService\s*\{/g)||[]).length,1);
    assert.match(originalRoot,
        /EarthPanelPolicy\.needsSource\(\s*subjectNavigator\.currentPath,\s*"seismic"\)\s*\|\|\s*SubjectPanelPolicy\.needsSource\(\s*subjectNavigator\.currentPath,\s*"seismic"\)/);
    for(const name of ["marine","coastal"])
        assert.ok(sourceGround.includes('SubjectPanelPolicy.needsSource(ground.subjectRoute,"'+name+'")'));
    for(const name of ["lightning","river"])
        assert.ok(originalRoot.includes('subjectNavigator.currentPath, "'+name+'"'));
    assert.match(originalRoot,/active: weatherStation\.menuOpen/);
    assert.match(originalRoot,/active: weatherStation\.menuOpen && weatherStation\.subjectNavigationOpen/);
    assert.ok(!originalRoot.includes("currentView"));
});

test("the original recent earthquake cards, provider rack and source fix remain in the same full scroll surface",()=>{
    for(const str of [
        'title: "SEISMIC // WORLDWIDE 24H"',
        'title: "OFFICIAL ALERTS // NWS"',
        'title: "RIVER // NOAA NWPS"',
        'title: "MARINE // NOAA NDBC"',
        'title: "COAST // NOAA CO-OPS"',
        'title: "LIGHTNING // NOAA NOWCOAST"',
        'title: "HEAT + FIRE WEATHER // NWS CONTEXT"',
        'title: "AIR // NEXT 12 HOURS"',
        'title: "ENVIRONMENT // SOURCE"',
        'title: "LIVE HISTORY // COASTAL RELATIONSHIP"',
        'title: "LIVE HISTORY // MARINE RELATIONSHIPS"',
        "StationRuntimeRack {",
        "id: seismicEventRow",
        "model: ground.recentSeismicEvents",
        "model: ground.pollenSpecies",
        "ground.airQualityForecast",
        "latitude",
        "airQualitySourceTime",
        "NeonScrollBar {",
        "id: groundScroll",
        "boundsBehavior: Flickable.StopAtBounds"
    ])assert.ok(sourceGround.includes(str),"original GROUND UI missing "+str);
    assert.equal((subjectPane.match(/StationGround\s*\{/g)||[]).length,1);
    assert.match(subjectPane,/active: weatherPane\.visible && weatherPane\.kind !== ""/);
    assert.match(subjectPane,/sourceComponent: weatherPane\.kind === "ground"\s*\? groundPanel/);
    assert.match(subjectPane,/subjectRoute: weatherPane\.subjectRoute/);
    for(const item of ["weatherService","nwsAlertSource","seismicSource","lightningSource",
                     "riverSource","persistentCacheStore","liveHistoryStore"])
        assert.ok(subjectPane.includes(item+": weatherPane."+item),
            "native GROUND reused source "+item);
});

test("other focused WEATHER, EARTH and COSMOS routes are preserved; no new feed or writer",()=>{
    for(const [route,id] of [
        ["weather/conditions/air","air-pm"],
        ["weather/conditions/pollen","pollen"],
        ["weather/forecasts/air","air-forecast"],
        ["weather/hazards/alerts","alerts"],
        ["weather/hazards/heat-fire","heat-fire"],
        ["weather/hazards/lightning","lightning"],
        ["weather/history/relationships/coastal","coastal-rel"],
        ["weather/history/relationships/marine","marine-rel"],
        ["weather/water/rivers","rivers"],
        ["weather/water/coast","coast"],
        ["weather/water/marine","marine"]
    ]){
        assert.equal(policy.kindForRoute(route),"ground",route);
        assert.equal(policy.visibleFor("ground",route,id),true,route+" original section");
    }
    for(const key of ["source","runtime","seismic"])
        assert.equal(policy.visibleFor("ground","weather/hazards/heat-fire",key),false);
    assert.equal(policy.kindForRoute("cosmos/sky/full"),"");
    assert.equal(policy.kindForRoute("earth/geology/earthquakes"),"");
    for(const file of [policyText,tabsText,routesText,subjectPane])
        for(const x of ["WeatherServices.","FileView {","Process {",
                       "XMLHttpRequest","swaymsg","curl "])
            assert.equal(file.includes(x),false,"unexpected service or write in route patch "+x);
});
