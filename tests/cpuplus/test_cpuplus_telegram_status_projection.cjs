#!/usr/bin/env node
"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const policy={};
vm.runInNewContext(read("services/connections/ConnectionsTelegramStatusPolicy.js")
    .replace(/^\.pragma library\s*/m,""),policy);
const view=(v)=>JSON.parse(JSON.stringify(policy.project(v)));
const active=(mode,changes={})=>({
    nativeSelected:true,adapterActive:true,backendMode:mode,
    privateMode:false,scopeMatches:true,loginInProgress:false,
    operationBusy:false,...changes
});
test("absent, inactive and wrong private identity never assert authorization",()=>{
    for(const data of [null,{},[],active("READY",{nativeSelected:false}),
                       active("READY",{adapterActive:false}),
                       active("READY",{privateMode:true,scopeMatches:false}),
                       active("READY",{loginInProgress:true}),
                       active("READY",{privateMode:true,scopeMatches:null})]){
        const x=view(data);
        assert.equal(x.authorizedAtLastCheck,false);
        assert.equal(x.canRecheck,false);
        assert.doesNotMatch(x.status,/AUTHORIZED/);
    }
    assert.equal(view(active("READY",{privateMode:true,scopeMatches:false})).status,
                 "PRIVATE IDENTITY CHANGED // NOT CHECKED");
});
test("only native READY at a matching scope exposes last-checked result",()=>{
    const s=view(active("READY"));
    assert.equal(s.status,"PROVIDER AUTHORIZED AT LAST CHECK");
    assert.equal(s.scope,"SHARED SESSION");
    assert.equal(s.authorizedAtLastCheck,true);
    assert.equal(s.canRecheck,true);
    assert.match(s.detail,/NOT A GUARANTEE/);
    const p=view(active("READY",{privateMode:true}));
    assert.equal(p.scope,"PRIVATE SESSION");
    assert.equal(p.authorizedAtLastCheck,true);
    assert.equal(p.canRecheck,true);
    assert.doesNotMatch(JSON.stringify(p),/identity-\d|\.session|token|Bearer/);
});
test("pairing, checking and in-flight sends are not actionable",()=>{
    const pairing=view(active("READY",{loginInProgress:true}));
    assert.equal(pairing.status,"TELEGRAM PAIRING IN PROGRESS");
    assert.equal(pairing.canRecheck,false);
    assert.equal(view(active("PROBING")).canRecheck,false);
    assert.equal(view(active("READY",{operationBusy:true})).canRecheck,false);
});
test("auth-required and unknown provider strings are not silently promoted",()=>{
    assert.equal(view(active("AUTH_REQUIRED")).status,"SIGN-IN REQUIRED");
    assert.equal(view(active("APP_REQUIRED")).status,"TELEGRAM APP SETUP REQUIRED");
    assert.equal(view(active("DEPENDENCY_MISSING")).status,"TELEGRAM DEPENDENCY MISSING");
    for(const mode of [undefined,null,12,{},"AUTHORIZED","CONNECTED",
                       "READY\nLOGIN=YES","READY // SECRET_TOKEN","SUCCESS"]) {
        const out=view(active(mode));
        assert.equal(out.authorizedAtLastCheck,false);
        assert.equal(out.status,"TELEGRAM STATUS UNAVAILABLE");
        assert.doesNotMatch(JSON.stringify(out),/SECRET_TOKEN/);
    }
});
test("read-only real adapter connection and recheck chain, no second login owner",()=>{
    const social=read("widgets/messanger/MessagingW.qml");
    const adapter=read("services/messaging/adapters/TelegramAdapter.qml");
    const bridge=read("services/messaging/bridges/telegram/bridge.py");
    const cpu=read("widgets/CpuPlusW.qml");
    const details=read("widgets/cpuplus/CpuPlusSettingsConnectionsDetailsPane.qml");
    const shell=read("shell.qml");
    const broker=read("services/connections/ConnectionsBroker.qml");
    assert.match(social,/readonly property var telegramConnectionObservation/);
    for(const bit of [
        "nativeSelected: messagingWindow.activeAppIndex === 2",
        "adapterActive: messageRouter.telegramBackend.active",
        "backendMode: messageRouter.telegramBackend.backendMode",
        "scopeMatches: !messagingWindow.telegramIsolationEnabled",
        "messageRouter.telegramBackend.identityId",
        "loginInProgress: messageRouter.telegramBackend.loginInProgress"
    ])assert.ok(social.includes(bit),bit);
    const fn=social.split("function recheckTelegramFromConnections() {",2)[1]
                   .split("\n    }\n",1)[0];
    for(const gate of ["activeAppIndex !== 2","!adapter.active",
        "!adapter.scopeValid","!state.scopeMatches","adapter.loginInProgress",
        "adapter.sending","adapter.appKeyStatusBusy",
        'adapter.backendMode === "PROBING"'])
        assert.ok(fn.includes(gate),"Missing recheck gate: "+gate);
    assert.match(fn,/adapter\.probe\(\);/);
    for(const forbidden of [
       "startLogin(","submitPhone(","submitCode(","saveApplicationKeys(",
       "loginProcess","--identity","session","log_out","unlink(","Qt.openUrl"
    ])assert.ok(!fn.includes(forbidden),"Unsafe recheck side effect "+forbidden);
    assert.match(adapter,/function probe\(\)/);
    assert.match(adapter,/healthProcess\.command = command\(\["health"\]\)/);
    assert.match(bridge,/await client\.is_user_authorized\(\)/);
    assert.ok(details.includes('import "../../services/connections/ConnectionsTelegramStatusPolicy.js" as TelegramStatus'));
    assert.ok(details.includes("readonly property var telegramStatus: TelegramStatus.project(telegramObservation)"));
    assert.ok(details.includes("signal telegramRecheckRequested()"));
    assert.ok(details.includes('visible: details.telegramStatus.canRecheck'));
    assert.ok(details.includes('label: "RECHECK SESSION"'));
    assert.ok(details.includes("onClicked: details.telegramRecheckRequested()"));
    assert.ok(details.includes("details.telegramStatus.authorizedAtLastCheck"));
    assert.ok(details.includes("CpuPlusIdAccountEditor {"));
    assert.ok(cpu.includes("signal telegramRecheckRequested()"));
    assert.ok(cpu.includes("telegramObservation: cpuPlusWindow.telegramConnectionObservation"));
    assert.ok(cpu.includes('cpuPlusWindow.selectedConnectionId === "telegram"'));
    assert.ok(cpu.includes("settingsConnectionsDetails.telegramStatus.canRecheck"));
    assert.ok(shell.includes("telegramConnectionObservation: messagingWindow"));
    assert.ok(shell.includes("messagingWindow.telegramConnectionObservation"));
    assert.ok(shell.includes("onTelegramRecheckRequested:"));
    assert.ok(shell.includes("messagingWindow.recheckTelegramFromConnections();"));
    assert.match(broker,/readonly property bool credentialActionsEnabled: false/);
    for(const src of [cpu,details,shell]){
        for(const forbidden of ["Telethon","secret-tool","ConnectionsBroker.authorize(",
                                "session.unlink(","log_out(","SocialIdentityStore.selectIdentity("])
            assert.ok(!src.includes(forbidden),"Privileged operation in CPU++ "+forbidden);
    }
});
