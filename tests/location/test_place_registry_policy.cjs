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
;({initialDocument, coordinate, place, normalize, parse, withHome})
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

console.log("Place Registry M1 manual Home policy: PASS");
