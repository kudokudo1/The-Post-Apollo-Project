"use strict";

const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");

const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const policy=read("widgets/weather/StationCosmosVisualPolicy.js");
const qml=read("widgets/weather/StationCosmosVisualInstruments.qml");
const sky=read("widgets/weather/StationSky.qml");
const skyPolicy=read("widgets/weather/StationSkyTwilightPolicy.js");
const cosmos=read("widgets/weather/StationCosmosSubjectPanelPolicy.js");
const moonService=read("services/weather/UsnoMoonService.qml");
const moonPolicy=read("services/weather/UsnoMoonPolicy.js");
const pane=read("widgets/weather/StationCosmosSubjectPane.qml");
const magicPane=read("widgets/weather/StationMagickSubjectPane.qml");
const v=vm.createContext({}),s=vm.createContext({}),n=vm.createContext({}),m=vm.createContext({});
for(const [text,context] of [[policy,v],[skyPolicy,s],[cosmos,n],[moonPolicy,m]])
  vm.runInContext(text.replace(/^\.pragma library\s*$/m,""),context);

test("Moon phase ribbon uses eight named stages, no invented daily calendar",()=>{
    assert.equal(v.FORMAT,"post-apollo.weather.cosmos-visuals.v2.v1");
    assert.deepEqual(JSON.parse(JSON.stringify(v.PHASES.map(x=>x.id))),[
      "new","waxing-crescent","first-quarter","waxing-gibbous",
      "full","waning-gibbous","last-quarter","waning-crescent"]);
    assert.equal(v.normalizedPhase("New Moon"),"new");
    assert.equal(v.normalizedPhase("THIRD QUARTER"),"last-quarter");
    assert.equal(v.normalizedPhase("WAXING GIBBOUS"),"waxing-gibbous");
    assert.equal(v.normalizedPhase("Waning Crescent"),"waning-crescent");
    assert.equal(v.normalizedPhase("UNKNOWN"),"");
    assert.match(qml,/EIGHT PHASE MARKERS \/\/ CURRENT STAGE ONLY/);
    assert.match(qml,/NOT LOCAL OPTICAL ORIENTATION/);
});

test("Moon display prefers USNO and explicitly labels WTTR daily fallback",()=>{
    const usno={available:true,phase:"Waxing Gibbous",
      illumination:71.5,sourceDate:"2026-11-03",
      rise:"06:30 AM",transit:"12:20 PM",set:"06:11 PM"};
    const forecast={available:true,moonPhaseLabel:"FULL MOON",
      moonIllumination:98,date:"2026-11-04"};
    const m1=v.moonDisplay(true,usno,forecast);
    assert.equal(m1.source,"USNO ONE-DAY");
    assert.equal(m1.sourceDate,"2026-11-03");
    assert.equal(m1.phaseId,"waxing-gibbous");
    assert.equal(m1.illumination,71.5);
    assert.equal(m1.waxing,true);
    const f=v.moonDisplay(false,usno,forecast);
    assert.equal(f.source,"WTTR DAILY FORECAST");
    assert.equal(f.phaseId,"full");
    assert.equal(f.illumination,98);
    assert.equal(f.sourceDate,"2026-11-04");
    const missing=v.moonDisplay(false,null,null);
    assert.equal(missing.ready,false);
    assert.equal(missing.illumination,null);
    assert.equal(missing.source,"NO VERIFIED PHASE");
});

test("illumination disk is physically fractional, not a fixed decorative glyph",()=>{
    for(const f of [0,10,25,50,75,90,100]){
        let area=0,whole=0;
        for(let y=-100+0.5;y<100;y+=1){
            const span=v.illuminatedSpan(f,true,y,100);
            area+=span.right-span.left;
            whole+=2*Math.sqrt(10000-y*y);
        }
        assert.ok(Math.abs(area/whole-f/100)<0.003,"fraction "+f);
    }
    for(const f of [10,30,50,70,90]){
        const wax=v.illuminatedSpan(f,true,0,50);
        const wane=v.illuminatedSpan(f,false,0,50);
        assert.equal(wax.left,-wane.right);
        assert.equal(wax.right,-wane.left);
    }
    assert.equal(v.illuminatedSpan(-1,true,0,30),null);
    assert.equal(v.illuminatedSpan(101,true,0,30),null);
    assert.equal(v.illuminatedSpan(40,true,50,30),null);
});

test("solar 24h arc reuses calibrated existing solarPosition; not planetary ephemeris",()=>{
    const date="2026-11-03",lat=38.9,lon=-77.04,offset=-300;
    const modeled=v.solarArc(date,lat,lon,offset,(minute,d,la,lo,off)=>
        s.solarPosition(d,minute,la,lo,off));
    assert.equal(modeled.ready,true);
    assert.equal(modeled.rows.length,73);
    assert.equal(modeled.rows[0].minute,0);
    assert.equal(modeled.rows.at(-1).minute,1439);
    assert.ok(modeled.rows.every(x=>isFinite(x.altitude)&&
                                   x.altitude>=-90&&x.altitude<=90));
    assert.ok(modeled.rows.some(x=>x.altitude>15));
    assert.ok(modeled.rows.some(x=>x.altitude<0));
    const noon=modeled.rows.find(x=>x.minute===720);
    const midnight=modeled.rows[0];
    assert.ok(noon.altitude>midnight.altitude);
    assert.ok(modeled.rows.some(x=>x.aboveHorizon));
    assert.equal(modeled.frame,"LOCAL CIVIL TIME");
    assert.equal(modeled.source,"CALIBRATED SOLAR POSITION MODEL");
    assert.equal(v.positionX(0,400),0);
    assert.equal(v.positionX(1439,400),400);
    assert.equal(v.positionY(0,100),50);
    assert.equal(v.positionY(90,100),0);
    assert.equal(v.positionY(-90,100),100);
    assert.equal(v.clockLabel(720),"12:00");
    assert.equal(v.clockLabel(1439),"23:59");
    assert.equal(v.nearestSolar(modeled.rows,729).minute,720);
});

test("solar arc refuses missing/invalid coordinates, date or civil offset",()=>{
    const calc=(minute,date,lat,lon,offset)=>
      s.solarPosition(date,minute,lat,lon,offset);
    const cases=[
       ["2026-11-03","",0,-300],
       ["2026-11-03",91,0,-300],
       ["2026-11-03",39,181,-300],
       ["2026-11-03",39,-77,null],
       ["2026-11-03",39,-77,1000],
       ["2026-02-30",39,-77,-300],
       ["--",39,-77,-300]
    ];
    for(const args of cases){
        const m=v.solarArc(...args,calc);
        assert.equal(m.ready,false,JSON.stringify(args));
        assert.equal(m.rows.length,0);
    }
    assert.equal(v.nearestSolar([],720),null);
    assert.equal(v.nearestSolar([],null),null);
    assert.equal(v.clockLabel(-1),"--");
});

test("visual is mounted only on route-eligible COSMOS SKY, not CLASSIC or WEATHER",()=>{
    assert.match(sky,/StationCosmosVisualInstruments\s*\{/);
    assert.match(sky,/visible: sky\.subjectRoute\.indexOf\("cosmos\/"\) === 0/);
    assert.match(sky,/showMoon: sky\.sectionVisible\("moon"\)/);
    assert.match(sky,/moonReady: moonService\.ready/);
    assert.match(sky,/moonEphemeris: moonService\.ephemeris/);
    assert.match(sky,/astronomySummary: sky\.astronomySummary/);
    assert.match(sky,/twilightSummary: sky\.twilightSummary/);
    assert.match(sky,/providerLocalMinute: sky\.providerLocalMinute/);
    assert.match(sky,/currentSolarPosition: sky\.currentSolarPosition/);
    assert.equal(n.visibleFor("sky","cosmos/moon/ephemeris","moon"),true);
    assert.equal(n.visibleFor("sky","cosmos/sun/position","astronomy"),true);
    assert.equal(n.visibleFor("sky","cosmos/sun/twilight","twilight"),true);
    assert.equal(n.visibleFor("sky","cosmos/planets-stars/planet-clock","moon"),false);
    assert.equal(n.needsSource("cosmos/overview","moon"),true);
    assert.equal(n.needsSource("cosmos/sun/position","moon"),false);
    assert.match(pane,/StationSky\s*\{/);
    assert.match(magicPane,/StationSky\s*\{/);
    assert.match(moonService,/MoonPolicy\.requestInfo\(date, latitude, longitude, offsetMinutes\)/);
    assert.match(moonPolicy,/function illuminationPercent\(/);
});

test("Canvas interactivity and source claims are explicit",()=>{
    assert.match(qml,/Canvas\s*\{/);
    assert.match(qml,/VisualPolicy\.illuminatedSpan\(/);
    assert.match(qml,/VisualPolicy\.solarArc\(/);
    assert.match(qml,/TwilightPolicy\.solarPosition\(/);
    assert.match(qml,/onClicked: function\(mouse\)/);
    assert.match(qml,/onPositionChanged: function\(mouse\)/);
    assert.match(qml,/visual\.lockedMinute=/);
    assert.match(qml,/onClicked: visual\.lockedMinute=-1/);
    assert.match(qml,/SOLAR MODEL UNAVAILABLE/);
    assert.match(qml,/NOT MEASURED SKY PHOTO/);
    assert.match(qml,/CURRENT STAGE ONLY/);
    assert.match(qml,/NOAA|SOLAR CENTER/);
});

test("V2 adds no independent provider/store, clock, astronomy model or false alignment",()=>{
    for(const source of [policy,qml]){
        for(const forbidden of ["WeatherServices.","Process {","FileView {",
           "XMLHttpRequest","new WebSocket","StationTerminal {",
           "Qt.callLater","Timer {","swaymsg","curl ",
           "zodiacLongitude","retrograde","planetaryHour","aspectAngle",
           "writeAdapter()","archiveEvent(","capture("]){
            assert.ok(!source.includes(forbidden),forbidden);
        }
    }
    assert.ok(!qml.includes("UsnoMoonService {"));
    assert.ok(!qml.includes("UsnoPlanetRiseSetService {"));
    assert.match(qml,/NO SEPARATE/mi.test(qml) ? /NO SEPARATE/i : /No separate USNO service/);
});
