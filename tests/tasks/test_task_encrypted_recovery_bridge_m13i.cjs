#!/usr/bin/env node
"use strict";
// M13i source contracts. CI does NOT instantiate the native Quickshell scene.
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const root=path.resolve(__dirname,"../..");
const read=(name)=>fs.readFileSync(path.join(root,name),"utf8");
const store=read("services/hub/ApolloHubTodoStore.qml");
const bridge=read("services/hub/TaskEncryptedRecoveryBridgeM13i.qml");
const provider=read("services/hub/TaskRecoveryProviderHostM13i.py");
const standalone=read("TaskEncryptedRecoveryHarnessM13i.qml");
const shell=read("shell.qml");

test("one live TASKS FileView, no second writer or source activation",()=>{
    assert.equal((store.match(/\bFileView\s*\{/g)||[]).length,1);
    assert.equal((store.match(/\btodoFile\.setText\s*\(/g)||[]).length,1);
    for(const gate of [
        "guardedWriterEnabled","ticketProducerEnabled",
        "independentlyAuthenticatedTicketReceipt",
        "encryptedRecoveryEnabled","encryptedRecoveryStorageAuthorized",
        "encryptedRecoveryUnlockAuthorized"
    ])
        assert.match(store,new RegExp(
            "readonly property bool "+gate+":\\s*false"));
    assert.match(store,/TaskEncryptedRecoveryBridgeM13i\s*\{\s*id:\s*encryptedRecoveryBridge/);
    assert.match(store,/function inspectEncryptedRecoveryProvider\(\)\s*\{[\s\S]*?encryptedRecoveryBridge\.inspectProvider\(\)/);
    assert.match(store,/readonly property string encryptedRecoveryProviderStatus:[\s\S]*?encryptedRecoveryBridge\.providerStatus/);
    assert.doesNotMatch(store,/\b(?:secret-tool|gnome-keyring-daemon)\b/);
});

test("QML bridge is loaded but only probes via explicit call, never on instantiation",()=>{
    assert.match(bridge,/readonly property bool encryptedRecoveryEnabled:\s*false/);
    for(const permission of [
        "userOptedIn","trustedKeyReleaseVerified","canPersistDraft",
        "canDecryptDraft","canRestoreDraft","canDeleteDraft",
        "canExportDraft","canWriteTaskSource","productionActivation"
    ])
        assert.match(bridge,new RegExp(
            "readonly property bool "+permission+":\\s*false"));
    assert.match(bridge,/function inspectProvider\(\)/);
    assert.match(bridge,/probe\.exec\(\["python3", "-B", "-I"/);
    assert.match(bridge,/Quickshell\.shellPath\("services\/hub\/TaskRecoveryProviderHostM13i\.py"\)/);
    assert.match(bridge,/Process\s*\{\s*id:\s*probe/);
    assert.match(bridge,/SplitParser\s*\{/);
    assert.match(bridge,/onRead:\s*function\(line\)/);
    assert.match(bridge,/onExited:\s*function\(code,\s*exitStatus\)/);
    assert.match(bridge,/msg\.providerPresent !== \(msg\.status === "SERVICE_ACQUIRED"\)/);
    assert.doesNotMatch(bridge,/\brunning:\s*true\b/);
    assert.doesNotMatch(bridge,/\b(?:FileView|StdioWriter|stdinEnabled)\s*[:{]/);
    assert.doesNotMatch(bridge,/\.write\(|\.setText\(|\.unlock\(|\.delete\(/);
});

test("provider process uses only the non-activating DBus daemon query",()=>{
    assert.match(provider,/NameHasOwner/);
    assert.match(provider,/org\.freedesktop\.DBus/);
    assert.match(provider,/org\.freedesktop\.secrets/);
    assert.match(provider,/sys\.argv\[1:\] == \["--probe"\]/);
    assert.match(provider,/timeout=4/);
    for(const forbidden of [
        "secret-tool","OpenSession","--unlock","CreateItem","Delete",
        "gnome-keyring-daemon","org.freedesktop.Secret.Collection",
        "set_password","get_password","subprocess.Popen"
    ])
        assert.equal(provider.includes(forbidden),false,
            "unsupported provider operation: "+forbidden);
    assert.doesNotMatch(provider,/\b(?:open|write|unlink|mkdir|remove)\s*\(/);
});

test("standalone UI is read-only and not included in live shell",()=>{
    assert.match(standalone,/TaskEncryptedRecoveryBridgeM13i\s*\{/);
    assert.match(standalone,/onClicked:\s*bridge\.inspectProvider\(\)/);
    assert.match(standalone,/RECOVERY \/\/ DISABLED/);
    assert.match(standalone,/CHECK PROVIDER/);
    assert.doesNotMatch(standalone,/secret-tool|setText\(|FileView\s*\{/);
    assert.doesNotMatch(shell,/TaskEncryptedRecoveryHarnessM13i/);
});

test("existing TASKS mutation method names are unchanged",()=>{
    for(const method of [
        "addTask","renameTask","setTaskDone","removeTask",
        "updateTaskDetails","createProject","renameProject",
        "deleteProject","assignTaskProject"
    ])
        assert.match(store,new RegExp("function "+method+"\\("));
});
