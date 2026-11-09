"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const ctx=vm.createContext({});
const load=p=>vm.runInContext(
    read(p).replace(/^\.pragma library\s*$/m,""),ctx);
load("widgets/weather/StationCosmosPlanetEventPolicy.js");
const clockRows=ctx.clockRows;
load("widgets/weather/StationCosmosPlanetSummaryPolicy.js");
const summary=ctx;
const strip=read("widgets/weather/StationCosmosPlanetsSkyStrip.qml");
const modes=read("widgets/weather/StationCosmosModesPane.qml");
const detail=read("widgets/weather/StationCosmosPlanetDatedDetailsPane.qml");
const date="2026-11-08";
const names=["MERCURY","VENUS","MARS","JUPITER","SATURN"];
function data(name,i){
  return {name,date,status:"NORMAL",
    rise:"0"+(i+3)+":14",riseAzimuth:80+i,
    transit:"1"+i+":32",transitAltitude:41+i,transitHemisphere:"S",
    set:"1"+(i+5)+":45",setAzimuth:275-i};
}
const rows=clockRows(names.map(data),date);
const saturnOnly=[{name:"SATURN",altitude:13.5,azimuth:222,direction:"SW"}];
const plain=o=>JSON.parse(JSON.stringify(o));

test("C41 five dated records remain inspectable even when CelNav contains Saturn alone",()=>{
 assert.equal(rows.length,5);
 for(let i=0;i<names.length;i++){
   const name=names[i];
   const result=summary.selection(name,saturnOnly,rows,date,true,true,"17:00");
   assert.equal(result.planet,name);
   assert.equal(result.currentIndex,name==="SATURN"?0:-1);
   assert.equal(result.mode,name==="SATURN"?"current":"dated");
   assert.equal(result.detailAvailable,true);
   assert.equal(result.values.some(x=>x==="--"),false,name);
   if(name==="SATURN"){
     assert.equal(result.labels[0],"ALT // HC");
     assert.equal(result.values[0],"13.5°");
     assert.equal(result.values[1],"222.0°");
     assert.equal(result.values[2],"SW");
   }else{
     assert.deepEqual(plain(result.labels),["RISE","TRANSIT","SET"]);
     assert.deepEqual(plain(result.values),
       [data(name,i).rise,data(name,i).transit,data(name,i).set]);
     assert.equal(result.sourceNote,"USNO MRST // DAY");
     assert.equal(result.stamp,date+" LOCAL");
     const facts=summary.datedFacts(result.datedRow,date,name);
     assert.equal(facts.length,12);
     assert.equal(facts[2].value,data(name,i).rise);
     assert.equal(facts[4].value,data(name,i).transit);
     assert.equal(facts[7].value,data(name,i).set);
     assert.equal(facts[10].value,"USNO MRST");
     assert.equal(facts[11].value,"ONE MINUTE // DATED EVENTS");
   }
 }
});

test("C41 rejects wrong-date source events and marks no-response statuses",()=>{
 const wrong=summary.selection("MERCURY",[],rows,"2026-11-09",true,true,"17:00");
 assert.equal(wrong.mode,"unavailable");
 assert.equal(wrong.detailAvailable,false);
 assert.equal(wrong.values[0],"--");
 const empty=clockRows([] ,date);
 const missing=summary.selection("VENUS",[],empty,date,true,true,"17:00");
 assert.equal(missing.mode,"dated");
 assert.equal(missing.status,"NO DATED RESPONSE");
 assert.deepEqual(plain(missing.values),["--","--","--"]);
 assert.match(missing.sourceNote,/NO DATED RESPONSE/);
 const waiting=summary.selection("MARS",[],rows,date,false,false,"17:00");
 assert.equal(waiting.mode,"unavailable");
 assert.equal(waiting.detailAvailable,false);
 const specialRows=clockRows([{name:"MARS",date,status:"CONTINUOUSLY BELOW HORIZON"}],date);
 const special=summary.selection("MARS",[],specialRows,date,true,true,"17:00");
 assert.equal(special.mode,"dated");
 assert.match(special.sourceNote,/CONTINUOUSLY BELOW HORIZON/);
 assert.deepEqual(plain(special.values),["--","--","--"]);
});

test("C41 current CelNav observations retain their actual ALT/AZ/DIR and UTC date",()=>{
 const current=summary.selection("SATURN",saturnOnly,rows,date,true,true,"17:00");
 assert.equal(current.mode,"current");
 assert.equal(current.sourceNote,"CURRENT FIX");
 assert.equal(current.stamp,"17:00 UTC");
 assert.equal(current.values[0],"13.5°");
 assert.equal(current.values[1],"222.0°");
 assert.equal(current.values[2],"SW");
 assert.equal(summary.selection("ALL",saturnOnly,rows,date,true,true,"17:00").planet,"SATURN");
 assert.equal(summary.selection("ALL",[],rows,date,true,true,"17:00").planet,"MERCURY");
});

test("C41 lower bar changes metric labels with source, preserves both arrows and details",()=>{
 assert.match(strip,/import "StationCosmosPlanetSummaryPolicy\.js" as Summary/);
 assert.match(strip,/readonly property var reading: Summary\.selection\(/);
 assert.match(strip,/datedRows: \[\]/);
 assert.match(strip,/datedSourceReady: false/);
 assert.match(strip,/strip\.reading\.mode === "current"/);
 for(let i=0;i<3;i++){
   assert.match(strip,new RegExp("strip\\.reading\\.labels\\["+i+"\\]"));
   assert.match(strip,new RegExp("strip\\.reading\\.values\\["+i+"\\]"));
 }
 assert.match(strip,/text: strip\.reading\.stamp/);
 assert.match(strip,/available: strip\.detailAvailable/);
 assert.match(strip,/onClicked: strip\.stepPlanet\(-1\)/);
 assert.match(strip,/onClicked: strip\.stepPlanet\(1\)/);
 assert.match(modes,/datedRows: cosmosModePane\.planetRows/);
 assert.match(modes,/datedSourceReady: !!cosmosModePane\.planetSource/);
 assert.match(modes,/cosmosModePane\.skyDetailsMode = index >= 0/);
 assert.match(modes,/id: planetsDatedDetailsComponent/);
 assert.match(modes,/StationCosmosPlanetDatedDetailsPane\s*\{/);
 assert.match(modes,/sourceComponent: cosmosModePane\.skyDetailsMode === "dated"/);
 assert.match(detail,/objectName: "cosmos-c41-dated-planet-details"/);
 assert.match(detail,/Summary\.datedFacts\(/);
 assert.match(detail,/columns: 3/);
 assert.match(detail,/NOT A CURRENT-SKY POSITION/);
});
