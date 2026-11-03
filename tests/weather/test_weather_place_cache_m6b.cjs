#!/usr/bin/env node
"use strict";
// Disposable, offline M6b policy tests: no network, desktop or user data.
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const path=require("node:path");
const source=fs.readFileSync(
    path.join(__dirname,"../../services/weather/WeatherPlaceCachePolicy.js"),
    "utf8"
).replace(/^\.pragma library\s*/,"");
const p=vm.runInNewContext(source+
  "\n;({initialDocument,key,payload,parse,normalizeDocument,upsert,record})");
const home="MANUAL|38.8243|-76.7451";
const alaska="MANUAL|61.2181|-149.9003";
const zero="MANUAL|0|0";
const t=1793710800000;

assert.equal(p.key(home),home);
assert.equal(p.key(alaska),alaska);
assert.equal(p.key(zero),zero);
for (const bad of ["","MANUAL||","MANUAL|0|","MANUAL||0","MANUAL|91|0",
                   "MANUAL|0|181","MANUAL|foo|0","LEGACY|38|-76",
                   "MANUAL|00|0","MANUAL|0.0000000|0",null]) {
    assert.equal(p.key(bad),"",String(bad));
}
const current={
    tempF:"41",feelsLikeF:"36",condition:"Overcast",
    weatherCode:"122",uvIndex:-1,humidity:"52",windMph:"6",
    windDirection:"NW",pressureHpa:1012,visibilityMiles:-1,
    cloudCover:90,precipMm:0,observationTime:"8 AM",
    localObservationDateTime:"2026-11-03 08:00:00"
};
const forecast={
    hourlyForecast:[{date:"2026-11-03",timeLabel:"9 AM",tempF:42}],
    dailyForecast:[{date:"2026-11-03",maxTempF:47,minTempF:35,
                    moonPhase:"--"}]
};
const aqi={aqi:23,aqiLabel:"GOOD",pm25:3,pm10:5,pollenAvailable:false,
           airQualityUtcOffsetMinutes:null,airQualityForecast:[]};
let doc=p.initialDocument();
assert.equal(doc.records.length,0);
assert.equal(p.record(doc,"weather-current",home,t),null);
const r1=p.upsert(doc,"weather-current",t,"WTTR",current);
// Invalid API ordering or missing key must not accidentally be accepted.
assert.equal(r1.ok,false);
const homeCurrent=p.upsert(doc,"weather-current",home,t,"WTTR",current);
assert.equal(homeCurrent.ok,true,homeCurrent.reason);
doc=homeCurrent.document;
assert.equal(doc.revision,1);
assert.equal(doc.records.length,1);
assert.equal(p.record(doc,"weather-current",home,t).provider,"WTTR");
assert.equal(p.record(doc,"weather-current",alaska,t),null);
assert.equal(p.record(doc,"weather-forecast",home,t),null);
assert.equal(p.record(doc,"weather-current",home,t+5400000).payload.tempF,"41");
assert.equal(p.record(doc,"weather-current",home,t+5400001),null);
assert.equal(p.record(doc,"weather-current",home,t-1),null);
assert.equal(p.record(doc,"weather-current",home,"bad"),null);

const homeForecast=p.upsert(doc,"weather-forecast",home,t,"WTTR",forecast);
assert.equal(homeForecast.ok,true,homeForecast.reason);
doc=homeForecast.document;
assert.equal(p.record(doc,"weather-forecast",home,t+43200000).provider,"WTTR");
assert.equal(p.record(doc,"weather-forecast",home,t+43200001),null);
const homeAqi=p.upsert(doc,"air-quality",home,t,"OPEN_METEO_AQI",aqi);
assert.equal(homeAqi.ok,true,homeAqi.reason);
doc=homeAqi.document;
assert.equal(p.record(doc,"air-quality",home,t).payload.aqi,23);
assert.equal(p.record(doc,"air-quality",home,t+10800001),null);
assert.equal(p.record(doc,"air-quality",alaska,t),null);

const alaskaCurrent={...current,tempF:"31",condition:"Snow"};
doc=p.upsert(doc,"weather-current",alaska,t+2000,"OPEN_METEO",
             alaskaCurrent).document;
doc=p.upsert(doc,"weather-forecast",alaska,t+2000,"OPEN_METEO",
             forecast).document;
assert.equal(p.record(doc,"weather-current",home,t+3000).payload.tempF,"41");
assert.equal(p.record(doc,"weather-current",alaska,t+3000).payload.tempF,"31");
assert.equal(p.record(doc,"weather-forecast",home,t+3000).provider,"WTTR");
assert.equal(p.record(doc,"weather-forecast",alaska,t+3000).provider,"OPEN_METEO");

// A restart sees the same exact coordinate keys and timestamps.
const restored=p.parse(JSON.stringify(doc));
assert.equal(restored.ok,true,restored.reason);
assert.equal(p.record(restored.document,"weather-current",home,t+3000)
             .payload.tempF,"41");
assert.equal(p.record(restored.document,"weather-current",alaska,t+3000)
             .payload.tempF,"31");
assert.equal(p.record(restored.document,"weather-current",home,t+5400001),null);
assert.equal(p.record(restored.document,"weather-current",zero,t),null);

// Replacing one point does not erase or rename the other.
const updated=p.upsert(doc,"weather-current",home,t+4000,"OPEN_METEO",
                       {...current,tempF:"50"});
assert.equal(updated.ok,true);
assert.equal(p.record(updated.document,"weather-current",home,t+4001)
             .payload.tempF,"50");
assert.equal(p.record(updated.document,"weather-current",alaska,t+4001)
             .payload.tempF,"31");
assert.equal(p.upsert(doc,"weather-current",home,t-1,"WTTR",current).reason,
             "OLDER_RECORD");

for(const bad of [
    ["weather-current",home,t,"OPEN_METEO_AQI",current],
    ["air-quality",home,t,"WTTR",aqi],
    ["weather-current","LEGACY|",t,"WTTR",current],
    ["weather-current","MANUAL||",t,"WTTR",current],
    ["weather-current",home,-1,"WTTR",current],
    ["weather-current",home,t,"WTTR",{...current,tempF:"--"}],
    ["weather-forecast",home,t,"WTTR",{hourlyForecast:[],dailyForecast:[]}],
    ["air-quality",home,t,"OPEN_METEO_AQI",{...aqi,aqi:501}]
]) {
    const invalid=p.upsert(doc,...bad);
    assert.equal(invalid.ok,false,String(bad));
}
const tampered=JSON.parse(JSON.stringify(doc));
tampered.records.push({...tampered.records[0]});
assert.equal(p.normalizeDocument(tampered).reason,"DUPLICATE_RECORD");
const invalidKey=JSON.parse(JSON.stringify(doc));
invalidKey.records[0].scopeKey="MANUAL|91|0";
assert.equal(p.normalizeDocument(invalidKey).reason,"INVALID_RECORD");
const invalidTimestamp=JSON.parse(JSON.stringify(doc));
invalidTimestamp.records[0].receivedAtMs="1793710800000";
assert.equal(p.normalizeDocument(invalidTimestamp).reason,"INVALID_RECORD");
assert.equal(p.parse("{broken").reason,"INVALID_JSON");
assert.equal(p.parse("x".repeat(262145)).reason,"DOCUMENT_TOO_LARGE_OR_EMPTY");
assert.equal(p.parse(JSON.stringify({...doc,version:2})).reason,
             "UNSUPPORTED_VERSION");
assert.equal(p.parse(JSON.stringify({...doc,records:{}})).reason,
             "INVALID_RECORDS");

// Deterministic bounded history: adding a 31st destination/source record
// removes the oldest one; it can never return under a different location.
let full=p.initialDocument();
for(let i=0;i<31;i++){
    const k="MANUAL|"+(i+1)+"|0";
    const inserted=p.upsert(full,"weather-current",k,t+i,"WTTR",current);
    assert.equal(inserted.ok,true,inserted.reason);
    full=inserted.document;
}
assert.equal(full.records.length,30);
assert.equal(p.record(full,"weather-current","MANUAL|1|0",t+40),null);
assert.equal(p.record(full,"weather-current","MANUAL|31|0",t+40)
             .scopeKey,"MANUAL|31|0");
console.log("Weather M6b per-location cache, TTL, migration isolation and bounds: PASS");
