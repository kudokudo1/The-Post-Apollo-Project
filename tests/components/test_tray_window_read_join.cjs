#!/usr/bin/env node
"use strict";
// Exercise the real QML publish method and imported JS completion gate with
// both possible Qt callback orders. No local Sway or D-Bus commands run.
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const load = p => fs.readFileSync(path.resolve(__dirname, "../../", p), "utf8");
const joinSource = load("modules/TrayWindowReadJoin.js");
const policySource = load("modules/TrayDesktopVisibility.js");
const qml = load("modules/Tray.qml");

const join = vm.createContext({});
vm.runInContext(joinSource, join);
const parser = vm.createContext({});
vm.runInContext(policySource, parser);

const swayTree = JSON.stringify({
    type:"root", nodes:[{
        type:"output", nodes:[{
            type:"workspace", nodes:[
                {type:"con", app_id:"vesktop", visible:true, nodes:[]},
                {type:"con", app_id:"lutris", visible:false, nodes:[]}
            ]
        }]
    }]
});

const fresh = join.freshRead();
assert.equal(join.outcome(fresh).ready, false);
const exitFirst = join.withExit(fresh, 0);
assert.equal(join.outcome(exitFirst).ready, false, "exit alone cannot publish");
const stdoutFirst = join.withStdout(fresh, swayTree);
assert.equal(join.outcome(stdoutFirst).ready, false, "stdout alone cannot publish");
for (const joined of [
    join.withStdout(exitFirst, swayTree),
    join.withExit(stdoutFirst, 0)
]) {
    const result = join.outcome(joined);
    assert.equal(result.ready, true);
    assert.equal(result.success, true);
    assert.deepEqual(Array.from(parser.visibleWindowKeysFromTree(result.stdout)),
        ["vesktop"]);
}
assert.equal(join.outcome(join.withStdout(join.withExit(fresh,1),swayTree)).success,false,
    "nonzero exit must not publish even valid-looking stdout");
assert.equal(join.outcome(join.withStdout(join.withExit(fresh,0),"")).reason,"empty-stdout");
assert.equal(join.outcome(join.withStdout(join.withExit(fresh,0),"{broken}")).success,true,
    "the separate Sway policy, not the stream gate, validates JSON");

const inspect = json => parser.inspectVisibleWindowTree(json);
assert.equal(inspect(swayTree).valid,true);
assert.equal(inspect(swayTree).windowCount,1);
assert.deepEqual(Array.from(inspect(swayTree).keys),["vesktop"]);
assert.equal(inspect("{bad").reason,"invalid-json");
assert.equal(inspect("{}").reason,"not-root");
assert.equal(inspect("").reason,"empty");
assert.equal(inspect(JSON.stringify({type:"root",nodes:[]})).valid,true);
assert.equal(inspect(JSON.stringify({type:"root",nodes:[]})).windowCount,0);
assert.equal(inspect(JSON.stringify({type:"root",nodes:[]})).keys.length,0);

// Run the actual publication method extracted from Tray.qml, with read-only
// Quickshell stand-ins. This catches a premature update in onExited.
const start = qml.indexOf("    function publishWindowTreeIfReady() {");
const end = qml.indexOf("\n    Component.onCompleted:", start);
assert.ok(start>=0 && end>start, "publisher QML method exists");
const body = qml.slice(start,end).trim();
let stops=0, restarts=0;
const context = vm.createContext({
    windowTreeRead: join.freshRead(),
    windowTreePublished: false,
    windowTreeDirty: false,
    windowTreeVisibleKeyCount: 0,
    windowTreeVisibleWindowCount: 0,
    windowTreeReadStatus: "unread",
    visibleDesktopKeys: ["stale-app"],
    WindowReadJoin: join,
    DesktopVisibility: parser,
    windowTreeTimeout: {stop() {stops++;}},
    desktopWindowRefresh: {restart() {restarts++;}},
    console: {warn() {}}
});
const publish = vm.runInContext("(" + body + ")", context);

context.windowTreeRead = join.withExit(join.freshRead(),0);
assert.equal(publish(),false);
assert.deepEqual(context.visibleDesktopKeys,["stale-app"],
    "exit cannot erase active cards while stdout is still arriving");
context.windowTreeRead = join.withStdout(context.windowTreeRead,swayTree);
assert.equal(publish(),true);
assert.deepEqual(Array.from(context.visibleDesktopKeys),["vesktop"]);
assert.equal(context.windowTreeReadStatus,"ok");
assert.equal(context.windowTreeVisibleKeyCount,1);
assert.equal(context.windowTreeVisibleWindowCount,1);
assert.equal(context.windowTreePublished,true);
assert.equal(publish(),false,"each generation publishes once");
assert.equal(stops,1);

// Simulate stream arriving before exit and an event that occurred during read.
context.windowTreeRead=join.withStdout(join.freshRead(),swayTree);
context.windowTreePublished=false;
context.windowTreeDirty=true;
assert.equal(publish(),false);
context.windowTreeRead=join.withExit(context.windowTreeRead,0);
assert.equal(publish(),true);
assert.equal(restarts,1,"coalesced event schedules one fresh read");
assert.equal(context.windowTreeDirty,false);

// Malformed output cannot preserve an old application's active card.
context.windowTreePublished=false;
context.visibleDesktopKeys=["stale-app"];
context.windowTreeRead=join.withStdout(join.withExit(join.freshRead(),0),"{broken}");
assert.equal(publish(),true);
assert.equal(context.windowTreeReadStatus,"invalid-json");
assert.equal(context.visibleDesktopKeys.length,0);

// Verify actual signal hooks and bounded fail-closed timeout in the QML.
assert.match(qml,/onStreamFinished:\s*\{[\s\S]*WindowReadJoin\.withStdout/);
assert.match(qml,/onExited:\s*function\(exitCode, exitStatus\)\s*\{[\s\S]*WindowReadJoin\.withExit/);
assert.match(qml,/onStarted:\s*\{\s*trayDock\.windowTreeRead = WindowReadJoin\.freshRead\(\)/);
assert.match(qml,/id:\s*windowTreeTimeout[\s\S]*?interval:\s*3500/);
assert.doesNotMatch(qml,/onExited:\s*function\(exitCode, exitStatus\)\s*\{\s*trayDock\.visibleDesktopKeys/);
assert.match(qml,/DesktopVisibility\.hasVisibleDesktopWindow/);
assert.match(qml,/readonly property bool cardEmphasized:\s*trayButton\.appOnDesktop/);
console.log("Tray stdout/exit join: both callback orders, failure, stale state, QML wiring PASS");
