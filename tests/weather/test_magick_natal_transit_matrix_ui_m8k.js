"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
function policy(p){
    const ctx=vm.createContext({});
    vm.runInContext(read(p).replace(/^\.pragma library\s*/,""),ctx);
    return ctx;
}
const Matrix=policy("widgets/weather/StationMagickTransitMatrixPolicy.js");
const Natal=policy("widgets/weather/StationMagickNatalWheelPolicy.js");
const plain=o=>JSON.parse(JSON.stringify(o));
const BIRTH="2000-03-21T15:20:00Z";
function natal(){
    return {format:Natal.FORMAT,epoch_utc:BIRTH,
        origin:"topocentric",frame:"true-ecliptic-of-date",
        position_model:"apparent",zodiac:"tropical",house_system:"whole-sign",
        observer:{latitude_deg:38.9,longitude_deg:-76.8,elevation_m:0},
        provenance:{engine:"skyfield",ephemeris_sha256:"a".repeat(64),
            house_method:"true-equinox-horizon-meridian-geometric"},
        ascendant_deg:22.25,mc_deg:292.3,
        house_cusps_deg:Array.from({length:12},(_,i)=>i*30),
        positions:Natal.TARGETS.map((id,i)=>({
            id,naif_id:Natal.EXACT_NAIF[id],
            longitude_deg:i===0?10:i===3?25:(14+31*i)%360,
            latitude_deg:0,distance_au:1.2
        }))
    };
}
function request(ch=natal(),natals=["sun","venus"],
                 moving=["moon","mercury"]){
    return Matrix.request(ch,"2026-11-07",7,natals,moving,[0,60],60);
}
function result(req=request(),chart=natal()){
    const from=Date.parse(req.start_utc),to=Date.parse(req.end_utc);
    const lines=req.transit_bodies.map((id,i)=>({
        id,sample_count:169,
        timeline:[0,86400000,to-from].map((offset,j)=>({
            epoch_utc:new Date(from+offset).toISOString().slice(0,19)+"Z",
            longitude_deg:40+i*10+j*3
        }))
    }));
    const matrix=[];
    for(const moving of req.transit_bodies)
        for(const natal of req.natal_bodies)
            matrix.push({natal_body:natal,transit_body:moving,
                aspect_count:natal==="sun"&&moving==="moon"?1:0});
    return {
        format:Matrix.RESULT_FORMAT,
        source:{engine:"skyfield",ephemeris_sha256:req.expected_ephemeris_sha256,
            position_model:"topocentric-apparent",
            coordinate_frame:"true-ecliptic-of-date"},
        observer:{latitude_deg:req.latitude_deg,longitude_deg:req.longitude_deg,
            elevation_m:0},
        natal_epoch_utc:req.natal_epoch_utc,
        natal_bodies:req.natal_bodies.slice(),
        natal_longitudes:req.natal_bodies.map(id=>({id,
            longitude_deg:chart.positions.find(p=>p.id===id).longitude_deg})),
        transit_bodies:req.transit_bodies.slice(),
        start_utc:req.start_utc,end_utc:req.end_utc,
        sample_minutes:60,sample_count:169,
        aspects_deg:req.aspects_deg.slice(),include_stations:true,
        series:lines,matrix,
        events:[
            {utc:"2026-11-08T03:12:36Z",type:"aspect",natal_body:"sun",
                transit_body:"moon",aspect:"sextile",aspect_target_deg:60,
                direction:"prograde",residual_deg:0.00001},
            {utc:"2026-11-09T06:00:00Z",type:"station",natal_body:null,
                transit_body:"mercury",direction:"retrograde",
                longitude_deg:105.6,velocity_deg_day:.0003,
                uncertainty_seconds:60}
        ],
        limitations:{
            crossing_search_not_tangency_complete:true,
            station_search_not_all_turns_guaranteed:true,
            station_rate_scan_interval_minutes_max:15,
            station_velocity_central_difference_minutes:20,
            station_time_bracket_seconds:60,
            contact_time_precision_seconds:1,
            stations_not_natal_pairs:true,
            chart_uses_respective_equinoxes_of_date:true,
            medical_or_spiritual_causality_claim:false
        }
    };
}
test("M8k strict source request allows 3x3 seven-day, respects 31-day budget",()=>{
    const ch=natal(),q=request(ch);
    assert.deepEqual(plain(q),{
        format:Matrix.REQUEST_FORMAT,natal_epoch_utc:BIRTH,
        start_utc:"2026-11-07T00:00:00Z",
        end_utc:"2026-11-14T00:00:00Z",
        latitude_deg:38.9,longitude_deg:-76.8,
        expected_ephemeris_sha256:"a".repeat(64),
        natal_bodies:["sun","venus"],transit_bodies:["moon","mercury"],
        sample_minutes:60,aspects_deg:[0,60],include_stations:true
    });
    assert.ok(Matrix.request(ch,"2026-11-07",7,
        ["sun","venus","mars_barycenter"],
        ["moon","mercury","jupiter_barycenter"],[0,60,90],60));
    assert.equal(Matrix.request(ch,"2026-11-07",14,
        ["sun","venus","mars_barycenter"],
        ["moon","mercury","jupiter_barycenter"],[0,60],60),null);
    assert.ok(Matrix.request(ch,"2026-11-07",14,
        ["sun","venus"],["moon","mercury"],[0],60));
    assert.ok(Matrix.request(ch,"2026-11-07",31,
        ["sun"],["moon"],[0],60));
    for(const invalid of [
        [ch,"2026-02-29",7,["sun"],["moon"],[0],60],
        [ch,"2026-11-07",7,[],["moon"],[0],60],
        [ch,"2026-11-07",7,["sun","sun"],["moon"],[0],60],
        [ch,"2026-11-07",7,["mars"],["moon"],[0],60],
        [ch,"2026-11-07",7,["sun"],["moon","moon"],[0],60],
        [ch,"2026-11-07",7,["sun"],["moon"],[45],60],
        [ch,"2026-11-07",7,["sun"],["moon"],[60,60],60],
        [ch,"2026-11-07",7,["sun"],["moon"],[60],15],
        [ch,"2099-12-31",7,["sun"],["moon"],[60],60],
    ])assert.equal(Matrix.request(...invalid),null);
    const bad=natal();bad.positions[1].naif_id=2;
    assert.equal(request(bad),null);
});
test("M8k verifies each natal longitude, aspect count and once-only stations",()=>{
    const ch=natal(),q=request(ch),raw=result(q,ch);
    const verified=Matrix.validate(raw,q,ch);
    assert.equal(verified.ready,true,verified.reason);
    assert.equal(verified.matrix.length,4);
    assert.equal(verified.events.length,2);
    assert.equal(verified.events.filter(x=>x.type==="station").length,1);
    assert.equal(verified.events[1].natal_body,null);
    assert.equal(verified.series.length,2);
    assert.equal(verified.sample_count,169);
    const single=Matrix.filtered(verified,"sun","moon","aspect",false);
    assert.equal(single.length,1);
    assert.equal(single[0].aspect,"sextile");
    assert.equal(Matrix.filtered(verified,"sun","mercury","ALL",false).length,0);
    assert.equal(Matrix.filtered(verified,"","mercury","station",false).length,1);
    assert.equal(Matrix.filtered(verified,"","","ALL",false).length,2);
    assert.equal(Matrix.filtered(verified,"","","ALL",true)[0].type,"station");
    assert.equal(Matrix.page(verified,"","","ALL",false,0).total,2);
    assert.equal(Matrix.nearestMinute("2026-11-08T03:12:36Z"),
                 "2026-11-08T03:13:00Z");
    assert.equal(Matrix.shortName("mars_barycenter"),"MAR");
});
test("M8k rejects corrupted kernel, site, period, natal IDs, series, pairs or events",()=>{
    const ch=natal(),req=request(ch);
    const changes=[
        v=>v.format="invented",
        v=>v.source.ephemeris_sha256="b".repeat(64),
        v=>v.source.position_model="geocentric",
        v=>v.source.coordinate_frame="J2000",
        v=>v.observer.latitude_deg=40,
        v=>v.observer.elevation_m=1,
        v=>v.natal_epoch_utc="2000-03-20T15:20:00Z",
        v=>v.start_utc="2026-11-08T00:00:00Z",
        v=>v.natal_bodies.reverse(),
        v=>v.natal_longitudes[0].longitude_deg=20,
        v=>v.natal_longitudes[1].id="moon",
        v=>v.transit_bodies.reverse(),
        v=>v.sample_minutes=30,
        v=>v.sample_count=3,
        v=>v.series[0].id="sun",
        v=>v.series[0].timeline[0].longitude_deg=361,
        v=>v.series[0].timeline[2].epoch_utc="2026-11-15T00:00:00Z",
        v=>v.matrix[0].aspect_count=2,
        v=>v.matrix[0].natal_body="moon",
        v=>v.events[0].natal_body="venus",
        v=>v.events[0].aspect_target_deg=90,
        v=>v.events[0].residual_deg=0.5,
        v=>v.events[1].natal_body="sun",
        v=>v.events[1].velocity_deg_day=8,
        v=>v.events[1].uncertainty_seconds=1,
        v=>v.events[1].utc="2026-11-15T00:00:00Z",
        v=>v.limitations.stations_not_natal_pairs=false
    ];
    for(const change of changes){
        const row=result(req,ch);change(row);
        const out=Matrix.validate(row,req,ch);
        assert.equal(out.ready,false,"invalid JPL result accepted: "+change);
    }
    assert.equal(Matrix.validate(null,req,ch).ready,false);
    assert.equal(Matrix.validate(result(req,ch),req,null).ready,false);
});
test("M8k preserves prior three views and has explicit, cancelable private JPL matrix",()=>{
    const astro=read("widgets/weather/StationMagickAstrologyPane.qml");
    const pane=read("widgets/weather/StationMagickTransitMatrixPane.qml");
    const svc=read("services/weather/CelestialTransitMatrixService.qml");
    const wheel=read("widgets/weather/StationMagickTransitChartPane.qml");
    const python=read("scripts/weather/celestial_transit_matrix.py");
    assert.match(astro,/StationMagickTransitMatrixPane\s*\{/);
    assert.match(astro,/WeatherServices\.CelestialTransitMatrixService\s*\{/);
    assert.match(astro,/label:"MATRIX"/);
    for(const label of ["WHEEL","TIMELINE","MULTI"])
        assert.ok(astro.includes('label:"'+label+'"'));
    assert.match(astro,/Matrix\.nearestMinute\(exactUtc\)/);
    assert.match(astro,/onEventRequested:function\(exactUtc,natalBody,transitBody,kind\)/);
    assert.match(astro,/astrology\.selectedNatalReference=natalBody/);
    assert.match(astro,/astrology\.requestTransit\(minute\)/);
    assert.match(wheel,/inspectionNatal/);
    assert.match(pane,/StationMagickUtcDateField\s*\{/);
    assert.match(pane,/Matrix\.page\(/);
    assert.match(pane,/Matrix\.request\(/);
    assert.match(pane,/model:atlas\.eventPage\.items/);
    assert.match(pane,/signal eventRequested\(string exactUtc,string natalBody,/);
    assert.match(pane,/STATION = MOVING ONLY/);
    assert.match(svc,/stdinEnabled:true/);
    assert.match(svc,/runner\.write\(JSON\.stringify\(matrixSource\.pending\)\+"\\n"\)/);
    assert.match(svc,/Matrix\.validate\(JSON\.parse\(text\),pending,natalChart\)/);
    assert.match(svc,/onActiveChanged:if\(!active\)clearState\(\)/);
    assert.match(python,/from celestial_transit_multi import/);
    assert.match(python,/search_crossings\(/);
    assert.match(python,/find_stations\(/);
    assert.match(python,/sys\.stdin\.readline\(4097\)/);
    for(const src of [pane,svc]){
        for(const bad of ["XMLHttpRequest","FileView {","localStorage",
                "Qt.openUrlExternally","writeFile(","console.log(",
                "Date.now()","Math.random("])
            assert.ok(!src.includes(bad),bad);
    }
});
