#!/usr/bin/env node
"use strict";
// V4 readiness presentation: no claim of production host registration.
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const source=read("services/connections/ConnectionsSignInHostBoundary.js");
const ctx={};
vm.runInNewContext(source.replace(/^\.pragma library\s*/m,""),ctx);
const result=JSON.parse(JSON.stringify(ctx.offline()));
const expected=[
  "canBeginSignIn","canCancel","canRetry","canConnect","canDisconnect","canConnectAll"
];
for(const k of expected)assert.equal(result[k],false,k+" may not be enabled");
assert.equal(result.heading,"SIGN IN LOCKED // TRUSTED HOST REQUIRED");
assert.equal(result.hostStatus,"HOST // NOT ENROLLED");
assert.equal(result.commandStatus,"SIGN-IN CHANNEL // NOT CONNECTED");
assert.equal(result.consentStatus,"CONSENT // NOT VERIFIED");
assert.equal(Object.hasOwn(result,"hostAuthenticated"),false);
assert.equal(Object.hasOwn(result,"session"),false);
assert.equal(Object.hasOwn(result,"token"),false);
assert.equal(Object.hasOwn(result,"receipt"),false);
assert.deepEqual(Object.keys(result).sort(),[
  ...expected,"heading","hostStatus","commandStatus","consentStatus","helpText"
].sort());
for(const code of [source,read("widgets/cpuplus/CpuPlusUniversalSignInHeaderPane.qml")]){
  for(const prohibited of [
      "Process {", "FileView {","Qt.openUrlExternally(",
      "Quickshell.env(", "ConnectionsBroker.authorize(",
      "begin_login(", "requestSignIn(","startLogin(","log_out(",
      "SocialIdentityStore.selectIdentity(", "setCredential(", "grantProvider("
  ]) assert.ok(!code.includes(prohibited),"no direct auth/credential action: "+prohibited);
}
const upper=read("widgets/cpuplus/CpuPlusUniversalSignInHeaderPane.qml");
const cpu=read("widgets/CpuPlusW.qml");
for(const fragment of [
  'import "../../services/connections/ConnectionsSignInHostBoundary.js" as HostBoundary',
  'readonly property var hostBridge: HostBoundary.offline()',
  'text: upperSignIn.hostBridge.heading',
  'text: upperSignIn.hostBridge.hostStatus',
  '+ "\\n" + upperSignIn.hostBridge.commandStatus',
  '+ "\\n" + upperSignIn.hostBridge.consentStatus',
  'text: upperSignIn.signIn.identityStatus',
  'text: upperSignIn.signIn.identityNote',
  'text: upperSignIn.signIn.connectionStatus',
  'text: upperSignIn.signIn.providerStatus',
  'text: upperSignIn.signIn.batchStatus',
  'height: visible ? Math.min(journeyBody.implicitHeight + 4, 204) : 0',
  'label: "OPEN ID MANAGEMENT"',
  'onClicked: upperSignIn.idManagementRequested()',
  'INSPECT LOCAL HOST',
  'onClicked: ConnectionsHostObservation.inspect()',
  '"HIDE SIGN-IN STATUS" : "VIEW SIGN-IN STATUS"',
  '"HIDE REQUEST FLOW" : "VIEW REQUEST FLOW"',
  'available: upperSignIn.journey.canBeginSignIn',
  'available: upperSignIn.signInFlow.canCancel',
  'available: upperSignIn.signInFlow.canRetry',
  'onClicked: contextReader.refresh()',
  'active: upperSignIn.panelActive && upperSignIn.statusExpanded'
]) assert.ok(upper.includes(fragment),"V4 layout or legacy connection lost: "+fragment);
const preStatus=upper.slice(0,upper.indexOf('id: journeyViewport'));
const details=upper.slice(upper.indexOf('id: journeyViewport'));
assert.ok(!preStatus.includes('upperSignIn.signIn.connectionStatus'));
assert.ok(!preStatus.includes('upperSignIn.signIn.providerStatus'));
assert.ok(!preStatus.includes('upperSignIn.signIn.batchStatus'));
assert.ok(details.includes('text: upperSignIn.signIn.connectionStatus'));
assert.ok(details.includes('text: upperSignIn.signIn.batchStatus'));
assert.ok(details.includes('TRUST BOUNDARIES // ALL LOCKED'));
assert.ok(details.includes('CONNECTIONS // READ-ONLY'));
assert.ok(cpu.includes("anchors.top: sharedHeaderLine.bottom"));
assert.ok(cpu.includes("? universalSignInUpperPane.bottom"));
assert.ok(cpu.includes("onIdManagementRequested:"));
assert.ok(!upper.includes("FlowContract.simulate("));
assert.ok(!upper.includes("ConnectionsSignInHostBoundary.authenticated("));
assert.doesNotMatch(upper,/onClicked:\s*.*(?:signInFlow\.can|canBeginSignIn|signInButtonLabel)/);
console.log("CPU++ Universal Sign-In V4 compact UX and fixed-offline host boundary: PASS");
