"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const source=read("widgets/weather/StationMagickAnnualAtlasPolicy.js");
const ctx=vm.createContext({});
vm.runInContext(source.replace(/^\.pragma library\s*/,""),ctx);
const A=ctx;
const plain=v=>JSON.parse(JSON.stringify(v));
const DAY=86400000;
function fixture(year=2026,zone="UTC"){
 const start=Date.UTC(year,0,1),count=A.dayCount(year);
 const days=Array.from({length:count},(_,i)=>{
   const angle=(i*12.2)%360;
   return {date:new Date(start+i*DAY).toISOString().slice(0,10),
     day_index:i,month:new Date(start+i*DAY).getUTCMonth()+1,
     phase_angle_deg:angle,phase_id:A.phaseFor(angle),
     illumination:i%101};
 });
 const lunar_events=Array.from({length:50},(_,i)=>({
   kind:"moon",id:["new","first-quarter","full","last-quarter"][i%4],
   date:days[i*7].date,time_utc:new Date(start+i*7*DAY).toISOString()
 }));
 const solar_terms=A.SOLAR_TERMS.map((id,i)=>({
   kind:"solar",id,longitude_deg:i*15,major:i%6===0,
   date:days[i*15].date,time_utc:new Date(start+i*15*DAY).toISOString()
 }));
 return {format:A.FORMAT,year,timezone:zone,day_basis:"local-noon",
   source:{engine:"skyfield",ephemeris_sha256:"a".repeat(64)},
   days,lunar_events,solar_terms,
   calendar_markers:{daily_moon:days.map(d=>({
      date:d.date,phase_id:d.phase_id,illumination:d.illumination
   })),events:lunar_events.concat(solar_terms)}
 };
}
test("M7b validates exactly 365 or 366 real dated Moon rows",()=>{
 const model=A.validate(fixture(),2026,"UTC");
 assert.equal(model.ready,true,model.reason);
 assert.equal(model.days.length,365);
 assert.equal(A.dayIndex(model,"2026-01-01"),0);
 assert.equal(A.dayIndex(model,"2026-12-31"),364);
 assert.equal(A.dayIndex(model,"2027-01-01"),-1);
 assert.equal(A.monthRows(model,2).length,28);
 assert.equal(A.monthIndex(model,3),59);
 const leap=A.validate(fixture(2024),2024,"UTC");
 assert.equal(leap.ready,true,leap.reason);
 assert.equal(A.monthRows(leap,2).length,29);
 assert.equal(A.dayIndex(leap,"2024-02-29"),59);
});
test("M7b preserves measured phases rather than repeating decorative symbols",()=>{
 const data=fixture(),model=A.validate(data,2026,"UTC");
 assert.equal(A.phaseFor(0),"new");
 assert.equal(A.phaseFor(89),"first-quarter");
 assert.equal(A.phaseFor(179),"full");
 assert.equal(A.phaseFor(271),"last-quarter");
 assert.equal(A.phaseFor(360),"");
 assert.equal(model.days[1].phase_id,"new");
 assert.equal(A.selectedDay(model,500),null);
 assert.equal(A.eventsOnDay(model,model.days[0].date).length,2);
 data.days[0].phase_id="full";
 assert.equal(A.validate(data,2026,"UTC").ready,false);
});
test("M7b rejects missing or invented annual measurements and solar terms",()=>{
 let data=fixture();
 assert.equal(A.validate(data,2027,"UTC").ready,false);
 assert.equal(A.validate(data,2026,"America/New_York").ready,false);
 data.days.pop();
 assert.equal(A.validate(data,2026,"UTC").ready,false);
 data=fixture();
 data.solar_terms[0].longitude_deg=45;
 assert.equal(A.validate(data,2026,"UTC").ready,false);
 data=fixture();
 data.calendar_markers.daily_moon[0].illumination=100;
 assert.equal(A.validate(data,2026,"UTC").ready,false);
 data=fixture();
 data.source.ephemeris_sha256="unverified";
 assert.equal(A.validate(data,2026,"UTC").ready,false);
});
test("M7b mapping is circular and retains actual month lengths",()=>{
 const m=A.validate(fixture(),2026,"UTC"),total=m.days.length;
 assert.equal(A.indexAtAngle(0,-1,0,0,12),0);
 assert.equal(A.indexAtAngle(1,0,0,0,12),3);
 assert.equal(A.indexAtAngle(0,1,0,0,12),6);
 assert.equal(A.indexAtAngle(-1,0,0,0,12),9);
 assert.ok(A.monthIndex(m,4)-A.monthIndex(m,3)===31);
 assert.ok(A.monthIndex(m,3)-A.monthIndex(m,2)===28);
 assert.ok(A.angleFor(0,total)<A.angleFor(total-1,total));
});
test("M7b mounts genuine radial wheels and keeps the original forecast",()=>{
 const pane=read("widgets/weather/StationMagickAnnualCalendarPane.qml");
 const host=read("widgets/weather/StationMagickLunarSolarPane.qml");
 const service=read("services/weather/CelestialAnnualCalendarService.qml");
 const script=read("scripts/weather/celestial_annual_calendar.py");
 assert.match(host,/StationMagickAnnualCalendarPane\s*\{/);
 assert.match(host,/runtimeNowMs: lunarSolarPane\.runtimeNowMs/);
 assert.match(pane,/StationMagickForecastCalendarPane\s*\{/);
 for(const label of ["LUNAR YEAR","SOLAR YEAR","FORECAST",
                     "CALCULATE YEAR","MONTH","IANA ZONE","SET ZONE"])
   assert.ok(pane.includes(label),label);
 assert.match(pane,/Atlas\.angleFor\(/);
 assert.match(pane,/Atlas\.dayIndex\(/);
 assert.match(pane,/data\.lunar_events/);
 assert.match(pane,/data\.solar_terms/);
 assert.match(pane,/day\.illumination/);
 assert.match(pane,/function disc\(/);
 assert.match(pane,/MouseArea\s*\{/);
 assert.match(service,/onClicked|function calculate\(/);
 assert.match(service,/Quickshell\.configDir\+"\/scripts\/weather\/celestial_annual_calendar\.py"/);
 assert.match(service,/Atlas\.validate\(parsed,year,timezoneId\)/);
 assert.match(script,/almanac\.moon_phases\(kernel\)/);
 assert.match(script,/solar_index\.step_days = 3\.0/);
 for(const forbidden of ["XMLHttpRequest","WebEngineView","FileView {",
         "Qt.openUrlExternally","writeFile(","Date.now()"]) {
    assert.ok(!pane.includes(forbidden),"pane forbidden "+forbidden);
    assert.ok(!service.includes(forbidden),"service forbidden "+forbidden);
 }
});
