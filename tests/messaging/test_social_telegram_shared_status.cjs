"use strict";

/** Shared Telegram status UI. Real QML function evaluated against synthetic
 * adapter states: no provider, credentials, Sway, or live user sessions. */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const selector = fs.readFileSync(path.join(root,"widgets/messanger/AppSelector.qml"),"utf8");
const host = fs.readFileSync(path.join(root,"widgets/messanger/MessagingW.qml"),"utf8");
const adapter = fs.readFileSync(path.join(root,"services/messaging/adapters/TelegramAdapter.qml"),"utf8");
const bridge = fs.readFileSync(path.join(root,"services/messaging/bridges/telegram/bridge.py"),"utf8");
const router = fs.readFileSync(path.join(root,"services/messaging/SocialMessageRouter.qml"),"utf8");
const identity = fs.readFileSync(path.join(root,"services/social/SocialIdentityStore.qml"),"utf8");
const pane = selector.split("id: settingsIdentityPane")[1]?.split("id: settingsEditorPane")[0];
assert.ok(pane,"Existing contact pane must remain");
const match=selector.match(
    /    function sharedTelegramStatusText\(\) \{([\s\S]*?)\n    \}\n\n    function browserAccountServiceSupported\(/
);
assert.ok(match,"Shared Telegram status formatter must be present");
function render(settings) {
    const state={
        accountSelectedServiceId:"telegram",
        sharedTelegramActive:false,
        sharedTelegramLoginInProgress:false,
        sharedTelegramBackendMode:"UNAVAILABLE",
        telegramIdentityModeActive:false,
        telegramIdentityScopeId:"",
        identitySnapshot:{activeId:"identity-1"},
        ...settings,
    };
    return vm.runInNewContext(
        "function sharedTelegramStatusText() {" + match[1] + "\n}\nsharedTelegramStatusText();",
        {appSelector:state}
    );
}
const cases=[
    [{accountSelectedServiceId:"x",sharedTelegramActive:true,sharedTelegramBackendMode:"READY"},""],
    [{sharedTelegramBackendMode:"READY"},"NOT CHECKED IN THIS VIEW // OPEN TELEGRAM"],
    [{sharedTelegramActive:true,sharedTelegramBackendMode:"READY"},
     "PROVIDER AUTHORIZED AT LAST CHECK // SHARED SESSION"],
    [{sharedTelegramActive:true,sharedTelegramBackendMode:"AUTH_REQUIRED"},
     "SIGN-IN REQUIRED // SHARED SESSION"],
    [{sharedTelegramActive:true,sharedTelegramBackendMode:"APP_REQUIRED"},
     "TELEGRAM APP SETUP REQUIRED // SHARED SESSION"],
    [{sharedTelegramActive:true,sharedTelegramBackendMode:"DEPENDENCY_MISSING"},
     "TELEGRAM PROVIDER UNAVAILABLE // DEPENDENCY MISSING"],
    [{sharedTelegramActive:true,sharedTelegramBackendMode:"PROBING"},
     "CHECKING TELEGRAM PROVIDER..."],
    [{sharedTelegramActive:true,sharedTelegramBackendMode:"ERROR"},
     "TELEGRAM STATUS UNAVAILABLE // SHARED SESSION"],
    [{sharedTelegramActive:true,sharedTelegramLoginInProgress:true,
      sharedTelegramBackendMode:"READY"},
     "TELEGRAM PAIRING IN PROGRESS // SHARED SESSION"],
    [{telegramIdentityModeActive:true,telegramIdentityScopeId:"identity-1",
      sharedTelegramActive:true,sharedTelegramBackendMode:"READY"},
     "PROVIDER AUTHORIZED AT LAST CHECK // PRIVATE SESSION // identity-1"],
    [{telegramIdentityModeActive:true,telegramIdentityScopeId:"identity-1",
      sharedTelegramActive:true,sharedTelegramBackendMode:"AUTH_REQUIRED"},
     "SIGN-IN REQUIRED // PRIVATE SESSION // identity-1"],
    [{telegramIdentityModeActive:true,telegramIdentityScopeId:"identity-2",
      sharedTelegramActive:true,sharedTelegramBackendMode:"READY"},
     "CHANGING TELEGRAM IDENTITY // NOT YET CHECKED"],
];
for(const [settings,expected]of cases)
    assert.equal(render(settings),expected,JSON.stringify(settings));
assert.match(render({sharedTelegramActive:true,sharedTelegramBackendMode:"READY"}),/LAST CHECK/);
assert.doesNotMatch(render({sharedTelegramActive:false,sharedTelegramBackendMode:"READY"}),/AUTHORIZED/);

// UI remains in the current narrow contact pane with reused ActionButtons.
for(const part of [
    'text: "LINKED ACCOUNTS"',
    '? "TELEGRAM // PRIVATE ACCOUNT" : "TELEGRAM // SHARED SESSION"',
    'label: appSelector.telegramIdentityModeActive',
    '? "USE SHARED TELEGRAM" : "USE PRIVATE TELEGRAM ACCOUNTS"',
    'text: "Telegram uses one legacy personal session.',
    'text: appSelector.sharedTelegramStatusText()',
    'label: "OPEN TELEGRAM"',
    'label: "RECHECK SHARED TELEGRAM"',
    'onTriggered: appSelector.sharedTelegramOpenRequested()',
    'onTriggered: appSelector.sharedTelegramRecheckRequested()',
    'appSelector.accountSelectedServiceId === "telegram"',
]){
    assert.ok(pane.includes(part),part);
}
assert.ok(selector.includes("function sharedTelegramStatusText()"));
assert.ok(selector.includes("signal sharedTelegramOpenRequested()"));
assert.ok(selector.includes("signal sharedTelegramRecheckRequested()"));
assert.ok(selector.includes("!appSelector.sharedTelegramLoginInProgress"));
assert.ok(selector.includes('appSelector.sharedTelegramBackendMode !== "PROBING"'));

// Router and Telethon remain sole native-provider owners. No account notes
// are used as identity-specific proof of Telegram authorization.
assert.ok(router.includes('readonly property var telegramBackend: telegram'));
assert.ok(router.includes('active: router.appIndex === 2'));
assert.ok(adapter.includes('function probe()'));
assert.ok(adapter.includes('healthProcess.command = command(["health"])'));
assert.ok(adapter.includes('healthRequestSerial = activationSerial'));
assert.ok(adapter.includes('property string identityId: ""'));
assert.ok(adapter.includes('commandArgs.push("--identity", identityId)'));
assert.ok(router.includes('identityId: router.telegramIdentityId'));
assert.ok(router.includes('telegramScopedServiceId'));
assert.ok(host.includes('function toggleTelegramIsolation()'));
assert.ok(host.includes('function reconcilePersistedTelegramIdentity()'));
assert.ok(host.includes('messageRouter.telegramScopedServiceId'));
assert.ok(adapter.includes('if (!adapter.active)'));
assert.ok(bridge.includes('await client.is_user_authorized()'));
assert.ok(bridge.includes('return {"mode": "READY", "detail": "Telegram account authorized"}'));
assert.ok(bridge.includes('"personal.session"'));
assert.ok(identity.includes('QR pairing, secret storage and live account switching stay separate.'));

// Host navigation is explicit and resumes the existing Telegram wizard;
// closing Settings cannot spuriously reopen the previous browser.
for(const part of [
    "function openSharedTelegram()",
    "function recheckSharedTelegram()",
    'appSelector.accountSelectedServiceId !== "telegram"',
    'appSelector.accountEditorIdentityId !== snap.activeId',
    'browserConnectionNavigationPending = true;',
    'appSelector.settingsOpen = false;',
    'activateApp(2);',
    'browserConnectionNavigationPending = false;',
    'activeAppIndex !== 2',
    'messageRouter.telegramBackend.probe();',
    'sharedTelegramActive: messageRouter.telegramBackend.active',
    'sharedTelegramBackendMode: messageRouter.telegramBackend.backendMode',
    'sharedTelegramLoginInProgress:',
    'onSharedTelegramOpenRequested: messagingWindow.openSharedTelegram()',
    'onSharedTelegramRecheckRequested: messagingWindow.recheckSharedTelegram()',
]){
    assert.ok(host.includes(part),part);
}
assert.ok(host.includes("function openBrowserAccountSignIn(serviceId, identityId)"));
assert.ok(host.includes("function inspectBrowserAccountWindow(serviceId, identityId)"));
assert.equal((host.match(/FloatingWindow \{/g)||[]).length,1);
assert.equal((selector.match(/id: settingsFooter/g)||[]).length,1);
const labels=[...selector.matchAll(/\bname:\s*"([^"]+)"/g)].map(m=>m[1]);
assert.equal(labels.length,32);
assert.deepEqual(labels.slice(0,4),["SESSIONS","DISCORD","TELEGRAM","X"]);
assert.equal(labels.at(-1),"BEREAL");
assert.ok(selector.includes('model: appSelector.railRows'));
assert.ok(selector.includes('id: settingsFamilyPane'));
assert.ok(selector.includes('id: settingsAppPane'));

console.log("Social Telegram status: shared/private scope states and UI isolation passed");
