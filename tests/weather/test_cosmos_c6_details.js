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


test("C26 NASA eclipse highlights are pinned above one bounded calendar and retain C6 inspector",()=>{
 const board=read("widgets/weather/StationCosmosEclipseBoard.qml");
 assert.match(modes,/kind === "eclipses" \? eclipseBoardComponent/);
 assert.match(modes,/id: eclipseBoardComponent\s*StationCosmosEclipseBoard\s*\{/);
 assert.match(modes,/eclipseSource: cosmosModePane\.eclipseSource/);
 assert.match(board,/objectName: "cosmos-c26-eclipse-sticky-header"/);
 assert.match(board,/objectName: "cosmos-c26-eclipse-highlight-row"/);
 assert.match(board,/objectName: "cosmos-c26-eclipse-highlight"/);
 assert.match(board,/eclipseBoard\.eclipseSource\.nextSolar/);
 assert.match(board,/eclipseBoard\.eclipseSource\.nextLunar/);
 assert.match(board,/objectName: "cosmos-c26-eclipse-catalog-frame"/);
 assert.match(board,/anchors\.top: fixedEclipseHeader\.bottom/);
 assert.match(board,/objectName: "cosmos-c26-eclipse-catalog-scroll"/);
 assert.match(board,/contentHeight: eclipseRows\.implicitHeight/);
 assert.match(board,/boundsBehavior: Flickable\.StopAtBounds/);
 assert.match(board,/objectName: "cosmos-c26-eclipse-event-card"/);
 assert.match(board,/model: eclipseBoard\.recordCount/);
 assert.match(board,/NeonScrollBar\s*\{[\s\S]*?flickable: eclipseScroll/);
 assert.match(board,/StationCosmosDetailPane\s*\{[\s\S]*?kind: "eclipses"/);
 assert.match(board,/readonly property int renderedFactCount: eclipseDetails\.renderedFactCount/);
 assert.match(board,/property alias selectedIndex: eclipseDetails\.selectedIndex/);
 assert.match(board,/function inspectFeatured\(row\)/);
 assert.match(board,/onClicked: eclipseBoard\.inspectRecord\(index\)/);
 assert.match(board,/onClicked: eclipseBoard\.inspecting = false/);
 assert.match(board,/LOCAL VISIBILITY \+ CONTACTS NOT CALCULATED/);
 assert.equal((board.match(/Flickable\s*\{/g)||[]).length,1);
 for(const forbidden of ["Process {","FileView {","XMLHttpRequest","ScrollView {"])
   assert.ok(!board.includes(forbidden),forbidden);
});


test("C27 SKY NOW uses real USNO positions with pinned compass and bounded star catalog",()=>{
 const sky=read("widgets/weather/StationCosmosStarsBoard.qml");
 assert.match(modes,/kind === "stars" \? starsBoardComponent/);
 assert.match(modes,/id: starsBoardComponent\s*StationCosmosStarsBoard\s*\{/);
 assert.match(modes,/celestialSource: cosmosModePane\.celnav/);
 assert.match(sky,/objectName: "cosmos-c27-sky-now-sticky-header"/);
 assert.match(sky,/objectName: "cosmos-c27-sky-position-plot"/);
 assert.match(sky,/objectName: "cosmos-c27-plotted-usno-star"/);
 assert.match(sky,/starBoard\.stars\[index\]/);
 assert.match(sky,/Math\.sin\(azRadians\)\*radiusAtAltitude/);
 assert.match(sky,/Math\.cos\(azRadians\)\*radiusAtAltitude/);
 assert.match(sky,/90-Math\.max\(0,Math\.min\(90,alt\)\)/);
 assert.match(sky,/onClicked: starBoard\.inspectStar\(plottedStar\.index\)/);
 assert.match(sky,/objectName: "cosmos-c27-featured-star-reading"/);
 assert.match(sky,/featuredAnchor\.anchorStar/);
 assert.match(sky,/featuredAnchor\.anchorAltitude/);
 assert.match(sky,/featuredAnchor\.anchorAzimuth/);
 assert.match(sky,/objectName: "cosmos-c27-star-catalog-frame"/);
 assert.match(sky,/anchors\.top: fixedSkyHeader\.bottom/);
 assert.match(sky,/objectName: "cosmos-c27-star-catalog-scroll"/);
 assert.match(sky,/contentHeight: starRows\.implicitHeight/);
 assert.match(sky,/boundsBehavior: Flickable\.StopAtBounds/);
 assert.match(sky,/objectName: "cosmos-c27-star-catalog-record"/);
 assert.match(sky,/NeonScrollBar\s*\{[\s\S]*?flickable: starCatalogScroll/);
 assert.match(sky,/StationCosmosDetailPane\s*\{[\s\S]*?kind: "stars"/);
 assert.match(sky,/property alias starsAsNav: starDetails\.starsAsNav/);
 assert.match(sky,/property alias selectedIndex: starDetails\.selectedIndex/);
 assert.match(sky,/readonly property int renderedFactCount: starDetails\.renderedFactCount/);
 assert.match(sky,/onClicked: starBoard\.inspectStar\(index\)/);
 assert.match(sky,/onClicked: starBoard\.inspecting = false/);
 assert.match(sky,/NOT FULL SKY OR OPTICAL VISIBILITY/);
 assert.equal((sky.match(/Flickable\s*\{/g)||[]).length,1);
 for(const forbidden of ["Process {","FileView {","XMLHttpRequest","ScrollView {"])
   assert.ok(!sky.includes(forbidden),forbidden);
});
