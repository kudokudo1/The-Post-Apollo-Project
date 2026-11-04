#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.resolve(__dirname, "../..");
const read = file => fs.readFileSync(path.join(root, file), "utf8");
const policy = {};
vm.runInNewContext(read("services/connections/ConnectionsRequestDisplayPolicy.js")
    .replace(/^\.pragma library\s*/m, ""), policy);

const id = "a".repeat(32);
const baseline = {
    ok:true, requestId:id, state:"PENDING", provider:"nasa-firms",
    consumer:"weather-earth", operation:"fires.hotspots.read",
    profile:"ci-only-profile", reason:"AWAITING_SIMULATED_REVIEW",
    expiresInMs:15000, credentialPresent:false, realGrantActive:false,
    canApproveInProduction:false, simulated:true,
};
const states=[
    ["PENDING","AWAITING_SIMULATED_REVIEW",15000],
    ["APPROVED","SIMULATED_HOST_APPROVED",4500],
    ["DENIED","OPERATOR_DENIED",0],
    ["CANCELLED","HOST_CANCELLED",0],
    ["CANCELLED","HOST_SHUTDOWN",0],
    ["EXPIRED","REQUEST_EXPIRED",0],
    ["COMPLETED","SYNTHETIC_OPERATION_COMPLETE",0],
    ["FAILED","HOST_DISCONNECTED",0],
    ["FAILED","FAKE_BROKER_APPROVAL_FAILED",0],
    ["FAILED","FAKE_OPERATION_FAILED",0],
];
for (const [state,reason,ms] of states) {
    const display=policy.project({...baseline,state,reason,expiresInMs:ms},"nasa-firms");
    assert.equal(display.state,state);
    assert.equal(display.title,"SIMULATED // "+state);
    assert.equal(display.explanation,"FAKE HOST TEST ONLY // NO REAL PERMISSION");
    assert.equal(display.live,false);
    assert.equal(display.canApprove,false);
    assert.equal(display.grantActive,false);
    assert.equal(display.reviewOnly,true);
    assert.equal(display.requestId,"");
    assert.equal(display.provider,"nasa-firms");
    assert.equal(display.expiresInMs,ms);
    assert.equal(policy.canAuthorize(display,"approve"),false);
    assert.equal(policy.canAuthorize(display,"deny"),false);
}

const malformed=[
    null, undefined, false, {}, [], "PENDING",
    {...baseline,requestId:"evil-abcdefghijklmnopqrstuv01234"},
    {...baseline,requestId:"A".repeat(32)},
    {...baseline,requestId:"x".repeat(32)},
    {...baseline,state:"CONNECTED"},
    {...baseline,state:"__proto__"},
    {...baseline,state:"PENDING",reason:"HOST_SHUTDOWN"},
    {...baseline,state:"COMPLETED",reason:"SYNTHETIC_OPERATION_COMPLETE",expiresInMs:3},
    {...baseline,provider:"proton-mail"},
    {...baseline,consumer:"social-mail"},
    {...baseline,operation:"mail.send"},
    {...baseline,profile:"other-user"},
    {...baseline,simulated:false},
    {...baseline,canApproveInProduction:true},
    {...baseline,realGrantActive:true},
    {...baseline,credentialPresent:true},
    {...baseline,expiresInMs:NaN},
    {...baseline,expiresInMs:60001},
    {...baseline,expiresInMs:1.1},
    {...baseline,expiresInMs:-1},
    {...baseline,secret:"PRIVATE"},
    {...baseline,token:"PRIVATE"},
    {...baseline,requestId:null},
];
for (const value of malformed) {
    const display=policy.project(value,"nasa-firms");
    assert.equal(display.state,"OFFLINE","bad record must be discarded");
    assert.equal(display.title,"HOST NOT CONNECTED");
    assert.equal(display.grantActive,false);
    assert.equal(display.canApprove,false);
    assert.equal(display.live,false);
}
for(const provider of ["social","proton-mail","unknown",null,"__proto__"]) {
    assert.equal(policy.project(baseline,provider).state,"OFFLINE");
}
assert.equal(policy.project(null,"nasa-firms").known,true);
assert.equal(policy.project(null,"proton-mail").known,true);
assert.equal(policy.project(null,"bad-provider").known,false);

const bridge=read("services/connections/ConnectionsRequestStatus.qml");
const moduleFile=read("services/connections/qmldir");
const details=read("widgets/cpuplus/CpuPlusSettingsConnectionsDetailsPane.qml");
const native=read("tests/cpuplus/fixtures/C1ConnectionsNative.qml");
const click=read("scripts/cpuplus/verify_connections_native_c1.sh");
assert.match(bridge,/pragma Singleton/);
assert.match(bridge,/readonly property bool hostConnected: false/);
assert.match(bridge,/readonly property bool hostAuthenticated: false/);
assert.match(bridge,/readonly property bool canApprove: false/);
assert.match(bridge,/readonly property var latestStatus: null/);
assert.match(bridge,/DisplayPolicy\.project\(latestStatus, providerId\)/);
assert.doesNotMatch(bridge,/Process\s*\{|StdioCollector|FileView|onCompleted:|secret-tool|sendRequest|setStatus|approve\(/i);
assert.match(moduleFile,/singleton ConnectionsRequestStatus 1\.0 ConnectionsRequestStatus.qml/);
assert.match(details,/ConnectionsRequestStatus\.display\(selectedId\)/);
assert.match(details,/RequestDisplayPolicy\.project\(syntheticStatusPreview, selectedId\)/);
assert.match(details,/label: details\.requestStatusOpen[\s\S]*?VIEW REQUEST STATUS/);
assert.match(details,/HOST NOT CONNECTED|NO HOST-VERIFIED REQUESTS ON THIS DESKTOP/);
assert.match(details,/READ-ONLY STATUS \/\/ NO APPROVAL OR REAL GRANT/);
assert.match(details,/onSelectedIdChanged:[\s\S]*?requestStatusOpen = false/);
assert.doesNotMatch(details,/onClicked:\s*ConnectionsBroker\.authorize|Quickshell\.env\(|Qt\.openUrlExternally/);
assert.match(native,/C2G_PASS \/\/ NATIVE_OFFLINE_SIMULATED_STATES_NO_GRANTS/);
assert.match(click,/click STATUS_OPEN/);
assert.match(click,/click STATUS_CLOSE/);
assert.match(click,/C2G_PASS \/\/ NATIVE_OFFLINE_SIMULATED_STATES_NO_GRANTS/);
assert.match(read("services/connections/ConnectionsBroker.qml"),
             /readonly property bool credentialActionsEnabled: false/);

const host=read("services/connections/experiments/C2fFakeRequestLifecycle.py");
for(const field of ["requestId","state","provider","consumer","operation",
                    "profile","reason","expiresInMs","credentialPresent",
                    "realGrantActive","canApproveInProduction","simulated"])
    assert.ok(host.includes('"'+field+'"'),field);
for(const state of ["PENDING","APPROVED","DENIED","CANCELLED","EXPIRED",
                    "COMPLETED","FAILED"])
    assert.ok(host.includes('"'+state+'"'),state);
console.log("C2G_PASS // READONLY_LIFECYCLE_STATUS_SANITIZATION_NATIVE_BOUNDARY");
