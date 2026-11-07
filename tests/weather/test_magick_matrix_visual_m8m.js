"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
function load(p){
 const ctx=vm.createContext({});
 vm.runInContext(read(p).replace(/^\.pragma library\s*/,""),ctx);
 return ctx;
}
const Visual=load("widgets/weather/StationMagickTransitMatrixVisualPolicy.js");
const Matrix=load("widgets/weather/StationMagickTransitMatrixPolicy.js");
const start=Date.parse("2026-11-07T00:00:00Z");
const utc=ms=>new Date(ms).toISOString().slice(0,19)+"Z";
function model(){
 const natal_bodies=["sun","venus"],transit_bodies=["moon","mercury"];
 const events=[
  {utc:"2026-11-07T03:12:36Z",ms:Date.parse("2026-11-07T03:12:36Z"),
   natal_body:"sun",transit_body:"moon",type:"aspect",aspect:"sextile",
   degrees:60,direction:"prograde",residual_deg:0.00002},
  {utc:"2026-11-08T06:00:00Z",ms:Date.parse("2026-11-08T06:00:00Z"),
   natal_body:null,transit_body:"mercury",type:"station",aspect:"",
   degrees:null,direction:"retrograde",velocity_deg_day:-0.003,
   longitude_deg:105.6,residual_deg:null},
  {utc:"2026-11-09T04:15:11Z",ms:Date.parse("2026-11-09T04:15:11Z"),
   natal_body:"venus",transit_body:"moon",type:"aspect",aspect:"square",
   degrees:90,direction:"retrograde",residual_deg:0.00001}
 ];
 return {ready:true,start_utc:utc(start),end_utc:utc(start+7*86400000),
  natal_bodies,transit_bodies,
  natals:[{id:"sun",longitude_deg:12},{id:"venus",longitude_deg:340}],
  matrix:[
   {natal_body:"sun",transit_body:"moon",aspect_count:1},
   {natal_body:"venus",transit_body:"moon",aspect_count:4},
   {natal_body:"sun",transit_body:"mercury",aspect_count:0},
   {natal_body:"venus",transit_body:"mercury",aspect_count:5}
  ],
  series:[
   {id:"moon",points:[
    {ms:start,utc:utc(start),longitude_deg:358},
    {ms:start+86400000,utc:utc(start+86400000),longitude_deg:1},
    {ms:start+7*86400000,utc:utc(start+7*86400000),longitude_deg:14}
   ]},
   {id:"mercury",points:[
    {ms:start,utc:utc(start),longitude_deg:108},
    {ms:start+86400000,utc:utc(start+86400000),longitude_deg:105},
    {ms:start+7*86400000,utc:utc(start+7*86400000),longitude_deg:110}
   ]}
  ],
  events};
}
test("M8m heatmap bins reflect only verified aspect counts",()=>{
 const m=model();
 assert.deepEqual([0,1,2,3,4,5,120,-1,NaN].map(Visual.heatTier),
                  [0,1,1,2,2,3,3,0,0]);
 assert.equal(Visual.cell(m,"sun","moon").count,1);
 assert.equal(Visual.cell(m,"sun","moon").tier,1);
 assert.equal(Visual.cell(m,"venus","moon").tier,2);
 assert.equal(Visual.cell(m,"venus","mercury").tier,3);
 assert.equal(Visual.cell(m,"sun","mercury").tier,0);
 assert.equal(Visual.cell(m,"sun","jupiter_barycenter"),null);
 assert.equal(Visual.cell({ready:false,matrix:m.matrix},"sun","moon"),null);
});
test("M8m timeline groups real UTC event markers in selected moving-body lanes",()=>{
 const m=model(),before=JSON.stringify(m);
 const timeline=Visual.timeline(m,m.events,580,90);
 assert.ok(timeline);
 assert.equal(timeline.markers.length,3);
 assert.ok(timeline.ticks.length>=2&&timeline.ticks.length<=8);
 assert.equal(timeline.markers[0].type,"aspect");
 assert.equal(timeline.markers[1].type,"station");
 assert.ok(timeline.markers[0].y!==timeline.markers[1].y);
 assert.ok(timeline.markers[0].x<timeline.markers[1].x);
 assert.equal(timeline.markers[1].natal_body,null);
 const pair=Matrix.filtered(m,"sun","moon","aspect",false);
 assert.equal(Visual.timeline(m,pair,580,90).markers.length,1);
 assert.equal(Visual.timeline(null,m.events,580,90),null);
 assert.equal(Visual.timeline(m,m.events,20,20),null);
 assert.equal(JSON.stringify(m),before,"timeline mutated verified data");
});
test("M8m INFO inspection keeps station free of natal association and exposes numerical limits",()=>{
 const m=model();
 const aspect=Visual.inspect(m,Visual.eventKey(m.events[0]));
 assert.equal(aspect.type,"aspect");
 assert.equal(aspect.numerical_bracket_seconds,1);
 assert.equal(aspect.utc,"2026-11-07T03:12:36Z");
 assert.equal(aspect.natal_body,"sun");
 assert.equal(aspect.residual_deg,0.00002);
 assert.equal(aspect.physical_time_accuracy_claim,false);
 const station=Visual.inspect(m,Visual.eventKey(m.events[1]));
 assert.equal(station.type,"station");
 assert.equal(station.natal_body,null);
 assert.equal(station.numerical_bracket_seconds,60);
 assert.equal(station.velocity_deg_day,-0.003);
 assert.equal(station.physical_time_accuracy_claim,false);
 assert.equal(Visual.inspect(m,"unknown"),null);
 assert.equal(Visual.inspect(null,Visual.eventKey(m.events[0])),null);
});
test("M8m inspection trajectory unwraps 360-degree source longitudes without fake event points",()=>{
 const m=model(),e=Visual.inspect(m,Visual.eventKey(m.events[0]));
 const draw=Visual.trajectory(m,e,640,180,1);
 assert.ok(draw);
 assert.equal(draw.points.length,3);
 assert.equal(draw.sampleCount,3);
 assert.ok(Math.abs(draw.points[0].y-draw.points[1].y)<80,
           "source longitude wrap caused 360-degree plotting jump");
 assert.equal(Math.round(draw.eventX),320);
 assert.ok(draw.referenceY!==null);
 const enlarged=Visual.trajectory(m,e,640,180,2);
 assert.ok(enlarged);
 assert.equal(enlarged.eventX,draw.eventX);
 assert.ok(Math.abs(enlarged.points[1].x-draw.eventX)>
           Math.abs(draw.points[1].x-draw.eventX));
 const stationary=Visual.inspect(m,Visual.eventKey(m.events[1]));
 assert.equal(Visual.trajectory(m,stationary,640,180,1).referenceY,null);
 assert.equal(Visual.trajectory(m,e,640,180,0),null);
 assert.equal(Visual.trajectory(m,e,640,180,10),null);
 assert.equal(Visual.trajectory(m,e,30,30,1),null);
});
test("M8m QML separates marker/INFO inspection from original WHEEL navigation",()=>{
 const ui=read("widgets/weather/StationMagickTransitMatrixPane.qml");
 const service=read("services/weather/CelestialTransitMatrixService.qml");
 const backend=read("scripts/weather/celestial_transit_matrix.py");
 assert.match(ui,/StationMagickTransitMatrixVisualPolicy\.js" as Visual/);
 assert.match(ui,/property bool inspectorOpen:false/);
 assert.match(ui,/readonly property var timelineModel:Visual\.timeline\(/);
 assert.match(ui,/readonly property var inspectedEvent:Visual\.inspect\(/);
 assert.match(ui,/readonly property var detailGeometry:Visual\.trajectory\(/);
 assert.match(ui,/function inspectEvent\(event\)/);
 assert.match(ui,/function closeInspector\(\)/);
 assert.match(ui,/id:matrixScroll/);
 assert.match(ui,/id:eventAxis/);
 assert.match(ui,/Visual\.cell\(model,natal,moving\)/);
 assert.match(ui,/idleFillColor:atlas\.cellFill/);
 assert.match(ui,/label:"INFO"/);
 assert.match(ui,/onClicked:atlas\.inspectEvent\(modelData\)/);
 assert.match(ui,/onClicked:atlas\.chooseEvent\(modelData\)/);
 assert.match(ui,/id:inspectorPanel/);
 assert.match(ui,/id:detailCanvas/);
 assert.match(ui,/atlas\.detailZoom=Math\.min\(8,atlas\.detailZoom\*1\.5\)/);
 assert.match(ui,/label:"WHEEL"/);
 assert.match(ui,/label:"CLOSE"/);
 assert.match(ui,/eventRequested\(event\.utc,reference,event\.transit_body,event\.type\)/);
 assert.match(service,/stdinEnabled:true/);
 assert.match(backend,/MAX_PAIR_SAMPLES = 2200/);
 for(const bad of ["XMLHttpRequest","FileView {","localStorage","writeFile(",
     "Qt.openUrlExternally","Math.random(","Date.now()"]){
   assert.ok(!ui.includes(bad),"unexpected UI side effect "+bad);
 }
});
