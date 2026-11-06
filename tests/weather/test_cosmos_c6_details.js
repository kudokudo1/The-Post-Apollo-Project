"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const ctx=vm.createContext({});
vm.runInContext(read("widgets/weather/StationCosmosDetailPolicy.js")
  .replace(/^\.pragma library\s*$/m,""),ctx);
const detail=read("widgets/weather/StationCosmosDetailPane.qml");
const modes=read("widgets/weather/StationCosmosModesPane.qml");
const fixture=read("tests/weather/fixtures/C5PopulatedNativeShell.qml");

test("all source-backed event and navigation records remain inspectable",()=>{
 const snap={date:"2026-11-05",time:"13:00",
    planets:Array.from({length:7},(_,i)=>({name:"OBJECT "+i,
        altitude:i+1,azimuth:250+i,direction:"WSW"})),
    stars:Array.from({length:14},(_,i)=>({name:"STAR "+i,
        altitude:i+1,azimuth:i+30,direction:"NE",constellation:"ORION"})),
    constellations:[{name:"ORION",count:14,anchorStar:"STAR 7",
        anchorAltitude:37.7,anchorAzimuth:120,anchorDirection:"SE",
        starNames:["STAR 7"]}]};
 const iss={passes:Array.from({length:8},(_,i)=>({id:i}))};
 const eclipse={events:Array.from({length:12},(_,i)=>({date:"2027-01-01",event:"ECLIPSE "+i}))};
 assert.equal(ctx.records("planets",snap,null,null,false).length,7);
 assert.equal(ctx.records("stars",snap,null,null,true).length,14);
 assert.equal(ctx.records("stars",snap,null,null,false).length,1);
 assert.equal(ctx.records("iss",null,iss,null,false).length,8);
 assert.equal(ctx.records("eclipses",null,null,eclipse,false).length,12);
 assert.equal(ctx.records("iss",null,null,null,false).length,0);
 assert.equal(ctx.records("planets",{planets:"malformed"},null,null,false).length,0);
});

test("ISS displays full rise peak set and source-limited interpretation",()=>{
 const record={rise:{timeUtc:"2026-11-06 12:00Z",direction:"W",azimuth:270},
   culminate:{timeUtc:"2026-11-06 12:05Z",degrees:53.6,azimuth:210},
   set:{timeUtc:"2026-11-06 12:10Z",direction:"E",azimuth:80},
   durationLabel:"10:00",minutesUntilRise:32.2};
 const facts=ctx.fields("iss",record,{},false);
 assert.equal(facts.length,12);
 assert.equal(facts[0].value,"2026-11-06 12:00Z");
 assert.equal(facts[1].value,"2026-11-06 12:05Z");
 assert.equal(facts[2].value,"2026-11-06 12:10Z");
 assert.equal(facts[3].value,"53.6°");
 assert.equal(facts[9].value,"10:00");
 assert.equal(facts[11].value,"GEOMETRIC ONLY");
 assert.equal(facts.slice(8).length,4);
 assert.equal(ctx.disclaimer("iss",false).includes("NOT OPTICAL VISIBILITY"),true);
});

test("NASA is global date-only and USNO exposes both anchors and nav stars",()=>{
 const eclipse={events:[],dateScope:"2026-2030",eventCount:22,sourceName:"NASA GSFC"};
 const solar=ctx.fields("eclipses",{event:"ANNULAR SOLAR ECLIPSE",
  date:"2027-02-06",body:"SOLAR",phase:"ANNULAR",daysUntil:92},
  {eclipse},false);
 assert.equal(solar.length,12);
 assert.equal(solar[8].value,"NOT CALCULATED");
 assert.equal(solar[9].value,"NOT PROVIDED");
 assert.equal(solar[11].value,"NOT PROVIDED");
 assert.equal(ctx.disclaimer("eclipses",false).includes("LOCAL VISIBILITY"),true);
 const snap={date:"2026-11-06",time:"02:00"};
 const planet=ctx.fields("planets",{altitude:7.25,azimuth:225.9,
   direction:"SW"}, {snapshot:snap},false);
 assert.equal(planet[0].value,"7.3°");
 assert.equal(planet[1].value,"225.9°");
 assert.equal(planet[4].value,"02:00");
 const star=ctx.fields("stars",{name:"SIRIUS",constellation:"CANIS MAJOR",
    navStarNumber:19,altitude:36.2,azimuth:190.1,direction:"S"},
    {snapshot:snap},true);
 assert.equal(star[3].value,"CANIS MAJOR");
 const anchor=ctx.fields("stars",{name:"CANIS MAJOR",count:1,
    anchorStar:"SIRIUS",anchorAltitude:36.2,anchorAzimuth:190.1,
    starNames:["SIRIUS"],directions:["S"]},{snapshot:snap},false);
 assert.equal(anchor[5].value,"SIRIUS");
});

test("focused detail UI shows all twelve fields without paging, main scroll or extra providers",()=>{
 assert.match(modes,/id: subjectCards\s*StationCosmosDetailPane\s*\{/);
 assert.match(modes,/celestialSource: cosmosModePane\.celnav/);
 assert.match(modes,/issSource: cosmosModePane\.issSource/);
 assert.match(modes,/eclipseSource: cosmosModePane\.eclipseSource/);
 assert.match(detail,/readonly property var facts:/);
 assert.match(detail,/renderedFactCount: factGridRepeater\.count/);
 assert.match(detail,/columns: 3/);
 assert.match(detail,/model: detailsPane\.recordCount > 0 \? 12 : 0/);
 assert.match(detail,/height: Math\.max\(1,\(factGrid\.height-3\*factGrid\.spacing\)\/4\)/);
 assert.match(detail,/detailsPane\.facts\[index\]/);
 assert.doesNotMatch(detail,/factPage|visibleFacts|id: factControls|label: "DATA [<>]"/);
 assert.match(detail,/detailsPane\.selectedIndex = \(detailsPane\.selectedIndex/);
 assert.match(detail,/detailsPane\.starsAsNav = !detailsPane\.starsAsNav/);
 for(const forbidden of ["Process {","FileView {","Flickable {","XMLHttpRequest","Timer {"])
   assert.ok(!detail.includes(forbidden),forbidden);
 assert.match(fixture,/ECLIPSE_FULL_CALENDAR_MISSING/);
 assert.match(fixture,/STAR_NAVIGATION_DETAILS_MISSING/);
});
