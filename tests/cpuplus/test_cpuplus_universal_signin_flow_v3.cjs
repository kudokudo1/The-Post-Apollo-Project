#!/usr/bin/env node
"use strict";
// Pure contract simulations. No host, token, real login, provider or network.
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const contractSource=read("services/connections/ConnectionsSignInFlowContract.js");
const ctx={};
vm.runInNewContext(contractSource.replace(/^\.pragma library\s*/m,""),ctx);
const copy=v=>v==null?v:JSON.parse(JSON.stringify(v));
const flow=()=>copy(ctx.offline());
const test=(s,e)=>copy(ctx.simulate(s,e));
const id="HOST_MINTED_REQ_0001";
const event=(phase,sequence,reason="NONE",requestId=id)=>({
    schema:"post-apollo.identity.signin-event.v0",
    requestId,sequence,phase,reason
});
const locked=()=>{
    const a=flow();
    assert.equal(a.label,"SIGN-IN COMMAND CHANNEL // NOT CONNECTED");
    assert.equal(a.requestLabel,"REQUEST // NONE (NO TRUSTED HOST)");
    assert.equal(a.stages.length,6);
    for(const key of ["canRequest","canCancel","canRetry","canConnect","canConnectAll"])
        assert.equal(a[key],false,key);
    assert.doesNotMatch(JSON.stringify(a),/HOST_MINTED_REQ|password|token|bearer|credential|userId|grant/i);
};
locked();
let a=test(null,event("REQUESTED",1));
assert.equal(a.phase,"REQUESTED");
assert.equal(a.simulated,true);
assert.equal(test(null,event("WAITING_FOR_USER",1)),null);
assert.equal(test(null,event("REQUESTED",2)),null);
assert.equal(test(a,event("REQUESTED",2)),null);
assert.equal(test(a,event("VERIFYING",3)),null);
assert.equal(test(a,event("WAITING_FOR_USER",1)),null);
assert.equal(test(a,event("WAITING_FOR_USER",2,"NONE","DIFFERENT_HOST_REQ")),null);
let b=test(a,event("WAITING_FOR_USER",2));
assert.equal(b.phase,"WAITING_FOR_USER");
let c=test(b,event("VERIFYING",3));
assert.equal(c.phase,"VERIFYING");
let d=test(c,event("AUTHENTICATED",4));
assert.equal(d.phase,"AUTHENTICATED");
assert.equal(d.simulated,true);
assert.equal(test(d,event("REQUESTED",5)),null);
assert.equal(test(d,event("CANCELLED",5,"USER_CANCELLED")),null);
assert.equal(test(c,event("AUTHENTICATED",4,"AUTH_FAILED")),null);
for(const [phase,reason] of [
    ["DENIED","CONSENT_DENIED"],["CANCELLED","USER_CANCELLED"],
    ["EXPIRED","EXPIRED"],["FAILED","AUTH_FAILED"],["HOST_LOST","HOST_LOST"]
]){
    const terminal=test(b,event(phase,3,reason));
    assert.equal(terminal.phase,phase);
    assert.equal(terminal.simulated,true);
    assert.equal(test(terminal,event("REQUESTED",4)),null);
    assert.equal(test(b,event(phase,3)),null);
}
assert.equal(test(c,event("DENIED",4,"CONSENT_DENIED")),null);
assert.equal(test(c,event("CANCELLED",4,"USER_CANCELLED")),null);
// Recovery is a *new*, separately host-minted REQUESTED event, never an
// implicit retry of a finished/cancelled request.
const otherId="HOST_MINTED_REQ_0002";
assert.equal(test(b,event("REQUESTED",3,"NONE",otherId)),null);
const fresh=test(null,event("REQUESTED",1,"NONE",otherId));
assert.equal(fresh.requestId,otherId);
for(const bad of [
    null,undefined,[],false,0,"READY",{},
    {...event("REQUESTED",1),token:"SECRET"},
    {...event("REQUESTED",1),clientId:"untrusted-client"},
    {...event("REQUESTED",1),hostAuthenticated:true},
    {...event("REQUESTED",1),consentApproved:true},
    {...event("REQUESTED",1),requestId:"too-short"},
    {...event("REQUESTED",1),requestId:"../../outside/safe"},
    {...event("REQUESTED",1),requestId:"x".repeat(97)},
    {...event("REQUESTED",1),requestId:23},
    {...event("REQUESTED",1),sequence:0},
    {...event("REQUESTED",1),sequence:1.1},
    {...event("REQUESTED",1),sequence:Number.MAX_SAFE_INTEGER+2},
    {...event("REQUESTED",1),phase:"SIGNED_IN"},
    {...event("REQUESTED",1),phase:"READY"},
    {...event("REQUESTED",1),reason:"CONSENT_DENIED"},
    {...event("FAILED",1,"AUTH_FAILED"),reason:"PASSWORD_REQUIRED"},
    {...event("REQUESTED",1),schema:"post-apollo.identity.signin-event.v9"}
]) assert.equal(test(null,bad),null,"must reject forged/malformed event");
assert.equal(test({requestId:id,sequence:1,phase:"REQUESTED",simulated:false},
                  event("WAITING_FOR_USER",2)),null);
assert.equal(test({requestId:id,sequence:1,phase:"REQUESTED",simulated:true,secret:"oops"},
                  event("WAITING_FOR_USER",2)),null);

const upper=read("widgets/cpuplus/CpuPlusUniversalSignInHeaderPane.qml");
const cpu=read("widgets/CpuPlusW.qml");
const old=read("services/connections/ConnectionsUnifiedSignInPolicy.js");
const v2=read("services/connections/ConnectionsIdentityJourneyPolicy.js");
for(const fragment of [
    'import "../../services/connections/ConnectionsSignInFlowContract.js" as FlowContract',
    'property bool flowExpanded: false',
    'readonly property var signInFlow: FlowContract.offline()',
    'onStatusExpandedChanged:',
    'flowExpanded = false;',
    'label: upperSignIn.flowExpanded',
    '"HIDE REQUEST FLOW" : "VIEW REQUEST FLOW"',
    'onClicked: upperSignIn.flowExpanded = !upperSignIn.flowExpanded',
    'model: upperSignIn.signInFlow.stages',
    'text: upperSignIn.signInFlow.label',
    'text: upperSignIn.signInFlow.requestLabel',
    'label: "CANCEL // UNAVAILABLE"',
    'available: upperSignIn.signInFlow.canCancel',
    'label: "RETRY // UNAVAILABLE"',
    'available: upperSignIn.signInFlow.canRetry',
    'available: upperSignIn.journey.canBeginSignIn',
    'onClicked: upperSignIn.idManagementRequested()',
    'onClicked: contextReader.refresh()',
    'IdentityCenterOrganizationDisplayReader {'
]) assert.ok(upper.includes(fragment),"missing V3 UI "+fragment);
assert.ok(cpu.includes("anchors.top: sharedHeaderLine.bottom"));
assert.ok(cpu.includes("? universalSignInUpperPane.bottom"));
assert.ok(cpu.includes("onIdManagementRequested:"));
assert.ok(cpu.includes("panelActive: cpuPlusWindow.menuOpen"));
assert.ok(old.includes("canBeginSignIn: false"));
assert.ok(v2.includes("canBeginSignIn: false"));
for(const source of [contractSource,upper]){
    for(const forbidden of ["Process {","FileView {","Qt.openUrlExternally(",
        "Quickshell.env(","begin_login(","requestSignIn(","setCredential(",
        "log_out(","ConnectionsBroker.authorize(","SocialIdentityStore.selectIdentity("])
        assert.ok(!source.includes(forbidden),"no auth actor "+forbidden);
}
assert.doesNotMatch(upper,/onClicked:\s*.*(?:signInFlow\.can|canBeginSignIn|signInButtonLabel)/);
locked();
console.log("CPU++ Universal Sign-In V3 strict host-event lifecycle, replay/host-loss and disabled actions: PASS");
