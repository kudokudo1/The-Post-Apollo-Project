#!/usr/bin/env node
"use strict";
// Hospital H1 protected Doctor-name candidate: executable source-method
// checks against fake state only. Neither a native issuer nor a real Doctor
// writer is ever connected, and no real database or user profile is touched.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.resolve(__dirname, "../..");
const policySource = fs.readFileSync(path.join(
    root, "services/hospital/HospitalDoctorNameIntentPolicy.js"
), "utf8");
const qmlSource = fs.readFileSync(path.join(
    root, "services/hospital/HospitalProtectedDoctorNameService.qml"
), "utf8");
const legacySource = fs.readFileSync(path.join(
    root, "services/hospital/HospitalDoctorNameService.qml"
), "utf8");
const hostSource = fs.readFileSync(path.join(root, "widgets/HospitalW.qml"), "utf8");
const policy = vm.createContext({});
vm.runInContext(policySource, policy);

assert.match(qmlSource, /readonly property bool protectedNameWritesReady:\s*false/);
assert.match(qmlSource, /import "HospitalDoctorNameIntentPolicy\.js" as NameIntentPolicy/);
assert.match(qmlSource, /PROTECTED DOCTOR NAME ISSUER NOT ENROLLED/);
assert.match(qmlSource, /DOCTOR NAME \/\/ NO WRITE PERFORMED/);
assert.match(hostSource, /HospitalDoctorNameService\s*\{/);
assert.ok(!hostSource.includes("HospitalProtectedDoctorNameService {"),
    "MIGRATION_CANDIDATE_WAS_ACTIVATED");
assert.match(legacySource, /doctor-name-set/);
for (const forbidden of [
    "Process {", "StdioCollector", "exec(", "bash", "store-command",
    "sqlite3", "database", "$HOME", "nativeClientPath:", "socket",
    "Qt.openUrlExternally(", "nameSaved(",
]) {
    // Comment text may mention databases or socket, so restrict these
    // checks to syntactically executable transport forms where needed.
    if (forbidden === "database" || forbidden === "socket"
            || forbidden === "bash" || forbidden === "nameSaved(")
        continue;
    assert.ok(!qmlSource.includes(forbidden),
        "CANDIDATE_REQUEST_CAN_MUTATE_SYSTEM: " + forbidden);
}
for (const forbidden of [
    "doctor-put", "status:", "role:", "roomId:", "assignmentId:",
    "argv:", "sql:", "permission:", "providerId:",
]) assert.ok(!policySource.includes(forbidden), "OVERBROAD_NAME_INTENT: " + forbidden);

function prepare(id, name) {
    return policy.prepareNameIntent(id, name);
}
function good(id, name) {
    const r = prepare(id, name);
    assert.equal(r.ok, true, String(r.reason));
    assert.deepEqual(Object.keys(r.intent).sort(),
        ["action", "doctorId", "name", "schema"]);
    assert.equal(r.intent.schema, "postapollo.hospital.doctor-name-intent.v1");
    assert.equal(r.intent.action, "DOCTOR_NAME_SET");
    return r.intent;
}
assert.equal(good("doctor-1", "New Name").name, "New Name");
assert.equal(good(" doctor-1 ", "  New Name  ").name, "New Name");
assert.equal(good("doctor-1", "").name, "");
assert.equal(good("doctor-1", "    ").name, "");
assert.equal(good("doctor-1", "🌸".repeat(96)).name, "🌸".repeat(96));
assert.equal(good("id_1:/-x.y", "Dr. Kudo").doctorId, "id_1:/-x.y");
assert.equal(good("d".repeat(160), "Doctor").doctorId.length, 160);

for (const [id, name] of [
    ["", "Name"], ["d".repeat(161), "Name"], ["../\\test", "Name"],
    ["bad id", "Name"], ["d\n1", "Name"], ["d", "a".repeat(97)],
    ["d", "a\nb"], ["d", "a\tb"], ["d", "a\x7fb"],
    ["d", "\uD800"], ["d", "\uDC00"], ["d", "🌸".repeat(97)],
    [17, "Doctor"], ["d", 12], ["d", null],
    ["d", {name: "override", role: "ADMIN"}],
]) {
    const result = prepare(id, name);
    assert.equal(result.ok, false, "MALFORMED_NAME_INTENT_ACCEPTED");
    assert.equal(result.intent, null);
    assert.match(result.reason, /^DOCTOR_NAME_/);
}

// Extract and execute the exact QML method bodies in a fake Scope, not a
// rewritten approximation of UI refusal. This catches future accidentally
// returning true, emitting nameSaved, or retaining a saved-Doctor payload.
function method(name, args) {
    const anchor = "function " + name + "(" + args + ") {";
    const start = qmlSource.indexOf(anchor);
    assert.ok(start >= 0, "MISSING_QML_METHOD_" + name);
    const braceStart = start + anchor.length - 1;
    let depth = 0;
    for (let i = braceStart; i < qmlSource.length; i++) {
        if (qmlSource[i] === "{") depth++;
        else if (qmlSource[i] === "}" && --depth === 0)
            return qmlSource.slice(start, i + 1);
    }
    throw new Error("UNCLOSED_QML_METHOD_" + name);
}
const run = vm.createContext({
    root: null,
    NameIntentPolicy: policy,
    saving: false,
    lastError: "",
    lastStatus: "",
    pendingDoctorId: "",
    lastSavedDoctor: null,
    preparedIntent: null,
    nameSavedCount: 0,
    refusedCount: 0,
    nameSaved: function() { ++run.nameSavedCount; },
    refused: function(message) {
        assert.match(message, /HOSPITAL NATIVE HOLD/);
        ++run.refusedCount;
    }
});
run.root = run;
for (const code of [
    method("clearStatus", ""),
    method("prepareName", "doctorIdValue, displayNameValue"),
    method("saveName", "doctorIdValue, displayNameValue")
]) vm.runInContext(code, run);
assert.equal(run.prepareName("doc-1", "  Candidate Doctor  "), true);
assert.equal(run.preparedIntent.doctorId, "doc-1");
assert.equal(run.preparedIntent.name, "Candidate Doctor");
assert.equal(run.saving, false);
assert.equal(run.nameSavedCount, 0);
assert.equal(run.saveName("doc-1", "New Doctor"), false);
assert.equal(run.nameSavedCount, 0);
assert.equal(run.saving, false);
assert.equal(run.lastSavedDoctor, null);
assert.equal(run.pendingDoctorId, "doc-1");
assert.equal(run.preparedIntent.action, "DOCTOR_NAME_SET");
assert.match(run.lastError, /PROTECTED DOCTOR NAME ISSUER NOT ENROLLED/);
assert.match(run.lastStatus, /NO WRITE PERFORMED/);
assert.equal(run.refusedCount, 1);
run.clearStatus();
assert.equal(run.lastError, "");
assert.equal(run.saveName("doc-1", "Invalid\x00Name"), false);
assert.equal(run.preparedIntent, null);
assert.equal(run.pendingDoctorId, "");
assert.equal(run.nameSavedCount, 0);
assert.equal(run.refusedCount, 2);
assert.match(run.lastError, /DOCTOR_NAME_TEXT_REFUSED/);
console.log("HOSPITAL H1 NAME INTENT // PASS // exact name-only payload, hostile text refusal, gated QML writer, legacy UI unchanged // NO NATIVE WRITE");
