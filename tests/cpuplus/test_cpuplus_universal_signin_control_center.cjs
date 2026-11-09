#!/usr/bin/env node
"use strict";
// Universal Sign-In V1 is a visual integration, not an auth grant.
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const policy={};
vm.runInNewContext(read("services/connections/ConnectionsUnifiedSignInPolicy.js")
    .replace(/^\.pragma library\s*/m,""),policy);
const clean=v=>JSON.parse(JSON.stringify(v));
const inspect=x=>clean(policy.project(x));
const gates=["canBeginSignIn","canConnect","canReconnect","canDisconnect","canConnectAll"];
const inputs=[
 null,undefined,{},[],0,"READY",
 {identityHostConnected:false,identityAuthenticated:true,
  credentialHostAuthenticated:true,credentialActionsEnabled:true,
  operatorConsentAuthenticated:true,localObservationSeen:true},
 {identityHostConnected:true,identityAuthenticated:false,
  credentialHostAuthenticated:true,credentialActionsEnabled:true,
  operatorConsentAuthenticated:true,localObservationSeen:false},
 {identityHostConnected:true,identityAuthenticated:true,
  credentialHostAuthenticated:true,credentialActionsEnabled:true,
  operatorConsentAuthenticated:true,localObservationSeen:true},
 {identityHostConnected:1,identityAuthenticated:1,
  credentialHostAuthenticated:1,credentialActionsEnabled:1,
  operatorConsentAuthenticated:1,localObservationSeen:1}
];
for(const x of inputs){
  const p=inspect(x);
  for(const g of gates) assert.equal(p[g],false,g+" may never be armed in V1");
  assert.equal(typeof p.identityStatus,"string");
  assert.equal(typeof p.connectionStatus,"string");
  assert.equal(p.batchStatus,"CONNECT ALL // UNAVAILABLE");
  assert.equal(p.providerStatus,"CONNECT / RECONNECT / DISCONNECT // UNAVAILABLE");
  assert.doesNotMatch(JSON.stringify(p),/token|password|secret|sessionPath|email/i);
}
assert.equal(inspect({identityHostConnected:false,identityAuthenticated:true}).identityVerified,false);
const allTrue=inputs[8];
assert.equal(inspect(allTrue).identityVerified,true);
assert.equal(inspect(allTrue).prerequisitesObserved,true);
assert.equal(inspect(inputs[9]).identityVerified,false);
assert.equal(inspect({localObservationSeen:true}).connectionStatus,
             "LOCAL HOST OBSERVED // NOT AUTHENTICATED");
assert.equal(inspect({}).connectionStatus,
             "LOCAL CONNECTIONS HOST // NOT VERIFIED");

// Existing authority/owner paths are read, never overwritten.
const overview=read("widgets/cpuplus/CpuPlusSettingsConnectionsOverviewPane.qml");
const cpu=read("widgets/CpuPlusW.qml");
const details=read("widgets/cpuplus/CpuPlusSettingsConnectionsDetailsPane.qml");
const broker=read("services/connections/ConnectionsBroker.qml");
const host=read("services/connections/ConnectionsHostObservation.qml");
const request=read("services/connections/ConnectionsRequestStatus.qml");
const idView=read("widgets/cpuplus/CpuPlusIdVerifiedContextPane.qml");
const policySource=read("services/connections/ConnectionsUnifiedSignInPolicy.js");
for(const s of [
 'signal idManagementRequested()',
 'text: "UNIVERSAL SIGN-IN // CONTROL"',
 'text: overview.signIn.identityStatus',
 'text: overview.signIn.connectionStatus',
 'text: overview.signIn.providerStatus',
 'text: overview.signIn.batchStatus',
 'label: "OPEN ID MANAGEMENT"',
 'onClicked: overview.idManagementRequested()',
 'INSPECT LOCAL HOST',
 'onClicked: ConnectionsHostObservation.inspect()',
 'identityHostConnected: false',
 'identityAuthenticated: false',
 'credentialHostAuthenticated: ConnectionsRequestStatus.hostAuthenticated',
 'credentialActionsEnabled: ConnectionsBroker.credentialActionsEnabled',
 'operatorConsentAuthenticated: ConnectionsRequestStatus.canApprove'
]) assert.ok(overview.includes(s),s);
assert.ok(cpu.includes("onIdManagementRequested:"));
assert.ok(cpu.includes("cpuPlusWindow.selectMode(5);"));
assert.ok(cpu.includes('cpuPlusWindow.selectLocalManagementSection("IDS");'));
assert.ok(cpu.includes('cpuPlusWindow.settingsSubMode === "CONNECTIONS"'));
assert.ok(idView.includes("CHECK HOST CONTEXT"));
assert.ok(details.includes("CpuPlusIdAccountEditor {"));
assert.ok(details.includes('label: "OPEN TELEGRAM"'));
assert.ok(details.includes('label: "RECHECK SESSION"'));
assert.match(broker,/readonly property bool credentialActionsEnabled: false/);
assert.match(request,/readonly property bool hostAuthenticated: false/);
assert.match(request,/readonly property bool canApprove: false/);
assert.match(host,/readonly property bool hostAuthenticated: false/);
assert.match(host,/readonly property bool credentialActionsEnabled: false/);
for(const src of [overview,policySource]){
  for(const forbidden of [
    "createIdentity(","selectIdentity(","log_out(","startLogin(",
    "begin_login(","ConnectionsBroker.approve(","setCredential(",
    "SocialIdentityStore.selectIdentity(","Qt.openUrlExternally(",
    "Quickshell.env(","Process {","FileView {","session.unlink("
  ]) assert.ok(!src.includes(forbidden),"UI may not mutate auth: "+forbidden);
}
assert.doesNotMatch(overview,/label:\s*"(?:SIGN IN|CONNECT ALL|DISCONNECT|APPROVE ACCESS)"/);
console.log("CPU++ Universal Sign-In visual integration: fail-closed gates and real UI navigation PASS");
