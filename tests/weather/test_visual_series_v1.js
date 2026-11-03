"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");

const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const source=read("widgets/weather/StationInteractiveSeriesPolicy.js");
const chart=read("widgets/weather/StationInteractiveHistoryChart.qml");
const integration=read("widgets/weather/StationSpaceWeatherTimelinePane.qml");
const cosmos=read("widgets/weather/StationCosmosSubjectPane.qml");
const space=read("widgets/weather/StationSpace.qml");
const history=read("services/weather/WeatherLiveHistoryStore.qml");
const historyPolicy=read("services/weather/WeatherLiveHistoryPolicy.js");
const context=vm.createContext({});
const historyCtx=vm.createContext({});
vm.runInContext(source.replace(/^\.pragma library\s*$/m,""),context);
vm.runInContext(historyPolicy.replace(/^\.pragma library\s*$/m,""),historyCtx);
const plain=x=>JSON.parse(JSON.stringify(x));
const NOW=Date.UTC(2026,10,3,12,0,0);
const minute=60000;
const sample=(ageMinutes,value,field="solarWindSpeed",receiptOffset=0)=>({
  observedAtMs:NOW-ageMinutes*minute,
  receivedAtMs:NOW-ageMinutes*minute+receiptOffset,
  payload:{[field]:value}
});
const modeled=(rows,field="solarWindSpeed",span=context.DAY_MS,cap=192)=>
  context.model(rows,field,NOW,span,cap);

test("V1 supports only 6H/24H/48H from retained 48-hour chronology",()=>{
  assert.equal(context.FORMAT,"post-apollo.weather.visual-series.v1");
  assert.deepEqual(plain(context.PRESETS.map(x=>x.id)),["6h","24h","48h"]);
  assert.equal(context.durationFor("6h"),6*60*minute);
  assert.equal(context.durationFor("24h"),24*60*minute);
  assert.equal(context.durationFor("48h"),48*60*minute);
  assert.equal(context.durationFor("7d"),context.DAY_MS);
  assert.equal(historyCtx.sourceRule("space-wind").maxAgeMs,48*60*minute);
  assert.equal(historyCtx.sourceRule("space-imf").maxAgeMs,48*60*minute);
  assert.equal(historyCtx.sourceRule("space-wind").maxSamples,576);
  assert.equal(historyCtx.sourceRule("space-imf").maxSamples,576);
});

test("observed clock determines window; receipt clock is not silently substituted",()=>{
  const rows=[sample(10,400,"solarWindSpeed",1000),sample(500,500,"solarWindSpeed",1000)];
  const r=modeled(rows,"solarWindSpeed",context.SIX_HOURS_MS);
  assert.equal(r.count,1);
  assert.equal(r.rows[0].value,400);
  assert.equal(r.rows[0].timeMs,NOW-10*minute);
  assert.equal(r.rows[0].receivedAtMs,NOW-10*minute+1000);
  assert.equal(r.startMs,NOW-context.SIX_HOURS_MS);
  assert.equal(r.endMs,NOW);
});

test("invalid payload values, future samples and impossible receipt clocks are ignored",()=>{
  const rows=[
    sample(10,380),sample(9,null),sample(8,""),sample(7,"NaN"),
    sample(6,"Infinity"),sample(-2,700),
    {...sample(5,500),receivedAtMs:0},
    {...sample(4,520),receivedAtMs:NOW+10*minute}
  ];
  const r=modeled(rows);
  assert.equal(r.count,1);
  assert.equal(r.rows[0].value,380);
  assert.equal(context.model(rows,"solarWindSpeed",NOW,72*60*minute,192).count,0);
  assert.equal(context.model(rows,"solarWindSpeed",0,context.DAY_MS,192).count,0);
});

test("duplicate observed timestamps choose latest receipt, maintain ascending chronology",()=>{
  const rows=[sample(10,390),sample(20,380),
     sample(10,450,"solarWindSpeed",3000),sample(30,370)];
  const m=modeled(rows);
  assert.equal(m.count,3);
  assert.deepEqual(plain(m.rows.map(x=>x.value)),[370,380,450]);
  assert.equal(m.rows[0].timeMs,NOW-30*minute);
  assert.equal(m.rows[2].timeMs,NOW-10*minute);
  assert.equal(m.rows[2].value,450);
});

test("a genuine temporal gap splits the stroke; no interpolation through outages",()=>{
  const input=[sample(1430,382),sample(1425,390),
               sample(30,450),sample(25,430)];
  const m=modeled(input,"solarWindSpeed",context.TWO_DAYS_MS);
  assert.equal(m.count,4);
  assert.equal(m.segments.length,2);
  assert.equal(m.gaps,1);
  assert.equal(m.segments[0].length,2);
  assert.equal(m.segments[1].length,2);
  assert.equal(m.firstMs,NOW-1430*minute);
  assert.equal(m.lastMs,NOW-25*minute);
  assert.ok(m.gapThresholdMs>=45*minute);
});

test("point budget keeps extrema and endpoints instead of uniform-stride spike loss",()=>{
  const rows=[];
  for(let i=0;i<320;i++)rows.push(sample(320-i,i===71?1200:i===190?100:420));
  const m=modeled(rows,"solarWindSpeed",context.DAY_MS,48);
  assert.equal(m.count,320);
  assert.ok(m.rows.length<=48);
  assert.equal(m.rows[0].timeMs,NOW-320*minute);
  assert.equal(m.rows.at(-1).timeMs,NOW-minute);
  assert.ok(m.rows.some(x=>x.value===1200));
  assert.ok(m.rows.some(x=>x.value===100));
  assert.equal(m.axis.min,100-110);
  assert.equal(m.axis.max,1200+110);
});

test("separate axes keep negative Bz, flat lines and actual units unambiguous",()=>{
  const bz=modeled([sample(30,-7.4,"bz"),sample(20,3.2,"bz")],"bz");
  assert.equal(bz.count,2);
  assert.ok(bz.axis.min < -7.4);
  assert.ok(bz.axis.max > 3.2);
  const flat=modeled([sample(10,0,"bz"),sample(5,0,"bz")],"bz");
  assert.ok(flat.axis.min < 0);
  assert.ok(flat.axis.max > 0);
  assert.ok(context.yPosition(-7.4,bz.axis,100)>context.yPosition(3.2,bz.axis,100));
  assert.match(chart,/INDEPENDENT AXES \/\/ NO INTERPOLATION/);
  assert.match(chart,/leftUnit: "KM\/S"/);
  assert.match(chart,/rightUnit: "NT"/);
});

test("point inspector picks a real timestamp with no generated midpoints",()=>{
  const left=modeled([sample(40,380),sample(20,420)]);
  const right=modeled([sample(42,-2,"bz"),sample(19,-5,"bz")],"bz");
  const selected=context.nearestTimestamp(left,right,NOW-21*minute);
  assert.equal(selected,NOW-20*minute);
  assert.equal(context.nearestValue(left,selected,10*minute).value,420);
  assert.equal(context.nearestValue(right,selected,10*minute).value,-5);
  assert.equal(context.nearestValue(right,selected,0),null);
  assert.equal(context.nearestTimestamp({rows:[]},{rows:[]},NOW),-1);
  assert.equal(context.freshnessLabel(left.lastMs,NOW,45),"FRESH 20M");
  assert.equal(context.freshnessLabel(-1,NOW,45),"NO SAMPLE");
  assert.equal(context.formatNumber(null,1),"--");
  assert.equal(context.formatNumber(-5.12,1),"-5.1");
  assert.equal(context.xPosition(left.startMs,left,360),0);
  assert.equal(context.xPosition(left.endMs,left,360),360);
  assert.ok(context.displayClock(selected).length>0);
});

test("null/empty series and one observation do not draw fictitious curves",()=>{
  const missing=modeled([]);
  assert.equal(missing.count,0);
  assert.equal(missing.rows.length,0);
  assert.equal(missing.segments.length,0);
  assert.equal(missing.axis.min,null);
  const one=modeled([sample(15,410)]);
  assert.equal(one.count,1);
  assert.equal(one.segments.length,1);
  assert.equal(one.segments[0].length,1);
  assert.match(chart,/NO RECORDED SAMPLES IN THIS WINDOW/);
  assert.match(chart,/context\.arc\(/);
  assert.match(chart,/drawSegments\(/);
});

test("QML has working range buttons, Bz toggle, hover and click lock",()=>{
  assert.match(chart,/model: Series\.PRESETS/);
  assert.match(chart,/onClicked:\s*\{\s*inspector\.rangeId = modelData\.id/);
  assert.match(chart,/onClicked: inspector\.showRight = !inspector\.showRight/);
  assert.match(chart,/onClicked: function\(mouse\)/);
  assert.match(chart,/inspector\.lockedTimeMs=selected/);
  assert.match(chart,/hoverEnabled: true/);
  assert.match(chart,/Series\.nearestTimestamp\(/);
  assert.match(chart,/Series\.nearestValue\(/);
  assert.match(chart,/chart\.segments|chart\.segments \|\|/);
  assert.match(chart,/WIND GAPS/);
  assert.match(chart,/POINTS NEED OBSERVATION \+ RECEIPT TIMESTAMPS/);
});

test("COSMOS SPACE WX uses existing 48H source reader without changing SPACE",()=>{
  assert.match(integration,/StationInteractiveHistoryChart\s*\{/);
  assert.match(integration,/StationSpace\s*\{/);
  assert.match(integration,/liveHistoryStore\.samples\("space-wind","global",runtimeNowMs\)/);
  assert.match(integration,/liveHistoryStore\.samples\("space-imf","global",runtimeNowMs\)/);
  assert.match(integration,/historyRevision;/);
  assert.match(cosmos,/id: spaceTimelineComponent/);
  assert.match(cosmos,/cosmos\/space-weather\/overview/);
  assert.match(cosmos,/cosmos\/space-weather\/history/);
  assert.match(cosmos,/spaceTimelineComponent : spaceComponent/);
  assert.match(space,/WeatherTrendInspector\s*\{/);
  assert.match(history,/function samples\(sourceId, scopeKey, nowMs\)/);
  assert.match(historyPolicy,/"space-wind": \{maxSamples:576, maxAgeMs:172800000\}/);
});

test("V1 has no fetcher, storage writer, new engine or external window",()=>{
  for(const src of [source,chart,integration]){
    for(const forbidden of ["FileView {","Process {","XMLHttpRequest",
      "WeatherServices.","new WebSocket","StationTerminal {",
      "swaymsg","writeAdapter()","append(","capture(","new Date().getTime()"]){
        assert.ok(!src.includes(forbidden),"unexpected ownership: "+forbidden);
    }
  }
  assert.match(chart,/renderStrategy: Canvas\.Immediate/);
  assert.match(chart,/Canvas \{/);
});
