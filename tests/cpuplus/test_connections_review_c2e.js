#!/usr/bin/env node
"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=name=>fs.readFileSync(path.join(root,name),"utf8");
function library(name){
    const context={};
    vm.runInNewContext(read(name).replace(/^\.pragma library\s*/m,""),context);
    return context;
}
const broker=library("services/connections/ConnectionsBrokerPolicy.js");
const review=library("services/connections/ConnectionsReviewPolicy.js");
function plain(x){return JSON.parse(JSON.stringify(x));}
const nasa=review.preview(broker.requirement("nasa-firms"));
assert.deepEqual(plain(nasa),{
  known:true,phase:"REVIEW_ONLY",provider:"nasa-firms",
  operations:["fires.hotspots.read"],consumers:["weather-earth"],
  authentication:"HOST IDENTITY + OPERATOR CONSENT REQUIRED",
  canApprove:false,hasActiveGrant:false,
  status:"NOT AUTHORIZED // HOST APPROVAL NOT CONNECTED"
});
const mail=review.preview(broker.requirement("proton-mail"));
assert.deepEqual(plain(mail.operations),["mail.read","mail.send","mail.modify"]);
assert.deepEqual(plain(mail.consumers),["social-mail","notifications-mail"]);
assert.equal(mail.canApprove,false);
assert.equal(mail.hasActiveGrant,false);
for(const invalid of [null, {}, {known:true,provider:"__proto__",grantEnabled:false,
                                    operations:[],consumers:[]},
    {...broker.requirement("nasa-firms"),grantEnabled:true},
    {...broker.requirement("nasa-firms"),operations:["mail.read"]},
    {...broker.requirement("nasa-firms"),consumers:["social-mail"]},
    {...broker.requirement("proton-mail"),operations:["mail.send","mail.read","mail.modify"]}
]) {
    const state=review.preview(invalid);
    assert.equal(state.known,false);
    assert.equal(state.canApprove,false);
}
for(const state of [nasa,mail,review.preview(null)]) {
    for(const choice of ["approve","deny","close",true,1,null,{}]) {
        const decision=review.decision(state,choice);
        assert.equal(decision.allowed,false);
    }
}
assert.equal(review.decision(nasa,"approve").reason,"HOST_CONSENT_NOT_CONNECTED");
assert.equal(review.decision(nasa,"deny").reason,"REVIEW_DISMISSED");

const details=read("widgets/cpuplus/CpuPlusSettingsConnectionsDetailsPane.qml");
assert.match(details,/ConnectionsReviewPolicy\.js" as ReviewPolicy/);
assert.match(details,/readonly property var permissionPreview: ReviewPolicy\.preview\(keyRequirement\)/);
assert.match(details,/label: "REVIEW ACCESS"/);
assert.match(details,/label: "DISMISS REVIEW"/);
assert.match(details,/label: "APPROVE \/\/ UNAVAILABLE"[\s\S]*?available: false/);
assert.match(details,/permissionReviewOpen = false/);
assert.match(details,/REVIEW CLOSED \/\/ NO ACCESS GRANTED/);
assert.match(details,/onSelectedIdChanged:\s*\{[\s\S]*?permissionReviewOpen = false/);
assert.match(details,/HOST APPROVAL, SECRET STORAGE, ACCOUNT LOGIN AND CROSS-APP GRANTS REMAIN DISABLED/);
assert.doesNotMatch(details,/ConnectionsBroker\.authorize\(\s*\{|\bsecretTool\b|Qt\.openUrlExternally|WriteCredential|onClicked:\s*ConnectionsBroker\.authorize/);
const native=read("tests/cpuplus/fixtures/C1ConnectionsNative.qml");
const shell=read("scripts/cpuplus/verify_connections_native_c1.sh");
assert.match(native,/C2E_PASS \/\/ NATIVE_ACCESS_REVIEW_DISMISS_NO_GRANT/);
assert.match(native,/if \(!preview\.known[\s\S]*?preview\.canApprove[\s\S]*?approve\.available/);
assert.match(shell,/click REVIEW_ACCESS/);
assert.match(shell,/click DISMISS_REVIEW/);
assert.match(shell,/C2E_PASS \/\/ NATIVE_ACCESS_REVIEW_DISMISS_NO_GRANT/);
const prod=read("services/connections/ConnectionsBroker.qml");
assert.match(prod,/readonly property bool credentialActionsEnabled: false/);
assert.match(read("services/connections/ConnectionsBrokerPolicy.js"),
             /TRUSTED_BROKER_NOT_ACTIVATED/);
console.log("C2E_PASS // PERMISSION_REVIEW_NO_GRANTS_UI_AND_BROKER_BOUNDARY");
