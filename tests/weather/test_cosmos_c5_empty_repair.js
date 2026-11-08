"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const run=p=>{
  const ctx=vm.createContext({});
  vm.runInContext(read(p).replace(/^\.pragma library\s*$/m,""),ctx);
  return ctx;
};
const calendar=run("widgets/weather/StationCosmosCivilCalendarPolicy.js");
const clock=run("widgets/weather/StationCosmosPlanetEventPolicy.js");
const modes=run("widgets/weather/StationCosmosModePolicy.js");
const cosmos=run("widgets/weather/StationCosmosSubjectPanelPolicy.js");
const surface=read("widgets/weather/StationWorkspaceSurface.qml");
const pane=read("widgets/weather/StationCosmosSubjectPane.qml");
const focus=read("widgets/weather/StationCosmosModesPane.qml");
const sky=read("widgets/weather/StationSky.qml");

test("C5 native workspace forwards instrument mode clicks into active navigation",()=>{
  assert.match(surface,/StationCosmosSubjectPane\s*\{[\s\S]*?onRouteRequested: function\(path\) \{ surface\.routeRequested\(path\); \}/);
  assert.match(pane,/StationCosmosModesPane\s*\{[\s\S]*?onRouteRequested: function\(path\) \{[\s\S]*?cosmosPane\.routeRequested\(path\)/);
  assert.match(focus,/onClicked: cosmosModePane\.routeRequested\(modelData\.route\)/);
  const routes=[
    "cosmos/sun/position","cosmos/sun/twilight",
    "cosmos/sun/suvi","cosmos/sun/xray","cosmos/sun/flares",
    "cosmos/sun/cycle","cosmos/planets-stars/planet-clock",
    "cosmos/planets-stars/celestial-fix",
    "cosmos/planets-stars/constellations",
    "cosmos/events/meteors","cosmos/events/eclipses","cosmos/events/iss"
  ];
  for(const route of routes) {
    assert.ok(cosmos.routeInfo(route),route);
    assert.ok(modes.family(route)!=="",route);
  }
});

test("C5 civil date uses only existing verified timezone, not system timezone",()=>{
  const timestamp=Date.parse("2026-11-05T03:30:00Z");
  assert.equal(calendar.localCivilDate(timestamp,-300),"2026-11-04");
  assert.equal(calendar.localCivilDate(timestamp,540),"2026-11-05");
  assert.equal(calendar.localCivilDate(timestamp,null),"");
  assert.equal(calendar.localCivilDate(timestamp,""),"");
  assert.equal(calendar.localCivilDate(timestamp,1000),"");
  assert.equal(calendar.localCivilDate(timestamp,NaN),"");
  assert.equal(calendar.localCivilDate(0,-300),"");
  assert.equal(calendar.exactDay("2026-02-30"),"");
  assert.equal(calendar.exactDay("--"),"");
  assert.equal(calendar.focusedDate("--",timestamp,-300,true),"2026-11-04");
  assert.equal(calendar.focusedDate("2026-11-01",timestamp,null,true),"2026-11-01");
  assert.equal(calendar.focusedDate("--",timestamp,null,true),"");
  assert.equal(calendar.focusedDate("--",timestamp,-300,false),"--");
  assert.match(sky,/CosmosCalendar\.focusedDate\(/);
  assert.match(sky,/openMeteoCivilOffsetAvailable/);
  assert.match(sky,/date: sky\.sourceOnly \? sky\.focusedCivilDate : sky\.astronomySummary\.date/);
  assert.match(focus,/readonly property string civilDate:/);
  assert.match(focus,/skyFeed\.focusedCivilDate : ""/);
  assert.match(focus,/ClockPolicy\.clockRows\([\s\S]*?civilDate\)/);
  assert.match(focus,/solarDate: cosmosModePane\.civilDate/);
});

test("No-source clock retains five planet categories and shows provider errors",()=>{
  const blank=clock.clockRows([],"");
  assert.equal(blank.length,5);
  assert.equal(blank.every(r=>!r.available && r.events.length===0),true);
  assert.match(focus,/readonly property var displayedPlanetRows:/);
  assert.match(focus,/id: planetClock\s*[\s\S]*?StationCosmosPlanetClockFace\s*\{/);
  assert.match(focus,/datedRows: cosmosModePane\.planetRows/);
  assert.match(focus,/sourceReady: !!cosmosModePane\.planetSource/);
  const dial=read("widgets/weather/StationCosmosPlanetClockFace.qml");
  assert.match(dial,/readonly property int renderedRowCount: Day\.PLANETS\.length/);
  assert.match(dial,/Day\.datedEvents\(/);
  assert.match(dial,/objectName: "cosmos-c28-clock-dial-canvas"/);
  assert.match(dial,/objectName: "cosmos-c5-planet-event-marker"/);
  assert.doesNotMatch(dial,/clockLane|LINEAR LANE|Flickable\s*\{/);
  for(const planet of ["MERCURY","VENUS","MARS","JUPITER","SATURN"])
    assert.ok(focus.includes('name:"'+planet+'"'),planet);
  for(const signal of [
    "USNO NEEDS VALID DATE, COORDINATES AND UTC OFFSET",
    "SOURCE REQUEST FAILED","SOURCE RECEIVING",
    "LOCATION COORDINATES UNAVAILABLE",
    "SOLAR MODEL NEEDS LOCAL DATE, LOCATION AND UTC OFFSET",
    "NO ACTIVE OR UPCOMING SHOWER IN THE SOURCE WINDOW"
  ])assert.ok(focus.includes(signal),signal);
  assert.match(focus,/visible: !cosmosModePane\.cards \|\| cosmosModePane\.cards\.length === 0/);
  assert.match(focus,/id: meteorScroll/);
  assert.match(focus,/contentHeight: meteorCards\.implicitHeight/);
  assert.match(focus,/sourceOnly: true/);
  for(const src of [calendar,clock,modes]) assert.ok(src);
});

test("C5 focused hidden astronomy acquisition uses route, not visual geometry",()=>{
  const gates=sky.match(/active: \(sky\.sourceOnly \|\| sky\.visible\)/g)||[];
  assert.equal(gates.length,6,"Moon, Eclipse, Celnav, ISS, Planets, Meteor are route-scoped");
  assert.match(focus,/SOURCE INACTIVE \/\/ ROUTE ACTIVATION FAILED/);
  assert.match(focus,/SOURCE IDLE \/\/ USE RETRY/);
  assert.match(focus,/label: "RETRY SOURCE"/);
  assert.match(focus,/cosmosModePane\.selectedProvider\.refresh\(\)/);
});

test("C5 populated source-to-render contracts use actual provider fields",()=>{
  assert.equal(calendar.localCivilMinute(Date.parse("2026-11-05T03:30:00Z"),-300),1350);
  assert.equal(calendar.localCivilMinute(Date.parse("2026-11-05T03:30:00Z"),540),750);
  assert.equal(calendar.localCivilMinute(Date.parse("2026-11-05T03:30:00Z"),null),-1);
  assert.equal(calendar.localCivilMinute(0,-300),-1);
  assert.match(sky,/sourceOnly \? focusedCivilDate : skyCycle\.date/);
  assert.match(sky,/CosmosCalendar\.localCivilMinute\(/);
  assert.match(focus,/focusedLocalMinute/);
  assert.match(focus,/item\.rise\.timeUtc/);
  assert.match(focus,/item\.culminate\.timeUtc/);
  assert.match(focus,/meteorSource\.activeShowers/);
  assert.match(focus,/seenShower\[item\.name\]/);
  for (const anchor of [
    'objectName: "cosmos-c5-sun-path"',
    'StationCosmosPlanetClockFace {',
    'id: subjectCards',
    'objectName: "cosmos-c5-meteor-card"'
  ]) assert.ok(focus.includes(anchor),anchor);
  assert.match(focus,/StationCosmosDetailPane\s*\{/);
});


test("C25 Meteors pins IAU next peaks outside the only inner catalog scroll",()=>{
  assert.match(focus,/id: meteorList\s*[\s\S]*?objectName: "cosmos-c25-meteor-board"/);
  assert.match(focus,/objectName: "cosmos-c25-meteor-sticky-header"/);
  assert.match(focus,/objectName: "cosmos-c25-meteor-next-peaks-row"/);
  assert.match(focus,/objectName: "cosmos-c25-meteor-peak-card"/);
  assert.match(focus,/readonly property int featuredCount: width >= 650 \? 5 : 3/);
  assert.match(focus,/meteorSource\.upcomingShowers \|\| \[\]/);
  assert.match(focus,/daysToPeak/);
  assert.match(focus,/peakUtc/);
  assert.match(focus,/solarLongitude/);
  assert.match(focus,/objectName: "cosmos-c25-meteor-catalog-frame"/);
  assert.match(focus,/anchors\.top: pinnedMeteorHeader\.bottom/);
  assert.match(focus,/anchors\.bottom: meteorCaveat\.top/);
  assert.match(focus,/objectName: "cosmos-c25-meteor-catalog-scroll"/);
  assert.match(focus,/contentHeight: meteorCards\.implicitHeight/);
  assert.match(focus,/boundsBehavior: Flickable\.StopAtBounds/);
  assert.match(focus,/NeonScrollBar\s*\{[\s\S]*?flickable: meteorScroll/);
  assert.match(focus,/function jumpToShower\(name\)/);
  assert.match(focus,/meteorScroll\.contentY = Math\.max\(0,Math\.min/);
  assert.match(focus,/onClicked: meteorBoard\.jumpToShower\(peakCard\.showerName\)/);
  assert.match(focus,/selectedShowerName === cardData\.name/);
  assert.match(focus,/CATALOG CONTEXT \/\/ NOT OBSERVED LOCAL RATE OR ZHR/);
  // Do not introduce any additional source host or page-wide scroll.
  assert.match(focus,/kind === "meteors" \? meteorList/);
  const scope=focus.slice(focus.indexOf("    Component {\n        id: meteorList"));
  assert.equal((scope.match(/\bFlickable\s*\{/g)||[]).length,1);
  assert.doesNotMatch(scope,/StationSky\s*\{|Process\s*\{|ScrollView\s*\{/);
  const reference=read("widgets/weather/StationSky.qml");
  assert.match(reference,/id: meteorUpcomingRow/);
  assert.match(reference,/meteorService\.upcomingShowers\.slice\(0, 5\)/);
});


test("C28 focused clock is an integrated source-backed circular instrument",()=>{
 const face=read("widgets/weather/StationCosmosPlanetClockFace.qml");
 const wheel=read("widgets/weather/StationCosmosPlanetDayWheel.qml");
 assert.match(face,/StationCosmosPlanetDayWheelPolicy\.js" as Day/);
 assert.match(face,/PlanetPolicy\.orderedEvents\(datedRows,selectedPlanet,selectedKind\)/);
 assert.match(face,/Day\.datedEvents\(/);
 assert.match(face,/Day\.geometry\(/);
 assert.match(face,/Day\.ringRadius\(/);
 assert.match(face,/Day\.timeAngle\(/);
 assert.match(face,/Day\.timeLabel\(/);
 assert.match(face,/Day\.point\(/);
 assert.match(face,/Day\.pick\(/);
 assert.match(face,/Day\.pickRing\(/);
 assert.match(face,/eventData\.kind==="rise"\?"R"/);
 assert.match(face,/eventData\.kind==="transit"\?"T":"S"/);
 assert.match(face,/objectName: "cosmos-c28-event-inspector"/);
 assert.match(face,/objectName: "cosmos-c28-planet-filters"/);
 assert.match(face,/objectName: "cosmos-c28-event-type-filters"/);
 assert.match(face,/onClicked: face\.lockedEvent=clockEvent\.eventData/);
 assert.match(face,/face\.step\(-1\)/);
 assert.match(face,/face\.step\(1\)/);
 assert.match(face,/onClicked: face\.pickPlanet\(modelData\)/);
 assert.match(face,/onClicked: face\.pickKind\(modelData\.id\)/);
 assert.match(face,/NO ORBITS OR RETROGRADE INFERENCE/);
 assert.match(face,/anchors\.bottom: clockFooter\.top/);
 assert.match(focus,/kind === "planet-clock" \? planetClock/);
 assert.match(focus,/localCivilMinute: cosmosModePane\.skyFeed/);
 assert.match(wheel,/Day\.ringRadius\(/);
 assert.match(wheel,/Day\.point\(/);
 for(const forbidden of [
   "Process {","Timer {","FileView {","XMLHttpRequest","Flickable {",
   "StationSky {","UsnoPlanetRiseSetService {"
 ])assert.ok(!face.includes(forbidden),forbidden);
});


test("C29 Meteors combines a credited embedded NASA photograph with a source-only 30D meter",()=>{
  const v=read("widgets/weather/StationCosmosMeteorVisual.qml");
  assert.match(focus,/StationCosmosMeteorVisual\s*\{[\s\S]*?id: meteorVisual/);
  assert.match(focus,/objectName: "cosmos-c29-meteor-image-panel"/);
  assert.match(focus,/upcomingShowers: meteorBoard\.upcomingShowers/);
  assert.match(focus,/selectedShowerName: meteorBoard\.selectedShowerName/);
  assert.match(focus,/sourceReady: !!cosmosModePane\.meteorSource/);
  assert.match(focus,/width: parent\.width >= 320/);
  assert.match(focus,/anchors\.left: meteorVisual\.right/);
  assert.match(focus,/contentHeight: meteorCards\.implicitHeight/);
  assert.match(v,/objectName: "cosmos-c29-meteor-visual"/);
  assert.match(v,/objectName: "cosmos-c29-meteor-photo-viewport"/);
  assert.match(v,/objectName: "cosmos-c29-nasa-archival-photo"/);
  assert.match(v,/url: "https:\/\/assets\.science\.nasa\.gov\//);
  assert.match(v,/source: visual\.showArchive \? visual\.archiveFrame\.url : ""/);
  assert.match(v,/NASA \/ BILL INGALLS/);
  assert.match(v,/PERSEIDS 2016/);
  assert.match(v,/SPRUCE KNOB 2016/);
  assert.match(v,/NASA PHOTO OFFLINE/);
  assert.match(v,/objectName: "cosmos-c29-peak-countdown"/);
  assert.match(v,/objectName: "cosmos-c29-source-countdown-fill"/);
  assert.match(v,/readonly property real daysToPeak:/);
  assert.match(v,/Number\(row\.daysToPeak\)/);
  assert.match(v,/remaining30DayFraction: hasCountdown/);
  assert.match(v,/Math\.min\(1,daysToPeak\/30\)/);
  assert.match(v,/Behavior on width\s*\{\s*NumberAnimation/);
  assert.match(v,/function setZoom\(next\)/);
  assert.match(v,/function resetView\(\)/);
  assert.match(v,/onPositionChanged: function\(mouse\)/);
  assert.match(v,/onWheel: function\(wheel\)/);
  assert.match(v,/onDoubleClicked: visual\.resetView\(\)/);
  assert.equal((v.match(/Image\s*\{/g)||[]).length,1);
  assert.equal((v.match(/Flickable\s*\{/g)||[]).length,0);
  for(const bad of ["Process {","FileView {","XMLHttpRequest","new WebSocket","UsnoPlanetRiseSetService {"])
    assert.ok(!v.includes(bad),bad);
});


test("C30 Meteors defaults to a moving radiant visualization, with a cycling credited photo archive",()=>{
  const v=read("widgets/weather/StationCosmosMeteorVisual.qml");
  const motion=read("widgets/weather/StationCosmosMeteorMotion.qml");
  assert.match(v,/property bool showArchive: false/);
  assert.match(v,/property bool playing: true/);
  assert.match(v,/StationCosmosMeteorMotion\s*\{[\s\S]*?peak: visual\.activePeak/);
  assert.match(v,/visible: !visual\.showArchive/);
  assert.match(v,/playing: visual\.playing/);
  assert.match(v,/readonly property var archiveFrames:/);
  assert.match(v,/property int archiveIndex: 0/);
  assert.match(v,/archiveIndex = \(archiveIndex \+ 1\) % archiveFrames\.length/);
  assert.match(v,/objectName: "cosmos-c30-nasa-gallery-timer"/);
  assert.match(v,/running: visual\.visible && visual\.showArchive && visual\.playing/);
  assert.match(v,/onTriggered: visual\.nextArchive\(\)/);
  assert.match(v,/objectName: "cosmos-c30-toggle-view"/);
  assert.match(v,/objectName: "cosmos-c30-play-pause"/);
  assert.match(v,/objectName: "cosmos-c30-gallery-next"/);
  assert.match(v,/visual\.playing = !visual\.playing/);
  assert.match(v,/onClicked: visual\.nextArchive\(\)/);
  assert.match(v,/EQUATORIAL SCHEMATIC \/\/ ARTISTIC TRAILS/);
  assert.match(motion,/objectName: "cosmos-c30-meteor-moving-sky"/);
  assert.match(motion,/objectName: "cosmos-c30-meteor-motion-driver"/);
  assert.match(motion,/running: motion\.visible && motion\.playing/);
  assert.match(motion,/skyCanvas\.requestPaint\(\)/);
  assert.match(motion,/readonly property bool radiantValid:/);
  assert.match(motion,/Number\(peak\.ra\)/);
  assert.match(motion,/Number\(peak\.dec\)/);
  assert.match(motion,/readonly property real radiantX:/);
  assert.match(motion,/readonly property real radiantY:/);
  assert.match(motion,/SIMULATED TRAILS/);
  assert.match(motion,/does not claim to show a local live sky/i);
  assert.match(motion,/Their \*rate is purely decorative\*/);
  assert.equal((motion.match(/Canvas\s*\{/g)||[]).length,1);
  assert.equal((motion.match(/Timer\s*\{/g)||[]).length,1);
  assert.equal((v.match(/Image\s*\{/g)||[]).length,1);
  assert.equal((v.match(/Timer\s*\{/g)||[]).length,1);
  for(const forbidden of ["Process {","FileView {","XMLHttpRequest","Flickable {"]) {
    assert.ok(!v.includes(forbidden),forbidden);
    assert.ok(!motion.includes(forbidden),forbidden);
  }
});
