"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root=path.resolve(__dirname,"../..");
const read=name=>fs.readFileSync(path.join(root,name),"utf8");
const compareSrc=read("widgets/weather/StationCosmosBearingComparisonPolicy.js");
const horizonSrc=read("widgets/weather/StationCosmosPlanetHorizonPolicy.js");
const planetSrc=read("widgets/weather/StationCosmosPlanetEventPolicy.js");
const qml=read("widgets/weather/StationCosmosBearingComparisonPane.qml");
const horizonQml=read("widgets/weather/StationCosmosPlanetHorizonPane.qml");
const clockQml=read("widgets/weather/StationCosmosPlanetEventClock.qml");
const sky=read("widgets/weather/StationSky.qml");
const C=vm.createContext({}), H=vm.createContext({}), P=vm.createContext({});
vm.runInContext(compareSrc.replace(/^\.pragma library\s*$/m,""),C);
vm.runInContext(horizonSrc.replace(/^\.pragma library\s*$/m,""),H);
vm.runInContext(planetSrc.replace(/^\.pragma library\s*$/m,""),P);
const plain=v=>JSON.parse(JSON.stringify(v));

function row(name,riseAz,setAz,date="2026-11-04") {
    return {name,date,status:"NORMAL",
        rise:"06:15",riseAzimuth:riseAz,
        transit:"12:15",transitAltitude:45,transitHemisphere:"S",
        set:"18:45",setAzimuth:setAz};
}
function raw(){
    return [
        row("MERCURY",350,200),
        row("VENUS",10,80),
        row("MARS",180,280),
        row("JUPITER",40,170),
        row("SATURN",40,150)
    ];
}
function source(){
    return H.markers(P.clockRows(raw(),"2026-11-04"),"ALL");
}

test("V3c compares two dated true-north source bearings, not positions",()=>{
    assert.equal(C.FORMAT,"post-apollo.weather.cosmos-bearing-comparison.v3c.v1");
    const result=plain(C.compare(source(),"2026-11-04","MERCURY","VENUS","rise"));
    assert.equal(result.ready,true);
    assert.equal(result.gap,20);
    assert.equal(result.signed,20);
    assert.equal(result.direction,"CLOCKWISE");
    assert.equal(result.eventA.azimuth,350);
    assert.equal(result.eventB.azimuth,10);
    assert.equal(result.frame,"TRUE-NORTH AZIMUTH");
    assert.ok(["eventA","eventB"].every(key=>result[key].source==="USNO MRST"));
    assert.equal(C.eventLabel(result.eventA),
        "MERCURY // RISE 06:15 LOCAL // 350° TRUE N");
    const reversed=C.compare(source(),"2026-11-04","VENUS","MERCURY","rise");
    assert.equal(reversed.gap,20);
    assert.equal(reversed.signed,-20);
    assert.equal(reversed.direction,"COUNTERCLOCKWISE");
    const set=C.compare(source(),"2026-11-04","MERCURY","VENUS","set");
    assert.equal(set.gap,120);
    assert.equal(set.direction,"COUNTERCLOCKWISE");
    assert.equal(set.eventA.clock,"18:45");
    assert.equal(set.eventB.clock,"18:45");
});

test("V3c zero and half-turn cases are unambiguous",()=>{
    const equal=C.compare(source(),"2026-11-04","JUPITER","SATURN","rise");
    assert.equal(equal.gap,0);
    assert.equal(equal.direction,"SAME BEARING");
    assert.equal(C.signedGap(0,180),180);
    assert.equal(C.signedGap(180,0),180);
    const half=C.compare(source(),"2026-11-04","MERCURY","MARS","rise");
    assert.equal(half.gap,170);
    assert.equal(C.signedGap(350,170),180);
    assert.equal(C.signedGap(20,340),-40);
    assert.equal(C.signedGap(null,10),null);
    assert.equal(C.azimuth(360),0);
    for (const bad of [-1,361,null,"",undefined,Infinity,NaN])
        assert.equal(C.azimuth(bad),null,String(bad));
});

test("V3c rejects wrong dates, unsupported pairs and invalid source",()=>{
    const events=source();
    assert.equal(C.compare(events,"2026-11-04","MERCURY","MERCURY","rise").ready,false);
    assert.match(C.compare(events,"2026-11-04","PLUTO","VENUS","rise").reason,/SELECT TWO/);
    assert.equal(C.compare(events,"2026-11-04","MERCURY","VENUS","transit").ready,false);
    assert.equal(C.compare(events,"2026-11-03","MERCURY","VENUS","rise").ready,false);
    assert.equal(C.compare(events,"2026-02-30","MERCURY","VENUS","rise").ready,false);
    assert.equal(C.compare([],"2026-11-04","MERCURY","VENUS","rise").ready,false);
    const damaged=plain(events);
    damaged[0].source="INVENTED";
    assert.equal(C.compare(damaged,"2026-11-04","MERCURY","VENUS","rise").ready,false);
    damaged[0].source="USNO MRST";
    damaged[0].date="2026-11-03";
    assert.equal(C.compare(damaged,"2026-11-04","MERCURY","VENUS","rise").ready,false);
    const wrongRow=raw();wrongRow[0].status="CONTINUOUSLY BELOW HORIZON";
    const unavailable=H.markers(P.clockRows(wrongRow,"2026-11-04"),"ALL");
    assert.equal(C.compare(unavailable,"2026-11-04","MERCURY","VENUS","rise").ready,false);
});

test("V3c geometry and pointer hitboxes are based on the same azimuth",()=>{
    const origin={cx:100,cy:100,r:75};
    const points=[
        [0,100,25],[90,175,100],[180,100,175],[270,25,100]
    ];
    for(const [bearing,x,y] of points){
        const p=C.point(bearing,origin.cx,origin.cy,origin.r);
        assert.ok(Math.abs(p.x-x)<1e-8,String(bearing)+" x");
        assert.ok(Math.abs(p.y-y)<1e-8,String(bearing)+" y");
    }
    const m=C.compare(source(),"2026-11-04","MERCURY","VENUS","rise");
    const a=C.point(m.eventA.azimuth,100,100,75);
    const b=C.point(m.eventB.azimuth,100,100,75);
    assert.equal(C.pickSide(m,a.x,a.y,100,100,75,13),"A");
    assert.equal(C.pickSide(m,b.x,b.y,100,100,75,13),"B");
    assert.equal(C.pickSide(m,100,100,100,100,75,13),"");
    // A +22px crosses toward B (whose marker is 26px away), so test
    // outside the hit radius *away* from both real bearing markers.
    assert.equal(C.pickSide(m,a.x-22,a.y,100,100,75,13),"");
    assert.equal(C.pickSide(null,a.x,a.y,100,100,75,13),"");
    assert.equal(C.pickSide(m,a.x,a.y,100,100,75,0),"");
    assert.equal(C.point(-1,100,100,75),null);
});

test("V3c tolerates bounded QML-indexed lists; never invents a fallback",()=>{
    const native=source(), list={length:native.length};
    native.forEach((e,i)=>{list[i]=e;});
    assert.equal(Array.isArray(list),false);
    assert.equal(C.compare(list,"2026-11-04","VENUS","MARS","rise").ready,true);
    assert.equal(C.compare({length:100000,0:native[0]},
        "2026-11-04","MERCURY","VENUS","rise").ready,false);
    assert.equal(C.compare("invalid input","2026-11-04",
        "MERCURY","VENUS","rise").ready,false);
});

test("V3c QML has real controls and reuses one USNO owner",()=>{
    assert.match(horizonQml,/signal compareRequested\(\)/);
    assert.match(horizonQml,/onClicked: horizonPane\.compareRequested\(\)/);
    assert.match(clockQml,/StationCosmosBearingComparisonPane\s*\{/);
    assert.match(clockQml,/visible: clock\.displayMode === "compare"/);
    assert.match(clockQml,/datedRows: clock\.rows/);
    assert.match(qml,/Compare\.compare\(/);
    assert.match(qml,/Horizon\.markers\(/);
    assert.match(qml,/Compare\.pickSide\(/);
    assert.match(qml,/onClicked: comparisonPane\.planetA=modelData/);
    assert.match(qml,/onClicked: comparisonPane\.planetB=modelData/);
    assert.match(qml,/onClicked: comparisonPane\.eventKind="rise"/);
    assert.match(qml,/onClicked: comparisonPane\.eventKind="set"/);
    assert.match(qml,/onClicked: comparisonPane\.activeSide = "A"/);
    assert.match(qml,/onClicked: comparisonPane\.activeSide = "B"/);
    assert.match(qml,/onClicked: comparisonPane\.backToHorizon\(\)/);
    assert.match(qml,/onClicked: comparisonPane\.returnToTimeline\(\)/);
    assert.match(qml,/height: 414/);
    assert.match(qml,/NOT ECLIPTIC ASPECT OR ORBITAL ANGLE/);
    assert.match(sky,/providerRows: planetRiseSetService\.rows/);
    assert.equal((sky.match(/WeatherServices\.UsnoPlanetRiseSetService\s*\{/g)||[]).length,1);
    for(const file of [qml,compareSrc])for(const banned of [
        "Process {","Timer {","FileView {","XMLHttpRequest",
        "new WebSocket","UsnoPlanetRiseSetService {","zodiacLongitude",
        "JPL","fetch(","Qt.callLater","swaymsg"
    ]) assert.ok(!file.includes(banned),banned);
});
