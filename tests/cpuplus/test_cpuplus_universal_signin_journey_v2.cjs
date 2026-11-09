#!/usr/bin/env node
"use strict";
// V2 read-only Identity Center journey, not an authorization or login client.
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const ctx={};
vm.runInNewContext(read("services/connections/ConnectionsIdentityJourneyPolicy.js")
    .replace(/^\.pragma library\s*/m,""),ctx);
const project=(snapshot,active)=>JSON.parse(JSON.stringify(ctx.project(snapshot,active)));
const gates=["canBeginSignIn","canReconnect","canDisconnect","canConnectAll"];
function locked(output){
    for(const key of gates) assert.equal(output[key],false,key);
    assert.equal(output.hostStep,"01 // TRUSTED SIGN-IN HOST REQUIRED");
    assert.equal(output.signInStep,"02 // SIGN-IN NOT AVAILABLE");
    assert.equal(output.identityStep,"03 // AUTHENTICATED IDENTITY NOT VERIFIED");
    assert.equal(output.providerStep,"04 // PROVIDER CONNECTIONS LOCKED");
    assert.equal(output.signInButtonLabel,"SIGN IN // HOST REQUIRED");
    assert.equal(Object.hasOwn(output,"hostAuthenticated"),false);
    assert.equal(Object.hasOwn(output,"identityAuthenticated"),false);
    assert.equal(Object.hasOwn(output,"signedIn"),false);
}
function fixture(status, orgs, portfolios){
    return {
        schema:"post-apollo.identity.desktop-context-display.v0",
        status:status,
        organizations:orgs||[],
        portfolios:portfolios||[],
        canSwitchOrganization:false
    };
}
const org={organizationId:"private-company-name",
           kind:"llc",scopeGrants:[]};
const context={portfolioId:"private-portfolio-name",
               organizationIds:["private-company-name"]};
const valid=[
    fixture("READY",[org],[context]),
    fixture("NO_MEMBERSHIPS"),
    fixture("SIGNED_OUT"),
    fixture("NOT_CONNECTED"),
    fixture("UNAVAILABLE")
];
locked(project(null,false));
assert.equal(project(null,false).displayStatus,"CONTEXT VIEW // NOT OPEN");
locked(project(null,true));
assert.equal(project(null,true).displayStatus,
             "CONTEXT VIEW // NO VALID RESPONSE YET");
assert.equal(project(valid[0],false).displayStatus,
             "CONTEXT VIEW // NOT OPEN");
const statuses=[
    "CONTEXT VIEW // DATA RETURNED (UNVERIFIED)",
    "CONTEXT VIEW // NO MEMBERSHIPS REPORTED",
    "CONTEXT VIEW // SIGNED OUT REPORTED",
    "CONTEXT VIEW // NOT CONNECTED",
    "CONTEXT VIEW // UNAVAILABLE"
];
valid.forEach((v,i)=>{
    const out=project(v,true);
    locked(out);
    assert.equal(out.displayStatus,statuses[i]);
    assert.doesNotMatch(JSON.stringify(out),
        /private-company-name|private-portfolio-name|identity-1|token|password|credential|bearer|refresh_token|api_hash/i);
});
const bad=[
    [],{},false,"SIGNED_IN","READY",
    { ...valid[0], status:"AUTHENTICATED"},
    { ...valid[0], schema:"post-apollo.identity.production-trust.v1" },
    { ...valid[0], canSwitchOrganization:true},
    { ...valid[0], hostAuthenticated:true },
    { ...valid[0], token:"secret" },
    { ...valid[0], sessionId:"secret" },
    { ...valid[0], organizations:"company" },
    { ...valid[0], portfolios:"account" },
    { ...valid[0], organizations:[] },
    { ...valid[1], organizations:[org] },
    { ...valid[2], organizations:[org] },
    { ...valid[3], portfolios:[context] },
    { ...valid[4], organizations:Array(101).fill(org) },
    { ...valid[0], portfolios:Array(101).fill(context) },
];
for(const v of bad){
    const out=project(v,true);
    locked(out);
    assert.equal(out.displayStatus,"CONTEXT VIEW // INVALID RESPONSE");
}
const upper=read("widgets/cpuplus/CpuPlusUniversalSignInHeaderPane.qml");
const cpu=read("widgets/CpuPlusW.qml");
const existingReader=read("widgets/messanger/IdentityCenterOrganizationDisplayReader.qml");
const existingId=read("widgets/cpuplus/CpuPlusIdVerifiedContextPane.qml");
const overview=read("widgets/cpuplus/CpuPlusSettingsConnectionsOverviewPane.qml");
const providerDetails=read("widgets/cpuplus/CpuPlusSettingsConnectionsDetailsPane.qml");
const broker=read("services/connections/ConnectionsBroker.qml");
for(const str of [
    'import "../messanger"',
    'import "../../services/connections/ConnectionsIdentityJourneyPolicy.js" as JourneyPolicy',
    'property bool panelActive: false',
    'property bool statusExpanded: false',
    'onPanelActiveChanged:',
    'statusExpanded = false;',
    'IdentityCenterOrganizationDisplayReader {',
    'active: upperSignIn.panelActive && upperSignIn.statusExpanded',
    'JourneyPolicy.project(contextReader.snapshot,',
    'label: upperSignIn.statusExpanded',
    '"HIDE SIGN-IN STATUS" : "VIEW SIGN-IN STATUS"',
    'onClicked: upperSignIn.statusExpanded = !upperSignIn.statusExpanded',
    'height: visible ? Math.min(journeyBody.implicitHeight + 4, 184) : 0',
    'text: upperSignIn.journey.displayStatus',
    'text: upperSignIn.journey.displayGuidance',
    'text: upperSignIn.journey.hostStep',
    'label: upperSignIn.journey.signInButtonLabel',
    'available: upperSignIn.journey.canBeginSignIn',
    'label: "REFRESH CONTEXT VIEW"',
    'onClicked: contextReader.refresh()',
    'text: upperSignIn.signIn.identityStatus',
    'label: "OPEN ID MANAGEMENT"',
    'onClicked: upperSignIn.idManagementRequested()',
    'ConnectionsHostObservation.inspect()'
]) assert.ok(upper.includes(str),"missing V2 upper UI "+str);
for(const str of [
    "panelActive: cpuPlusWindow.menuOpen",
    '&& cpuPlusWindow.selectedModeIndex === 6',
    '&& cpuPlusWindow.settingsSubMode === "CONNECTIONS"',
    'anchors.top: sharedHeaderLine.bottom',
    '? universalSignInUpperPane.bottom',
    'onIdManagementRequested:',
    'cpuPlusWindow.selectMode(5);'
]) assert.ok(cpu.includes(str),"missing CPU++ guard "+str);
assert.ok(existingReader.includes("function validDisplay(view)"));
assert.ok(existingReader.includes('snapshotProcess.command = [pythonPath, readerPath, "--json"]'));
assert.ok(existingReader.includes("if (!active)"));
assert.ok(existingId.includes("CHECK HOST CONTEXT"));
assert.ok(overview.includes('text: "CONNECTION INVENTORY"'));
assert.ok(providerDetails.includes('label: "OPEN TELEGRAM"'));
assert.ok(providerDetails.includes('label: "RECHECK SESSION"'));
assert.ok(providerDetails.includes("CpuPlusIdAccountEditor {"));
assert.ok(broker.includes("readonly property bool credentialActionsEnabled: false"));
for(const x of [upper,read("services/connections/ConnectionsIdentityJourneyPolicy.js")]){
    for(const forbidden of [
        "Process {","FileView {","Qt.openUrlExternally(",
        "Quickshell.env(","setCredential(","begin_login(",
        "startLogin(","log_out(","setStatus(","requestGrant(",
        "SocialIdentityStore.selectIdentity(","ConnectionsBroker.authorize("
    ]) assert.ok(!x.includes(forbidden),"no unauthorized auth call "+forbidden);
}
assert.doesNotMatch(upper,/label:\s*"(SIGN IN|CONNECT ALL|DISCONNECT)"/);
console.log("CPU++ Universal Sign-In V2 token-free context status and fail-closed journey: PASS");
