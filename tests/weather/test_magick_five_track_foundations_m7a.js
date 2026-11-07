"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
function moduleJs(file){
  const context=vm.createContext({});
  vm.runInContext(read(file).replace(/^\.pragma library\s*/m,""),context);
  return context;
}
const cal=moduleJs("widgets/weather/StationMagickForecastCalendarPolicy.js");
const hours=moduleJs("widgets/weather/StationMagickPlanetaryHoursPolicy.js");
const timing=moduleJs("widgets/weather/StationMagickTimingAtlasPolicy.js");
const setup=moduleJs("widgets/weather/StationMagickEventChartSetupPolicy.js");
const agrippa=moduleJs("widgets/weather/StationMagickAgrippaCorrespondencePolicy.js");
const symbols=moduleJs("widgets/weather/StationMagickSymbolismPolicy.js");
const journal=moduleJs("widgets/weather/StationMagickJournalDraftPolicy.js");
const plain=v=>JSON.parse(JSON.stringify(v));
const forecast=[
 {date:"2026-11-06",sunrise:"6:30 AM",sunset:"5:10 PM",
  moonPhase:"Waning Crescent",moonIllumination:18},
 {date:"2026-11-07",sunrise:"6:31 AM",sunset:"5:09 PM",
  moonPhase:"New Moon",moonIllumination:0},
 {date:"2026-11-08",sunrise:"6:32 AM",sunset:"5:08 PM",
  moonPhase:"Waxing Crescent",moonIllumination:8},
 {date:"2026-11-09",sunrise:"6:33 AM",sunset:"5:07 PM",
  moonPhase:"Waxing Crescent",moonIllumination:14}
];

test("M7a calendar reads exactly the daily provider phase, illumination and light boundaries",()=>{
 const before=JSON.stringify(forecast),model=cal.build(forecast);
 assert.equal(model.ready,true,model.reason);
 assert.equal(model.count,4);
 assert.equal(model.firstDate,"2026-11-06");
 assert.equal(model.lastDate,"2026-11-09");
 assert.equal(model.rows[0].weekday,"FRI");
 assert.equal(model.rows[0].phase,"WANE CRESCENT");
 assert.equal(model.rows[0].illumination,18);
 assert.equal(model.rows[0].daylightMinutes,640);
 assert.equal(model.rows[1].phase,"NEW");
 assert.equal(model.rows[1].illumination,0,"zero is a valid measured percentage");
 assert.equal(model.rows[1].daylightMinutes,638);
 assert.equal(cal.initialDate(model,"2026-11-08 10:30"),"2026-11-08");
 assert.equal(cal.initialDate(model,"2026-11-20 10:30"),model.firstDate);
 assert.equal(cal.select(model,"2026-11-08").illumination,8);
 assert.equal(cal.select(model,"2026-11-12"),null);
 assert.equal(JSON.stringify(forecast),before,"observation source immutable");
});
test("M7a calendar refuses invented/invalid dates and unknown physical readings",()=>{
 assert.equal(cal.build([]).ready,false);
 const missing=plain(forecast);
 missing[1].date="2026-11-10";
 assert.equal(cal.build(missing).ready,false);
 assert.equal(cal.stamp("2026-02-29"),null);
 assert.notEqual(cal.stamp("2024-02-29"),null);
 const altered=plain(forecast);altered[0].moonPhase="mystery";
 altered[0].moonIllumination=999;
 altered[0].sunrise="--";
 const result=cal.build(altered);
 assert.equal(result.ready,true);
 assert.equal(result.rows[0].phase,"PHASE UNKNOWN");
 assert.equal(result.rows[0].illumination,null);
 assert.equal(result.rows[0].daylightMinutes,null);
 assert.equal(result.rows.length,4,"does not fabricate full lunar cycle");
});
test("M7a timing reuses M6d exact 24 historical local-clock hours",()=>{
 const days=plain(timing.availableDates(forecast,hours.validDate,hours.nextDate));
 assert.deepEqual(days,["2026-11-06","2026-11-07","2026-11-08"]);
 assert.deepEqual(plain(timing.availableDates([],hours.validDate,hours.nextDate)),[]);
 assert.deepEqual(plain(timing.availableDates(
  [forecast[0],forecast[0]],hours.validDate,hours.nextDate)),[]);
 const plan=hours.build(forecast,"",days[1]),chart=timing.histogram(plan);
 assert.equal(plan.ready,true,plan.reason);
 assert.ok(chart);
 assert.equal(chart.phases.day,12);
 assert.equal(chart.phases.night,12);
 assert.equal(Object.values(chart.counts).reduce((a,b)=>a+b,0),24);
 assert.equal(timing.choose(plan,12).phase,"night");
 assert.equal(timing.choose(plan,23).endLabel,"6:32 AM +1D");
 assert.equal(timing.choose(plan,24),null);
 assert.equal(timing.histogram({ready:true,hours:[]}),null);
 assert.equal(plan.basis,"CIVIL CLOCK // DST TRANSITIONS NOT RESOLVED");
});
test("M7a event input contract respects UTC date, location, zodiac and houses",()=>{
 const v=setup.validate("2026-11-06","14:20","38.9","-76.8","tropical","whole-sign");
 assert.equal(v.valid,true,v.errors.join(","));
 assert.equal(v.eventUtc,"2026-11-06T14:20:00Z");
 assert.equal(v.latitude,38.9);
 assert.equal(v.longitude,-76.8);
 assert.equal(v.chartCalculated,false);
 assert.equal(v.sessionOnly,true);
 assert.match(v.missing,/MULTI-BODY EPHEMERIS/);
 assert.equal(setup.validate("2026-02-29","25:00","91","200",
    "tropical","equal").valid,false);
 assert.equal(setup.validate("2024-02-29","00:00","-90","180",
    "sidereal","equal").valid,true);
 assert.equal(setup.validate("2026-11-06","12:50","1e6","0",
    "tropical","whole-sign").valid,false);
 assert.equal(setup.validate("2026-11-06","12:50","0","0",
    "unknown","whole-sign").valid,false);
});
test("M7a symbolism is sourced to Agrippa without invented associations",()=>{
 const a=symbols.build(agrippa.PLANETS,agrippa.CATEGORIES,agrippa.SOURCE,
                       "metals","silver");
 assert.equal(a.ready,true,a.reason);
 assert.equal(a.count,4,"substring includes quicksilver");
 assert.equal(a.sourceId,agrippa.SOURCE.id);
 const shared=plain(symbols.associated(a,"silver","metals"));
 assert.deepEqual(shared.map(r=>r.planet),["jupiter","venus","moon"]);
 assert.ok(shared.every(r=>r.sourceId===agrippa.SOURCE.id));
 assert.equal(symbols.associated(a,"quicksilver","metals").length,1);
 assert.equal(symbols.associated(a,"silver","plants").length,0);
 assert.equal(symbols.build([],agrippa.CATEGORIES,agrippa.SOURCE,"all","").ready,false);
 assert.equal(symbols.build(agrippa.PLANETS,agrippa.CATEGORIES,
               {id:"other"},"all","").ready,false);
 const p=symbols.place(0,400,220);
 assert.ok(p);
 assert.equal(symbols.hit(0,400,220,p.x,p.y),true);
 assert.equal(symbols.hit(0,400,220,0,0),false);
});
test("M7a journal remains bounded, ephemeral and has no persistence semantics",()=>{
 const draft=journal.summary("  Night Notes  "," First thought.\n Second one. ");
 assert.equal(draft.valid,true);
 assert.equal(draft.title,"Night Notes");
 assert.equal(draft.wordCount,4);
 assert.equal(draft.sessionOnly,true);
 assert.equal(draft.persisted,false);
 assert.match(draft.provenance,/NOT SAVED/);
 assert.equal(journal.summary("a".repeat(97),"").valid,false);
 assert.equal(journal.summary("a","b".repeat(2049)).valid,false);
 assert.equal(journal.summary("", "").hasContent,false);
 assert.equal(journal.summary("Observation","").hasContent,true);
});
test("M7a new routes, chart controls and privacy ownership are wired without new actors",()=>{
 const subject=read("widgets/weather/StationMagickSubjectPane.qml");
 const lunar=read("widgets/weather/StationMagickLunarSolarPane.qml");
 const astro=read("widgets/weather/StationMagickAstrologyPane.qml");
 const sources=[
 "widgets/weather/StationMagickForecastCalendarPane.qml",
 "widgets/weather/StationMagickTimingAtlasPane.qml",
 "widgets/weather/StationMagickEventChartSetupPane.qml",
 "widgets/weather/StationMagickSymbolismPane.qml",
 "widgets/weather/StationMagickJournalDraftPane.qml"];
 const uis=sources.map(read);
 assert.match(lunar,/StationMagickAnnualCalendarPane\s*\{/);
 assert.match(lunar,/weatherService: lunarSolarPane\.weatherService/);
 // EVENT SETUP remains available in PAIR; M8c reuses the control for NATAL/TRANSITS.
 assert.match(astro,/: "EVENT SETUP"/);
 assert.match(astro,/else astrology\.eventSetupOpen=true;/);
 assert.match(astro,/StationMagickEventChartSetupPane\s*\{/);
 assert.match(astro,/onCloseRequested: astrology\.eventSetupOpen=false/);
 assert.match(subject,/magick\/planetary\/timing/);
 assert.match(subject,/magick\/divination\/symbolism/);
 assert.match(subject,/magick\/grimoire\/journal/);
 for(const token of ["StationMagickTimingAtlasPane",
                     "StationMagickSymbolismPane",
                     "StationMagickJournalDraftPane"])assert.ok(subject.includes(token));
 assert.match(uis[0],/Calendar\.build\(/);
 assert.match(uis[0],/DAILY FORECAST SNAPSHOTS/);
 assert.match(uis[1],/Hours\.build\(daily,"",targetDate\)/);
 assert.match(uis[1],/DST ACTUAL ELAPSED TIME UNVERIFIED/);
 assert.match(uis[2],/SESSION-ONLY INPUT/);
 assert.match(uis[2],/CALCULATE NATAL/);
 assert.match(uis[2],/SIDEREAL DISABLED \/\/ NO VERIFIED AYANAMSA/);
 assert.match(uis[3],/symbols?/i);
 assert.match(uis[3],/AGRIPPA BOOK I, 1651/);
 assert.match(uis[4],/TextEdit\.PlainText/);
 assert.match(uis[4],/CONFIRM CLEAR/);
 assert.match(uis[4],/onVisibleChanged:/);
 assert.match(uis[4],/UNSAVED SESSION DRAFT/);
 for(const src of uis.concat([lunar,astro,subject])){
  for(const forbidden of ["Process {","FileView {","XMLHttpRequest",
       "Qt.openUrlExternally","WebEngineView","writeFile","localStorage"]){
   // The old astronomy/lunar host may include a legacy source display, but
   // none of the newly added M7a components may own a side-effect actor.
   if(uis.includes(src))assert.ok(!src.includes(forbidden),forbidden);
  }
 }
});
