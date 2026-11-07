"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
function policy(file){
 const c=vm.createContext({});
 vm.runInContext(read(file).replace(/^\.pragma library\s*/,""),c);
 return c;
}
const Setup=policy("widgets/weather/StationMagickEventChartSetupPolicy.js");
const Request=policy("widgets/weather/StationMagickNatalRequestPolicy.js");
const Wheel=policy("widgets/weather/StationMagickNatalWheelPolicy.js");
const plain=o=>JSON.parse(JSON.stringify(o));
function valid(){
 return Setup.validate("2026-11-06","14:20","38.9","-76.8",
                       "tropical","whole-sign");
}
function calculated(req){
 return {
    format:Wheel.FORMAT,epoch_utc:req.epoch_utc,
    origin:"topocentric",frame:"true-ecliptic-of-date",
    position_model:"apparent",zodiac:req.zodiac,
    house_system:req.house_system,
    observer:{latitude_deg:req.latitude_deg,
        longitude_deg:req.longitude_deg,elevation_m:0},
    provenance:{engine:"skyfield",
        ephemeris_sha256:"a".repeat(64),
        house_method:"true-equinox-horizon-meridian-geometric"},
    ascendant_deg:255.57,mc_deg:184.37,
    house_cusps_deg:Array.from({length:12},(_,i)=>(240+30*i)%360),
    positions:Array.from(Wheel.TARGETS,(id,i)=>({
       id,naif_id:Wheel.EXACT_NAIF[id],longitude_deg:(14+31*i)%360,
       latitude_deg:0.2,distance_au:1.4
    }))
 };
}
test("M8b only explicit source tropical UTC event request passes",()=>{
 const draft=valid(),r=Request.fromDraft(draft);
 assert.ok(draft.valid);
 assert.equal(r.format,Request.FORMAT);
 assert.equal(r.epoch_utc,"2026-11-06T14:20:00Z");
 assert.equal(r.latitude_deg,38.9);
 assert.equal(r.longitude_deg,-76.8);
 assert.equal(r.zodiac,"tropical");
 assert.equal(r.house_system,"whole-sign");
 assert.equal(r.fromProfile,undefined);
 const sidereal=Setup.validate("2026-11-06","14:20","38.9",
                              "-76.8","sidereal","equal");
 assert.equal(sidereal.valid,true);
 assert.equal(Request.fromDraft(sidereal),null,
     "sidereal is unsupported until verified ayanamsa");
 assert.equal(Request.fromDraft({valid:true}),null);
 assert.equal(Request.fromDraft(Setup.validate(
     "2026-11-06","14:20","91","-76.8","tropical","equal")),null);
});
test("M8b validates complete source and guards exact observer/time match",()=>{
 const req=plain(Request.fromDraft(valid()));
 const data=calculated(req);
 assert.equal(Wheel.validate(data).ready,true);
 assert.equal(Request.matches(data,req),true);
 data.observer.longitude_deg=-78.8;
 assert.equal(Request.matches(data,req),false);
 data.observer.longitude_deg=req.longitude_deg;
 data.epoch_utc="2026-11-05T14:20:00Z";
 assert.equal(Request.matches(data,req),false);
 data.epoch_utc=req.epoch_utc;
 data.provenance.house_method="unverified";
 assert.equal(Request.matches(data,req),false);
 data.provenance.house_method="true-equinox-horizon-meridian-geometric";
 data.position_model="geometric";
 assert.equal(Request.matches(data,req),false);
 const partial=calculated(req);
 partial.positions.pop();
 assert.equal(Wheel.validate(partial).ready,false);
});
test("M8b launches source only on deliberate event form submit, not on navigation",()=>{
 const service=read("services/weather/CelestialNatalChartService.qml");
 const setup=read("widgets/weather/StationMagickEventChartSetupPane.qml");
 const astro=read("widgets/weather/StationMagickAstrologyPane.qml");
 const backend=read("scripts/weather/celestial_natal_chart.py");
 assert.match(setup,/signal calculateRequested\(var draft\)/);
 assert.match(setup,/label:"CALCULATE NATAL"/);
 assert.match(setup,/available:eventSetup\.draft\.valid&&eventSetup\.zodiac==="tropical"/);
 assert.match(setup,/SIDEREAL DISABLED \/\/ NO VERIFIED AYANAMSA/);
 assert.match(setup,/onVisibleChanged: \{/);
 assert.match(setup,/else clearInput\(\)/);
 assert.match(setup,/StationMagickUtcDateField\s*\{/);
 assert.match(setup,/Setup\.validate\(/);
 assert.match(astro,/WeatherServices\.CelestialNatalChartService\s*\{/);
 assert.match(astro,/onCalculateRequested: function\(draft\)/);
 assert.match(astro,/natalSource\.calculate\(draft\)/);
 assert.match(astro,/chartData: astrology\.fullChartData/);
 assert.match(astro,/property var fullChartData: null/);
 assert.match(service,/stdinEnabled: true/);
 assert.match(service,/onStarted: \{/);
 assert.match(service,/calculator\.write\(JSON\.stringify\(natalService\.pending\)\+"\\n"\)/);
 assert.match(service,/Request\.matches\(value,pending\)/);
 assert.match(service,/Wheel\.validate\(value\)/);
 assert.match(service,/if\(calculator\.running\) calculator\.running=false;/);
 assert.match(service,/onActiveChanged: if\(!active\)clearState\(\)/);
 assert.match(service,/command: \[\]/);
 assert.match(backend,/sys\.stdin\.readline\(2049\)/);
 assert.match(backend,/from skyfield\.framelib import true_equator_and_equinox_of_date/);
 for(const forbidden of ['"--latitude"', '"--longitude"',
    '"--instant"', '"--birth"', "FileView {", "XMLHttpRequest",
    "writeFile(", "localStorage", "Qt.openUrlExternally"]){
     assert.ok(!service.includes(forbidden),
         "private source or side effect not allowed: "+forbidden);
 }
});
test("M8b keeps full chart separate from existing JPL two-body pair",()=>{
 const astro=read("widgets/weather/StationMagickAstrologyPane.qml");
 assert.match(astro,/StationMagickCelestialInstrument\s*\{/);
 assert.match(astro,/visible: !astrology\.natalMode/);
 assert.match(astro,/StationMagickNatalChartWheelPane\s*\{/);
 assert.match(astro,/visible: astrology\.natalMode/);
 assert.match(astro,/chartData: astrology\.fullChartData/);
 assert.match(astro,/astrology\.celestialSource\.refresh\(\)/);
 assert.match(astro,/natalSource\.calculate\(draft\)/);
 assert.match(astro,/active: astrology\.visible/);
});
