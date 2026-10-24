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


// NOAA GOES XRS flares are peak-class event observations, not a solar
// prediction, an R-scale radio blackout warning or live X-ray flux.
const flareSource = fs.readFileSync(
    path.join(root, "services/weather/SolarFlarePolicy.js"), "utf8"
).replace(/^\.pragma library\s*/m, "");
const flares = {};
vm.runInNewContext(flareSource, flares);

assert.equal(typeof flares.parseFlares, "function");
assert.equal(typeof flares.parseClass, "function");
assert.equal(flares.parseClass("M5.3").label, "M5.3");
assert.equal(flares.parseClass("x1.0").letter, "X");
assert.equal(flares.parseClass("C0.0"), null);
assert.equal(flares.parseClass("G2"), null);
assert.equal(flares.parseClass(null), null);
const now = Date.parse("2026-10-23T12:00:00Z");
const flare = (peak, magnitude, satellite = 18, end = null) => ({
    satellite: satellite,
    begin_time: "2026-10-23T06:00:00Z",
    max_time: peak,
    max_class: magnitude,
    end_time: end,
    max_xrlong: 0.00001,
});
const records = [
    flare("2026-10-23T07:00:00Z", "C2.1"),
    flare("2026-10-23T11:00:00Z", "M5.3", 19, "2026-10-23T11:14:00Z"),
    flare("2026-10-23T10:00:00Z", "B8.7"),
    flare("2026-10-22T10:00:00Z", "X1.1"),
    flare("2026-10-23T11:00:00Z", "M5.3", 19), // duplicate
    flare("2026-10-23T09:00:00Z", null),       // unclassified
    flare("2026-10-24T08:00:00Z", "X2.0"),     // invalid future
    flare("not-a-time", "C3.0"),                // invalid timestamp
];
const result = flares.parseFlares(records, now);
assert.equal(result.events.length, 3);
assert.deepEqual(Array.from(result.events, f => f.classLabel),
                 ["M5.3", "B8.7", "C2.1"]);
assert.equal(result.latest.satellite, "GOES-19");
assert.equal(result.latest.ended, true);
assert.equal(result.latest.peakUtc, "10-23 11:00 UTC");
assert.equal(result.count24h, 3);
assert.equal(result.cPlus24h, 2);
assert.equal(flares.parseFlares([], now).latest, null);
assert.equal(flares.parseFlares([], now).count24h, 0);
assert.throws(() => flares.parseFlares({}, now));
assert.throws(() => flares.parseFlares([], NaN));


// NOAA GOES primary XRS 1-minute readings. The sample's class equivalent
// is a descriptive flux level, not a flare detection or NOAA alert.
const xraySource = fs.readFileSync(
    path.join(root, "services/weather/XrayFluxPolicy.js"), "utf8"
).replace(/^\.pragma library\s*/m, "");
const xray = {};
vm.runInNewContext(xraySource, xray);
assert.equal(typeof xray.parseXraySeries, "function");
assert.equal(xray.fluxClass(1e-4).label, "X1.0");
assert.equal(xray.fluxClass(5e-5).label, "M5.0");
assert.equal(xray.fluxClass(1e-6).label, "C1.0");
assert.equal(xray.fluxClass(2e-7).label, "B2.0");
assert.equal(xray.fluxClass(1e-8).label, "A1.0");
assert.equal(xray.fluxClass(null).label, "--");
assert.equal(xray.logMeter(1e-9), 0);
assert.equal(xray.logMeter(1e-4), 1);
assert.equal(xray.utcTime(0), "-- UTC");

const sampleNow = Date.parse("2026-10-23T12:00:00Z");
const sample = (time, energy, flux, satellite = 19) => ({
    time_tag: time, energy, flux, satellite
});
const xrayPayload = [
    sample("2026-10-23T06:10:00Z", "0.1-0.8nm", 2e-7),
    sample("2026-10-23T07:10:00Z", "0.1-0.8nm", 5e-7),
    sample("2026-10-23T08:10:00Z", "0.1-0.8nm", 2e-6),
    sample("2026-10-23T09:10:00Z", "0.1-0.8nm", 5e-6),
    sample("2026-10-23T10:10:00Z", "0.1-0.8nm", 9e-6),
    sample("2026-10-23T11:59:00Z", "0.1-0.8nm", 2e-5),
    sample("2026-10-23T11:59:00Z", "0.05-0.4nm", 1.5e-6),
    sample("2026-10-23T11:59:00Z", "0.05-0.4nm", 7e-6, 18),
    sample("2026-10-23T12:12:00Z", "0.1-0.8nm", 2e-4), // Future
    sample("2026-10-23T11:58:00Z", "0.1-0.8nm", null), // Missing
    sample("2026-10-23T11:58:00Z", "other", 1e-4), // Wrong band
    sample("2026-10-23T01:59:00Z", "0.1-0.8nm", 1e-4), // Outside window
];
const xrayResult = xray.parseXraySeries(xrayPayload, sampleNow);
assert.equal(xrayResult.fluxLong, 2e-5);
assert.equal(xrayResult.fluxShort, 1.5e-6);
assert.equal(xrayResult.satellite, "GOES-19");
assert.equal(xrayResult.classEquivalent.label, "M2.0");
assert.equal(xrayResult.sampleUtc, "11:59 UTC");
assert.equal(xrayResult.trend.length, 6);
assert.equal(xrayResult.trend[xrayResult.trend.length - 1].flux, 2e-5);
assert.ok(xrayResult.trend.every(entry => entry.level >= 0 && entry.level <= 1));
assert.equal(xray.parseXraySeries([
    sample("2026-10-23T11:59:00Z", "0.1-0.8nm", 1e-6),
    sample("2026-10-23T11:59:00Z", "0.05-0.4nm", 2e-7, 18)
], sampleNow).fluxShort, -1);
assert.throws(() => xray.parseXraySeries({}, sampleNow));
assert.throws(() => xray.parseXraySeries([], sampleNow));
assert.throws(() => xray.parseXraySeries(xrayPayload, NaN));


// NOAA official alert products are recent issued BULLETINS, not inferred
// active warnings. Verify class, cancellations, extension and time limits.
const swpcSource = fs.readFileSync(
    path.join(root, "services/weather/SwpcAlertPolicy.js"), "utf8"
).replace(/^\.pragma library\s*/m, "");
const swpc = {};
vm.runInNewContext(swpcSource, swpc);
assert.equal(typeof swpc.parseBulletins, "function");
assert.equal(typeof swpc.classify, "function");
const bulletinNow = Date.parse("2026-10-23T12:00:00Z");
const bulletin = (id, when, body) => ({
    product_id: id, issue_datetime: when,
    message: "Space Weather Message Code: " + id + "\r\n"
             + "Issue Time: 2026 Oct 23 0000 UTC\r\n\r\n" + body
});
const swpcFeed = [
    bulletin("WATA20", "2026-10-23 10:20:00.000",
             "CANCEL WATCH: Geomagnetic Storm Category G1 Predicted"),
    bulletin("K04W", "2026-10-23 11:30:00.000",
             "EXTENDED WARNING: Geomagnetic K-index of 4 expected\r\nNow Valid Until: 2026 Oct 24 0000 UTC"),
    bulletin("K05A", "2026-10-23 11:50:00.000",
             "ALERT: Geomagnetic K-index of 5\r\nNOAA Scale: G1 - Minor"),
    bulletin("SUM10R", "2026-10-23 09:30:00.000",
             "SUMMARY: 10cm Radio Burst"),
    bulletin("A20F", "2026-10-22 11:00:00.000",
             "WATCH: Geomagnetic Storm Category G2 Predicted"),
    bulletin("K05A", "2026-10-23 11:50:00.000",
             "ALERT: Geomagnetic K-index of 5\r\nNOAA Scale: G1 - Minor"), // duplicate
    bulletin("OUTDATED", "2026-10-20 09:00:00.000",
             "WARNING: Too old"),
    bulletin("FUTURE", "2026-10-24 09:00:00.000",
             "WATCH: Invalid future"),
    bulletin("INVALID", "2026-10-23 11:45:00.000",
             "Unclassified prose"),
];
const bulletinResult = swpc.parseBulletins(swpcFeed, bulletinNow, 48, 3);
assert.equal(bulletinResult.count, 5);
assert.equal(bulletinResult.bulletins.length, 3);
assert.deepEqual(Array.from(bulletinResult.bulletins, b => b.kind),
                 ["ALERT", "WARNING", "CANCELLATION"]);
assert.equal(bulletinResult.bulletins[0].scale, "G1");
assert.equal(bulletinResult.bulletins[0].issueUtc, "10-23 11:50 UTC");
assert.equal(bulletinResult.bulletins[0].code, "K05A");
assert.match(bulletinResult.bulletins[1].subject, /K-index of 4 expected/);
assert.equal(bulletinResult.bulletins[2].originalType, "CANCEL WATCH");
assert.equal(swpc.parseBulletins([], bulletinNow, 48, 3).count, 0);
assert.equal(swpc.classify("NOAA Scale: G3"), null);
assert.equal(swpc.issuedTime("2026-10-23 11:50:00.000"), bulletinNow - 600000);
assert.equal(swpc.issuedTime("bad"), -1);
assert.equal(swpc.utcLabel(0), "-- UTC");
assert.throws(() => swpc.parseBulletins({}, bulletinNow, 48, 3));
assert.throws(() => swpc.parseBulletins([], NaN, 48, 3));


// NOAA notifications timeline: ordinary warnings have Valid From/Valid To,
// extensions have Issue Time/Now Valid Until. Watches forecast calendar days;
// neither source age nor issue time alone establishes "active".
const swpcValiditySource = fs.readFileSync(
    path.join(root, "services/weather/SwpcValidityPolicy.js"), "utf8"
).replace(/^\.pragma library\s*/m, "");
const swpcValidity = {};
vm.runInNewContext(swpcValiditySource, swpcValidity);
assert.equal(typeof swpcValidity.assess, "function");
assert.equal(swpcValidity.noaaTime("2026 Oct 23 1400 UTC"),
             Date.parse("2026-10-23T14:00:00Z"));
assert.equal(swpcValidity.noaaTime("2026 Feb 30 1000 UTC"), -1);
assert.equal(swpcValidity.noaaTime("2026 Oct 23 2460 UTC"), -1);
assert.equal(swpcValidity.noaaTime("2026 Oct 23 14:00 UTC"), -1);

const validityNow = Date.parse("2026-10-23T12:00:00Z");
const issued = (id, timestamp, heading, extra) => ({
    product_id: id,
    issue_datetime: timestamp,
    message: "Space Weather Message Code: " + id + "\r\n" +
             "Serial Number: 123\r\n\r\n" + heading +
             (extra ? "\r\n" + extra : "")
});
const validityFeed = [
    issued("K04W", "2026-10-22 18:00:00.000",
           "WARNING: Geomagnetic K-index of 4 expected",
           "Valid From: 2026 Oct 22 1800 UTC\r\nValid To: 2026 Oct 23 1400 UTC"),
    issued("K04W", "2026-10-23 09:00:00.000",
           "EXTENDED WARNING: Geomagnetic K-index of 4 expected",
           "Valid From: 2026 Oct 22 1800 UTC\r\nNow Valid Until: 2026 Oct 23 1500 UTC"),
    issued("K05W", "2026-10-23 07:00:00.000",
           "WARNING: Geomagnetic K-index of 5 expected",
           "Valid From: 2026 Oct 23 0700 UTC\r\nValid To: 2026 Oct 23 1600 UTC"),
    issued("K05W", "2026-10-23 11:00:00.000",
           "CANCEL WARNING: Geomagnetic K-index of 5 expected"),
    issued("K06W", "2026-10-22 04:00:00.000",
           "WARNING: Geomagnetic K-index of 6 expected",
           "Valid From: 2026 Oct 22 0500 UTC\r\nValid To: 2026 Oct 22 1000 UTC"),
    issued("K07W", "2026-10-23 08:00:00.000",
           "WARNING: Sudden Impulse expected"), // unknown validity
    issued("A20F", "2026-10-22 07:00:00.000",
           "WATCH: Geomagnetic Storm Category G2 Predicted"),
    issued("A20F", "2026-10-23 08:00:00.000",
           "WATCH: Geomagnetic Storm Category G1 Predicted",
           "THIS SUPERSEDES ANY/ALL PRIOR WATCHES IN EFFECT"),
    issued("K05A", "2026-10-23 10:00:00.000",
           "ALERT: Geomagnetic K-index of 5\r\nActive Warning: YES"),
    issued("SUM10R", "2026-10-23 10:00:00.000",
           "SUMMARY: 10cm Radio Burst"),
    issued("OLD", "2026-10-09 10:00:00.000",
           "WARNING: out of lookback",
           "Valid From: 2026 Oct 09 1000 UTC\r\nValid To: 2026 Oct 25 1200 UTC"),
];
const assessed = swpcValidity.assess(validityFeed, validityNow, 168, 3);
assert.equal(assessed.windowCount, 1);
assert.equal(assessed.windows.length, 1);
assert.equal(assessed.windows[0].productId, "K04W");
assert.equal(assessed.windows[0].state, "WINDOW OPEN");
assert.equal(assessed.windows[0].untilUtc, "10-23 15:00 UTC");
assert.equal(assessed.uncertainCount, 2);
assert.equal(assessed.endedCount, 1);
assert.ok(assessed.supersededCount >= 3);
assert.equal(swpcValidity.assess(validityFeed,
    Date.parse("2026-10-23T16:00:00Z"), 168, 3).windowCount, 0);
assert.equal(swpcValidity.assess([], validityNow, 168, 3).windowCount, 0);
assert.throws(() => swpcValidity.assess(null, validityNow, 168, 3));
assert.throws(() => swpcValidity.assess([], NaN, 168, 3));


// SWPC geomagnetic watch products forecast UTC calendar days. Explicit
// cancellations and any/all supersession must prevent stale watch cards.
const watchSource = fs.readFileSync(
    path.join(root, "services/weather/SwpcWatchPolicy.js"), "utf8"
).replace(/^\.pragma library\s*/m, "");
const watches = {};
vm.runInNewContext(watchSource, watches);
assert.equal(typeof watches.assessWatchDays, "function");
assert.equal(typeof watches.predictedDays, "function");
const watchMsg = (id, issue, serial, heading, days, supersede) => ({
    product_id: id,
    issue_datetime: issue,
    message: "Space Weather Message Code: WAT" + id + "\r\n"
        + "Serial Number: " + serial + "\r\n"
        + "Issue Time: 2026 Oct 23 0000 UTC\r\n\r\n"
        + heading + "\r\n"
        + (days ? "Highest Storm Level Predicted by Day:\r\n" + days + "\r\n" : "")
        + (supersede ? "THIS SUPERSEDES ANY/ALL PRIOR WATCHES IN EFFECT\r\n" : "")
});
const watchNow = Date.parse("2026-10-23T13:00:00Z");
const watchArchive = [
    watchMsg("A30F", "2026-10-22 18:00:00.000", "91",
        "WATCH: Geomagnetic Storm Category G2 Predicted",
        "Oct 23: G2 (Moderate) Oct 24: G2 (Moderate) Oct 25: None (Below G1)",
        true),
    watchMsg("A20F", "2026-10-23 10:00:00.000", "92",
        "WATCH: Geomagnetic Storm Category G1 Predicted",
        "Oct 23: None (Below G1)   Oct 24: G1 (Minor)   Oct 25: G1 (Minor)",
        true)
];
const watchState = watches.assessWatchDays(watchArchive, watchNow, 168, 3);
assert.equal(watchState.forecastDayCount, 3);
assert.equal(watchState.projectedDays, 2);
assert.deepEqual(Array.from(watchState.days, d => d.level), [0, 1, 1]);
assert.deepEqual(Array.from(watchState.days, d => d.dateUtc),
                 ["10-23 UTC", "10-24 UTC", "10-25 UTC"]);
assert.equal(watchState.days[0].levelLabel, "BELOW G1");
assert.equal(watchState.supersededCount, 1);

const cancelWatch = watchMsg("A30F", "2026-10-23 11:00:00.000", "93",
    "CANCEL WATCH: Geomagnetic Storm Category G2 Predicted",
    "Oct 23: None (Below G1)", false);
const cancelled = watches.assessWatchDays([
    watchArchive[0], cancelWatch
], watchNow, 168, 3);
assert.equal(cancelled.forecastDayCount, 0);
assert.equal(cancelled.canceledCount, 1);

const unaffected = watches.assessWatchDays([
    watchMsg("A20F", "2026-10-23 07:00:00.000", "94",
        "WATCH: Geomagnetic Storm Category G1 Predicted",
        "Oct 23: G1 (Minor) Oct 24: None (Below G1)", false),
    watchMsg("A30F", "2026-10-23 08:00:00.000", "95",
        "WATCH: Geomagnetic Storm Category G2 Predicted",
        "Oct 23: G2 (Moderate) Oct 24: None (Below G1)", false),
    cancelWatch
], watchNow, 168, 3);
assert.equal(unaffected.forecastDayCount, 2);
assert.equal(unaffected.days[0].level, 1);
assert.equal(unaffected.days[1].level, 0);

const crossover = watches.assessWatchDays([
    watchMsg("A40F", "2026-12-31 22:00:00.000", "96",
        "WATCH: Geomagnetic Storm Category G4 Predicted",
        "Jan 01: G4 (Severe)\nJan 02: G2 (Moderate)\nJan 03: None (Below G1)",
        true)
], Date.parse("2027-01-01T03:00:00Z"), 168, 3);
assert.equal(crossover.forecastDayCount, 3);
assert.deepEqual(Array.from(crossover.days, d => d.dateUtc),
                 ["01-01 UTC", "01-02 UTC", "01-03 UTC"]);
assert.equal(crossover.days[0].levelLabel, "G4");

const malformedNew = watches.assessWatchDays([
    watchArchive[0],
    watchMsg("A20F", "2026-10-23 11:00:00.000", "97",
             "WATCH: Geomagnetic Storm Category G1 Predicted",
             "Oct 32: G1 (Minor)", true)
], watchNow, 168, 3);
assert.equal(malformedNew.forecastDayCount, 0);
assert.equal(malformedNew.unresolvedCount, 1);
assert.throws(() => watches.assessWatchDays(null, watchNow, 168, 3));
assert.throws(() => watches.assessWatchDays([], NaN, 168, 3));
assert.equal(watches.predictedDays("NOAA bulletin", watchNow).length, 0);



// Source racks: MAP/NASA EONET, NEWS/GDELT and RADIO/Radio Browser.
const discoverySource = fs.readFileSync(
    path.join(root, "services/weather/StationDiscoveryPolicy.js"), "utf8"
).replace(/^\.pragma library\s*/m, "");
const discovery = {};
vm.runInNewContext(discoverySource, discovery);
assert.equal(typeof discovery.parse, "function");
assert.equal(discovery.safeUrl("javascript:alert(1)"), "");
assert.equal(discovery.safeUrl("https://example.org/item"), "https://example.org/item");

const mapped = discovery.parse("map", {
    events: [{
        id: "EONET-1",
        title: "Tropical Storm Sample",
        link: "https://eonet.gsfc.nasa.gov/api/v3/events/EONET-1",
        categories: [{id:"severeStorms", title:"Severe Storms"}],
        geometry: [{
            date: "2026-10-23T12:00:00Z",
            type: "Point", coordinates: [-70.2, 20.4]
        }]
    }]
});
assert.equal(mapped.length, 1);
assert.equal(mapped[0].title, "Tropical Storm Sample");
assert.match(mapped[0].detail, /20\.40, -70\.20/);
assert.equal(mapped[0].action, "OPEN NASA EVENT");
assert.throws(() => discovery.parse("map", {}));

const headlines = discovery.parse("news", {
    articles: [
        {title:"Weather report", url:"https://news.test/article",
         domain:"example.com", sourcecountry:"United States",
         seendate:"20261023T113000Z"},
        {title:"Duplicate", url:"https://news.test/article"},
        {title:"Unsafe", url:"javascript:alert(1)"}
    ]
});
assert.equal(headlines.length, 1);
assert.equal(headlines[0].time, "10-23 11:30 UTC");
assert.equal(headlines[0].action, "READ ARTICLE");
assert.throws(() => discovery.parse("news", null));

const streams = discovery.parse("radio", [
    {stationuuid:"one", name:"Public Radio", url_resolved:"https://radio.test/live",
     country:"US", codec:"MP3", bitrate:128, lastcheckok:1, language:"English"},
    {stationuuid:"one", name:"Duplicate", url_resolved:"https://radio.test/a",
     lastcheckok:1},
    {stationuuid:"two", name:"Down", url_resolved:"https://radio.test/b",
     lastcheckok:0},
    {stationuuid:"three", name:"Invalid", url_resolved:"file:///tmp/a",
     lastcheckok:1}
]);
assert.equal(streams.length, 1);
assert.equal(streams[0].action, "OPEN STREAM URL");
assert.match(streams[0].detail, /MP3 128kbps/);
assert.throws(() => discovery.parse("radio", {}));
assert.throws(() => discovery.parse("unknown", []));


// Sway is the compositor position authority: panel anchored top/right with a
// 20px margin, header/rail offsets, and a QML-local terminal bay. Qt's
// Wayland mapToGlobal is intentionally not used to move Kitty.
const terminalGeometrySource = fs.readFileSync(
    path.join(root, "widgets/weather/StationTerminalGeometry.js"), "utf8"
).replace(/^\.pragma library\s*/m, "");
const terminalGeometry = {};
vm.runInNewContext(terminalGeometrySource, terminalGeometry);
const terminalOutputs = [
    {name: "DP-5", active: true,
     rect: {x: 0, y: 0, width: 2560, height: 1440}},
    {name: "HDMI-A-1", active: true,
     rect: {x: -1360, y: 200, width: 1360, height: 768}},
    {name: "OFF", active: false,
     rect: {x: 5000, y: 0, width: 1000, height: 800}},
];
function stationBay(output) {
    return terminalGeometry.position(
        terminalOutputs, output, 1000, 20, 62, 160, 30, 70, 780, 416
    );
}
assert.deepEqual(JSON.parse(JSON.stringify(stationBay("DP-5"))),
                 {x: 1730, y: 132, width: 780, height: 416});
assert.deepEqual(JSON.parse(JSON.stringify(stationBay("HDMI-A-1"))),
                 {x: -830, y: 332, width: 780, height: 416});
assert.equal(stationBay("OFF"), null);
assert.equal(stationBay("WRONG-OUTPUT"), null);
assert.equal(terminalGeometry.position([], "DP-5",
    1000, 20, 62, 160, 30, 70, 780, 416), null);
assert.equal(terminalGeometry.position(terminalOutputs, "DP-5",
    3000, 20, 62, 160, 30, 70, 780, 416), null);
assert.equal(terminalGeometry.position(terminalOutputs, "DP-5",
    1000, 20, 62, 160, 30, 70, 1200, 416), null);
assert.equal(terminalGeometry.position(terminalOutputs, "DP-5",
    1000, 20, 62, 160, 30, 70, 780, Infinity), null);


// Expected enlarged terminal bay inside the top/right anchored Station,
// including a compositor output with a negative global origin.
function expandedBay(output) {
    return terminalGeometry.position(
        terminalOutputs, output, 1000, 20, 62, 160, 14, 90, 812, 468
    );
}
assert.deepEqual(JSON.parse(JSON.stringify(expandedBay("DP-5"))),
                 {x: 1714, y: 152, width: 812, height: 468});
assert.deepEqual(JSON.parse(JSON.stringify(expandedBay("HDMI-A-1"))),
                 {x: -846, y: 352, width: 812, height: 468});

console.log("Weather data policy contracts: PASS");
