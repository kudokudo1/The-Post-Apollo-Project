#!/usr/bin/env node
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const src = fs.readFileSync(
    path.join(__dirname,"../../services/weather/OpenMeteoFallbackPolicy.js"),
    "utf8"
).replace(/^\.pragma library\s*/,"");
const p = vm.runInNewContext(src +
    "\n;({point,endpoint,wmo,compass,timeLabel,parse})");
for (const pair of [
    ["","0"],["0",""],["NaN","0"],["0","Infinity"],
    ["91","0"],["-91","0"],["0","181"],["0","-181"],
    [null,0],[0,undefined],["12abc","4"],["0x12",0],
]) assert.equal(p.endpoint(pair[0],pair[1]),"",String(pair));
assert.ok(p.endpoint("0","0").includes("latitude=0&longitude=0"));
assert.ok(p.endpoint("61.2181","-149.9003").includes(
    "latitude=61.2181&longitude=-149.9003"));
const url = p.endpoint(40,-75);
for (const val of ["current=temperature_2m","hourly=temperature_2m",
                   "daily=weather_code","timezone=auto","forecast_days=3",
                   "temperature_unit=fahrenheit","wind_speed_unit=mph"])
    assert.ok(url.includes(val),val);
assert.equal(p.wmo(0).weatherCode,"113");
assert.equal(p.wmo(2).description,"Partly cloudy");
assert.equal(p.wmo(61).weatherCode,"296");
assert.equal(p.wmo(95).description,"Thunderstorm");
assert.equal(p.wmo(500).weatherCode,"");
assert.equal(p.compass(0),"N");
assert.equal(p.compass(90),"E");
assert.equal(p.compass(360),"N");
assert.equal(p.compass(null),"--");
assert.equal(p.timeLabel("2026-11-03T18:00"),"6 PM");
assert.equal(p.timeLabel("2026-11-03T18:30"),"6:30 PM");

const fixture = {
    latitude:61.2,longitude:-149.9,timezone:"America/Anchorage",
    current: {
        time:"2026-11-03T18:00",temperature_2m:31.2,
        apparent_temperature:24.1,relative_humidity_2m:81,
        precipitation:0.6,weather_code:71,cloud_cover:73,
        pressure_msl:1005.3,wind_speed_10m:9.4,wind_direction_10m:92
    },
    hourly: {
        time:["2026-11-03T16:00","2026-11-03T17:00",
              "2026-11-03T18:00","2026-11-03T19:00",
              "2026-11-03T20:00","2026-11-03T21:00",
              "2026-11-03T22:00","2026-11-03T23:00",
              "2026-11-04T00:00"],
        temperature_2m:[35,34,31,30,28,27,25,22,20],
        apparent_temperature:[32,31,24,23,20,19,18,15,14],
        relative_humidity_2m:[70,75,81,82,82,85,86,88,90],
        dew_point_2m:[30,29,27,26,25,24,23,22,20],
        precipitation_probability:[10,10,20,30,35,40,40,45,50],
        precipitation:[0,0,0.6,0.4,0.2,0.1,0,0,0],
        pressure_msl:[1007,1006,1005,1005,1004,1003,1002,1002,1000],
        cloud_cover:[60,66,73,75,80,85,87,90,95],
        wind_speed_10m:[8,8,9.4,10,9,9,10,11,12],
        wind_direction_10m:[90,90,92,110,110,120,125,140,145],
        weather_code:[3,3,71,71,71,71,71,71,71]
    },
    daily: {
        time:["2026-11-03","2026-11-04","2026-11-05"],
        weather_code:[71,3,61],
        temperature_2m_max:[36,33,38],
        temperature_2m_min:[23,21,22],
        precipitation_probability_max:[85,15,50],
        sunrise:["2026-11-03T09:00","2026-11-04T09:04","2026-11-05T09:06"],
        sunset:["2026-11-03T17:10","2026-11-04T17:08","2026-11-05T17:06"]
    }
};
const parsed=p.parse(JSON.stringify(fixture));
assert.equal(parsed.ok,true,parsed.reason||"");
assert.equal(parsed.current.tempF,"31.2");
assert.equal(parsed.current.condition,"Snow");
assert.equal(parsed.current.weatherCode,"227");
assert.equal(parsed.current.windDirection,"E");
assert.equal(parsed.current.localObservationDateTime,"2026-11-03 18:00:00");
assert.equal(parsed.current.uvIndex,-1);
assert.equal(parsed.current.visibilityMiles,-1);
assert.equal(parsed.hourly.length,6);
assert.equal(parsed.hourly[0].date,"2026-11-03");
assert.equal(parsed.hourly[0].timeLabel,"6 PM");
assert.equal(parsed.hourly[0].chanceRain,20);
assert.equal(parsed.hourly[0].chanceSnow,-1);
assert.equal(parsed.hourly[0].weatherCode,"227");
assert.equal(parsed.daily.length,3);
assert.equal(parsed.daily[0].sunrise,"9 AM");
assert.equal(parsed.daily[0].sunset,"5:10 PM");
assert.equal(parsed.daily[0].moonPhase,"--");
assert.equal(parsed.daily[0].avgTempF,-999);

// No invented observations from omitted fields.
const sparse={current:{time:"2026-11-03T10:15",temperature_2m:0,
                     weather_code:0}};
const sparseResult=p.parse(JSON.stringify(sparse));
assert.equal(sparseResult.ok,true);
assert.equal(sparseResult.current.tempF,"0");
assert.equal(sparseResult.current.humidity,"--");
assert.equal(sparseResult.current.windDirection,"--");
assert.equal(sparseResult.hourly.length,0);
assert.equal(sparseResult.daily.length,0);
for (const bad of [
    "", "invalid-json", "x".repeat(262145),
    JSON.stringify({error:true,reason:"bad"}),
    JSON.stringify({current:{time:"",temperature_2m:20}}),
    JSON.stringify({current:{time:"2026-11-03T10:00",temperature_2m:null}}),
    JSON.stringify({current:{time:"2026-11-03T10:00",temperature_2m:""}})
]) assert.equal(p.parse(bad).ok,false,bad.slice(0,100));
console.log("Weather M6 Open-Meteo fallback parser and no-invented-values: PASS");
