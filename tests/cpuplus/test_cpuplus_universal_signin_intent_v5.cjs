#!/usr/bin/env node
"use strict";
// No network, host command, QML actuator, credential, file write or login.
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const src=read("services/connections/ConnectionsSignInIntentProposal.js");
const context={};
vm.runInNewContext(src.replace(/^\.pragma library\s*/m,""),context);
const inspect=v=>JSON.parse(JSON.stringify(context.review(v)));
const schema="post-apollo.identity.command-intent.proposed-v0";
const id="HOST_MINTED_REQ_0001";
const candidate=(action,requestId)=>({schema,action,requestId});
const good=[candidate("BEGIN",null),candidate("CANCEL",id),candidate("RECOVER",id)];
const rejected=[
 null,undefined,false,0,[],{}, "BEGIN",
 candidate("BEGIN",id),candidate("CANCEL",null),candidate("RECOVER",null),
 candidate("OTHER",id), candidate("SIGN_IN",null), candidate("LOGIN",null),
 candidate("DISCONNECT",id), candidate("CONNECT_ALL",null),
 candidate("BEGIN",0), candidate("CANCEL",false),
 candidate("RECOVER",{}),candidate("CANCEL","test"),
 candidate("CANCEL","../outside"),candidate("CANCEL","x".repeat(97)),
 candidate("CANCEL","x".repeat(15)),candidate("CANCEL","has space___________"),
 {...candidate("BEGIN",null),token:"secrets"},
 {...candidate("BEGIN",null),issuer:"https://untrusted"},
 {...candidate("BEGIN",null),url:"https://untrusted"},
 {...candidate("BEGIN",null),hostAuthenticated:true},
 {...candidate("BEGIN",null),consentVerified:true},
 {...candidate("CANCEL",id),password:"secret"},
 {...candidate("RECOVER",id),nonce:"secret"},
 {...candidate("RECOVER",id),sequence:1},
 {...candidate("CANCEL",id),accessToken:"secret"},
 {...candidate("BEGIN",null),schema:"post-apollo.identity.command-intent.v1"}
];
function locked(result,expected){
    assert.equal(result.shape,expected);
    assert.equal(result.authority,"NONE");
    for(const k of [
       "hostAuthenticated","operatorConsentVerified","canDispatch",
       "canBeginSignIn","canCancel","canRecover","canConnectProvider"
    ]) assert.equal(result[k],false,k);
    assert.equal(result.note,"OWNER-REVIEWED HOST COMMAND INTERFACE NOT INSTALLED");
    assert.deepEqual(Object.keys(result).sort(),[
       "shape","authority","hostAuthenticated","operatorConsentVerified",
       "canDispatch","canBeginSignIn","canCancel","canRecover",
       "canConnectProvider","note"
    ].sort());
    assert.doesNotMatch(JSON.stringify(result),/HOST_MINTED_REQ|password|bearer|accessToken|https:/i);
}
for(const x of good)locked(inspect(x),"CANDIDATE_ONLY");
for(const x of rejected)locked(inspect(x),"REJECTED");
assert.equal(context.compatibleShape(candidate("BEGIN",null)),true);
assert.equal(context.compatibleShape(candidate("CANCEL",id)),true);
assert.equal(context.compatibleShape(candidate("RECOVER",id)),true);
// Even syntactically valid "CANCEL" cannot assert current request ownership;
// this remains an owner-reviewed proposal and can never dispatch.
for(const x of good)assert.equal(inspect(x).canDispatch,false);
const current=read("widgets/cpuplus/CpuPlusUniversalSignInHeaderPane.qml");
const bridge=read("services/connections/ConnectionsSignInHostBoundary.js");
const request=read("services/connections/ConnectionsRequestStatus.qml");
const broker=read("services/connections/ConnectionsBroker.qml");
const flow=read("services/connections/ConnectionsSignInFlowContract.js");
assert.ok(bridge.includes("canBeginSignIn: false"));
assert.ok(bridge.includes("canCancel: false"));
assert.ok(bridge.includes("canRetry: false"));
assert.ok(request.includes("readonly property bool hostAuthenticated: false"));
assert.ok(request.includes("readonly property bool canApprove: false"));
assert.ok(broker.includes("readonly property bool credentialActionsEnabled: false"));
assert.ok(flow.includes("function simulate(prev, event)"));
assert.ok(flow.includes("simulated: true"));
assert.ok(current.includes('label: "OPEN ID MANAGEMENT"'));
assert.ok(current.includes("ConnectionsHostObservation.inspect()"));
assert.ok(current.includes("available: upperSignIn.journey.canBeginSignIn"));
assert.ok(current.includes("available: upperSignIn.signInFlow.canCancel"));
assert.ok(current.includes("available: upperSignIn.signInFlow.canRetry"));
assert.ok(current.includes("readonly property var hostBridge: HostBoundary.offline()"));
assert.ok(!current.includes("ConnectionsSignInIntentProposal.js"));
assert.ok(!current.includes("ConnectionsSignInIntentProposal.review("));
for(const c of [src,current]){
  for(const prohibited of [
    "Process {","FileView {","Qt.openUrlExternally(",
    "Quickshell.env(","log_out(","startLogin(","requestSignIn(",
    "ConnectionsBroker.authorize(","setCredential(","sendCommand(",
    "transmit(","fetch(","SocialIdentityStore.selectIdentity("
  ])assert.ok(!c.includes(prohibited),"unexpected command/secret action "+prohibited);
}
console.log("Universal Sign-In V5 command candidate: strictly review-only; no live host/consent/credential authority PASS");
