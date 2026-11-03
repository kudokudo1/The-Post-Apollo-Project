"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = p => fs.readFileSync(path.join(root, p), "utf8");
const policy = read("widgets/weather/StationCosmosPlanetEventPolicy.js");
const qml = read("widgets/weather/StationCosmosPlanetEventClock.qml");
const sky = read("widgets/weather/StationSky.qml");
const service = read("services/weather/UsnoPlanetRiseSetService.qml");
const parser = read("scripts/weather/usno_planet_rise_set.py");
const routes = read("widgets/weather/StationCosmosSubjectPanelPolicy.js");
const context = vm.createContext({});
vm.runInContext(policy.replace(/^\.pragma library\s*$/m, ""), context);
const p = context;

function row(name, date = "2026-11-03") {
    return {
        name, date, status: "NORMAL",
        rise: "21:43", riseAzimuth: 103, riseLabel: "9:43 PM",
        transit: "02:12", transitAltitude: 46,
        transitHemisphere: "S", transitLabel: "2:12 AM",
        set: "09:17", setAzimuth: 258, setLabel: "9:17 AM"
    };
}
const plain = value => JSON.parse(JSON.stringify(value));

test("V2b only uses exact minute HH:MM local events", () => {
    assert.equal(p.FORMAT, "post-apollo.weather.cosmos-planet-clock.v2b.v1");
    assert.equal(p.minuteOf("00:00"), 0);
    assert.equal(p.minuteOf("23:59"), 1439);
    assert.equal(p.minuteOf("02:12"), 132);
    for (const bad of ["24:00", "12:60", "1:05", "12:5", "", null, 1300])
        assert.equal(p.minuteOf(bad), null, String(bad));
    assert.equal(p.validDate("2026-11-03"), true);
    assert.equal(p.validDate("2026-02-30"), false);
    assert.equal(p.validDate("2026-11-3"), false);
    assert.equal(p.timeX(0, 1440), 0);
    assert.equal(p.timeX(720, 1440), 720);
    assert.equal(p.timeX(1439, 1440), 1439);
    assert.equal(p.timeX(-1, 1440), null);
    assert.equal(p.timeX(1440, 1440), null);
});

test("Five source-keyed rows do not manufacture missing planet events", () => {
    const result = plain(p.clockRows([row("MERCURY"), row("SATURN")], "2026-11-03"));
    assert.deepEqual(result.map(r => r.name), [
        "MERCURY", "VENUS", "MARS", "JUPITER", "SATURN"
    ]);
    assert.deepEqual(result.map(r => r.events.length), [3, 0, 0, 0, 3]);
    assert.equal(p.rowCountWithEvents(result), 2);
    assert.equal(result[1].status, "NO DATED RESPONSE");
    assert.equal(result[0].events[0].clock, "21:43");
    assert.equal(result[0].events[1].clock, "02:12");
    assert.equal(result[0].events[2].clock, "09:17");
    assert.equal(result[0].events[1].altitude, 46);
    assert.equal(result[0].events[1].hemisphere, "S");
    assert.equal(result[0].events[0].azimuth, 103);
    assert.equal(result[0].events[2].azimuth, 258);
    // Events are *not* joined into fake tracks or chronological daily cycles.
    assert.ok(result[0].events[0].minute > result[0].events[1].minute);
    assert.equal(p.eventsFor(result[0], "rise").length, 1);
    assert.equal(p.eventsFor(result[0], "ALL").length, 3);
    assert.equal(p.eventsFor(result[0], "set")[0].kind, "set");
});

test("Wrong-day, malformed, absent and special-status input fail closed", () => {
    const wrongDate = p.clockRows([row("VENUS", "2026-11-04")], "2026-11-03");
    assert.equal(wrongDate[1].available, false);
    const noDate = p.clockRows([row("VENUS")], "not-a-date");
    assert.equal(p.rowCountWithEvents(noDate), 0);
    const above = row("MARS");
    above.status = "CONTINUOUSLY ABOVE HORIZON";
    const below = row("JUPITER");
    below.status = "CONTINUOUSLY BELOW HORIZON";
    const partial = row("SATURN");
    partial.set = "--";
    const unknown = row("VENUS");
    unknown.status = "PARTIAL / UNPARSED";
    const rows = p.clockRows([above, below, partial, unknown], "2026-11-03");
    assert.equal(rows[2].status, "CONTINUOUSLY ABOVE HORIZON");
    assert.equal(rows[2].events.length, 0);
    assert.equal(rows[3].status, "CONTINUOUSLY BELOW HORIZON");
    assert.equal(rows[3].events.length, 0);
    assert.equal(rows[4].status, "PARTIAL EVENTS");
    assert.equal(rows[4].events.length, 2);
    assert.equal(rows[1].events.length, 0);
});

test("No invented angle when USNO field is absent or invalid", () => {
    const source = row("VENUS");
    source.riseAzimuth = null;
    source.transitAltitude = "";
    source.setAzimuth = 400;
    const events = p.clockRows([source], "2026-11-03")[1].events;
    assert.equal(events[0].azimuth, null);
    assert.equal(events[1].altitude, null);
    assert.equal(events[2].azimuth, null);
    assert.equal(p.eventDetail(events[0]).includes("AZ"), false);
    assert.equal(p.eventDetail(events[1]).includes("ALT"), false);
    assert.match(p.eventDetail(events[2]), /VENUS \/\/ SET 09:17 LOCAL/);
    assert.match(p.eventDetail(null), /SELECT AN EVENT/);
});

test("QML actions work and no duplicate collector or fake ephemeris exists", () => {
    assert.match(qml, /ActionButton\s*\{/);
    assert.match(qml, /onClicked: clock\.selectedPlanet = modelData/);
    assert.match(qml, /onClicked: clock\.selectedKind = modelData\.id|clock\.selectedKind = modelData\.id/);
    assert.match(qml, /MouseArea\s*\{/);
    assert.match(qml, /preventStealing: true/);
    assert.match(qml, /onClicked: clock\.lockedEvent = eventMarker\.modelData/);
    assert.match(qml, /onClicked: clock\.lockedEvent = null/);
    assert.match(qml, /PlanetPolicy\.clockRows\(/);
    assert.match(qml, /NO MOTION BETWEEN EVENTS/);
    assert.match(qml, /NO ZODIAC OR RETROGRADE INFERENCE/);
    for (const forbidden of [
        "Process {", "Timer {", "FileView {", "XMLHttpRequest",
        "UsnoPlanetRiseSetService {", "new WebSocket", "Qt.callLater",
        "swaymsg", "sunriseBasedAltitude", "zodiacLongitude"
    ]) assert.ok(!qml.includes(forbidden), forbidden);
});

test("COSMOS-only integration reuses original provider and leaves CLASSIC source", () => {
    assert.match(sky, /StationCosmosPlanetEventClock\s*\{/);
    assert.match(sky, /visible: sky\.subjectRoute\.indexOf\("cosmos\/"\) === 0/);
    assert.match(sky, /providerRows: planetRiseSetService\.rows/);
    assert.match(sky, /sourceReady: planetRiseSetService\.ready/);
    assert.match(sky, /civilDate: sky\.astronomySummary\.date/);
    assert.equal((sky.match(/WeatherServices\.UsnoPlanetRiseSetService\s*\{/g) || []).length, 1);
    assert.match(routes, /"cosmos\/planets-stars\/planet-clock".*?"planet-clock"/);
    assert.match(parser, /"source": "USNO MRST"/);
    assert.match(parser, /"precision": "ONE MINUTE"/);
    assert.match(service, /rows = parsed\.planets/);
});
