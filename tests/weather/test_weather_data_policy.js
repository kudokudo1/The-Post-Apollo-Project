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
    "parseAirQualityForecast",
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

const hourlyForecast = context.parseAirQualityForecast({
    time: Array.from({length: 12}, (_, i) => "2026-10-22T" + String(i + 10).padStart(2, "0") + ":00"),
    us_aqi: [30, 31, 50, 51, null, 76, 120, 121, 160, 161, 200, 201],
    pm2_5: [8.2, 8.3, 9.3, 9.4, null, 10.1, 14.4, 14.5, 21, 21.1, 28, 29],
    pm10: [12.1, 12.2, 14, 14.1, null, 16, 22, 23, 26, 27, 34, 35],
}, 12);
assert.equal(hourlyForecast.length, 6);
assert.deepEqual(Array.from(hourlyForecast, x => x.label), ["10 AM", "12 PM", "2 PM", "4 PM", "6 PM", "8 PM"]);
assert.equal(hourlyForecast[0].aqi, 30);
assert.equal(hourlyForecast[1].aqi, 50);
assert.equal(hourlyForecast[2].aqi, -1);
assert.equal(hourlyForecast[2].pm25, -1);
assert.equal(hourlyForecast[5].pm10, 34);
assert.equal(context.parseAirQualityForecast(null, 12).length, 0);
assert.equal(context.parseAirQualityForecast({time: [], us_aqi: []}, 12).length, 0);
assert.equal(context.parseAirQualityForecast({
    time: ["bad", "2026-10-22T13:00"],
    us_aqi: [0, 22]
}, 12).length, 0);
assert.equal(context.parseAirQualityForecast({
    time: ["2026-10-22T07:00"],
    us_aqi: [null],
    pm2_5: [null]
}, 12)[0].aqi, -1);


// The worldwide USGS GeoJSON feed is independent of AQI and location.
// Validate sorting, missing data, coordinate order and distance calculations.
const seismicSource = fs.readFileSync(
    path.join(root, "services/weather/SeismicPolicy.js"), "utf8"
).replace(/^\.pragma library\s*/m, "");
const seismic = {};
vm.runInNewContext(seismicSource, seismic);

assert.equal(typeof seismic.parseFeed, "function");
assert.equal(typeof seismic.distanceKm, "function");
assert.equal(typeof seismic.formatUtc, "function");
const earthquake = (id, mag, time, lon, lat, depth, place) => ({
    type: "Feature",
    id,
    properties: { type: "earthquake", mag, time, place },
    geometry: { type: "Point", coordinates: [lon, lat, depth] }
});
const feed = {
    type: "FeatureCollection",
    features: [
        earthquake("a", 2.7, 1600000000000, -121.5, 38, 8.6, "Northern California"),
        earthquake("b", 4.8, 1600001000000, -118, 34, 11.2, "Los Angeles"),
        earthquake("ignored", null, 1600002000000, 140, -30, 2, "Unknown magnitude"),
        earthquake("older", 3.1, 1500000000000, 135, 40, 21, "Japan"),
        earthquake("c", 3.4, 1600003000000, -150, 61, 4.5, "Alaska"),
        { type: "Feature", properties: { type: "quarry blast", mag: 3, time: 1600004000000 },
          geometry: { type: "Point", coordinates: [-120, 40, 6] } }
    ]
};
const latestQuakes = seismic.parseFeed(feed, 3);
assert.equal(latestQuakes.length, 3);
assert.deepEqual(Array.from(latestQuakes, v => v.id), ["c", "b", "a"]);
assert.equal(latestQuakes[0].magnitude, 3.4);
assert.equal(latestQuakes[0].latitude, 61);
assert.equal(latestQuakes[0].longitude, -150);
assert.equal(latestQuakes[0].depthKm, 4.5);
assert.match(latestQuakes[0].utc, /^\d{2}:\d{2} UTC$/);
assert.equal(seismic.parseFeed({type: "FeatureCollection", features: []}, 3).length, 0);
assert.throws(() => seismic.parseFeed({features: []}, 3));
assert.throws(() => seismic.parseFeed(null, 3));
assert.ok(Math.abs(seismic.distanceKm(0, 0, 0, 1) - 111.195) < 0.2);
assert.equal(seismic.distanceKm(0, 0, 0, 0), 0);
assert.equal(seismic.distanceKm("", "", 0, 0), -1);
assert.equal(seismic.distanceKm(91, 0, 0, 0), -1);
assert.equal(seismic.distanceKm(0, 181, 0, 0), -1);


// NOAA OVATION covers the globe at one-degree intervals. Its largest
// hemispheric grid values are not an observer-specific viewing probability.
const auroraSource = fs.readFileSync(
    path.join(root, "services/weather/AuroraPolicy.js"), "utf8"
).replace(/^\.pragma library\s*/m, "");
const aurora = {};
vm.runInNewContext(auroraSource, aurora);
assert.equal(typeof aurora.parseOvation, "function");
assert.equal(typeof aurora.utcLabel, "function");

const ovation = {
    "Observation Time": "2026-10-22T20:00:00Z",
    "Forecast Time": "2026-10-22T21:00:00Z",
    "Data Format": "[Longitude, Latitude, Aurora]",
    coordinates: [
        [0, 63, 24], [10, 65, 85], [20, 67, 18],
        [1, -58, 5], [3, -72, 46], [4, -62, 34],
        [5, 0, 100], [6, 43, null], [7, -30, -1],
        [370, 44, 99], [9, -95, 92], [1, 55, 120],
    ],
};
const ovationSummary = aurora.parseOvation(ovation);
assert.equal(ovationSummary.northPeak, 85);
assert.equal(ovationSummary.southPeak, 46);
assert.equal(ovationSummary.northCells, 3);
assert.equal(ovationSummary.southCells, 3);
assert.equal(aurora.utcLabel(ovationSummary.forecastTimeMs), "21:00 UTC");
assert.equal(aurora.utcLabel(ovationSummary.observationTimeMs), "20:00 UTC");
assert.equal(aurora.utcLabel(0), "-- UTC");
assert.throws(() => aurora.parseOvation(null));
assert.throws(() => aurora.parseOvation({coordinates: []}));
assert.throws(() => aurora.parseOvation({
    ...ovation, "Forecast Time": "2026-10-22T19:59:00Z"
}));
assert.throws(() => aurora.parseOvation({
    ...ovation, coordinates: [[0, 60, 40]]
}));

console.log("Weather data policy contracts: PASS");
