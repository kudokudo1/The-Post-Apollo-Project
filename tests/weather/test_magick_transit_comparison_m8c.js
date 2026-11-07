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
const Natal=policy("widgets/weather/StationMagickNatalWheelPolicy.js");
const Transit=policy("widgets/weather/StationMagickTransitComparisonPolicy.js");
const plain=x=>JSON.parse(JSON.stringify(x));
const BIRTH="2000-03-21T15:20:00Z",TRANSIT="2026-11-06T18:15:00Z";
function chart(epoch,longitudes=null) {
    const asc=29.1;
    const names=Array.from(Natal.TARGETS);
    return {
        format:Natal.FORMAT,epoch_utc:epoch,
        origin:"topocentric",frame:"true-ecliptic-of-date",
        position_model:"apparent",zodiac:"tropical",
        house_system:"whole-sign",ascendant_deg:asc,mc_deg:280.2,
        observer:{latitude_deg:38.9,longitude_deg:-76.8,elevation_m:0},
        provenance:{engine:"skyfield",ephemeris_sha256:"b".repeat(64),
            house_method:"true-equinox-horizon-meridian-geometric"},
        house_cusps_deg:Array.from({length:12},(_,i)=>30*i),
        positions:names.map((id,i)=>({
            id,naif_id:Natal.EXACT_NAIF[id],
            longitude_deg:longitudes?longitudes[i]:(i*29)%360,
            latitude_deg:0.1,distance_au:1.2
        }))
    };
}
function pair(a=chart(BIRTH),b=chart(TRANSIT)){
    return Transit.build(Natal.validate(a),Natal.validate(b),a,b,TRANSIT,3);
}
test("M8c constructs explicit UTC transit draft using current natal-site coordinates",()=>{
    const original=chart(BIRTH);
    const req=Transit.makeDraft(original,TRANSIT);
    assert.deepEqual(plain(req),{
        valid:true,sessionOnly:true,eventUtc:TRANSIT,
        latitude:38.9,longitude:-76.8,zodiac:"tropical",
        houseSystem:"whole-sign"
    });
    assert.equal(Transit.makeDraft(original,"2026-02-29T14:20:00Z"),null);
    assert.equal(Transit.makeDraft(original,"2026-11-06T18:15:00-05:00"),null);
    assert.equal(Transit.makeDraft(original,"2026-11-06"),null);
    assert.equal(Transit.makeDraft(original,"2026-11-06T18:15:01Z"),null);
    assert.equal(Transit.makeDraft(original,"2100-01-01T00:00:00Z"),null);
    const edited=plain(original);edited.provenance.ephemeris_sha256="unknown";
    assert.equal(Transit.makeDraft(edited,TRANSIT),null);
    edited.provenance.ephemeris_sha256="b".repeat(64);
    edited.zodiac="sidereal";
    assert.equal(Transit.makeDraft(edited,TRANSIT),null);
});
test("M8c refuses mismatched time, observer, JPL hash, frame, models and targets",()=>{
    const original=chart(BIRTH);
    assert.equal(pair().ready,true);
    const changes=[
        x=>x.epoch_utc="2026-11-05T18:15:00Z",
        x=>x.observer.latitude_deg=39.9,
        x=>x.observer.longitude_deg=-76.9,
        x=>x.observer.elevation_m=5,
        x=>x.provenance.ephemeris_sha256="a".repeat(64),
        x=>x.provenance.engine="unverified",
        x=>x.origin="geocentric",
        x=>x.frame="ecliptic-j2000",
        x=>x.position_model="geometric",
        x=>x.zodiac="sidereal",
        x=>x.house_system="equal",
        x=>x.positions[0].id="venus",
        x=>x.positions[2].naif_id=2,
        x=>x.positions.pop()
    ];
    for(const edit of changes){
        const t=chart(TRANSIT);edit(t);
        const r=pair(original,t);
        assert.equal(r.ready,false,"mismatched provenance or target accepted: "+edit.toString());
    }
    assert.equal(Transit.build(Natal.validate(original),Natal.validate(
        chart(TRANSIT)),original,chart(TRANSIT),"2026-11-05T00:00:00Z",3).ready,false);
    assert.equal(Transit.build(Natal.validate(original),Natal.validate(
        chart(TRANSIT)),original,chart(TRANSIT),TRANSIT,7).ready,false);
});
test("M8c computes signed planet shifts and cross-chart aspect tolerances",()=>{
    const n=[350,30,0,90,180,50,10,105,225,305];
    const t=[10,150,0,0,250,50,190,105,310,125];
    const m=pair(chart(BIRTH,n),chart(TRANSIT,t));
    assert.equal(m.ready,true,m.reason);
    assert.equal(m.format,Transit.FORMAT);
    assert.equal(m.deltas.length,10);
    assert.equal(m.deltas[0].id,"sun");
    assert.equal(m.deltas[0].signed_delta_deg,20);
    assert.equal(Transit.signedDelta(10,350),-20);
    assert.equal(Transit.separation(350,10),20);
    assert.ok(m.aspects.find(x=>x.transit_id==="sun"&&
        x.natal_id==="sun")===undefined);
    assert.ok(m.aspects.some(x=>x.transit_id==="moon"&&
        x.natal_id==="moon"&&x.name==="trine"&&x.orb_deg===0));
    assert.ok(m.aspects.some(x=>x.transit_id==="mercury"&&
        x.natal_id==="mercury"&&x.name==="conjunction"));
    assert.ok(m.aspects.every(x=>x.orb_deg<=3));
    assert.ok(m.aspects.every(x=>x.separation_deg<=180));
    assert.equal(m.limitations.exact_aspect_event_time_calculated,false);
    assert.equal(m.limitations.moving_planets_are_topocentric_at_natal_location,true);
});
test("M8c never accepts a selected-pair graph as either source",()=>{
    const n=chart(BIRTH),t=chart(TRANSIT);
    t.positions=t.positions.slice(0,2);
    assert.equal(pair(n,t).ready,false);
    t.positions=chart(TRANSIT).positions;
    const wrong=plain(n);
    wrong.positions.pop();
    assert.equal(pair(wrong,t).ready,false);
    assert.equal(pair(null,t).ready,false);
});
test("M8c is manual, source-bounded, privacy-preserving and keeps M8b paths",()=>{
    const astro=read("widgets/weather/StationMagickAstrologyPane.qml");
    const ui=read("widgets/weather/StationMagickTransitChartPane.qml");
    const service=read("services/weather/CelestialNatalChartService.qml");
    const previous=read("widgets/weather/StationMagickNatalChartWheelPane.qml");
    const backend=read("scripts/weather/celestial_natal_chart.py");
    assert.match(astro,/WeatherServices\.CelestialNatalChartService\s*\{/g);
    assert.equal((astro.match(/WeatherServices\.CelestialNatalChartService\s*\{/g)||[]).length,2);
    assert.match(astro,/function requestTransit\(instant\)/);
    assert.match(astro,/Transit\.makeDraft\(natalSource\.chartData,instant\)/);
    assert.match(astro,/return transitSource\.calculate\(draft\)/);
    assert.match(astro,/active: astrology\.visible && astrology\.natalMode/);
    assert.match(astro,/transitSource\.clearState\(\)/);
    assert.match(astro,/StationMagickTransitChartPane\s*\{/);
    assert.match(astro,/visible: astrology\.natalMode && astrology\.transitMode/);
    assert.match(astro,/onCalculateRequested: function\(instant\)/);
    assert.match(astro,/astrology\.requestTransit\(instant\)/);
    assert.match(astro,/StationMagickNatalChartWheelPane\s*\{/);
    assert.match(astro,/StationMagickCelestialInstrument\s*\{/);
    assert.match(ui,/label:"TRANSIT UTC"/);
    assert.match(ui,/Transit\.utc\(instant\)/);
    assert.match(ui,/Transit\.build\(/);
    assert.match(ui,/onWheel:function\(wheelEvent\)/);
    assert.match(ui,/Viewport\.inversePoint\(/);
    assert.match(ui,/transits\.relatedAspects\.forEach/);
    assert.match(ui,/natal\.planets\.forEach/);
    assert.match(ui,/transits\.comparison\.transit\.forEach/);
    assert.match(ui,/onVisibleChanged: if\(!visible\)clearEntry\(\)/);
    assert.match(previous,/Chart\.validate\(chartData\)/);
    assert.match(service,/stdinEnabled: true/);
    assert.match(backend,/sys\.stdin\.readline\(2049\)/);
    for(const forbidden of ["Process {","FileView {","XMLHttpRequest","writeFile(",
        "localStorage","Qt.openUrlExternally","Date.now()","Math.random("]){
        assert.ok(!ui.includes(forbidden),"unexpected side effect in UI: "+forbidden);
    }
});
