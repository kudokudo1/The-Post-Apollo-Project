#!/usr/bin/env node
"use strict";

// C1 contracts are read-only. Real mailbox auth and key broker are NOT here.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.resolve(__dirname, "../..");
const read = pathName => fs.readFileSync(path.join(root, pathName), "utf8");

const policy = {};
vm.runInNewContext(
    read("services/connections/ConnectionsPolicy.js")
        .replace(/^\.pragma library\s*/m, ""), policy
);
const socials = {
    socialState: "ready",
    socialSnapshot: {activeId:"identity-2",activeName:"Research",
                     identities:[{id:"identity-2",name:"Research"}]},
    socialAccountState: "ready",
    socialAccounts: {
        identities: {
            "identity-2": {
                email: "not-to-be-displayed@example.test",
                phone: "123456789",
                accounts: {
                    discord: [{id:"account-1",label:"Personal"},
                              {id:"account-2",label:"Work"}],
                    telegram: "Family"
                }
            }
        }
    },
    notificationsReady: true,
    firmsKeyPresent: false
};
let rows = policy.build(socials);
assert.equal(rows.length, 7);
assert.equal(new Set(rows.map(x=>x.id)).size, 7);
assert.equal(policy.find(rows,"social").status,"LAYOUT READY");
assert.match(policy.find(rows,"social").detail,/Research/);
assert.equal(policy.find(rows,"social").context,"SAVED ACCOUNT NAMES // 3");
assert.equal(policy.find(rows,"notifications").status,"LOCAL ENGINE READY");
assert.equal(policy.find(rows,"proton-mail").status,"ADAPTER NOT CONNECTED");
assert.equal(policy.find(rows,"nasa-firms").status,"KEY REQUIRED");
assert.equal(policy.find(rows,"bbc-world").status,"PUBLIC // ON DEMAND");
assert.equal(policy.find(rows,"al-jazeera-english").status,"PUBLIC // ON DEMAND");
assert.equal(policy.find(rows,"gdelt").status,"PUBLIC // RATE LIMITS");
assert.equal(policy.find(rows,"unknown"),null);
assert.deepEqual(JSON.parse(JSON.stringify(policy.counters(rows))), {
    keyRequired:1, unverifiedAccounts:1, publicSources:3
});
assert.doesNotMatch(JSON.stringify(rows),/not-to-be-displayed@example\.test|123456789|Personal|Work|Family/);
assert.doesNotMatch(JSON.stringify(rows),/TOKEN|SECRET VALUE|API KEY CONTENT/i);

rows = policy.build({...socials, firmsKeyPresent:true});
assert.equal(policy.find(rows,"nasa-firms").status,
             "KEY PRESENT // UNVERIFIED");
assert.equal(policy.counters(rows).keyRequired,0);
rows = policy.build({...socials,
    socialState:"error", socialSnapshot:{activeName:"Stale",
                                       activeId:"identity-2"},
    socialAccountState:"error", notificationsReady:false});
assert.equal(policy.find(rows,"social").status,"LAYOUT UNAVAILABLE");
assert.equal(policy.find(rows,"social").detail,
             "SOCIAL STORAGE // ERROR");
assert.equal(policy.find(rows,"notifications").status,
             "LOCAL ENGINE WAITING");
assert.equal(policy.find(rows,"social").context,
             "SAVED ACCOUNT NAMES // NOT LOADED");
assert.doesNotMatch(JSON.stringify(rows),/Stale|Personal|Work/);

assert.equal(policy.accountNamesCount(null,"identity-1"),0);
assert.equal(policy.accountNamesCount({identities:{}}, "identity-1"),0);
assert.equal(policy.accountNamesCount(
    {identities:{"identity-1":{accounts:{a:[],b:"",c:"One"}}}},
    "identity-1"),1);

// No new writer, no raw key model, no fake auth, no browser yank.
const service = read("services/connections/ConnectionsRegistry.qml");
assert.match(service,/pragma Singleton/);
assert.match(service,/qs\.services\.social/);
assert.match(service,/SocialIdentityStore\.snapshot/);
assert.match(service,/SocialAccountDetailsStore\.saved/);
assert.match(service,/NotificationsService\.historyReady/);
assert.match(service,/FirmsPolicy\.configuredKey/);
assert.match(service,/ConnectionPolicy\.build/);
assert.match(service,/SocialIdentityStore\.reloadFromDisk\(\)/);
assert.match(service,/SocialAccountDetailsStore\.refresh\(\)/);
assert.doesNotMatch(service,/FileView|Process\s*\{|setText\(|write\(|Qt\.openUrlExternally/);
assert.doesNotMatch(service,/property (?:var|string) (?:secret|token|mapKey)/i);

const cpu = read("widgets/CpuPlusW.qml");
const overview = read("widgets/cpuplus/CpuPlusSettingsConnectionsOverviewPane.qml");
const list = read("widgets/cpuplus/CpuPlusSettingsConnectionsListPane.qml");
const details = read("widgets/cpuplus/CpuPlusSettingsConnectionsDetailsPane.qml");
assert.match(cpu,/name: "CONNECTIONS", key: "CONNECTIONS"/);
assert.match(cpu,/CpuPlusSettingsConnectionsOverviewPane\s*\{/);
assert.match(cpu,/CpuPlusSettingsConnectionsListPane\s*\{/);
assert.match(cpu,/CpuPlusSettingsConnectionsDetailsPane\s*\{/);
assert.match(cpu,/settingsSubMode === "LOCATION"/);
assert.match(cpu,/settingsSubMode === "TIME"/);
assert.match(cpu,/selectedConnectionId = providerId/);
assert.match(overview,/ConnectionsRegistry\.refreshSocial\(\)/);
assert.match(list,/ConnectionsRegistry\.rows/);
assert.match(list,/selector\.providerSelected\(modelData\.id\)/);
assert.match(details,/ConnectionsRegistry\.entry\(selectedId\)/);
assert.match(details,/details\.guideOpen = !details\.guideOpen/);
assert.match(details,/visible: details\.selectedId === "social"/);
for(const item of [service,overview,list,details]) {
    assert.doesNotMatch(item,/Qt\.openUrlExternally|keyring|SecretService\s*\{|setAccountLabel|createIdentity\(|selectIdentity\(/);
}

// Social is an organization store and existing notification mail actions do
// not establish authentication. These boundaries must not be edited by C1.
assert.match(read("services/social/SocialIdentityStore.qml"),
             /Single writer for Social identity ORGANIZATION metadata/);
assert.match(read("services/social/SocialAccountDetailsStore.qml"),
             /Setup notes only\. Provider authentication is handled separately/);
assert.match(read("services/notifications/mail/ProtonRelayPilot.qml"),
             /mailboxAccess":false/);
console.log("C1 CPU++ Connections shared status, Social read-only bridge and no-secrets contracts: PASS");
