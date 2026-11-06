"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const source=read("widgets/weather/StationMagickPlanetaryHoursPolicy.js");
const qml=read("widgets/weather/StationMagickPlanetaryHoursPane.qml");
const subject=read("widgets/weather/StationMagickSubjectPane.qml");
const route=read("widgets/weather/StationMagickSubjectPanelPolicy.js");
const weatherPolicy=read("services/weather/WeatherCyclePolicy.js");
const dataPolicy=read("services/weather/WeatherDataPolicy.js");
const ctx=vm.createContext({});
vm.runInContext(source.replace(/^\.pragma library\s*/m,""),ctx);
const H=ctx;
const plain=v=>JSON.parse(JSON.stringify(v));
const daily=[
    {date:"2026-11-06",sunrise:"6:00 AM",sunset:"6:00 PM"},
    {date:"2026-11-07",sunrise:"6:30 AM",sunset:"5:58 PM"},
    {date:"2026-11-08",sunrise:"6:31 AM",sunset:"5:57 PM"}
];
test("M6d constructs exactly 12 day and 12 night hours using two real provider days",()=>{
    const before=JSON.stringify(daily);
    const p=H.build(daily,"2026-11-06 14:15");
    assert.equal(p.ready,true,p.reason);
    assert.equal(p.date,"2026-11-06");
    assert.equal(p.nextDate,"2026-11-07");
    assert.equal(p.weekday,5,"Friday is calendar weekday 5 independent of PC locale");
    assert.equal(p.dayRuler,"venus");
    assert.equal(p.hours.length,24);
    assert.deepEqual(plain(p.hours.map(h=>h.phase)),
       Array(12).fill("day").concat(Array(12).fill("night")));
    assert.equal(p.dayMinutes,720);
    assert.equal(p.nightMinutes,750);
    assert.equal(p.hours[0].startMinute,360);
    assert.equal(p.hours[0].endMinute,420);
    assert.equal(p.hours[11].endMinute,1080);
    assert.equal(p.hours[12].startMinute,1080);
    assert.equal(p.hours[23].endMinute,1830);
    assert.equal(p.hours[23].endLabel,"6:30 AM +1D");
    assert.equal(H.observedIndex(p,"2026-11-06 14:15"),8);
    assert.equal(JSON.stringify(daily),before,"existing provider forecast is read-only");
});
test("M6d weekday first-hour rulers and Chaldean seven-ruler repetition",()=>{
    const rulers=["sun","moon","mars","mercury","jupiter","venus","saturn"];
    for(let i=0;i<7;i++){
        const date=new Date(Date.UTC(2026,10,1+i)).toISOString().slice(0,10);
        const following=new Date(Date.UTC(2026,10,2+i)).toISOString().slice(0,10);
        const p=H.build([{date,sunrise:"6:00 AM",sunset:"6:00 PM"},
            {date:following,sunrise:"6:00 AM",sunset:"6:00 PM"}],date+" 12:00");
        assert.equal(p.ready,true,p.reason);
        assert.equal(p.hours[0].ruler,rulers[p.weekday]);
        assert.equal(p.hours[7].ruler,p.hours[0].ruler);
        assert.equal(p.hours[14].ruler,p.hours[0].ruler);
        assert.equal(p.hours[12].phase,"night");
        assert.equal(p.hours[23].ruler,
            H.ORDER[(H.ORDER.indexOf(p.dayRuler)+23)%7]);
        assert.equal(p.hours[0].ordinal,1);
        assert.equal(p.hours[12].ordinal,1);
    }
    // One full 24-segment cycle advances three rulers, matching the
    // next sunrise's weekday start in the historical naming sequence.
    const fri=H.build(daily,"2026-11-06 14:15");
    assert.equal(H.ORDER[(H.ORDER.indexOf(fri.dayRuler)+24)%7],"saturn");
});
test("M6d strict provider-local clocks and valid civil calendar",()=>{
    assert.equal(H.localMinute("12:00 AM"),0);
    assert.equal(H.localMinute("12:00 PM"),720);
    assert.equal(H.localMinute("6:07 pm"),1087);
    assert.equal(H.localMinute("24:00 PM"),-1);
    assert.equal(H.localMinute("06:00"),-1);
    assert.equal(H.localMinute("06:70 AM"),-1);
    assert.equal(H.nextDate("2026-12-31"),"2027-01-01");
    assert.equal(H.nextDate("2026-02-29"),"");
    assert.equal(H.validDate("2024-02-29")!==null,true);
    assert.equal(H.observedDate("2026-11-06 07:05:30 PM"),"2026-11-06");
    assert.equal(H.observedMinute("2026-11-06 07:05:30 PM"),1145);
    assert.equal(H.observedDate("not known"),"");
    assert.equal(H.clockLabel(1440),"12:00 AM +1D");
    assert.equal(H.clockLabel(1800),"6:00 AM +1D");
});
test("M6d fails closed without the next day's event or at polar/no-rise values",()=>{
    function reject(mod,obs="2026-11-06 07:00"){
        const input=JSON.parse(JSON.stringify(daily));
        mod(input);
        return H.build(input,obs);
    }
    assert.equal(H.build([], "2026-11-06 07:00").ready,false);
    assert.equal(reject(d=>d.splice(1,2)).ready,false);
    assert.equal(reject(d=>{d[1].date="2026-11-09"}).ready,false);
    assert.equal(reject(d=>{d[1].date=d[0].date}).ready,false);
    assert.equal(reject(d=>{d[0].sunrise="--"}).ready,false);
    assert.equal(reject(d=>{d[0].sunrise="7:00 PM"}).ready,false);
    assert.equal(reject(d=>{d[0].sunset="--"}).ready,false);
    assert.equal(reject(d=>{d[1].sunrise="--"}).ready,false);
    assert.equal(reject(d=>{d[0].date="2026-11-32"}).ready,false);
    assert.equal(reject(d=>{}, "2026-11-20 07:00").ready,false);
    assert.equal(H.build(daily,"", "2026-11-06").ready,true);
    assert.equal(H.build(daily,"", "2026-11-12").ready,false);
    assert.equal(H.observedIndex(H.build(daily,"2026-11-06 07:00"),
        "2026-11-07 07:00"),-1);
});
test("M6d graphical ring picks only real 24 sectors and supports day/night",()=>{
    const p=H.build(daily,"2026-11-06 09:00");
    const g=H.wheelGeometry(500,240);
    assert.ok(g);
    assert.equal(H.pick(p,g,g.cx,g.cy-g.radius),0);
    assert.equal(H.pick(p,g,g.cx+g.radius,g.cy),6);
    assert.equal(H.pick(p,g,g.cx,g.cy+g.radius),12);
    assert.equal(H.pick(p,g,g.cx-g.radius,g.cy),18);
    assert.equal(H.pick(p,g,g.cx,g.cy),-1);
    assert.equal(H.pick(p,g,-99,-99),-1);
    assert.equal(H.pick(null,g,g.cx,g.cy),-1);
    assert.equal(H.wheelGeometry(40,200),null);
    assert.equal(p.basis,"CIVIL CLOCK // DST TRANSITIONS NOT RESOLVED");
    assert.equal(p.source,"WEATHER FORECAST // PROVIDER LOCAL");
});
test("M6d is a source-owned new HOURS screen, not an invented astronomy feed",()=>{
    assert.match(qml,/import "StationMagickPlanetaryHoursPolicy\.js" as Hours/);
    assert.match(qml,/Hours\.build\(/);
    assert.match(qml,/weatherService\.dailyForecast/);
    assert.match(qml,/weatherService\.localObservationDateTime/);
    assert.match(qml,/id: dial/);
    assert.match(qml,/ctx\.arc\(g\.cx,g\.cy,g\.radius,begin,end\)/);
    assert.match(qml,/Hours\.pick\(hours\.plan,g,mouse\.x,mouse\.y\)/);
    assert.match(qml,/label: "◀ HOUR"/);
    assert.match(qml,/label: "HOUR ▶"/);
    assert.match(qml,/hours\.moveHour\(wheel\.angleDelta\.y>0\?1:-1\)/);
    assert.match(qml,/hours\.routeRequested\("cosmos\/sun\/twilight"\)/);
    assert.match(qml,/TRADITIONAL RULERS \/\/ CULTURAL CONVENTION/);
    assert.match(qml,/DST TRANSITION DURATION UNVERIFIED/);
    assert.match(subject,/readonly property bool planetaryHoursRoute:/);
    assert.match(subject,/magickPane\.planetaryHoursRoute\s*\?\s*planetaryHoursReference/);
    assert.match(subject,/id: planetaryHoursReference\s*StationMagickPlanetaryHoursPane/);
    assert.match(subject,/weatherService: magickPane\.weatherService/);
    assert.match(route,/"magick\/planetary\/hours": \{/);
    assert.match(route,/M6D CHALDEAN-ORDER PLANETARY HOURS/);
    assert.match(dataPolicy,/sunrise: textValue\(astronomy\.sunrise, "--"\)/);
    assert.match(dataPolicy,/sunset: textValue\(astronomy\.sunset, "--"\)/);
    assert.match(weatherPolicy,/function astronomySummary\(/);
    for(const file of [source,qml]){
        for(const forbidden of ["Process {","Timer {","FileView {",
                                "XMLHttpRequest","fetch(","Qt.openUrlExternally",
                                "curl ","new WebSocket","Date.now()"]){
            assert.ok(!file.includes(forbidden),"unapproved actor "+forbidden);
        }
    }
});
