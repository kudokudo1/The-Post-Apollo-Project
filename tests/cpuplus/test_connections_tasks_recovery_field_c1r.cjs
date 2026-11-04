#!/usr/bin/env node
"use strict";
// C1r // new TASKS recovery entry in standard CPU++ Connections card.
// Never auth, read or write credentials. Uses synthetic status strings only.
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=n=>fs.readFileSync(path.join(root,n),"utf8");
const policy={};
vm.runInNewContext(read("services/connections/ConnectionsPolicy.js")
    .replace(/^\.pragma library\s*/m,""),policy);
const off={
    tasksProviderStatus:"NOT CHECKED",tasksProviderChecking:false,
    tasksBrokerActionsEnabled:false,tasksRecoveryEnabled:false,
    tasksRecoveryStorageAuthorized:false,tasksRecoveryUnlockAuthorized:false,
    tasksDraftHostEnabled:false,tasksDraftHostWriteAuthorized:false
};
function row(data={}) {
    return JSON.parse(JSON.stringify(policy.find(policy.build({...off,...data}),
                                              "tasks-recovery")));
}
test("TASKS uses the identical Connections tile + details data schema",()=>{
    const all=JSON.parse(JSON.stringify(policy.build(off)));
    assert.equal(all.length,8);
    assert.deepEqual(all.map(x=>x.id),[
        "social","notifications","tasks-recovery","proton-mail",
        "nasa-firms","bbc-world","al-jazeera-english","gdelt"
    ]);
    for(const x of all) {
        assert.deepEqual(Object.keys(x),[
            "id","title","status","kind","accent","detail","context",
            "consumers","permissions","setup","action"
        ]);
    }
    const x=row();
    assert.equal(x.title,"TASKS // DRAFT RECOVERY");
    assert.equal(x.status,"RECOVERY // OFF");
    assert.equal(x.kind,"local");
    assert.equal(x.accent,"orange");
    assert.match(x.permissions,/ENCRYPTED DRAFT CAPTURE/);
    assert.match(x.permissions,/UNLOCK AND PREVIEW/);
    assert.match(x.permissions,/SCOPED DELETE \(DISABLED\)/);
    assert.match(x.setup,/TASKS > SYNC > RECOVERY/);
    assert.equal(policy.counters(all).keyRequired,1);
    assert.equal(policy.counters(all).publicSources,3);
});
test("only real shared C2 status labels appear, never raw provider text",()=>{
    const expected={
        "NOT CHECKED":"KEYRING // NOT CHECKED",
        "SERVICE_ACQUIRED":"KEYRING FOUND // UNLOCK UNKNOWN",
        "SERVICE_NOT_RUNNING":"KEYRING SERVICE // NOT RUNNING",
        "SESSION_BUS_UNAVAILABLE":"KEYRING // SESSION BUS UNAVAILABLE",
        "DBUS_PROBE_TOOL_MISSING":"KEYRING // PROBE TOOL MISSING"
    };
    for(const [status,label] of Object.entries(expected)) {
        const x=row({tasksProviderStatus:status});
        assert.equal(x.detail,label);
        assert.equal(x.status,"RECOVERY // OFF");
    }
    for(const status of [
        "<SECRET_KEY>", "SERVICE_ACQUIRED\nAUTH=TRUE", "VALID TOKEN",
        "AUTHORIZATION_GRANTED", null, 42, {}, [], undefined
    ]) {
        const x=row({tasksProviderStatus:status});
        assert.equal(x.detail,"KEYRING // STATUS UNVERIFIED");
        assert.equal(JSON.stringify(x).includes("<SECRET_KEY>"),false);
    }
    assert.equal(row({tasksProviderStatus:"SERVICE_ACQUIRED",
        tasksProviderChecking:true}).detail,"KEYRING // CHECKING");
});
test("all unexpected broker or TASKS flags result in REVIEW, never READY",()=>{
    const flags=[
        "tasksBrokerActionsEnabled","tasksRecoveryEnabled",
        "tasksRecoveryStorageAuthorized","tasksRecoveryUnlockAuthorized",
        "tasksDraftHostEnabled","tasksDraftHostWriteAuthorized"
    ];
    for(const f of flags){
        const x=row({tasksProviderStatus:"SERVICE_ACQUIRED",[f]:true});
        assert.equal(x.status,"RECOVERY // STATE REQUIRES REVIEW");
        assert.match(x.context,/GRANTS CLOSED/);
        assert.doesNotMatch(JSON.stringify(x),/RECOVERY READY|KEY RELEASED/);
    }
    assert.equal(row({tasksProviderStatus:"SERVICE_ACQUIRED",
        tasksRecoveryEnabled:undefined}).status,
        "RECOVERY // STATE REQUIRES REVIEW");
    assert.equal(JSON.stringify(row({tasksProviderStatus:"SERVICE_ACQUIRED"}))
        .includes("UNLOCK UNKNOWN"),true);
});
test("registry binds read-only canonical owners and never stores a TASKS key",()=>{
    const registry=read("services/connections/ConnectionsRegistry.qml");
    const broker=read("services/connections/ConnectionsBroker.qml");
    const saved=read("services/hub/ApolloHubTodoStore.qml");
    assert.match(registry,/import qs\.services\.hub/);
    assert.match(registry,/ConnectionsBroker\.status/);
    assert.match(registry,/ConnectionsBroker\.checking/);
    assert.match(registry,/ConnectionsBroker\.credentialActionsEnabled/);
    for(const n of [
        "encryptedRecoveryEnabled","encryptedRecoveryStorageAuthorized",
        "encryptedRecoveryUnlockAuthorized","encryptedDraftHostEnabled",
        "encryptedDraftHostWriteAuthorized"
    ]) {
        assert.match(registry,new RegExp("ApolloHubTodoStore\\."+n));
        assert.match(saved,new RegExp("readonly property bool "+n+":\\s*false"));
    }
    assert.match(broker,/readonly property bool credentialActionsEnabled: false/);
    assert.doesNotMatch(registry,/FileView\s*\{|Process\s*\{|setText\(|writeFile|secret-tool|OpenSession/);
    assert.equal((saved.match(/\bFileView\s*\{/g)||[]).length,1);
    assert.equal((saved.match(/\btodoFile\.setText\s*\(/g)||[]).length,1);
});
test("same ListPane/DetailsPane style and explicit probe, no fake click-to-grant",()=>{
    const list=read("widgets/cpuplus/CpuPlusSettingsConnectionsListPane.qml");
    const details=read("widgets/cpuplus/CpuPlusSettingsConnectionsDetailsPane.qml");
    const overview=read("widgets/cpuplus/CpuPlusSettingsConnectionsOverviewPane.qml");
    const cpu=read("widgets/CpuPlusW.qml");
    assert.match(list,/model: ConnectionsRegistry\.rows/);
    assert.match(list,/sourceChoice\.modelData\.title/);
    assert.match(list,/sourceChoice\.modelData\.status/);
    assert.match(list,/selected: selector\.selectedId === modelData\.id/);
    assert.match(list,/onClicked: selector\.providerSelected\(modelData\.id\)/);
    assert.match(details,/ConnectionsRegistry\.entry\(selectedId\)/);
    assert.match(details,/details\.selectedId === "tasks-recovery"/);
    assert.match(details,/text: details\.source \? details\.source\.detail/);
    assert.match(details,/TASKS RECOVERY \/\/ SECURITY STATUS/);
    assert.match(details,/CHECKPOINT DELETE \/\/ DISABLED/);
    assert.match(details,/onClicked: ConnectionsBroker\.checkAvailability\(\)/);
    assert.match(details,/available: !ConnectionsBroker\.checking/);
    assert.match(details,/READ ONLY \/\/ KEYRING PRESENCE DOES NOT PROVE UNLOCK OR APPROVAL/);
    assert.match(details,/GohuText\s*\{/);
    assert.match(details,/QuietText\s*\{/);
    assert.match(details,/ActionButton\s*\{/);
    assert.match(details,/Rectangle \{width:parent\.width; height:1; color:Colors\.cyan\}/);
    assert.match(cpu,/selectedConnectionId = providerId/);
    assert.match(overview,/CONNECTIONS \/\/ SHARED CONTROL/);
    for(const q of [list,details,overview,cpu]){
        assert.doesNotMatch(q,/Qt\.openUrlExternally\(/);
    }
    assert.doesNotMatch(details,/secret-tool|ConnectionsBroker\.authorize\(|TaskEncryptedDraftHostM13k|TaskEncryptedRecoveryBridgeM13i/);
});
