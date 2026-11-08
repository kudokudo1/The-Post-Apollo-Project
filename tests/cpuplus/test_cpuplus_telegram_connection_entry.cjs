#!/usr/bin/env node
"use strict";
// CPU++ Telegram entrypoint: actual navigation to existing provider owner,
// not a second Telegram login client, a forged authenticated session or Connect All.
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const policy={};
vm.runInNewContext(read("services/connections/ConnectionsPolicy.js")
    .replace(/^\.pragma library\s*/m,""),policy);
const inputs={
  socialState:"ready",socialSnapshot:{activeId:"identity-1",activeName:"Main"},
  socialAccountState:"ready",socialAccounts:{identities:{}},
  notificationsReady:true,firmKeyPresent:false
};
const rows=policy.build(inputs);
assert.equal(rows.length,9);
assert.deepEqual([...new Set(rows.map(x=>x.id))].sort(),rows.map(x=>x.id).sort());
const telegram=policy.find(rows,"telegram");
assert.equal(telegram.title,"TELEGRAM // NATIVE");
assert.equal(telegram.status,"CHECK SESSION IN SOCIAL");
assert.equal(telegram.action,"OPEN TELEGRAM");
assert.match(telegram.context,/SHARED DEFAULT/);
assert.match(telegram.context,/SOCIAL OPT-IN/);
assert.match(telegram.setup,/existing Social Telegram pane/);
assert.doesNotMatch(JSON.stringify(telegram),/AUTHORIZED AT LAST CHECK|CONNECTED \u002f\u002f VERIFIED|access_token|sessionPath|API HASH/);
assert.equal(policy.counters(rows).unverifiedAccounts,1); // Proton remains pending.
const details=read("widgets/cpuplus/CpuPlusSettingsConnectionsDetailsPane.qml");
const cpu=read("widgets/CpuPlusW.qml");
const shell=read("shell.qml");
const social=read("widgets/messanger/MessagingW.qml");
const native=read("services/messaging/adapters/TelegramAdapter.qml");
const bridge=read("services/messaging/bridges/telegram/bridge.py");
for(const part of [
  "signal telegramOpenRequested()",
  'visible: details.selectedId === "telegram"',
  'label: "OPEN TELEGRAM"',
  "onClicked: details.telegramOpenRequested()"
])assert.ok(details.includes(part),part);
assert.equal((details.match(/label: "OPEN TELEGRAM"/g)||[]).length,1);
assert.ok(cpu.includes("signal telegramAccessRequested()"));
assert.ok(cpu.includes("onTelegramOpenRequested:"));
assert.ok(cpu.includes('cpuPlusWindow.selectedConnectionId === "telegram"'));
assert.ok(cpu.includes("cpuPlusWindow.telegramAccessRequested();"));
assert.ok(shell.includes("onTelegramAccessRequested:"));
assert.ok(shell.includes("messagingWindow.openTelegramFromConnections()"));
assert.ok(shell.includes("cpuPlusWindow.close();"));
const fn=social.split("function openTelegramFromConnections() {",2)[1]
  .split("\n    }\n",1)[0];
assert.ok(fn.includes("if (browserConnectionNavigationPending)"));
assert.ok(fn.includes("menuOpen = true;"));
assert.ok(fn.includes("appSelector.settingsOpen = false;"));
assert.ok(fn.includes("activateApp(2, false);"));
assert.ok(fn.includes("return activeAppIndex === 2;"));
for(const forbidden of [
  "startLogin(","loginProcess","submitCode(","submitPhone(","sessionPath",
  "telegramIsolationEnabled =","telegramActiveIdentityId =",
  "SocialIdentityStore.selectIdentity(","secret-tool","ConnectionsBroker.authorize("
]) assert.ok(!fn.includes(forbidden),"Social router must not call "+forbidden);
for(const source of [details,cpu,shell]) {
  assert.ok(!source.includes("Telethon"),"No new Telegram client in CPU++");
}
assert.match(native,/function probe\(\)/);
assert.match(native,/healthProcess\.command = command\(\["health"\]\)/);
assert.match(bridge,/await client\.is_user_authorized\(\)/);
assert.match(bridge,/if args\.command == "health":/);
assert.ok(!details.includes('onClicked: ConnectionsBroker.authorize('));
assert.ok(!details.includes('onClicked: SocialIdentityStore.selectIdentity('));
assert.match(read("services/connections/ConnectionsBroker.qml"),
             /readonly property bool credentialActionsEnabled: false/);
assert.match(read("widgets/cpuplus/CpuPlusSettingsConnectionsDetailsPane.qml"),
             /CpuPlusIdAccountEditor \{/);
assert.equal((read("services/social/SocialAccountDetailsStore.qml").match(/id: writer/g)||[]).length,1);
console.log("CPU++ native Telegram routed to existing Social owner, no invented authority: PASS");
