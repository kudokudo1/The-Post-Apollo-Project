"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
function policy(pathname){
    const ctx=vm.createContext({});
    vm.runInContext(read(pathname).replace(/^\.pragma library\s*/,""),ctx);
    return ctx;
}
const hours=policy("widgets/weather/StationMagickPlanetaryHoursPolicy.js");
const dial=policy("widgets/weather/StationMagickTraditionalDialPolicy.js");
const chart=policy("widgets/weather/StationMagickNatalWheelPolicy.js");
const symbols=policy("widgets/weather/StationMagickSymbolismPolicy.js");
const agrippa=policy("widgets/weather/StationMagickAgrippaCorrespondencePolicy.js");
const forecast=[
    {date:"2026-11-06",sunrise:"6:30 AM",sunset:"5:10 PM"},
    {date:"2026-11-07",sunrise:"6:31 AM",sunset:"5:09 PM"}
];
const close=(x,y,e=1e-8)=>assert.ok(Math.abs(x-y)<=e,String(x)+" != "+String(y));

test("M8a planetary dial uses exact M6d historical rulers and source civil bounds",()=>{
    const plan=hours.build(forecast,"","2026-11-06");
    assert.equal(plan.ready,true,plan.reason);
    const source=dial.build(plan);
    assert.equal(source.ready,true,source.reason);
    assert.equal(source.sectors.length,24);
    assert.equal(source.sectors[0].ruler,plan.dayRuler);
    assert.equal(source.sectors[0].startMinute,390);
    assert.equal(source.sectors[11].endMinute,1030);
    assert.equal(source.sectors[12].phase,"night");
    assert.equal(source.sectors[23].endMinute,1831);
    close(source.sectors[0].startAngle,-Math.PI/2);
    close(source.sectors[23].endAngle,3*Math.PI/2);
    const dayAngular=source.sectors[11].endAngle-source.sectors[0].startAngle;
    assert.ok(dayAngular<Math.PI,"shorter November daylight must occupy less ring");
    assert.ok(source.basis.includes("DST TRANSITIONS NOT RESOLVED"));
    assert.equal(source.source,"WEATHER FORECAST // PROVIDER LOCAL");
});
test("M8a timing dial hit testing follows unequal source sectors, not 1/24 slices",()=>{
    const model=dial.build(hours.build(forecast,"","2026-11-06"));
    const g=dial.layout(430,290);
    assert.ok(g);
    for(const i of [0,5,11,12,16,23]){
        const s=model.sectors[i],a=(s.startAngle+s.endAngle)/2;
        const r=(g.inner+g.outer)/2;
        const x=g.cx+Math.cos(a)*r,y=g.cy+Math.sin(a)*r;
        assert.equal(dial.select(model,g,x,y),i);
    }
    assert.equal(dial.select(model,g,g.cx,g.cy),-1);
    assert.equal(dial.select(model,g,-1,-1),-1);
    assert.equal(dial.layout(80,70),null);
    const broken=JSON.parse(JSON.stringify(hours.build(forecast,"","2026-11-06")));
    broken.hours[8].startMinute+=8;
    assert.equal(dial.build(broken).ready,false);
    assert.equal(dial.build({ready:true,hours:[]}).ready,false);
});
function natalFixture(){
    const asc=22.25,targets=Array.from(chart.TARGETS),positions=targets.map((id,i)=>({
        id,naif_id:chart.EXACT_NAIF[id],
        longitude_deg:(14+i*31)%360
    }));
    return {format:chart.FORMAT,epoch_utc:"2026-11-06T14:20:00Z",
        origin:"topocentric",frame:"true-ecliptic-of-date",
        zodiac:"tropical",house_system:"whole-sign",
        provenance:{engine:"skyfield",ephemeris_sha256:"a".repeat(64)},
        ascendant_deg:asc,mc_deg:292.3,
        positions,house_cusps_deg:Array.from({length:12},(_,i)=>i*30)};
}
test("M8a natal wheel refuses M4 selected-pair data and does not fabricate houses",()=>{
    assert.equal(chart.validate(null).ready,false);
    assert.equal(chart.validate({positions:[]}).ready,false);
    const partial=natalFixture();
    partial.positions=partial.positions.slice(0,2);
    assert.equal(chart.validate(partial).ready,false);
    const noHash=natalFixture();
    noHash.provenance.ephemeris_sha256="fake";
    assert.equal(chart.validate(noHash).ready,false);
    const falseTarget=natalFixture();
    falseTarget.positions[4].naif_id=499;
    assert.equal(chart.validate(falseTarget).ready,false,
        "Mars system barycenter may not masquerade as Mars center");
    const falseHouse=natalFixture();
    falseHouse.house_cusps_deg[1]=31;
    assert.equal(chart.validate(falseHouse).ready,false);
});
test("M8a accepts complete verified chart contract and calculates angular geometry",()=>{
    const a=chart.validate(natalFixture());
    assert.equal(a.ready,true,a.reason);
    assert.equal(a.planets.length,10);
    assert.equal(a.cusps.length,12);
    assert.equal(a.ascendant_deg,22.25);
    assert.equal(a.planets[4].id,"mars_barycenter");
    assert.equal(chart.SIGNS.length,12);
    const at=chart.point(a.ascendant_deg,a.ascendant_deg,100);
    close(at.x,-100);close(at.y,0);
    close(chart.separation(350,10),20);
    const p=chart.derivedAspects([
        {id:"sun",longitude_deg:0},
        {id:"moon",longitude_deg:120},
        {id:"venus",longitude_deg:90}
    ],6);
    assert.equal(p.length,2);
    assert.equal(p[0].name,"trine");
    assert.equal(p[1].name,"square");
    const equal=natalFixture();
    equal.house_system="equal";
    equal.house_cusps_deg=Array.from({length:12},(_,i)=>(22.25+i*30)%360);
    assert.equal(chart.validate(equal).ready,true);
    equal.zodiac="sidereal";
    assert.equal(chart.validate(equal).ready,false,"sidereal requires named ayanamsa");
    equal.ayanamsa_id="lahiri";
    assert.equal(chart.validate(equal).ready,true);
});
test("M8a source-bound atlas reuses exact historical entries, no invented plants",()=>{
    const source=agrippa.entry("sun","plants");
    assert.equal(source.chapter,23);
    assert.ok(source.values.includes("marigold"));
    assert.ok(source.values.includes("saffron"));
    assert.deepEqual(JSON.parse(JSON.stringify(agrippa.shared("silver","metals"))),
        ["jupiter","venus","moon"]);
    const m=symbols.build(agrippa.PLANETS,agrippa.CATEGORIES,agrippa.SOURCE,
                          "plants","marigold");
    assert.equal(m.ready,true);
    assert.equal(m.sourceId,"agrippa-1651-book-i-23-29");
    assert.ok(m.rows.every(x=>x.chapter>=23&&x.chapter<=29));
});
test("M8a instrument routes and zoomable controls are mounted without side effects",()=>{
    const timing=read("widgets/weather/StationMagickTimingAtlasPane.qml");
    const clock=read("widgets/weather/StationMagickTraditionalClockPane.qml");
    const astro=read("widgets/weather/StationMagickAstrologyPane.qml");
    const natal=read("widgets/weather/StationMagickNatalChartWheelPane.qml");
    const symbol=read("widgets/weather/StationMagickSymbolismPane.qml");
    const atlas=read("widgets/weather/StationMagickCorrespondenceAtlasPane.qml");
    assert.match(timing,/StationMagickTraditionalClockPane\s*\{/);
    assert.match(timing,/Hours\.build\(daily,"",targetDate\)/);
    assert.match(clock,/Dial\.build\(plan\)/);
    assert.match(clock,/Dial\.select\(clock\.model,geometry,p\.x,p\.y\)/);
    assert.match(clock,/onWheel:function\(wheel\)/);
    assert.match(clock,/onLanesRequested: timing\.clockMode=false/);
    assert.match(astro,/StationMagickNatalChartWheelPane\s*\{/);
    assert.match(astro,/chartData: astrology\.fullChartData/);
    assert.match(astro,/property var fullChartData: null/);
    assert.match(astro,/StationMagickCelestialInstrument\s*\{/);
    assert.match(natal,/Chart\.validate\(chartData\)/);
    assert.match(natal,/REFERENCE SIGNS ONLY/);
    assert.match(natal,/if\(ready\)\{/);
    assert.match(natal,/onWheel:function\(wheel\)/);
    assert.match(symbol,/StationMagickCorrespondenceAtlasPane\s*\{/);
    assert.match(symbol,/onNetworkRequested:symbolism\.atlasMode=false/);
    assert.match(atlas,/Agrippa\.entry\(planetId,categoryId\)/);
    assert.match(atlas,/Agrippa\.shared\(term,categoryId\)/);
    assert.match(atlas,/SOURCE LINKS/);
    for(const ui of [clock,natal,atlas]){
        for(const forbidden of ["Process {","FileView {","XMLHttpRequest",
            "Qt.openUrlExternally","Math.random(","Date.now()","writeFile("])
            assert.ok(!ui.includes(forbidden),forbidden);
    }
});
