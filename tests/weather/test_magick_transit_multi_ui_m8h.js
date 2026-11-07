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
const Multi=policy("widgets/weather/StationMagickTransitMultiPolicy.js");
const Natal=policy("widgets/weather/StationMagickNatalWheelPolicy.js");
const plain=o=>JSON.parse(JSON.stringify(o));
const BIRTH="2000-03-21T15:20:00Z";
function natal(){
 return {format:Natal.FORMAT,epoch_utc:BIRTH,origin:"topocentric",
  frame:"true-ecliptic-of-date",position_model:"apparent",zodiac:"tropical",
  house_system:"whole-sign",observer:{latitude_deg:38.9,
     longitude_deg:-76.8,elevation_m:0},
  provenance:{engine:"skyfield",ephemeris_sha256:"a".repeat(64),
     house_method:"true-equinox-horizon-meridian-geometric"},
  ascendant_deg:22.25,mc_deg:292.3,
  house_cusps_deg:Array.from({length:12},(_,i)=>30*i),
  positions:Natal.TARGETS.map((id,i)=>({
      id,naif_id:Natal.EXACT_NAIF[id],
      longitude_deg:i===0?10:(14+31*i)%360,
      latitude_deg:0,distance_au:1.2
  }))};
}
function request(ch=natal(),date="2026-11-07",days=7,
                 bodies=["moon","mercury","venus"],aspects=[60,90]){
 return Multi.request(ch,date,days,"sun",bodies,aspects,60);
}
function result(req=request(),ch=natal()){
 const from=Date.parse(req.start_utc),to=Date.parse(req.end_utc);
 const natalLon=ch.positions.find(p=>p.id===req.natal_body).longitude_deg;
 const row=(ms,deg)=>({
    epoch_utc:new Date(ms).toISOString().slice(0,19)+"Z",
    longitude_deg:(natalLon+deg)%360,
    relative_unwrapped_deg:deg
 });
 const series=req.transit_bodies.map((id,i)=>({
    id,sample_count:Math.ceil((to-from)/(req.sample_minutes*60000))+1,
    timeline:[row(from,40+i*3),row(from+86400000,60+i*3),
              row(to,70+i*3)]
 }));
 const events=[
    {utc:"2026-11-08T03:12:36Z",type:"aspect",natal_body:"sun",
     transit_body:req.transit_bodies[0],aspect:"sextile",
     aspect_target_deg:60,direction:"prograde",residual_deg:0.00001},
    {utc:"2026-11-09T06:00:00Z",type:"station",natal_body:"sun",
     transit_body:req.transit_bodies[1],direction:"retrograde",
     longitude_deg:103.75,velocity_deg_day:0.003,
     uncertainty_seconds:60}
 ];
 return {format:Multi.RESULT_FORMAT,
   source:{engine:"skyfield",ephemeris_sha256:req.expected_ephemeris_sha256,
       position_model:"topocentric-apparent",
       coordinate_frame:"true-ecliptic-of-date"},
   observer:{latitude_deg:req.latitude_deg,longitude_deg:req.longitude_deg,
             elevation_m:0},
   natal_epoch_utc:req.natal_epoch_utc,natal_body:req.natal_body,
   natal_longitude_deg:natalLon,start_utc:req.start_utc,
   end_utc:req.end_utc,transit_bodies:req.transit_bodies.slice(),
   sample_minutes:req.sample_minutes,aspects_deg:req.aspects_deg.slice(),
   include_stations:true,series,events,
   limitations:{
      crossing_search_not_tangency_complete:true,
      station_search_not_all_turns_guaranteed:true,
      station_velocity_central_difference_minutes:20,
      station_time_bracket_seconds:60,
      contact_time_precision_seconds:1,
      chart_uses_respective_equinoxes_of_date:true,
      medical_or_spiritual_causality_claim:false
   }};
}
test("M8h builds bounded three-planet and aspect-subset JPL request",()=>{
 const req=request();
 assert.deepEqual(plain(req),{
    format:Multi.REQUEST_FORMAT,natal_epoch_utc:BIRTH,
    start_utc:"2026-11-07T00:00:00Z",
    end_utc:"2026-11-14T00:00:00Z",
    latitude_deg:38.9,longitude_deg:-76.8,
    expected_ephemeris_sha256:"a".repeat(64),
    natal_body:"sun",
    transit_bodies:["moon","mercury","venus"],
    sample_minutes:60,aspects_deg:[60,90],include_stations:true
 });
 assert.equal(Multi.request(natal(),"2026-11-07",7,"sun",
     ["moon"],[0],30).sample_minutes,30);
 assert.equal(request(natal(),"2026-11-07",31).end_utc,
              "2026-12-08T00:00:00Z");
 for(const invalid of [
  [natal(),"2026-11-07",7,"sun",[],[60],60],
  [natal(),"2026-11-07",7,"sun",["moon","moon"],[60],60],
  [natal(),"2026-11-07",7,"sun",["sun","moon","venus","mercury"],[60],60],
  [natal(),"2026-11-07",7,"sun",["mars"],[60],60],
  [natal(),"2026-11-07",7,"sun",["moon"],[],60],
  [natal(),"2026-11-07",7,"sun",["moon"],[60,60],60],
  [natal(),"2026-11-07",7,"sun",["moon"],[45],60],
  [natal(),"2026-11-07",7,"sun",["moon"],[60],15],
  [natal(),"2026-02-29",7,"sun",["moon"],[60],60],
  [natal(),"2099-12-31",7,"sun",["moon"],[60],60],
  [natal(),"2026-11-07",32,"sun",["moon"],[60],60]
 ]){
    assert.equal(Multi.request(...invalid),null);
 }
 let wrong=natal();wrong.positions[2].naif_id=2;
 assert.equal(Multi.request(wrong,"2026-11-07",7,"sun",
                   ["moon"],[60],60),null);
});
test("M8h source checked across all three series and stations",()=>{
 const ch=natal(),req=request(ch),raw=result(req,ch);
 const model=Multi.validate(raw,req,ch);
 assert.equal(model.ready,true,model.reason);
 assert.equal(model.series.length,3);
 assert.equal(model.sample_count,169);
 assert.equal(model.series[0].points.length,3);
 assert.equal(model.events.length,2);
 assert.equal(model.events[0].type,"aspect");
 assert.equal(model.events[1].type,"station");
 assert.equal(model.events[1].direction,"retrograde");
 assert.equal(Multi.browserEvents(model,"station","",false).length,1);
 assert.equal(Multi.browserEvents(model,"aspect","moon",false).length,1);
 assert.equal(Multi.browserEvents(model,"ALL","venus",false).length,0);
 assert.equal(Multi.browserEvents(model,"ALL","",true)[0].type,"station");
 const plot=Multi.graph(model,420,160);
 assert.ok(plot);
 assert.equal(plot.lines.length,3);
 assert.equal(plot.events.length,2);
 assert.equal(plot.lines[0].points.length,3);
 assert.ok(plot.lines[0].points[0].x<plot.lines[0].points[2].x);
 assert.equal(Multi.graph(model,40,20),null);
 assert.equal(Multi.shortLabel("mars_barycenter"),"MAR");
});
test("M8h rejects wrong hashes, source, dates, bodies, samples or invented events",()=>{
 const ch=natal(),req=request(ch);
 const changes=[
  v=>v.format="wrong",
  v=>v.source.ephemeris_sha256="b".repeat(64),
  v=>v.source.position_model="geocentric",
  v=>v.source.coordinate_frame="J2000",
  v=>v.observer.latitude_deg=40,
  v=>v.observer.elevation_m=5,
  v=>v.natal_epoch_utc="2000-03-20T15:20:00Z",
  v=>v.natal_body="venus",
  v=>v.natal_longitude_deg=15,
  v=>v.start_utc="2026-11-08T00:00:00Z",
  v=>v.sample_minutes=30,
  v=>v.transit_bodies.reverse(),
  v=>v.aspects_deg=[0,90],
  v=>v.include_stations=false,
  v=>v.series[0].id="sun",
  v=>v.series[0].sample_count=5,
  v=>v.series[0].timeline[0].longitude_deg=77,
  v=>v.series[0].timeline[2].epoch_utc="2026-11-15T00:00:00Z",
  v=>v.events[0].aspect="invented",
  v=>v.events[0].aspect_target_deg=120,
  v=>v.events[0].residual_deg=1,
  v=>v.events[0].transit_body="pluto_barycenter",
  v=>v.events[1].direction="stationary",
  v=>v.events[1].velocity_deg_day=5,
  v=>v.events[1].uncertainty_seconds=1,
  v=>v.events[1].utc="2026-11-16T00:00:00Z",
  v=>v.limitations.station_search_not_all_turns_guaranteed=false
 ];
 for(const change of changes){
    const raw=result(req,ch);change(raw);
    const check=Multi.validate(raw,req,ch);
    assert.equal(check.ready,false,"admitted invalid source "+change.toString());
 }
 assert.equal(Multi.validate(null,req,ch).ready,false);
 assert.equal(Multi.validate(result(req,ch),req,null).ready,false);
});
test("M8h exact event time survives nearest-minute wheel selection",()=>{
 assert.equal(Multi.nearestMinute("2026-11-08T03:12:36Z"),
              "2026-11-08T03:13:00Z");
 assert.equal(Multi.nearestMinute("2026-11-08T03:12:15Z"),
              "2026-11-08T03:12:00Z");
 assert.equal(Multi.nearestMinute("invalid"),"");
});
test("M8h has three independent transit views and explicit-only private search",()=>{
 const parent=read("widgets/weather/StationMagickAstrologyPane.qml");
 const pane=read("widgets/weather/StationMagickTransitMultiPane.qml");
 const svc=read("services/weather/CelestialTransitMultiService.qml");
 const wheel=read("widgets/weather/StationMagickTransitChartPane.qml");
 const backend=read("scripts/weather/celestial_transit_multi.py");
 assert.match(parent,/WeatherServices\.CelestialTransitMultiService\s*\{/);
 assert.match(parent,/StationMagickTransitMultiPane\s*\{/);
 assert.match(parent,/label:"WHEEL"/);
 assert.match(parent,/label:"TIMELINE"/);
 assert.match(parent,/label:"MULTI"/);
 assert.match(parent,/onEventRequested: function\(exactUtc,body,kind\)/);
 assert.match(parent,/Multi\.nearestMinute\(exactUtc\)/);
 assert.match(parent,/astrology\.selectedMultiBody=body/);
 assert.match(parent,/astrology\.requestTransit\(minute\)/);
 assert.match(parent,/multiSource\.clearState\(\)/);
 assert.match(wheel,/inspectionTarget/);
 assert.match(wheel,/ESTIMATED STATION/);
 assert.match(pane,/StationMagickUtcDateField\s*\{/);
 assert.match(pane,/Multi\.graph\(model,plot\.width,plot\.height\)/);
 assert.match(pane,/signal eventRequested\(string exactUtc,string body,string kind\)/);
 assert.match(pane,/onClicked:atlas\.selectAspect\(modelData\.deg\)/);
 assert.match(pane,/atlas\.chooseEvent\(modelData\)/);
 assert.match(pane,/onWheel:function\(wheel\)/);
 assert.match(pane,/label:atlas\.busy\?"WAIT":"SEARCH"/);
 assert.match(svc,/stdinEnabled:true/);
 assert.match(svc,/calculator\.write\(JSON\.stringify\(multiSource\.pending\)\+"\\n"\)/);
 assert.match(svc,/Multi\.validate\(JSON\.parse\(source\),pending,natalChart\)/);
 assert.match(svc,/calculator\.running=false/);
 assert.match(backend,/from celestial_transit_timeline import/);
 assert.match(backend,/find_stations\(/);
 assert.match(backend,/search_crossings\(/);
 assert.match(backend,/sys\.stdin\.readline\(4097\)/);
 for(const source of [pane,svc]){
    for(const invalid of ["XMLHttpRequest","FileView {","localStorage",
        "Qt.openUrlExternally","writeFile(","PositionSource {",
        "console.log(","Math.random(","Date.now()"]){
       assert.ok(!source.includes(invalid),invalid);
    }
 }
});
