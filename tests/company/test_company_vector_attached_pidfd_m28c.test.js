#!/usr/bin/env node
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const root = path.resolve(__dirname, "../..");
const read = file => fs.readFileSync(path.join(root, file), "utf8");

const controller = read("services/company/CompanyVectorSidecarController.qml");
const coverage = read("widgets/CompanyCoveragePane.qml");
const company = read("widgets/CompanyNetworkW.qml");
const link = read("widgets/CompanyVectorBridgeLink.qml");
const launcher = read("services/company/CompanyVectorSidecarLaunch.py");
const bridge = read("experiments/company-vector-qt/CompanyVectorHostBridge.py");

test("M28c reports the actual attached Quickshell Process PID, never guessed parent or manual PID", () => {
    assert.match(controller, /signal nativeChildStarted\(int pid\)/);
    assert.match(controller, /onStarted:\s*\{/);
    assert.match(controller, /const attachedPid = Number\(vectorRunner\.processId\)/);
    assert.match(controller, /controller\.nativeChildStarted\(attachedPid\)/);
    assert.match(controller, /Math\.floor\(attachedPid\) === attachedPid/);
    assert.doesNotMatch(controller, /Quickshell\.processId/);
    assert.doesNotMatch(controller, /startDetached\(|swaymsg|\/proc\/|Qt\.openUrlExternally/);
    assert.match(controller, /vectorRunner\.running=true/);
    assert.match(controller, /vectorRunner\.running=false/);
});

test("Coverage propagates only the lifecycle of its existing native M15 launcher", () => {
    assert.match(coverage, /signal nativeVectorChildStarted\(int pid\)/);
    assert.match(coverage, /onNativeChildStarted:\s*function\(pid\)/);
    assert.match(coverage, /root\.nativeVectorChildStarted\(pid\)/);
    assert.match(coverage, /if \(vectorController\.launch\(online\)\)/);
    assert.match(coverage, /root\.nativeVectorLaunchRequested\(online\)/);
    assert.match(coverage, /vectorController\.stop\(\)/);
    assert.match(coverage, /onRunningChanged: if \(!running\) root\.nativeVectorClosed\(\)/);
    assert.doesNotMatch(coverage, /(?:^|\n)\s*(?:Process|FileView)\s*\{/);
});

test("M28c remains a safe optional bridge on old protocol or missing M25 module", () => {
    assert.match(company, /property bool vectorBridgeOptIn:\s*false/);
    assert.match(link, /property bool bridgeEnabled:\s*false/);
    assert.match(link, /typeof object\.reportNativeChildPid !== "function"/);
    assert.match(link, /function reportChildPid\(pid\)/);
    assert.match(link, /return object\.reportNativeChildPid\(actual\)/);
    assert.match(company, /function onNativeVectorChildStarted\(pid\)/);
    assert.match(company, /vectorBridgeLink\.reportChildPid\(pid\)/);
    assert.match(company, /function onNativeVectorLaunchRequested\(online\)/);
    assert.match(company, /function onNativeVectorClosed\(\)/);
    assert.match(link, /Qt\.createQmlObject\(/);
    assert.doesNotMatch(link, /^\s*import PostApollo\.CompanyVector/m);
    assert.doesNotMatch(company, /^\s*import PostApollo\.CompanyVector/m);
    assert.doesNotMatch(link+company+coverage, /\b(?:wl_display_connect|wlr_scene_|wlr_seat_|posix_spawn)\b/);
    assert.match(link, /failure must not suppress or replace the M15 launcher/i);
});

test("M15 execv/execve preserves the exact attached child PID, unlike spawning a new process", () => {
    assert.match(launcher, /os\.execv\(str\(executable\)/);
    assert.match(bridge, /os\.execve\(str\(binary\)/);
    assert.doesNotMatch(launcher+bridge, /(?:^|\n)\s*(?:subprocess\.Popen|os\.fork|os\.system|os\.spawnv)/m);
    assert.match(launcher, /trusted_executable\(home\)/);
    assert.match(bridge, /owned_path\(home/);
    assert.match(controller, /online \? "online" : "offline"/);
});
