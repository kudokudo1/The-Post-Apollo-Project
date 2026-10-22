#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const source = fs.readFileSync(
    path.join(root, "services/weather/WeatherDataPolicy.js"),
    "utf8"
).replace(/^\.pragma library\s*/m, "");

const context = {};
vm.runInNewContext(source, context);

for (const name of [
    "currentAtmosphere",
    "parseForecast",
    "parseAirQuality",
])
    assert.equal(typeof context[name], "function", name);

const current = {
    localObsDateTime: "2026-10-22 06:20 AM",
    pressure: "1014",
    visibility: "16",
    cloudcover: "63",
    precipMM: "0.4",
};

const atmosphere = context.currentAtmosphere(current);
assert.equal(atmosphere.pressureHpa, 1014);
assert.ok(Math.abs(atmosphere.visibilityMiles - 9.941936) < 0.0001);
assert.equal(atmosphere.cloudCover, 63);
assert.equal(atmosphere.precipMm, 0.4);
assert.equal(atmosphere.observationTime, current.localObsDateTime);

function hour(time, tempF, condition, rain, extra = {}) {
    return {
        time: String(time),
        tempF: String(tempF),
        FeelsLikeF: String(tempF - 1),
        DewPointF: String(tempF - 10),
        humidity: "70",
        chanceofrain: String(rain),
        chanceofsnow: "0",
        precipMM: rain > 0 ? "0.5" : "0",
        pressure: "1013",
        visibilityMiles: "9",
        cloudcover: "55",
        uvIndex: "2",
        windspeedMiles: "8",
        winddir16Point: "NW",
        weatherCode: "116",
        weatherDesc: [{value: condition}],
        ...extra,
    };
}

const payload = {
    weather: [
        {
            date: "2026-10-22",
            maxtempF: "72",
            mintempF: "51",
            avgtempF: "62",
            uvIndex: "4",
            astronomy: [{
                sunrise: "07:21 AM",
                sunset: "06:18 PM",
                moon_phase: "Waxing Gibbous",
                moon_illumination: "82",
            }],
            hourly: [
                hour(0, 54, "Clear", 0),
                hour(300, 53, "Clear", 0),
                hour(600, 55, "Partly cloudy", 10),
                hour(900, 61, "Cloudy", 20),
                hour(1200, 69, "Light rain", 60),
                hour(1500, 72, "Light rain", 70),
                hour(1800, 65, "Cloudy", 30),
                hour(2100, 59, "Clear", 10),
            ],
        },
        {
            date: "2026-10-23",
            maxtempF: "68",
            mintempF: "49",
            avgtempF: "59",
            uvIndex: "3",
            astronomy: [{
                sunrise: "07:22 AM",
                sunset: "06:17 PM",
                moon_phase: "Waxing Gibbous",
                moon_illumination: "89",
            }],
            hourly: [
                hour(0, 52, "Clear", 0),
                hour(300, 50, "Clear", 0),
                hour(600, 51, "Cloudy", 20),
            ],
        },
    ],
};

const forecast = context.parseForecast(payload, current, 6);
assert.equal(forecast.hourly.length, 6);
assert.equal(forecast.hourly[0].timeLabel, "6 AM");
assert.equal(forecast.hourly[0].tempF, 55);
assert.equal(forecast.hourly[2].chanceRain, 60);
assert.equal(forecast.hourly[2].dewPointF, 59);
assert.equal(forecast.hourly[5].timeLabel, "9 PM");

assert.equal(forecast.daily.length, 2);
assert.equal(forecast.daily[0].maxTempF, 72);
assert.equal(forecast.daily[0].minTempF, 51);
assert.equal(forecast.daily[0].chanceRain, 70);
assert.equal(forecast.daily[0].sunrise, "07:21 AM");
assert.equal(forecast.daily[0].sunset, "06:18 PM");
assert.equal(forecast.daily[0].moonPhase, "Waxing Gibbous");

const air = context.parseAirQuality({
    time: "2026-10-22T06:15",
    us_aqi: 42,
    us_aqi_ozone: 37,
    us_aqi_nitrogen_dioxide: 18,
    us_aqi_carbon_monoxide: 9,
    pm2_5: 7.2,
    pm10: 14.1,
    carbon_monoxide: 187,
    nitrogen_dioxide: 11.5,
    ozone: 58.4,
    dust: 2.1,
    alder_pollen: null,
    birch_pollen: null,
    grass_pollen: 3.5,
    mugwort_pollen: null,
    olive_pollen: null,
    ragweed_pollen: 8.4,
});

assert.equal(air.usAqi, 42);
assert.equal(air.ozoneAqi, 37);
assert.equal(air.nitrogenDioxideAqi, 18);
assert.equal(air.carbonMonoxideAqi, 9);
assert.equal(air.pm25, 7.2);
assert.equal(air.pm10, 14.1);
assert.equal(air.carbonMonoxide, 187);
assert.equal(air.nitrogenDioxide, 11.5);
assert.equal(air.ozone, 58.4);
assert.equal(air.dust, 2.1);
assert.equal(air.grassPollen, 3.5);
assert.equal(air.ragweedPollen, 8.4);
assert.equal(air.alderPollen, -1);
assert.equal(air.pollenAvailable, true);

const noPollen = context.parseAirQuality({
    us_aqi: 20,
    pm2_5: 2,
    pm10: 4,
});
assert.equal(noPollen.pollenAvailable, false);

console.log("Weather data policy contracts: PASS");
