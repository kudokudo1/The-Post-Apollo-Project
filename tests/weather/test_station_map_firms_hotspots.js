#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = rel => fs.readFileSync(path.join(root, rel), "utf8");

function load(relative) {
    const source = read(relative).replace(/^\.pragma library\s*/m, "");
    const context = {Date, Number, String, Array, JSON, Object, Math, isFinite};
    vm.runInNewContext(source, context, {filename: relative});
    return context;
}

const projection = load("widgets/weather/StationMapProjectionPolicy.js");
const firms = load("services/weather/FirmsHotspotPolicy.js");

assert.equal(typeof projection.visibleBounds, "function");
let bounds = projection.visibleBounds(900, 450, 1, 0, 0);
assert.equal(bounds.valid, true);
assert.equal(bounds.west, -180);
assert.equal(bounds.east, 180);
assert.equal(bounds.south, -90);
assert.equal(bounds.north, 90);
assert.equal(bounds.longitudeSpan, 360);
assert.equal(bounds.latitudeSpan, 180);

bounds = projection.visibleBounds(900, 450, 6, -77, 38);
assert.equal(bounds.valid, true);
assert.ok(Math.abs(bounds.longitudeSpan - 60) < 1e-9);
assert.ok(Math.abs(bounds.latitudeSpan - 30) < 1e-9);

assert.equal(firms.configuredKey(""), "");
assert.equal(firms.configuredKey("short"), "");
assert.equal(firms.configuredKey("abcDEF_12345678"), "abcDEF_12345678");
assert.equal(firms.configuredKey("bad/key/value"), "");

let area = firms.boundedArea(bounds, 60, 40);
assert.equal(area.valid, true);
assert.match(area.bbox, /^-?\d+\.\d{4},-?\d+\.\d{4},-?\d+\.\d{4},-?\d+\.\d{4}$/);

area = firms.boundedArea(
    projection.visibleBounds(900, 450, 5, 0, 0), 60, 40
);
assert.equal(area.valid, false);
assert.equal(area.reason, "ZOOM IN // VIEW TOO WIDE");

const csv = [
    "latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_ti5,frp,daynight",
    '38.5000,-77.2500,331.2,0.4,0.5,2026-10-27,42,N21,VIIRS,h,2.0NRT,294.1,12.4,D',
    '38.5000,-77.2500,331.2,0.4,0.5,2026-10-27,0042,N21,VIIRS,h,2.0NRT,294.1,12.4,D',
    '39.1250,-76.5000,305.0,0.4,0.5,2026-10-27,2315,N21,VIIRS,n,2.0NRT,289.0,4.5,N',
    'bad,-76.0,300,0.4,0.5,2026-10-27,2315,N21,VIIRS,l,2.0NRT,285,1.0,N'
].join("\n");

const rows = Array.from(firms.parseViirsCsv(csv, 800));
assert.equal(rows.length, 2, "duplicate + malformed rows are filtered");
assert.equal(rows[0].coordinates, "38.5000, -77.2500");
assert.equal(rows[0].acquiredUtc, "2026-10-27 00:42Z");
assert.equal(rows[0].confidenceCode, "h");
assert.equal(rows[0].confidenceLabel, "HIGH");
assert.equal(rows[0].brightnessK, 331.2);
assert.equal(rows[0].frpMw, 12.4);
assert.equal(rows[0].satellite, "N21");
assert.equal(rows[0].instrument, "VIIRS");
assert.equal(rows[0].dayNight, "D");
assert.equal(rows[1].confidenceLabel, "NOMINAL");
assert.equal(rows[1].acquiredUtc, "2026-10-27 23:15Z");
assert.throws(() => firms.parseViirsCsv("latitude,longitude\n1,2", 800));

const service = read("services/weather/FirmsHotspotService.qml");
assert.match(service, /POST_APOLLO_FIRMS_MAP_KEY/);
assert.match(service, /FirmsPolicy\.boundedArea\(bounds, 60, 40\)/);
assert.match(service, /lastRequestMs > 0 && now - lastRequestMs < 30000/);
assert.match(service, /FIRMS REQUEST COOLDOWN/);
assert.match(service, /VIIRS_NOAA21_NRT/);
assert.match(service, /scripts\/weather\/firms_area_fetch\.py/);
assert.match(service, /FirmsPolicy\.parseViirsCsv\(raw, 800\)/);
assert.equal((service.match(/\bProcess\s*\{/g) || []).length, 1);
assert.equal((service.match(/\bTimer\s*\{/g) || []).length, 0);
const commandStart = service.indexOf("fetchProcess.command = [");
const commandEnd = service.indexOf("];", commandStart);
const command = service.slice(commandStart, commandEnd);
assert.doesNotMatch(command, /mapKey|POST_APOLLO_FIRMS_MAP_KEY|firms\.modaps/);

const ui = read("widgets/weather/StationDiscovery.qml");
assert.match(ui, /WeatherServices\.FirmsHotspotService\s*\{/);
assert.match(ui, /FirmsAreaPolicy\.boundedArea\(mapVisibleBounds, 60, 40\)/);
assert.match(ui, /label: "FETCH HOTSPOTS"/);
assert.match(ui, /available: firmsService\.configured[\s\S]*?firmsAreaReady[\s\S]*?!firmsService\.loading/);
assert.match(ui, /ONE DAY \/\/ MAX 60° × 40° VIEW \/\/ NO AUTO-FETCH/);
assert.match(ui, /KEY NEVER SHOWN OR PASSED IN PROCESS ARGV/);
assert.match(ui, /model: firmsService\.ready \? firmsService\.hotspots : \[\]/);
assert.match(ui, /title: "HOTSPOT INSPECTOR \/\/ NASA FIRMS"/);
assert.match(ui, /SATELLITE HOTSPOT, NOT FIRE PERIMETER/);
assert.match(ui, /selectedMapHotspot = modelData/);
assert.match(ui, /SPATIAL PLOT \/\/ EONET \+ FIRMS \+ NEWS MENTIONS/);
assert.match(ui, /NASA FIRMS \/\/ VIIRS NOAA-21 HOTSPOTS/);
assert.doesNotMatch(ui, /firmsService\.mapKey/);

console.log("Weather MAP manual bounded FIRMS hotspot overlay: PASS");
