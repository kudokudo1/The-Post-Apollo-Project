#!/usr/bin/env node
"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const cp=require("node:child_process");
const ROOT=path.resolve(__dirname,"../..");
const file=path.join(__dirname,"fixtures/TaskNativeKeyringRecoveryM13h.cjs");
const sh=path.join(__dirname,"fixtures/TaskNativeKeyringIsolatedCIM13h.sh");
test("does not access keyring without explicit disposable run argument",()=>{
    const a=cp.spawnSync(process.execPath,[file],{
        encoding:"utf8",timeout:3000,env:{PATH:process.env.PATH||"/usr/bin:/bin"}});
    assert.equal(a.status,0);
    assert.equal(a.stdout.trim(),"M13H_MANUAL_DISPOSABLE_TEST_ONLY");
    assert.equal(a.stderr,"");
});
test("manual native test has scope guards and random unique label, not global unlock",()=>{
    const text=fs.readFileSync(file,"utf8");
    assert.match(text,/--native-disposable-test/);
    assert.match(text,/crypto\.randomBytes\(16\)\.toString\('hex'\)/);
    assert.match(text,/post-apollo-tasks-m13h-disposable-test/);
    assert.match(text,/secret\(\['clear',\.\.\.attrs\(token\)\]\)/);
    assert.match(text,/C\.O_CREAT\|C\.O_EXCL\|C\.O_NOFOLLOW/);
    assert.match(text,/if\(process\.platform!=='linux'/);
    assert.match(text,/fs\.mkdtempSync\(path\.join\(os\.tmpdir\(\),'postapollo-m13h-'\)\)/);
    assert.match(text,/fs\.rmdirSync\(root\)/);
    assert.match(text,/M13H_TEST_KEY_CLEANUP_UNVERIFIED id=/);
    assert.doesNotMatch(text,/rmSync\(|execSync\(|systemctl|gnome-keyring-daemon --unlock|pkill/);
    assert.doesNotMatch(text,/Quickshell\.dataDir|apollo-hub-todo-v1\.json/);
});
test("CI executes same manual harness in separate disposable HOME and bus",()=>{
    const text=fs.readFileSync(sh,"utf8");
    assert.match(text,/dbus-run-session/); // Called externally by workflow.
    assert.match(text,/gnome-keyring-daemon --unlock --components=secrets/);
    assert.match(text,/--native-disposable-test/);
    assert.match(text,/M13H_NATIVE_ENCRYPTED_RESTART_PASS/);
    assert.doesNotMatch(text,/sudo |\\/var\\/home\\//);
});
test("production TASKS still has one FileView and compile-time disabled guards",()=>{
    const store=fs.readFileSync(path.join(ROOT,"services/hub/ApolloHubTodoStore.qml"),"utf8");
    const shell=fs.readFileSync(path.join(ROOT,"shell.qml"),"utf8");
    assert.doesNotMatch(store+shell,/TaskNativeKeyringRecoveryM13h/);
    assert.equal((store.match(/\bFileView\s*\{/g)||[]).length,1);
    assert.equal((store.match(/\btodoFile\.setText\s*\(/g)||[]).length,1);
    for(const k of ["ticketProducerEnabled","guardedWriterEnabled",
        "independentlyAuthenticatedTicketReceipt"])
        assert.match(store,new RegExp("readonly property bool "+k+":\\s*false"));
});
