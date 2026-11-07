"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
function policy(file){
 const ctx=vm.createContext({});
 vm.runInContext(read(file).replace(/^\.pragma library\s*/,""),ctx);
 return ctx;
}
const Timeline=policy("widgets/weather/StationMagickTransitTimelinePolicy.js");
const Natal=policy("widgets/weather/StationMagickNatalWheelPolicy.js");
const plain=o=>JSON.parse(JSON.stringify(o));
const natalEpoch="2000-03-21T15:20:00Z";
function natal(){
 const asc=22.25;
 return {format:Natal.FORMAT,epoch_utc:natalEpoch,origin:"topocentric",
  frame:"true-ecliptic-of-date",position_model:"apparent",
  zodiac:"tropical",house_system:"whole-sign",
  observer:{latitude_deg:38.9,longitude_deg:-76.8,elevation_m:0},
  provenance:{engine:"skyfield",ephemeris_sha256:"a".repeat(64),
    house_method:"true-equinox-horizon-meridian-geometric"},
  ascendant_deg:asc,mc_deg:292.3,
  house_cusps_deg:Array.from({length:12},(_,i)=>i*30),
  positions:Natal.TARGETS.map((id,i)=>({
    id,naif_id:Natal.EXACT_NAIF[id],longitude_deg:i===0?10:(14+i*31)%360,
    latitude_deg:0.1,distance_au:1.2
  }))};
}
function request(ch=natal(),date="2026-11-07",span=7){
 return Timeline.request(ch,date,span,"sun","moon",60);
}
function source(req=request(),ch=natal()){
 const natalLon=ch.positions[0].longitude_deg;
 const start=Date.parse(req.start_utc),end=Date.parse(req.end_utc);
 const mid=start+86400000;
 const row=(ms,relative)=>({
   epoch_utc:new Date(ms).toISOString().slice(0,19)+"Z",
   longitude_deg:(natalLon+relative)%360,
   relative_unwrapped_deg:relative
 });
 return {format:Timeline.RESULT_FORMAT,
   source:{engine:"skyfield",ephemeris_sha256:req.expected_ephemeris_sha256,
     position_model:"topocentric-apparent",
     coordinate_frame:"true-ecliptic-of-date"},
   observer:{latitude_deg:req.latitude_deg,longitude_deg:req.longitude_deg,
             elevation_m:0},
   natal_epoch_utc:req.natal_epoch_utc,
   natal_body:req.natal_body,transit_body:req.transit_body,
   natal_longitude_deg:natalLon,start_utc:req.start_utc,end_utc:req.end_utc,
   sample_minutes:req.sample_minutes,
   sample_count:Math.ceil((end-start)/(req.sample_minutes*60000))+1,
   timeline:[row(start,40),row(mid,60),row(end,70)],
   contacts:[{utc:"2026-11-08T03:12:36Z",aspect:"sextile",
     aspect_target_deg:60,direction:"prograde",residual_deg:0.00001}],
   limitations:{
     crossing_search_not_tangency_complete:true,
     contact_time_precision_seconds:1,
     chart_uses_respective_equinoxes_of_date:true,
     medical_or_spiritual_causality_claim:false
   }
 };
}
test("M8g reuses exact natal chart, UTC TASKS date and named JPL targets",()=>{
 const req=request();
 assert.ok(req);
 assert.deepEqual(plain(req),{
  format:Timeline.REQUEST_FORMAT,natal_epoch_utc:natalEpoch,
  start_utc:"2026-11-07T00:00:00Z",end_utc:"2026-11-14T00:00:00Z",
  latitude_deg:38.9,longitude_deg:-76.8,
  expected_ephemeris_sha256:"a".repeat(64),
  natal_body:"sun",transit_body:"moon",sample_minutes:60,
  aspects_deg:[0,60,90,120,180]
 });
 assert.equal(Timeline.TARGETS.length,10);
 assert.equal(Timeline.request(natal(),"2026-11-07",1,"sun","moon",30).sample_minutes,30);
 assert.equal(Timeline.request(natal(),"2026-11-07",14,"sun","moon",60).end_utc,
              "2026-11-21T00:00:00Z");
 assert.equal(Timeline.request(natal(),"2026-11-07",31,"sun","moon",60).end_utc,
              "2026-12-08T00:00:00Z");
 assert.equal(Timeline.request(natal(),"2026-11-07",32,"sun","moon",60),null);
 assert.equal(Timeline.request(natal(),"2026-02-29",7,"sun","moon",60),null);
 assert.equal(Timeline.request(natal(),"2026-11-07",7,"mars","moon",60),null);
 assert.equal(Timeline.request(natal(),"2026-11-07",7,"sun","moon",15),null);
 assert.equal(Timeline.request(natal(),"2099-12-31",7,"sun","moon",60),null);
 const bad=natal();bad.positions[2].naif_id=2;
 assert.equal(Timeline.request(bad,"2026-11-07",7,"sun","moon",60),null);
});
test("M8g checks bound source result and renders physical longitude-derived plot",()=>{
 const ch=natal(),req=request(ch),raw=source(req,ch);
 const model=Timeline.validate(raw,req,ch);
 assert.equal(model.ready,true,model.reason);
 assert.equal(model.sample_count,169);
 assert.equal(model.contacts.length,1);
 assert.equal(model.timeline[0].relative_deg,40);
 const graphic=Timeline.plot(model,430,180);
 assert.ok(graphic);
 assert.equal(graphic.points.length,3);
 assert.equal(graphic.events.length,1);
 assert.ok(graphic.points[0].x<graphic.points[1].x);
 assert.ok(graphic.points[1].x<graphic.points[2].x);
 assert.equal(Timeline.plot(model,30,25),null);
});
test("M8g refuses mismatched kernel, observer, bodies, time, samples and contact claims",()=>{
 const ch=natal(),req=request(ch);
 const checks=[
  v=>v.format="incorrect",
  v=>v.source.ephemeris_sha256="b".repeat(64),
  v=>v.source.position_model="geocentric",
  v=>v.source.coordinate_frame="J2000",
  v=>v.observer.longitude_deg=-80,
  v=>v.observer.elevation_m=5,
  v=>v.natal_epoch_utc="2000-03-20T15:20:00Z",
  v=>v.natal_body="venus",
  v=>v.transit_body="mars_barycenter",
  v=>v.start_utc="2026-11-06T00:00:00Z",
  v=>v.sample_minutes=30,
  v=>v.sample_count=5,
  v=>v.natal_longitude_deg=11.5,
  v=>v.timeline[1].epoch_utc=v.timeline[0].epoch_utc,
  v=>v.timeline[1].longitude_deg=140,
  v=>v.timeline[2].epoch_utc="2026-11-15T00:00:00Z",
  v=>v.contacts[0].aspect="invented",
  v=>v.contacts[0].aspect_target_deg=90,
  v=>v.contacts[0].residual_deg=0.5,
  v=>v.contacts[0].utc="2026-11-15T00:00:00Z",
  v=>v.limitations.crossing_search_not_tangency_complete=false
 ];
 for(const change of checks){
  const raw=source(req,ch);change(raw);
  const state=Timeline.validate(raw,req,ch);
  assert.equal(state.ready,false,"invalid JPL result admitted: "+change.toString());
 }
 assert.equal(Timeline.validate(null,req,ch).ready,false);
 assert.equal(Timeline.validate(source(req,ch),req,null).ready,false);
});
test("M8g preserves full refined UTC event while chart selects nearest valid minute",()=>{
 assert.equal(Timeline.nearestMinute("2026-11-08T03:12:36Z"),
              "2026-11-08T03:13:00Z");
 assert.equal(Timeline.nearestMinute("2026-11-08T03:12:28Z"),
              "2026-11-08T03:12:00Z");
 assert.equal(Timeline.nearestMinute("2026-11-08T23:59:50Z"),
              "2026-11-09T00:00:00Z");
 assert.equal(Timeline.nearestMinute("2026-02-29T00:00:00Z"),"");
 assert.equal(Timeline.nearestMinute("not an event"),"");
});
test("M8g offscreen timeline and private Process integration preserve old JPL/natal paths",()=>{
 const astro=read("widgets/weather/StationMagickAstrologyPane.qml");
 const pane=read("widgets/weather/StationMagickTransitTimelinePane.qml");
 const wheel=read("widgets/weather/StationMagickTransitChartPane.qml");
 const service=read("services/weather/CelestialTransitTimelineService.qml");
 const backend=read("scripts/weather/celestial_transit_timeline.py");
 assert.match(astro,/WeatherServices\.CelestialTransitTimelineService\s*\{/);
 assert.match(astro,/natalChart: astrology\.fullChartData/);
 assert.match(astro,/StationMagickTransitChartPane\s*\{/);
 assert.match(astro,/StationMagickTransitTimelinePane\s*\{/);
 assert.match(astro,/label:"TIMELINE"/);
 assert.match(astro,/label:"WHEEL"/);
 assert.match(astro,/Timeline\.nearestMinute\(exactUtc\)/);
 assert.match(astro,/astrology\.selectedContactUtc=exactUtc/);
 assert.match(astro,/astrology\.requestTransit\(minute\)/);
 assert.match(wheel,/CHART NEAREST UTC MINUTE/);
 assert.match(wheel,/selectedContactUtc: ""/);
 assert.match(pane,/StationMagickUtcDateField\s*\{/);
 assert.match(pane,/Timeline\.plot\(model,curve\.width,curve\.height\)/);
 assert.match(pane,/label:timeline\.busy\?"WAIT":"SEARCH"/);
 assert.match(pane,/onContactRequested/);
 assert.match(pane,/signal contactRequested\(string exactUtc\)/);
 assert.match(pane,/onWheel:function\(wheel\)/);
 assert.match(pane,/timeline\.chooseEvent\(modelData\.utc\)/);
 assert.match(service,/stdinEnabled:true/);
 assert.match(service,/calculator\.write\(JSON\.stringify\(finder\.pending\)\+"\\n"\)/);
 assert.match(service,/Timeline\.validate\(source,pending,natalChart\)/);
 assert.match(service,/if\(text\.length<100\|\|text\.length>65536\)/);
 assert.match(service,/onActiveChanged:if\(!active\)clearState\(\)/);
 assert.match(backend,/stdin\.readline\(4097\)/);
 assert.equal((astro.match(/WeatherServices\.CelestialNatalChartService\s*\{/g)||[]).length,2);
 for(const code of [pane,service]){
   for(const forbidden of ["FileView {","XMLHttpRequest","localStorage",
       "Qt.openUrlExternally","writeFile(","Geolocation","console.log(",
       "Date.now()","Math.random("])
    assert.ok(!code.includes(forbidden),forbidden);
 }
});
