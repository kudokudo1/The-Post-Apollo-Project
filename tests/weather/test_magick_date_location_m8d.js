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
const Defaults=policy("widgets/weather/StationMagickDateLocationPolicy.js");
const TaskDates=policy("widgets/tasks/TaskDateSegments.js");
const Setup=policy("widgets/weather/StationMagickEventChartSetupPolicy.js");
const Request=policy("widgets/weather/StationMagickNatalRequestPolicy.js");
const Transit=policy("widgets/weather/StationMagickTransitComparisonPolicy.js");
const plain=x=>JSON.parse(JSON.stringify(x));
const home={label:"Home",latitude:38.900001,longitude:-76.820042,source:"MANUAL"};
test("M8d TODAY and NOW use actual supplied UTC instant, not machine-local date",()=>{
 const before=new Date("2026-11-07T23:59:59.000Z");
 const after=new Date("2026-11-08T00:00:01.000Z");
 assert.equal(Defaults.utcDay(before),"2026-11-07");
 assert.equal(Defaults.utcDay(after),"2026-11-08");
 assert.deepEqual(plain(Defaults.utcClock(after)),{date:"2026-11-08",time:"00:00"});
 assert.equal(Defaults.utcTime(before),"23:59");
 assert.equal(Defaults.utcDay(new Date("2026-02-29T12:00:00Z")),"2026-03-01");
 assert.equal(Defaults.utcClock(new Date("2100-01-01T12:00:00Z")),null);
 assert.equal(Defaults.utcClock(new Date(NaN)),null);
});
test("M8d reuses TASKS year/month/day steppers with supported historical bounds",()=>{
 assert.equal(TaskDates.step("2024-02-29","day",1),"2024-03-01");
 assert.equal(TaskDates.step("2024-03-01","day",-1),"2024-02-29");
 assert.equal(TaskDates.step("2024-02-29","year",1),"2025-02-28");
 assert.equal(TaskDates.step("2026-01-31","month",1),"2026-02-28");
 const edit=TaskDates.setPart("2024-02-29","year","2025");
 assert.equal(edit.date,"2025-02-28");
 assert.equal(Setup.eventDate(edit.date),edit.date);
 assert.equal(Setup.eventDate("1900-12-31"),null);
 assert.equal(Setup.eventDate("2100-01-01"),null);
 assert.equal(Setup.eventDate("2026-02-29"),null);
});
test("M8d Home fallback uses saved manual Home when BOTH coordinates empty",()=>{
 const location=Defaults.location("","",home);
 assert.deepEqual(plain(location),{
     ready:true,source:"HOME",
     latitude:"38.900001",longitude:"-76.820042",
     label:"POST-APOLLO HOME // Home"
 });
 assert.equal(Defaults.safeHome(home).label,"Home");
 assert.equal(Defaults.location("","",null).ready,false);
 assert.equal(Defaults.location("","",{...home,source:"PROVIDER"}).ready,false);
 assert.equal(Defaults.location("","",{...home,latitude:100}).ready,false);
 const draft=Setup.validate("2026-11-07","15:31",location.latitude,
                            location.longitude,"tropical","whole-sign");
 assert.equal(draft.valid,true);
 assert.equal(draft.latitude,38.900001);
 assert.equal(Request.fromDraft(draft).latitude_deg,38.900001);
});
test("M8d manual coordinate pair always overrides saved Home, never blends",()=>{
 const manual=Defaults.location("0","0",home);
 assert.equal(manual.source,"MANUAL");
 assert.equal(manual.latitude,"0"); assert.equal(manual.longitude,"0");
 assert.equal(Setup.validate("2026-11-07","15:31",manual.latitude,
                manual.longitude,"tropical","equal").valid,true);
 for(const [lat,lon] of [["38.9",""],["","-76.8"]]){
    const incomplete=Defaults.location(lat,lon,home);
    assert.equal(incomplete.ready,false);
    assert.equal(incomplete.source,"INCOMPLETE");
    assert.equal(incomplete.latitude,"");
    assert.equal(incomplete.longitude,"");
 }
 const bad=Defaults.location("oops","-76.8",home);
 assert.equal(bad.source,"MANUAL");
 assert.equal(Setup.validate("2026-11-07","15:31",bad.latitude,
                bad.longitude,"tropical","equal").valid,false);
 assert.equal(Defaults.location("","",{...home,latitude:NaN}).ready,false);
 assert.equal(Defaults.location("","",{...home,longitude:Infinity}).ready,false);
});
test("M8d wiring reuses TASKS components, reads Home only, never invents GPS",()=>{
 const date=read("widgets/weather/StationMagickUtcDateField.qml");
 const form=read("widgets/weather/StationMagickEventChartSetupPane.qml");
 const transit=read("widgets/weather/StationMagickTransitChartPane.qml");
 const registry=read("services/location/PlaceRegistry.qml");
 const a=read("widgets/weather/StationMagickAstrologyPane.qml");
 assert.equal((date.match(/TasksFields\.TaskDateSegment\s*\{/g)||[]).length,3);
 assert.match(date,/import "\.\.\/tasks\/TaskDateSegments\.js" as Segments/);
 assert.match(date,/Segments\.setPart\(/);
 assert.match(date,/Segments\.step\(/);
 assert.match(date,/Setup\.eventDate\(next\.date\)/);
 assert.match(date,/label:"TODAY"/);
 assert.match(form,/import qs\.services\.location/);
 assert.match(form,/PlaceRegistry\.homePlace/);
 assert.match(form,/Defaults\.location\(/);
 assert.match(form,/dateValue:eventSetup\.utcDate/);
 assert.match(form,/onDateEdited:function\(date\)\{eventSetup\.utcDate=date;\}/);
 assert.match(form,/StationMagickUtcDateField\s*\{/);
 assert.match(form,/onVisibleChanged: \{/);
 assert.match(form,/if\(!utcDate\)setCurrentDate\(\)/);
 assert.match(form,/label:"NOW UTC"/);
 assert.match(form,/AUTO HOME \/\/ SAVED DEFAULT, NOT LIVE GPS/);
 assert.match(form,/eventSetup\.draft\.valid&&eventSetup\.zodiac==="tropical"/);
 assert.match(form,/onClicked:eventSetup\.calculateRequested\(eventSetup\.draft\)/);
 assert.match(transit,/StationMagickUtcDateField\s*\{/);
 assert.match(transit,/if\(!dateText\)dateText=Defaults\.utcDay\(\)/);
 assert.match(transit,/label:"NOW UTC"/);
 assert.match(transit,/const instant=transits\.dateText\+"T"\+transits\.timeText\+":00Z"/);
 assert.match(transit,/Transit\.utc\(instant\)/);
 assert.match(a,/transitSource\.calculate\(draft\)/);
 assert.match(registry,/readonly property var homePlace:/);
 for(const source of [date,form,transit]){
   for(const forbidden of ["Process {","FileView {","XMLHttpRequest",
       "localStorage","Qt.openUrlExternally","Geolocation",
       "PositionSource {","GPSPositioningMethods","writeFile("])
      assert.ok(!source.includes(forbidden),forbidden);
 }
 assert.ok(!form.includes("PlaceRegistry.effectivePlace"),
     "Explore destination must never be treated as live device position");
 assert.ok(!form.includes("weatherService.providerLatitude"));
});
