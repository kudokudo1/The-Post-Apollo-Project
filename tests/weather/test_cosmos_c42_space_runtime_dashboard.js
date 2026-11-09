"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const hub=read("widgets/weather/StationCosmosSpaceWeatherHubPane.qml");
const space=read("widgets/weather/StationSpace.qml");
const subject=read("widgets/weather/StationCosmosSubjectPane.qml");
const routing=read("widgets/weather/StationCosmosSubjectPanelPolicy.js");
const ctx=vm.createContext({Date,Number,Math,isFinite,String,Array,Object});
vm.runInContext(read("services/weather/WeatherRuntimePolicy.js")
    .replace(/^\.pragma library\s*$/m,""),ctx);

test("C43 SPACE end-page has exactly DASHBOARD and DIRECTORY, with original routes",()=>{
 assert.match(hub,/property string viewMode: "dashboard"/);
 for(const mode of ["dashboard","directory"])
     assert.ok(hub.includes('kind:"'+mode+'"'),"missing "+mode);
 assert.doesNotMatch(hub,/kind:"services"|label:"SERVICES"|viewMode === "services"/);
 assert.match(hub,/Math\.max\(1,\(viewRail\.width-viewRail\.spacing\)\/2\)/);
 assert.equal((hub.match(/route:"cosmos\/space-weather\//g)||[]).length,7);
 assert.match(hub,/route:"cosmos\/sun\/activity"/);
 assert.match(hub,/routeRequested\(modelData.route\)/);
 assert.match(subject,/id: spaceHubComponent\s*StationCosmosSpaceWeatherHubPane/);
 assert.match(subject,/weatherService: cosmosPane\.weatherService/);
 assert.match(subject,/liveHistoryStore: cosmosPane\.liveHistoryStore/);
 assert.match(routing,/"cosmos\/space-weather\/overview": \{page:"space",space:\[\]\}/);
});

test("C42 uses one existing StationSpace runtime owner, no new provider or duplicate fetcher",()=>{
 assert.equal((hub.match(/StationSpace\s*\{/g)||[]).length,1);
 assert.match(hub,/objectName: "cosmos-c42-source-only-space-owner"/);
 assert.match(hub,/sourceOnly: true/);
 assert.match(hub,/subjectRoute: "cosmos\/space-weather\/full"/);
 assert.match(hub,/property bool activateLiveFeeds: true/);
 assert.match(hub,/visible: spaceHub\.visible && spaceHub\.activateLiveFeeds/);
 assert.doesNotMatch(hub,/Process\s*\{|Timer\s*\{|WeatherServices\./);
 assert.match(space,/readonly property var runtimeRows: \[/);
 assert.match(space,/readonly property var runtimeBriefs: \(\{/);
 assert.match(space,/readonly property bool solarImageActive:\s*!space\.sourceOnly/);
 assert.match(subject,/StationCosmosSpaceWeatherHubPane\s*\{/);
});

test("C42 exposes exactly eleven actual NOAA runtime rows with correct freshness, RX/OBS and cadence",()=>{
 const ids=[
   "space-kp","space-wind","space-imf","space-flux","aurora",
   "solar-flares","xray-flux","swpc-alerts","solar-cycle",
   "noaa-scales","kp-forecast"
 ];
 assert.equal((space.slice(space.indexOf("readonly property var runtimeRows: ["),
        space.indexOf("readonly property var runtimeBriefs:")).match(
        /RuntimePolicy\.displayRow\(/g)||[]).length,11);
 for(const id of ids){
   assert.ok(space.includes('"'+id+'",'),id);
   assert.ok(space.includes('"'+id+'":'),"missing report: "+id);
   assert.ok(ctx.sourceSpec(id),"uncataloged: "+id);
 }
 assert.match(hub,/readonly property var runtimeRows: statusOwner\.runtimeRows/);
 assert.match(hub,/RuntimePolicy\.summarizeRows\(runtimeRows\)/);
 assert.match(hub,/RuntimePolicy\.rowStateLabel\(runtimeItem\.modelData\)/);
 assert.match(hub,/RuntimePolicy\.rowAgeLabel\(runtimeItem\.modelData\)/);
 assert.match(hub,/RuntimePolicy\.cadenceLabel\(runtimeItem\.modelData\)/);
 assert.match(hub,/RuntimePolicy\.statusToken\(row\)/);
 const now=Date.UTC(2026,10,9,8,30);
 const sample=ctx.displayRow("space-kp",{
    active:true,ready:true,loading:false,errorText:"",
    receivedAt:new Date(now-12*60000),
    observedAt:new Date(now-13*60000),usingCache:false
 },now);
 assert.match(ctx.rowAgeLabel(sample),/RX 12m/);
 assert.match(ctx.rowAgeLabel(sample),/OBS 13m/);
 assert.equal(ctx.cadenceLabel(sample),"5m");
 assert.equal(ctx.rowStateLabel(sample),"LIVE // AGING");
 assert.equal(ctx.statusToken(sample),"yellow");
});

test("C42 status includes actual provider brief and avoids claiming missing data is live",()=>{
 assert.match(hub,/readonly property string serviceBrief/);
 assert.match(hub,/statusOwner\.runtimeBriefs/);
 assert.match(hub,/NO CURRENT PROVIDER REPORT/);
 assert.doesNotMatch(hub,/serviceOwnerNote|SOURCE NOTES/);
 for(const wanted of [
    "OBSERVED KP","SOLAR WIND","IMF BT","F10.7","OVATION",
    "GOES FLARES","GOES XRS","BULLETINS / 48H","PREDICTED SSN",
    "KP OUTLOOK","productStamp"
 ]) assert.ok(space.includes(wanted),wanted);
 assert.match(hub,/READY \/\/ /);
 assert.match(hub,/FRESHNESS \/\/ RX \/ OBS \/\/ CADENCE/);
 assert.match(hub,/RX = LOCAL RECEIVE AGE \/\/ OBS = PROVIDER SAMPLE AGE/);
 assert.match(hub,/objectName: "cosmos-c42-selected-service-report"/);
 assert.match(hub,/height: visible \? 38 : 0/);
 assert.match(hub,/onTapped: spaceHub\.selectedServiceId =/);
});

test("C42 current four metric tiles and all eleven runtime rows are fixed, non-scrolling",()=>{
 assert.match(hub,/objectName: "cosmos-c42-space-metrics"/);
 for(const label of ["KP","WIND","BZ // IMF","F10.7"])
     assert.ok(hub.includes('label:"'+label+'"'),label);
 assert.match(hub,/objectName: "cosmos-c42-runtime-rows"/);
 assert.match(hub,/Math\.max\(1,runtimeList\.height/);
 assert.match(hub,/objectName: "cosmos-c42-space-directory"/);
 assert.doesNotMatch(hub,/Flickable\s*\{|ScrollView\s*\{|WebEngine|Image\s*\{/);
});
