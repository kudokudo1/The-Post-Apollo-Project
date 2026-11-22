#!/usr/bin/env node
"use strict";
// Run the SAME pure policy invoked by QML, then exercise the actual
// advanceDoctorRead QML method body with a mocked Scope/Process state.
// No Qt instance, host files, service, SQLite or live Doctor data.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const ROOT = path.resolve(__dirname, "../..");
const policySource = fs.readFileSync(path.join(
    ROOT, "services/hospital/HospitalDoctorDirectoryExitPolicy.js"
), "utf8");
const qmlSource = fs.readFileSync(path.join(
    ROOT, "services/hospital/HospitalDoctorService.qml"
), "utf8");
const ctx = vm.createContext({});
vm.runInContext(policySource, ctx);

function qmlMethod(name, args) {
    const anchor = "function " + name + "(" + args + ") {";
    const at = qmlSource.indexOf(anchor);
    assert.ok(at >= 0, "QML method missing " + name);
    let depth = 0, end = -1;
    const start = at + anchor.length - 1;
    for (let i = start; i < qmlSource.length; ++i) {
        if (qmlSource[i] === "{") depth++;
        else if (qmlSource[i] === "}" && --depth === 0) {
            end = i + 1;
            break;
        }
    }
    assert.ok(end > start, "QML braces not closed: " + name);
    return qmlSource.slice(at, end);
}
const method = qmlMethod("advanceDoctorRead", "next");
assert.ok(qmlSource.includes(
    'import "HospitalDoctorDirectoryExitPolicy.js" as DoctorReadPolicy'
));
for (const marker of [
    "listProcess.pendingRead = DoctorReadPolicy.begin();",
    "DoctorReadPolicy.captureStdout(",
    "DoctorReadPolicy.captureStderr(",
    "DoctorReadPolicy.captureExit(",
    'listProcess.exec([nativeReaderPath, "doctor-directory"]);',
    "if (!root.refreshing || !listProcess.pendingRead)",
]) assert.ok(qmlSource.includes(marker), marker);
for (const forbidden of [
    "root.doctors = doctors;",
    "root.doctors = result.map(",
    "saveProcess.exec(",
    "pxArgs(",
    '"doctor-put"',
]) assert.ok(!qmlSource.includes(forbidden), "Unsafe source " + forbidden);

function doctor(id = "doctor-fixture") {
    return {
        id: id,
        name: "Fixture Doctor",
        role: "DOCTOR",
        status: "ACTIVE",
        createdAt: "2026-11-22",
        updatedAt: "2026-11-22",
    };
}
const raw = JSON.stringify([doctor()]);

function makeScope() {
    const scope = vm.createContext({
        listProcess: {pendingRead: ctx.begin()},
        refreshing: true,
        listResponseAccepted: false,
        loaded: false,
        doctors: [],
        lastError: "",
        lastRefreshedAt: "",
        refreshEvents: 0,
        doctorsRefreshed: function() { ++scope.refreshEvents; },
        Date: Date,
    });
    vm.runInContext(method, scope);
    const push = (type, value) => {
        if (!scope.refreshing || !scope.listProcess.pendingRead)
            return;
        const before = scope.listProcess.pendingRead;
        const after = type === "stdout"
            ? ctx.captureStdout(before, value)
            : type === "stderr"
                ? ctx.captureStderr(before, value)
                : ctx.captureExit(before, value[0], value[1]);
        scope.advanceDoctorRead(after);
    };
    return {scope, push};
}
function emptyBeforeCompletion(h) {
    // HospitalW's roster consumes the published doctors directly,
    // without a loaded flag, so this must stay empty on EVERY event
    // before the complete acceptance transition.
    assert.equal(h.scope.doctors.length, 0, "ROSTER_LEAKED_PENDING_STDOUT");
    assert.equal(h.scope.loaded, false);
    assert.equal(h.scope.listResponseAccepted, false);
    assert.equal(h.scope.refreshing, true);
    assert.equal(h.scope.refreshEvents, 0);
}
const events = [
    ["stdout", raw],
    ["stderr", ""],
    ["exit", [0, 0]],
];
const permutations = [
    [0, 1, 2], [0, 2, 1], [1, 0, 2],
    [1, 2, 0], [2, 0, 1], [2, 1, 0],
];
for (const sequence of permutations) {
    const h = makeScope();
    for (let i = 0; i < 3; ++i) {
        const [kind, value] = events[sequence[i]];
        h.push(kind, value);
        if (i < 2) emptyBeforeCompletion(h);
    }
    assert.equal(h.scope.loaded, true, "VALID_EXIT_MUST_COMMIT");
    assert.equal(h.scope.listResponseAccepted, true);
    assert.equal(h.scope.doctors.length, 1);
    assert.equal(h.scope.doctors[0].id, "doctor-fixture");
    assert.equal(h.scope.refreshing, false);
    assert.equal(h.scope.refreshEvents, 1);
    // Any callback arriving after completion must never change the roster.
    h.push("stderr", "LATE ERROR");
    h.push("stdout", JSON.stringify([doctor("late-doctor")]));
    h.push("exit", [1, 0]);
    assert.equal(h.scope.doctors[0].id, "doctor-fixture");
    assert.equal(h.scope.refreshEvents, 1);
}
for (const [caseName, override] of [
    ["nonzero-after-stdout", {exit: [2, 0]}],
    ["crash-zero-exit", {exit: [0, 1]}],
    ["unexpected-exit-type", {exit: ["0", 0]}],
    ["stderr-after-exit", {stderr: "BACKEND FAILED"}],
    ["malformed-output", {stdout: "{broken"}],
    ["empty-stdout", {stdout: ""}],
    ["duplicate-identity", {stdout: JSON.stringify([
        doctor("doctor-1"), doctor(" doctor-1 ")] )}],
    ["oversized-list", {stdout: JSON.stringify(
        Array.from({length: 251}, (_, i) => doctor("doctor-" + i)))}],
    ["object-not-list", {stdout: JSON.stringify({id: "doctor-1"})}],
]) {
    for (const order of permutations) {
        const h = makeScope();
        const sequence = events.map(([kind, value]) =>
            [kind, Object.hasOwn(override, kind) ? override[kind] : value]);
        for (let i = 0; i < 3; ++i) {
            const [kind, value] = sequence[order[i]];
            h.push(kind, value);
            if (i < 2) emptyBeforeCompletion(h);
        }
        assert.equal(h.scope.loaded, false, caseName);
        assert.equal(h.scope.listResponseAccepted, false, caseName);
        assert.equal(h.scope.doctors.length, 0, "FAILED_PROCESS_EXPOSED_ROSTER: " + caseName);
        assert.equal(h.scope.refreshing, false, caseName);
        assert.ok(h.scope.lastError, caseName);
        assert.equal(h.scope.refreshEvents, 1, caseName);
        h.push("stdout", JSON.stringify([doctor("late-after-failure")]));
        h.push("exit", [0, 0]);
        assert.equal(h.scope.doctors.length, 0, "LATE_CALLBACK_RESTORED_ROSTER");
    }
}
// Duplicated stdout before exit must not pass.
for (const order of ["early", "late"]) {
    const h = makeScope();
    h.push("stdout", raw);
    h.push("stdout", JSON.stringify([doctor("duplicate")]));
    if (order === "early") h.push("stderr", "");
    h.push("exit", [0, 0]);
    if (order === "late") h.push("stderr", "");
    assert.equal(h.scope.doctors.length, 0);
    assert.equal(h.scope.loaded, false);
}
// No process exit, no stderr completion, or no stdout completion: no
// publishing and no permission to start another read on the SAME Process.
for (const missing of ["stdout", "stderr", "exit"]) {
    const h = makeScope();
    for (const [kind, value] of events)
        if (kind !== missing) h.push(kind, value);
    emptyBeforeCompletion(h);
}
// Explicit empty [] is a valid *successful* zero-Doctor directory.
const none = makeScope();
none.push("exit", [0, 0]);
none.push("stderr", "");
none.push("stdout", "[]");
assert.equal(none.scope.loaded, true);
assert.equal(none.scope.doctors.length, 0);
assert.equal(none.scope.refreshEvents, 1);
console.log("HOSPITAL DOCTOR EVENT ORDER // PASS // real QML commit method + six signal orders, failure permutations, late data quarantine, no early roster publication");
