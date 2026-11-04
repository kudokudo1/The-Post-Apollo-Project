"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const src=read("services/weather/CelestialVisualQueryPolicy.js");
const service=read("services/weather/CelestialVisualService.qml");
const pane=read("widgets/weather/StationMagickSubjectPane.qml");
const station=read("widgets/weather/WeatherStationW.qml");
const context=vm.createContext({Date,Math,isFinite,JSON});
vm.runInContext(src.replace(/^\.pragma library\s*/m,""),context);
const plain=x=>JSON.parse(JSON.stringify(x));

test("six exact-JPL pair presets, never silently relabel planetary barycenters",()=>{
    const pairs=plain(context.PAIRS);
    assert.equal(pairs.length,6);
    assert.equal(new Set(pairs.map(p=>p.id)).size,pairs.length);
    for (const p of pairs) {
        assert.equal(p.bodies.length,2);
        assert.equal(new Set(p.bodies).size,2);
        assert.ok(p.label.length>2);
    }
    assert.deepEqual(plain(context.pairFor("venus-mars").bodies),
                     ["venus","mars_barycenter"]);
    assert.deepEqual(plain(context.pairFor("jupiter-saturn").bodies),
                     ["jupiter_barycenter","saturn_barycenter"]);
    assert.deepEqual(plain(context.pairFor("uranus-neptune").bodies),
                     ["uranus_barycenter","neptune_barycenter"]);
    assert.equal(context.initialPairForRoute("magick/astrology/retrogrades"),
                 "mercury-sun");
    assert.equal(context.initialPairForRoute("magick/astrology/charts"),
                 "moon-sun");
    assert.equal(context.pairFor("unknown"),null);
    assert.equal(context.pairAfter("moon-sun",-1),"moon-pluto");
    assert.equal(context.pairAfter("moon-pluto",1),"moon-sun");
});

test("UTC time navigation stays absolute across DST and leap-year boundaries",()=>{
    assert.equal(context.dayFor("2026-11-03",0),"2026-11-03");
    assert.equal(context.dayFor("2026-11-03",-30),"2026-10-04");
    assert.equal(context.dayFor("2026-11-03",30),"2026-12-03");
    assert.equal(context.dayFor("2024-02-28",1),"2024-02-29");
    assert.equal(context.dayFor("2024-02-29",1),"2024-03-01");
    assert.equal(context.dayFor("2026-03-08",1),"2026-03-09");
    assert.equal(context.dayFor("2026-11-01",-1),"2026-10-31");
    assert.equal(context.dayFor("2026-02-30",0),"");
    assert.equal(context.dayFor("2026-11-03T00:00:00-05:00",0),"");
    assert.equal(context.dayFor("2026-11-03",3651),"");
    assert.equal(context.shiftOffset(3620,30),3650);
    assert.equal(context.shiftOffset(-3620,-30),-3650);
    assert.equal(context.shiftOffset(0,NaN),null);
    assert.equal(context.shiftOffset("0",30),null);
    assert.equal(context.shiftOffset(0,30),30);
});

test("14, 29 and 90-day bounded query windows keep original M4 contract",()=>{
    for (const span of [14,29,90]){
        const req=plain(context.requestFor("2026-11-03",0,"moon-sun",span));
        assert.equal(req.format,"post-apollo.weather.celestial-visual-data.v1");
        assert.deepEqual(req.bodies,["moon","sun"]);
        assert.equal(req.step_hours,12);
        assert.equal(req.include_events,true);
        assert.equal(req.include_heliocentric_spatial,true);
        assert.equal(req.solar_overview_bodies.length,10);
        assert.ok(req.solar_overview_bodies.includes("earth"));
        assert.ok(req.solar_overview_bodies.includes("jupiter_barycenter"));
        assert.equal((Date.parse(req.end_utc)-Date.parse(req.start_utc))/86400000,
                     span);
        assert.ok(span*2+1<=721);
        assert.equal(req.start_utc.endsWith("Z"),true);
        assert.equal(req.end_utc.endsWith("Z"),true);
    }
    assert.equal(context.spanAfter(14),29);
    assert.equal(context.spanAfter(29),90);
    assert.equal(context.spanAfter(90),14);
    assert.equal(context.requestFor("bad",0,"moon-sun",29),null);
    assert.equal(context.requestFor("2026-11-03",0,"fake",29),null);
    assert.equal(context.requestFor("2026-11-03",0,"moon-sun",500),null);
    const j=plain(context.requestFor("2026-11-03",90,"jupiter-saturn",29));
    assert.deepEqual(j.bodies,["jupiter_barycenter","saturn_barycenter"]);
});

test("result matching rejects stale date/pair/span even with valid-looking SHA",()=>{
    const expected=plain(context.requestFor("2026-11-03",0,"venus-mars",29));
    const row={
        format:context.FORMAT,
        provenance:{ephemeris_sha256:"a".repeat(64)},
        query:{origin:"geocentric",position_model:"apparent",
            frame:"true-ecliptic-of-date",
            bodies:expected.bodies.slice().sort(),
            start_utc:expected.start_utc.replace(".000Z",".000000Z"),
            end_utc:expected.end_utc.replace(".000Z",".000000Z"),
            step_hours:12,include_events:true,
            include_heliocentric_spatial:true,
            solar_overview_bodies:expected.solar_overview_bodies.slice()},
        sample_count:2,
        heliocentric_spatial:{
            format:"post-apollo.weather.heliocentric-spatial.v1",
            origin:"heliocentric",origin_body:"sun",
            position_model:"geometric",frame:"true-ecliptic-of-date",
            sample_count:2,series:[{},{}]
        },
        solar_overview:{
            format:"post-apollo.weather.solar-overview.v1",
            origin:"heliocentric",origin_body:"sun",
            position_model:"geometric",frame:"true-ecliptic-of-date",
            epoch:"exact-m4-grid",units:"AU",
            source:"same-JPL-kernel-as-M4",
            sample_count:2,times_unix_ms:[1,2],
            series:expected.solar_overview_bodies.map(body=>({
                body,vectors_au:[[1,0,0],[1,0,0]]
            }))
        },
        series:[{},{}],relationships:[{}],event_markers:[]
    };
    assert.equal(context.matchesResult(row,expected),true);
    const noAtlas=JSON.parse(JSON.stringify(row));
    delete noAtlas.solar_overview;
    assert.equal(context.matchesResult(noAtlas,expected),false);
    const wrongAtlas=JSON.parse(JSON.stringify(row));
    wrongAtlas.solar_overview.series[0].body="fake";
    assert.equal(context.matchesResult(wrongAtlas,expected),false);
    const noSpatial=JSON.parse(JSON.stringify(row));
    delete noSpatial.heliocentric_spatial;
    assert.equal(context.matchesResult(noSpatial,expected),false);
    const changed=plain(context.requestFor("2026-11-03",30,"venus-mars",29));
    assert.equal(context.matchesResult(row,changed),false);
    assert.equal(context.matchesResult(row,
         plain(context.requestFor("2026-11-03",0,"venus-mars",14))),false);
    assert.equal(context.matchesResult(row,
         plain(context.requestFor("2026-11-03",0,"moon-sun",29))),false);
    const wrong=JSON.parse(JSON.stringify(row));
    wrong.query.bodies=["mars","venus"];
    assert.equal(context.matchesResult(wrong,expected),false);
    wrong.query.bodies=expected.bodies.slice().sort();
    wrong.provenance.ephemeris_sha256="not-a-checksum";
    assert.equal(context.matchesResult(wrong,expected),false);
});

test("visible controls are functional and route through single owning service",()=>{
    assert.match(service,/import "CelestialVisualQueryPolicy.js" as Query/);
    assert.match(service,/property string pairPreset/);
    assert.match(service,/property int dateOffsetDays/);
    assert.match(service,/property int spanDays/);
    assert.match(service,/Query\.requestFor\(anchorDayUtc,dateOffsetDays,pairPreset,spanDays\)/);
    assert.match(service,/function shiftDate\(days\)/);
    assert.match(service,/function returnToToday\(\)/);
    assert.match(service,/function cyclePair\(direction\)/);
    assert.match(service,/function cycleSpan\(\)/);
    assert.match(service,/Query\.matchesResult\(value,request\(\)\)/);
    assert.match(service,/onCurrentKeyChanged: clearState\(\)/);
    assert.match(service,/calculation\.running=true/);
    assert.match(service,/onRouteChanged:/);
    // M5k retains all original date-navigation semantics while allowing
    // the day jump to be edited (previously hardcoded at 30).
    for(const call of ["jumpDate(-1)","jumpDate(1)","returnToToday()",
                       "adjustDateStepDays(-1)","adjustDateStepDays(1)",
                       "cyclePair(-1)","cyclePair(1)","cycleSpan()"])
        assert.ok(pane.includes("magickPane.celestialSource."+call),call);
    assert.match(service,/function shiftDate\(days\)/);
    assert.match(service,/function jumpDate\(direction\)/);
    assert.match(service,/property int dateStepDays:/);
    assert.match(pane,/contentHeight: Math\.max\(height, 620\)/);
    assert.match(pane,/StationMagickCelestialInstrument\s*\{/);
    assert.equal((station.match(/WeatherServices\.CelestialVisualService\s*\{/g)||[]).length,1);
    for(const no of ["Process {","Timer {","FileView {","XMLHttpRequest",
                    "swaymsg","WeatherServices."])
        assert.equal(pane.includes(no),false,"unexpected view side-effect "+no);
    assert.equal(service.includes("Timer {"),false);
    assert.equal(service.includes("onCurrentKeyChanged: refresh()"),false);
});
