#!/usr/bin/env node
"use strict";
// Verify the same QML-imported policy with no filesystem or geolocation.
// Remove only the QML .pragma declaration for Node's VM.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

const source = fs.readFileSync(
    path.join(__dirname, "../../services/location/PlacePolicy.js"), "utf8"
).replace(/^\.pragma library\s*/, "");
const policy = vm.runInNewContext(source + `
;({initialDocument, coordinate, place, normalize, parse, withHome,
   withExplore, withoutExplore, activeExplore, effectivePlace, contextKind})
`);

const empty = policy.initialDocument();
assert.equal(empty.home, null);
assert.equal(empty.revision, 0);
assert.equal(empty.schema, "post-apollo.places.v1");

// No implicit geolocation: blank or missing coordinates always fail.
// Zero is an explicitly valid coordinate, never a blank-string default.
for (const value of ["", " ", null, undefined, "NaN", "Infinity",
                     "1e3", "0x10", "91", "-91.1", "23.1234567"]) {
    assert.equal(policy.coordinate(value, 90), null, String(value));
}
assert.equal(policy.coordinate("0", 90), 0);
assert.equal(policy.coordinate("-90", 90), -90);
assert.equal(policy.coordinate("+90", 90), 90);
assert.equal(policy.coordinate("-180", 180), -180);
assert.equal(policy.coordinate("180", 180), 180);
assert.equal(policy.coordinate("181", 180), null);

// Reject absent labels, malicious control characters and bad coordinates.
assert.equal(policy.place("", "38.8", "-76.7").reason, "HOME_LABEL_INVALID");
assert.equal(policy.place("Home\nUnknown", "38.8", "-76.7").reason, "HOME_LABEL_INVALID");
assert.equal(policy.place("Home", "", "-76.7").reason, "LATITUDE_INVALID");
assert.equal(policy.place("Home", "38.8", "").reason, "LONGITUDE_INVALID");
assert.equal(policy.place("Home", "38.8", "-181").reason, "LONGITUDE_INVALID");

// Explicit Save Home generates one safe revision of a versioned document.
const saved = policy.withHome(empty, "  Example City  ", "38.8243", "-76.7451");
assert.equal(saved.ok, true);
assert.equal(saved.document.revision, 1);
assert.equal(saved.document.home.label, "Example City");
assert.equal(saved.document.home.latitude, 38.8243);
assert.equal(saved.document.home.longitude, -76.7451);
assert.equal(saved.document.home.source, "MANUAL");

const restored = policy.parse(JSON.stringify(saved.document));
assert.equal(restored.ok, true);
assert.equal(restored.document.home.label, "Example City");
assert.equal(restored.document.revision, 1);

// Replacement is intentional, and a failed validation never mutates Home.
const invalid = policy.withHome(saved.document, "Other", "", "");
assert.equal(invalid.ok, false);
assert.equal(saved.document.home.label, "Example City");
const replacement = policy.withHome(saved.document, "New Home", "0", "0");
assert.equal(replacement.ok, true);
assert.equal(replacement.document.revision, 2);
assert.equal(replacement.document.home.latitude, 0);
assert.equal(replacement.document.home.longitude, 0);
assert.equal(saved.document.revision, 1);

// Invalid/corrupted/foreign persistence fails closed without guessed data.
assert.equal(policy.parse("garbage").reason, "JSON_INVALID");
assert.equal(policy.parse("").reason, "DOCUMENT_INVALID");
assert.equal(policy.parse(JSON.stringify({schema:"future",revision:2,home:null})).reason,
             "UNSUPPORTED_VERSION");
assert.equal(policy.parse(JSON.stringify({schema:empty.schema,revision:-1,home:null})).reason,
             "REVISION_INVALID");
assert.equal(policy.parse(JSON.stringify({schema:empty.schema,revision:1,home:{}})).reason,
             "HOME_INVALID");
assert.equal(policy.parse(JSON.stringify({schema:empty.schema,revision:1})).reason,
             "HOME_INVALID");
assert.equal(policy.parse("x".repeat(4097)).reason, "DOCUMENT_INVALID");
const badVersion = policy.withHome({schema:"future",revision:2,home:null},"Home","0","0");
assert.equal(badVersion.reason, "UNSUPPORTED_VERSION");

// M2: M1 Home-only data migrates without rewriting user-selected Home.
const legacy = JSON.parse(JSON.stringify(saved.document));
assert.equal(Object.prototype.hasOwnProperty.call(legacy, "explore"), true);
delete legacy.explore;
const migrated = policy.parse(JSON.stringify(legacy));
assert.equal(migrated.ok, true);
assert.equal(migrated.document.home.label, "Example City");
assert.equal(migrated.document.explore, null);
assert.equal(migrated.document.revision, 1);

const start = 1793653200000;
const noHome = policy.withExplore(empty, "Anchorage", "61.2181", "-149.9003",
                                  "2H", start);
assert.equal(noHome.reason, "HOME_NOT_SET");
assert.equal(policy.effectivePlace(empty, start), null);
assert.equal(policy.contextKind(empty, start), "NONE");

for (const duration of ["", "30", "FOREVER", "2HOURS", null]) {
    assert.equal(policy.withExplore(saved.document, "Anchorage", "61", "-149",
                                    duration, start).reason,
                 "EXPLORE_DURATION_INVALID");
}
assert.equal(policy.withExplore(saved.document, "Anchorage", "", "-149",
                                "2H", start).reason, "LATITUDE_INVALID");
assert.equal(policy.withExplore(saved.document, "", "61", "-149",
                                "2H", start).reason, "HOME_LABEL_INVALID");
assert.equal(policy.withExplore(saved.document, "Anchorage", "61", "-149",
                                "2H", "").reason, "EXPLORE_TIME_INVALID");
assert.equal(policy.withExplore(saved.document, "Anchorage", "61", "-149",
                                "2H", Number.NaN).reason, "EXPLORE_TIME_INVALID");

for (const [duration, ms] of [["30M", 1800000], ["2H", 7200000],
                             ["1D", 86400000]]) {
    const moved = policy.withExplore(saved.document, "Anchorage", "61.2181",
                                     "-149.9003", duration, start);
    assert.equal(moved.ok, true);
    assert.equal(moved.document.explore.durationKey, duration);
    assert.equal(moved.document.explore.startedAtMs, start);
    assert.equal(moved.document.explore.expiresAtMs, start + ms);
    assert.equal(moved.document.home.label, "Example City");
    assert.equal(moved.document.revision, saved.document.revision + 1);
    assert.equal(policy.contextKind(moved.document, start), "EXPLORE");
    assert.equal(policy.effectivePlace(moved.document, start).label, "Anchorage");
    assert.equal(policy.contextKind(moved.document, start + ms - 1), "EXPLORE");
    assert.equal(policy.contextKind(moved.document, start + ms), "HOME");
    assert.equal(policy.effectivePlace(moved.document, start + ms).label,
                 "Example City");

    // Restart does not extend a temporary destination's expiry time.
    const restored = policy.parse(JSON.stringify(moved.document));
    assert.equal(restored.ok, true);
    assert.equal(restored.document.explore.expiresAtMs, start + ms);
    assert.equal(policy.contextKind(restored.document, start + ms + 1), "HOME");
    assert.equal(policy.contextKind(restored.document, start - 1), "HOME");

    // Return Home clears the persisted override, not the underlying Home.
    const returned = policy.withoutExplore(moved.document);
    assert.equal(returned.ok, true);
    assert.equal(returned.document.home.label, "Example City");
    assert.equal(returned.document.explore, null);
    assert.equal(returned.document.revision, moved.document.revision + 1);
    assert.equal(policy.contextKind(returned.document, start + 1), "HOME");
    assert.equal(policy.withoutExplore(returned.document).reason,
                 "NO_EXPLORE_TO_CLEAR");

    // A Home replacement during Explore affects only the return destination.
    const movedHome = policy.withHome(moved.document, "Revised Home",
                                       "40.000", "-75.000");
    assert.equal(movedHome.ok, true);
    assert.equal(movedHome.document.explore.place.label, "Anchorage");
    assert.equal(policy.effectivePlace(movedHome.document, start).label,
                 "Anchorage");
    assert.equal(policy.effectivePlace(movedHome.document, start + ms).label,
                 "Revised Home");
}

const held = policy.withExplore(saved.document, "Tokyo", "35.6762",
                                 "139.6503", "MANUAL", start);
assert.equal(held.ok, true);
assert.equal(held.document.explore.expiresAtMs, null);
assert.equal(policy.contextKind(held.document, start + 50 * 86400000),
             "EXPLORE");
assert.equal(policy.withoutExplore(held.document).document.explore, null);

// Reject malformed persisted overrides, including coerced timestamps.
const badExplore = JSON.parse(JSON.stringify(held.document));
badExplore.explore.startedAtMs = "1793653200000";
assert.equal(policy.parse(JSON.stringify(badExplore)).reason,
             "EXPLORE_TIME_INVALID");
badExplore.explore.startedAtMs = start;
badExplore.explore.expiresAtMs = start + 7200000;
assert.equal(policy.parse(JSON.stringify(badExplore)).reason,
             "EXPLORE_TIME_INVALID");
badExplore.explore.durationKey = "2H";
badExplore.explore.expiresAtMs = start + 30;
assert.equal(policy.parse(JSON.stringify(badExplore)).reason,
             "EXPLORE_TIME_INVALID");
badExplore.explore.expiresAtMs = start + 7200000;
badExplore.explore.place.latitude = "";
assert.equal(policy.parse(JSON.stringify(badExplore)).reason,
             "EXPLORE_INVALID");
const orphan = JSON.parse(JSON.stringify(held.document));
orphan.home = null;
assert.equal(policy.parse(JSON.stringify(orphan)).reason,
             "EXPLORE_WITHOUT_HOME");

// Invalid wall-clock observations fail closed to Home.
assert.equal(policy.contextKind(held.document, ""), "HOME");
assert.equal(policy.effectivePlace(held.document, NaN).label, "Example City");

console.log("Place Registry M1/M2 Home and Explore policy: PASS");
