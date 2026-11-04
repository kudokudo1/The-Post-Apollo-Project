#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const root = path.resolve(__dirname,"../..");
const read = p => fs.readFileSync(path.join(root,p),"utf8");
const policy={};
vm.runInNewContext(
    read("services/connections/ConnectionsHostStatusPolicy.js")
        .replace(/^\.pragma library\s*/m,""),policy);
const plain=x=>JSON.parse(JSON.stringify(x));
const statuses=[
    "NOT_CHECKED","CHECKING","RUNTIME_UNAVAILABLE","RUNTIME_UNSAFE",
    "HOST_NOT_FOUND","HOST_UNAVAILABLE","PEER_UNVERIFIED",
    "RESPONSE_INVALID","OBSERVED_UNVERIFIED"
];
const base={
    status:"OBSERVED_UNVERIFIED",provider:"nasa-firms",state:"PENDING",
    hostAuthenticated:false,credentialPresent:false,grantActive:false,
    canApprove:false,
};
assert.deepEqual(plain(policy.offline()),{
    status:"NOT_CHECKED",label:"LOCAL HOST NOT INSPECTED",state:"",
    stateLabel:"",hostAuthenticated:false,grantActive:false,
    canApprove:false,observationOnly:true
});
for(const state of ["IDLE","PENDING","APPROVED","DENIED","CANCELLED",
                    "EXPIRED","COMPLETED","FAILED"]) {
    const v=policy.project({...base,state});
    assert.equal(v.status,"OBSERVED_UNVERIFIED");
    assert.equal(v.state,state);
    assert.equal(v.stateLabel,"OBSERVED // "+state+" // UNVERIFIED");
    assert.equal(v.hostAuthenticated,false);
    assert.equal(v.grantActive,false);
    assert.equal(v.canApprove,false);
    assert.equal(v.observationOnly,true);
}
for(const status of statuses.filter(x=>x!=="OBSERVED_UNVERIFIED")) {
    const v=policy.project({...base,status,state:""});
    assert.equal(v.status,status);
    assert.equal(v.state,"");
    assert.equal(v.grantActive,false);
}
for(const record of [
    null,[],{},'OBSERVED_UNVERIFIED',
    {...base,status:"CONNECTED"},
    {...base,status:"__proto__"},
    {...base,state:"CONNECTED"},
    {...base,state:"__proto__"},
    {...base,provider:"proton-mail"},
    {...base,hostAuthenticated:true},
    {...base,credentialPresent:true},
    {...base,canApprove:true},
    {...base,grantActive:true},
    {...base,token:"sensitive"},
    {...base,requestId:"ab".repeat(16)},
    {...base,status:"HOST_NOT_FOUND",state:"PENDING"},
]) {
    assert.equal(policy.project(record).status,"RESPONSE_INVALID");
}
const singleton=read("services/connections/ConnectionsHostObservation.qml");
const python=read("services/connections/ConnectionsHostStatusInspect.py");
const pane=read("widgets/cpuplus/CpuPlusSettingsConnectionsDetailsPane.qml");
const qmldir=read("services/connections/qmldir");
const legacy=read("services/connections/ConnectionsRequestStatus.qml");
const broker=read("services/connections/ConnectionsBroker.qml");
assert.match(singleton,/pragma Singleton/);
assert.match(qmldir,/singleton ConnectionsHostObservation 1\.0 ConnectionsHostObservation\.qml/);
assert.match(singleton,/readonly property bool hostAuthenticated: false/);
assert.match(singleton,/readonly property bool credentialActionsEnabled: false/);
assert.match(singleton,/function inspect\(\)/);
assert.match(singleton,/host\.exec\(\[/);
assert.match(singleton,/ConnectionsHostStatusInspect\.py/);
assert.match(singleton,/Policy\.project\(source\)/);
assert.match(singleton,/rawResult = ""/);
assert.doesNotMatch(singleton,/onCompleted\s*:|secret-tool|stdinEnabled: true|host\.write\(/i);
assert.match(pane,/label: ConnectionsHostObservation\.checking/);
assert.match(pane,/INSPECT LOCAL HOST/);
assert.match(pane,/onClicked: ConnectionsHostObservation\.inspect\(\)/);
assert.match(pane,/ConnectionsHostObservation\.observation\.stateLabel/);
assert.match(pane,/NO KEYS OR PERMISSIONS SHARED/);
assert.match(python,/SO_PEERCRED/);
assert.match(python,/sock\.sendall\(REQUEST\)/);
assert.match(legacy,/readonly property bool hostConnected: false/);
assert.match(legacy,/readonly property bool hostAuthenticated: false/);
assert.match(legacy,/readonly property var latestStatus: null/);
assert.match(broker,/readonly property bool credentialActionsEnabled: false/);
assert.match(read("services/connections/ConnectionsBrokerPolicy.js"),
             /TRUSTED_BROKER_NOT_ACTIVATED/);
assert.doesNotMatch(pane,/onClicked:\s*ConnectionsBroker\.authorize|Qt\.openUrlExternally/i);
console.log("C2I_PASS // HOST_INSPECTION_UI_SCHEMA_AND_PRODUCTION_GRANTS_CLOSED");
