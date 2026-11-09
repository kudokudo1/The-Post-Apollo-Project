// ANGEL M1 pure journal schema/pattern validation. No disk/clock mutations.
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const source = fs.readFileSync(
    path.join(root, "services/time/AngelObservationPolicy.js"), "utf8"
).replace(/^\.pragma library\s*$/m, "");
const policy = {};
vm.runInNewContext(source, policy, {filename: "AngelObservationPolicy.js"});
const copy = (value) => JSON.parse(JSON.stringify(value));
const context = (mode = "manual", displayTime = "2:22 PM") => ({
    captureMode: mode,
    displayTime,
    zoneId: "America/New_York",
    utcOffsetMinutes: -300,
    displayCalibrationMs: 0
});

assert.equal(policy.VERSION, 1);
assert.equal(policy.MAX_ROWS, 4096);
assert.equal(policy.MAX_DIGITS, 8);
assert.deepEqual(copy(policy.emptyDocument()), {
    version: 1, nextId: 1, observations: []
});
assert.equal(policy.clockCapture(new Date(2026, 10, 4, 14, 22).getTime())
    .digits, "222");
assert.equal(policy.clockCapture(new Date(2026, 10, 4, 14, 22).getTime())
    .displayTime, "2:22 PM");
assert.equal(policy.clockCapture(new Date(2026, 10, 4, 10, 1).getTime())
    .digits, "1001");
for (const value of ["222", "101", "347", "0202", "001", "0", "12345678"])
    assert.equal(policy.validDigits(value), true, value);
for (const value of ["", "123456789", "12:34", "-222", "12+3",
                     " 222", "222\n", "NaN", "2.22"])
    assert.equal(policy.validDigits(value), false, value);

let doc = copy(policy.emptyDocument());
let next = policy.create(doc, "222", context("clock"), 1793802120000);
assert.equal(next.ok, true);
assert.equal(next.document.observations[0].id, "a1");
assert.equal(next.document.observations[0].captureMode, "clock");
assert.equal(next.document.observations[0].observedAtMs, 1793802120000);
assert.deepEqual(copy(doc.observations), [],
    "draft creation must not mutate confirmed document");
doc = copy(next.document);
next = policy.create(doc, "222", context(), 1793802120001);
assert.equal(next.ok, true, "multiple sightings of same sequence are distinct");
assert.equal(next.document.observations[1].id, "a2");
doc = copy(next.document);
next = policy.create(doc, "347", context("manual", "3:47 PM"), 1793802120002);
assert.equal(next.ok, true);
doc = copy(next.document);
assert.equal(doc.observations.length, 3);
assert.equal(doc.nextId, 4);
assert.deepEqual(copy(policy.parse(JSON.stringify(doc)).document), doc);
assert.equal(policy.remove(doc, "a2", false).reason, "CONFIRM_REQUIRED");
assert.equal(policy.remove(doc, "a999", true).reason, "UNKNOWN_ID");
const removed = policy.remove(doc, "a2", true);
assert.equal(removed.ok, true);
assert.deepEqual(copy(removed.document.observations.map(x => x.id)),
    ["a1", "a3"]);
assert.equal(removed.document.nextId, 4);
assert.equal(doc.observations.length, 3, "removal is staged, not in-place");

for (const [digits, kind] of [
    ["222", "repeat"], ["101", "mirror"], ["202", "mirror"],
    ["123", "sequence"], ["321", "sequence"],
    ["347", "add"], ["321", "subtract"], ["101", "subtract"],
    ["12", "other"], ["0202", "other"]
]) {
    assert.equal(policy.matchesFilter(digits, kind), true,
                 digits + " must match " + kind);
}
assert.equal(policy.matchesFilter("222", "mirror"), false,
    "repeated digits should not drown out distinct mirror patterns");
assert.deepEqual(copy(policy.patternTags("347")), ["ADD"]);
assert.deepEqual(copy(policy.patternTags("321")), ["SEQUENCE", "SUBTRACT"]);
assert.deepEqual(copy(policy.patternTags("101")), ["MIRROR", "ADD", "SUBTRACT"]);

const rows = [
    policy.create(policy.emptyDocument(), "222", context(), 1000)
        .document.observations[0],
    {...policy.create(policy.emptyDocument(), "347", context(), 2000)
        .document.observations[0], id: "a2"},
    {...policy.create(policy.emptyDocument(), "101", context(), 3000)
        .document.observations[0], id: "a3"},
];
assert.deepEqual(copy(policy.filter(rows, "", "all").map(x => x.id)),
    ["a3", "a2", "a1"]);
assert.deepEqual(copy(policy.filter(rows, "22", "all").map(x => x.digits)),
    ["222"]);
assert.deepEqual(copy(policy.filter(rows, "", "add").map(x => x.digits)),
    ["101", "347"]);
assert.deepEqual(copy(policy.filter(rows, "", "mirror").map(x => x.digits)),
    ["101"]);
assert.deepEqual(copy(policy.filter(rows, "A", "all")), []);
assert.deepEqual(copy(policy.filter(rows, "", "unknown-filter")), []);

for (const invalid of [
    "nope", "{}", "[]",
    JSON.stringify({version: 2, nextId: 1, observations: []}),
    JSON.stringify({...doc, nextId: 3}),
    JSON.stringify({...doc, observations: doc.observations.concat(doc.observations[0])}),
    JSON.stringify({...doc, observations: [{...doc.observations[0], digits: "2:22"}]}),
    JSON.stringify({...doc, observations: [{...doc.observations[0], zoneId: "../../"}]}),
    JSON.stringify({...doc, observations: [{...doc.observations[0], displayTime: "BAD"}]})
]) {
    assert.equal(policy.parse(invalid).ok, false, invalid);
}
const full = policy.emptyDocument();
full.nextId = 4097;
for (let i = 1; i <= 4096; i++) {
    full.observations.push({
        id: "a" + i, digits: "222", observedAtMs: 1793802120000 + i,
        displayTime: "2:22 PM", zoneId: "UTC",
        utcOffsetMinutes: 0, displayCalibrationMs: 0,
        captureMode: "clock"
    });
}
assert.equal(policy.validate(full).ok, true);
assert.equal(policy.create(full, "222", context(), 1793803000000).reason, "CAPACITY");

// ERR is a review bucket, not a mutually exclusive claim about numerology.
// It includes structurally unmatched numbers and any selected observation
// explicitly marked by the user, without modifying other sightings.
assert.equal(policy.FILTERS.includes("err"), true);
const errBase = policy.emptyDocument();
const errFirst = policy.create(errBase, "222", context(), 2000);
const errSecond = policy.create(errFirst.document, "222", context(), 3000);
const errOther = policy.create(errSecond.document, "809", context(), 4000);
const errDoc = copy(errOther.document);
assert.equal(policy.matchesFilter("809", "other"), true);
assert.equal(policy.matchesFilter("809", "err"), true);
assert.deepEqual(copy(policy.filter(errDoc.observations, "", "err")
    .map(x => x.digits)), ["809"], "unmatched automatically belongs to ERR");
assert.equal(policy.filter(errDoc.observations, "", "repeat").length, 2);
assert.equal(policy.toggleErr(errDoc, "a999").reason, "UNKNOWN_ID");
const marked = policy.toggleErr(errDoc, "a1");
assert.equal(marked.ok, true);
assert.equal(marked.errMarked, true);
assert.equal(errDoc.observations[0].errMarked, false,
    "marking must never mutate the confirmed document");
assert.equal(marked.document.observations[1].errMarked, false,
    "same number, different occurrence must remain unmarked");
assert.deepEqual(copy(policy.filter(marked.document.observations, "", "err")
    .map(x => x.id)), ["a3", "a1"]);
assert.deepEqual(copy(policy.filter(marked.document.observations, "22", "err")
    .map(x => x.id)), ["a1"]);
assert.equal(policy.filter(marked.document.observations, "", "other").length, 1,
    "OTHER remains purely automatic, not influenced by manually marked ERR");
assert.equal(policy.filter(marked.document.observations, "", "repeat").length, 2,
    "a mark cannot destroy original classifications");
const unmarked = policy.toggleErr(marked.document, "a1");
assert.equal(unmarked.ok, true);
assert.equal(unmarked.errMarked, false);
assert.deepEqual(copy(policy.filter(unmarked.document.observations, "", "err")
    .map(x => x.id)), ["a3"]);
assert.equal(policy.parse(JSON.stringify(marked.document)).ok, true,
    "flag survives JSON roundtrip");
const legacy = copy(errDoc);
for (const row of legacy.observations) delete row.errMarked;
assert.equal(policy.parse(JSON.stringify(legacy)).ok, true,
    "existing v1 journals without errMarked must load unmodified");
assert.deepEqual(copy(policy.parse(JSON.stringify(legacy)).document
    .observations.map(x => x.errMarked)), [false, false, false]);
assert.equal(policy.parse(JSON.stringify({
    ...errDoc, observations: [{
        ...errDoc.observations[0], errMarked: "true"
    }]
})).ok, false, "reject invalid review field type");

// The date already lives in every v1 record's UTC instant and saved offset.
// Render the calendar day observed then, not the reader's current timezone,
// current DST rules or the separate clock-display calibration.
const justAfterMidnightUtc = Date.UTC(2026, 10, 7, 0, 10);
const easternRecord = {
    observedAtMs: justAfterMidnightUtc,
    utcOffsetMinutes: -300,
    displayCalibrationMs: 300000
};
assert.equal(policy.observedDate(easternRecord), "2026-11-06",
    "UTC midnight can still be the previous saved local calendar date");
assert.equal(policy.observedDate({...easternRecord, utcOffsetMinutes: 330}),
    "2026-11-07", "a recorded positive UTC offset moves the day forward");
assert.equal(policy.observedDate({...easternRecord, utcOffsetMinutes: -240}),
    "2026-11-06", "the saved DST offset remains authoritative");
assert.equal(policy.observedDate({...easternRecord, displayCalibrationMs: 0}),
    "2026-11-06", "display-only time calibration never changes the saved day");
assert.equal(policy.observedDate({...easternRecord, utcOffsetMinutes: -999}),
    "DATE UNKNOWN", "bad offset must not manufacture a date");
assert.equal(policy.observedDate({observedAtMs: 9000000000000000,
                                 utcOffsetMinutes: 0}),
    "DATE UNKNOWN", "out-of-range JS Date must fail safely");
assert.equal(policy.observedDate(null), "DATE UNKNOWN");

// Date display introduces no new journal field or second writer.
// Existing observations retain their exact raw instant and UTC offset.
const dated = policy.create(policy.emptyDocument(), "1212",
    context("manual", "12:12 AM"), justAfterMidnightUtc);
assert.equal(dated.ok, true);
assert.equal(policy.observedDate(dated.document.observations[0]),
    "2026-11-06");
const datedRoundTrip = policy.parse(JSON.stringify(dated.document));
assert.equal(datedRoundTrip.ok, true);
assert.deepEqual(copy(datedRoundTrip.document), copy(dated.document));
assert.equal(policy.VERSION, 1);

// Favorite membership is by exact digit string, not observation ID.
const numberFavoriteKey = policy.favoriteKey("222");
assert.equal(numberFavoriteKey, "fav1:local:angel:number:222");
assert.equal(policy.favoriteKey("22:2"), "");
assert.deepEqual(copy(policy.filter(errDoc.observations, "", "favorite",
    [numberFavoriteKey]).map(x => x.id)), ["a2", "a1"]);
assert.deepEqual(copy(policy.filter(errDoc.observations, "", "favorite",
    []).map(x => x.id)), []);
assert.equal(policy.FILTERS.includes("favorite"), true);

// Multiplication and division are structural, integer triplet patterns.
assert.equal(policy.matchesFilter("224", "multiply"), true);
assert.equal(policy.matchesFilter("842", "divide"), true);
assert.equal(policy.matchesFilter("804", "divide"), false, "division by zero");
assert.equal(policy.matchesFilter("825", "divide"), false);
assert.equal(policy.matchesFilter("224", "divide"), false);
assert.equal(policy.matchesFilter("224", "add"), true, "filters can overlap");
assert.deepEqual(copy(policy.patternTags("224")), ["ADD", "MULTIPLY"]);
assert.equal(policy.FILTERS.includes("multiply"), true);
assert.equal(policy.FILTERS.includes("divide"), true);

// Notes are per sighting, bounded, opt-in, and backwards-compatible with v1.
const noted = policy.setNote(errDoc, "a1", "First sighting");
assert.equal(noted.ok, true);
assert.equal(noted.document.observations[0].note, "First sighting");
assert.equal(noted.document.observations[1].note, undefined);
assert.equal(errDoc.observations[0].note, undefined, "stage does not mutate");
assert.equal(policy.parse(JSON.stringify(noted.document)).ok, true);
assert.equal(policy.setNote(errDoc, "a999", "note").reason, "UNKNOWN_ID");
assert.equal(policy.setNote(errDoc, "a1", "x".repeat(281)).reason,
    "INVALID_NOTE");
const clearedNote = policy.setNote(noted.document, "a1", "");
assert.equal(clearedNote.ok, true);
assert.equal(clearedNote.document.observations[0].note, undefined);
assert.equal(policy.parse(JSON.stringify(errDoc)).ok, true,
    "pre-note journal remains loadable");

console.log("ANGEL_OBSERVATION_POLICY_PASS");
