"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");

const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const ctx=vm.createContext({});
vm.runInContext(read("widgets/weather/StationCosmosPlanetDayWheelPolicy.js")
    .replace(/^\.pragma library\s*$/m,""),ctx);
const strip=read("widgets/weather/StationCosmosPlanetsSkyStrip.qml");
const modes=read("widgets/weather/StationCosmosModesPane.qml");
const names=Array.from(ctx.PLANETS);

test("C40 fixed order moves both directions over all five planets",()=>{
 assert.deepEqual(names,["MERCURY","VENUS","MARS","JUPITER","SATURN"]);
 for(let i=0;i<names.length;i++) {
    const prev=names[(i+names.length-1)%names.length];
    const next=names[(i+1)%names.length];
    assert.equal(ctx.adjacentPlanet(names[i],-1),prev,names[i]+" left");
    assert.equal(ctx.adjacentPlanet(names[i],1),next,names[i]+" right");
 }
 assert.equal(ctx.adjacentPlanet("ALL",1),"MERCURY");
 assert.equal(ctx.adjacentPlanet("ALL",-1),"SATURN");
 assert.equal(ctx.adjacentPlanet("UNKNOWN",1),"MERCURY");
 assert.equal(ctx.adjacentPlanet("UNKNOWN",-1),"SATURN");
 for(const invalid of [0,2,-2,null,undefined])
    assert.equal(ctx.adjacentPlanet("MARS",invalid),"");
});

test("C40 SKY NOW arrows use five-ring order, not the USNO snapshot subset",()=>{
 assert.match(strip,/import "StationCosmosPlanetDayWheelPolicy\.js" as DayWheel/);
 assert.match(strip,/readonly property int selectablePlanetCount: DayWheel\.PLANETS\.length/);
 assert.match(strip,/const target = DayWheel\.adjacentPlanet\(selectedPlanet, delta\)/);
 assert.match(strip,/if \(target\) planetPicked\(target\)/);
 assert.doesNotMatch(strip,/const i=currentIndex\s*<\s*0/);
 assert.doesNotMatch(strip,/planetPicked\(String\(records\[i\]/);
 assert.match(strip,/objectName: "cosmos-c39-sky-prev"[\s\S]*?onClicked: strip\.stepPlanet\(-1\)/);
 assert.match(strip,/objectName: "cosmos-c39-sky-next"[\s\S]*?onClicked: strip\.stepPlanet\(1\)/);
 assert.equal((strip.match(/available: strip\.selectablePlanetCount>0/g)||[]).length,2);
 assert.doesNotMatch(strip,/available: strip\.recordCount>0/);
});

test("C40 still declines to invent instantaneous sky positions for an unsampled planet",()=>{
 assert.match(strip,/readonly property var records: Details\.records\("planets",snapshot/);
 assert.match(strip,/readonly property var currentRecord: currentIndex >= 0/);
 assert.match(strip,/readonly property string sourceNote: reading\.sourceNote/);
 assert.match(strip,/available: strip\.detailAvailable/);
 assert.match(modes,/selectedPlanet: cosmosModePane\.planetSelection/);
 assert.match(modes,/cosmosModePane\.planetSelection = name/);
 const onlySaturn=[{name:"SATURN",altitude:13.5,azimuth:222,direction:"SW"}];
 assert.equal(onlySaturn.length,1);
 assert.equal(names.length,5);
 assert.equal(ctx.adjacentPlanet("SATURN",1),"MERCURY");
 assert.equal(ctx.adjacentPlanet("SATURN",-1),"JUPITER");
});
