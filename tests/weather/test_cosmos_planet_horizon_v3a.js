"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = p => fs.readFileSync(path.join(root,p),"utf8");
const clockPolicy = read("widgets/weather/StationCosmosPlanetEventPolicy.js");
const horizonPolicy = read("widgets/weather/StationCosmosPlanetHorizonPolicy.js");
const qml = read("widgets/weather/StationCosmosPlanetHorizonPane.qml");
const clockQml = read("widgets/weather/StationCosmosPlanetEventClock.qml");
const sky = read("widgets/weather/StationSky.qml");
const p = vm.createContext({});
const h = vm.createContext({});
vm.runInContext(clockPolicy.replace(/^\.pragma library\s*$/m,""),p);
vm.runInContext(horizonPolicy.replace(/^\.pragma library\s*$/m,""),h);
const plain = v => JSON.parse(JSON.stringify(v));

function raw(name,date="2026-11-04") {
    return {name,date,status:"NORMAL",
        rise:"06:10",riseAzimuth:90,
        transit:"12:00",transitAltitude:43,transitHemisphere:"S",
        set:"18:10",setAzimuth:270};
}
function rows() {
    return p.clockRows(["MERCURY","VENUS","MARS","JUPITER","SATURN"]
        .map(name=>raw(name)),"2026-11-04");
}

test("V3a uses exact dated and source-stamped rise/set bearings",()=>{
    assert.equal(h.FORMAT,"post-apollo.weather.cosmos-horizon-compass.v3a.v1");
    const out = plain(h.markers(rows(),"ALL"));
    assert.equal(out.length,10);
    assert.deepEqual(out.map(m=>m.kind),Array.from({length:5}).flatMap(()=>["rise","set"]));
    assert.ok(out.every(m=>m.source==="USNO MRST" && m.date==="2026-11-04"));
    assert.deepEqual(out.filter(m=>m.planet==="VENUS").map(m=>m.azimuth),[90,270]);
    assert.deepEqual(plain(h.markers(rows(),"MARS")).map(m=>m.planet),["MARS","MARS"]);
    assert.deepEqual(plain(h.markers(rows(),"PLUTO")),[]);
    assert.match(h.markerLabel(out[0]),/90° TRUE N/);
    assert.match(h.markerLabel(null),/SELECT A RISE OR SET MARKER/);
});

test("V3a geometry respects true north, east, south and west",()=>{
    const g=h.geometry(240,240);
    assert.equal(g.radius,96);
    for(const [az,x,y] of [[0,120,24],[90,216,120],
                           [180,120,216],[270,24,120],[360,120,24]]) {
        const pos=h.point(az,240,240);
        assert.ok(Math.abs(pos.x-x)<1e-8,"x @ "+az);
        assert.ok(Math.abs(pos.y-y)<1e-8,"y @ "+az);
    }
    assert.equal(h.point(-1,240,240),null);
    assert.equal(h.point(361,240,240),null);
    assert.equal(h.point(null,240,240),null);
    assert.equal(h.point(90,0,240),null);
});

test("V3a pointer hit testing locks only real source markers",()=>{
    const source=h.markers(rows(),"MERCURY");
    const rise=h.point(90,240,240,"MERCURY");
    const set=h.point(270,240,240,"MERCURY");
    assert.equal(h.pick(source,rise.x,rise.y,240,240,13).kind,"rise");
    assert.equal(h.pick(source,set.x,set.y,240,240,13).kind,"set");
    assert.equal(h.pick(source,120,120,240,240,13),null);
    assert.equal(h.pick(source,rise.x+20,rise.y,240,240,13),null);
    assert.equal(h.pick(source,rise.x,rise.y,240,240,-1),null);
    assert.equal(h.byId(source,source[0].id).kind,"rise");
    assert.equal(h.byId(source,"not an event"),null);
});

test("V3a transit altitude remains separate from azimuth bearings",()=>{
    const trans=plain(h.transits(rows()));
    assert.equal(trans.length,5);
    assert.deepEqual(trans.map(t=>t.altitude),[43,43,43,43,43]);
    assert.equal(trans[0].clock,"12:00");
    assert.equal(trans[0].hemisphere,"S");
    assert.equal(h.altitudeLabel(trans[0]),"43°S @ 12:00 LOCAL");
    assert.equal(h.altitudeLabel(null),"NO TRANSIT ALTITUDE");

    const bad=raw("VENUS");
    bad.riseAzimuth=null;
    bad.setAzimuth=400;
    bad.transitAltitude=100;
    const invalid=p.clockRows([bad],"2026-11-04");
    assert.equal(h.markers(invalid,"ALL").length,0);
    assert.equal(h.transits(invalid)[1].altitude,null);
    const wrong=p.clockRows([raw("VENUS","2026-11-03")],"2026-11-04");
    assert.equal(h.markers(wrong,"ALL").length,0);
    assert.ok(h.transits(wrong).every(x=>x.altitude===null));
    const circumpolar=raw("MARS");
    circumpolar.status="CONTINUOUSLY ABOVE HORIZON";
    const special=p.clockRows([circumpolar],"2026-11-04");
    assert.equal(h.markers(special,"ALL").length,0);
});

test("V3a accepts bounded QML-indexed rows; refuses malformed inputs",()=>{
    const five=rows(), list={length:five.length};
    five.forEach((value,i)=>{list[i]=value});
    assert.equal(Array.isArray(list),false);
    assert.equal(h.markers(list,"ALL").length,10);
    assert.equal(h.transits(list).filter(t=>t.altitude!==null).length,5);
    assert.equal(h.markers({length:10000,0:five[0]},"ALL").length,0);
    assert.equal(h.markers("not a QML list","ALL").length,0);
    const forged=plain(five);
    forged[0].events[0].source="UNKNOWN";
    forged[0].events[1].date="2026-11-03";
    assert.equal(h.markers(forged,"MERCURY").length,1);
});

test("V3a is an in-place COSMOS visualization, not a new provider",()=>{
    assert.match(clockQml,/StationCosmosPlanetHorizonPane\s*\{/);
    assert.match(clockQml,/property string displayMode: "timeline"/);
    assert.match(clockQml,/onClicked: clock\.displayMode = "horizon"/);
    assert.match(clockQml,/onReturnToTimeline: clock\.displayMode = "timeline"/);
    assert.match(clockQml,/datedRows: clock\.rows/);
    assert.match(clockQml,/selectedPlanet: clock\.selectedPlanet/);
    assert.match(qml,/Canvas\s*\{/);
    assert.match(qml,/Horizon\.markers\(/);
    assert.match(qml,/Horizon\.transits\(/);
    assert.match(qml,/Horizon\.pick\(/);
    assert.match(qml,/onClicked: horizonPane\.planetPicked\(/);
    assert.match(qml,/onClicked: horizonPane\.returnToTimeline\(\)/);
    assert.match(qml,/NO PLANET TRACK OR ECLIPTIC ALIGNMENT IMPLIED/);
    assert.match(qml,/height: 414/);
    assert.match(clockQml,/height: 414/);
    assert.match(sky,/StationCosmosPlanetEventClock\s*\{/);
    assert.match(sky,/providerRows: planetRiseSetService\.rows/);
    assert.equal((sky.match(/WeatherServices\.UsnoPlanetRiseSetService\s*\{/g)||[]).length,1);
    for(const file of [qml,horizonPolicy]) {
        for(const banned of ["Process {","Timer {","FileView {","XMLHttpRequest",
            "new WebSocket","UsnoPlanetRiseSetService {",
            "zodiacLongitude","writeAdapter()","swaymsg","Qt.callLater"])
            assert.ok(!file.includes(banned),banned);
    }
});
