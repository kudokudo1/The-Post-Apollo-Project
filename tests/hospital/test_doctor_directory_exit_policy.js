#!/usr/bin/env node
"use strict";
// Execute the actual DoctorService QML lifecycle methods in a mocked Scope.
// Cross-refresh race and timeout coverage is source-level, not a live host.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const ROOT = path.resolve(__dirname, "../..");
const qml = fs.readFileSync(path.join(
    ROOT, "services/hospital/HospitalDoctorService.qml"
), "utf8");
const policy = vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(
    ROOT, "services/hospital/HospitalDoctorDirectoryExitPolicy.js"
), "utf8"), policy);

function method(name, args) {
    const anchor = "function " + name + "(" + args + ") {";
    const start = qml.indexOf(anchor);
    assert.ok(start >= 0, "Missing QML method " + name);
    const open = start + anchor.length - 1;
    let depth = 0;
    for (let i = open; i < qml.length; i++) {
        if (qml[i] === "{") depth++;
        else if (qml[i] === "}" && --depth === 0)
            return qml.slice(start, i + 1);
    }
    throw new Error("Unbalanced QML method " + name);
}
const names = [
    ["refresh", ""],
    ["isCurrentDoctorRead", "process, generation"],
    ["completeDoctorRead", "process, generation, result"],
    ["advanceDoctorRead", "process, generation, next"],
    ["failDoctorRead", "process, generation, reason"],
    ["timeoutDoctorRead", "watchdog, process, generation"],
];
const methods = names.map(([n, args]) => method(n, args));
for (const needle of [
    "doctorReadFactory.createObject(root, {",
    "requestGeneration: generation",
    "readGeneration += 1;",
    "doctorWatchdogFactory.createObject(root, {",
    "ownerProcess: process,",
    "requestGeneration: generation",
    "activeWatchdog = watchdog;",
    "activeWatchdog = null;",
    "watchdog.start();",
    "watchdog.stop();",
    "watchdog.destroy();",
    "Qt.callLater(function() {",
    "process.destroy();",
    "activeRead === process",
    "generation === readGeneration",
    "requestProcess, requestProcess.requestGeneration",
    "DoctorReadPolicy.captureStdout(",
    "DoctorReadPolicy.captureStderr(",
    "DoctorReadPolicy.captureExit(",
    "HOSPITAL BACKEND NOT READY // DOCTOR READ TIMED OUT",
    'process.exec([nativeReaderPath, "doctor-directory"]);',
    "onTriggered: root.timeoutDoctorRead(",
    "requestWatchdog, requestWatchdog.ownerProcess,",
    "requestWatchdog.requestGeneration",
    "activeWatchdog !== watchdog",
]) assert.ok(qml.includes(needle), "Unpinned QML source: " + needle);
for (const forbidden of [
    "listProcess.pendingRead",
    "doctorReadWatchdog",
    "root.activeRead, root.readGeneration",
    "root.doctors = doctors;",
    "saveProcess.exec(",
    "pxArgs(",
    '"doctor-put"',
]) assert.ok(!qml.includes(forbidden), "Legacy/stale QML: " + forbidden);

function doctor(id = "doctor-fixture") {
    return {
        id: id, name: "Fixture Doctor", role: "DOCTOR",
        status: "ACTIVE", createdAt: "2026-11-22",
        updatedAt: "2026-11-22"
    };
}
const stdout = JSON.stringify([doctor()]);
function mock(options = {}) {
    const jobs = [];
    const timers = [];
    const later = [];
    const scope = vm.createContext({
        root: null,
        DoctorReadPolicy: policy,
        doctors: [],
        loaded: false,
        refreshing: false,
        saving: false,
        listResponseAccepted: false,
        lastError: "",
        lastRefreshedAt: "",
        lastSavedDoctor: null,
        activeRead: null,
        activeWatchdog: null,
        readGeneration: 0,
        nativeReaderPath: "/usr/libexec/post-apollo/hospital/hospital-room-read",
        notifications: 0,
        doctorsRefreshed: function() { scope.notifications++; },
        Qt: {callLater: function(fn) { later.push(fn); }},
        Date: Date,
    });
    scope.root = scope;
    scope.doctorReadFactory = {
        createObject: function(parent, args) {
            if (options.factoryFails) return null;
            const instance = {
                requestGeneration: args.requestGeneration,
                pendingRead: policy.begin(),
                running: false,
                destroyed: false,
                launch: null,
                exec: function(argv) {
                    if (options.execThrows) throw new Error("start failure");
                    this.running = true;
                    this.launch = [...argv];
                },
                destroy: function() { this.destroyed = true; },
            };
            jobs.push(instance);
            return instance;
        }
    };
    scope.doctorWatchdogFactory = {
        createObject: function(parent, props) {
            if (options.timerFactoryFails) return null;
            const timer = {
                ownerProcess: props.ownerProcess,
                requestGeneration: props.requestGeneration,
                active: false,
                stopped: false,
                destroyed: false,
                start: function() {
                    if (options.timerStartThrows)
                        throw new Error("watchdog timer start failure");
                    this.active = true;
                },
                stop: function() { this.active = false; this.stopped = true; },
                destroy: function() { this.destroyed = true; },
            };
            timers.push(timer);
            return timer;
        }
    };
    for (const source of methods)
        vm.runInContext(source, scope);
    const deliver = (job, kind, value) => {
        if (!scope.isCurrentDoctorRead(job, job.requestGeneration))
            return false;
        const prev = job.pendingRead;
        const next = kind === "stdout"
            ? policy.captureStdout(prev, value)
            : kind === "stderr"
                ? policy.captureStderr(prev, value)
                : policy.captureExit(prev, value[0], value[1]);
        scope.advanceDoctorRead(job, job.requestGeneration, next);
        return true;
    };
    const fireWatchdog = (timer) => {
        // The QML Timer's onTriggered forwards its ORIGINAL owner identity,
        // not the current active request's mutable state.
        return scope.timeoutDoctorRead(
            timer, timer.ownerProcess, timer.requestGeneration
        );
    };
    return {scope, jobs, timers, later, deliver, fireWatchdog};
}
const events = [
    ["stdout", stdout],
    ["stderr", ""],
    ["exit", [0, 0]],
];
const orders = [
    [0, 1, 2], [0, 2, 1], [1, 0, 2],
    [1, 2, 0], [2, 0, 1], [2, 1, 0],
];
function unpublished(h, priorNotifications = 0) {
    assert.equal(h.scope.doctors.length, 0, "PUBLISHED_PREMATURE_ROSTER");
    assert.equal(h.scope.loaded, false);
    assert.equal(h.scope.listResponseAccepted, false);
    assert.equal(h.scope.refreshing, true);
    assert.equal(h.scope.notifications, priorNotifications,
        "UNVERIFIED_REFRESH_EMITTED_NEW_NOTIFICATION");
}
function commit(h, index, values = events, sequence = [0, 1, 2]) {
    const job = h.jobs[index];
    const priorNotifications = h.scope.notifications;
    for (let i = 0; i < 3; i++) {
        const [kind, val] = values[sequence[i]];
        assert.equal(h.deliver(job, kind, val), true);
        if (i < 2) unpublished(h, priorNotifications);
    }
    return job;
}
// Existing semantics: six possible callback orders all commit only after
// complete zero-normal-exit, stdout valid and stderr empty.
for (const sequence of orders) {
    const h = mock();
    assert.equal(h.scope.refresh(), true);
    assert.deepEqual(h.jobs[0].launch, [
        "/usr/libexec/post-apollo/hospital/hospital-room-read", "doctor-directory"
    ]);
    assert.equal(h.scope.refresh(), false, "OVERLAP_MUST_REFUSE");
    unpublished(h);
    const job = commit(h, 0, events, sequence);
    assert.equal(h.scope.loaded, true);
    assert.equal(h.scope.doctors[0].id, "doctor-fixture");
    assert.equal(h.scope.notifications, 1);
    assert.equal(h.timers.length, 1);
    assert.equal(h.timers[0].active, false);
    assert.equal(h.timers[0].stopped, true);
    assert.equal(job.pendingRead, null);
    assert.equal(h.scope.activeRead, null);
    assert.equal(h.scope.refreshing, false);
    assert.equal(job.running, false);
    h.later.forEach(fn => fn());
    assert.equal(job.destroyed, true);
    assert.equal(h.timers[0].destroyed, true);
}
for (const [label, override] of [
    ["nonzero", {exit: [2, 0]}],
    ["crash", {exit: [0, 1]}],
    ["bad-status", {exit: [0, "NormalExit"]}],
    ["late-stderr", {stderr: "ACCESS DENIED"}],
    ["empty", {stdout: ""}],
    ["malformed", {stdout: "{bad"}],
    ["duplicate-id", {stdout: JSON.stringify([
        doctor("A"), doctor(" A ")])}],
    ["over-limit", {stdout: JSON.stringify(Array.from(
        {length: 251}, (_, n) => doctor("doctor-" + n)))}],
]) {
    for (const sequence of orders) {
        const h = mock();
        assert.equal(h.scope.refresh(), true);
        const responses = events.map(([kind, val]) =>
            [kind, Object.hasOwn(override, kind) ? override[kind] : val]);
        commit(h, 0, responses, sequence);
        assert.equal(h.scope.loaded, false, label);
        assert.equal(h.scope.doctors.length, 0, label);
        assert.equal(h.scope.refreshing, false, label);
        assert.ok(h.scope.lastError, label);
    }
}
// The previously untested race: old stdout arrives after a NEW request
// has already started. Request identity is the immutable Process object
// plus generation, not the mutable shared Process's current argument list.
for (const terminal of ["success", "nonzero", "timeout"]) {
    const h = mock();
    assert.equal(h.scope.refresh(), true);
    const old = h.jobs[0];
    const oldTimer = h.timers[0];
    if (terminal === "timeout") {
        assert.equal(h.fireWatchdog(oldTimer), true);
    } else {
        const responses = events.map(([k, v]) =>
            [k, terminal === "nonzero" && k === "exit" ? [1, 0] : v]);
        commit(h, 0, responses);
    }
    assert.equal(h.scope.refresh(), true);
    const current = h.jobs[1];
    const currentTimer = h.timers[1];
    assert.notStrictEqual(old, current);
    assert.notStrictEqual(oldTimer, currentTimer);
    assert.notEqual(old.requestGeneration, current.requestGeneration);
    assert.strictEqual(oldTimer.ownerProcess, old);
    assert.strictEqual(currentTimer.ownerProcess, current);
    assert.equal(oldTimer.requestGeneration, old.requestGeneration);
    assert.equal(currentTimer.requestGeneration, current.requestGeneration);
    assert.equal(oldTimer.active, false, "OLD_TIMER_MUST_BE_STOPPED");
    assert.equal(currentTimer.active, true, "NEW_TIMER_MUST_BE_RUNNING");
    unpublished(h, 1);
    // Emulate an already-queued timeout handler from A AFTER B starts.
    // It must not cancel B, even if A's timer was previously stopped.
    assert.equal(h.fireWatchdog(oldTimer), false);
    assert.equal(h.scope.timeoutDoctorRead(
        oldTimer, current, current.requestGeneration), false,
        "A_STALE_TIMER_CANNOT_BORROW_B_PROCESS_AND_GENERATION");
    unpublished(h, 1);
    for (const [kind, value] of [
        ["stdout", JSON.stringify([doctor("stale")])],
        ["stderr", "STALE ERROR"],
        ["exit", [0, 0]],
    ]) {
        assert.equal(h.deliver(old, kind, value), false);
        unpublished(h, 1);
    }
    assert.equal(h.scope.advanceDoctorRead(
        old, old.requestGeneration, policy.captureStdout(
            policy.begin(), JSON.stringify([doctor("forged-old")])
        )), undefined);
    unpublished(h, 1);
    commit(h, 1, [
        ["stdout", JSON.stringify([doctor("fresh")])],
        ["stderr", ""],
        ["exit", [0, 0]]
    ], [2, 0, 1]);
    assert.equal(h.scope.loaded, true);
    assert.equal(h.scope.doctors.length, 1);
    assert.equal(h.scope.doctors[0].id, "fresh");
    assert.equal(currentTimer.active, false);
    // Already-queued old A and current B timeout events cannot erase
    // a roster once the B Process has completed and been retired.
    assert.equal(h.fireWatchdog(oldTimer), false);
    assert.equal(h.fireWatchdog(currentTimer), false);
    assert.equal(h.scope.doctors[0].id, "fresh");
    // Even after new success, old callbacks cannot replace the roster.
    assert.equal(h.deliver(old, "stdout",
        JSON.stringify([doctor("later") ])), false);
    assert.equal(h.scope.doctors[0].id, "fresh");
}
// If the host process fails before process-exit signal, watchdog recovery
// makes the directory unavailable and a NEW isolated retry possible.
for (const opts of [
    {factoryFails: true},
    {execThrows: true},
    {timerFactoryFails: true},
    {timerStartThrows: true},
]) {
    const h = mock(opts);
    assert.equal(h.scope.refresh(), false);
    assert.equal(h.scope.doctors.length, 0);
    assert.equal(h.scope.loaded, false);
    assert.equal(h.scope.refreshing, false);
    assert.equal(h.scope.activeRead, null);
    assert.match(h.scope.lastError, /(START FAILED|WATCHDOG UNAVAILABLE)/);
    assert.equal(h.scope.activeWatchdog, null);
    h.later.forEach(fn => fn());
    assert.ok(h.jobs.every(job => job.destroyed),
        "FAILED_START_LEAKED_PROCESS_OBJECT");
    assert.ok(h.timers.every(timer => timer.destroyed),
        "FAILED_START_LEAKED_WATCHDOG_OBJECT");
}
for (const omit of ["stdout", "stderr", "exit"]) {
    const h = mock();
    assert.equal(h.scope.refresh(), true);
    const job = h.jobs[0];
    for (const [kind, val] of events)
        if (kind !== omit) h.deliver(job, kind, val);
    unpublished(h);
    assert.equal(h.fireWatchdog(h.timers[0]), true);
    assert.equal(h.scope.loaded, false);
    assert.equal(h.scope.refreshing, false);
    assert.equal(h.scope.activeRead, null);
    assert.equal(job.running, false);
    assert.equal(h.scope.doctors.length, 0);
    assert.match(h.scope.lastError, /TIMED OUT/);
    // Missing callback from retired process after retry starts is refused.
    assert.equal(h.scope.refresh(), true);
    assert.equal(h.deliver(job, omit, omit === "exit" ? [0, 0] : ""), false);
    assert.equal(h.fireWatchdog(h.timers[0]), false,
        "OLD_TIMEOUT_CANNOT_CANCEL_RETRY");
    assert.equal(h.timers[1].active, true);
    unpublished(h, 1);
}
// A real [] is successful, and stale data is cleared at refresh start.
const h = mock();
assert.equal(h.scope.refresh(), true);
commit(h, 0, [["stdout", "[]"], ["stderr", ""], ["exit", [0, 0]]]);
assert.equal(h.scope.loaded, true);
assert.equal(h.scope.doctors.length, 0);
assert.equal(h.scope.refresh(), true);
unpublished(h, 1);
// Another queued-event ordering: A succeeds, B becomes active, then both
// A's stale timer and A's late stream callback run. Neither may promote or
// cancel B before its own watchdog fires.
const retry = mock();
assert.equal(retry.scope.refresh(), true);
commit(retry, 0);
assert.equal(retry.scope.refresh(), true);
assert.equal(retry.fireWatchdog(retry.timers[0]), false);
assert.equal(retry.deliver(retry.jobs[0], "stdout",
    JSON.stringify([doctor("stale") ])), false);
unpublished(retry, 1);
assert.equal(retry.fireWatchdog(retry.timers[1]), true);
assert.equal(retry.scope.loaded, false);
assert.equal(retry.scope.doctors.length, 0);
assert.match(retry.scope.lastError, /TIMED OUT/);
assert.equal(retry.scope.notifications, 2);
console.log("HOSPITAL DOCTOR WATCHDOG OWNER // PASS // six event orders, old-timer-after-retry isolation, wrong-owner timer refusal, startup and timeout cleanup // SOURCE-ONLY");
